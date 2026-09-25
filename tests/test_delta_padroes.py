"""Padrões Delta da sessão e da Bronze — declarados, não herdados.

Rodam DENTRO do contêiner pda-spark. Só gravam em `tmp_path`, nunca no MinIO,
e nenhuma função para a sessão Spark da suíte.
"""

from __future__ import annotations

import inspect
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pyspark.sql import functions as F  # noqa: E402
from pyspark.sql.types import DecimalType, StringType, StructField, StructType  # noqa: E402

from medalhao import bronze  # noqa: E402
from pda.contrato import PoliticaDecimal  # noqa: E402

COMP = "2026-01"
ESQUEMA = StructType(
    [
        StructField("especie_codigo", StringType()),
        StructField("especie_descricao", StringType()),
        StructField("vl_liquido", DecimalType(14, 2)),
    ]
)
LINHAS = [("01", "APOSENTADORIA", Decimal("10.00")), ("02", "PENSAO", Decimal("20.50"))]


@pytest.fixture(scope="module")
def spark():
    # a sessão é da suíte: getOrCreate reaproveita e ninguém a para
    return bronze.criar_sessao("teste-delta-padroes")


def _politica() -> PoliticaDecimal:
    return PoliticaDecimal(
        modo="HALF_EVEN",
        escala=2,
        escala_maxima_intermediarios=3,
        precisao=14,
        nao_negativo=True,
        emax=999999,
        emin=-999999,
    )


def _propriedades(spark, caminho: str) -> dict:
    return bronze._delta_table(spark, caminho).detail().select("properties").first()[0] or {}


def _base(spark, caminho: str):
    bronze._garantir_tabela(spark, caminho, _politica())
    df = spark.createDataFrame(LINHAS, ESQUEMA).withColumn("competencia", F.lit(COMP))
    bronze.publicar_competencia(spark, df, caminho, COMP, {"competencia": COMP})
    return df


def test_sessao_declara_as_tres_praticas(spark):
    assert bronze.RETENCAO_PADRAO == "interval 1825 days"
    esperado = {
        "spark.databricks.delta.schema.autoMerge.enabled": "false",
        "spark.databricks.delta.retentionDurationCheck.enabled": "true",
        "spark.databricks.delta.replaceWhere.constraintCheck.enabled": "true",
        "spark.databricks.delta.properties.defaults.logRetentionDuration": bronze.RETENCAO_PADRAO,
        "spark.databricks.delta.properties.defaults.deletedFileRetentionDuration": bronze.RETENCAO_PADRAO,
    }
    for chave, valor in esperado.items():
        assert spark.conf.get(chave) == valor, chave
    # segunda chamada reaproveita a sessão e continua declarando
    outra = bronze.criar_sessao("outra")
    for chave, valor in esperado.items():
        assert outra.conf.get(chave) == valor, chave


def test_tabela_nova_nasce_com_retencao_de_cinco_anos(spark, tmp_path):
    caminho = str(tmp_path / "nova")
    bronze._garantir_tabela(spark, caminho, _politica())
    props = _propriedades(spark, caminho)
    assert props["delta.logRetentionDuration"] == bronze.RETENCAO_PADRAO
    assert props["delta.deletedFileRetentionDuration"] == bronze.RETENCAO_PADRAO


def test_tabela_existente_reentrada_sem_commit(spark, tmp_path):
    caminho = str(tmp_path / "existente")
    bronze._garantir_tabela(spark, caminho, _politica())
    versao = bronze._versao_atual(spark, caminho)
    props = _propriedades(spark, caminho)
    bronze._garantir_tabela(spark, caminho, _politica())
    assert bronze._versao_atual(spark, caminho) == versao
    assert _propriedades(spark, caminho) == props


def test_bronze_evolui_coluna_nova_por_padrao(spark, tmp_path):
    caminho = str(tmp_path / "tab")
    base = _base(spark, caminho)
    for funcao in (bronze.executar_leitura, bronze.publicar_bronze):
        assert inspect.signature(funcao).parameters["evolucao_aditiva"].default is True
    padrao = inspect.signature(bronze.publicar_bronze).parameters["evolucao_aditiva"].default
    bronze.publicar_competencia(
        spark, base.withColumn("nova", F.lit("x")), caminho, COMP, {"competencia": COMP},
        evolucao_aditiva=padrao,
    )
    assert "nova" in spark.read.format("delta").load(caminho).columns


def test_bronze_troca_de_tipo_recusada_mesmo_por_padrao(spark, tmp_path):
    caminho = str(tmp_path / "tab")
    base = _base(spark, caminho)
    trocado = base.withColumn("vl_liquido", F.col("vl_liquido").cast("double"))
    with pytest.raises(bronze.EvolucaoRecusada):
        bronze.publicar_competencia(
            spark, trocado, caminho, COMP, {"competencia": COMP}, evolucao_aditiva=True
        )


def test_bronze_coluna_removida_recusada(spark, tmp_path):
    caminho = str(tmp_path / "tab")
    base = _base(spark, caminho)
    sem_coluna = base.drop("especie_descricao")
    with pytest.raises(Exception):
        bronze.publicar_competencia(
            spark, sem_coluna, caminho, COMP, {"competencia": COMP}, evolucao_aditiva=True
        )
    assert "especie_descricao" in spark.read.format("delta").load(caminho).columns


def test_bronze_evolucao_desligada_recusa(spark, tmp_path):
    caminho = str(tmp_path / "tab")
    base = _base(spark, caminho)
    with pytest.raises(bronze.EvolucaoRecusada):
        bronze.publicar_competencia(
            spark, base.withColumn("nova", F.lit("x")), caminho, COMP, {"competencia": COMP},
            evolucao_aditiva=False,
        )


def test_publicar_competencia_segue_desligado():
    assert inspect.signature(bronze.publicar_competencia).parameters["evolucao_aditiva"].default is False
