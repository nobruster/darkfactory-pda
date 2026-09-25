"""Bronze da referência: as linhas do dicionário e do glossário, COMO VIERAM, lidas do landing.

Lê os bytes da partição `sha256=<sha256>` do landing — nunca da origem bruta —, confere que o sha256
dos bytes é o da `_PROCEDENCIA.json` e o do nome da partição, e só então grava em Delta.

A planilha é lida por um parser PRÓPRIO (zipfile sobre BytesIO e xml, só a biblioteca padrão):
o leitor genérico de planilha do repositório descarta as linhas sem valor e não devolve o número da linha. Aqui cada
elemento `<row>` vira um registro, com o número que o XML traz no atributo `r`, texto sem trim
e célula ausente nula. O cabeçalho e as linhas sem valor entram: a Bronze não filtra, a Silver
conforma.

Estados: PUBLICADO | DIVERGE | NAO_MEDIDO | RECUSADO. Só PUBLICADO deixa a versão no destino.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import uuid
import zipfile
from dataclasses import dataclass
from typing import List, Optional, Tuple
from xml.etree import ElementTree as ET

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType, StringType, StructField, StructType

PUBLICADO = "PUBLICADO"
DIVERGE = "DIVERGE"
NAO_MEDIDO = "NAO_MEDIDO"
RECUSADO = "RECUSADO"

LANDING_PADRAO = "s3a://landing/pda/referencia"
DESTINO_PADRAO = "s3a://bronze/pda/referencia"
PROCEDENCIA = "_PROCEDENCIA.json"

DICIONARIO = "dicionario-especies-beneficio.xlsx"
GLOSSARIO = "glossario-beneficios-emitidos.xlsx"
TABELAS = {DICIONARIO: "dicionario_especies", GLOSSARIO: "glossario"}

COLUNAS = ("linha", "coluna_a", "coluna_b", "arquivo", "sha256_arquivo")
ESQUEMA = StructType(
    [
        StructField("linha", IntegerType(), nullable=False),
        StructField("coluna_a", StringType()),
        StructField("coluna_b", StringType()),
        StructField("arquivo", StringType(), nullable=False),
        StructField("sha256_arquivo", StringType(), nullable=False),
    ]
)

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_NS_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_NS_PACOTE = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_SHA256 = re.compile(r"[0-9a-f]{64}")


class PlanilhaRecusada(Exception):
    """O .xlsx não é uma planilha única e legível — recusada, nunca lida pela metade."""


@dataclass(frozen=True)
class Resultado:
    estado: str
    motivo: str = ""
    tabela: Optional[str] = None
    particao: Optional[str] = None
    versao: Optional[int] = None
    linhas: int = 0
    id_execucao: Optional[str] = None
    detalhe: Optional[dict] = None


# ---------------------------------------------------------------- bytes do landing


def _caminho(spark: SparkSession, uri: str):
    jvm = spark._jvm
    caminho = jvm.org.apache.hadoop.fs.Path(uri)
    return caminho, caminho.getFileSystem(spark._jsc.hadoopConfiguration())


def _ler_bytes(spark: SparkSession, uri: str) -> Optional[bytes]:
    """Os bytes do objeto, ou None se ele não existe."""
    caminho, fs = _caminho(spark, uri)
    if not fs.exists(caminho):
        return None
    fs.setVerifyChecksum(False)
    saida = spark._jvm.java.io.ByteArrayOutputStream()
    entrada = fs.open(caminho)
    try:
        spark._jvm.org.apache.hadoop.io.IOUtils.copyBytes(entrada, saida, 65536, False)
    finally:
        entrada.close()
    return bytes(saida.toByteArray())


def _sha256(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


# ---------------------------------------------------------------- parser da planilha


def _texto(no) -> str:
    return "".join(t.text or "" for t in no.iter(f"{_NS}t"))


def _alvo_da_planilha(z: zipfile.ZipFile) -> str:
    """O caminho da ÚNICA planilha do pacote; qualquer outra contagem é recusa."""
    try:
        livro = ET.fromstring(z.read("xl/workbook.xml"))
    except (KeyError, ET.ParseError) as exc:
        raise PlanilhaRecusada(f"workbook ilegível: {type(exc).__name__}") from exc
    planilhas = list(livro.iter(f"{_NS}sheet"))
    if len(planilhas) != 1:
        raise PlanilhaRecusada(f"{len(planilhas)} planilhas — exatamente uma é exigida")
    id_rel = planilhas[0].get(f"{_NS_REL}id")
    try:
        relacoes = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    except (KeyError, ET.ParseError) as exc:
        raise PlanilhaRecusada(f"relações do workbook ilegíveis: {type(exc).__name__}") from exc
    for r in relacoes.iter(f"{_NS_PACOTE}Relationship"):
        if r.get("Id") == id_rel:
            alvo = r.get("Target", "")
            return alvo.lstrip("/") if alvo.startswith("/") else "xl/" + alvo
    raise PlanilhaRecusada(f"planilha {id_rel!r} sem relação no workbook")


def _compartilhadas(z: zipfile.ZipFile) -> List[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    raiz = ET.fromstring(z.read("xl/sharedStrings.xml"))
    return [_texto(si) for si in raiz.iter(f"{_NS}si")]


def _valor(celula, compartilhadas: List[str]) -> Optional[str]:
    tipo = celula.get("t")
    if tipo == "inlineStr":
        return _texto(celula)
    v = celula.find(f"{_NS}v")
    if v is None or v.text is None:
        return None
    return compartilhadas[int(v.text)] if tipo == "s" else v.text


def ler_planilha(dados: bytes) -> List[Tuple[int, Optional[str], Optional[str]]]:
    """(linha, coluna_a, coluna_b) de CADA `<row>`, na ordem do XML — sem filtrar, sem aparar."""
    try:
        with zipfile.ZipFile(io.BytesIO(dados)) as z:
            planilha = ET.fromstring(z.read(_alvo_da_planilha(z)))
            compartilhadas = _compartilhadas(z)
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        raise PlanilhaRecusada(f"planilha ilegível: {type(exc).__name__}") from exc
    linhas = []
    for row in planilha.iter(f"{_NS}row"):
        numero = row.get("r")
        if numero is None or not numero.isdigit():
            raise PlanilhaRecusada(f"<row> sem número no atributo r: {numero!r}")
        colunas = {"A": None, "B": None}
        for c in row.iter(f"{_NS}c"):
            letra = re.match(r"[A-Z]+", c.get("r", ""))
            if letra and letra.group(0) in colunas:
                colunas[letra.group(0)] = _valor(c, compartilhadas)
        linhas.append((int(numero), colunas["A"], colunas["B"]))
    return linhas


# ---------------------------------------------------------------- Delta


def _delta_table(spark: SparkSession, caminho: str):
    from delta.tables import DeltaTable

    return DeltaTable.forPath(spark, caminho)


def _garantir_tabela(spark: SparkSession, caminho: str) -> None:
    from delta.tables import DeltaTable

    (
        DeltaTable.createIfNotExists(spark)
        .location(caminho)
        .addColumn("linha", IntegerType(), nullable=False)
        .addColumn("coluna_a", StringType())
        .addColumn("coluna_b", StringType())
        .addColumn("arquivo", StringType(), nullable=False)
        .addColumn("sha256_arquivo", StringType(), nullable=False)
        .partitionedBy("sha256_arquivo")
        .execute()
    )


def _versao_do_commit(spark: SparkSession, caminho: str, id_execucao: str) -> Optional[int]:
    """A versão do PRÓPRIO commit, achada pelo id_execucao — nunca 'a última', que pode ser de outro."""
    historico = _delta_table(spark, caminho).history().select("version", "userMetadata").collect()
    for r in sorted(historico, key=lambda h: h["version"], reverse=True):
        try:
            meta = json.loads(r["userMetadata"] or "")
        except ValueError:
            continue
        if isinstance(meta, dict) and meta.get("id_execucao") == id_execucao:
            return int(r["version"])
    return None


def _versao_atual(spark: SparkSession, caminho: str) -> int:
    return int(_delta_table(spark, caminho).history(1).select("version").first()[0])


def _lidas(spark: SparkSession, caminho: str, versao: int, sha: str) -> DataFrame:
    return (
        spark.read.format("delta")
        .option("versionAsOf", versao)
        .load(caminho)
        .where(F.col("sha256_arquivo") == sha)
        .select(*COLUNAS)
    )


def _conferir(spark: SparkSession, caminho: str, versao: int, sha: str, esperado: DataFrame) -> Tuple[bool, dict]:
    """RELÊ a versão commitada e compara o multiconjunto de todas as colunas, nos DOIS sentidos."""
    lido = _lidas(spark, caminho, versao, sha)
    so_esperado = esperado.exceptAll(lido).count()
    so_lido = lido.exceptAll(esperado).count()
    detalhe = {"versao": versao, "so_no_esperado": so_esperado, "so_no_lido": so_lido}
    return so_esperado == 0 and so_lido == 0, detalhe


def _reverter(spark: SparkSession, caminho: str, sha: str, existia: bool, versao_anterior: int, meta: dict) -> None:
    """Desfaz SÓ a partição do arquivo — outra partição da mesma tabela não é tocada."""
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
        _delta_table(spark, caminho).delete(condicao)
    finally:
        spark.conf.unset(chave)


# ---------------------------------------------------------------- publicar


def _prova_do_landing(spark: SparkSession, particao: str, arquivo: str) -> Tuple[Optional[bytes], Optional[dict], str]:
    """(bytes, prova, motivo). Sem motivo, os dois vieram."""
    dados = _ler_bytes(spark, f"{particao}/{arquivo}")
    corpo = _ler_bytes(spark, f"{particao}/{PROCEDENCIA}")
    if dados is None or corpo is None:
        return None, None, "PARTICAO_AUSENTE_NO_LANDING"
    try:
        prova = json.loads(corpo.decode("utf-8"))
    except ValueError:
        return dados, None, "PROVA_ILEGIVEL"
    if not isinstance(prova, dict):
        return dados, None, "PROVA_ILEGIVEL"
    return dados, prova, ""


def publicar(
    spark: SparkSession,
    landing: str,
    destino: str,
    arquivo: str,
    sha256: str,
    id_execucao: Optional[str] = None,
) -> Resultado:
    """Lê `arquivo` da partição `sha256=<sha256>` do landing, confere a prova e publica na Bronze.

    Divergência de sha256 recusa SEM gravar; planilha sem linha é NAO_MEDIDO; falha da
    reconferência reverte a partição e devolve DIVERGE.
    """
    if arquivo not in TABELAS:
        return Resultado(RECUSADO, "ARQUIVO_DESCONHECIDO")
    if not _SHA256.fullmatch(sha256 or ""):
        return Resultado(RECUSADO, "SHA256_INVALIDO")

    particao = f"{landing.rstrip('/')}/{arquivo.rsplit('.', 1)[0]}/sha256={sha256}"
    dados, prova, motivo = _prova_do_landing(spark, particao, arquivo)
    if motivo == "PARTICAO_AUSENTE_NO_LANDING":
        return Resultado(NAO_MEDIDO, motivo, particao=particao)
    if prova is None:
        return Resultado(RECUSADO, motivo, particao=particao)
    if _sha256(dados) != sha256 or prova.get("sha256") != sha256 or prova.get("arquivo") != arquivo:
        return Resultado(RECUSADO, "SHA256_DIVERGENTE", particao=particao)

    try:
        registros = ler_planilha(dados)
    except PlanilhaRecusada as exc:
        return Resultado(RECUSADO, f"PLANILHA_RECUSADA: {exc}", particao=particao)
    if not registros:
        return Resultado(NAO_MEDIDO, "PLANILHA_SEM_LINHAS", particao=particao)

    id_execucao = id_execucao or uuid.uuid4().hex
    caminho = f"{destino.rstrip('/')}/{TABELAS[arquivo]}"
    meta = {
        "particao_landing": particao,
        "sha256_prova": prova["sha256"],
        "id_execucao": id_execucao,
        "linhas": len(registros),
        "arquivo": arquivo,
    }
    esperado = spark.createDataFrame([(n, a, b, arquivo, sha256) for n, a, b in registros], ESQUEMA)

    _garantir_tabela(spark, caminho)
    existia = _lidas(spark, caminho, _versao_atual(spark, caminho), sha256).limit(1).count() > 0
    versao_anterior = _versao_atual(spark, caminho)
    (
        esperado.write.format("delta")
        .mode("overwrite")
        .option("replaceWhere", f"sha256_arquivo = '{sha256}'")
        .option("userMetadata", json.dumps(meta, ensure_ascii=False, sort_keys=True))
        .save(caminho)
    )
    versao = _versao_do_commit(spark, caminho, id_execucao)
    if versao is None:
        return Resultado(DIVERGE, "COMMIT_NAO_ENCONTRADO", tabela=caminho, particao=particao, id_execucao=id_execucao)
    ok, detalhe = _conferir(spark, caminho, versao, sha256, esperado)
    if not ok:
        _reverter(spark, caminho, sha256, existia, versao_anterior, meta)
        return Resultado(
            DIVERGE, "RECONFERENCIA_DIVERGE", tabela=caminho, particao=particao, versao=versao,
            linhas=len(registros), id_execucao=id_execucao, detalhe=detalhe,
        )
    return Resultado(
        PUBLICADO, tabela=caminho, particao=particao, versao=versao, linhas=len(registros),
        id_execucao=id_execucao, detalhe=detalhe,
    )
