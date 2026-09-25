"""Testes do landing de referência — bytes como vieram, com prova.

Rodam DENTRO do contêiner pda-spark. Gravam só em tmp_path.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from medalhao import bronze  # noqa: E402
from produtor import landing_referencia as lr  # noqa: E402

DICIO, GLOSS = lr.ARQUIVOS
BYTES = {DICIO: b"PK\x03\x04dicionario\x00\xff", GLOSS: b"PK\x03\x04glossario\x00\xfe"}


def _sha(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


@pytest.fixture(scope="session")
def spark():
    sessao = bronze.criar_sessao("teste-landing-referencia")
    yield sessao
    sessao.stop()


@pytest.fixture
def origem(tmp_path):
    pasta = tmp_path / "raw"
    pasta.mkdir()
    for nome, dados in BYTES.items():
        (pasta / nome).write_bytes(dados)
    linhas = [_sha(d) + "  _raw/" + n + "\n" for n, d in BYTES.items()]
    (pasta / "CHECKSUMS.txt").write_text("".join(linhas), encoding="utf-8")
    return pasta


@pytest.fixture
def destino(tmp_path):
    return tmp_path / "landing"


def _pasta(destino: Path, nome: str) -> Path:
    return destino / Path(nome).stem / ("sha256=" + _sha(BYTES[nome]))


def _gravar(spark, origem, destino, arquivos=lr.ARQUIVOS):
    return lr.gravar(spark, str(origem), str(destino), arquivos)


def _arquivos(destino: Path) -> list[Path]:
    return [p for p in destino.rglob("*") if p.is_file() and not p.name.endswith(".crc")]


def _conteudo(destino: Path) -> dict[str, bytes]:
    return {str(p.relative_to(destino)): p.read_bytes() for p in _arquivos(destino)}


def test_padroes():
    assert lr.DESTINO_PADRAO == "s3a://landing/pda/referencia"
    assert lr.ORIGEM_PADRAO == "/dados/_raw"


def test_grava_os_bytes_como_vieram(spark, origem, destino):
    res = _gravar(spark, origem, destino)
    assert res == {DICIO: lr.GRAVADO, GLOSS: lr.GRAVADO}
    for nome, dados in BYTES.items():
        assert (_pasta(destino, nome) / nome).read_bytes() == dados


def test_prova_ao_lado_do_arquivo(spark, origem, destino):
    _gravar(spark, origem, destino)
    for nome, dados in BYTES.items():
        texto = (_pasta(destino, nome) / "_PROCEDENCIA.json").read_text(encoding="utf-8")
        prova = json.loads(texto)
        assert prova["arquivo"] == nome
        assert prova["sha256"] == _sha(dados)
        assert prova["tamanho"] == len(dados)
        assert prova["origem"] == str(origem / nome)
        assert prova["instante"]


def test_rele_e_confere_o_sha256(spark, origem, destino):
    _gravar(spark, origem, destino)
    for nome in BYTES:
        texto = (_pasta(destino, nome) / "_PROCEDENCIA.json").read_text(encoding="utf-8")
        assert _sha((_pasta(destino, nome) / nome).read_bytes()) == json.loads(texto)["sha256"]


def test_segunda_execucao_integro_sem_regravar(spark, origem, destino):
    _gravar(spark, origem, destino)
    antes = _conteudo(destino)
    mtimes = {p: p.stat().st_mtime_ns for p in _arquivos(destino)}
    res = _gravar(spark, origem, destino)
    assert res == {DICIO: lr.INTEGRO, GLOSS: lr.INTEGRO}
    assert _conteudo(destino) == antes
    assert {p: p.stat().st_mtime_ns for p in _arquivos(destino)} == mtimes


def test_objeto_divergente_nao_sobrescreve(spark, origem, destino):
    pasta = _pasta(destino, DICIO)
    pasta.mkdir(parents=True)
    (pasta / DICIO).write_bytes(b"outros bytes")
    res = _gravar(spark, origem, destino)
    assert res[DICIO] == lr.DIVERGE
    assert (pasta / DICIO).read_bytes() == b"outros bytes"
    assert not (pasta / "_PROCEDENCIA.json").exists()
    assert res[GLOSS] == lr.GRAVADO


def test_bytes_sem_prova_diverge(spark, origem, destino):
    pasta = _pasta(destino, DICIO)
    pasta.mkdir(parents=True)
    (pasta / DICIO).write_bytes(BYTES[DICIO])
    res = _gravar(spark, origem, destino)
    assert res[DICIO] == lr.DIVERGE
    assert not (pasta / "_PROCEDENCIA.json").exists()


def test_prova_com_tamanho_divergente_diverge(spark, origem, destino):
    _gravar(spark, origem, destino)
    prova = _pasta(destino, DICIO) / "_PROCEDENCIA.json"
    conteudo = json.loads(prova.read_text(encoding="utf-8"))
    conteudo["tamanho"] += 1
    prova.write_text(json.dumps(conteudo), encoding="utf-8")
    (prova.parent / ("." + prova.name + ".crc")).unlink(missing_ok=True)
    antes = prova.read_bytes()
    assert _gravar(spark, origem, destino)[DICIO] == lr.DIVERGE
    assert prova.read_bytes() == antes


def test_prova_sem_arquivo_diverge(spark, origem, destino):
    pasta = _pasta(destino, DICIO)
    pasta.mkdir(parents=True)
    (pasta / "_PROCEDENCIA.json").write_text("{}", encoding="utf-8")
    res = _gravar(spark, origem, destino)
    assert res[DICIO] == lr.DIVERGE
    assert not (pasta / DICIO).exists()
    assert (pasta / "_PROCEDENCIA.json").read_text(encoding="utf-8") == "{}"


def test_sha256_divergente_nao_grava(spark, origem, destino):
    (origem / DICIO).write_bytes(b"adulterado")
    res = _gravar(spark, origem, destino)
    assert res[DICIO] == lr.NAO_MEDIDO
    assert not (destino / Path(DICIO).stem).exists()


def test_arquivo_ausente_nao_medido(spark, origem, destino):
    (origem / GLOSS).unlink()
    res = _gravar(spark, origem, destino)
    assert res[GLOSS] == lr.NAO_MEDIDO
    assert res[DICIO] == lr.GRAVADO
    assert not (destino / Path(GLOSS).stem).exists()


def test_arquivo_fora_da_lista_recusa(spark, origem, destino):
    (origem / "outro.xlsx").write_bytes(b"x")
    res = _gravar(spark, origem, destino, (DICIO, "outro.xlsx"))
    assert res == {DICIO: lr.GRAVADO, "outro.xlsx": lr.RECUSADO}
    assert not (destino / "outro").exists()


def test_resultado_por_arquivo(spark, origem, destino):
    (origem / DICIO).write_bytes(b"adulterado")
    res = _gravar(spark, origem, destino)
    assert set(res) == {DICIO, GLOSS}
    assert res == {DICIO: lr.NAO_MEDIDO, GLOSS: lr.GRAVADO}
