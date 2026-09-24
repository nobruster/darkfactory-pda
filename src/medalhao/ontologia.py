"""Ontologia versionada dos benefícios emitidos, reconferida contra os bytes do INSS.

Os .xlsx são lidos só com a biblioteca padrão (zipfile e xml): o contêiner não tem rede.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Union
from xml.etree import ElementTree as ET

import yaml

from pda import contrato as contrato_mod

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

NAO_MEDIDO = "NAO_MEDIDO"
DIRETORIO_RAW = Path("/dados/_raw")
RAIZ = Path(__file__).resolve().parent.parent.parent
ARQUIVO_ONTOLOGIA = RAIZ / "src" / "ontologia" / "beneficios-emitidos.yaml"
ARQUIVO_CONTRATO = RAIZ / "contracts" / "competencia-202601.yaml"


class OntologiaRecusada(Exception):
    """A ontologia, uma fonte ou o contrato não conferem — recusada, nunca parcial."""

    def __init__(self, motivo: str, detalhe: str = ""):
        self.motivo = motivo
        self.detalhe = detalhe
        super().__init__(f"{motivo}: {detalhe}" if detalhe else motivo)


class NaoMedido(str):
    """NAO_MEDIDO com a causa: ausência não é medição, e nunca vira OK."""

    motivo: str = ""

    def __new__(cls, motivo: str):
        obj = super().__new__(cls, NAO_MEDIDO)
        obj.motivo = motivo
        return obj


@dataclass(frozen=True)
class Ontologia:
    fontes: dict
    colunas: tuple
    termos: tuple
    especies: tuple
    sha256: str


def _texto(no) -> str:
    return "".join(t.text or "" for t in no.iter(f"{_NS}t"))


def ler_xlsx(caminho) -> List[Dict[str, str]]:
    """Linhas da primeira planilha: cada uma é {letra_da_coluna: texto}; células vazias somem."""
    with zipfile.ZipFile(caminho) as z:
        compartilhadas: List[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            raiz = ET.fromstring(z.read("xl/sharedStrings.xml"))
            compartilhadas = [_texto(si) for si in raiz.iter(f"{_NS}si")]
        planilha = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    linhas: List[Dict[str, str]] = []
    for row in planilha.iter(f"{_NS}row"):
        celulas: Dict[str, str] = {}
        for c in row.iter(f"{_NS}c"):
            coluna = re.match(r"[A-Z]+", c.get("r", "")).group(0)
            tipo = c.get("t")
            v = c.find(f"{_NS}v")
            if tipo == "inlineStr":
                valor = _texto(c)
            elif v is None or v.text is None:
                continue
            elif tipo == "s":
                valor = compartilhadas[int(v.text)]
            else:
                valor = v.text
            celulas[coluna] = valor
        if celulas:
            linhas.append(celulas)
    return linhas


def _sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _checksums(caminho: Path) -> Dict[str, str]:
    """Linhas '<sha256>  _raw/<arquivo>', casadas pelo NOME do arquivo."""
    achados: Dict[str, str] = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        partes = linha.split(None, 1)
        if len(partes) == 2:
            achados[Path(partes[1].strip()).name] = partes[0].lower()
    return achados


def _especies_do_dicionario(linhas) -> Dict[str, str]:
    especies: Dict[str, str] = {}
    for r in linhas:
        codigo = r.get("A", "")
        if not codigo.isdigit():
            continue
        codigo = codigo.zfill(2)
        if codigo in especies:
            raise OntologiaRecusada("CODIGO_REPETIDO_NO_DICIONARIO", codigo)
        especies[codigo] = r.get("B", "")
    return especies


def _termos_do_glossario(linhas) -> Dict[str, str]:
    termos: Dict[str, str] = {}
    for r in linhas[1:]:  # a primeira linha é o cabeçalho Nome/Descrição
        if "A" in r:
            termos[r["A"]] = r.get("B", "")
    return termos


def _contrato(caminho_contrato: Path):
    bruto = yaml.safe_load(caminho_contrato.read_text(encoding="utf-8")) or {}
    vistos: Dict[str, str] = {}
    for g in (bruto.get("grupos_especie") or {}).get("grupos") or []:
        for codigo in g.get("codigos") or []:
            if codigo in vistos:
                raise OntologiaRecusada(
                    "CODIGO_EM_DOIS_GRUPOS", f"{codigo} em {vistos[codigo]} e {g.get('grupo')}"
                )
            vistos[codigo] = g.get("grupo")
    try:
        contrato = contrato_mod.carregar_contrato(caminho_contrato)
    except contrato_mod.ContratoRecusado as erro:
        raise OntologiaRecusada("CONTRATO_RECUSADO", str(erro)) from erro
    if contrato == contrato_mod.NAO_MEDIDO:
        raise OntologiaRecusada("CONTRATO_NAO_MEDIDO", str(caminho_contrato))
    if contrato.grupos_especie is None:
        raise OntologiaRecusada("SEM_GRUPOS_ESPECIE", str(caminho_contrato))
    return contrato


def carregar_ontologia(
    caminho_ontologia=ARQUIVO_ONTOLOGIA,
    caminho_contrato=ARQUIVO_CONTRATO,
    diretorio_raw=DIRETORIO_RAW,
) -> Union[Ontologia, NaoMedido]:
    """Devolve a ontologia só se ela confere com os bytes de _raw/ e com o contrato.

    Levanta OntologiaRecusada, com o motivo nomeado, em qualquer divergência. Devolve NAO_MEDIDO
    (nunca OK) quando algo que precisava ser lido não foi: arquivo ausente, dicionário ou
    glossário sem linha alguma, CSV da fonte do contrato ausente.
    """
    diretorio_raw = Path(diretorio_raw)
    declarada = yaml.safe_load(Path(caminho_ontologia).read_text(encoding="utf-8")) or {}
    contrato = _contrato(Path(caminho_contrato))

    fontes = declarada.get("fontes") or {}
    arquivos = {}
    for chave in ("dicionario", "glossario"):
        fonte = fontes.get(chave) or {}
        caminho = diretorio_raw / str(fonte.get("arquivo", ""))
        if not fonte.get("arquivo") or not caminho.is_file():
            return NaoMedido(f"FONTE_AUSENTE:{fonte.get('arquivo')}")
        arquivos[chave] = caminho
    csv = diretorio_raw / Path(contrato.procedencia.fonte).name
    if not csv.is_file():
        return NaoMedido(f"CSV_DA_FONTE_AUSENTE:{csv.name}")
    caminho_checksums = diretorio_raw / "CHECKSUMS.txt"
    if not caminho_checksums.is_file():
        return NaoMedido("CHECKSUMS_AUSENTE")
    checksums = _checksums(caminho_checksums)

    dicionario = _especies_do_dicionario(ler_xlsx(arquivos["dicionario"]))
    glossario = _termos_do_glossario(ler_xlsx(arquivos["glossario"]))
    if not dicionario:
        return NaoMedido("ZERO_ESPECIES_LIDAS")
    if not glossario:
        return NaoMedido("ZERO_TERMOS_LIDOS")

    for chave, caminho in arquivos.items():
        real = _sha256_arquivo(caminho)
        if real != str(fontes[chave].get("sha256", "")).lower():
            raise OntologiaRecusada("SHA256_DIVERGENTE", f"{caminho.name}: arquivo {real}")
        if caminho.name not in checksums:
            return NaoMedido(f"CHECKSUMS_SEM_LINHA:{caminho.name}")
        if real != checksums[caminho.name]:
            raise OntologiaRecusada("CHECKSUMS_DIVERGENTE", caminho.name)

    layout = contrato.layout
    with open(csv, "rb") as f:
        cabecalho = f.readline().decode(layout.encoding).rstrip("\r\n").split(layout.separador)
    if len(cabecalho) != layout.total_colunas:
        raise OntologiaRecusada(
            "CSV_COM_OUTRO_TOTAL_DE_COLUNAS", f"{len(cabecalho)} != {layout.total_colunas}"
        )

    colunas = list(declarada.get("colunas") or [])
    posicoes = [c.get("posicao") for c in colunas]
    repetidas = sorted({p for p in posicoes if posicoes.count(p) > 1})
    if repetidas:
        raise OntologiaRecusada("POSICAO_REPETIDA", str(repetidas))
    faltando = sorted(set(range(layout.total_colunas)) - set(posicoes))
    sobrando = sorted(set(posicoes) - set(range(layout.total_colunas)))
    if faltando or sobrando:
        raise OntologiaRecusada("POSICAO_FALTANDO", f"faltam {faltando}, sobram {sobrando}")
    for c in colunas:
        if c["cabecalho"] != cabecalho[c["posicao"]]:
            raise OntologiaRecusada(
                "CABECALHO_DIFERENTE_DO_CSV",
                f"posição {c['posicao']}: {c['cabecalho']!r} != {cabecalho[c['posicao']]!r}",
            )

    termos = list(declarada.get("termos") or [])
    for t in termos:
        if t["nome"] not in glossario:
            raise OntologiaRecusada("TERMO_FORA_DO_GLOSSARIO", t["nome"])
        if t["descricao"] != glossario[t["nome"]]:
            raise OntologiaRecusada("DESCRICAO_DE_TERMO_DIFERENTE", t["nome"])
    nomes = [t["nome"] for t in termos]
    if len(set(nomes)) != len(nomes) or set(nomes) != set(glossario):
        raise OntologiaRecusada(
            "TERMOS_DIVERGEM_DO_GLOSSARIO", f"{sorted(set(glossario) ^ set(nomes))}"
        )
    for c in colunas:
        if c["termo"] not in glossario:
            raise OntologiaRecusada("TERMO_FORA_DO_GLOSSARIO", f"coluna {c['posicao']}: {c['termo']}")

    especies = list(declarada.get("especies") or [])
    codigos = [e["codigo"] for e in especies]
    if len(set(codigos)) != len(codigos) or set(codigos) != set(dicionario):
        raise OntologiaRecusada(
            "CODIGOS_DIVERGEM_DO_DICIONARIO", f"{sorted(set(codigos) ^ set(dicionario))}"
        )
    for e in especies:
        if e["nome"] != dicionario[e["codigo"]]:
            raise OntologiaRecusada("NOME_DIFERENTE_DO_DICIONARIO", e["codigo"])

    grupo_de = {codigo: g.grupo for g in contrato.grupos_especie.grupos for codigo in g.codigos}
    sem_grupo = sorted(set(codigos) - set(grupo_de))
    if sem_grupo:
        raise OntologiaRecusada("CODIGO_SEM_GRUPO", str(sem_grupo))
    fora = sorted(set(grupo_de) - set(codigos))
    if fora:
        raise OntologiaRecusada("GRUPO_DE_CODIGO_FORA_DO_DICIONARIO", str(fora))

    resolvido = {
        "fontes": {k: {"arquivo": v["arquivo"], "sha256": v["sha256"]} for k, v in fontes.items()},
        "colunas": sorted(colunas, key=lambda c: c["posicao"]),
        "termos": termos,
        "especies": [
            {"codigo": e["codigo"], "nome": e["nome"], "grupo": grupo_de[e["codigo"]]}
            for e in sorted(especies, key=lambda e: e["codigo"])
        ],
    }
    canonico = json.dumps(resolvido, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return Ontologia(
        fontes=resolvido["fontes"],
        colunas=tuple(resolvido["colunas"]),
        termos=tuple(resolvido["termos"]),
        especies=tuple(resolvido["especies"]),
        sha256=hashlib.sha256(canonico.encode("utf-8")).hexdigest(),
    )
