"""Projeção da ontologia no Postgres: tudo ou nada, reconferida linha a linha.

O banco NÃO é fonte da verdade — a ontologia versionada é. Aqui ela é carregada numa
transação só e relida DENTRO dela, antes do commit; divergiu, desfaz. Credenciais só do
ambiente (PG_*), nunca no código, nunca em mensagem.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Callable, Dict, Optional

import psycopg
from psycopg import sql

PROJETADA = "PROJETADA"
DIVERGENTE = "DIVERGENTE"

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
