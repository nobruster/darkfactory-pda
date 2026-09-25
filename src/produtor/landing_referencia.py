"""Põe no landing, COMO VIERAM, os dois arquivos de referência do INSS.

O landing guarda a fonte: os bytes do .xlsx, iguais aos de `_raw`, com a prova
de procedência ao lado. Nada é convertido. Este é o único módulo que lê `_raw`;
as camadas seguintes leem a anterior.

Cada arquivo é INDEPENDENTE e tem o seu resultado. Antes de copiar, o sha256
dos bytes é conferido contra a linha do CHECKSUMS.txt (casada pelo NOME). Depois
de gravar, os bytes são RELIDOS do destino e o sha256 é conferido de novo.

Nada é sobrescrito nem apagado — nem a prova é recriada. Bytes diferentes, bytes
sem prova (tentativa interrompida), prova sem bytes ou prova que não confere
com os bytes devolvem DIVERGE; a retomada é decisão do dono.

Token por arquivo: GRAVADO | INTEGRO | DIVERGE | NAO_MEDIDO | RECUSADO
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from py4j.protocol import Py4JJavaError

DESTINO_PADRAO = "s3a://landing/pda/referencia"
ORIGEM_PADRAO = "/dados/_raw"
ARQUIVOS = (
    "dicionario-especies-beneficio.xlsx",
    "glossario-beneficios-emitidos.xlsx",
)
PROCEDENCIA = "_PROCEDENCIA.json"

GRAVADO = "GRAVADO"
INTEGRO = "INTEGRO"
DIVERGE = "DIVERGE"
NAO_MEDIDO = "NAO_MEDIDO"
RECUSADO = "RECUSADO"


def _sha256(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def _checksums(origem: Path) -> dict[str, str]:
    """`<sha256>  _raw/<arquivo>` → {arquivo: sha256}, casado pelo nome."""
    arquivo = origem / "CHECKSUMS.txt"
    if not arquivo.is_file():
        return {}
    achados: dict[str, str] = {}
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        partes = linha.split(None, 1)
        if len(partes) == 2:
            achados[Path(partes[1].strip().lstrip("*")).name] = partes[0].lower()
    return achados


class _Destino:
    """O FileSystem do Hadoop por trás de um caminho (s3a://, file://, local)."""

    def __init__(self, spark, base: str):
        self._jvm = spark._jvm
        self._conf = spark._jsc.hadoopConfiguration()
        self._base = base.rstrip("/")

    def _path(self, uri: str):
        return self._jvm.org.apache.hadoop.fs.Path(uri)

    def _fs(self, uri: str):
        return self._path(uri).getFileSystem(self._conf)

    def existe(self, uri: str) -> bool:
        return bool(self._fs(uri).exists(self._path(uri)))

    def ler(self, uri: str) -> bytes:
        saida = self._jvm.java.io.ByteArrayOutputStream()
        entrada = self._fs(uri).open(self._path(uri))
        self._jvm.org.apache.hadoop.io.IOUtils.copyBytes(entrada, saida, 4096, True)
        return bytes(saida.toByteArray())

    def criar(self, uri: str, dados: bytes) -> None:
        # overwrite=False: se alguém entrou no meio, a criação falha em vez de sobrescrever
        fluxo = self._fs(uri).create(self._path(uri), False)
        try:
            fluxo.write(bytearray(dados))
        finally:
            fluxo.close()

    def pasta(self, arquivo: str, sha: str) -> str:
        return self._base + "/" + Path(arquivo).stem + "/sha256=" + sha


def _julgar_destino(destino: _Destino, pasta: str, arquivo: str, sha: str, tamanho: int) -> str | None:
    """None = destino vazio, pode gravar; senão INTEGRO ou DIVERGE."""
    uri_obj, uri_prova = pasta + "/" + arquivo, pasta + "/" + PROCEDENCIA
    tem_obj, tem_prova = destino.existe(uri_obj), destino.existe(uri_prova)
    if not tem_obj and not tem_prova:
        return None
    if not (tem_obj and tem_prova):
        return DIVERGE
    try:
        dados = destino.ler(uri_obj)
        prova = json.loads(destino.ler(uri_prova).decode("utf-8"))
    except (ValueError, Py4JJavaError):
        return DIVERGE
    if not isinstance(prova, dict):
        return DIVERGE
    confere = (
        _sha256(dados) == sha
        and len(dados) == tamanho
        and prova.get("arquivo") == arquivo
        and prova.get("sha256") == sha
        and prova.get("tamanho") == tamanho
    )
    return INTEGRO if confere else DIVERGE


def _um(origem: Path, destino: _Destino, esperados: dict[str, str], arquivo: str) -> str:
    if arquivo not in ARQUIVOS:
        return RECUSADO
    fonte = origem / arquivo
    sha_esperado = esperados.get(arquivo)
    if sha_esperado is None or not fonte.is_file():
        return NAO_MEDIDO
    dados = fonte.read_bytes()
    sha = _sha256(dados)
    if sha != sha_esperado:
        return NAO_MEDIDO

    pasta = destino.pasta(arquivo, sha)
    veredito = _julgar_destino(destino, pasta, arquivo, sha, len(dados))
    if veredito is not None:
        return veredito

    destino.criar(pasta + "/" + arquivo, dados)
    prova = {
        "arquivo": arquivo,
        "sha256": sha,
        "tamanho": len(dados),
        "origem": str(fonte),
        "instante": datetime.now(timezone.utc).isoformat(),
    }
    corpo = json.dumps(prova, ensure_ascii=False, indent=2).encode("utf-8")
    destino.criar(pasta + "/" + PROCEDENCIA, corpo)
    return GRAVADO if _sha256(destino.ler(pasta + "/" + arquivo)) == sha else DIVERGE


def gravar(spark, origem: str = ORIGEM_PADRAO, destino: str = DESTINO_PADRAO, arquivos=ARQUIVOS) -> dict[str, str]:
    """{arquivo: token} — um resultado por arquivo pedido, sem que um afete o outro."""
    raiz = Path(origem)
    esperados = _checksums(raiz)
    alvo = _Destino(spark, destino)
    return {nome: _um(raiz, alvo, esperados, nome) for nome in arquivos}
