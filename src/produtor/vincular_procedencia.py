"""Vincula a partição da landing ao CSV de origem e grava a prova ao lado dela.

O produtor grava com append e nunca prova de onde os bytes vieram. Aqui, sem
tocar em nenhum objeto de dado, o vinculador confere que a partição É a
transformação do CSV declarado no contrato e grava `_PROCEDENCIA.json` com o
que viu: hash do CSV, MANIFESTO dos objetos (nome, tamanho, sha256) e os cinco
controles.

Ordem que importa: o manifesto é calculado ANTES de comparar e recalculado
ANTES de gravar — uma partição que muda no meio da conferência não é a que foi
conferida. Em qualquer divergência nada é gravado, e uma prova anterior nunca
é sobrescrita em silêncio.

Token: PROCEDENCIA=GRAVADO|INTEGRO|DIVERGE|NAO_MEDIDO
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType, StringType, StructField, StructType

from produtor import gramatica

NOME_PROVA = "_PROCEDENCIA.json"
GRAVADO, INTEGRO, DIVERGE, NAO_MEDIDO = "GRAVADO", "INTEGRO", "DIVERGE", "NAO_MEDIDO"

_ENCODING_JVM = {
    "latin-1": "ISO-8859-1", "latin1": "ISO-8859-1",
    "iso-8859-1": "ISO-8859-1", "utf-8": "UTF-8", "utf8": "UTF-8",
}
_COLUNAS = ("especie_codigo", "especie_descricao", "vl_liquido")


@dataclass
class Vinculo:
    veredito: str
    motivo: str = ""
    diferencas: list = field(default_factory=list)
    prova: Optional[dict] = None


def _fim(veredito: str, motivo: str = "", diferencas=None, prova=None) -> Vinculo:
    return Vinculo(veredito, motivo, list(diferencas or []), prova)


class _Armazem:
    """Objetos do lago pelo Hadoop FS — o mesmo caminho serve a s3a:// e file://."""

    def __init__(self, spark):
        self._jvm = spark._jvm
        self._conf = spark._jsc.hadoopConfiguration()

    def _caminho(self, uri: str):
        return self._jvm.org.apache.hadoop.fs.Path(uri)

    def _fs(self, uri: str):
        fs = self._caminho(uri).getFileSystem(self._conf)
        # o sha256 do manifesto é a verificação; o .crc do FS local levantaria
        # ChecksumException ao ler um objeto alterado em vez de deixar o
        # manifesto acusar a diferença
        fs.setVerifyChecksum(False)
        return fs

    def existe(self, uri: str) -> bool:
        return bool(self._fs(uri).exists(self._caminho(uri)))

    def listar(self, uri: str) -> dict:
        """{nome relativo: tamanho} de todo arquivo sob o prefixo."""
        fs = self._fs(uri)
        base = fs.makeQualified(self._caminho(uri)).toUri().getPath().rstrip("/")
        achados: dict = {}
        pendentes = [self._caminho(uri)]
        while pendentes:
            for st in fs.listStatus(pendentes.pop()):
                if st.isDirectory():
                    pendentes.append(st.getPath())
                else:
                    nome = st.getPath().toUri().getPath()[len(base):].lstrip("/")
                    achados[nome] = int(st.getLen())
        return achados

    def sha256(self, uri: str) -> str:
        jvm = self._jvm
        resumo = jvm.java.security.MessageDigest.getInstance("SHA-256")
        saida = jvm.java.security.DigestOutputStream(
            jvm.java.io.OutputStream.nullOutputStream(), resumo)
        entrada = self._fs(uri).open(self._caminho(uri))
        try:
            jvm.org.apache.hadoop.io.IOUtils.copyBytes(entrada, saida, 65536, False)
        finally:
            entrada.close()
        return bytes(resumo.digest()).hex()

    def ler(self, uri: str) -> bytes:
        jvm = self._jvm
        saida = jvm.java.io.ByteArrayOutputStream()
        entrada = self._fs(uri).open(self._caminho(uri))
        try:
            jvm.org.apache.hadoop.io.IOUtils.copyBytes(entrada, saida, 65536, False)
        finally:
            entrada.close()
        return bytes(saida.toByteArray())

    def gravar_novo(self, uri: str, dados: bytes) -> None:
        """Cria sem sobrescrever: se o objeto existir, levanta."""
        saida = self._fs(uri).create(self._caminho(uri), False)
        try:
            saida.write(bytearray(dados))
        finally:
            saida.close()


def _uri(local_ou_uri: str) -> str:
    if "://" in local_ou_uri:
        return local_ou_uri.rstrip("/")
    return "file://" + os.path.abspath(local_ou_uri).rstrip("/")


def _sha256_arquivo(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def _manifesto(armazem: _Armazem, particao: str, ignorados) -> list:
    """Nome, tamanho e sha256 de todo objeto de dado. Isenções nomeadas uma a
    uma — um `_extra.parquet` é objeto a mais, não auxiliar."""
    isentos = set(ignorados) | {NOME_PROVA}
    return [
        {"nome": nome, "tamanho": tam, "sha256": armazem.sha256(f"{particao}/{nome}")}
        for nome, tam in sorted(armazem.listar(particao).items())
        if nome not in isentos
    ]


def ler_fonte(spark, csv, contrato):
    """Lê o CSV pelas posições do layout; valor em DecimalType, nunca float."""
    layout, pol = contrato.layout, contrato.politica_decimal
    esquema = StructType([
        StructField(f"c{i}", StringType(), True) for i in range(layout.total_colunas)
    ])
    bruto = (
        spark.read.option("header", "true")
        .option("sep", layout.separador)
        .option("encoding", _ENCODING_JVM.get(layout.encoding.lower(), layout.encoding))
        .schema(esquema)
        .csv(str(csv))
    )
    valor = gramatica.valor_decimal(
        F.col(f"c{layout.posicoes['vl_liquido']}"), pol.precisao, pol.escala)
    return bruto.select(
        F.trim(F.col(f"c{layout.posicoes['especie']}")).alias(_COLUNAS[0]),
        F.col(f"c{layout.posicoes['descricao_especie']}").alias(_COLUNAS[1]),
        valor.alias(_COLUNAS[2]),
    )


def _controles(df) -> dict:
    a = df.agg(
        F.count(F.lit(1)).alias("n"),
        F.sum(F.when(F.col("vl_liquido").isNull(), 1).otherwise(0)).alias("inv"),
        F.sum("vl_liquido").alias("soma"),
        F.min("vl_liquido").alias("min"),
        F.max("vl_liquido").alias("max"),
    ).collect()[0]
    return {
        "count_linhas": str(int(a["n"] or 0)),
        "linhas_invalidas": str(int(a["inv"] or 0)),
        "sum_vl_liquido": str(a["soma"]) if a["soma"] is not None else "0",
        "min_vl_liquido": str(a["min"]) if a["min"] is not None else "",
        "max_vl_liquido": str(a["max"]) if a["max"] is not None else "",
    }


def _comparar(fonte, particao) -> Optional[str]:
    """None se os multiconjuntos são iguais; senão o motivo. exceptAll vazio +
    contagens iguais provam a igualdade."""
    if fonte.count() != particao.count():
        return "CONTAGEM_DIFERE"
    if fonte.exceptAll(particao).count() != 0 or particao.exceptAll(fonte).count() != 0:
        return "CONTEUDO_DIFERE"
    return None


def _diferencas_manifesto(antigo: list, novo: list) -> list:
    a = {o["nome"]: o for o in antigo}
    n = {o["nome"]: o for o in novo}
    difs = [f"objeto acrescentado: {k}" for k in sorted(n.keys() - a.keys())]
    difs += [f"objeto removido: {k}" for k in sorted(a.keys() - n.keys())]
    difs += [f"objeto alterado: {k}" for k in sorted(a.keys() & n.keys()) if a[k] != n[k]]
    return difs


def _gravar_prova(armazem: _Armazem, uri: str, prova: dict) -> None:
    dados = json.dumps(prova, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8")
    armazem.gravar_novo(uri, dados)


def vincular(spark, contrato, csv, *, competencia: Optional[str] = None,
             raiz: Optional[str] = None, id_execucao: Optional[str] = None) -> Vinculo:
    """Confere a partição contra o CSV e grava `_PROCEDENCIA.json` — só se tudo bater."""
    if isinstance(contrato, str) or contrato is None:
        return _fim(NAO_MEDIDO, "CONTRATO_NAO_MEDIDO")
    competencia = competencia or contrato.competencia
    if not re.fullmatch(r"[A-Za-z0-9._-]+", competencia or ""):
        return _fim(NAO_MEDIDO, "COMPETENCIA_INVALIDA")
    if contrato.competencia != competencia:
        return _fim(NAO_MEDIDO, "CONTRATO_DE_OUTRA_COMPETENCIA")
    if contrato.particionamento is None:
        return _fim(NAO_MEDIDO, "CONTRATO_SEM_PARTICIONAMENTO")
    hash_contrato = contrato.procedencia.hash_csv_sha256
    if not hash_contrato:
        return _fim(NAO_MEDIDO, "CONTRATO_SEM_HASH_DO_CSV")
    csv = Path(csv)
    if not csv.is_file():
        return _fim(NAO_MEDIDO, "CSV_AUSENTE")

    part = contrato.particionamento
    base = _uri(raiz) if raiz else part.caminho.rstrip("/")
    particao = f"{base}/{part.chave}={competencia}"
    ignorados = part.objetos_auxiliares_ignorados
    armazem = _Armazem(spark)
    if not armazem.existe(particao):
        return _fim(NAO_MEDIDO, "PARTICAO_AUSENTE")

    manifesto = _manifesto(armazem, particao, ignorados)
    hash_csv = _sha256_arquivo(csv)
    if hash_csv != hash_contrato:
        return _fim(DIVERGE, "HASH_DO_CSV_DIVERGE",
                    [f"contrato {hash_contrato} != csv {hash_csv}"])
    if not manifesto:
        return _fim(NAO_MEDIDO, "PARTICAO_SEM_OBJETOS_DE_DADO")

    uri_prova = f"{particao}/{NOME_PROVA}"
    anterior = None
    if armazem.existe(uri_prova):
        try:
            anterior = json.loads(armazem.ler(uri_prova).decode("utf-8"))
            anterior["manifesto"], anterior["controles"]
        except (ValueError, KeyError, TypeError):
            return _fim(DIVERGE, "PROVA_ANTERIOR_ILEGIVEL", [f"{NOME_PROVA} não é uma prova válida"])
        difs = []
        if anterior.get("competencia") != competencia:
            difs.append("competência difere")
        if anterior.get("csv_sha256") != hash_csv:
            difs.append("hash do CSV difere")
        difs += _diferencas_manifesto(anterior["manifesto"], manifesto)
        if difs:
            return _fim(DIVERGE, "PROVA_ANTERIOR_DIVERGE", difs)

    spark.conf.set("spark.sql.ansi.enabled", "true")
    fonte = ler_fonte(spark, csv, contrato)
    lida = spark.read.parquet(particao).select(*_COLUNAS)
    if not isinstance(lida.schema["vl_liquido"].dataType, DecimalType):
        return _fim(DIVERGE, "VALOR_DA_PARTICAO_NAO_E_DECIMAL",
                    [f"vl_liquido é {lida.schema['vl_liquido'].dataType.simpleString()}"])
    pol = contrato.politica_decimal
    lida = lida.withColumn("vl_liquido", F.col("vl_liquido").cast(DecimalType(pol.precisao, pol.escala)))

    if fonte.limit(1).count() == 0 or lida.limit(1).count() == 0:
        return _fim(NAO_MEDIDO, "ZERO_LINHAS")
    motivo = _comparar(fonte, lida)
    if motivo:
        return _fim(DIVERGE, motivo)

    controles = _controles(lida)
    if anterior is not None:
        if anterior["controles"] != controles:
            return _fim(DIVERGE, "PROVA_ANTERIOR_DIVERGE", ["controles diferem"])
        return _fim(INTEGRO, prova=anterior)

    if _manifesto(armazem, particao, ignorados) != manifesto:
        return _fim(DIVERGE, "MANIFESTO_MUDOU_ANTES_DE_GRAVAR")

    prova = {
        "competencia": competencia,
        "csv_nome": csv.name,
        "csv_sha256": hash_csv,
        "manifesto": manifesto,
        "controles": controles,
        "id_execucao": id_execucao,
        "gravado_em": datetime.now(timezone.utc).isoformat(),
    }
    _gravar_prova(armazem, uri_prova, prova)
    if json.loads(armazem.ler(uri_prova).decode("utf-8")) != prova:
        return _fim(DIVERGE, "RELEITURA_DIVERGE")
    return _fim(GRAVADO, prova=prova)
