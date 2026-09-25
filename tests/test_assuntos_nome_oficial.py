"""Testes do nome oficial na fat_especie — lido da Silver especie NA versão que a Gold principal registrou.

Rodam DENTRO do contêiner pda-spark. Tudo grava só sob `tmp_path`, nunca no MinIO; a Silver
especie de fixture é uma tabela Delta com o schema de `medalhao.especie`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pyspark.sql import functions as F

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_gold as tg  # noqa: E402
from test_gold import cadeias_por_modulo, spark  # noqa: E402,F401  (a mesma sessão de teste)
from test_gold_assuntos import _lido, _nomes, _preparar, _rodar  # noqa: E402
from medalhao import bronze, especie, gold_assuntos as ga  # noqa: E402

COMP = tg.COMP
CODIGOS = sorted(tg.MAPA_ESPERADO)


# ---------------------------------------------------------------- apoio


def _gravar_especie(spark, caminho, prefixo="Nome", omitir=()):
    """Um commit da Silver especie de fixture: uma linha por código, menos os omitidos."""
    linhas = [(c, f"{prefixo} {c}", "grupo", f"fonte {c}", True, COMP) for c in CODIGOS if c not in set(omitir)]
    especie._garantir_tabela(spark, caminho)
    bronze.publicar_competencia(spark, spark.createDataFrame(linhas, especie.SCHEMA), caminho, COMP, {"competencia": COMP})
    return bronze._versao_atual(spark, caminho)


def _registrar_na_gold(spark, d, caminho, versao):
    """Republica a Gold principal com a chave silver_especie {caminho, versao} no commit."""
    _, dono, _ = bronze.ler_competencia_publicada(spark, d["gold"], COMP)
    dono = {k: v for k, v in dono.items() if k not in ("nome_oficial", "motivo_nome_oficial")}
    dono["silver_especie"] = {"caminho": caminho, "versao": versao}
    atual = spark.read.format("delta").load(d["gold"]).where(F.col("competencia") == COMP)
    bronze.publicar_competencia(spark, atual, d["gold"], COMP, dono)


def _rodar_em(spark, tmp_path, d, contrato, sub, **kw):
    return ga.executar_gold_assuntos(
        spark, caminho_contrato=contrato, silver_destino=d["silver"], gold_principal_destino=d["gold"],
        fat_destino=str(tmp_path / sub / "fat"), kpis_destino=str(tmp_path / sub / "kpis"),
        preparo_raiz=str(tmp_path / sub / "prep"), id_execucao=sub, **kw,
    )


def _nomes_publicados(spark, caminho):
    return {r["especie_codigo"]: r["nome_oficial"] for r in _lido(spark, caminho).collect()}


def _dono(spark, caminho):
    return bronze.ler_competencia_publicada(spark, str(caminho), COMP)[1]


# ---------------------------------------------------------------- eval_1


def test_fat_nome_da_mesma_especie_da_gold(spark, tmp_path):
    cen, d, contrato = _preparar(spark, tmp_path)
    esp = str(tmp_path / "especie")
    _gravar_especie(spark, esp, prefixo="Antigo")
    v = _gravar_especie(spark, esp, prefixo="Fixado")
    _registrar_na_gold(spark, d, esp, v)
    _gravar_especie(spark, esp, prefixo="Posterior")  # versão mais recente: a fat NÃO pode lê-la
    r = _rodar(spark, tmp_path, d, contrato)
    assert r.estado == ga.INTEGRO, (r.estado, r.motivo, r.diferencas)
    assert _nomes_publicados(spark, tmp_path / "fat") == {c: f"Fixado {c}" for c in CODIGOS}


def test_fat_controles_iguais_com_e_sem_nome(spark, tmp_path):
    cen, d, contrato = _preparar(spark, tmp_path)
    sem = _rodar_em(spark, tmp_path, d, contrato, "sem")
    esp = str(tmp_path / "especie")
    _registrar_na_gold(spark, d, esp, _gravar_especie(spark, esp))
    com = _rodar_em(spark, tmp_path, d, contrato, "com")
    assert sem.estado == com.estado == ga.INTEGRO, (sem.motivo, com.motivo)
    assert sem.controles == com.controles
    base = [c for c in ga.FAT_COLUNAS if c != "nome_oficial"]
    linhas = lambda sub: sorted(map(tuple, _lido(spark, tmp_path / sub / "fat").select(*base).collect()))  # noqa: E731
    assert linhas("sem") == linhas("com")
    k = lambda sub: _lido(spark, tmp_path / sub / "kpis").first().asDict()  # noqa: E731
    assert k("sem") == k("com")


def test_fat_nome_oficial_no_fim_das_colunas(spark, tmp_path):
    assert ga.FAT_COLUNAS[-1] == "nome_oficial"
    cen, d, contrato = _preparar(spark, tmp_path)
    esp = str(tmp_path / "especie")
    _registrar_na_gold(spark, d, esp, _gravar_especie(spark, esp))
    assert _rodar(spark, tmp_path, d, contrato).estado == ga.INTEGRO
    assert tuple(_lido(spark, tmp_path / "fat").columns) == ga.FAT_COLUNAS


def test_fat_commit_nomeia_a_especie_lida(spark, tmp_path):
    cen, d, contrato = _preparar(spark, tmp_path)
    esp = str(tmp_path / "especie")
    v = _gravar_especie(spark, esp)
    _registrar_na_gold(spark, d, esp, v)
    assert _rodar(spark, tmp_path, d, contrato).estado == ga.INTEGRO
    dono = _dono(spark, tmp_path / "fat")
    assert dono["silver_especie"] == {"caminho": esp, "versao": v}
    assert "nome_oficial" not in dono


# ---------------------------------------------------------------- eval_2


def test_fat_codigo_sem_nome_diverge(spark, tmp_path):
    cen, d, contrato = _preparar(spark, tmp_path)
    esp = str(tmp_path / "especie")
    _registrar_na_gold(spark, d, esp, _gravar_especie(spark, esp, omitir=("02",)))
    r = _rodar(spark, tmp_path, d, contrato)
    assert r.estado == ga.DIVERGE and "NOME_OFICIAL_AUSENTE" in _nomes(r)
    assert not (tmp_path / "fat").exists() and not (tmp_path / "kpis").exists()  # nada publicado


def test_fat_sem_especie_nome_nulo_e_registrado(spark, tmp_path):
    cen, d, contrato = _preparar(spark, tmp_path)
    r = _rodar(spark, tmp_path, d, contrato)
    assert r.estado == ga.INTEGRO and r.silver_especie is None
    assert set(_nomes_publicados(spark, tmp_path / "fat").values()) == {None}
    dono = _dono(spark, tmp_path / "fat")
    assert dono["nome_oficial"] == ga.NAO_MEDIDO
    assert dono["motivo_nome_oficial"]
    assert "silver_especie" not in dono


def test_fat_reconferencia_acusa_nome_trocado(spark, tmp_path):
    cen, d, contrato = _preparar(spark, tmp_path)
    esp = str(tmp_path / "especie")
    _registrar_na_gold(spark, d, esp, _gravar_especie(spark, esp))
    assert _rodar(spark, tmp_path, d, contrato).estado == ga.INTEGRO
    esperado = _lido(spark, tmp_path / "fat")
    trocado = esperado.withColumn(
        "nome_oficial",
        F.when(F.col("especie_codigo") == "01", F.lit("Nome 02"))
        .when(F.col("especie_codigo") == "02", F.lit("Nome 01"))
        .otherwise(F.col("nome_oficial")),
    )
    caminho = str(tmp_path / "trocada")
    ga._garantir_tabela(spark, caminho, esperado.schema, ("especie_codigo", "competencia"), ga.MONETARIAS_FAT)
    bronze.publicar_competencia(spark, trocado, caminho, COMP, {"competencia": COMP})
    versao = bronze._versao_atual(spark, caminho)
    ok, detalhe = ga._conferir_tabela(spark, caminho, versao, esperado, COMP)
    assert ok is False and detalhe["so_no_esperado"] == 2 and detalhe["so_no_lido"] == 2


def test_fat_existente_evolui_e_outra_competencia_intacta(spark, tmp_path):
    cen, d, contrato = _preparar(spark, tmp_path)
    assert _rodar_em(spark, tmp_path, d, contrato, "pre").estado == ga.INTEGRO
    antiga = _lido(spark, tmp_path / "pre" / "fat").drop("nome_oficial").withColumn("competencia", F.lit("2026-02"))
    destino = str(tmp_path / "fat")
    antiga.write.format("delta").partitionBy("competencia").save(destino)
    assert "nome_oficial" not in spark.read.format("delta").load(destino).columns

    esp = str(tmp_path / "especie")
    _registrar_na_gold(spark, d, esp, _gravar_especie(spark, esp))
    with pytest.raises(bronze.EvolucaoRecusada):
        _rodar(spark, tmp_path, d, contrato, evolucao_aditiva=False)
    r = _rodar(spark, tmp_path, d, contrato, evolucao_aditiva=True)
    assert r.estado == ga.INTEGRO, (r.estado, r.motivo, r.diferencas)

    tabela = spark.read.format("delta").load(destino)
    assert tuple(tabela.columns) == ga.FAT_COLUNAS
    assert _nomes_publicados(spark, destino) == {c: f"Nome {c}" for c in CODIGOS}
    intacta = tabela.where(F.col("competencia") == "2026-02")
    assert intacta.count() == antiga.count()
    assert intacta.where(F.col("nome_oficial").isNotNull()).count() == 0
    assert intacta.drop("nome_oficial").exceptAll(antiga).count() == 0


def test_fat_evolui_por_padrao_sem_sinalizador(spark, tmp_path):
    cen, d, contrato = _preparar(spark, tmp_path)
    assert _rodar_em(spark, tmp_path, d, contrato, "pre").estado == ga.INTEGRO
    antiga = _lido(spark, tmp_path / "pre" / "fat").drop("nome_oficial").withColumn("competencia", F.lit("2026-02"))
    destino = str(tmp_path / "fat")
    antiga.write.format("delta").partitionBy("competencia").save(destino)
    assert "nome_oficial" not in spark.read.format("delta").load(destino).columns

    esp = str(tmp_path / "especie")
    _registrar_na_gold(spark, d, esp, _gravar_especie(spark, esp))
    r = _rodar(spark, tmp_path, d, contrato)
    assert r.estado == ga.INTEGRO, (r.estado, r.motivo, r.diferencas)

    tabela = spark.read.format("delta").load(destino)
    assert tuple(tabela.columns) == ga.FAT_COLUNAS
    assert _nomes_publicados(spark, destino) == {c: f"Nome {c}" for c in CODIGOS}
    intacta = tabela.where(F.col("competencia") == "2026-02")
    assert intacta.count() == antiga.count()
    assert intacta.where(F.col("nome_oficial").isNotNull()).count() == 0
