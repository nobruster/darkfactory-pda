"""Testes da Gold da referência — dim_especie e dim_termo, lidas SÓ da Silver.

Rodam DENTRO do contêiner pda-spark. Gravam só em tmp_path; nenhum cenário usa skip, xfail ou
importorskip, e nenhuma função para a sessão Spark.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from medalhao import bronze, especie, glossario, gold_referencia as g  # noqa: E402

SHA = "a" * 64
OUTRO_SHA = "b" * 64
COMP = "2026-03"
OUTRA_COMP = "2026-04"

ESPECIES = [
    ("01", "Pensão por morte previdenciária", "Pensão por morte", "Pensão por morte", True),
    ("02", "Aposentadoria por idade", "Aposentadoria", "Aposentadoria por ida", False),
]
TERMOS = [("Renda", "Valor mensal"), ("Espécie", "Tipo de benefício")]


@pytest.fixture(scope="session")
def spark():
    return bronze.criar_sessao("teste-gold-referencia")


def _grava_silver_especie(spark, caminho, competencia=COMP, linhas=ESPECIES, modo="append"):
    dados = [(c, n, gr, d, ok, competencia) for c, n, gr, d, ok in linhas]
    df = spark.createDataFrame(dados, especie.SCHEMA)
    df.write.format("delta").mode(modo).save(str(caminho))


def _grava_silver_glossario(spark, caminho, sha=SHA, termos=TERMOS, modo="append"):
    df = spark.createDataFrame([(t, d, sha) for t, d in termos], glossario.ESQUEMA)
    df.write.format("delta").mode(modo).save(str(caminho))


@pytest.fixture
def silver(spark, tmp_path):
    """(silver_especie, silver_glossario) já com a competência e o sha256 padrão."""
    esp, glo = tmp_path / "silver_especie", tmp_path / "silver_glossario"
    _grava_silver_especie(spark, esp)
    _grava_silver_glossario(spark, glo)
    return str(esp), str(glo)


@pytest.fixture
def destino(tmp_path):
    return str(tmp_path / "gold")


def _publicar(spark, silver, destino, competencia=COMP, sha=SHA, **kw):
    return g.publicar(spark, silver[0], silver[1], destino, competencia, sha, **kw)


def _lido(spark, destino, tabela, coluna, valor):
    df = spark.read.format("delta").load(f"{destino}/{tabela}").where(f"{coluna} = '{valor}'")
    return sorted(tuple(r) for r in df.collect())


def _meta_do_commit(spark, caminho, versao) -> dict:
    from delta.tables import DeltaTable

    linhas = DeltaTable.forPath(spark, caminho).history().select("version", "userMetadata").collect()
    return json.loads(next(r["userMetadata"] for r in linhas if r["version"] == versao))


# ---------------------------------------------------------------- B-1


def test_padroes():
    assert g.DESTINO_PADRAO == "s3a://gold/pda/referencia"
    assert g.ESPECIE_COLUNAS == (
        "codigo", "nome_oficial", "grupo", "descricao_fonte", "texto_fonte_confere_prefixo", "competencia",
    )
    assert g.TERMO_COLUNAS == ("termo", "descricao", "sha256_arquivo")


def test_dim_especie_da_silver(spark, silver, destino):
    res = _publicar(spark, silver, destino)
    assert res.estado == g.INTEGRO, res
    assert res.dim_especie.estado == g.INTEGRO and res.consumo_integro
    esperado = sorted((c, n, gr, d, ok, COMP) for c, n, gr, d, ok in ESPECIES)
    assert _lido(spark, destino, "dim_especie", "competencia", COMP) == esperado
    assert res.dim_especie.linhas == len(ESPECIES)


def test_dim_termo_da_silver(spark, silver, destino):
    res = _publicar(spark, silver, destino)
    assert res.dim_termo.estado == g.INTEGRO, res
    assert _lido(spark, destino, "dim_termo", "sha256_arquivo", SHA) == sorted((t, d, SHA) for t, d in TERMOS)


def test_dim_termo_da_silver_so_do_sha256_pedido(spark, silver, destino):
    """Dois glossários na Silver: só o pedido é selecionado, o termo repetido entre arquivos não conta."""
    _grava_silver_glossario(spark, silver[1], sha=OUTRO_SHA, termos=[("Renda", "outra descrição")])
    res = _publicar(spark, silver, destino)
    assert res.dim_termo.estado == g.INTEGRO, res
    assert _lido(spark, destino, "dim_termo", "sha256_arquivo", OUTRO_SHA) == []
    assert len(_lido(spark, destino, "dim_termo", "sha256_arquivo", SHA)) == len(TERMOS)


def test_linhagem_das_tabelas_silver(spark, silver, destino, monkeypatch):
    """O commit leva as versões FIXADAS no início; commit novo na Silver depois disso não entra."""
    v_esp = bronze._versao_atual(spark, silver[0])
    v_glo = bronze._versao_atual(spark, silver[1])
    original = g._selecionar_termo

    def com_commit_no_meio(spark_, caminho, versao, sha):
        _grava_silver_glossario(spark_, silver[1], sha=SHA, termos=[("Intruso", "de depois")])
        return original(spark_, caminho, versao, sha)

    monkeypatch.setattr(g, "_selecionar_termo", com_commit_no_meio)
    res = _publicar(spark, silver, destino, id_execucao="exec-1")
    assert res.estado == g.INTEGRO, res
    assert bronze._versao_atual(spark, silver[1]) > v_glo
    assert (res.versao_silver_especie, res.versao_silver_glossario) == (v_esp, v_glo)
    for tabela, dim in (("dim_especie", res.dim_especie), ("dim_termo", res.dim_termo)):
        meta = _meta_do_commit(spark, f"{destino}/{tabela}", dim.versao)
        assert meta["versao_silver_especie"] == v_esp
        assert meta["versao_silver_glossario"] == v_glo
        assert meta["id_execucao"] == "exec-1"
    assert "Intruso" not in [t for t, *_ in _lido(spark, destino, "dim_termo", "sha256_arquivo", SHA)]


def test_reconfere_o_proprio_commit(spark, silver, destino):
    res = _publicar(spark, silver, destino)
    for dim in (res.dim_especie, res.dim_termo):
        assert dim.detalhe == {"versao": dim.versao, "so_no_esperado": 0, "so_no_lido": 0}


@pytest.mark.parametrize("defeito", ["a_menos", "a_mais"])
def test_reconfere_o_proprio_commit_acusa_linha_a_menos_e_a_mais(spark, silver, destino, monkeypatch, defeito):
    original = g._ler_commit

    def adulterada(spark_, caminho, versao, condicao, colunas):
        lido = original(spark_, caminho, versao, condicao, colunas)
        if not caminho.endswith("dim_termo"):
            return lido
        return lido.where("termo <> 'Renda'") if defeito == "a_menos" else lido.unionAll(lido.where("termo = 'Renda'"))

    monkeypatch.setattr(g, "_ler_commit", adulterada)
    res = _publicar(spark, silver, destino)
    assert res.estado == g.DIVERGE and not res.consumo_integro
    assert res.dim_termo.estado == g.DIVERGE
    assert res.dim_termo.detalhe["so_no_esperado" if defeito == "a_menos" else "so_no_lido"] == 1
    assert res.dim_especie.estado == g.INTEGRO  # independente
    monkeypatch.setattr(g, "_ler_commit", original)
    assert _lido(spark, destino, "dim_termo", "sha256_arquivo", SHA) == []  # revertido


def test_republicar_nao_duplica(spark, silver, destino):
    assert _publicar(spark, silver, destino).estado == g.INTEGRO
    assert _publicar(spark, silver, destino).estado == g.INTEGRO
    assert len(_lido(spark, destino, "dim_especie", "competencia", COMP)) == len(ESPECIES)
    assert len(_lido(spark, destino, "dim_termo", "sha256_arquivo", SHA)) == len(TERMOS)


def test_outra_competencia_intacta(spark, silver, destino):
    _grava_silver_especie(spark, silver[0], competencia=OUTRA_COMP, linhas=ESPECIES[:1])
    assert _publicar(spark, silver, destino, competencia=OUTRA_COMP).estado == g.INTEGRO
    antes = _lido(spark, destino, "dim_especie", "competencia", OUTRA_COMP)
    assert _publicar(spark, silver, destino, competencia=COMP).estado == g.INTEGRO
    assert _lido(spark, destino, "dim_especie", "competencia", OUTRA_COMP) == antes
    assert len(antes) == 1
    assert len(_lido(spark, destino, "dim_especie", "competencia", COMP)) == len(ESPECIES)


def test_outra_versao_do_glossario_intacta(spark, silver, destino):
    _grava_silver_glossario(spark, silver[1], sha=OUTRO_SHA, termos=[("Outro", "de outra versão")])
    assert _publicar(spark, silver, destino, sha=OUTRO_SHA).estado == g.INTEGRO
    antes = _lido(spark, destino, "dim_termo", "sha256_arquivo", OUTRO_SHA)
    assert _publicar(spark, silver, destino, sha=SHA).estado == g.INTEGRO
    assert _lido(spark, destino, "dim_termo", "sha256_arquivo", OUTRO_SHA) == antes
    assert len(antes) == 1


# ---------------------------------------------------------------- B-2


def test_silver_vazia_nao_medido(spark, silver, destino):
    """Competência sem linha na Silver especie: NAO_MEDIDO e a dimensão não ganha versão."""
    res = _publicar(spark, silver, destino, competencia="2099-01")
    assert res.dim_especie.estado == g.NAO_MEDIDO and res.dim_especie.motivo.startswith("SILVER_SEM_LINHAS")
    assert res.estado == g.NAO_MEDIDO and not res.consumo_integro
    assert not Path(destino, "dim_especie").exists()


def test_silver_vazia_nao_medido_nao_apaga_particao_existente(spark, silver, destino):
    assert _publicar(spark, silver, destino).estado == g.INTEGRO
    antes = _lido(spark, destino, "dim_especie", "competencia", COMP)
    vazia = str(Path(silver[0]).parent / "silver_especie_vazia")
    _grava_silver_especie(spark, vazia, competencia=OUTRA_COMP)
    res = g.publicar(spark, vazia, silver[1], destino, COMP, SHA)
    assert res.dim_especie.estado == g.NAO_MEDIDO
    assert _lido(spark, destino, "dim_especie", "competencia", COMP) == antes


def test_glossario_ausente_nao_apaga_particao(spark, silver, destino):
    assert _publicar(spark, silver, destino).estado == g.INTEGRO
    antes = _lido(spark, destino, "dim_termo", "sha256_arquivo", SHA)
    versao = bronze._versao_atual(spark, f"{destino}/dim_termo")
    res = _publicar(spark, silver, destino, sha="c" * 64)
    assert res.dim_termo.estado == g.NAO_MEDIDO
    assert bronze._versao_atual(spark, f"{destino}/dim_termo") == versao  # nenhuma gravação
    assert _lido(spark, destino, "dim_termo", "sha256_arquivo", SHA) == antes
    assert antes


def test_dimensoes_independentes(spark, silver, destino):
    res = _publicar(spark, silver, destino, sha="c" * 64)
    assert res.dim_especie.estado == g.INTEGRO
    assert res.dim_termo.estado == g.NAO_MEDIDO
    assert res.estado == g.NAO_MEDIDO and not res.consumo_integro
    assert len(_lido(spark, destino, "dim_especie", "competencia", COMP)) == len(ESPECIES)
    assert not Path(destino, "dim_termo").exists()


def test_dimensoes_independentes_codigo_duplicado_so_recusa_a_especie(spark, silver, destino):
    _grava_silver_especie(spark, silver[0], linhas=ESPECIES[:1])  # o mesmo código 01 de novo
    res = _publicar(spark, silver, destino)
    assert res.dim_especie.estado == g.DIVERGE and res.dim_especie.motivo.startswith("CODIGO_DUPLICADO")
    assert res.dim_termo.estado == g.INTEGRO
    assert not Path(destino, "dim_especie").exists()


def test_silver_ausente_nao_medido(spark, silver, destino, tmp_path):
    res = g.publicar(spark, str(tmp_path / "nao-existe"), silver[1], destino, COMP, SHA)
    assert (res.dim_especie.estado, res.dim_especie.motivo) == (g.NAO_MEDIDO, "SILVER_AUSENTE")
    assert res.dim_termo.estado == g.INTEGRO


def test_entradas_invalidas_nao_chegam_ao_replace_where(spark, silver, destino):
    assert _publicar(spark, silver, destino, competencia="x' OR '1'='1").estado == g.ERRO_LEITURA
    assert _publicar(spark, silver, destino, sha="x' OR '1'='1").estado == g.ERRO_LEITURA
    assert not Path(destino).exists()


def test_modulo_le_so_a_silver():
    """Pelo AST: nenhum nome, atributo, import ou texto do módulo referencia camadas anteriores."""
    fonte = Path(g.__file__).read_text(encoding="utf-8")
    proibidos = ("bronze", "landing", "_raw")
    achados = []
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, ast.Name):
            textos = [no.id]
        elif isinstance(no, ast.Attribute):
            textos = [no.attr]
        elif isinstance(no, (ast.Import, ast.ImportFrom)):
            textos = [a.name for a in no.names] + [getattr(no, "module", None) or ""]
        elif isinstance(no, ast.Constant) and isinstance(no.value, str):
            textos = [no.value]
        elif isinstance(no, (ast.FunctionDef, ast.arg)):
            textos = [getattr(no, "name", None) or getattr(no, "arg", "")]
        else:
            continue
        achados += [(t, p) for t in textos for p in proibidos if p in t.lower()]
    assert achados == []
