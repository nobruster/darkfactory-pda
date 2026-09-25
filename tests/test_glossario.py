"""Testes da Silver do glossário — os termos conformados a partir da Bronze da referência.

Rodam DENTRO do contêiner pda-spark. Gravam só em tmp_path; o que vem da origem bruta
(`/dados/_raw`) é só LIDO para montar o landing, e a ausência dele faz o teste falhar.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from medalhao import bronze, bronze_referencia as br, glossario as g  # noqa: E402
from produtor import landing_referencia as lr  # noqa: E402
from test_bronze_referencia import LINHAS as DICIONARIO_SINTETICO, _landing, _sha, _xlsx  # noqa: E402

DICIO, GLOSS = lr.ARQUIVOS

GLOSSARIO = [
    (1, "Nome", "Descrição"),
    (2, "  Espécie ", "  Tipo de benefício  "),
    (3, None, None),
    (4, "Renda", "Valor mensal"),
    (5, "   ", None),
]
ESPERADO = [("Espécie", "Tipo de benefício"), ("Renda", "Valor mensal")]


@pytest.fixture(scope="session")
def spark():
    return bronze.criar_sessao("teste-glossario")


def _bronze_de(spark, tmp_path, linhas, nome: str = "raw"):
    """A Bronze publicada por bronze_referencia; devolve (raiz_da_bronze, sha256 do glossário)."""
    gloss = _xlsx(linhas)
    landing = _landing(spark, tmp_path, _xlsx(DICIONARIO_SINTETICO), gloss, nome=nome)
    raiz = tmp_path / "bronze"
    res = br.publicar(spark, str(landing), str(raiz), GLOSS, _sha(gloss))
    assert res.estado == br.PUBLICADO, res
    return raiz, _sha(gloss)


def _publicar(spark, raiz, destino, sha, aprovado=None, **kw):
    return g.publicar(spark, str(raiz), str(destino), sha, sha if aprovado is None else aprovado, **kw)


@pytest.fixture
def destino(tmp_path):
    return tmp_path / "silver"


def _termos(spark, destino: Path, sha: str | None = None) -> list[tuple]:
    df = spark.read.format("delta").load(str(destino))
    if sha is not None:
        df = df.where(df.sha256_arquivo == sha)
    return sorted(tuple(r) for r in df.select(*g.COLUNAS).collect())


def _meta_do_commit(spark, destino: Path, versao: int) -> dict:
    from delta.tables import DeltaTable

    linhas = DeltaTable.forPath(spark, str(destino)).history().select("version", "userMetadata").collect()
    return json.loads(next(r["userMetadata"] for r in linhas if r["version"] == versao))


# ---------------------------------------------------------------- B-1


def test_padroes():
    assert g.DESTINO_PADRAO == "s3a://silver/pda/glossario"
    assert g.BRONZE_PADRAO == "s3a://bronze/pda/referencia"
    assert g.COLUNAS == ("termo", "descricao", "sha256_arquivo")


def test_conforma_e_conta_descartes(spark, tmp_path, destino):
    raiz, sha = _bronze_de(spark, tmp_path, GLOSSARIO)
    res = _publicar(spark, raiz, destino, sha)
    assert res.estado == g.PUBLICADO, res
    assert res.linhas == 2
    assert res.descartes == {"cabecalho": 1, "vazias": 2}
    # pontas aparadas, texto da fonte intocado, uma linha por termo
    assert _termos(spark, destino) == [(t, d, sha) for t, d in sorted(ESPERADO)]


def test_linhagem_da_bronze_no_commit(spark, tmp_path, destino):
    raiz, sha = _bronze_de(spark, tmp_path, GLOSSARIO)
    versao_bronze = bronze._versao_atual(spark, str(raiz / "glossario"))
    res = _publicar(spark, raiz, destino, sha, id_execucao="exec-1")
    assert res.estado == g.PUBLICADO
    meta = _meta_do_commit(spark, destino, res.versao)
    assert meta["versao_bronze"] == versao_bronze == res.versao_bronze
    assert meta["sha256"] == sha
    assert meta["descartes"] == {"cabecalho": 1, "vazias": 2}
    assert meta["id_execucao"] == "exec-1"


def test_treze_termos_na_referencia_real(spark, tmp_path, destino):
    """O glossário real do INSS, lido de /dados/_raw só para montar o landing."""
    origem = Path("/dados/_raw")
    landing = tmp_path / "landing"
    assert lr.gravar(spark, str(origem), str(landing)) == {DICIO: lr.GRAVADO, GLOSS: lr.GRAVADO}
    dados = (origem / GLOSS).read_bytes()
    raiz = tmp_path / "bronze"
    assert br.publicar(spark, str(landing), str(raiz), GLOSS, _sha(dados)).estado == br.PUBLICADO
    res = _publicar(spark, raiz, destino, _sha(dados))
    assert res.estado == g.PUBLICADO, res
    assert res.linhas == 13
    assert len(_termos(spark, destino)) == 13
    assert res.descartes["cabecalho"] == 1
    assert res.descartes["vazias"] == 10


def test_le_a_bronze_na_versao_fixada(spark, tmp_path, destino, monkeypatch):
    """Um commit novo na Bronze DEPOIS de fixada a versão não entra na leitura nem na linhagem."""
    raiz, sha = _bronze_de(spark, tmp_path, GLOSSARIO)
    fixada = bronze._versao_atual(spark, str(raiz / "glossario"))
    outro = _xlsx([(1, "Nome", "Descrição"), (2, "Intruso", "de outro arquivo")])
    outro_landing = _landing(spark, tmp_path, _xlsx(DICIONARIO_SINTETICO), outro, nome="raw2")
    original = g._ler_da_bronze

    def com_commit_no_meio(spark_, caminho, versao, sha_):
        assert br.publicar(spark_, str(outro_landing), str(raiz), GLOSS, _sha(outro)).estado == br.PUBLICADO
        return original(spark_, caminho, versao, sha_)

    monkeypatch.setattr(g, "_ler_da_bronze", com_commit_no_meio)
    res = _publicar(spark, raiz, destino, sha)
    assert res.estado == g.PUBLICADO
    assert bronze._versao_atual(spark, str(raiz / "glossario")) > fixada
    assert res.versao_bronze == fixada
    assert _meta_do_commit(spark, destino, res.versao)["versao_bronze"] == fixada
    assert [t for t, *_ in _termos(spark, destino)] == sorted(t for t, _ in ESPERADO)  # sem o "Intruso"


def test_seleciona_o_sha256_pedido_antes_de_conformar(spark, tmp_path, destino):
    """Dois glossários na Bronze: o termo repetido ENTRE arquivos não é repetido."""
    raiz, sha = _bronze_de(spark, tmp_path, GLOSSARIO)
    outro = _xlsx([(1, "Nome", "Descrição"), (2, "Renda", "outra descrição")])
    landing = _landing(spark, tmp_path, _xlsx(DICIONARIO_SINTETICO), outro, nome="raw2")
    assert br.publicar(spark, str(landing), str(raiz), GLOSS, _sha(outro)).estado == br.PUBLICADO
    res = _publicar(spark, raiz, destino, sha)
    assert res.estado == g.PUBLICADO
    assert _termos(spark, destino, _sha(outro)) == []


def test_republicar_mesmo_sha_nao_duplica(spark, tmp_path, destino):
    raiz, sha = _bronze_de(spark, tmp_path, GLOSSARIO)
    assert _publicar(spark, raiz, destino, sha).estado == g.PUBLICADO
    assert _publicar(spark, raiz, destino, sha).estado == g.PUBLICADO
    assert len(_termos(spark, destino)) == len(ESPERADO)


def test_reconfere_o_proprio_commit(spark, tmp_path, destino):
    """O que se confere é a versão do PRÓPRIO commit, com os dois sentidos zerados."""
    raiz, sha = _bronze_de(spark, tmp_path, GLOSSARIO)
    res = _publicar(spark, raiz, destino, sha)
    assert res.estado == g.PUBLICADO
    assert res.detalhe == {"versao": res.versao, "so_no_esperado": 0, "so_no_lido": 0}


@pytest.mark.parametrize("defeito", ["a_menos", "a_mais"])
def test_reconfere_o_proprio_commit_acusa_termo_a_menos_e_a_mais(spark, tmp_path, destino, monkeypatch, defeito):
    raiz, sha = _bronze_de(spark, tmp_path, GLOSSARIO)
    original = g._lidas

    def adulterada(spark_, caminho, versao, sha_):
        lido = original(spark_, caminho, versao, sha_)
        alvo = "termo = 'Renda'"
        return lido.where("termo <> 'Renda'") if defeito == "a_menos" else lido.unionAll(lido.where(alvo))

    monkeypatch.setattr(g, "_lidas", adulterada)
    res = _publicar(spark, raiz, destino, sha)
    assert res.estado == g.DIVERGE
    assert res.detalhe["so_no_esperado" if defeito == "a_menos" else "so_no_lido"] == 1
    monkeypatch.setattr(g, "_lidas", original)
    assert _termos(spark, destino, sha) == []  # revertido


# ---------------------------------------------------------------- B-2


def test_termo_repetido_recusa(spark, tmp_path, destino):
    raiz, sha = _bronze_de(spark, tmp_path, [(1, "Nome", "Descrição"), (2, "Renda", "a"), (3, "Renda", "b")])
    res = _publicar(spark, raiz, destino, sha)
    assert res.estado == g.RECUSADO
    assert res.motivo.startswith("TERMO_REPETIDO")
    assert not destino.exists()


def test_termo_repetido_so_depois_de_aparar_recusa(spark, tmp_path, destino):
    raiz, sha = _bronze_de(spark, tmp_path, [(1, "Nome", "Descrição"), (2, "Renda", "a"), (3, "  Renda ", "b")])
    res = _publicar(spark, raiz, destino, sha)
    assert res.estado == g.RECUSADO
    assert res.motivo.startswith("TERMO_REPETIDO")
    assert not destino.exists()


def test_termo_vazio_recusa(spark, tmp_path, destino):
    raiz, sha = _bronze_de(spark, tmp_path, [(1, "Nome", "Descrição"), (2, "Renda", "a"), (3, None, "só a descrição")])
    res = _publicar(spark, raiz, destino, sha)
    assert (res.estado, res.motivo) == (g.RECUSADO, "TERMO_VAZIO")
    assert not destino.exists()


def test_sem_termos_nao_medido(spark, tmp_path, destino):
    raiz, sha = _bronze_de(spark, tmp_path, [(1, "Nome", "Descrição"), (2, None, None)])
    res = _publicar(spark, raiz, destino, sha)
    assert (res.estado, res.motivo) == (g.NAO_MEDIDO, "NENHUM_TERMO")
    assert res.descartes == {"cabecalho": 1, "vazias": 1}
    assert not destino.exists()

    # sha256 ausente da versão lida
    ausente = "a" * 64
    res = _publicar(spark, raiz, destino, ausente)
    assert (res.estado, res.motivo) == (g.NAO_MEDIDO, "SHA256_AUSENTE_DA_BRONZE")
    assert not destino.exists()


def test_glossario_nao_aprovado_recusa(spark, tmp_path, destino):
    raiz, sha = _bronze_de(spark, tmp_path, GLOSSARIO)
    res = _publicar(spark, raiz, destino, sha, aprovado="0" * 64)
    assert (res.estado, res.motivo) == (g.RECUSADO, "GLOSSARIO_NAO_APROVADO")
    assert not destino.exists()
    # SEM ler: com uma Bronze que nem existe, a recusa é a mesma, não NAO_MEDIDO
    res = g.publicar(spark, str(tmp_path / "nao-existe"), str(destino), sha, "0" * 64)
    assert (res.estado, res.motivo) == (g.RECUSADO, "GLOSSARIO_NAO_APROVADO")
    assert not destino.exists()
