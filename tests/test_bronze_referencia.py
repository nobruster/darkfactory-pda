"""Testes da Bronze da referência — linhas como vieram, lidas do landing.

Rodam DENTRO do contêiner pda-spark. Gravam só em tmp_path; o que vem da origem bruta
(`/dados/_raw`) é só LIDO, e a ausência dele faz o teste falhar.
"""

from __future__ import annotations

import ast
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from medalhao import bronze, bronze_referencia as br  # noqa: E402
from produtor import landing_referencia as lr  # noqa: E402

DICIO, GLOSS = lr.ARQUIVOS
COLUNAS = ("linha", "coluna_a", "coluna_b", "arquivo", "sha256_arquivo")

_NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
_NS_REL = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
_NS_PACOTE = "http://schemas.openxmlformats.org/package/2006/relationships"


def _sha(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


@pytest.fixture(scope="session")
def spark():
    return bronze.criar_sessao("teste-bronze-referencia")


# ---------------------------------------------------------------- xlsx sintético


def _celula(ref: str, valor, compartilhadas: list | None) -> str:
    if valor is None:
        return ""
    if compartilhadas is not None:
        compartilhadas.append(valor)
        return f'<c r="{ref}" t="s"><v>{len(compartilhadas) - 1}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{escape(valor)}</t></is></c>'


def _xlsx(linhas, planilhas: int = 1, compartilhado: bool = False) -> bytes:
    """`linhas` = [(número_da_linha, A, B)]; A/B None = célula ausente; ambos None = <row> sem valor."""
    strings: list | None = [] if compartilhado else None
    corpo = ""
    for numero, a, b in linhas:
        celulas = _celula(f"A{numero}", a, strings) + _celula(f"B{numero}", b, strings)
        corpo += f'<row r="{numero}">{celulas}</row>' if celulas else f'<row r="{numero}"/>'
    folha = f'<worksheet {_NS}><sheetData>{corpo}</sheetData></worksheet>'
    abas = "".join(f'<sheet name="P{i}" sheetId="{i}" r:id="rId{i}"/>' for i in range(1, planilhas + 1))
    livro = f"<workbook {_NS} {_NS_REL}><sheets>{abas}</sheets></workbook>"
    relacoes = "".join(
        f'<Relationship Id="rId{i}" Type="worksheet" Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, planilhas + 1)
    )
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as z:
        z.writestr("xl/workbook.xml", livro)
        z.writestr("xl/_rels/workbook.xml.rels", f'<Relationships xmlns="{_NS_PACOTE}">{relacoes}</Relationships>')
        for i in range(1, planilhas + 1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", folha)
        if strings is not None:
            itens = "".join(f'<si><t xml:space="preserve">{escape(s)}</t></si>' for s in strings)
            z.writestr("xl/sharedStrings.xml", f"<sst {_NS}>{itens}</sst>")
    return saida.getvalue()


LINHAS = [
    (1, "Código", "Descrição"),
    (3, "01", "  Aposentadoria por idade  "),
    (5, None, None),
    (8, "42", None),
    (9, None, "só a descrição"),
]

GLOSSARIO = [(1, "Nome", "Descrição"), (2, "Espécie", "Tipo de benefício"), (4, None, None)]


# ---------------------------------------------------------------- landing


def _landing(spark, tmp_path, dicio: bytes, gloss: bytes | None = None, nome: str = "raw") -> Path:
    """O landing gravado por landing_referencia, em tmp_path."""
    origem = tmp_path / nome
    origem.mkdir()
    arquivos = {DICIO: dicio, GLOSS: gloss if gloss is not None else _xlsx(GLOSSARIO)}
    for arquivo, dados in arquivos.items():
        (origem / arquivo).write_bytes(dados)
    (origem / "CHECKSUMS.txt").write_text(
        "".join(f"{_sha(d)}  _raw/{n}\n" for n, d in arquivos.items()), encoding="utf-8"
    )
    landing = tmp_path / "landing"
    res = lr.gravar(spark, str(origem), str(landing))
    assert res == {DICIO: lr.GRAVADO, GLOSS: lr.GRAVADO}
    return landing


@pytest.fixture
def destino(tmp_path):
    return tmp_path / "bronze"


def _publicar(spark, landing, destino, arquivo, dados, **kw):
    return br.publicar(spark, str(landing), str(destino), arquivo, _sha(dados), **kw)


def _tabela(spark, destino: Path, nome: str):
    return spark.read.format("delta").load(str(destino / nome))


def _registros(spark, destino: Path, nome: str, sha: str | None = None) -> list[tuple]:
    df = _tabela(spark, destino, nome)
    if sha is not None:
        df = df.where(df.sha256_arquivo == sha)
    return sorted((tuple(r) for r in df.select(*COLUNAS).collect()), key=lambda t: (t[4], t[0]))


def _historico(spark, destino: Path, nome: str) -> list[dict]:
    from delta.tables import DeltaTable

    linhas = DeltaTable.forPath(spark, str(destino / nome)).history().select("version", "userMetadata").collect()
    return [{"versao": r["version"], "meta": r["userMetadata"]} for r in sorted(linhas, key=lambda r: r["version"])]


# ---------------------------------------------------------------- B-1


def test_padroes():
    assert br.LANDING_PADRAO == "s3a://landing/pda/referencia"
    assert br.DESTINO_PADRAO == "s3a://bronze/pda/referencia"
    assert br.TABELAS == {DICIO: "dicionario_especies", GLOSS: "glossario"}


def test_publica_as_linhas_como_vieram_dicionario_e_glossario(spark, tmp_path, destino):
    dicio, gloss = _xlsx(LINHAS, compartilhado=True), _xlsx(GLOSSARIO)
    landing = _landing(spark, tmp_path, dicio, gloss)
    r1 = _publicar(spark, landing, destino, DICIO, dicio)
    r2 = _publicar(spark, landing, destino, GLOSS, gloss)
    assert (r1.estado, r2.estado) == (br.PUBLICADO, br.PUBLICADO)
    assert (r1.linhas, r2.linhas) == (len(LINHAS), len(GLOSSARIO))
    sd, sg = _sha(dicio), _sha(gloss)
    # texto sem trim, célula ausente nula, dois destinos distintos
    assert _registros(spark, destino, "dicionario_especies") == [
        (n, a, b, DICIO, sd) for n, a, b in LINHAS
    ]
    assert _registros(spark, destino, "glossario") == [(n, a, b, GLOSS, sg) for n, a, b in GLOSSARIO]


def test_linhas_como_vieram_dos_bytes_do_real(spark, tmp_path, destino):
    """Os dois arquivos reais do INSS, lidos de /dados/_raw só para montar o landing."""
    origem = Path("/dados/_raw")
    landing = tmp_path / "landing"
    res = lr.gravar(spark, str(origem), str(landing))
    assert res == {DICIO: lr.GRAVADO, GLOSS: lr.GRAVADO}
    esperado = {DICIO: (69, 2), GLOSS: (24, 10)}
    for arquivo, (total, vazias) in esperado.items():
        dados = (origem / arquivo).read_bytes()
        r = br.publicar(spark, str(landing), str(destino), arquivo, _sha(dados))
        assert r.estado == br.PUBLICADO, r
        tabela = br.TABELAS[arquivo]
        regs = _registros(spark, destino, tabela)
        assert len(regs) == total
        assert sum(1 for _, a, b, *_ in regs if a is None and b is None) == vazias


def test_cabecalho_e_vazias_entram(spark, tmp_path, destino):
    dicio = _xlsx(LINHAS)
    landing = _landing(spark, tmp_path, dicio)
    assert _publicar(spark, landing, destino, DICIO, dicio).estado == br.PUBLICADO
    regs = {n: (a, b) for n, a, b, *_ in _registros(spark, destino, "dicionario_especies")}
    assert regs[1] == ("Código", "Descrição")  # o cabeçalho não é filtrado
    assert regs[5] == (None, None)  # a <row> sem valor entra
    assert regs[8] == ("42", None)
    assert regs[9] == (None, "só a descrição")


def test_numero_da_linha_e_o_do_xml(spark, tmp_path, destino):
    dicio = _xlsx([(4, "a", "b"), (11, None, None), (12, "c", "d")])
    landing = _landing(spark, tmp_path, dicio)
    assert _publicar(spark, landing, destino, DICIO, dicio).estado == br.PUBLICADO
    numeros = [t[0] for t in _registros(spark, destino, "dicionario_especies")]
    assert numeros == [4, 11, 12]  # o atributo r, nunca uma contagem 1..n


def test_linhagem_do_landing_no_commit(spark, tmp_path, destino):
    dicio = _xlsx(LINHAS)
    landing = _landing(spark, tmp_path, dicio)
    res = _publicar(spark, landing, destino, DICIO, dicio, id_execucao="exec-1")
    assert res.estado == br.PUBLICADO
    meta = json.loads(
        next(h["meta"] for h in _historico(spark, destino, "dicionario_especies") if h["versao"] == res.versao)
    )
    assert meta["particao_landing"] == f"{landing}/dicionario-especies-beneficio/sha256={_sha(dicio)}"
    assert meta["sha256_prova"] == _sha(dicio)
    assert meta["id_execucao"] == "exec-1"
    assert meta["linhas"] == len(LINHAS)


# ---------------------------------------------------------------- reconferência e idempotência


def test_reconfere_o_proprio_commit(spark, tmp_path, destino):
    """Com um commit de OUTRA partição depois, a versão conferida continua sendo a do próprio commit."""
    v1, v2 = _xlsx(LINHAS), _xlsx(LINHAS + [(20, "novo", "outro")])
    landing = _landing(spark, tmp_path, v1, nome="raw1")
    lr.gravar(spark, *_origem_de(tmp_path, "raw2", v2))
    r1 = _publicar(spark, landing, destino, DICIO, v1)
    r2 = _publicar(spark, landing, destino, DICIO, v2)
    assert (r1.estado, r2.estado) == (br.PUBLICADO, br.PUBLICADO)
    assert r2.versao > r1.versao
    assert r1.detalhe == {"versao": r1.versao, "so_no_esperado": 0, "so_no_lido": 0}
    lido = spark.read.format("delta").option("versionAsOf", r1.versao).load(str(destino / "dicionario_especies"))
    assert lido.count() == len(LINHAS)  # a versão do primeiro commit ainda só tem o primeiro arquivo


def _origem_de(tmp_path, nome: str, dicio: bytes):
    """(origem, destino) para gravar OUTRO dicionário no MESMO landing."""
    origem = tmp_path / nome
    origem.mkdir()
    (origem / DICIO).write_bytes(dicio)
    (origem / "CHECKSUMS.txt").write_text(f"{_sha(dicio)}  _raw/{DICIO}\n", encoding="utf-8")
    return str(origem), str(tmp_path / "landing"), (DICIO,)


@pytest.mark.parametrize("defeito", ["a_menos", "a_mais"])
def test_reconfere_o_proprio_commit_acusa_linha_a_menos_e_a_mais(spark, tmp_path, destino, monkeypatch, defeito):
    dicio = _xlsx(LINHAS)
    landing = _landing(spark, tmp_path, dicio)
    original = br._lidas

    def adulterada(spark_, caminho, versao, sha):
        lido = original(spark_, caminho, versao, sha)
        return lido.where("linha <> 3") if defeito == "a_menos" else lido.unionAll(lido.where("linha = 3"))

    monkeypatch.setattr(br, "_lidas", adulterada)
    res = _publicar(spark, landing, destino, DICIO, dicio)
    assert res.estado == br.DIVERGE
    assert res.detalhe["so_no_esperado" if defeito == "a_menos" else "so_no_lido"] == 1
    monkeypatch.setattr(br, "_lidas", original)
    assert _registros(spark, destino, "dicionario_especies", _sha(dicio)) == []  # revertido


def test_republicar_mesmo_sha_substitui_so_a_particao(spark, tmp_path, destino):
    v1, v2 = _xlsx(LINHAS), _xlsx(LINHAS + [(20, "novo", "outro")])
    landing = _landing(spark, tmp_path, v1, nome="raw1")
    lr.gravar(spark, *_origem_de(tmp_path, "raw2", v2))
    for dados in (v1, v2):
        assert _publicar(spark, landing, destino, DICIO, dados).estado == br.PUBLICADO
    do_v2 = _registros(spark, destino, "dicionario_especies", _sha(v2))
    assert len(do_v2) == len(LINHAS) + 1

    de_novo = _publicar(spark, landing, destino, DICIO, v1)
    assert de_novo.estado == br.PUBLICADO
    assert len(_registros(spark, destino, "dicionario_especies", _sha(v1))) == len(LINHAS)  # sem duplicar
    assert _registros(spark, destino, "dicionario_especies", _sha(v2)) == do_v2  # a outra partição intacta
    assert len(_registros(spark, destino, "dicionario_especies")) == 2 * len(LINHAS) + 1


# ---------------------------------------------------------------- B-2


def test_prova_divergente_nao_grava(spark, tmp_path, destino):
    dicio = _xlsx(LINHAS)
    landing = _landing(spark, tmp_path, dicio)
    pasta = landing / "dicionario-especies-beneficio" / f"sha256={_sha(dicio)}"

    # 1) a prova diz outro sha256
    prova = json.loads((pasta / "_PROCEDENCIA.json").read_text(encoding="utf-8"))
    (pasta / "_PROCEDENCIA.json").write_text(json.dumps({**prova, "sha256": "0" * 64}), encoding="utf-8")
    r = _publicar(spark, landing, destino, DICIO, dicio)
    assert (r.estado, r.motivo) == (br.RECUSADO, "SHA256_DIVERGENTE")
    assert not destino.exists()

    # 2) a prova está certa, os bytes da partição não são os do nome
    (pasta / "_PROCEDENCIA.json").write_text(json.dumps(prova), encoding="utf-8")
    (pasta / DICIO).write_bytes(dicio + b"\x00")
    r = _publicar(spark, landing, destino, DICIO, dicio)
    assert (r.estado, r.motivo) == (br.RECUSADO, "SHA256_DIVERGENTE")
    assert not destino.exists()


def test_prova_divergente_nao_grava_pedidos_invalidos(spark, tmp_path, destino):
    dicio = _xlsx(LINHAS)
    landing = _landing(spark, tmp_path, dicio)
    assert br.publicar(spark, str(landing), str(destino), "outro.xlsx", _sha(dicio)).estado == br.RECUSADO
    assert br.publicar(spark, str(landing), str(destino), DICIO, "../x").estado == br.RECUSADO
    assert br.publicar(spark, str(landing), str(destino), DICIO, "a" * 64).estado == br.NAO_MEDIDO  # sem partição
    assert not destino.exists()


def test_planilha_vazia_nao_medido(spark, tmp_path, destino):
    vazio = _xlsx([])
    landing = _landing(spark, tmp_path, vazio)
    res = _publicar(spark, landing, destino, DICIO, vazio)
    assert res.estado == br.NAO_MEDIDO
    assert not destino.exists()


def test_mais_de_uma_planilha_recusa(spark, tmp_path, destino):
    duas = _xlsx(LINHAS, planilhas=2)
    landing = _landing(spark, tmp_path, duas)
    res = _publicar(spark, landing, destino, DICIO, duas)
    assert res.estado == br.RECUSADO
    assert "2 planilhas" in res.motivo
    assert not destino.exists()


def test_modulo_nao_le_raw():
    fonte = Path(br.__file__).read_text(encoding="utf-8")
    arvore = ast.parse(fonte)
    nomes = [n.value for n in ast.walk(arvore) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    nomes += [n.id for n in ast.walk(arvore) if isinstance(n, ast.Name)]
    nomes += [n.attr for n in ast.walk(arvore) if isinstance(n, ast.Attribute)]
    nomes += [a.name for n in ast.walk(arvore) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names]
    nomes += [n.module or "" for n in ast.walk(arvore) if isinstance(n, ast.ImportFrom)]
    assert not [n for n in nomes if "_raw" in n or "/dados" in n or "ontologia" in n]
