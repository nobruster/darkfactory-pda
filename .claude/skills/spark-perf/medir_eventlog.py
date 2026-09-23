#!/usr/bin/env python3
"""Mede um job ou um pipeline Spark pelo event log e compara com uma baseline.

Python puro (stdlib), sem pyspark: roda fora do contêiner, sobre o diretório
que `spark.eventLog.dir` gravou.

Três modos, cada um com token estável na última linha:

  relatorio  <eventlog>                                   -> MEDICAO=OK|NAO_MEDIDO
  baseline   <eventlog> --resultado R --gravar B [--substituir]
                                                          -> BASELINE=GRAVADA|RECUSADA|NAO_MEDIDO
  comparar   <eventlog> --resultado R --baseline B [--tolerancia 0.10]
                                                          -> PERF=MELHOR|IGUAL|PIOR|NAO_MEDIDO

<eventlog> pode ser um arquivo de log, um diretório `eventlog_v2_*` (rolling)
ou um diretório com vários apps (o pipeline inteiro: um diretório por execução).

Doutrina (AGENTS.md):
  - Regra 9: log ausente, em andamento, comprimido, corrompido ou com zero
    tasks devolve NAO_MEDIDO, nunca IGUAL. Descartes são contados.
  - Regras 3 e 5: performance nunca troca resultado. `comparar` exige o
    arquivo de resultado (controles em string/Decimal + exceptAll contra a
    saída da baseline). Resultado diferente devolve PIOR — é defeito, não ganho.
  - Regra 3: a baseline não é sobrescrita sem `--substituir` explícito.

Campos lidos (JsonProtocol do Spark 3.5): SparkListenerTaskEnd."Task Metrics"
{"Executor Run Time", "Executor CPU Time", "JVM GC Time", "Memory Bytes Spilled",
"Disk Bytes Spilled", "Shuffle Read Metrics" {"Remote Bytes Read",
"Local Bytes Read", "Total Records Read"}, "Shuffle Write Metrics"
{"Shuffle Bytes Written", "Shuffle Records Written"}, "Input Metrics"
{"Bytes Read", "Records Read"}, "Output Metrics" {"Bytes Written",
"Records Written"}} e SparkListenerStageCompleted."Stage Info".
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

CODECS = (".zstd", ".lz4", ".lzf", ".snappy")
IGNORAR = (".crc",)

# Métricas que decidem o veredito. (chave, rótulo, piso absoluto de ruído)
# O piso evita chamar de PIOR 40 ms a mais num job de 300 ms.
METRICAS_GATE = (
    ("parede_ms", "tempo de parede (ms)", 2000),
    ("executor_run_ms", "tempo de executor (ms)", 2000),
    ("shuffle_bytes", "shuffle lido+escrito (bytes)", 16 * 1024 * 1024),
    ("spill_disco_bytes", "spill em disco (bytes)", 1),
    ("spill_memoria_bytes", "spill em memória (bytes)", 64 * 1024 * 1024),
)

AMBIENTE_CHAVES = ("spark.master", "spark.driver.memory", "spark.executor.memory",
                   "spark.executor.cores", "spark.executor.instances")


class NaoMedido(Exception):
    """Ausência de medição. Nunca vira IGUAL."""


# --------------------------------------------------------------------------- leitura

def localizar_logs(caminho: Path) -> list[list[Path]]:
    """Devolve uma lista de apps; cada app é a lista ordenada dos seus arquivos."""
    if not caminho.exists():
        raise NaoMedido(f"event log não existe: {caminho}")
    if caminho.is_file():
        return [[caminho]]
    if caminho.name.startswith("eventlog_v2_"):
        return [_arquivos_rolling(caminho)]
    apps: list[list[Path]] = []
    for filho in sorted(caminho.iterdir()):
        if filho.name.startswith(".") or filho.name.endswith(IGNORAR):
            continue
        if filho.is_dir() and filho.name.startswith("eventlog_v2_"):
            apps.append(_arquivos_rolling(filho))
        elif filho.is_file():
            apps.append([filho])
    if not apps:
        raise NaoMedido(f"nenhum event log em {caminho}")
    return apps


def _arquivos_rolling(d: Path) -> list[Path]:
    status = [f for f in d.iterdir() if f.name.startswith("appstatus_")]
    if any(f.name.endswith(".inprogress") for f in status):
        raise NaoMedido(f"app ainda em andamento (appstatus .inprogress): {d.name}")
    evs = [f for f in d.iterdir() if f.name.startswith("events_")]
    if not evs:
        raise NaoMedido(f"diretório rolling sem events_*: {d.name}")
    return sorted(evs, key=lambda f: int(f.name.split("_")[1]))


def _checar_arquivo(f: Path) -> None:
    nome = f.name
    if nome.endswith(".inprogress"):
        raise NaoMedido(f"app não terminou (ou não chamou spark.stop()): {nome}")
    base = nome[:-len(".compact")] if nome.endswith(".compact") else nome
    if base.endswith(CODECS):
        raise NaoMedido(f"log comprimido ({nome}); este leitor é stdlib. "
                        "Rode com spark.eventLog.compress=false")


def ler_app(arquivos: list[Path]) -> dict:
    app = {"arquivos": [str(f) for f in arquivos], "nome": None, "id": None,
           "versao_spark": None, "inicio": None, "fim": None, "ambiente": {},
           "sql": {}, "estagios": {}, "tarefas": {}, "linhas": 0, "descartes": 0,
           "tarefas_sem_metricas": 0, "ts_ultimo": None, "ts_retrocessos": [],
           "ts_max": None}
    for f in arquivos:
        _checar_arquivo(f)
        with f.open("r", encoding="utf-8", errors="strict") as fh:
            for linha in fh:
                if not linha.strip():
                    continue
                app["linhas"] += 1
                try:
                    ev = json.loads(linha)
                except json.JSONDecodeError:
                    app["descartes"] += 1
                    continue
                _consumir(app, ev)
    return app


def _marcar_ts(app: dict, ts) -> None:
    """Timestamps de parede em ordem de arquivo não podem voltar atrás.

    `Executor Run Time` vem de System.nanoTime() (monotônico); `Timestamp`,
    `Submission/Completion Time` e `Finish Time` vêm do relógio de parede, que
    pode saltar (NTP, WSL2). Retrocesso > 1 s marca a parede como inconsistente.
    """
    if not isinstance(ts, int) or ts <= 0:
        return
    if app["ts_ultimo"] is not None and ts < app["ts_ultimo"] - 1000:
        app["ts_retrocessos"].append(app["ts_ultimo"] - ts)
    app["ts_ultimo"] = ts
    app["ts_max"] = ts if app["ts_max"] is None else max(app["ts_max"], ts)


def _consumir(app: dict, ev: dict) -> None:
    tipo = ev.get("Event")
    # ApplicationStart carrega o startTime do SparkContext, anterior a eventos
    # gravados antes dele (BlockManagerAdded): retrocesso estrutural, não salto
    # de relógio. Medido: ~1,1 s em todo log do 3.5.9. Fica fora da checagem.
    if tipo != "SparkListenerApplicationStart":
        _marcar_ts(app, ev.get("Timestamp") or ev.get("Submission Time")
                   or ev.get("Completion Time"))
    info_ts = ev.get("Stage Info") or ev.get("Task Info") or {}
    _marcar_ts(app, info_ts.get("Completion Time") or info_ts.get("Finish Time"))
    if tipo == "SparkListenerLogStart":
        app["versao_spark"] = ev.get("Spark Version")
    elif tipo == "SparkListenerApplicationStart":
        app["nome"], app["id"] = ev.get("App Name"), ev.get("App ID")
        app["inicio"] = ev.get("Timestamp")
    elif tipo == "SparkListenerApplicationEnd":
        app["fim"] = ev.get("Timestamp")
    elif tipo == "SparkListenerEnvironmentUpdate":
        props = ev.get("Spark Properties") or {}
        if isinstance(props, list):             # formatos antigos: lista de pares
            props = dict(props)
        app["ambiente"] = {k: v for k, v in props.items()
                           if k in AMBIENTE_CHAVES or k.startswith("spark.sql.")}
    elif tipo == "SparkListenerStageCompleted":
        info = ev.get("Stage Info") or {}
        chave = (info.get("Stage ID"), info.get("Stage Attempt ID"))
        app["estagios"][chave] = {
            "nome": info.get("Stage Name", ""),
            "n_tarefas": info.get("Number of Tasks"),
            "submissao": info.get("Submission Time"),
            "conclusao": info.get("Completion Time"),
            "falha": info.get("Failure Reason"),
        }
    elif tipo == "SparkListenerTaskEnd":
        chave = (ev.get("Stage ID"), ev.get("Stage Attempt ID"))
        motivo = (ev.get("Task End Reason") or {}).get("Reason", "?")
        m = ev.get("Task Metrics")
        lista = app["tarefas"].setdefault(chave, [])
        if m is None:
            app["tarefas_sem_metricas"] += 1
            lista.append({"ok": motivo == "Success", "sem_metricas": True})
            return
        sr = m.get("Shuffle Read Metrics") or {}
        sw = m.get("Shuffle Write Metrics") or {}
        im = m.get("Input Metrics") or {}
        om = m.get("Output Metrics") or {}
        lista.append({
            "ok": motivo == "Success",
            "run_ms": m.get("Executor Run Time", 0),
            "cpu_ns": m.get("Executor CPU Time", 0),
            "gc_ms": m.get("JVM GC Time", 0),
            "spill_mem": m.get("Memory Bytes Spilled", 0),
            "spill_disco": m.get("Disk Bytes Spilled", 0),
            "shuffle_lido": sr.get("Remote Bytes Read", 0) + sr.get("Local Bytes Read", 0),
            "shuffle_escrito": sw.get("Shuffle Bytes Written", 0),
            "entrada_bytes": im.get("Bytes Read", 0),
            "entrada_linhas": im.get("Records Read", 0),
            "saida_bytes": om.get("Bytes Written", 0),
            "saida_linhas": om.get("Records Written", 0),
        })


# --------------------------------------------------------------------------- agregação

def _razao(valores: list[int]) -> Optional[float]:
    if len(valores) < 2:
        return None
    med = statistics.median(valores)
    return None if med <= 0 else max(valores) / med


def agregar_app(app: dict, min_tarefas_skew: int) -> dict:
    estagios = []
    tot = dict(tarefas=0, falhas=0, executor_run_ms=0, cpu_ms=0, gc_ms=0,
               shuffle_lido=0, shuffle_escrito=0, spill_memoria_bytes=0,
               spill_disco_bytes=0, entrada_bytes=0, saida_bytes=0)
    for chave in sorted(set(app["tarefas"]) | set(app["estagios"]),
                        key=lambda c: (c[0] or 0, c[1] or 0)):
        ts = app["tarefas"].get(chave, [])
        ok = [t for t in ts if t["ok"] and not t.get("sem_metricas")]
        info = app["estagios"].get(chave, {})
        s = lambda k: sum(t[k] for t in ok)
        run = [t["run_ms"] for t in ok]
        bytes_task = [t["entrada_bytes"] + t["shuffle_lido"] for t in ok]
        parede = None
        if info.get("submissao") and info.get("conclusao"):
            parede = info["conclusao"] - info["submissao"]
        e = {
            "app": app["nome"], "estagio": chave[0], "tentativa": chave[1],
            "nome": info.get("nome", "?"), "tarefas": len(ok),
            "falhas": len(ts) - len(ok), "parede_ms": parede,
            "executor_run_ms": s("run_ms"), "gc_ms": s("gc_ms"),
            "task_max_ms": max(run) if run else 0,
            "task_mediana_ms": statistics.median(run) if run else 0,
            "skew_tempo": _razao(run) if len(ok) >= min_tarefas_skew else None,
            "skew_bytes": _razao(bytes_task) if len(ok) >= min_tarefas_skew else None,
            "entrada_bytes": s("entrada_bytes"), "saida_bytes": s("saida_bytes"),
            "shuffle_lido": s("shuffle_lido"), "shuffle_escrito": s("shuffle_escrito"),
            "spill_memoria_bytes": s("spill_mem"), "spill_disco_bytes": s("spill_disco"),
            "falha_estagio": info.get("falha"),
        }
        estagios.append(e)
        tot["tarefas"] += e["tarefas"]
        tot["falhas"] += e["falhas"]
        for k in ("executor_run_ms", "gc_ms", "shuffle_lido", "shuffle_escrito",
                  "spill_memoria_bytes", "spill_disco_bytes", "entrada_bytes", "saida_bytes"):
            tot[k] += e[k]
        tot["cpu_ms"] += sum(t["cpu_ns"] for t in ok) // 1_000_000
    tot["shuffle_bytes"] = tot["shuffle_lido"] + tot["shuffle_escrito"]
    tot["parede_ms"] = (app["fim"] - app["inicio"]) if app["fim"] and app["inicio"] else None
    consistente = (not app["ts_retrocessos"]
                   and (app["ts_max"] is None or app["fim"] is None
                        or app["ts_max"] <= app["fim"] + 1000))
    return {"relogio_consistente": consistente,
            "relogio_retrocesso_max_ms": max(app["ts_retrocessos"], default=0),
            "nome": app["nome"], "id": app["id"], "versao_spark": app["versao_spark"],
            "ambiente": app["ambiente"], "linhas_log": app["linhas"],
            "descartes": app["descartes"], "tarefas_sem_metricas": app["tarefas_sem_metricas"],
            "totais": tot, "estagios": estagios}


def medir(caminho: Path, min_tarefas_skew: int = 4) -> dict:
    apps = []
    for arquivos in localizar_logs(caminho):
        app = ler_app(arquivos)
        rot = arquivos[0].parent.name if arquivos[0].name.startswith("events_") else arquivos[0].name
        if app["linhas"] == 0:
            raise NaoMedido(f"log vazio: {rot}")
        if app["descartes"]:
            raise NaoMedido(f"{app['descartes']} linha(s) ilegível(is) em {rot}; "
                            "medição incompleta não compara")
        if app["fim"] is None:
            raise NaoMedido(f"sem SparkListenerApplicationEnd em {rot}")
        apps.append(agregar_app(app, min_tarefas_skew))
    nomes = [a["nome"] for a in apps]
    if len(set(nomes)) != len(nomes):
        raise NaoMedido(f"nomes de app repetidos no diretório {nomes}: "
                        "uma execução por diretório, apps com spark.app.name distinto")
    total = {k: 0 for k in ("tarefas", "falhas", "parede_ms", "executor_run_ms", "cpu_ms",
                            "gc_ms", "shuffle_bytes", "shuffle_lido", "shuffle_escrito",
                            "spill_memoria_bytes", "spill_disco_bytes", "entrada_bytes",
                            "saida_bytes")}
    for a in apps:
        for k in total:
            total[k] += a["totais"][k] or 0
    if total["tarefas"] == 0:
        raise NaoMedido("zero tasks concluídas com métricas: nada foi medido")
    return {"apps": apps, "total": total}


# --------------------------------------------------------------------------- relatório

def _mb(b: int) -> str:
    return f"{b / 1048576:,.1f}"


def _r(x: Optional[float]) -> str:
    return "-" if x is None else f"{x:.1f}"


def imprimir(med: dict, skew_limite: float, gc_limite: float) -> None:
    cab = (f"{'app':<18} {'stg':>4} {'tsk':>5} {'parede':>8} {'run_ms':>9} "
           f"{'max/med':>7} {'skB':>5} {'in_MB':>8} {'shR_MB':>8} {'shW_MB':>8} "
           f"{'spM_MB':>8} {'spD_MB':>8}  sinais  nome")
    print(cab)
    print("-" * len(cab))
    for a in med["apps"]:
        for e in a["estagios"]:
            sinais = []
            if (e["skew_tempo"] or 0) >= skew_limite:
                sinais.append("SKEW")
            if e["spill_disco_bytes"] or e["spill_memoria_bytes"]:
                sinais.append("SPILL")
            if e["executor_run_ms"] and e["gc_ms"] / e["executor_run_ms"] >= gc_limite:
                sinais.append("GC")
            if e["falhas"] or e["falha_estagio"]:
                sinais.append("FALHA")
            if (e["parede_ms"] or 0) > (a["totais"]["parede_ms"] or 0):
                sinais.append("RELOGIO")
            print(f"{(a['nome'] or '?')[:18]:<18} {e['estagio']:>4} {e['tarefas']:>5} "
                  f"{e['parede_ms'] if e['parede_ms'] is not None else '-':>8} "
                  f"{e['executor_run_ms']:>9} {_r(e['skew_tempo']):>7} {_r(e['skew_bytes']):>5} "
                  f"{_mb(e['entrada_bytes']):>8} {_mb(e['shuffle_lido']):>8} "
                  f"{_mb(e['shuffle_escrito']):>8} {_mb(e['spill_memoria_bytes']):>8} "
                  f"{_mb(e['spill_disco_bytes']):>8}  {','.join(sinais) or '-':<6}  "
                  f"{e['nome'][:60]}")
    t = med["total"]
    print()
    for a in med["apps"]:
        at = a["totais"]
        print(f"app {a['nome']}  spark={a['versao_spark']}  parede={at['parede_ms']} ms  "
              f"tarefas={at['tarefas']} falhas={at['falhas']}  linhas_log={a['linhas_log']}")
        if not a["relogio_consistente"]:
            print(f"  RELOGIO INCONSISTENTE em {a['nome']}: timestamps de parede retrocedem "
                  f"até {a['relogio_retrocesso_max_ms']} ms. Parede não entra no gate; "
                  "Executor Run Time (nanoTime) continua valendo.")
    print(f"TOTAL  parede={t['parede_ms']} ms  executor={t['executor_run_ms']} ms  "
          f"gc={t['gc_ms']} ms  shuffle R/W={_mb(t['shuffle_lido'])}/{_mb(t['shuffle_escrito'])} MB  "
          f"spill mem/disco={_mb(t['spill_memoria_bytes'])}/{_mb(t['spill_disco_bytes'])} MB")


# --------------------------------------------------------------------------- resultado

def ler_resultado(p: Path, exige_multiconjunto: bool) -> dict:
    """Controles da saída do job. Dinheiro em string; float é recusado (Regra 5)."""
    if not p.exists():
        raise NaoMedido(f"arquivo de resultado não existe: {p}")

    def _sem_float(s: str):
        raise NaoMedido(f"float no resultado ({s}); controles trafegam como string")

    r = json.loads(p.read_text(encoding="utf-8"), parse_float=_sem_float)
    ctl = r.get("controles")
    if not isinstance(ctl, dict) or not ctl:
        raise NaoMedido("resultado sem 'controles'")
    for k, v in ctl.items():
        if v is not None and not isinstance(v, str):
            raise NaoMedido(f"controle '{k}' não é string: {v!r}")
    try:
        if "linhas" not in ctl or Decimal(ctl["linhas"]) <= 0:
            raise NaoMedido("controles com zero linhas (ou sem 'linhas'): nada foi medido")
    except InvalidOperation:
        raise NaoMedido(f"'linhas' ilegível: {ctl.get('linhas')!r}")
    if exige_multiconjunto:
        mc = r.get("multiconjunto")
        if not isinstance(mc, dict) or not {"so_baseline", "so_atual"} <= set(mc):
            raise NaoMedido("resultado sem 'multiconjunto' {so_baseline, so_atual}: "
                            "sem exceptAll contra a saída da baseline não há prova de "
                            "resultado idêntico")
    return r


# --------------------------------------------------------------------------- gate

def _resumo(med: dict) -> dict:
    return {"total": med["total"],
            "relogio_consistente": all(a["relogio_consistente"] for a in med["apps"]),
            "apps": {a["nome"]: {"totais": a["totais"], "versao_spark": a["versao_spark"],
                                 "relogio_consistente": a["relogio_consistente"],
                                 "ambiente": a["ambiente"]} for a in med["apps"]}}


def comparar(med: dict, base: dict, resultado: dict, tol: float) -> tuple[str, list[str]]:
    notas: list[str] = []
    # 1. Resultado idêntico, antes de qualquer número de tempo.
    ctl_b, ctl_a = base["resultado"]["controles"], resultado["controles"]
    diverg = {k: (ctl_b.get(k), ctl_a.get(k)) for k in set(ctl_b) | set(ctl_a)
              if ctl_b.get(k) != ctl_a.get(k)}
    mc = resultado["multiconjunto"]
    if diverg or mc["so_baseline"] != 0 or mc["so_atual"] != 0:
        for k, (b, a) in sorted(diverg.items()):
            notas.append(f"RESULTADO controle {k}: baseline={b} atual={a}")
        notas.append(f"RESULTADO multiconjunto: só baseline={mc['so_baseline']} "
                     f"só atual={mc['so_atual']}")
        notas.append("otimização que muda o resultado é defeito, não ganho")
        return "PIOR", notas
    notas.append("RESULTADO idêntico (controles e multiconjunto)")

    # 2. Mesmo pipeline e mesmo ambiente.
    ab, aa = base["medicao"]["apps"], _resumo(med)["apps"]
    if set(ab) != set(aa):
        raise NaoMedido(f"composição do pipeline mudou: baseline={sorted(ab)} "
                        f"atual={sorted(aa)} — rebaseline deliberado")
    for nome in ab:
        vb, va = ab[nome]["versao_spark"], aa[nome]["versao_spark"]
        if vb != va:
            raise NaoMedido(f"{nome}: Spark {vb} na baseline, {va} agora")
        for k in AMBIENTE_CHAVES:
            if ab[nome]["ambiente"].get(k) != aa[nome]["ambiente"].get(k):
                raise NaoMedido(f"{nome}: ambiente diferente em {k}: "
                                f"{ab[nome]['ambiente'].get(k)} -> {aa[nome]['ambiente'].get(k)}")
        mud = {k for k in set(ab[nome]["ambiente"]) | set(aa[nome]["ambiente"])
               if k.startswith("spark.sql.")
               and ab[nome]["ambiente"].get(k) != aa[nome]["ambiente"].get(k)}
        for k in sorted(mud):
            notas.append(f"{nome}: conf {k}: {ab[nome]['ambiente'].get(k)} -> "
                         f"{aa[nome]['ambiente'].get(k)}")

    # 3. Métricas, no total e por app.
    pior, melhor = False, False
    ra = _resumo(med)
    escopos = [("TOTAL", base["medicao"]["total"], med["total"],
                base["medicao"].get("relogio_consistente", False) and ra["relogio_consistente"])]
    escopos += [(n, ab[n]["totais"], aa[n]["totais"],
                 ab[n].get("relogio_consistente", False) and aa[n]["relogio_consistente"])
                for n in sorted(ab)]
    for escopo, b, a, relogio_ok in escopos:
        if not relogio_ok:
            notas.append(f"{escopo}: parede fora do gate (relógio inconsistente num dos lados)")
        for k, rotulo, piso in METRICAS_GATE:
            if k == "parede_ms" and not relogio_ok:
                continue
            vb, va = b.get(k) or 0, a.get(k) or 0
            delta = va - vb
            rel = (delta / vb) if vb else (0.0 if va == 0 else float("inf"))
            if abs(delta) < piso:
                continue
            if rel > tol:
                pior = True
                notas.append(f"PIOR  {escopo}: {rotulo} {vb} -> {va} ({rel:+.1%})")
            elif rel < -tol:
                melhor = True
                notas.append(f"melhor {escopo}: {rotulo} {vb} -> {va} ({rel:+.1%})")
    if pior:
        return "PIOR", notas
    return ("MELHOR" if melhor else "IGUAL"), notas


# --------------------------------------------------------------------------- CLI

def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("modo", choices=("relatorio", "baseline", "comparar"))
    ap.add_argument("eventlog", type=Path)
    ap.add_argument("--resultado", type=Path, help="JSON com controles (e multiconjunto)")
    ap.add_argument("--gravar", type=Path, help="baseline a gravar")
    ap.add_argument("--baseline", type=Path, help="baseline a comparar")
    ap.add_argument("--substituir", action="store_true", help="sobrescreve baseline existente")
    ap.add_argument("--tolerancia", type=float, default=0.10)
    ap.add_argument("--skew", type=float, default=5.0, help="max/mediana que acende SKEW")
    ap.add_argument("--gc", type=float, default=0.10, help="fração GC/run que acende GC")
    ap.add_argument("--min-tarefas-skew", type=int, default=4)
    ap.add_argument("--json", type=Path, help="grava a medição em JSON")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    token = {"relatorio": "MEDICAO", "baseline": "BASELINE", "comparar": "PERF"}[a.modo]
    try:
        if a.modo == "baseline" and not a.gravar:
            raise NaoMedido("--gravar é obrigatório")
        if a.modo == "comparar" and not a.baseline:
            raise NaoMedido("--baseline é obrigatório")
        if a.modo != "relatorio" and not a.resultado:
            raise NaoMedido("--resultado é obrigatório: sem controles não há prova "
                            "de que o resultado não mudou")
        if a.modo == "baseline" and a.gravar.exists() and not a.substituir:
            print(f"baseline já existe: {a.gravar}. Substituir é decisão deliberada "
                  "(--substituir), nunca para um gate passar.")
            print("BASELINE=RECUSADA")
            return 1
        med = medir(a.eventlog, a.min_tarefas_skew)
        imprimir(med, a.skew, a.gc)
        if a.json:
            a.json.write_text(json.dumps(med, indent=2, default=str, ensure_ascii=False),
                              encoding="utf-8")
        if a.modo == "relatorio":
            print("MEDICAO=OK")
            return 0
        if a.modo == "baseline":
            res = ler_resultado(a.resultado, exige_multiconjunto=False)
            doc = {"formato": 1, "eventlog": str(a.eventlog), "tolerancia_sugerida": a.tolerancia,
                   "resultado": {"controles": res["controles"]}, "medicao": _resumo(med)}
            a.gravar.parent.mkdir(parents=True, exist_ok=True)
            a.gravar.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                                encoding="utf-8")
            print(f"baseline gravada em {a.gravar}")
            print("BASELINE=GRAVADA")
            return 0
        if not a.baseline.exists():
            raise NaoMedido(f"baseline não existe: {a.baseline}")
        base = json.loads(a.baseline.read_text(encoding="utf-8"))
        res = ler_resultado(a.resultado, exige_multiconjunto=True)
        veredito, notas = comparar(med, base, res, a.tolerancia)
        print()
        for n in notas:
            print(f"  {n}")
        print(f"PERF={veredito}")
        return 0 if veredito in ("MELHOR", "IGUAL") else 1
    except NaoMedido as e:
        print(f"NAO_MEDIDO: {e}", file=sys.stderr)
        print(f"{token}=NAO_MEDIDO")
        return 1
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        print(f"ERRO de leitura: {e}", file=sys.stderr)
        print(f"{token}=NAO_MEDIDO")
        return 1


if __name__ == "__main__":
    sys.exit(main())
