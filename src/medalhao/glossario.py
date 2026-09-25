"""Silver do glossário: os termos do INSS conformados, lidos da Bronze da referência.

Lê a Bronze (`<bronze>/glossario`), nunca `_raw` nem a ontologia. A Bronze é lida UMA vez, numa versão
fixada no início, e só as linhas do `sha256_arquivo` pedido entram na conformação.

Conforma NESTA ORDEM: apara as pontas; descarta a linha de cabeçalho e as linhas com as DUAS células
vazias (contando os descartes, Regra 9); recusa termo vazio com descrição preenchida e termo repetido.
A descrição é o texto da fonte: só se aparam as pontas, nada se reescreve.

Estados: PUBLICADO | DIVERGE | NAO_MEDIDO | RECUSADO. Só PUBLICADO deixa a versão no destino.
"""

from __future__ import annotations

import json
import uuid
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

from medalhao import bronze

PUBLICADO = "PUBLICADO"
DIVERGE = "DIVERGE"
NAO_MEDIDO = "NAO_MEDIDO"
RECUSADO = "RECUSADO"

BRONZE_PADRAO = "s3a://bronze/pda/referencia"
DESTINO_PADRAO = "s3a://silver/pda/glossario"
TABELA_BRONZE = "glossario"
CABECALHO = "Nome"

COLUNAS = ("termo", "descricao", "sha256_arquivo")
ESQUEMA = StructType(
    [
        StructField("termo", StringType(), nullable=False),
        StructField("descricao", StringType()),
        StructField("sha256_arquivo", StringType(), nullable=False),
    ]
)


@dataclass(frozen=True)
class Resultado:
    estado: str
    motivo: str = ""
    tabela: Optional[str] = None
    versao: Optional[int] = None
    versao_bronze: Optional[int] = None
    linhas: int = 0
    descartes: Optional[Dict[str, int]] = None
    id_execucao: Optional[str] = None
    detalhe: Optional[dict] = None


class ConformacaoRecusada(Exception):
    """O glossário não se conforma — recusado, nunca gravado pela metade."""

    def __init__(self, motivo: str):
        super().__init__(motivo)
        self.motivo = motivo


def _aparar(texto: Optional[str]) -> str:
    return (texto or "").strip()


def conformar(registros: List[Tuple[Optional[str], Optional[str]]]) -> Tuple[List[Tuple[str, str]], Dict[str, int]]:
    """(termo, descricao) por termo e os descartes contados. Levanta ConformacaoRecusada."""
    aparadas = [(_aparar(a), _aparar(b)) for a, b in registros]
    vazias = sum(1 for a, b in aparadas if not a and not b)
    restantes = [(a, b) for a, b in aparadas if a or b]
    cabecalhos = sum(1 for a, _ in restantes if a == CABECALHO)
    termos = [(a, b) for a, b in restantes if a != CABECALHO]
    if any(not a for a, _ in termos):
        raise ConformacaoRecusada("TERMO_VAZIO")
    repetidos = sorted(t for t, n in Counter(a for a, _ in termos).items() if n > 1)
    if repetidos:
        raise ConformacaoRecusada(f"TERMO_REPETIDO: {repetidos}")
    return termos, {"cabecalho": cabecalhos, "vazias": vazias}


# ---------------------------------------------------------------- Delta


def _garantir_tabela(spark: SparkSession, caminho: str) -> None:
    from delta.tables import DeltaTable

    (
        DeltaTable.createIfNotExists(spark)
        .location(caminho)
        .addColumn("termo", StringType(), nullable=False)
        .addColumn("descricao", StringType())
        .addColumn("sha256_arquivo", StringType(), nullable=False)
        .partitionedBy("sha256_arquivo")
        .execute()
    )


def _e_delta(spark: SparkSession, caminho: str) -> bool:
    from delta.tables import DeltaTable

    try:
        return DeltaTable.isDeltaTable(spark, caminho)
    except Exception:  # noqa: BLE001 — caminho ilegível é o mesmo que ausente para esta pergunta
        return False


def _versao_do_commit(spark: SparkSession, caminho: str, id_execucao: str) -> Optional[int]:
    """A versão do PRÓPRIO commit, achada pelo id_execucao — nunca 'a última'."""
    achadas = []
    for versao, meta in bronze._historico(spark, caminho):
        try:
            corpo = json.loads(meta) if meta else None
        except ValueError:
            continue
        if isinstance(corpo, dict) and corpo.get("id_execucao") == id_execucao:
            achadas.append(versao)
    return max(achadas) if achadas else None


def _lidas(spark: SparkSession, caminho: str, versao: int, sha: str) -> DataFrame:
    return bronze._ler_versao(spark, caminho, versao).where(F.col("sha256_arquivo") == sha).select(*COLUNAS)


def _ler_da_bronze(spark: SparkSession, caminho: str, versao: int, sha: str) -> List[Tuple[Optional[str], Optional[str]]]:
    """A ÚNICA leitura da Bronze: a versão fixada, SÓ o sha256 pedido, na ordem das linhas."""
    lidas = (
        bronze._ler_versao(spark, caminho, versao)
        .where(F.col("sha256_arquivo") == sha)
        .orderBy("linha")
        .select("coluna_a", "coluna_b")
        .collect()
    )
    return [(r["coluna_a"], r["coluna_b"]) for r in lidas]


def _conferir(spark: SparkSession, caminho: str, versao: int, sha: str, esperado: DataFrame) -> Tuple[bool, dict]:
    """RELÊ a versão do próprio commit e compara o multiconjunto, nos DOIS sentidos."""
    lido = _lidas(spark, caminho, versao, sha)
    so_esperado = esperado.exceptAll(lido).count()
    so_lido = lido.exceptAll(esperado).count()
    return so_esperado == 0 and so_lido == 0, {
        "versao": versao, "so_no_esperado": so_esperado, "so_no_lido": so_lido,
    }


def _reverter(spark: SparkSession, caminho: str, sha: str, existia: bool, versao_anterior: int, meta: dict) -> None:
    """Desfaz SÓ a partição do sha256 — outra partição da mesma tabela não é tocada."""
    condicao = f"sha256_arquivo = '{sha}'"
    meta_json = json.dumps({**meta, "estado": "REVERTIDO"}, ensure_ascii=False, sort_keys=True)
    if existia:
        (
            _lidas(spark, caminho, versao_anterior, sha)
            .write.format("delta")
            .mode("overwrite")
            .option("replaceWhere", condicao)
            .option("userMetadata", meta_json)
            .save(caminho)
        )
        return
    chave = "spark.databricks.delta.commitInfo.userMetadata"
    spark.conf.set(chave, meta_json)
    try:
        bronze._delta_table(spark, caminho).delete(condicao)
    finally:
        spark.conf.unset(chave)


# ---------------------------------------------------------------- publicar


def publicar(
    spark: SparkSession,
    bronze_raiz: str,
    destino: str,
    sha256: str,
    sha256_aprovado: str,
    id_execucao: Optional[str] = None,
) -> Resultado:
    """Conforma o glossário do `sha256` pedido, lido da Bronze, e o grava na Silver com a linhagem.

    sha256 diferente do aprovado recusa SEM ler nem gravar; termo vazio ou repetido recusa SEM gravar;
    sha256 ausente da Bronze ou sem termo é NAO_MEDIDO; falha da reconferência reverte e devolve DIVERGE.
    """
    if sha256 != sha256_aprovado:
        return Resultado(RECUSADO, "GLOSSARIO_NAO_APROVADO")

    origem = f"{bronze_raiz.rstrip('/')}/{TABELA_BRONZE}"
    if not _e_delta(spark, origem):
        return Resultado(NAO_MEDIDO, "BRONZE_AUSENTE")
    versao_bronze = bronze._versao_atual(spark, origem)
    registros = _ler_da_bronze(spark, origem, versao_bronze, sha256)
    if not registros:
        return Resultado(NAO_MEDIDO, "SHA256_AUSENTE_DA_BRONZE", versao_bronze=versao_bronze)
    try:
        termos, descartes = conformar(registros)
    except ConformacaoRecusada as exc:
        return Resultado(RECUSADO, exc.motivo, versao_bronze=versao_bronze)
    if not termos:
        return Resultado(NAO_MEDIDO, "NENHUM_TERMO", versao_bronze=versao_bronze, descartes=descartes)

    id_execucao = id_execucao or uuid.uuid4().hex
    caminho = destino.rstrip("/")
    meta = {
        "versao_bronze": versao_bronze,
        "sha256": sha256,
        "descartes": descartes,
        "id_execucao": id_execucao,
        "linhas": len(termos),
    }
    esperado = spark.createDataFrame([(t, d, sha256) for t, d in termos], ESQUEMA)

    _garantir_tabela(spark, caminho)
    versao_anterior = bronze._versao_atual(spark, caminho)
    existia = _lidas(spark, caminho, versao_anterior, sha256).limit(1).count() > 0
    (
        esperado.write.format("delta")
        .mode("overwrite")
        .option("replaceWhere", f"sha256_arquivo = '{sha256}'")
        .option("userMetadata", json.dumps(meta, ensure_ascii=False, sort_keys=True))
        .save(caminho)
    )
    versao = _versao_do_commit(spark, caminho, id_execucao)
    if versao is None:
        return Resultado(
            DIVERGE, "COMMIT_NAO_ENCONTRADO", tabela=caminho, versao_bronze=versao_bronze,
            descartes=descartes, id_execucao=id_execucao,
        )
    ok, detalhe = _conferir(spark, caminho, versao, sha256, esperado)
    if not ok:
        _reverter(spark, caminho, sha256, existia, versao_anterior, meta)
        return Resultado(
            DIVERGE, "RECONFERENCIA_DIVERGE", tabela=caminho, versao=versao, versao_bronze=versao_bronze,
            linhas=len(termos), descartes=descartes, id_execucao=id_execucao, detalhe=detalhe,
        )
    return Resultado(
        PUBLICADO, tabela=caminho, versao=versao, versao_bronze=versao_bronze, linhas=len(termos),
        descartes=descartes, id_execucao=id_execucao, detalhe=detalhe,
    )
