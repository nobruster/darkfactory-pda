"""Gold da referência: dim_especie e dim_termo, servidas SÓ a partir da Silver.

A Gold serve o que a Silver conformou — não recalcula nome nem grupo. Cada tabela Silver é lida
numa versão fixada no INÍCIO (versionAsOf), e essas versões vão no commit de cada dimensão, ao
lado do id_execucao.

As duas dimensões são publicações INDEPENDENTES, cada uma com o seu estado: INTEGRO, DIVERGE,
NAO_MEDIDO ou ERRO_LEITURA. Seleção vazia é NAO_MEDIDO ANTES de gravar — ela nunca chega ao
replaceWhere, que apagaria a partição existente. O consumo só lê as duas juntas se as duas
estiverem INTEGRO (`Resultado.consumo_integro`).

- dim_especie: replaceWhere da COMPETÊNCIA; as outras competências ficam intactas.
- dim_termo: replaceWhere do sha256_arquivo; as outras versões do glossário ficam intactas.
- Nunca append, nunca overwrite da tabela inteira.
- Gravado, o destino é relido NA versão do próprio commit (achada pelo id_execucao).
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, replace
from typing import Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import BooleanType, StringType, StructField, StructType

INTEGRO = "INTEGRO"
DIVERGE = "DIVERGE"
NAO_MEDIDO = "NAO_MEDIDO"
ERRO_LEITURA = "ERRO_LEITURA"

DESTINO_PADRAO = "s3a://gold/pda/referencia"
SILVER_ESPECIE_PADRAO = "s3a://silver/pda/especie"
SILVER_GLOSSARIO_PADRAO = "s3a://silver/pda/glossario"

ESPECIE_COLUNAS = (
    "codigo", "nome_oficial", "grupo", "descricao_fonte", "texto_fonte_confere_prefixo", "competencia",
)
TERMO_COLUNAS = ("termo", "descricao", "sha256_arquivo")

ESPECIE_SCHEMA = StructType([
    StructField("codigo", StringType(), nullable=False),
    StructField("nome_oficial", StringType()),
    StructField("grupo", StringType()),
    StructField("descricao_fonte", StringType()),
    StructField("texto_fonte_confere_prefixo", BooleanType()),
    StructField("competencia", StringType(), nullable=False),
])
TERMO_SCHEMA = StructType([
    StructField("termo", StringType(), nullable=False),
    StructField("descricao", StringType()),
    StructField("sha256_arquivo", StringType(), nullable=False),
])

_GRAVIDADE = (ERRO_LEITURA, DIVERGE, NAO_MEDIDO)


@dataclass(frozen=True)
class Dimensao:
    """O estado de UMA dimensão: nunca um booleano solto."""

    estado: str
    motivo: str = ""
    tabela: Optional[str] = None
    versao: Optional[int] = None
    linhas: int = 0
    detalhe: Optional[dict] = None


@dataclass(frozen=True)
class Resultado:
    estado: str
    competencia: str
    sha256_glossario: str
    dim_especie: Dimensao = Dimensao(NAO_MEDIDO, "NAO_TENTADA")
    dim_termo: Dimensao = Dimensao(NAO_MEDIDO, "NAO_TENTADA")
    versao_silver_especie: Optional[int] = None
    versao_silver_glossario: Optional[int] = None
    id_execucao: Optional[str] = None
    motivo: str = ""

    @property
    def consumo_integro(self) -> bool:
        """O consumo só lê as duas dimensões juntas se as duas estiverem INTEGRO."""
        return self.dim_especie.estado == INTEGRO and self.dim_termo.estado == INTEGRO


# ---------------------------------------------------------------- Delta

def _delta_table(spark: SparkSession, caminho: str):
    from delta.tables import DeltaTable

    return DeltaTable.forPath(spark, caminho)


def _e_delta(spark: SparkSession, caminho: str) -> bool:
    from delta.tables import DeltaTable

    try:
        return DeltaTable.isDeltaTable(spark, caminho)
    except Exception:  # noqa: BLE001 — caminho ilegível é o mesmo que ausente para esta pergunta
        return False


def _versao_atual(spark: SparkSession, caminho: str) -> int:
    return int(_delta_table(spark, caminho).history(1).select("version").first()[0])


def _historico(spark: SparkSession, caminho: str):
    linhas = _delta_table(spark, caminho).history().select("version", "userMetadata").collect()
    return [(int(r["version"]), r["userMetadata"]) for r in linhas]


def _ler_versao(spark: SparkSession, caminho: str, versao: int) -> DataFrame:
    return spark.read.format("delta").option("versionAsOf", versao).load(caminho)


def _garantir_tabela(spark: SparkSession, caminho: str, schema: StructType, particao: str) -> None:
    from delta.tables import DeltaTable

    construtor = DeltaTable.createIfNotExists(spark).location(caminho)
    for campo in schema:
        construtor = construtor.addColumn(campo.name, campo.dataType, nullable=campo.nullable)
    construtor.partitionedBy(particao).execute()


def _versao_do_commit(spark: SparkSession, caminho: str, id_execucao: str) -> Optional[int]:
    """Versão do PRÓPRIO commit, achada pelo id_execucao — nunca 'a última'."""
    achadas = []
    for versao, meta in _historico(spark, caminho):
        try:
            corpo = json.loads(meta) if meta else None
        except ValueError:
            continue
        if isinstance(corpo, dict) and corpo.get("id_execucao") == id_execucao:
            achadas.append(versao)
    return max(achadas) if achadas else None


def _ler_commit(spark: SparkSession, caminho: str, versao: int, condicao: str, colunas) -> DataFrame:
    return _ler_versao(spark, caminho, versao).where(F.expr(condicao)).select(*colunas)


def _reverter(spark: SparkSession, caminho: str, condicao: str, existia: bool, versao_anterior: int, meta: dict) -> None:
    """Desfaz SÓ a partição publicada — outra partição da mesma tabela não é tocada."""
    meta_json = json.dumps({**meta, "estado": "REVERTIDO"}, ensure_ascii=False, sort_keys=True)
    if existia:
        (
            _ler_versao(spark, caminho, versao_anterior).where(F.expr(condicao))
            .write.format("delta").mode("overwrite")
            .option("replaceWhere", condicao)
            .option("userMetadata", meta_json)
            .save(caminho)
        )
        return
    chave = "spark.databricks.delta.commitInfo.userMetadata"
    spark.conf.set(chave, meta_json)
    try:
        _delta_table(spark, caminho).delete(condicao)
    finally:
        spark.conf.unset(chave)


# ---------------------------------------------------------------- seleção na Silver


def _selecionar_especie(spark: SparkSession, caminho: str, versao: int, competencia: str) -> DataFrame:
    """Só a competência pedida, na versão fixada; o que a Silver conformou entra COMO VEIO."""
    return (
        _ler_versao(spark, caminho, versao)
        .where(F.col("competencia") == competencia)
        .select(
            F.col("especie_codigo").alias("codigo"), "nome_oficial", "grupo", "descricao_fonte",
            "texto_fonte_confere_prefixo", "competencia",
        )
    )


def _selecionar_termo(spark: SparkSession, caminho: str, versao: int, sha256: str) -> DataFrame:
    """Só o sha256 pedido, SELECIONADO na Silver antes de publicar."""
    return _ler_versao(spark, caminho, versao).where(F.col("sha256_arquivo") == sha256).select(*TERMO_COLUNAS)


# ---------------------------------------------------------------- publicação de uma dimensão


def _publicar_dimensao(
    spark: SparkSession,
    tabela: str,
    caminho: str,
    esperado: DataFrame,
    chave: str,
    valor: str,
    schema: StructType,
    colunas,
    unicidade: str,
    meta: dict,
    id_execucao: str,
) -> Dimensao:
    """Confere a seleção, grava UM commit com replaceWhere e reconfere o gravado."""
    linhas = esperado.count()
    if linhas == 0:
        return Dimensao(NAO_MEDIDO, f"SILVER_SEM_LINHAS:{tabela}", tabela=caminho)
    distintos = esperado.select(unicidade).distinct().count()
    if distintos != linhas:
        return Dimensao(DIVERGE, f"{unicidade.upper()}_DUPLICADO:{tabela}", tabela=caminho, linhas=linhas,
                        detalhe={"linhas": linhas, "distintos": distintos})

    condicao = f"{chave} = '{valor}'"
    _garantir_tabela(spark, caminho, schema, chave)
    versao_anterior = _versao_atual(spark, caminho)
    existia = _ler_commit(spark, caminho, versao_anterior, condicao, colunas).limit(1).count() > 0
    meta = {**meta, "tabela": tabela, "estado": INTEGRO, "id_execucao": id_execucao}
    (
        esperado.write.format("delta").mode("overwrite")
        .option("replaceWhere", condicao)
        .option("userMetadata", json.dumps(meta, ensure_ascii=False, sort_keys=True))
        .save(caminho)
    )
    versao = _versao_do_commit(spark, caminho, id_execucao)
    if versao is None:
        _reverter(spark, caminho, condicao, existia, versao_anterior, meta)
        return Dimensao(DIVERGE, "COMMIT_NAO_ENCONTRADO", tabela=caminho, linhas=linhas)
    lido = _ler_commit(spark, caminho, versao, condicao, colunas)
    so_esperado = esperado.select(*colunas).exceptAll(lido).count()
    so_lido = lido.exceptAll(esperado.select(*colunas)).count()
    detalhe = {"versao": versao, "so_no_esperado": so_esperado, "so_no_lido": so_lido}
    if so_esperado or so_lido:
        _reverter(spark, caminho, condicao, existia, versao_anterior, meta)
        return Dimensao(DIVERGE, "RECONFERENCIA_DIVERGE", tabela=caminho, versao=versao, linhas=linhas,
                        detalhe=detalhe)
    return Dimensao(INTEGRO, tabela=caminho, versao=versao, linhas=linhas, detalhe=detalhe)


def _estado_geral(*dimensoes: Dimensao) -> str:
    estados = {d.estado for d in dimensoes}
    for estado in _GRAVIDADE:
        if estado in estados:
            return estado
    return INTEGRO


# ---------------------------------------------------------------- publicar


def publicar(
    spark: SparkSession,
    silver_especie: str,
    silver_glossario: str,
    destino: str,
    competencia: str,
    sha256_glossario: str,
    id_execucao: Optional[str] = None,
) -> Resultado:
    """Publica dim_especie (da competência) e dim_termo (do sha256) na Gold, lidas SÓ da Silver."""
    if not re.fullmatch(r"[A-Za-z0-9._-]+", competencia or ""):
        return Resultado(ERRO_LEITURA, str(competencia), str(sha256_glossario), motivo="COMPETENCIA_INVALIDA")
    if not re.fullmatch(r"[A-Za-z0-9]+", sha256_glossario or ""):
        return Resultado(ERRO_LEITURA, competencia, str(sha256_glossario), motivo="SHA256_INVALIDO")

    id_execucao = id_execucao or uuid.uuid4().hex
    raiz = destino.rstrip("/")

    # As versões das duas tabelas Silver são fixadas ANTES de qualquer seleção.
    versoes = {}
    for nome, caminho in (("especie", silver_especie), ("glossario", silver_glossario)):
        try:
            versoes[nome] = _versao_atual(spark, caminho) if _e_delta(spark, caminho) else None
        except Exception as exc:  # noqa: BLE001 — não conseguiu medir: não é NAO_MEDIDO
            versoes[nome] = exc
    v_esp, v_glo = versoes["especie"], versoes["glossario"]
    r = Resultado(
        INTEGRO, competencia, sha256_glossario, id_execucao=id_execucao,
        versao_silver_especie=v_esp if isinstance(v_esp, int) else None,
        versao_silver_glossario=v_glo if isinstance(v_glo, int) else None,
    )
    linhagem = {
        "competencia": competencia,
        "versao_silver_especie": r.versao_silver_especie,
        "versao_silver_glossario": r.versao_silver_glossario,
    }

    def _dimensao(versao, silver, selecionar, **publicacao) -> Dimensao:
        if versao is None:
            return Dimensao(NAO_MEDIDO, "SILVER_AUSENTE", tabela=silver)
        if isinstance(versao, Exception):
            return Dimensao(ERRO_LEITURA, f"{type(versao).__name__}: {versao}")
        try:
            return _publicar_dimensao(spark, esperado=selecionar(versao), meta=linhagem,
                                      id_execucao=id_execucao, **publicacao)
        except Exception as exc:  # noqa: BLE001 — não conseguiu medir: não é NAO_MEDIDO
            return Dimensao(ERRO_LEITURA, f"{type(exc).__name__}: {exc}")

    especie = _dimensao(
        v_esp, silver_especie, lambda v: _selecionar_especie(spark, silver_especie, v, competencia),
        tabela="dim_especie", caminho=f"{raiz}/dim_especie", chave="competencia", valor=competencia,
        schema=ESPECIE_SCHEMA, colunas=ESPECIE_COLUNAS, unicidade="codigo",
    )
    termo = _dimensao(
        v_glo, silver_glossario, lambda v: _selecionar_termo(spark, silver_glossario, v, sha256_glossario),
        tabela="dim_termo", caminho=f"{raiz}/dim_termo", chave="sha256_arquivo", valor=sha256_glossario,
        schema=TERMO_SCHEMA, colunas=TERMO_COLUNAS, unicidade="termo",
    )
    return replace(r, estado=_estado_geral(especie, termo), dim_especie=especie, dim_termo=termo)
