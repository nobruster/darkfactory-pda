"""Prova que o medidor acusa. Verificador que nunca reprovou não é verificador.

Rodar:  python -m pytest .claude/skills/spark-perf/ -v

Os eventos sintéticos usam os nomes de campo do JsonProtocol do Spark 3.5,
conferidos contra logs reais do apache/spark:3.5.9.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import medir_eventlog as m  # noqa: E402

T0 = 1_790_000_000_000
CONTROLES = {"linhas": "41572553", "soma": "78521752562.12", "minimo": "0.01",
             "maximo": "99999.99", "nulos": "0"}


def tarefa(stage, run=1000, spill_mem=0, spill_disco=0, sh_r=0, sh_w=0,
           fim=T0 + 5000, motivo="Success"):
    return {"Event": "SparkListenerTaskEnd", "Stage ID": stage, "Stage Attempt ID": 0,
            "Task Type": "ResultTask", "Task End Reason": {"Reason": motivo},
            "Task Info": {"Task ID": 1, "Launch Time": fim - run, "Finish Time": fim},
            "Task Metrics": {
                "Executor Run Time": run, "Executor CPU Time": run * 1_000_000,
                "JVM GC Time": 10, "Memory Bytes Spilled": spill_mem,
                "Disk Bytes Spilled": spill_disco,
                "Shuffle Read Metrics": {"Remote Bytes Read": 0, "Local Bytes Read": sh_r,
                                         "Total Records Read": 0},
                "Shuffle Write Metrics": {"Shuffle Bytes Written": sh_w,
                                          "Shuffle Records Written": 0},
                "Input Metrics": {"Bytes Read": 100, "Records Read": 10},
                "Output Metrics": {"Bytes Written": 0, "Records Written": 0}}}


def app_log(nome="job", tarefas=None, fim=T0 + 20000, conf=None, extra=None):
    conf = {"spark.master": "local[*]", **(conf or {})}
    evs = [{"Event": "SparkListenerLogStart", "Spark Version": "3.5.9"},
           {"Event": "SparkListenerBlockManagerAdded", "Timestamp": T0 + 1100},
           {"Event": "SparkListenerEnvironmentUpdate", "Spark Properties": conf},
           {"Event": "SparkListenerApplicationStart", "App Name": nome,
            "App ID": f"local-{nome}", "Timestamp": T0},
           {"Event": "SparkListenerStageSubmitted", "Stage Info": {"Stage ID": 0}}]
    evs += tarefas if tarefas is not None else [tarefa(0) for _ in range(4)]
    evs += [{"Event": "SparkListenerStageCompleted",
             "Stage Info": {"Stage ID": 0, "Stage Attempt ID": 0, "Stage Name": "count at x.py:1",
                            "Number of Tasks": 4, "Submission Time": T0 + 2000,
                            "Completion Time": T0 + 6000}}]
    evs += extra or []
    if fim is not None:
        evs.append({"Event": "SparkListenerApplicationEnd", "Timestamp": fim})
    return "\n".join(json.dumps(e) for e in evs) + "\n"


def escrever(d: Path, nome: str, texto: str) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    p = d / nome
    p.write_text(texto, encoding="utf-8")
    return p


def resultado(p: Path, controles=None, so_b=0, so_a=0, com_mc=True) -> Path:
    doc = {"controles": controles or CONTROLES}
    if com_mc:
        doc["multiconjunto"] = {"so_baseline": so_b, "so_atual": so_a}
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


def ultima(capsys) -> str:
    return capsys.readouterr().out.strip().splitlines()[-1]


@pytest.fixture
def base(tmp_path):
    ev = tmp_path / "ev-base"
    escrever(ev, "local-1", app_log(tarefas=[tarefa(0, sh_w=100 << 20) for _ in range(4)]))
    b = tmp_path / "baseline.json"
    assert m.main(["baseline", str(ev), "--resultado",
                   str(resultado(tmp_path / "r0.json", com_mc=False)),
                   "--gravar", str(b)]) == 0
    return b


# ------------------------------------------------------------ Regra 9: NAO_MEDIDO

def test_caminho_inexistente(tmp_path, capsys):
    assert m.main(["relatorio", str(tmp_path / "nada")]) == 1
    assert ultima(capsys) == "MEDICAO=NAO_MEDIDO"


def test_diretorio_vazio(tmp_path, capsys):
    (tmp_path / "ev").mkdir()
    assert m.main(["relatorio", str(tmp_path / "ev")]) == 1
    assert ultima(capsys) == "MEDICAO=NAO_MEDIDO"


def test_log_em_andamento(tmp_path, capsys):
    escrever(tmp_path / "ev", "local-1.inprogress", app_log())
    assert m.main(["relatorio", str(tmp_path / "ev")]) == 1
    assert ultima(capsys) == "MEDICAO=NAO_MEDIDO"


def test_log_comprimido(tmp_path, capsys):
    escrever(tmp_path / "ev", "local-1.zstd", "binario")
    assert m.main(["relatorio", str(tmp_path / "ev")]) == 1
    assert ultima(capsys) == "MEDICAO=NAO_MEDIDO"


def test_zero_tarefas_nao_e_igual(tmp_path, base, capsys):
    ev = tmp_path / "ev"
    escrever(ev, "local-1", app_log(tarefas=[]))
    rc = m.main(["comparar", str(ev), "--resultado", str(resultado(tmp_path / "r.json")),
                 "--baseline", str(base)])
    assert rc == 1 and ultima(capsys) == "PERF=NAO_MEDIDO"


def test_linha_corrompida(tmp_path, capsys):
    escrever(tmp_path / "ev", "local-1", app_log() + '{"Event": "SparkListenerTa\n')
    assert m.main(["relatorio", str(tmp_path / "ev")]) == 1
    assert ultima(capsys) == "MEDICAO=NAO_MEDIDO"


def test_sem_application_end(tmp_path, capsys):
    escrever(tmp_path / "ev", "local-1", app_log(fim=None))
    assert m.main(["relatorio", str(tmp_path / "ev")]) == 1
    assert ultima(capsys) == "MEDICAO=NAO_MEDIDO"


def test_rolling_em_andamento(tmp_path, capsys):
    d = tmp_path / "ev" / "eventlog_v2_local-1"
    escrever(d, "events_1_local-1", app_log())
    escrever(d, "appstatus_local-1.inprogress", "")
    assert m.main(["relatorio", str(tmp_path / "ev")]) == 1
    assert ultima(capsys) == "MEDICAO=NAO_MEDIDO"


def test_rolling_completo_mede(tmp_path, capsys):
    d = tmp_path / "ev" / "eventlog_v2_local-1"
    escrever(d, "events_1_local-1", app_log())
    escrever(d, "appstatus_local-1", "")
    assert m.main(["relatorio", str(tmp_path / "ev")]) == 0
    assert ultima(capsys) == "MEDICAO=OK"


# ------------------------------------------------------------ resultado idêntico

def test_sem_resultado_nao_compara(tmp_path, base, capsys):
    escrever(tmp_path / "ev", "local-1", app_log())
    assert m.main(["comparar", str(tmp_path / "ev"), "--baseline", str(base)]) == 1
    assert ultima(capsys) == "PERF=NAO_MEDIDO"


def test_sem_multiconjunto_nao_compara(tmp_path, base, capsys):
    escrever(tmp_path / "ev", "local-1", app_log())
    r = resultado(tmp_path / "r.json", com_mc=False)
    assert m.main(["comparar", str(tmp_path / "ev"), "--resultado", str(r),
                   "--baseline", str(base)]) == 1
    assert ultima(capsys) == "PERF=NAO_MEDIDO"


def test_float_no_resultado_e_recusado(tmp_path, base, capsys):
    escrever(tmp_path / "ev", "local-1", app_log())
    r = tmp_path / "r.json"
    r.write_text('{"controles": {"linhas": "10", "soma": 0.3}, '
                 '"multiconjunto": {"so_baseline": 0, "so_atual": 0}}')
    assert m.main(["comparar", str(tmp_path / "ev"), "--resultado", str(r),
                   "--baseline", str(base)]) == 1
    assert ultima(capsys) == "PERF=NAO_MEDIDO"


def test_centavo_a_menos_e_pior_mesmo_mais_rapido(tmp_path, base, capsys):
    escrever(tmp_path / "ev", "local-1",
             app_log(tarefas=[tarefa(0, run=10) for _ in range(4)], fim=T0 + 8000))
    r = resultado(tmp_path / "r.json", controles={**CONTROLES, "soma": "78521752562.11"})
    assert m.main(["comparar", str(tmp_path / "ev"), "--resultado", str(r),
                   "--baseline", str(base)]) == 1
    assert ultima(capsys) == "PERF=PIOR"


def test_linha_trocada_e_pior(tmp_path, base, capsys):
    escrever(tmp_path / "ev", "local-1", app_log())
    r = resultado(tmp_path / "r.json", so_b=1, so_a=1)
    assert m.main(["comparar", str(tmp_path / "ev"), "--resultado", str(r),
                   "--baseline", str(base)]) == 1
    assert ultima(capsys) == "PERF=PIOR"


def test_baseline_nao_se_sobrescreve(tmp_path, base, capsys):
    rc = m.main(["baseline", str(tmp_path / "ev-base"), "--resultado",
                 str(resultado(tmp_path / "r.json", com_mc=False)), "--gravar", str(base)])
    assert rc == 1 and ultima(capsys) == "BASELINE=RECUSADA"


# ------------------------------------------------------------ métricas

def test_mesma_execucao_e_igual(tmp_path, base, capsys):
    escrever(tmp_path / "ev", "local-1",
             app_log(tarefas=[tarefa(0, sh_w=100 << 20) for _ in range(4)]))
    assert m.main(["comparar", str(tmp_path / "ev"), "--resultado",
                   str(resultado(tmp_path / "r.json")), "--baseline", str(base)]) == 0
    assert ultima(capsys) == "PERF=IGUAL"


def test_spill_novo_e_pior(tmp_path, base, capsys):
    escrever(tmp_path / "ev", "local-1", app_log(
        tarefas=[tarefa(0, sh_w=100 << 20, spill_disco=1 << 20) for _ in range(4)]))
    assert m.main(["comparar", str(tmp_path / "ev"), "--resultado",
                   str(resultado(tmp_path / "r.json")), "--baseline", str(base)]) == 1
    assert ultima(capsys) == "PERF=PIOR"


def test_menos_shuffle_e_melhor(tmp_path, base, capsys):
    escrever(tmp_path / "ev", "local-1",
             app_log(tarefas=[tarefa(0, sh_w=10 << 20) for _ in range(4)]))
    assert m.main(["comparar", str(tmp_path / "ev"), "--resultado",
                   str(resultado(tmp_path / "r.json")), "--baseline", str(base)]) == 0
    assert ultima(capsys) == "PERF=MELHOR"


def test_ganho_num_app_nao_esconde_perda_no_outro(tmp_path, capsys):
    ev_b, ev_a = tmp_path / "b", tmp_path / "a"
    escrever(ev_b, "l-1", app_log("bronze", [tarefa(0, run=10000) for _ in range(4)]))
    escrever(ev_b, "l-2", app_log("silver", [tarefa(0, run=10000) for _ in range(4)]))
    escrever(ev_a, "l-1", app_log("bronze", [tarefa(0, run=1000) for _ in range(4)]))
    escrever(ev_a, "l-2", app_log("silver", [tarefa(0, run=14000) for _ in range(4)]))
    b = tmp_path / "base.json"
    m.main(["baseline", str(ev_b), "--resultado",
            str(resultado(tmp_path / "r0.json", com_mc=False)), "--gravar", str(b)])
    assert m.main(["comparar", str(ev_a), "--resultado", str(resultado(tmp_path / "r.json")),
                   "--baseline", str(b)]) == 1
    assert ultima(capsys) == "PERF=PIOR"


def test_ambiente_diferente_nao_compara(tmp_path, base, capsys):
    escrever(tmp_path / "ev", "local-1", app_log(conf={"spark.master": "local[2]"}))
    assert m.main(["comparar", str(tmp_path / "ev"), "--resultado",
                   str(resultado(tmp_path / "r.json")), "--baseline", str(base)]) == 1
    assert ultima(capsys) == "PERF=NAO_MEDIDO"


def test_pipeline_com_outra_composicao_nao_compara(tmp_path, base, capsys):
    escrever(tmp_path / "ev", "local-1", app_log(nome="outro"))
    assert m.main(["comparar", str(tmp_path / "ev"), "--resultado",
                   str(resultado(tmp_path / "r.json")), "--baseline", str(base)]) == 1
    assert ultima(capsys) == "PERF=NAO_MEDIDO"


# ------------------------------------------------------------ relógio

def test_application_start_nao_e_salto_de_relogio(tmp_path):
    escrever(tmp_path / "ev", "local-1", app_log())
    assert m.medir(tmp_path / "ev")["apps"][0]["relogio_consistente"] is True


def test_salto_de_relogio_tira_a_parede_do_gate(tmp_path, base, capsys):
    # Medido no WSL2: JobEnd seguido de JobStart 34 s "no passado".
    salto = [{"Event": "SparkListenerJobEnd", "Completion Time": T0 + 40000},
             {"Event": "SparkListenerJobStart", "Submission Time": T0 + 6000}]
    escrever(tmp_path / "ev", "local-1", app_log(
        tarefas=[tarefa(0, sh_w=100 << 20) for _ in range(4)], extra=salto, fim=T0 + 90000))
    assert m.medir(tmp_path / "ev")["apps"][0]["relogio_consistente"] is False
    rc = m.main(["comparar", str(tmp_path / "ev"), "--resultado",
                 str(resultado(tmp_path / "r.json")), "--baseline", str(base)])
    saida = capsys.readouterr().out
    assert "parede fora do gate" in saida
    assert rc == 0 and saida.strip().splitlines()[-1] == "PERF=IGUAL"


def test_skew_acende_no_relatorio(tmp_path, capsys):
    ts = [tarefa(0, run=1000) for _ in range(7)] + [tarefa(0, run=20000)]
    escrever(tmp_path / "ev", "local-1", app_log(tarefas=ts))
    assert m.main(["relatorio", str(tmp_path / "ev")]) == 0
    assert "SKEW" in capsys.readouterr().out
