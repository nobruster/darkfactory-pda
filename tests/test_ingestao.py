"""Testes da ingestão julgada — a Bronze só publica com o juízo do segundo motor.

Rodam DENTRO do contêiner pda-spark. O cenário (lago Parquet, CSV protegido e contrato) é o
mesmo de `test_gold`, derivado do MESMO CSV mínimo. Nada grava no destino real.
"""

from __future__ import annotations

import hashlib
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_gold as tg  # noqa: E402
from medalhao import bronze, ingestao  # noqa: E402
from pda import evidencia, leitura, orquestracao  # noqa: E402

COMP = tg.COMP


@pytest.fixture(scope="session")
def spark():
    sessao = bronze.criar_sessao("teste-ingestao")
    sessao.conf.set("spark.sql.shuffle.partitions", "4")
    yield sessao
    sessao.stop()


def _rodar(spark, tmp_path, cen, *, id_execucao="e1"):
    return ingestao.executar_ingestao(
        spark,
        diretorio_evidencia=Path(tmp_path) / "evidencia",
        competencia_solicitada=cen.comp,
        caminho_contrato=cen.contrato,
        caminho_csv=cen.csv,
        raiz=str(cen.raiz),
        procedencia=tg._procedencia(cen),
        destino=str(Path(tmp_path) / "dest"),
        preparo_raiz=str(Path(tmp_path) / "prep"),
        id_execucao=id_execucao,
    )


def _destino(tmp_path) -> Path:
    return Path(tmp_path) / "dest"


def _pacote(desfecho):
    return evidencia.ler_pacote(desfecho.caminho_pacote)


# ---------------------------------------------------------------- B-1


def test_julga_na_ingestao_com_segundo_motor(spark, tmp_path, monkeypatch):
    cen = tg._cenario(spark, tmp_path)
    chamadas = {"bronze": [], "leitor": []}
    original_bronze = bronze.executar_leitura
    original_leitor = leitura.ler_competencia

    def espia_bronze(*a, **kw):
        chamadas["bronze"].append(kw.get("gravar"))
        return original_bronze(*a, **kw)

    def espia_leitor(*a, **kw):
        chamadas["leitor"].append(str(a[0]))
        return original_leitor(*a, **kw)

    monkeypatch.setattr(bronze, "executar_leitura", espia_bronze)
    monkeypatch.setattr(leitura, "ler_competencia", espia_leitor)

    desfecho, b = _rodar(spark, tmp_path, cen)

    assert chamadas["bronze"] == [False]  # o Spark mede SEM gravar
    assert chamadas["leitor"] == [str(cen.csv)]  # o segundo motor lê o CSV
    assert desfecho.veredito == evidencia.ACEITO
    pacote = _pacote(desfecho)
    assert pacote["totais_leitura"]["01"]["texto"] == "1621.00"
    assert b.estado == bronze.INTEGRO and b.gravacao is not None


def test_publica_bronze_so_com_aceito(spark, tmp_path):
    cen = tg._cenario(spark, tmp_path)
    desfecho, b = _rodar(spark, tmp_path, cen)
    assert desfecho.autorizado_publicar is True
    linhas, dono, _ = bronze.ler_competencia_publicada(spark, str(_destino(tmp_path)), COMP)
    assert linhas.count() == 7
    assert dono["competencia"] == COMP

    sem = tg._cenario(spark, Path(tmp_path) / "sem", sem_ancora=True)
    desfecho2, b2 = _rodar(spark, Path(tmp_path) / "sem", sem)
    assert desfecho2.veredito == evidencia.ACEITO_SEM_ANCORA
    assert not _destino(Path(tmp_path) / "sem").exists()
    assert b2.gravacao is None


def test_commit_da_bronze_nomeia_o_pacote(spark, tmp_path):
    cen = tg._cenario(spark, tmp_path)
    desfecho, _ = _rodar(spark, tmp_path, cen)
    _, dono, _ = bronze.ler_competencia_publicada(spark, str(_destino(tmp_path)), COMP)
    assert dono["caminho_pacote"] == str(desfecho.caminho_pacote)
    assert dono["sha256_pacote"] == hashlib.sha256(Path(desfecho.caminho_pacote).read_bytes()).hexdigest()


def test_publicado_confere_com_o_julgado(spark, tmp_path, monkeypatch):
    cen = tg._cenario(spark, tmp_path)
    desfecho, _ = _rodar(spark, tmp_path, cen)
    julgado = ingestao._julgado_do_pacote(_pacote(desfecho))
    linhas, _, _ = bronze.ler_competencia_publicada(spark, str(_destino(tmp_path)), COMP)
    observados, por_codigo = bronze.medir_controles(linhas, tg._politica())
    assert observados == julgado["controles"]
    assert por_codigo == julgado["total_por_codigo"]

    # Se o publicado não bate com o que o pacote julgou, reverte a competência e diverge.
    outro = Path(tmp_path) / "outro"
    cen2 = tg._cenario(spark, outro)
    original = ingestao._julgado_do_pacote

    def adulterado(pacote):
        j = original(pacote)
        j["total_por_codigo"] = {**j["total_por_codigo"], "01": Decimal("1.00")}
        return j

    monkeypatch.setattr(ingestao, "_julgado_do_pacote", adulterado)
    _, b = _rodar(spark, outro, cen2)
    assert b.estado == bronze.DIVERGE
    assert not bronze._competencia_existe(spark, str(_destino(outro)), COMP)


# ---------------------------------------------------------------- B-2


def test_recusado_nao_publica(spark, tmp_path):
    cen = tg._cenario(spark, tmp_path, sum_ancora="2012.00")
    desfecho, b = _rodar(spark, tmp_path, cen)
    assert desfecho.veredito == evidencia.RECUSADO
    assert desfecho.autorizado_publicar is False
    assert not _destino(tmp_path).exists()
    assert b.gravacao is None


def test_erro_nao_publica(spark, tmp_path, monkeypatch):
    cen = tg._cenario(spark, tmp_path)

    def quebra(*a, **kw):
        raise RuntimeError("segundo motor caiu")

    monkeypatch.setattr(leitura, "ler_competencia", quebra)
    desfecho, b = _rodar(spark, tmp_path, cen)
    assert desfecho.veredito == evidencia.ERRO
    assert not _destino(tmp_path).exists()
    assert b.gravacao is None
    assert _pacote(desfecho)["evento_falha"]["tipo"] == "RuntimeError"


def test_pacote_fica_como_evidencia(spark, tmp_path):
    cen = tg._cenario(spark, tmp_path, sum_ancora="2012.00")
    desfecho, _ = _rodar(spark, tmp_path, cen)
    assert desfecho.caminho_pacote is not None and Path(desfecho.caminho_pacote).exists()
    pacote = _pacote(desfecho)
    assert pacote["veredito_gravado"] == desfecho.veredito == evidencia.RECUSADO
    assert pacote["causa_gravada"] == desfecho.causa
    assert pacote["ancora_controles"]["sum_vl_liquido"]["texto"] == "2012.00"
    assert pacote["agregado_controles"]["sum_vl_liquido"]["texto"] == "2011.00"


# ---------------------------------------------------------------- reuso


def test_reusa_conduzir_selado(spark, tmp_path, monkeypatch):
    cen = tg._cenario(spark, tmp_path)
    original = orquestracao.conduzir
    vistas = []

    def espia(**kw):
        vistas.append(kw["competencia_solicitada"])
        return original(**kw)

    monkeypatch.setattr(orquestracao, "conduzir", espia)
    desfecho, _ = _rodar(spark, tmp_path, cen)
    assert vistas == [COMP]
    assert isinstance(desfecho, orquestracao.Desfecho)
    fonte = Path(ingestao.__file__).read_text(encoding="utf-8")
    assert "def julgar" not in fonte and "juizo_mod.julgar" not in fonte


def test_reusa_leitor_posicional(spark, tmp_path, monkeypatch):
    cen = tg._cenario(spark, tmp_path)
    original = leitura.ler_competencia
    vistas = []

    def espia(caminho, contrato):
        vistas.append(Path(caminho))
        return original(caminho, contrato)

    monkeypatch.setattr(leitura, "ler_competencia", espia)
    _rodar(spark, tmp_path, cen)
    assert vistas == [cen.csv]
    fonte = Path(ingestao.__file__).read_text(encoding="utf-8")
    assert "spark.read.csv" not in fonte and ".csv(" not in fonte
