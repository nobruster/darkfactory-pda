"""Limpeza do preparo — apaga o estágio privado de uma execução já publicada e conferida.

Só apaga `<camada>/_preparo/.../execucao=<id>` quando o ÚLTIMO commit que nomeia a competência no
`userMetadata` da tabela publicada é o dessa execução, com estado de publicação (INTEGRO) — não de
reversão. Qualquer outro caso preserva o preparo e devolve o motivo. Nunca VACUUM: o histórico da
tabela publicada é evidência; só o preparo, que não é histórico, sai.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from medalhao import bronze

CAMADAS = ("bronze", "silver", "gold")
ID_VALIDO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

APAGADO = "APAGADO"
PRESERVADO = "PRESERVADO"
RECUSADO = "RECUSADO"


@dataclass(frozen=True)
class Limpeza:
    resultado: str  # APAGADO | PRESERVADO | RECUSADO
    motivo: str = ""
    prefixo: str = ""
    conferido: bool = False

    @property
    def apagou(self) -> bool:
        return self.resultado == APAGADO


class CaminhoRecusado(ValueError):
    pass


def montar_prefixo(camada: str, preparo_raiz: str, id_execucao: str) -> str:
    """Monta `<...>/<camada>/_preparo/.../execucao=<id>` de partes validadas; recusa o resto."""
    if camada not in CAMADAS:
        raise CaminhoRecusado(f"CAMADA_INVALIDA: {camada!r}")
    if not isinstance(id_execucao, str) or not ID_VALIDO.match(id_execucao):
        raise CaminhoRecusado(f"ID_EXECUCAO_INVALIDO: {id_execucao!r}")
    if not isinstance(preparo_raiz, str) or not preparo_raiz.strip():
        raise CaminhoRecusado("PREPARO_VAZIO")
    corpo = preparo_raiz.split("://", 1)[-1]
    partes = [p for p in corpo.split("/") if p]
    if any(p in (".", "..") for p in partes):
        raise CaminhoRecusado(f"CAMINHO_FORA_DO_PREPARO: {preparo_raiz!r}")
    achou = [i for i in range(len(partes) - 1) if partes[i] == camada and partes[i + 1] == "_preparo"]
    if not achou or len(partes) <= achou[-1] + 2:
        raise CaminhoRecusado(f"CAMINHO_FORA_DO_PREPARO: {preparo_raiz!r}")
    return f"{preparo_raiz.rstrip('/')}/execucao={id_execucao}"


def _historico(spark: SparkSession, publicada: str) -> List[Tuple[int, Optional[str]]]:
    return bronze._historico(spark, publicada)


def _commit_da_competencia(historico, competencia: str) -> Optional[Tuple[int, dict]]:
    for versao, meta in sorted(historico, key=lambda t: t[0], reverse=True):
        if not meta:
            continue
        try:
            corpo = json.loads(meta)
        except ValueError:
            continue
        if isinstance(corpo, dict) and corpo.get("competencia") == competencia:
            return versao, corpo
    return None


def _medir(spark: SparkSession, publicada: str, coluna_soma: str) -> Tuple[int, int, Any]:
    versao = bronze._versao_atual(spark, publicada)
    linhas = spark.read.format("delta").option("versionAsOf", versao).load(publicada)
    contagem, soma = linhas.agg(F.count(F.lit(1)), F.sum(coluna_soma)).collect()[0]
    return versao, int(contagem), soma


def _apagar(spark: SparkSession, prefixo: str) -> None:
    jvm = spark._jvm
    caminho = jvm.org.apache.hadoop.fs.Path(prefixo)
    caminho.getFileSystem(spark._jsc.hadoopConfiguration()).delete(caminho, True)


def limpar_preparo(
    spark: SparkSession,
    camada: str,
    publicada: str,
    preparo_raiz: str,
    competencia: str,
    id_execucao: str,
    coluna_soma: str = "vl_liquido",
) -> Limpeza:
    try:
        prefixo = montar_prefixo(camada, preparo_raiz, id_execucao)
    except CaminhoRecusado as exc:
        return Limpeza(RECUSADO, str(exc))

    dono = _commit_da_competencia(_historico(spark, publicada), competencia)
    if dono is None:
        return Limpeza(PRESERVADO, "EXECUCAO_NAO_PUBLICADA", prefixo)
    _, meta = dono
    if meta.get("id_execucao") != id_execucao:
        return Limpeza(PRESERVADO, "EXECUCAO_NAO_E_A_ULTIMA_PUBLICADA", prefixo)
    if meta.get("estado") != bronze.INTEGRO:
        return Limpeza(PRESERVADO, f"ESTADO_NAO_E_PUBLICACAO: {meta.get('estado')}", prefixo)

    antes = _medir(spark, publicada, coluna_soma)
    _apagar(spark, prefixo)
    depois = _medir(spark, publicada, coluna_soma)
    if antes != depois:
        return Limpeza(APAGADO, f"PUBLICADA_MUDOU: {antes} -> {depois}", prefixo, conferido=False)
    return Limpeza(APAGADO, "", prefixo, conferido=True)
