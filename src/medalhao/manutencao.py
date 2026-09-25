"""Manutenção das tabelas Delta publicadas: retenção de cinco anos e OPTIMIZE com prova.

Não há VACUUM aqui: apagar arquivo é apagar evidência, e só se faz sob pedido do
dono (ADR 0017). Quem chama este módulo ao fim de cada carga é o procedimento de
publicação do dono — nunca `publicar`, cujas versões os testes conferem exatas.
"""

from __future__ import annotations

import re
from typing import Dict, Optional

from pyspark.sql import DataFrame, SparkSession

from medalhao import bronze

RETENCAO_DIAS = 1825
RETENCAO_ALVO = f"interval {RETENCAO_DIAS} days"
PROPRIEDADES_RETENCAO = ("delta.logRetentionDuration", "delta.deletedFileRetentionDuration")

_INTERVALO = re.compile(r"^\s*interval\s+(\d+)\s+days?\s*$", re.IGNORECASE)

_delta_table = bronze._delta_table


def _propriedades(spark: SparkSession, caminho: str) -> Dict[str, str]:
    return _delta_table(spark, caminho).detail().select("properties").first()[0] or {}


def _dias(valor: str) -> Optional[int]:
    m = _INTERVALO.match(str(valor))
    return int(m.group(1)) if m else None


def planejar_retencao(spark: SparkSession, caminho: str) -> dict:
    """O que `garantir_retencao` faria, sem commit. Ver `garantir_retencao`."""
    atuais = _propriedades(spark, caminho)
    anteriores = {p: atuais.get(p) for p in PROPRIEDADES_RETENCAO}
    a_gravar: Dict[str, str] = {}
    corrigiu = False
    for prop in PROPRIEDADES_RETENCAO:
        valor = atuais.get(prop)
        if valor is None:
            a_gravar[prop] = RETENCAO_ALVO
            continue
        dias = _dias(valor)
        if dias is None:
            return {
                "resultado": "NAO_MEDIDO",
                "motivo": f"{prop} em formato ilegível: {valor!r}",
                "propriedade": prop,
                "anteriores": anteriores,
            }
        if dias < RETENCAO_DIAS:
            a_gravar[prop] = RETENCAO_ALVO
            corrigiu = True
    if not a_gravar:
        return {"resultado": "JA_TINHA", "anteriores": anteriores}
    return {
        "resultado": "CORRIGIDA" if corrigiu else "ALTERADA",
        "anteriores": anteriores,
        "gravadas": a_gravar,
    }


def garantir_retencao(spark: SparkSession, caminho: str) -> dict:
    """Leva CADA propriedade de retenção a >= 1825 dias, sem nunca encurtar.

    Devolve `resultado` em JA_TINHA | ALTERADA | CORRIGIDA | NAO_MEDIDO, com os
    valores `anteriores`. Sem nada a mudar não há commit; com mudança, um único ALTER.
    """
    plano = planejar_retencao(spark, caminho)
    if plano["resultado"] in ("ALTERADA", "CORRIGIDA"):
        lista = ", ".join(f"'{p}' = '{v}'" for p, v in plano["gravadas"].items())
        spark.sql(f"ALTER TABLE delta.`{caminho}` SET TBLPROPERTIES ({lista})")
    return plano


def _compactar(spark: SparkSession, caminho: str):
    return _delta_table(spark, caminho).optimize().executeCompaction()


def _ler_versao(spark: SparkSession, caminho: str, versao: int) -> DataFrame:
    return spark.read.format("delta").option("versionAsOf", int(versao)).load(caminho)


def _iguais(a: DataFrame, b: DataFrame) -> bool:
    """Multiconjunto nos dois sentidos, no motor: o OPTIMIZE não grava contagem de linhas."""
    return a.exceptAll(b).count() == 0 and b.exceptAll(a).count() == 0


def otimizar(spark: SparkSession, caminho: str) -> dict:
    """OPTIMIZE (compactação) e prova de que o dado da versão nova é o da anterior.

    SEM_MUDANCA | OTIMIZADA | DIVERGE | NAO_MEDIDO. Métricas de arquivo só são relatadas.
    """
    v = bronze._versao_atual(spark, caminho)
    metricas = _compactar(spark, caminho).collect()
    novos = [
        r
        for r in _delta_table(spark, caminho).history().select("version", "operation").collect()
        if int(r["version"]) > v
    ]
    if not novos:
        return {"resultado": "SEM_MUDANCA", "versao_antes": v}
    if len(novos) != 1 or novos[0]["operation"] != "OPTIMIZE":
        return {
            "resultado": "NAO_MEDIDO",
            "motivo": "commit alheio ao OPTIMIZE entre as versões (escrita concorrente)",
            "versao_antes": v,
            "commits": [(int(r["version"]), r["operation"]) for r in novos],
        }
    w = int(novos[0]["version"])
    igual = _iguais(_ler_versao(spark, caminho, v), _ler_versao(spark, caminho, w))
    return {
        "resultado": "OTIMIZADA" if igual else "DIVERGE",
        "versao_antes": v,
        "versao_depois": w,
        "metricas": str(metricas[0][1]) if metricas else None,
    }
