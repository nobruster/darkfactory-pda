"""Projeção da ontologia no Postgres: tudo ou nada, reconferida linha a linha.

O banco NÃO é fonte da verdade — a ontologia versionada é. Aqui ela é carregada numa
transação só e relida DENTRO dela, antes do commit; divergiu, desfaz. Credenciais só do
ambiente (PG_*), nunca no código, nunca em mensagem.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Optional

import psycopg
from psycopg import sql

PROJETADA = "PROJETADA"
DIVERGENTE = "DIVERGENTE"
NAO_MEDIDO = "NAO_MEDIDO"

DIRETORIO_RAW_PADRAO = "/dados/_raw"
GOLD_PADRAO = "s3a://gold/pda/referencia"

VARIAVEIS = ("PG_HOST", "PG_PORT", "PG_DB", "PG_USER", "PG_PASSWORD")
_PADRAO_SCHEMA = re.compile(r"[a-z][a-z0-9_]{0,62}")

# ordem de carga: dependências antes de quem as referencia
TABELAS = ("fonte", "termo", "coluna", "grupo", "especie", "carga")

_DDL = {
    "fonte": "chave text PRIMARY KEY, arquivo text NOT NULL, sha256 text NOT NULL",
    "termo": "nome text PRIMARY KEY, descricao text NOT NULL",
    "coluna": (
        "posicao integer PRIMARY KEY, cabecalho text NOT NULL, "
        "termo text NOT NULL REFERENCES {termo}(nome), papel text"
    ),
    "grupo": "nome text PRIMARY KEY",
    "especie": (
        "codigo text PRIMARY KEY, nome text NOT NULL, "
        "grupo text NOT NULL REFERENCES {grupo}(nome)"
    ),
    "carga": "id integer PRIMARY KEY, sha256 text NOT NULL, carregada_em timestamptz NOT NULL",
}


class ProjecaoRecusada(Exception):
    """Recusa antes de qualquer SQL, ou conexão que falhou — a mensagem nunca traz valor secreto."""

    def __init__(self, motivo: str, detalhe: str = ""):
        self.motivo = motivo
        self.detalhe = detalhe
        super().__init__(f"{motivo}: {detalhe}" if detalhe else motivo)


@dataclass(frozen=True)
class Projecao:
    veredito: str
    contagens: Dict[str, int]
    divergencia: str = ""
    versoes: Dict[str, int] = field(default_factory=dict)


def validar_schema(schema) -> str:
    if not isinstance(schema, str) or not _PADRAO_SCHEMA.fullmatch(schema):
        raise ProjecaoRecusada("SCHEMA_INVALIDO", "use letras minúsculas, dígitos e _")
    if schema == "public" or schema.startswith("pg_"):
        raise ProjecaoRecusada("SCHEMA_RESERVADO", schema)
    return schema


def _parametros_do_ambiente() -> dict:
    ausentes = [v for v in VARIAVEIS if not os.environ.get(v)]
    if ausentes:
        raise ProjecaoRecusada("VARIAVEL_AUSENTE", ", ".join(ausentes))
    return {
        "host": os.environ["PG_HOST"],
        "port": os.environ["PG_PORT"],
        "dbname": os.environ["PG_DB"],
        "user": os.environ["PG_USER"],
        "password": os.environ["PG_PASSWORD"],
        "connect_timeout": 10,
    }


def _esperado(ontologia) -> Dict[str, set]:
    grupos = {e["grupo"] for e in ontologia.especies}
    return {
        "fonte": {(k, v["arquivo"], v["sha256"]) for k, v in ontologia.fontes.items()},
        "termo": {(t["nome"], t["descricao"]) for t in ontologia.termos},
        "coluna": {
            (c["posicao"], c["cabecalho"], c["termo"], c.get("papel")) for c in ontologia.colunas
        },
        "grupo": {(g,) for g in grupos},
        "especie": {(e["codigo"], e["nome"], e["grupo"]) for e in ontologia.especies},
    }


def _id(schema: str, tabela: str) -> sql.Identifier:
    return sql.Identifier(schema, tabela)


def _criar(cur, schema: str) -> None:
    cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))
    for tabela in reversed(TABELAS):
        cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(_id(schema, tabela)))
    for tabela in TABELAS:
        refs = {t: _id(schema, t) for t in ("termo", "grupo")}
        corpo = sql.SQL(_DDL[tabela]).format(**refs)
        cur.execute(sql.SQL("CREATE TABLE {} ({})").format(_id(schema, tabela), corpo))


def _inserir(cur, schema: str, tabela: str, linhas) -> None:
    linhas = sorted(linhas, key=lambda r: tuple(str(x) for x in r))
    if not linhas:
        return
    marcadores = sql.SQL(", ").join([sql.Placeholder()] * len(linhas[0]))
    cur.executemany(
        sql.SQL("INSERT INTO {} VALUES ({})").format(_id(schema, tabela), marcadores), linhas
    )


def projetar_ontologia(
    ontologia,
    schema,
    apos_tabela: Optional[Callable] = None,
) -> Projecao:
    """Carrega a ontologia em `schema`, reconfere dentro da transação e só então faz commit.

    `apos_tabela(cursor, tabela)` roda dentro da transação depois de cada tabela carregada.
    Devolve PROJETADA com as contagens, ou DIVERGENTE (transação desfeita).
    """
    schema = validar_schema(schema)
    parametros = _parametros_do_ambiente()
    try:
        conexao = psycopg.connect(**parametros)
    except psycopg.Error as erro:
        raise ProjecaoRecusada("CONEXAO_FALHOU", type(erro).__name__) from None

    esperado = _esperado(ontologia)
    with conexao:
        try:
            with conexao.cursor() as cur:
                _criar(cur, schema)
                for tabela in TABELAS:
                    if tabela == "carga":
                        cur.execute(
                            sql.SQL("INSERT INTO {} VALUES (1, %s, now())").format(
                                _id(schema, tabela)
                            ),
                            (ontologia.sha256,),
                        )
                    else:
                        _inserir(cur, schema, tabela, esperado[tabela])
                    if apos_tabela is not None:
                        apos_tabela(cur, tabela)

                for tabela in TABELAS[:-1]:
                    cur.execute(sql.SQL("SELECT * FROM {}").format(_id(schema, tabela)))
                    lidas = cur.fetchall()
                    if len(lidas) != len(esperado[tabela]) or set(lidas) != esperado[tabela]:
                        conexao.rollback()
                        return Projecao(DIVERGENTE, {}, tabela)
                cur.execute(sql.SQL("SELECT id, sha256 FROM {}").format(_id(schema, "carga")))
                if cur.fetchall() != [(1, ontologia.sha256)]:
                    conexao.rollback()
                    return Projecao(DIVERGENTE, {}, "carga")

                contagens = {t: len(esperado[t]) for t in TABELAS[:-1]}
        except BaseException:
            conexao.rollback()
            raise
        conexao.commit()
    return Projecao(PROJETADA, contagens)


# ---------------------------------------------------------------- projeção validada pela Gold

_DDL_VALIDACAO = (
    "id integer PRIMARY KEY, competencia text NOT NULL, versao_dim_especie integer NOT NULL, "
    "versao_dim_termo integer NOT NULL, conferido_em timestamptz NOT NULL"
)


def _ler_fontes(ontologia, raw) -> Dict[str, list]:
    """Lê cada .xlsx UMA vez: os mesmos bytes vão ao sha256 e ao parser da ontologia."""
    from medalhao import ontologia as onto_mod

    raw = Path(raw)
    caminho_checksums = raw / "CHECKSUMS.txt"
    if not caminho_checksums.is_file():
        raise ProjecaoRecusada("CHECKSUMS_AUSENTE", str(caminho_checksums))
    checksums = onto_mod._checksums(caminho_checksums)
    linhas = {}
    for chave in ("dicionario", "glossario"):
        fonte = ontologia.fontes.get(chave) or {}
        arquivo = raw / str(fonte.get("arquivo", ""))
        if not fonte.get("arquivo") or not arquivo.is_file():
            raise ProjecaoRecusada("FONTE_AUSENTE", str(fonte.get("arquivo")))
        dados = arquivo.read_bytes()
        real = hashlib.sha256(dados).hexdigest()
        if real != str(fonte.get("sha256", "")).lower():
            raise ProjecaoRecusada("SHA256_NAO_APROVADO", arquivo.name)
        if checksums.get(arquivo.name) != real:
            raise ProjecaoRecusada("CHECKSUMS_DIVERGENTE", arquivo.name)
        linhas[chave] = onto_mod.ler_xlsx(io.BytesIO(dados))
    return linhas


def _esperado_dos_arquivos(ontologia, contrato, linhas) -> Dict[str, set]:
    from medalhao import ontologia as onto_mod

    dicionario = onto_mod._especies_do_dicionario(linhas["dicionario"])
    glossario = onto_mod._termos_do_glossario(linhas["glossario"])
    grupo_de = {c: g.grupo for g in contrato.grupos_especie.grupos for c in g.codigos}
    sem_grupo = sorted(set(dicionario) - set(grupo_de))
    if sem_grupo:
        raise ProjecaoRecusada("CODIGO_SEM_GRUPO", str(sem_grupo))
    return {
        "fonte": {(k, v["arquivo"], v["sha256"]) for k, v in ontologia.fontes.items()},
        "termo": set(glossario.items()),
        "coluna": {
            (c["posicao"], c["cabecalho"], c["termo"], c.get("papel")) for c in ontologia.colunas
        },
        "grupo": {(grupo_de[c],) for c in dicionario},
        "especie": {(c, nome, grupo_de[c]) for c, nome in dicionario.items()},
    }


def _versao_e_linhas(spark, gold: str, tabela: str, chave: str, valor: str, colunas):
    """(versão V, linhas) da dimensão, lidas NA versão V; (None, []) se a Gold não a tem."""
    from medalhao import gold_referencia as g

    caminho = f"{gold.rstrip('/')}/{tabela}"
    if not g._e_delta(spark, caminho):
        return None, []
    versao = g._versao_atual(spark, caminho)
    df = g._ler_versao(spark, caminho, versao).where(g.F.col(chave) == valor).select(*colunas)
    return versao, [tuple(r) for r in df.collect()]


def projetar_validado(
    spark,
    ontologia,
    contrato,
    schema,
    competencia,
    raw=DIRETORIO_RAW_PADRAO,
    gold=GOLD_PADRAO,
) -> Projecao:
    """Carrega o Postgres dos PRÓPRIOS .xlsx e só publica o que concorda com a Gold da referência.

    Independente da Gold: os dados vêm dos bytes conferidos, lidos pelo parser da ontologia. A
    Gold só entra como juiz, dentro da transação, comparando o que o Postgres gravou (relido pela
    mesma conexão) como multiconjunto nos dois sentidos. Devolve PROJETADA, DIVERGENTE (nomeando
    a dimensão; transação desfeita) ou NAO_MEDIDO (Gold sem linhas; sem commit).
    """
    schema = validar_schema(schema)
    linhas = _ler_fontes(ontologia, raw)  # recusa sem conectar
    esperado = _esperado_dos_arquivos(ontologia, contrato, linhas)
    sha_glossario = str(ontologia.fontes["glossario"]["sha256"]).lower()
    parametros = _parametros_do_ambiente()
    try:
        conexao = psycopg.connect(**parametros)
    except psycopg.Error as erro:
        raise ProjecaoRecusada("CONEXAO_FALHOU", type(erro).__name__) from None

    with conexao:
        try:
            with conexao.cursor() as cur:
                _criar(cur, schema)
                cur.execute(
                    sql.SQL("DROP TABLE IF EXISTS {}").format(_id(schema, "validacao_gold"))
                )
                cur.execute(
                    sql.SQL("CREATE TABLE {} ({})").format(
                        _id(schema, "validacao_gold"), sql.SQL(_DDL_VALIDACAO)
                    )
                )
                for tabela in TABELAS:
                    if tabela == "carga":
                        cur.execute(
                            sql.SQL("INSERT INTO {} VALUES (1, %s, now())").format(
                                _id(schema, tabela)
                            ),
                            (ontologia.sha256,),
                        )
                    else:
                        _inserir(cur, schema, tabela, esperado[tabela])

                v_esp, gold_esp = _versao_e_linhas(
                    spark, gold, "dim_especie", "competencia", competencia,
                    ("codigo", "nome_oficial", "grupo"),
                )
                v_ter, gold_ter = _versao_e_linhas(
                    spark, gold, "dim_termo", "sha256_arquivo", sha_glossario,
                    ("termo", "descricao"),
                )
                for nome, lidas in (("dim_especie", gold_esp), ("dim_termo", gold_ter)):
                    if not lidas:
                        conexao.rollback()
                        return Projecao(NAO_MEDIDO, {}, nome)

                # o que foi GRAVADO, pela conexão da própria transação
                cur.execute(
                    sql.SQL("SELECT codigo, nome, grupo FROM {}").format(_id(schema, "especie"))
                )
                pg_esp = [tuple(r) for r in cur.fetchall()]
                cur.execute(sql.SQL("SELECT nome, descricao FROM {}").format(_id(schema, "termo")))
                pg_ter = [tuple(r) for r in cur.fetchall()]
                for nome, gravado, da_gold in (
                    ("dim_especie", pg_esp, gold_esp),
                    ("dim_termo", pg_ter, gold_ter),
                ):
                    if Counter(gravado) != Counter(da_gold):  # multiplicidade, nos dois sentidos
                        conexao.rollback()
                        return Projecao(DIVERGENTE, {}, nome)

                cur.execute(
                    sql.SQL("INSERT INTO {} VALUES (1, %s, %s, %s, now())").format(
                        _id(schema, "validacao_gold")
                    ),
                    (competencia, v_esp, v_ter),
                )
                contagens = {t: len(esperado[t]) for t in TABELAS[:-1]}
        except BaseException:
            conexao.rollback()
            raise
        conexao.commit()
    return Projecao(PROJETADA, contagens, versoes={"dim_especie": v_esp, "dim_termo": v_ter})
