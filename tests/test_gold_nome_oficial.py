"""Testes do nome oficial na Gold principal — lido da Silver especie, ligado pelo código.

Rodam DENTRO do contêiner pda-spark. Tudo grava só sob `tmp_path`, nunca no MinIO; a Silver
especie de fixture é uma tabela Delta com o schema de `medalhao.especie`.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest
from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType, StringType, StructField, StructType

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_gold as tg  # noqa: E402
from medalhao import bronze, especie, gold  # noqa: E402

COMP = tg.COMP
CODIGOS = sorted(tg.MAPA_ESPERADO)

ESQUEMA_5 = StructType(
    [
        StructField("especie_codigo", StringType()),
        StructField("especie_descricao", StringType()),
        StructField("vl_liquido_total", DecimalType(14, 2)),
        StructField("competencia", StringType()),
        StructField("nome_oficial", StringType()),
    ]
)


@pytest.fixture(scope="session")
def spark():
    sessao = bronze.criar_sessao("teste-gold-nome-oficial")
    sessao.conf.set("spark.sql.shuffle.partitions", "4")
    yield sessao
    sessao.stop()


# ---------------------------------------------------------------- apoio


def _gravar_especie(spark, caminho, prefixo="Nome", omitir=(), comp=COMP):
    """Um commit da Silver especie de fixture: uma linha por código, menos os omitidos."""
    linhas = [
        (c, f"{prefixo} {c}", "grupo", f"fonte {c}", True, comp) for c in CODIGOS if c not in set(omitir)
    ]
    especie._garantir_tabela(spark, caminho)
    bronze.publicar_competencia(
        spark, spark.createDataFrame(linhas, especie.SCHEMA), caminho, comp, {"competencia": comp}
    )
    return bronze._versao_atual(spark, caminho)


def _agregar(spark, tmp_path, especie_destino=None):
    cen = tg._cenario(spark, tmp_path)
    contrato, s = tg._ate_silver(spark, cen)
    g = gold.agregar(spark, contrato, s, especie_destino=especie_destino)
    return contrato, g


def _publicar(spark, tmp_path, contrato, g, destino=None, **kw):
    destino = destino or str(tmp_path / "dest")
    r = gold.publicar(spark, contrato, g, tg._desfecho_autorizado(tmp_path), destino=destino, id_execucao="e1", **kw)
    return r, destino


def _nomes_publicados(spark, destino, comp=COMP):
    lido = spark.read.format("delta").load(destino).where(F.col("competencia") == comp)
    return {r["especie_codigo"]: r["nome_oficial"] for r in lido.collect()}


def _linhas4(g):
    return sorted(map(tuple, g.linhas.select(*gold.GOLD_COLUNAS[:4]).collect()))


# ---------------------------------------------------------------- eval_1


def test_nome_oficial_vem_da_silver_especie(spark, tmp_path):
    esp = str(tmp_path / "especie")
    _gravar_especie(spark, esp)
    contrato, g = _agregar(spark, tmp_path, esp)
    assert g.estado == gold.INTEGRO, (g.estado, g.motivo, g.diferencas)
    assert gold.GOLD_COLUNAS[-1] == "nome_oficial"
    assert tuple(g.linhas.columns) == gold.GOLD_COLUNAS
    r, destino = _publicar(spark, tmp_path, contrato, g)
    assert r.gravacao["destino"] == destino
    assert _nomes_publicados(spark, destino) == {c: f"Nome {c}" for c in CODIGOS}


def test_controles_iguais_com_e_sem_nome(spark, tmp_path):
    esp = str(tmp_path / "especie")
    _gravar_especie(spark, esp)
    _, sem = _agregar(spark, tmp_path / "a")
    _, com = _agregar(spark, tmp_path / "b", esp)
    assert sem.estado == com.estado == gold.INTEGRO
    assert sem.controles == com.controles
    assert sem.total_por_codigo == com.total_por_codigo == tg.MAPA_ESPERADO
    assert _linhas4(sem) == _linhas4(com)  # o left join veio DEPOIS do groupBy: mesmas linhas, mesmas somas
    assert com.linhas.count() == sem.linhas.count() == len(CODIGOS)


def test_commit_nomeia_a_versao_da_especie(spark, tmp_path):
    esp = str(tmp_path / "especie")
    _gravar_especie(spark, esp)
    v = _gravar_especie(spark, esp, prefixo="Novo")
    contrato, g = _agregar(spark, tmp_path, esp)
    r, destino = _publicar(spark, tmp_path, contrato, g)
    _, dono, _ = gold.ler_competencia_publicada(spark, destino, COMP)
    assert dono["silver_especie"] == {"caminho": esp, "versao": v}
    assert "nome_oficial" not in dono
    assert r.silver_especie == {"caminho": esp, "versao": v}


def test_especie_lida_na_versao_fixada(spark, tmp_path):
    esp = str(tmp_path / "especie")
    _gravar_especie(spark, esp, prefixo="Antigo")
    v = _gravar_especie(spark, esp, prefixo="Fixado")
    contrato, g = _agregar(spark, tmp_path, esp)
    assert g.silver_especie["versao"] == v
    _gravar_especie(spark, esp, prefixo="Posterior")  # uma versão nova ANTES de publicar
    r, destino = _publicar(spark, tmp_path, contrato, g)
    assert _nomes_publicados(spark, destino) == {c: f"Fixado {c}" for c in CODIGOS}
    _, dono, _ = gold.ler_competencia_publicada(spark, destino, COMP)
    assert dono["silver_especie"]["versao"] == v


# ---------------------------------------------------------------- eval_2


def test_codigo_sem_nome_diverge_e_nao_publica(spark, tmp_path):
    esp = str(tmp_path / "especie")
    _gravar_especie(spark, esp, omitir=("02",))
    contrato, g = _agregar(spark, tmp_path, esp)
    assert g.estado == gold.DIVERGE
    assert "NOME_OFICIAL_AUSENTE" in tg._nomes(g)
    assert "02" in [d for d in g.diferencas if d["identidade"] == "NOME_OFICIAL_AUSENTE"][0]["observado"]
    r, destino = _publicar(spark, tmp_path, contrato, g)
    assert r.estado == gold.DIVERGE and r.gravacao is None
    assert not Path(destino).exists()  # nada publicado


def test_sem_especie_nome_nulo_e_registrado(spark, tmp_path):
    contrato, g = _agregar(spark, tmp_path)
    assert g.estado == gold.INTEGRO and g.silver_especie is None
    r, destino = _publicar(spark, tmp_path, contrato, g)
    assert r.gravacao["destino"] == destino
    assert set(_nomes_publicados(spark, destino).values()) == {None}
    _, dono, _ = gold.ler_competencia_publicada(spark, destino, COMP)
    assert dono["nome_oficial"] == gold.NAO_MEDIDO
    assert dono["motivo_nome_oficial"] == "SEM_SILVER_ESPECIE"
    assert "silver_especie" not in dono


def test_reconferencia_acusa_nome_trocado(spark, tmp_path):
    pol = tg._politica()
    linhas = [("01", "A", Decimal("10.00"), COMP, "Um"), ("02", "B", Decimal("20.00"), COMP, "Dois")]
    trocado = [("01", "A", Decimal("10.00"), COMP, "Dois"), ("02", "B", Decimal("20.00"), COMP, "Um")]
    esperado = spark.createDataFrame(linhas, ESQUEMA_5)
    caminho = str(tmp_path / "tab")
    gold._garantir_tabela(spark, caminho, pol)
    bronze.publicar_competencia(spark, spark.createDataFrame(trocado, ESQUEMA_5), caminho, COMP, {"competencia": COMP})
    controles = {"sum_vl_liquido": Decimal("30.00")}
    versao = gold._versao_atual(spark, caminho)

    ok, detalhe = gold._conferir_tabela(spark, caminho, versao, esperado, controles, COMP, pol, com_nome=True)
    assert detalhe["controles_divergentes"] == ()  # a soma não vê o nome trocado
    assert detalhe["so_no_esperado"] == 2 and detalhe["so_no_lido"] == 2
    assert ok is False

    ok, detalhe = gold._conferir_tabela(spark, caminho, versao, esperado, controles, COMP, pol, com_nome=True)
    assert ok is False
    # sem especie_destino, um nome preenchido no publicado também é acusado
    sem_nome = esperado.withColumn("nome_oficial", F.lit(None).cast(StringType()))
    ok, detalhe = gold._conferir_tabela(spark, caminho, versao, sem_nome, controles, COMP, pol)
    assert ok is False and detalhe["nomes_nao_nulos"] == 2


def test_tabela_de_quatro_colunas_evolui_aditiva(spark, tmp_path):
    esp = str(tmp_path / "especie")
    _gravar_especie(spark, esp)
    destino = str(tmp_path / "dest")
    antiga = tg._df_gold(spark, [("01", "A", "10.00"), ("02", "B", "20.00")], "2026-02")
    antiga.write.format("delta").partitionBy("competencia").save(destino)
    assert tuple(spark.read.format("delta").load(destino).columns) == gold.GOLD_COLUNAS[:4]

    contrato, g = _agregar(spark, tmp_path, esp)
    with pytest.raises(gold.EvolucaoRecusada):
        _publicar(spark, tmp_path, contrato, g, destino)
    r, _ = _publicar(spark, tmp_path, contrato, g, destino, evolucao_aditiva=True)
    assert r.gravacao["destino"] == destino

    tabela = spark.read.format("delta").load(destino)
    assert tuple(tabela.columns) == gold.GOLD_COLUNAS
    assert _nomes_publicados(spark, destino) == {c: f"Nome {c}" for c in CODIGOS}
    intacta = tabela.where(F.col("competencia") == "2026-02").collect()
    assert sorted((r["especie_codigo"], r["vl_liquido_total"]) for r in intacta) == [
        ("01", Decimal("10.00")), ("02", Decimal("20.00")),
    ]
    assert {r["nome_oficial"] for r in intacta} == {None}
