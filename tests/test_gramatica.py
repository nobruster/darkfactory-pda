"""A gramática Spark dá o MESMO veredito que o juiz Python (pda.leitura)."""
import sys
from decimal import Decimal
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from pyspark.sql import SparkSession  # noqa: E402
from pyspark.sql import functions as F  # noqa: E402
from pyspark.sql.types import DecimalType, StringType, StructField, StructType  # noqa: E402

from pda import leitura  # noqa: E402
from produtor import gramatica  # noqa: E402

ESCALA = 2
PRECISAO = 18
TEXTOS = [
    "1.518,00", "        1.518,00", "\t1,00", "\xa01,00", "1518,00", "1,5",
    "1,50", "1,500", "-5,00", "-0,00", "0,00", "1.62,00", "abc", "", "NaN",
    "1e3,00", "1.518,00\n", "\x85\x1f7,00 \x0b", "-1.000,00",
]
ESPECIES = ["01", " 01 ", "1", "001", "ab", "", None, "\xa002\t"]


@pytest.fixture(scope="module")
def spark():
    sessao = SparkSession.builder.appName("test_gramatica").getOrCreate()
    sessao.conf.set("spark.sql.ansi.enabled", "true")
    return sessao


def _df(spark, valores):
    schema = StructType([StructField("t", StringType())])
    return spark.createDataFrame([(v,) for v in valores], schema)


def _valores(spark, textos, precisao=PRECISAO, escala=ESCALA):
    df = _df(spark, textos).select(gramatica.valor_decimal(F.col("t"), precisao, escala).alias("v"))
    return [r.v for r in df.collect()]


def _confere(spark, textos):
    obtido = _valores(spark, textos)
    for texto, valor in zip(textos, obtido):
        assert valor == leitura._converter_monetario(texto, ESCALA), repr(texto)


def test_mesmo_veredito_do_juiz(spark):
    _confere(spark, TEXTOS)


def test_texto_com_espacos_nas_pontas(spark):
    _confere(spark, ["        1.518,00", "1.518,00\n", "\x85\x1f7,00 \x0b"])


def test_nbsp_e_tab_como_o_juiz(spark):
    _confere(spark, ["\xa01,00", "\t1,00", "1,00\xa0"])


def test_uma_casa_decimal_vale(spark):
    assert _valores(spark, ["1,5"]) == [Decimal("1.50")]


def test_negativo_invalido(spark):
    assert _valores(spark, ["-5,00"]) == [None]


def test_menos_zero_aceito_como_o_juiz(spark):
    assert _valores(spark, ["-0,00"]) == [Decimal("0.00")]
    _confere(spark, ["-0,00"])


def test_casas_demais_invalido(spark):
    assert _valores(spark, ["1,500"]) == [None]


def test_fora_da_precisao_falha(spark):
    with pytest.raises(Exception):
        _valores(spark, ["1.000,00"], precisao=5)


def test_negativo_fora_da_precisao_e_invalido(spark):
    assert _valores(spark, ["-1.000,00"], precisao=5) == [None]


def test_escala_negativa_recusa():
    with pytest.raises(ValueError):
        gramatica.valor_decimal(F.col("t"), 5, -1)


def test_especie_mesmo_veredito_do_juiz(spark):
    df = _df(spark, ESPECIES).select(gramatica.especie_valida(F.col("t")).alias("v"))
    obtido = [r.v for r in df.collect()]
    esperado = [False if e is None else leitura._especie_valida(e) for e in ESPECIES]
    assert obtido == esperado


def test_resultado_decimal_nunca_float(spark):
    df = _df(spark, ["1,50"]).select(gramatica.valor_decimal(F.col("t"), PRECISAO, ESCALA).alias("v"))
    assert df.schema["v"].dataType == DecimalType(PRECISAO, ESCALA)


def test_regex_exposta():
    assert gramatica.PADRAO_MONETARIO_BR == leitura._PADRAO_MONETARIO_BR.pattern
    assert gramatica.PADRAO_ESPECIE == leitura._PADRAO_ESPECIE.pattern
