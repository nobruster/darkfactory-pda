"""Testes da limpeza do preparo — apaga só o prefixo da execução publicada e conferida.

Rodam DENTRO do contêiner pda-spark, sobre tabelas Delta sob `tmp_path`.
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pyspark.sql.types import DecimalType, StringType, StructField, StructType  # noqa: E402

from test_gold import spark  # noqa: E402,F401  (a mesma sessão de teste)
from medalhao import limpeza  # noqa: E402

COMP = "2026-03"
ESQUEMA = StructType([StructField("competencia", StringType()), StructField("vl_liquido", DecimalType(14, 2))])


def _commit(spark, destino, valor, meta, primeiro=False):
    df = spark.createDataFrame([(COMP, Decimal(valor))], ESQUEMA)
    escritor = df.write.format("delta").mode("overwrite").option("userMetadata", json.dumps(meta))
    if not primeiro:
        escritor = escritor.option("replaceWhere", f"competencia = '{COMP}'")
    escritor.save(str(destino))


def _preparo(tmp_path, camada, id_execucao):
    raiz = Path(tmp_path) / camada / "_preparo" / "pda" / "t"
    execucao = raiz / f"execucao={id_execucao}"
    execucao.mkdir(parents=True)
    (execucao / "parte.parquet").write_text("x")
    return raiz, execucao


def _publicar(spark, tmp_path, id_execucao="e1", estado="INTEGRO"):
    destino = Path(tmp_path) / "gold" / "pda" / "t"
    _commit(spark, destino, "10.00", {"competencia": COMP, "estado": estado, "id_execucao": id_execucao}, primeiro=True)
    return destino


def _limpar(spark, destino, raiz, id_execucao="e1"):
    return limpeza.limpar_preparo(spark, "gold", str(destino), str(raiz), COMP, id_execucao)


def test_apaga_preparo_de_execucao_publicada(spark, tmp_path):
    destino = _publicar(spark, tmp_path)
    raiz, execucao = _preparo(tmp_path, "gold", "e1")
    r = _limpar(spark, destino, raiz)
    assert r.apagou and r.conferido, r
    assert not execucao.exists()


def test_publicada_intacta_depois(spark, tmp_path):
    destino = _publicar(spark, tmp_path)
    raiz, _ = _preparo(tmp_path, "gold", "e1")
    antes = limpeza._medir(spark, str(destino), "vl_liquido")
    r = _limpar(spark, destino, raiz)
    assert r.conferido
    assert limpeza._medir(spark, str(destino), "vl_liquido") == antes


def test_id_vazio_recusado(spark, tmp_path):
    destino = _publicar(spark, tmp_path)
    raiz, execucao = _preparo(tmp_path, "gold", "e1")
    for vazio in ("", "  ", None):
        r = _limpar(spark, destino, raiz, vazio)
        assert r.resultado == limpeza.RECUSADO and not r.apagou
    assert execucao.exists() and raiz.exists()


def test_caminho_fora_do_preparo_recusado(spark, tmp_path):
    destino = _publicar(spark, tmp_path)
    _, execucao = _preparo(tmp_path, "gold", "e1")
    for fora in (str(Path(tmp_path) / "gold" / "pda"), "", "s3a://gold", str(Path(tmp_path) / "gold" / "_preparo"),
                 str(Path(tmp_path) / "gold" / "_preparo" / ".." / "pda")):
        r = _limpar(spark, destino, fora)
        assert r.resultado == limpeza.RECUSADO and not r.apagou, fora
    assert execucao.exists()


def test_execucao_nao_publicada_preserva(spark, tmp_path):
    destino = _publicar(spark, tmp_path, id_execucao="outra")
    raiz, execucao = _preparo(tmp_path, "gold", "e1")
    r = _limpar(spark, destino, raiz)
    assert r.resultado == limpeza.PRESERVADO and r.motivo
    assert execucao.exists()


def test_commit_revertido_preserva(spark, tmp_path):
    destino = _publicar(spark, tmp_path)
    _commit(spark, destino, "10.00", {"competencia": COMP, "estado": "REVERTIDO", "id_execucao": "e1"})
    raiz, execucao = _preparo(tmp_path, "gold", "e1")
    r = _limpar(spark, destino, raiz)
    assert r.resultado == limpeza.PRESERVADO and "REVERTIDO" in r.motivo
    assert execucao.exists()


def test_commit_seguido_de_outro_preserva(spark, tmp_path):
    destino = _publicar(spark, tmp_path)
    _commit(spark, destino, "11.00", {"competencia": COMP, "estado": "INTEGRO", "id_execucao": "e2"})
    raiz, execucao = _preparo(tmp_path, "gold", "e1")
    assert _limpar(spark, destino, raiz).resultado == limpeza.PRESERVADO
    assert execucao.exists()


def test_outra_execucao_intacta(spark, tmp_path):
    destino = _publicar(spark, tmp_path)
    raiz, execucao = _preparo(tmp_path, "gold", "e1")
    outra = raiz / "execucao=e10"
    outra.mkdir()
    (outra / "parte.parquet").write_text("y")
    r = _limpar(spark, destino, raiz)
    assert r.apagou
    assert not execucao.exists()
    assert (outra / "parte.parquet").exists()


def test_substituida_conferida_apaga(spark, tmp_path):
    destino = _publicar(spark, tmp_path)
    _commit(spark, destino, "11.00", {"competencia": COMP, "estado": "INTEGRO", "id_execucao": "e2"})
    raiz, execucao = _preparo(tmp_path, "gold", "e1")
    r = _limpar(spark, destino, raiz)
    assert r.apagou and r.conferido, r
    assert not execucao.exists()


def test_publicada_intacta_apos_limpar_substituida(spark, tmp_path):
    destino = _publicar(spark, tmp_path)
    _commit(spark, destino, "11.00", {"competencia": COMP, "estado": "INTEGRO", "id_execucao": "e2"})
    raiz, _ = _preparo(tmp_path, "gold", "e1")
    antes = limpeza._medir(spark, str(destino), "vl_liquido")
    assert _limpar(spark, destino, raiz).conferido
    assert limpeza._medir(spark, str(destino), "vl_liquido") == antes


def test_revertida_preserva(spark, tmp_path):
    destino = _publicar(spark, tmp_path)
    _commit(spark, destino, "10.00", {"competencia": COMP, "estado": "REVERTIDO", "id_execucao": "e1"})
    _commit(spark, destino, "12.00", {"competencia": COMP, "estado": "INTEGRO", "id_execucao": "e3"})
    raiz, execucao = _preparo(tmp_path, "gold", "e1")
    r = _limpar(spark, destino, raiz)
    assert r.resultado == limpeza.PRESERVADO and r.motivo
    assert execucao.exists()


def test_sem_commit_preserva(spark, tmp_path):
    destino = _publicar(spark, tmp_path, id_execucao="e0")
    raiz, execucao = _preparo(tmp_path, "gold", "e1")
    r = _limpar(spark, destino, raiz)
    assert r.resultado == limpeza.PRESERVADO and r.motivo
    assert execucao.exists()


def test_execucao_ativa_preserva(spark, tmp_path):
    destino = _publicar(spark, tmp_path, id_execucao="e0")
    _commit(spark, destino, "11.00", {"competencia": COMP, "estado": "INTEGRO", "id_execucao": "e2"})
    raiz, ativa = _preparo(tmp_path, "gold", "e9")
    r = _limpar(spark, destino, raiz, "e9")
    assert r.resultado == limpeza.PRESERVADO and r.motivo == "EXECUCAO_NAO_PUBLICADA"
    assert ativa.exists()


def test_prefixo_montado_de_partes_validadas(tmp_path):
    raiz = str(Path(tmp_path) / "gold" / "_preparo" / "pda" / "t")
    assert limpeza.montar_prefixo("gold", raiz, "e1") == f"{raiz}/execucao=e1"
    assert limpeza.montar_prefixo("gold", "s3a://gold/_preparo/pda/t/", "e1") == "s3a://gold/_preparo/pda/t/execucao=e1"
    for camada, r, i in (("gold", raiz, ""), ("gold", raiz, "../x"), ("gold", raiz, "a/b"), ("prata", raiz, "e1"),
                         ("silver", raiz, "e1"), ("gold", "", "e1"), ("gold", "s3a://gold", "e1")):
        with pytest.raises(limpeza.CaminhoRecusado):
            limpeza.montar_prefixo(camada, r, i)
