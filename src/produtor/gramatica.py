"""A gramática do juiz, uma só, expressa em Spark.

O juiz Python selado (`pda.leitura`) é o oráculo: este módulo se ajusta a ele,
nunca o contrário. A regex monetária e o padrão de espécie vivem aqui, e só
aqui, para os módulos do produtor importarem em vez de copiar.

Ordem do juiz: gramática, casas decimais, sinal — e só DEPOIS a precisão.
Valor inválido por qualquer das três é NULL e nunca chega ao cast; valor
VÁLIDO que não cabe em `DecimalType(precisao, escala)` faz a ação falhar
(ANSI), nunca vira NULL.
"""
from pyspark.sql import Column
from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType

# Os mesmos caracteres que str.strip() tira no domínio latin-1.
_BRANCOS = r" \t\n\r\u000b\u000c\u001c-\u001f\u0085 "
_TIRAR_PONTAS = rf"^[{_BRANCOS}]+|[{_BRANCOS}]+$"

PADRAO_MONETARIO_BR = r"^-?\d{1,3}(\.\d{3})*,\d+$"
PADRAO_ESPECIE = r"^\d{2}$"


def _aparar(coluna: Column) -> Column:
    return F.regexp_replace(coluna.cast("string"), _TIRAR_PONTAS, "")


def valor_decimal(coluna: Column, precisao: int, escala: int) -> Column:
    """Texto monetário BR -> DecimalType(precisao, escala), ou NULL se o juiz recusa."""
    if escala < 0:
        raise ValueError(f"escala negativa: {escala}")
    limpo = _aparar(coluna)
    casas = F.length(F.regexp_extract(limpo, r",(\d+)$", 1))
    negativo = limpo.startswith("-") & limpo.rlike("[1-9]")
    valido = limpo.rlike(PADRAO_MONETARIO_BR) & (casas <= escala) & ~negativo
    numero = F.regexp_replace(F.regexp_replace(limpo, r"\.", ""), ",", ".")
    return F.when(valido, numero.cast(DecimalType(precisao, escala)))


def especie_valida(coluna: Column) -> Column:
    """True se o código é ^\\d{2}$ depois de aparar; nulo é inválido."""
    return F.coalesce(_aparar(coluna).rlike(PADRAO_ESPECIE), F.lit(False))
