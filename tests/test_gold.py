"""Testes da Gold — agrega por código, reconcilia com a âncora e publica em Delta.

Rodam DENTRO do contêiner pda-spark. Gold consome a saída REAL de Silver
(`silver.executar_classificacao` sobre a saída real de Bronze sobre um lago de teste), nunca uma
fixture escrita à mão. Nada grava no destino real: os destinos Delta vivem sob `tmp_path`.
"""

from __future__ import annotations

import csv
import dataclasses
import decimal
import hashlib
import json
import os
import sys
import time
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pyspark.sql import functions as F  # noqa: E402
from pyspark.sql.types import (  # noqa: E402
    DecimalType,
    DoubleType,
    StringType,
    StructField,
    StructType,
)

import test_silver as ts  # noqa: E402
from medalhao import bronze, gold, silver  # noqa: E402
from pda import envelope as envelope_mod  # noqa: E402
from pda import evidencia, juizo, orquestracao  # noqa: E402
from pda.contrato import carregar_contrato  # noqa: E402

RAIZ_REPO = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "competencia-min.csv"
COMP = "2026-03"

MAPA_ESPERADO = {
    "01": Decimal("1621.00"),
    "03": Decimal("100.00"),
    "23": Decimal("50.00"),
    "59": Decimal("25.00"),
    "04": Decimal("200.00"),
    "83": Decimal("10.00"),
    "02": Decimal("5.00"),
}

ESQUEMA_GOLD = StructType(
    [
        StructField("especie_codigo", StringType()),
        StructField("especie_descricao", StringType()),
        StructField("vl_liquido_total", DecimalType(14, 2)),
        StructField("competencia", StringType()),
    ]
)


# ---------------------------------------------------------------- apoio


@pytest.fixture(scope="session")
def spark():
    sessao = bronze.criar_sessao("teste-gold")
    sessao.conf.set("spark.sql.shuffle.partitions", "4")
    yield sessao
    sessao.stop()


def _politica():
    return ts._politica()


def _linhas_do_csv():
    linhas = []
    with open(FIXTURE, encoding="utf-8", newline="") as arquivo:
        leitor = csv.reader(arquivo, delimiter=";")
        next(leitor)
        for linha in leitor:
            valor = Decimal(linha[9].strip().replace(".", "").replace(",", "."))
            linhas.append((linha[12].strip(), linha[13].strip(), valor))
    return linhas


def _cenario(spark, tmp_path, comp=COMP, *, com_mapa=True, sem_ancora=False, sum_ancora="2011.00"):
    """Lago Parquet + CSV protegido + contrato YAML, todos derivados do MESMO CSV mínimo."""
    base = Path(tmp_path) / f"c-{comp}"
    base.mkdir(parents=True, exist_ok=True)
    caminho_csv = base / "competencia.csv"
    caminho_csv.write_bytes(FIXTURE.read_bytes())
    os.chmod(caminho_csv, 0o444)
    hash_csv = hashlib.sha256(caminho_csv.read_bytes()).hexdigest()

    raiz = base / "lago"
    spark.createDataFrame(_linhas_do_csv(), ts.ESQUEMA).coalesce(1).write.mode("overwrite").parquet(
        str(raiz / f"competencia={comp}")
    )
    dados = {
        "competencia": comp,
        "procedencia": {
            "fonte": "fixture-teste", "publicado_em": comp,
            "hash_zip_sha256": "a" * 64, "hash_csv_sha256": hash_csv,
        },
        "layout": {
            "total_colunas": 14, "separador": ";", "encoding": "utf-8",
            "posicoes": {"vl_liquido": 9, "especie": 12, "descricao_especie": 13},
        },
        "ancora": {
            "count_linhas": 7, "sum_vl_liquido": sum_ancora, "min_vl_liquido": "5.00",
            "max_vl_liquido": "1621.00", "linhas_invalidas": 0,
            "aprovado_por": "teste", "aprovado_em": "2026-09-23",
        },
        "cardinalidade": {
            "codigos_distintos": 7, "descricoes_distintas": 3, "colapsos": 2, "codigos_colapsados": 6,
        },
        "defeitos_conhecidos": [
            {
                "tipo": silver.TIPO_COLAPSO, "descricao": "identidade colapsada na origem",
                "quantidade": 2, "aprovador": "teste", "aprovado_em": "2026-09-23",
            }
        ],
        "politica_decimal": {
            "modo": "HALF_EVEN", "granularidade": "total", "escala": 2,
            "escala_maxima_intermediarios": 3, "precisao": 14, "nao_negativo": True,
            "emax": 999999, "emin": -999999,
        },
        "particionamento": {
            "chave": "competencia", "caminho": str(raiz), "formato": "parquet",
            "valores_medidos": [comp], "objetos_auxiliares_ignorados": ["_SUCCESS"],
        },
    }
    if com_mapa:
        dados["mapa_colapsos"] = {
            "aprovado_por": "teste", "aprovado_em": "2026-09-23",
            "grupos": [
                {"descricao": "Pensão por Morte de", "codigos": ["01", "03", "23", "59"]},
                {"descricao": "Aposentadoria por In", "codigos": ["04", "83"]},
            ],
        }
    if sem_ancora:
        del dados["ancora"]
    caminho_contrato = base / "contrato.yaml"
    caminho_contrato.write_text(yaml.safe_dump(dados, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return SimpleNamespace(comp=comp, contrato=caminho_contrato, csv=caminho_csv, raiz=raiz, hash=hash_csv)


def _procedencia(cen):
    return {"hash_csv_sha256": cen.hash}


def _ate_silver(spark, cen, procedencia=True):
    contrato = carregar_contrato(cen.contrato)
    b = bronze.executar_leitura(
        spark, contrato, raiz=str(cen.raiz), gravar=False, procedencia=_procedencia(cen) if procedencia else None
    )
    assert b.estado == bronze.INTEGRO, (b.estado, b.motivo, b.diferencas)
    s = silver.executar_classificacao(spark, contrato, b, gravar=False)
    assert s.estado == silver.INTEGRO, (s.estado, s.motivo, s.diferencas)
    return contrato, s


def _rodar(spark, tmp_path, cen, *, procedencia=True, id_execucao="e1", **kw):
    return gold.executar_gold(
        spark,
        diretorio_evidencia=Path(tmp_path) / "evidencia",
        competencia_solicitada=cen.comp,
        caminho_contrato=cen.contrato,
        caminho_csv=cen.csv,
        raiz=str(cen.raiz),
        procedencia=_procedencia(cen) if procedencia else None,
        destino=str(Path(tmp_path) / "dest"),
        preparo_raiz=str(Path(tmp_path) / "prep"),
        id_execucao=id_execucao,
        **kw,
    )


def _pacote(desfecho):
    return evidencia.ler_pacote(desfecho.caminho_pacote)


def _diagnostico(desfecho):
    return json.loads(_pacote(desfecho)["evento_falha"]["mensagem"])


def _nomes(r):
    return {d["identidade"] for d in r.diferencas}


def _desfecho_autorizado(tmp_path, autorizado=True, existe=True):
    caminho = Path(tmp_path) / "pacote.json"
    caminho.write_text('{"pacote": true}', encoding="utf-8")
    return orquestracao.Desfecho(
        veredito="ACEITO", causa="JULGADO", codigo_saida=0,
        caminho_pacote=caminho if existe else None, duracao_segundos=0.1, autorizado_publicar=autorizado,
    )


def _gold_de(spark, tmp_path, comp=COMP):
    cen = _cenario(spark, tmp_path, comp)
    contrato, s = _ate_silver(spark, cen)
    g = gold.agregar(spark, contrato, s)
    assert g.estado == gold.INTEGRO, (g.estado, g.motivo, g.diferencas)
    return contrato, s, g


def _df_gold(spark, linhas, comp=COMP):
    return spark.createDataFrame([(c, d, Decimal(v), comp) for c, d, v in linhas], ESQUEMA_GOLD)


# ---------------------------------------------------------------- eval_1


def test_arredonda_uma_vez():
    pol = _politica()
    # 2,345 + 2,345: por campo 2,34 + 2,34 = 4,68; no total 4,690 -> 4,69
    assert gold.total_arredondado(["2.345", "2.345"], pol) == Decimal("4.69")
    assert gold._soma_exata(["2.345", "2.345"], pol) == Decimal("4.690")
    with pytest.raises(TypeError):
        gold.total_arredondado([0.1, 0.2], pol)


def test_half_even_do_contrato():
    pol = _politica()
    assert pol.modo == "HALF_EVEN"
    assert gold.contexto_declarado(pol).rounding == decimal.ROUND_HALF_EVEN
    assert gold.total_arredondado(["0.125"], pol) == Decimal("0.12")  # meio-para-cima daria 0.13
    assert gold.total_arredondado(["0.135"], pol) == Decimal("0.14")
    assert "ROUND_HALF_UP" not in (RAIZ_REPO / "src" / "medalhao" / "gold.py").read_text(encoding="utf-8")


def test_nao_arredonda_por_campo():
    pol = _politica()
    por_campo = sum(
        (Decimal(v).quantize(Decimal("0.01"), rounding=decimal.ROUND_HALF_EVEN) for v in ("2.345", "2.345")),
        Decimal("0"),
    )
    assert por_campo == Decimal("4.68")
    assert gold.total_arredondado(["2.345", "2.345"], pol) == Decimal("4.69") != por_campo


def test_traps_declaradas():
    pol = _politica()
    padrao, ctx = decimal.DefaultContext, decimal.getcontext()
    antigos = (padrao.traps[decimal.Inexact], ctx.traps[decimal.Inexact], padrao.Emax, ctx.Emax)
    try:
        padrao.traps[decimal.Inexact] = True
        ctx.traps[decimal.Inexact] = True
        with pytest.raises(decimal.Inexact):
            with decimal.localcontext():
                Decimal("2.345").quantize(Decimal(".01"))
        assert gold.total_arredondado(["2.345"], pol) == Decimal("2.34")

        padrao.Emax = ctx.Emax = 5  # a âncora viraria Infinity num contexto herdado
        assert gold.total_arredondado(["78521752562.12"], pol) == Decimal("78521752562.12")
    finally:
        padrao.traps[decimal.Inexact], ctx.traps[decimal.Inexact] = antigos[0], antigos[1]
        padrao.Emax, ctx.Emax = antigos[2], antigos[3]


def test_recusa_sob_procedencia_nao_vinculada(spark, tmp_path):
    cen = _cenario(spark, tmp_path)
    desfecho, g = _rodar(spark, tmp_path, cen, procedencia=False)
    assert desfecho.autorizado_publicar is False
    assert desfecho.veredito == evidencia.ERRO
    assert not (tmp_path / "dest").exists()  # nada publicado
    assert gold.PROCEDENCIA_NAO_VINCULADA in g.marcas  # a marca atravessa Bronze -> Silver -> Gold
    assert _diagnostico(desfecho)["motivo"] == gold.PROCEDENCIA_NAO_VINCULADA


def test_ansi_declarado_estouro_nao_vira_nulo(spark, tmp_path):
    cen = _cenario(spark, tmp_path)
    contrato, s = _ate_silver(spark, cen)
    spark.conf.set("spark.sql.ansi.enabled", "false")
    try:
        gold.agregar(spark, contrato, s)
        assert spark.conf.get("spark.sql.ansi.enabled") == "true"
    finally:
        spark.conf.set("spark.sql.ansi.enabled", "true")
    with pytest.raises(Exception):
        spark.sql("SELECT CAST(CAST('99999999999999.99' AS DECIMAL(16,2)) AS DECIMAL(14,2)) AS v").collect()


def test_cobertura_anexada_ao_pacote(spark, tmp_path, monkeypatch):
    cen = _cenario(spark, tmp_path)
    desfecho, g = _rodar(spark, tmp_path, cen)
    assert desfecho.autorizado_publicar and g.estado == gold.INTEGRO
    anexo = json.loads(Path(str(desfecho.caminho_pacote) + ".cobertura.json").read_text(encoding="utf-8"))
    assert anexo["sha256_pacote"] == hashlib.sha256(desfecho.caminho_pacote.read_bytes()).hexdigest()
    assert anexo["verificados_pelo_mapa"] == ["01", "03", "04", "23", "59", "83"]
    assert anexo["so_por_cardinalidade"] == ["02"]
    assert gold.anexo_confere(desfecho.caminho_pacote, g)

    desfecho.caminho_pacote.write_text(desfecho.caminho_pacote.read_text(encoding="utf-8") + " ", encoding="utf-8")
    assert not gold.anexo_confere(desfecho.caminho_pacote, g)  # o anexo é do pacote, não de outro

    # sem o anexo gravado, nada é publicado
    contrato = carregar_contrato(cen.contrato)
    monkeypatch.setattr(gold, "gravar_anexo", lambda *a, **k: None)
    outro = tmp_path / "outro"
    outro.mkdir()
    novo = _desfecho_autorizado(outro)
    r = gold.publicar(spark, contrato, g, novo, destino=str(outro / "dest"))
    assert r.gravacao == g.gravacao and not (outro / "dest").exists()


def test_publica_em_um_unico_commit(spark, tmp_path):
    cen = _cenario(spark, tmp_path)
    dest = str(tmp_path / "dest")
    desfecho, g = _rodar(spark, tmp_path, cen)
    assert desfecho.autorizado_publicar and g.gravacao["destino"] == dest
    historico = gold._delta_table(spark, dest).history().select("version", "operation", "userMetadata").collect()
    escritas = [h for h in historico if h["operation"] == "WRITE"]
    assert len(escritas) == 1  # a publicação é UM commit
    assert json.loads(escritas[0]["userMetadata"])["competencia"] == COMP
    assert spark.read.format("delta").option("versionAsOf", escritas[0]["version"]).load(dest).count() == 7


def test_interrompida_antes_do_commit_nao_publica(spark, tmp_path, monkeypatch):
    cen = _cenario(spark, tmp_path)
    dest = str(tmp_path / "dest")
    _rodar(spark, tmp_path, cen)
    versao = gold._versao_atual(spark, dest)
    antes = sorted(map(tuple, spark.read.format("delta").load(dest).collect()))

    def cai(*a, **k):
        raise RuntimeError("interrompida antes do commit")

    monkeypatch.setattr(gold, "publicar_competencia", cai)
    with pytest.raises(RuntimeError):
        _rodar(spark, tmp_path, cen, id_execucao="e2")
    assert gold._versao_atual(spark, dest) == versao  # o destino ficou como estava
    assert sorted(map(tuple, spark.read.format("delta").load(dest).collect())) == antes


def test_reconfere_multiconjunto_das_linhas(spark, tmp_path):
    pol = _politica()
    esperado = _df_gold(spark, [("01", "A", v) for v in ("10.00", "20.00", "30.00", "40.00")])
    lido = _df_gold(spark, [("01", "A", v) for v in ("10.00", "21.00", "29.00", "40.00")])
    caminho = str(tmp_path / "tab")
    gold._garantir_tabela(spark, caminho, pol)
    gold.publicar_competencia(spark, lido, caminho, COMP, {"competencia": COMP})
    ok, detalhe = gold._conferir_tabela(
        spark, caminho, gold._versao_atual(spark, caminho), esperado, {"sum_vl_liquido": Decimal("100.00")}, COMP, pol
    )
    assert detalhe["controles_divergentes"] == ()  # 10/20 por 11/19 preserva a soma
    assert detalhe["so_no_esperado"] == 2 and detalhe["so_no_lido"] == 2
    assert ok is False


def test_commit_carrega_a_forma(spark, tmp_path):
    cen = _cenario(spark, tmp_path)
    desfecho, g = _rodar(spark, tmp_path, cen)
    campos = {f.name for f in dataclasses.fields(g)}
    assert {
        "estado", "competencia", "controles", "total_por_codigo", "marcas",
        "hash_procedencia", "linhas", "defeitos", "cobertura", "reconciliacao",
    } <= campos
    assert tuple(g.linhas.columns) == gold.GOLD_COLUNAS == (
        "especie_codigo", "especie_descricao", "vl_liquido_total", "competencia",
    )
    _, dono, _ = gold.ler_competencia_publicada(spark, str(tmp_path / "dest"), COMP)
    assert set(dono) >= {
        "estado", "competencia", "hash_procedencia", "controles", "marcas", "defeitos",
        "total_por_codigo", "cobertura_referencial", "id_execucao", "versao_camada_anterior",
    }
    assert dono["total_por_codigo"]["01"] == "1621.00"
    assert dono["controles"]["sum_vl_liquido"] == "2011.00"
    assert dono["cobertura_referencial"]["so_por_cardinalidade"] == ["02"]


def _publicar_duas(spark, tmp_path):
    dest = str(tmp_path / "dest")
    for comp, exec_id in (("2026-01", "e1"), ("2026-02", "e2")):
        contrato, s, g = _gold_de(spark, tmp_path, comp)
        gold.publicar(spark, contrato, g, _desfecho_autorizado(tmp_path), destino=dest, id_execucao=exec_id)
    return dest


def test_resolve_versao_uma_vez(spark, tmp_path):
    dest = _publicar_duas(spark, tmp_path)
    dados, _, versao = gold.ler_competencia_publicada(spark, dest, "2026-01")
    assert versao == max(v for v, _ in gold._historico(spark, dest))
    assert dados.count() == 7
    assert {x[0] for x in dados.select("competencia").distinct().collect()} == {"2026-01"}


def test_schema_evolucao_so_aditiva():
    atual = StructType(ESQUEMA_GOLD.fields)
    with pytest.raises(gold.EvolucaoRecusada):
        gold.verificar_evolucao(atual, StructType([StructField("vl_liquido_total", DoubleType())]))
    with pytest.raises(gold.EvolucaoRecusada):
        gold.verificar_evolucao(atual, StructType([StructField("vl_liquido_total", DecimalType(14, 3))]))
    assert gold.verificar_evolucao(atual, StructType(atual.fields + [StructField("nova", StringType())])) == ("nova",)
    fonte = (RAIZ_REPO / "src" / "medalhao" / "gold.py").read_text(encoding="utf-8")
    assert 'option("overwriteSchema"' not in fonte


def test_check_nao_negativo(spark, tmp_path):
    caminho = str(tmp_path / "tab")
    gold._garantir_tabela(spark, caminho, _politica())
    negativo = spark.createDataFrame([("01", "A", Decimal("-1.00"), COMP)], ESQUEMA_GOLD)
    with pytest.raises(Exception):
        negativo.write.format("delta").mode("append").save(caminho)
    sem_chave = spark.createDataFrame([(None, "A", Decimal("1.00"), COMP)], ESQUEMA_GOLD)
    with pytest.raises(Exception):
        sem_chave.write.format("delta").mode("append").save(caminho)


def test_reconfere_no_preparo_antes_de_publicar(spark, tmp_path, monkeypatch):
    original = gold._gravar_preparo

    def adulterado(spark_, linhas, preparo, competencia, metadados):
        mexido = linhas.withColumn(
            "vl_liquido_total", (F.col("vl_liquido_total") + F.lit(Decimal("0.01"))).cast(DecimalType(14, 2))
        )
        original(spark_, mexido, preparo, competencia, metadados)

    monkeypatch.setattr(gold, "_gravar_preparo", adulterado)
    cen = _cenario(spark, tmp_path)
    contrato, s = _ate_silver(spark, cen)
    g = gold.agregar(spark, contrato, s, preparo_raiz=str(tmp_path / "prep"), id_execucao="e1")
    assert g.estado == gold.DIVERGE
    assert "reconferencia_no_preparo" in _nomes(g)
    assert not (tmp_path / "dest").exists()  # nada foi publicado


def test_reverte_so_a_competencia(spark, tmp_path, monkeypatch):
    dest = str(tmp_path / "dest")
    c1, _, g1 = _gold_de(spark, tmp_path, "2026-01")
    gold.publicar(spark, c1, g1, _desfecho_autorizado(tmp_path), destino=dest, id_execucao="e1")
    c2, _, g2 = _gold_de(spark, tmp_path, "2026-02")
    original = gold._conferir_tabela

    def reprova_a_publicada(spark_, caminho, *args, **kw):
        if caminho == dest:
            return False, {"so_no_esperado": 1, "so_no_lido": 0, "controles_divergentes": ()}
        return original(spark_, caminho, *args, **kw)

    monkeypatch.setattr(gold, "_conferir_tabela", reprova_a_publicada)
    r = gold.publicar(spark, c2, g2, _desfecho_autorizado(tmp_path), destino=dest, id_execucao="e3")
    assert r.estado == gold.DIVERGE and "reconferencia_publicada" in _nomes(r)
    tabela = spark.read.format("delta").load(dest)
    assert tabela.where("competencia = '2026-02'").count() == 0  # revertida
    assert tabela.where("competencia = '2026-01'").count() == 7  # intacta
    operacoes = [x[0] for x in gold._delta_table(spark, dest).history().select("operation").collect()]
    assert "RESTORE" not in operacoes


def test_metadados_do_commit_dono_da_competencia(spark, tmp_path):
    dest = _publicar_duas(spark, tmp_path)
    _, dono, versao = gold.ler_competencia_publicada(spark, dest, "2026-01")
    historico = dict(gold._historico(spark, dest))
    assert json.loads(historico[versao])["competencia"] == "2026-02"  # o commit V é de OUTRA
    assert dono["competencia"] == "2026-01"
    assert dono["id_execucao"] == "e1"


# ---------------------------------------------------------------- eval_2


def test_reconcilia_recalculando(spark, tmp_path):
    cen = _cenario(spark, tmp_path)
    contrato, s = _ate_silver(spark, cen)
    # a camada anterior AFIRMA o total e o mapa corretos, mas as linhas perderam o código 02
    sem_02 = dataclasses.replace(s, linhas=s.linhas.where(F.col("especie_codigo") != "02"))
    g = gold.agregar(spark, contrato, sem_02)
    assert g.estado == gold.DIVERGE and g.linhas is None
    assert "soma_das_linhas" in _nomes(g)  # recalculado, não herdado de Bronze/Silver


def test_mapa_por_codigo(spark, tmp_path):
    cen = _cenario(spark, tmp_path)
    contrato, s, g = _gold_de(spark, tmp_path)
    assert g.total_por_codigo == MAPA_ESPERADO == s.total_por_codigo
    assert all(isinstance(v, Decimal) for v in g.total_por_codigo.values())
    assert g.reconciliacao == gold.INTEGRO
    assert g.controles["sum_vl_liquido"] == Decimal("2011.00") == contrato.ancora.sum_vl_liquido


def test_redistribuicao_compensada(spark, tmp_path):
    cen = _cenario(spark, tmp_path)
    contrato, s = _ate_silver(spark, cen)
    # mesma soma e mesmas chaves: o mapa da camada anterior desloca 1.00 do código 01 para o 03
    deslocado = dict(s.total_por_codigo)
    deslocado["01"] -= Decimal("1.00")
    deslocado["03"] += Decimal("1.00")
    assert sum(deslocado.values()) == sum(s.total_por_codigo.values()) and set(deslocado) == set(s.total_por_codigo)
    g = gold.agregar(spark, contrato, dataclasses.replace(s, total_por_codigo=deslocado))
    assert g.estado == gold.DIVERGE
    assert {"total_por_codigo:01", "total_por_codigo:03"} <= _nomes(g)

    # e o inverso: as LINHAS deslocam o valor, o mapa anterior é o honesto
    movido = s.linhas.withColumn(
        "vl_liquido",
        F.when(F.col("especie_codigo") == "01", F.col("vl_liquido") - F.lit(Decimal("1.00")))
        .when(F.col("especie_codigo") == "03", F.col("vl_liquido") + F.lit(Decimal("1.00")))
        .otherwise(F.col("vl_liquido"))
        .cast(DecimalType(14, 2)),
    )
    g2 = gold.agregar(spark, contrato, dataclasses.replace(s, linhas=movido))
    assert g2.estado == gold.DIVERGE
    assert "soma_das_linhas" not in _nomes(g2)  # a soma bate: só o mapa acusa
    assert {"total_por_codigo:01", "total_por_codigo:03"} <= _nomes(g2)


def test_contagem_de_codigos(spark, tmp_path):
    cen = _cenario(spark, tmp_path)
    contrato, s = _ate_silver(spark, cen)
    card = dataclasses.replace(contrato.cardinalidade, codigos_distintos=8)
    g = gold.agregar(spark, dataclasses.replace(contrato, cardinalidade=card), s)
    assert g.estado == gold.DIVERGE
    assert "codigos_distintos" in _nomes(g)
    ok = gold.agregar(spark, contrato, s)
    assert ok.linhas.count() == contrato.cardinalidade.codigos_distintos


def test_competencia_bate_com_o_contrato(spark, tmp_path):
    cen = _cenario(spark, tmp_path)
    contrato, s = _ate_silver(spark, cen)
    outra = dataclasses.replace(s, competencia="2026-04")  # mesmos valores por código
    g = gold.agregar(spark, contrato, outra)
    assert g.estado == gold.DIVERGE and "competencia_silver" in _nomes(g)

    linhas_outra = s.linhas.withColumn("competencia", F.lit("2026-04"))
    g2 = gold.agregar(spark, contrato, dataclasses.replace(s, linhas=linhas_outra))
    assert g2.estado == gold.DIVERGE and "linhas_de_outra_competencia" in _nomes(g2)


def test_uma_linha_por_codigo(spark, tmp_path):
    contrato, s, g = _gold_de(spark, tmp_path)
    assert g.linhas.count() == g.linhas.select("especie_codigo").distinct().count() == 7
    # ('01', 30.00) e ('01', 10.00) + ('01', 20.00) dão o MESMO mapa: só o grão acusa
    linhas = [(c, d, str(v)) for c, d, v in [
        ("01", "PENSAO", Decimal("1601.00")), ("01", "PENSAO", Decimal("20.00")),
        ("03", "PENSAO", Decimal("100.00")), ("23", "PENSAO", Decimal("50.00")),
        ("59", "PENSAO", Decimal("25.00")), ("04", "APOS", Decimal("200.00")),
        ("83", "APOS", Decimal("10.00")), ("02", "AUX", Decimal("5.00")),
    ]]
    dif, mapa, _ = gold._reconciliar(_df_gold(spark, linhas), contrato, s, COMP)
    assert mapa["01"] == Decimal("1621.00")
    assert "codigo_duplicado:01" in {d["identidade"] for d in dif}


@pytest.mark.parametrize("estado", [silver.BLOQUEADO, silver.DIVERGE, silver.NAO_MEDIDO, silver.ERRO_LEITURA])
def test_recusa_silver_nao_integro(spark, estado):
    entrada = silver.SilverClassificado(estado=estado, competencia=ts.COMP, motivo=f"SILVER_{estado}")
    g = gold.agregar(spark, ts._contrato(), entrada)
    assert g.estado == estado  # propagado, sem tradução
    assert g.linhas is None and g.motivo == f"SILVER_{estado}"


def test_consome_saida_real_de_silver(spark, tmp_path):
    cen = _cenario(spark, tmp_path)
    contrato = carregar_contrato(cen.contrato)
    b = bronze.executar_leitura(spark, contrato, raiz=str(cen.raiz), gravar=False, procedencia=_procedencia(cen))
    dest_silver = str(tmp_path / "silver")
    s = silver.executar_classificacao(
        spark, contrato, b, gravar=True, destino=dest_silver, preparo_raiz=str(tmp_path / "sprep"), id_execucao="s1"
    )
    assert isinstance(s, silver.SilverClassificado) and tuple(s.linhas.columns) == silver.SILVER_COLUNAS
    direto = gold.agregar(spark, contrato, s)
    lido = gold.agregar(spark, contrato, silver_destino=dest_silver)
    assert direto.estado == lido.estado == gold.INTEGRO
    assert lido.versao_silver == gold._versao_atual(spark, dest_silver)
    assert lido.total_por_codigo == direto.total_por_codigo == MAPA_ESPERADO
    assert "from medalhao import bronze, silver" in (RAIZ_REPO / "src" / "medalhao" / "gold.py").read_text("utf-8")


def test_publica_so_com_autorizado_publicar(spark, tmp_path):
    contrato, _, g = _gold_de(spark, tmp_path)
    dest = tmp_path / "dest"
    r = gold.publicar(spark, contrato, g, _desfecho_autorizado(tmp_path, autorizado=False), destino=str(dest))
    assert not dest.exists() and r.gravacao == g.gravacao
    gold.publicar(spark, contrato, g, _desfecho_autorizado(tmp_path, autorizado=True), destino=str(dest))
    assert spark.read.format("delta").load(str(dest)).count() == 7


def test_descricao_publicada_bate_com_a_original(spark, tmp_path):
    contrato, s, g = _gold_de(spark, tmp_path)
    linhas = {r[0]: r for r in g.linhas.collect()}
    trocadas = [
        ("02", linhas["04"]["especie_descricao"], linhas["02"]["vl_liquido_total"]),
        ("04", linhas["02"]["especie_descricao"], linhas["04"]["vl_liquido_total"]),
    ] + [(c, r["especie_descricao"], r["vl_liquido_total"]) for c, r in linhas.items() if c not in ("02", "04")]
    dif, mapa, soma = gold._reconciliar(_df_gold(spark, trocadas), contrato, s, COMP)
    assert soma == contrato.ancora.sum_vl_liquido and mapa == s.total_por_codigo  # tudo o mais passa
    assert {d["identidade"] for d in dif} == {"descricao_publicada:02", "descricao_publicada:04"}


def test_publica_so_com_pacote_em_disco(spark, tmp_path):
    contrato, _, g = _gold_de(spark, tmp_path)
    dest = tmp_path / "dest"
    gold.publicar(spark, contrato, g, _desfecho_autorizado(tmp_path, existe=False), destino=str(dest))
    assert not dest.exists()
    inexistente = orquestracao.Desfecho("ACEITO", "JULGADO", 0, tmp_path / "nao-existe.json", 0.1, True)
    gold.publicar(spark, contrato, g, inexistente, destino=str(dest))
    assert not dest.exists()


def test_envelope_so_defeitos_de_linha(spark, tmp_path):
    r, _ = ts._classificar(spark, tmp_path)  # 5 linhas de detalhe, 4 códigos
    contrato = ts._contrato()
    g = gold.agregar(spark, contrato, r)
    assert g.estado == gold.INTEGRO, (g.motivo, g.diferencas)
    env = gold.montar_envelope(g)
    assert set(env) == set(envelope_mod.ENVELOPE_SCHEMA["properties"])
    assert env["defeitos"] == []  # defeitos de LINHA: vazio no único caminho que emite envelope
    # controles de DETALHE recebidos de Bronze, nunca recalculados sobre as linhas agregadas
    assert env["controles"]["count_linhas"] == 5 and g.linhas.count() == 4
    assert env["controles"]["sum_vl_liquido"] == "65.00"
    assert env["sha256_arquivo_lido"] == g.hash_procedencia


def test_envelope_validado_antes_dos_insumos(spark, tmp_path, monkeypatch):
    eventos = []
    validar, julgar = envelope_mod.validar_envelope, juizo.julgar
    monkeypatch.setattr(
        envelope_mod, "validar_envelope", lambda *a, **k: (eventos.append("validar"), validar(*a, **k))[1]
    )
    monkeypatch.setattr(juizo, "julgar", lambda *a, **k: (eventos.append("julgar"), julgar(*a, **k))[1])
    cen = _cenario(spark, tmp_path)
    desfecho, _ = _rodar(spark, tmp_path, cen)
    assert desfecho.autorizado_publicar and eventos == ["validar", "julgar"]

    eventos.clear()
    montar = gold.montar_envelope
    monkeypatch.setattr(gold, "montar_envelope", lambda g: {**montar(g), "sha256_arquivo_lido": "0" * 64})
    cen2 = _cenario(spark, tmp_path, "2026-05")
    desfecho2, _ = _rodar(spark, tmp_path / "x", cen2)
    assert desfecho2.veredito == evidencia.ERRO and desfecho2.autorizado_publicar is False
    assert "julgar" not in eventos  # a recusa do envelope vem ANTES dos insumos
    assert _diagnostico(desfecho2)["camada"] == "envelope"


def test_envelope_positivo_sem_defeitos_de_linha(spark, tmp_path):
    cen = _cenario(spark, tmp_path)
    desfecho, g = _rodar(spark, tmp_path, cen)
    pacote = _pacote(desfecho)
    assert desfecho.veredito == evidencia.ACEITO and desfecho.autorizado_publicar
    assert pacote["defeitos_envelope"] == [] == pacote["defeitos_leitura"]
    assert pacote["agregado_controles"]["linhas_invalidas"] == 0
    assert pacote["hash_ancorado"] == pacote["hash_observado"] == pacote["hash_declarado"] == cen.hash


# ---------------------------------------------------------------- eval_3


def test_diverge_nao_publica(spark, tmp_path):
    cen = _cenario(spark, tmp_path)
    contrato, s = _ate_silver(spark, cen)
    torto = dataclasses.replace(contrato, ancora=dataclasses.replace(contrato.ancora, sum_vl_liquido=Decimal("2011.01")))
    g = gold.agregar(spark, torto, s)
    assert g.estado == gold.DIVERGE and "soma_das_linhas" in _nomes(g)
    dest = tmp_path / "dest"
    gold.publicar(spark, torto, g, _desfecho_autorizado(tmp_path), destino=str(dest))
    assert not dest.exists()

    # na cadeia: âncora torta -> Bronze DIVERGE -> ERRO, sem autorização e sem publicar
    cen2 = _cenario(spark, tmp_path / "y", "2026-06", sum_ancora="2011.01")
    desfecho, _ = _rodar(spark, tmp_path / "y", cen2)
    assert desfecho.autorizado_publicar is False and not (tmp_path / "y" / "dest").exists()


def test_sem_ancora_gold_nao_invocado(spark, tmp_path):
    cen = _cenario(spark, tmp_path, sem_ancora=True)

    def nunca(contrato):
        raise AssertionError("Gold não pode ser invocado sem âncora")

    desfecho = orquestracao.conduzir(
        diretorio_evidencia=tmp_path / "evidencia", competencia_solicitada=COMP,
        caminho_contrato=cen.contrato, executar_leitura=nunca,
    )
    assert desfecho.veredito == evidencia.ACEITO_SEM_ANCORA and desfecho.autorizado_publicar is False
    assert _pacote(desfecho)["contrato_status"] == evidencia.CONTRATO_NAO_MEDIDO
    # NAO_MEDIDO e DIVERGE são estados distintos
    entrada = silver.SilverClassificado(estado=silver.NAO_MEDIDO, competencia=ts.COMP, motivo="MAPA_NAO_DECLARADO")
    g = gold.agregar(spark, ts._contrato(), entrada)
    assert g.estado == gold.NAO_MEDIDO != gold.DIVERGE


def test_destino_inalterado_durante(spark, tmp_path, monkeypatch):
    cen = _cenario(spark, tmp_path)
    dest = str(tmp_path / "dest")
    _rodar(spark, tmp_path, cen)
    versao = gold._versao_atual(spark, dest)
    antes = sorted(map(tuple, spark.read.format("delta").load(dest).collect()))
    vistos = []
    original = gold._reconciliar

    def espia(*a, **k):
        vistos.append(
            (gold._versao_atual(spark, dest), sorted(map(tuple, spark.read.format("delta").load(dest).collect())))
        )
        return original(*a, **k)

    monkeypatch.setattr(gold, "_reconciliar", espia)
    _rodar(spark, tmp_path, cen, id_execucao="e2")
    assert vistos == [(versao, antes)]  # DURANTE a reconciliação, o destino não se moveu


def test_classifica_diferenca_das_seis(spark, tmp_path):
    cen = _cenario(spark, tmp_path)
    contrato, s = _ate_silver(spark, cen)
    torto = dataclasses.replace(contrato, ancora=dataclasses.replace(contrato.ancora, sum_vl_liquido=Decimal("1.00")))
    g = gold.agregar(spark, torto, s)
    assert g.estado == gold.DIVERGE and g.diferencas
    for d in g.diferencas:
        assert d["classificacao"] in juizo.CLASSIFICACOES_VALIDAS  # exatamente UMA das seis
        assert isinstance(d["classificacao"], str)
        assert d["classificacao"] == juizo.UNRESOLVED and gold.bloqueia(d["classificacao"])  # sem classificar, bloqueia
    assert set(json.loads(gold.diagnostico("gold", g))["classificacoes"]) == _nomes(g)


def test_orcamento_leitura_ao_veredito_medido(spark, tmp_path, monkeypatch):
    original = gold.agregar

    def lenta(*a, **k):
        time.sleep(0.4)
        return original(*a, **k)

    monkeypatch.setattr(gold, "agregar", lenta)
    cen = _cenario(spark, tmp_path)
    desfecho, _ = _rodar(spark, tmp_path, cen)
    pacote = _pacote(desfecho)
    # do início da leitura (Bronze) ao veredito: inclui Bronze, Silver e Gold
    assert 0.4 <= pacote["duracao_segundos"] <= 20 * 60
    assert desfecho.duracao_segundos == pacote["duracao_segundos"]

    # a cadeia que PARA em Silver com NAO_MEDIDO também grava a duração, até esse veredito
    cen2 = _cenario(spark, tmp_path / "z", "2026-07", com_mapa=False)
    parada, _ = _rodar(spark, tmp_path / "z", cen2)
    assert 0 < _pacote(parada)["duracao_segundos"] <= 20 * 60


def test_parada_antecipada_grava_evidencia(spark, tmp_path):
    cen = _cenario(spark, tmp_path, com_mapa=False)
    desfecho, g = _rodar(spark, tmp_path, cen)
    assert desfecho.veredito == evidencia.ERRO and desfecho.autorizado_publicar is False
    assert desfecho.caminho_pacote is not None and desfecho.caminho_pacote.exists()
    assert _pacote(desfecho)["evento_falha"]["tipo"] == "CadeiaParou"
    assert not (tmp_path / "dest").exists()


def test_diagnostico_estruturado_no_pacote(spark, tmp_path):
    cen = _cenario(spark, tmp_path, sum_ancora="2011.01")
    desfecho, _ = _rodar(spark, tmp_path, cen)
    d = _diagnostico(desfecho)
    assert {"camada", "estado", "controles_divergentes", "classificacoes"} <= set(d)
    assert d["camada"] == "bronze" and d["estado"] == bronze.DIVERGE
    soma = [c for c in d["controles_divergentes"] if c["controle"] == "sum_vl_liquido"][0]
    assert soma["observado"] == "2011.00" and soma["ancorado"] == "2011.01"

    cen2 = _cenario(spark, tmp_path / "w", "2026-08", com_mapa=False)
    desfecho2, _ = _rodar(spark, tmp_path / "w", cen2)
    d2 = _diagnostico(desfecho2)
    assert d2["camada"] == "silver" and d2["estado"] == silver.NAO_MEDIDO  # VERBATIM, não re-rotulado
    assert desfecho2.veredito == evidencia.ERRO


def test_marca_de_procedencia_vira_evidencia(spark, tmp_path):
    cen = _cenario(spark, tmp_path)
    desfecho, _ = _rodar(spark, tmp_path, cen, procedencia=False)
    assert desfecho.autorizado_publicar is False and desfecho.caminho_pacote.exists()
    d = _diagnostico(desfecho)
    assert d["motivo"] == gold.PROCEDENCIA_NAO_VINCULADA
    assert gold.PROCEDENCIA_NAO_VINCULADA in d["marcas"]
    assert _pacote(desfecho)["evento_falha"]["mensagem"]  # o pacote guarda {tipo, mensagem}: a mensagem é o diagnóstico
