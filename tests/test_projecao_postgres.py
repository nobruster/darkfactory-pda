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


# ---------------------------------------------------------------- projeção validada pela Gold

from pda.contrato import carregar_contrato  # noqa: E402

from medalhao import bronze, gold_referencia as gold_ref  # noqa: E402
from medalhao import ontologia as onto_mod  # noqa: E402
from medalhao.projecao_postgres import NAO_MEDIDO, projetar_validado  # noqa: E402

COMP = "2026-03"


@pytest.fixture(scope="session")
def spark():
    return bronze.criar_sessao("teste-projecao-postgres")


@pytest.fixture(scope="module")
def contrato():
    return carregar_contrato(onto_mod.ARQUIVO_CONTRATO)


def _sha_glossario(onto: Ontologia) -> str:
    return onto.fontes["glossario"]["sha256"]


def _gravar_gold(spark, raiz, onto, competencia=COMP, especies=None, termos=None, modo="overwrite"):
    """Gold falsa em tmp_path, montada da ontologia versionada (não do código sob teste)."""
    if especies is None:
        especies = [(e["codigo"], e["nome"], e["grupo"]) for e in onto.especies]
    if termos is None:
        termos = [(t["nome"], t["descricao"]) for t in onto.termos]
    esp = spark.createDataFrame(
        [(c, n, g, None, None, competencia) for c, n, g in especies], gold_ref.ESPECIE_SCHEMA
    )
    ter = spark.createDataFrame(
        [(t, d, _sha_glossario(onto)) for t, d in termos], gold_ref.TERMO_SCHEMA
    )
    esp.write.format("delta").mode(modo).save(f"{raiz}/dim_especie")
    ter.write.format("delta").mode(modo).save(f"{raiz}/dim_termo")


@pytest.fixture
def gold(spark, tmp_path, ontologia):
    raiz = str(tmp_path / "gold")
    _gravar_gold(spark, raiz, ontologia)
    return raiz


def _validar(spark, ontologia, contrato, schema, gold, **kw):
    return projetar_validado(spark, ontologia, contrato, schema, COMP, gold=gold, **kw)


def test_validado_carrega_os_proprios_arquivos(spark, ontologia, contrato, schema, gold, monkeypatch):
    lidos = []
    original = onto_mod.ler_xlsx

    def espia(fonte):
        lidos.append(type(fonte).__name__)
        return original(fonte)

    monkeypatch.setattr(onto_mod, "ler_xlsx", espia)
    r = _validar(spark, ontologia, contrato, schema, gold)
    assert r.veredito == PROJETADA, r
    assert lidos == ["BytesIO", "BytesIO"]  # o parser da ontologia, sobre os bytes já conferidos
    assert r.contagens == {"fonte": 2, "termo": 13, "coluna": 14, "grupo": 5, "especie": 65}
    especie = _consultar(schema, "SELECT codigo, nome, grupo FROM especie")
    assert set(especie) == {(e["codigo"], e["nome"], e["grupo"]) for e in ontologia.especies}
    assert _sha_gravado(schema) == ontologia.sha256


def test_validado_confere_contra_a_gold(spark, ontologia, contrato, schema, gold):
    r = _validar(spark, ontologia, contrato, schema, gold)
    assert r.veredito == PROJETADA, r
    linhas = _consultar(
        schema, "SELECT id, competencia, versao_dim_especie, versao_dim_termo FROM validacao_gold"
    )
    assert len(linhas) == 1 and linhas[0][0] == 1 and linhas[0][1] == COMP
    chaves = _consultar(
        schema,
        "SELECT kcu.column_name FROM information_schema.table_constraints tc "
        "JOIN information_schema.key_column_usage kcu "
        "ON kcu.constraint_name = tc.constraint_name AND kcu.table_schema = tc.table_schema "
        "WHERE tc.table_schema = %s AND tc.table_name = 'validacao_gold' "
        "AND tc.constraint_type = 'PRIMARY KEY'",
        schema,
    )
    assert chaves == [("id",)]


def test_validado_gold_divergente_desfaz(spark, ontologia, contrato, schema, gold, tmp_path):
    assert _validar(spark, ontologia, contrato, schema, gold).veredito == PROJETADA
    esp = [(e["codigo"], e["nome"], e["grupo"]) for e in ontologia.especies]
    esp[0] = (esp[0][0], "nome adulterado", esp[0][2])
    ruim = str(tmp_path / "gold_ruim")
    _gravar_gold(spark, ruim, ontologia, especies=esp)
    r = _validar(spark, _outra(ontologia), contrato, schema, ruim)
    assert r.veredito == DIVERGENTE and r.divergencia == "dim_especie"
    assert _sha_gravado(schema) == ontologia.sha256
    assert _consultar(schema, "SELECT count(*) FROM validacao_gold")[0][0] == 1


def test_validado_glossario_divergente_desfaz(spark, ontologia, contrato, schema, gold, tmp_path):
    assert _validar(spark, ontologia, contrato, schema, gold).veredito == PROJETADA
    ter = [(t["nome"], t["descricao"]) for t in ontologia.termos]
    ter[0] = (ter[0][0], "descrição adulterada")
    ruim = str(tmp_path / "gold_ruim")
    _gravar_gold(spark, ruim, ontologia, termos=ter)  # defeito SÓ na dim_termo
    r = _validar(spark, _outra(ontologia), contrato, schema, ruim)
    assert r.veredito == DIVERGENTE and r.divergencia == "dim_termo"
    assert _sha_gravado(schema) == ontologia.sha256


def test_validado_segunda_carga_troca_a_validacao(spark, ontologia, contrato, schema, gold):
    assert _validar(spark, ontologia, contrato, schema, gold).veredito == PROJETADA
    antes = _consultar(schema, "SELECT versao_dim_especie, versao_dim_termo FROM validacao_gold")
    _gravar_gold(spark, gold, ontologia, modo="overwrite")  # novos commits nas duas dimensões
    assert _validar(spark, ontologia, contrato, schema, gold).veredito == PROJETADA
    depois = _consultar(schema, "SELECT versao_dim_especie, versao_dim_termo FROM validacao_gold")
    assert len(depois) == 1
    assert depois[0][0] > antes[0][0] and depois[0][1] > antes[0][1]


def test_validado_linha_repetida_na_gold_diverge(spark, ontologia, contrato, schema, tmp_path):
    esp = [(e["codigo"], e["nome"], e["grupo"]) for e in ontologia.especies]
    ruim = str(tmp_path / "gold_repetida")
    _gravar_gold(spark, ruim, ontologia, especies=esp + [esp[0]])
    r = _validar(spark, ontologia, contrato, schema, ruim)
    assert r.veredito == DIVERGENTE and r.divergencia == "dim_especie"


def test_validado_compara_o_que_foi_gravado(spark, ontologia, contrato, schema, gold, monkeypatch):
    """A estrutura Python bate com a Gold; o que foi gravado no Postgres, não — tem de divergir."""
    original = proj._inserir

    def grava_errado(cur, esquema, tabela, linhas):
        if tabela == "especie":
            linhas = [
                (c, "gravado errado" if i == 0 else n, g)
                for i, (c, n, g) in enumerate(sorted(linhas))
            ]
        return original(cur, esquema, tabela, linhas)

    monkeypatch.setattr(proj, "_inserir", grava_errado)
    r = _validar(spark, ontologia, contrato, schema, gold)
    assert r.veredito == DIVERGENTE and r.divergencia == "dim_especie"


def test_validado_gold_vazia_nao_medido(spark, ontologia, contrato, schema, gold, tmp_path):
    assert _validar(spark, ontologia, contrato, schema, gold).veredito == PROJETADA
    # Gold sem linhas da competência pedida
    r = projetar_validado(spark, _outra(ontologia), contrato, schema, "2099-12", gold=gold)
    assert r.veredito == NAO_MEDIDO and r.divergencia == "dim_especie"
    # Gold sem nenhuma tabela
    r = _validar(spark, _outra(ontologia), contrato, schema, str(tmp_path / "nao_existe"))
    assert r.veredito == NAO_MEDIDO
    assert _sha_gravado(schema) == ontologia.sha256  # sem commit: a carga anterior segue


def test_validado_sha256_nao_aprovado_recusa(spark, ontologia, contrato, schema, gold, monkeypatch):
    _proibir_conexao(monkeypatch)
    fontes = {k: dict(v) for k, v in ontologia.fontes.items()}
    fontes["glossario"]["sha256"] = "0" * 64
    with pytest.raises(ProjecaoRecusada) as erro:
        _validar(spark, dataclasses.replace(ontologia, fontes=fontes), contrato, schema, gold)
    assert erro.value.motivo == "SHA256_NAO_APROVADO"


def test_validado_registra_versoes_da_gold(spark, ontologia, contrato, schema, gold):
    for _ in range(2):  # empurra as versões para além de 0
        _gravar_gold(spark, gold, ontologia, modo="overwrite")
    r = _validar(spark, ontologia, contrato, schema, gold)
    assert r.veredito == PROJETADA, r
    v_esp = gold_ref._versao_atual(spark, f"{gold}/dim_especie")
    v_ter = gold_ref._versao_atual(spark, f"{gold}/dim_termo")
    assert v_esp >= 2 and v_ter >= 2
    assert r.versoes == {"dim_especie": v_esp, "dim_termo": v_ter}
    assert _consultar(schema, "SELECT versao_dim_especie, versao_dim_termo FROM validacao_gold") == [
        (v_esp, v_ter)
    ]


def test_validado_real_contra_a_gold_de_producao(spark, ontologia, contrato, schema):
    """Os .xlsx reais de /dados/_raw contra a Gold de produção (só leitura), num schema 'teste_'."""
    r = projetar_validado(spark, ontologia, contrato, schema, contrato.competencia)
    assert r.veredito == PROJETADA, r
    assert r.contagens["especie"] == 65
    (linha,) = _consultar(schema, "SELECT competencia FROM validacao_gold")
    assert linha[0] == contrato.competencia
