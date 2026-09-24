"""Testes da ontologia versionada — reconferida contra os bytes reais de /dados/_raw.

Rodam DENTRO do contêiner pda-spark. Os cenários de recusa trabalham em cópias sob `tmp_path`
e nunca alteram /dados/_raw. Fonte ausente no ambiente FALHA o teste: nada aqui pula.
"""

from __future__ import annotations

import ast
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from medalhao import ontologia as onto  # noqa: E402
from medalhao.ontologia import NAO_MEDIDO, OntologiaRecusada, carregar_ontologia  # noqa: E402

RAW = Path("/dados/_raw")
ARQ_ONTOLOGIA = onto.ARQUIVO_ONTOLOGIA
ARQ_CONTRATO = onto.ARQUIVO_CONTRATO
ARQ_DICIONARIO = "dicionario-especies-beneficio.xlsx"
ARQ_GLOSSARIO = "glossario-beneficios-emitidos.xlsx"
CSV_FONTE = "D.SDA.PDA.003.EMI.202601.csv"


# ---------------------------------------------------------------- apoio


def _cenario(tmp_path):
    """Cópias pequenas: os dois .xlsx, o cabeçalho do CSV do contrato, CHECKSUMS, ontologia, contrato."""
    raw = tmp_path / "_raw"
    raw.mkdir()
    for nome in (ARQ_DICIONARIO, ARQ_GLOSSARIO):
        shutil.copy(RAW / nome, raw / nome)
    with open(RAW / CSV_FONTE, "rb") as f:
        (raw / CSV_FONTE).write_bytes(f.readline())
    linhas = [
        linha
        for linha in (RAW / "CHECKSUMS.txt").read_text(encoding="utf-8").splitlines()
        if linha.endswith((ARQ_DICIONARIO, ARQ_GLOSSARIO))
    ]
    assert len(linhas) == 2
    (raw / "CHECKSUMS.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    ontologia = tmp_path / "beneficios-emitidos.yaml"
    shutil.copy(ARQ_ONTOLOGIA, ontologia)
    contrato = tmp_path / "competencia-202601.yaml"
    shutil.copy(ARQ_CONTRATO, contrato)
    return raw, ontologia, contrato


def _editar(caminho, mexer):
    dados = yaml.safe_load(Path(caminho).read_text(encoding="utf-8"))
    mexer(dados)
    Path(caminho).write_text(
        yaml.safe_dump(dados, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def _carregar(raw, ontologia, contrato):
    return carregar_ontologia(ontologia, contrato, raw)


def _recusa(raw, ontologia, contrato):
    with pytest.raises(OntologiaRecusada) as erro:
        _carregar(raw, ontologia, contrato)
    return erro.value.motivo


def _xlsx_minimo(caminho, linhas):
    """Planilha mínima (strings inline), só com a biblioteca padrão."""
    corpo = ""
    for i, (a, b) in enumerate(linhas, start=1):
        corpo += (
            f'<row r="{i}"><c r="A{i}" t="inlineStr"><is><t>{a}</t></is></c>'
            f'<c r="B{i}" t="inlineStr"><is><t>{b}</t></is></c></row>'
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{corpo}</sheetData></worksheet>"
    )
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("xl/worksheets/sheet1.xml", xml)


# ---------------------------------------------------------------- B-1: a ontologia real confere


def test_ontologia_real_confere():
    o = carregar_ontologia()
    assert not isinstance(o, str), f"esperava a ontologia, veio {o!r} ({getattr(o, 'motivo', '')})"
    assert len(o.colunas) == 14
    assert len(o.termos) == 13
    assert len(o.especies) == 65
    for chave, arquivo in (("dicionario", ARQ_DICIONARIO), ("glossario", ARQ_GLOSSARIO)):
        real = hashlib.sha256((RAW / arquivo).read_bytes()).hexdigest()
        assert o.fontes[chave]["sha256"] == real
        assert f"{real}  _raw/{arquivo}" in (RAW / "CHECKSUMS.txt").read_text(encoding="utf-8")


def test_sessenta_e_cinco_especies_com_nome_oficial_e_grupo_do_contrato():
    o = carregar_ontologia()
    assert len(o.especies) == 65
    dicionario = onto._especies_do_dicionario(onto.ler_xlsx(RAW / ARQ_DICIONARIO))
    contrato = yaml.safe_load(ARQ_CONTRATO.read_text(encoding="utf-8"))
    grupo_de = {
        c: g["grupo"] for g in contrato["grupos_especie"]["grupos"] for c in g["codigos"]
    }
    for e in o.especies:
        assert len(e["codigo"]) == 2 and e["codigo"].isdigit()
        assert e["nome"] == dicionario[e["codigo"]]
        assert e["grupo"] == grupo_de[e["codigo"]]
    assert {e["codigo"] for e in o.especies} == set(dicionario)


def test_catorze_colunas_por_posicao_com_as_duas_especie():
    o = carregar_ontologia()
    assert [c["posicao"] for c in o.colunas] == list(range(14))
    with open(RAW / CSV_FONTE, "rb") as f:
        cabecalho = f.readline().decode("latin-1").rstrip("\r\n").split(";")
    assert [c["cabecalho"] for c in o.colunas] == cabecalho
    c12, c13 = o.colunas[12], o.colunas[13]
    assert (c12["cabecalho"], c12["papel"]) == ("Espécie", "codigo")
    assert (c13["cabecalho"], c13["papel"]) == ("Espécie", "descricao_truncada")
    assert c12["termo"] == c13["termo"] == "Espécie"


def test_sha256_cobre_os_grupos(tmp_path):
    raw, ontologia, contrato = _cenario(tmp_path)
    antes = _carregar(raw, ontologia, contrato)
    assert antes.sha256 == carregar_ontologia().sha256

    def mover(dados):
        grupos = {g["grupo"]: g["codigos"] for g in dados["grupos_especie"]["grupos"]}
        grupos["Outros"].remove("79")
        grupos["Auxilio"].append("79")

    _editar(contrato, mover)
    depois = _carregar(raw, ontologia, contrato)
    assert depois.sha256 != antes.sha256
    assert len(depois.sha256) == 64


# ---------------------------------------------------------------- B-2: divergência recusa com motivo


def test_sha256_divergente_recusa(tmp_path):
    raw, ontologia, contrato = _cenario(tmp_path)
    _editar(ontologia, lambda d: d["fontes"]["dicionario"].update(sha256="0" * 64))
    assert _recusa(raw, ontologia, contrato) == "SHA256_DIVERGENTE"


def test_checksums_divergente_recusa(tmp_path):
    raw, ontologia, contrato = _cenario(tmp_path)
    texto = (raw / "CHECKSUMS.txt").read_text(encoding="utf-8")
    real = hashlib.sha256((raw / ARQ_GLOSSARIO).read_bytes()).hexdigest()
    (raw / "CHECKSUMS.txt").write_text(texto.replace(real, "f" * 64), encoding="utf-8")
    assert _recusa(raw, ontologia, contrato) == "CHECKSUMS_DIVERGENTE"


def test_nome_diferente_recusa(tmp_path):
    raw, ontologia, contrato = _cenario(tmp_path)
    _editar(ontologia, lambda d: d["especies"][0].update(nome="Pensão por Morte de Trab. Rural"))
    assert _recusa(raw, ontologia, contrato) == "NOME_DIFERENTE_DO_DICIONARIO"


def test_codigo_sem_grupo_recusa(tmp_path):
    raw, ontologia, contrato = _cenario(tmp_path)

    def tirar(dados):
        dados["grupos_especie"]["grupos"][2]["codigos"].remove("16")
        dados["cardinalidade"]["codigos_distintos"] = 64

    _editar(contrato, tirar)
    assert _recusa(raw, ontologia, contrato) == "CODIGO_SEM_GRUPO"


def test_codigo_em_dois_grupos_recusa(tmp_path):
    raw, ontologia, contrato = _cenario(tmp_path)
    _editar(contrato, lambda d: d["grupos_especie"]["grupos"][2]["codigos"].append("01"))
    assert _recusa(raw, ontologia, contrato) == "CODIGO_EM_DOIS_GRUPOS"


def test_termo_fora_do_glossario_recusa(tmp_path):
    raw, ontologia, contrato = _cenario(tmp_path)
    _editar(ontologia, lambda d: d["termos"][1].update(nome="Termo Inventado"))
    assert _recusa(raw, ontologia, contrato) == "TERMO_FORA_DO_GLOSSARIO"


def test_descricao_de_termo_diferente_recusa(tmp_path):
    raw, ontologia, contrato = _cenario(tmp_path)
    _editar(ontologia, lambda d: d["termos"][3].update(descricao="Sexo do beneficiário."))
    assert _recusa(raw, ontologia, contrato) == "DESCRICAO_DE_TERMO_DIFERENTE"


def test_cabecalho_trocado_recusa(tmp_path):
    raw, ontologia, contrato = _cenario(tmp_path)
    _editar(ontologia, lambda d: d["colunas"][3].update(cabecalho="Tipo de Benefício"))
    assert _recusa(raw, ontologia, contrato) == "CABECALHO_DIFERENTE_DO_CSV"


def test_posicao_repetida_recusa(tmp_path):
    raw, ontologia, contrato = _cenario(tmp_path)
    _editar(ontologia, lambda d: d["colunas"][13].update(posicao=12))
    assert _recusa(raw, ontologia, contrato) == "POSICAO_REPETIDA"


def test_posicao_faltando_recusa(tmp_path):
    raw, ontologia, contrato = _cenario(tmp_path)
    _editar(ontologia, lambda d: d["colunas"].pop())
    assert _recusa(raw, ontologia, contrato) == "POSICAO_FALTANDO"


def test_csv_de_outro_layout_ignorado(tmp_path):
    raw, ontologia, contrato = _cenario(tmp_path)
    esperado = _carregar(raw, ontologia, contrato)
    # 2025-07: 13 colunas, uma só 'Espécie' na posição 0 — não é a fonte do contrato.
    (raw / "D.SDA.PDA.003.EMI.202507.csv").write_bytes(
        "Espécie;Despacho;Sexo;Clientela;Tipo Benefício;UF;Meio pagamento;Banco;Mun Pagto;"
        "Mun Resid;Vl Líquido;Ramo Atividade;Dt início validade\r\n".encode("latin-1")
    )
    assert _carregar(raw, ontologia, contrato).sha256 == esperado.sha256


# ---------------------------------------------------------------- Regra 9: ausência não é medição


def test_dicionario_vazio_nao_medido(tmp_path):
    raw, ontologia, contrato = _cenario(tmp_path)
    _xlsx_minimo(raw / ARQ_DICIONARIO, [("Código", "Benefício")])
    resultado = _carregar(raw, ontologia, contrato)
    assert resultado == NAO_MEDIDO and isinstance(resultado, str)
    assert resultado.motivo == "ZERO_ESPECIES_LIDAS"


def test_glossario_vazio_nao_medido(tmp_path):
    raw, ontologia, contrato = _cenario(tmp_path)
    _xlsx_minimo(raw / ARQ_GLOSSARIO, [("Nome", "Descrição")])
    resultado = _carregar(raw, ontologia, contrato)
    assert resultado == NAO_MEDIDO
    assert resultado.motivo == "ZERO_TERMOS_LIDOS"


def test_fonte_ausente_nao_medido(tmp_path):
    raw, ontologia, contrato = _cenario(tmp_path)
    (raw / ARQ_GLOSSARIO).unlink()
    assert _carregar(raw, ontologia, contrato) == NAO_MEDIDO
    (tmp_path / "outro").mkdir()
    raw2, ontologia2, contrato2 = _cenario(tmp_path / "outro")
    (raw2 / CSV_FONTE).unlink()
    resultado = _carregar(raw2, ontologia2, contrato2)
    assert resultado == NAO_MEDIDO
    assert resultado.motivo.startswith("CSV_DA_FONTE_AUSENTE")


def test_contrato_nao_medido_recusa(tmp_path):
    raw, ontologia, contrato = _cenario(tmp_path)
    _editar(contrato, lambda d: d.pop("ancora"))
    assert _recusa(raw, ontologia, contrato) == "CONTRATO_NAO_MEDIDO"
    _editar(contrato, lambda d: d.update(ancora={"count_linhas": 1}))
    assert _recusa(raw, ontologia, contrato) == "CONTRATO_NAO_MEDIDO"


def test_contrato_sem_grupos_especie_recusa(tmp_path):
    raw, ontologia, contrato = _cenario(tmp_path)
    _editar(contrato, lambda d: d.pop("grupos_especie"))
    assert _recusa(raw, ontologia, contrato) == "SEM_GRUPOS_ESPECIE"


def test_le_xlsx_sem_dependencia(tmp_path):
    proibidos = {"openpyxl", "pandas", "xlrd"}
    arvore = ast.parse(Path(onto.__file__).read_text(encoding="utf-8"))
    importados = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            importados |= {a.name.split(".")[0] for a in no.names}
        elif isinstance(no, ast.ImportFrom) and no.module:
            importados.add(no.module.split(".")[0])
    assert not (importados & proibidos), importados & proibidos
    assert {"zipfile", "xml"} <= importados

    caminho = tmp_path / "minimo.xlsx"
    _xlsx_minimo(caminho, [("Código", "Benefício"), ("4", "Nome Oficial")])
    assert onto.ler_xlsx(caminho) == [
        {"A": "Código", "B": "Benefício"},
        {"A": "4", "B": "Nome Oficial"},
    ]
