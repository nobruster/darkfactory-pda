"""Padrões Delta da Silver e da ingestão — evolução aditiva por padrão, com a guarda.

Rodam DENTRO do contêiner pda-spark. Só gravam em `tmp_path`, nunca no MinIO,
e nenhuma função para a sessão Spark da suíte.
"""

from __future__ import annotations

import inspect
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pyspark.sql import functions as F  # noqa: E402
from pyspark.sql.types import DecimalType, StringType, StructField, StructType  # noqa: E402

from medalhao import bronze, ingestao, silver  # noqa: E402
from pda.contrato import PoliticaDecimal  # noqa: E402

COMP = "2026-01"
ESQUEMA = StructType(
    [
        StructField("especie_codigo", StringType()),
        StructField("especie_descricao", StringType()),
        StructField("especie_descricao_normalizada", StringType()),
        StructField("vl_liquido", DecimalType(14, 2)),
        StructField("classificacao", StringType()),
    ]
)
LINHAS = [
    ("01", "Aposentadoria", "APOSENTADORIA", Decimal("10.00"), None),
    ("02", "Pensao", "PENSAO", Decimal("20.50"), None),
]


@pytest.fixture(scope="module")
def spark():
    # a sessão é da suíte: getOrCreate reaproveita e ninguém a para
    return bronze.criar_sessao("teste-delta-padroes-silver")


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


def _base(spark, caminho: str):
    silver._garantir_tabela(spark, caminho, _politica())
    df = spark.createDataFrame(LINHAS, ESQUEMA).withColumn("competencia", F.lit(COMP))
    silver.publicar_competencia(spark, df, caminho, COMP, {"competencia": COMP})
    return df


def _padrao(funcao) -> bool:
    return inspect.signature(funcao).parameters["evolucao_aditiva"].default


def _publicar(spark, df, caminho, evolucao):
    silver.publicar_competencia(spark, df, caminho, COMP, {"competencia": COMP}, evolucao_aditiva=evolucao)


def test_silver_evolui_por_padrao(spark, tmp_path):
    caminho = str(tmp_path / "tab")
    base = _base(spark, caminho)
    assert _padrao(silver.executar_classificacao) is True
    _publicar(spark, base.withColumn("nova", F.lit("x")), caminho, _padrao(silver.executar_classificacao))
    assert "nova" in spark.read.format("delta").load(caminho).columns


def test_silver_troca_de_tipo_recusada(spark, tmp_path):
    caminho = str(tmp_path / "tab")
    base = _base(spark, caminho)
    trocado = base.withColumn("vl_liquido", F.col("vl_liquido").cast("double"))
    with pytest.raises(silver.EvolucaoRecusada):
        _publicar(spark, trocado, caminho, _padrao(silver.executar_classificacao))


def test_silver_coluna_removida_recusada(spark, tmp_path):
    caminho = str(tmp_path / "tab")
    base = _base(spark, caminho)
    with pytest.raises(silver.EvolucaoRecusada):
        _publicar(spark, base.drop("especie_descricao"), caminho, _padrao(silver.executar_classificacao))


def test_silver_evolucao_desligada_recusa(spark, tmp_path):
    caminho = str(tmp_path / "tab")
    base = _base(spark, caminho)
    with pytest.raises(silver.EvolucaoRecusada):
        _publicar(spark, base.withColumn("nova", F.lit("x")), caminho, False)
    assert "nova" not in spark.read.format("delta").load(caminho).columns


def test_ingestao_evolui_por_padrao():
    assert _padrao(ingestao.executar_ingestao) is True


@pytest.mark.parametrize("valor", [True, False])
def test_ingestao_repassa_o_sinalizador(spark, tmp_path, monkeypatch, valor):
    pacote = tmp_path / "pacote.json"
    pacote.write_text("{}")
    desfecho = SimpleNamespace(autorizado_publicar=True, caminho_pacote=pacote)
    visto = {}

    monkeypatch.setattr(ingestao, "montar_leitura", lambda *a, **k: None)
    monkeypatch.setattr(ingestao.orquestracao, "conduzir", lambda **k: desfecho)
    monkeypatch.setattr(ingestao.evidencia, "ler_pacote", lambda c: {})
    monkeypatch.setattr(ingestao.contrato_mod, "carregar_contrato", lambda c: object())
    monkeypatch.setattr(ingestao, "_julgado_do_pacote", lambda p: {})

    def falso(spark, contrato, medido, **kwargs):
        visto.update(kwargs)
        return "publicado"

    monkeypatch.setattr(ingestao.bronze, "publicar_bronze", falso)
    ingestao.executar_ingestao(
        spark,
        diretorio_evidencia=tmp_path,
        competencia_solicitada=COMP,
        caminho_contrato="x",
        caminho_csv="y",
        raiz="z",
        evolucao_aditiva=valor,
    )
    assert visto["evolucao_aditiva"] is valor
