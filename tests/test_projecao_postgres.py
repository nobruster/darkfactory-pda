"""Testes da projeção da ontologia no Postgres.

Rodam DENTRO do contêiner pda-spark, com PG_* do ambiente. Cada teste usa um schema
'teste_<aleatório>' apagado no finalizer — mesmo quando o teste falha — e nunca apaga schema
que ele não criou. Postgres indisponível FALHA o teste: nada aqui pula.
"""

from __future__ import annotations

import dataclasses
import os
import secrets
import sys
from pathlib import Path

import psycopg
import pytest
from psycopg import sql

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from medalhao import projecao_postgres as proj  # noqa: E402
from medalhao.ontologia import Ontologia, carregar_ontologia  # noqa: E402
from medalhao.projecao_postgres import (  # noqa: E402
    DIVERGENTE,
    PROJETADA,
    ProjecaoRecusada,
    projetar_ontologia,
)

_CRIADOS: set = set()


# ---------------------------------------------------------------- apoio


def _conectar():
    return psycopg.connect(
        host=os.environ["PG_HOST"],
        port=os.environ["PG_PORT"],
        dbname=os.environ["PG_DB"],
        user=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"],
        connect_timeout=10,
    )


def _novo_schema() -> str:
    nome = "teste_" + secrets.token_hex(6)
    _CRIADOS.add(nome)
    return nome


def _apagar(schema: str) -> None:
    """Só apaga o que este processo criou."""
    assert schema in _CRIADOS and schema.startswith("teste_"), f"recusa apagar {schema}"
    with _conectar() as conn:
        conn.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))


def _existe(schema: str) -> bool:
    with _conectar() as conn:
        linha = conn.execute(
            "SELECT count(*) FROM information_schema.schemata WHERE schema_name = %s", (schema,)
        ).fetchone()
    return linha[0] == 1


def _consultar(schema: str, consulta: str, *args):
    with _conectar() as conn:
        conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        return conn.execute(consulta, args).fetchall()


def _sha_gravado(schema: str) -> str:
    return _consultar(schema, "SELECT sha256 FROM carga")[0][0]


@pytest.fixture
def schema(request):
    nome = _novo_schema()
    request.addfinalizer(lambda: _apagar(nome))
    return nome


@pytest.fixture(scope="module")
def ontologia():
    onto = carregar_ontologia()
    assert isinstance(onto, Ontologia), f"ontologia não carregou: {onto!r}"
    return onto


def _outra(onto: Ontologia, sha: str = "b" * 64) -> Ontologia:
    return dataclasses.replace(onto, sha256=sha)


def _proibir_conexao(monkeypatch):
    def _falha(*a, **k):
        raise AssertionError("psycopg.connect foi chamado")

    monkeypatch.setattr(psycopg, "connect", _falha)


# ---------------------------------------------------------------- eval_1


def test_projeta_e_reconfere(ontologia, schema):
    r = projetar_ontologia(ontologia, schema)
    assert r.veredito == PROJETADA
    assert r.contagens == {"fonte": 2, "termo": 13, "coluna": 14, "grupo": 5, "especie": 65}
    for tabela, n in r.contagens.items():
        assert _consultar(schema, sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(tabela)))[
            0
        ][0] == n
    especie = _consultar(schema, "SELECT codigo, nome, grupo FROM especie ORDER BY codigo")
    assert {(e["codigo"], e["nome"], e["grupo"]) for e in ontologia.especies} == set(especie)


def test_projeta_e_reconfere_e_idempotente(ontologia, schema):
    assert projetar_ontologia(ontologia, schema).veredito == PROJETADA
    assert projetar_ontologia(ontologia, schema).veredito == PROJETADA
    assert _consultar(schema, "SELECT count(*) FROM carga")[0][0] == 1


def test_grava_sha256_da_ontologia(ontologia, schema):
    projetar_ontologia(ontologia, schema)
    assert _sha_gravado(schema) == ontologia.sha256
    (instante,) = _consultar(schema, "SELECT carregada_em FROM carga")[0]
    assert instante is not None


def test_chave_primaria_em_cada_tabela(ontologia, schema):
    projetar_ontologia(ontologia, schema)
    com_pk = {
        t
        for (t,) in _consultar(
            schema,
            "SELECT table_name FROM information_schema.table_constraints "
            "WHERE table_schema = %s AND constraint_type = 'PRIMARY KEY'",
            schema,
        )
    }
    assert com_pk == set(proj.TABELAS)


def test_chaves_estrangeiras_valem(ontologia, schema):
    projetar_ontologia(ontologia, schema)
    fks = {
        (t, c)
        for t, c in _consultar(
            schema,
            "SELECT tc.table_name, kcu.column_name "
            "FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu "
            "  ON kcu.constraint_name = tc.constraint_name AND kcu.table_schema = tc.table_schema "
            "WHERE tc.table_schema = %s AND tc.constraint_type = 'FOREIGN KEY'",
            schema,
        )
    }
    assert fks == {("coluna", "termo"), ("especie", "grupo")}
    with _conectar() as conn:
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            conn.execute(
                sql.SQL("INSERT INTO {} VALUES ('99', 'x', 'grupo-inexistente')").format(
                    sql.Identifier(schema, "especie")
                )
            )
        conn.rollback()
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            conn.execute(
                sql.SQL("INSERT INTO {} VALUES (99, 'x', 'termo-inexistente', NULL)").format(
                    sql.Identifier(schema, "coluna")
                )
            )
        conn.rollback()


# ---------------------------------------------------------------- eval_2


def test_falha_no_meio_preserva_carga_anterior(ontologia, schema):
    assert projetar_ontologia(ontologia, schema).veredito == PROJETADA
    antes = _sha_gravado(schema)

    def quebra(cur, tabela):
        if tabela == "coluna":
            raise RuntimeError("falha injetada")

    with pytest.raises(RuntimeError, match="falha injetada"):
        projetar_ontologia(_outra(ontologia), schema, apos_tabela=quebra)

    assert _sha_gravado(schema) == antes == ontologia.sha256
    assert _consultar(schema, "SELECT count(*) FROM especie")[0][0] == 65


def test_divergencia_desfaz_e_preserva_carga_anterior(ontologia, schema):
    assert projetar_ontologia(ontologia, schema).veredito == PROJETADA

    def altera(cur, tabela):
        if tabela == "termo":
            cur.execute(
                sql.SQL("UPDATE {} SET descricao = 'adulterada'").format(
                    sql.Identifier(schema, "termo")
                )
            )

    r = projetar_ontologia(_outra(ontologia), schema, apos_tabela=altera)
    assert r.veredito == DIVERGENTE
    assert r.divergencia == "termo"
    assert _sha_gravado(schema) == ontologia.sha256
    assert _consultar(schema, "SELECT count(*) FROM termo WHERE descricao = 'adulterada'")[0][0] == 0


# ---------------------------------------------------------------- eval_3


def test_variavel_ausente_recusa_sem_conectar(ontologia, schema, monkeypatch):
    _proibir_conexao(monkeypatch)
    valor = os.environ["PG_PASSWORD"]
    monkeypatch.delenv("PG_PASSWORD")
    with pytest.raises(ProjecaoRecusada) as erro:
        projetar_ontologia(ontologia, schema)
    assert "PG_PASSWORD" in str(erro.value)
    assert valor not in str(erro.value)


def test_erro_de_conexao_nao_vaza_senha(ontologia, schema, monkeypatch):
    segredo = "segredo-" + secrets.token_hex(8)
    monkeypatch.setenv("PG_PASSWORD", segredo)
    monkeypatch.setenv("PG_PORT", "1")
    with pytest.raises(ProjecaoRecusada) as erro:
        projetar_ontologia(ontologia, schema)
    assert segredo not in str(erro.value)
    assert segredo not in repr(erro.value)
    assert erro.value.__cause__ is None


@pytest.mark.parametrize("nome", ["Maiusculo", "com-hifen", "com espaco", "x; DROP SCHEMA y", "", "1abc"])
def test_schema_invalido_recusa(ontologia, nome, monkeypatch):
    _proibir_conexao(monkeypatch)
    with pytest.raises(ProjecaoRecusada) as erro:
        projetar_ontologia(ontologia, nome)
    assert erro.value.motivo == "SCHEMA_INVALIDO"


def test_schema_invalido_recusa_sem_padrao(ontologia):
    with pytest.raises(TypeError):
        projetar_ontologia(ontologia)  # schema é obrigatório, sem valor padrão


@pytest.mark.parametrize("nome", ["public", "pg_catalog", "pg_temp"])
def test_schema_public_recusa(ontologia, nome, monkeypatch):
    _proibir_conexao(monkeypatch)
    with pytest.raises(ProjecaoRecusada) as erro:
        projetar_ontologia(ontologia, nome)
    assert erro.value.motivo == "SCHEMA_RESERVADO"


def test_schema_de_teste_apagado(ontologia, request):
    criado = _novo_schema()
    with pytest.raises(RuntimeError, match="teste falhou"):
        try:
            assert projetar_ontologia(ontologia, criado).veredito == PROJETADA
            assert _existe(criado)
            raise RuntimeError("teste falhou")
        finally:
            _apagar(criado)  # o que o finalizer da fixture faz
    assert not _existe(criado)
    with pytest.raises(AssertionError):
        _apagar("public")  # nunca apaga o que não criou


def test_sem_credencial_no_codigo():
    fonte = Path(proj.__file__).read_text(encoding="utf-8")
    for var in ("PG_PASSWORD", "PG_USER", "PG_HOST"):
        assert os.environ[var] not in fonte or len(os.environ[var]) < 4
