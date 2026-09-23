"""Testes do vinculador de procedência — a partição só ganha _PROCEDENCIA.json
se for a transformação do CSV declarado no contrato.

Rodam DENTRO do contêiner pda-spark. Cada teste monta o seu próprio CSV e a
sua própria partição em `tmp_path`; nada toca o lago real.
"""

from __future__ import annotations

import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import DecimalType, StringType, StructField, StructType

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pda.contrato import (  # noqa: E402
    Ancora,
    Cardinalidade,
    Contrato,
    Layout,
    Particionamento,
    PoliticaDecimal,
    Procedencia,
)
from produtor import vincular_procedencia as vp  # noqa: E402

COMP = "2026-01"

# (especie, descricao, valor como no CSV brasileiro) — o esperado na partição é a
# transformação destas linhas.
LINHAS_CSV = [
    ("01", "Aposentadoria", "1.234,56"),
    ("02", "Pensao", "0,10"),
    ("01", "Aposentadoria", "0,20"),
]
LINHAS_PARTICAO = [
    ("01", "Aposentadoria", Decimal("1234.56")),
    ("02", "Pensao", Decimal("0.10")),
    ("01", "Aposentadoria", Decimal("0.20")),
]
ESQUEMA = StructType([
    StructField("especie_codigo", StringType()),
    StructField("especie_descricao", StringType()),
    StructField("vl_liquido", DecimalType(14, 2)),
])


@pytest.fixture(scope="session")
def spark():
    sessao = (
        SparkSession.builder.master("local[2]").appName("teste-vincula")
        .config("spark.sql.shuffle.partitions", "2").getOrCreate()
    )
    yield sessao
    sessao.stop()


def _csv(tmp_path: Path, linhas=LINHAS_CSV, nome="fonte.csv") -> Path:
    caminho = tmp_path / nome
    cab = ";".join(f"h{i}" for i in range(14))
    corpo = []
    for esp, desc, val in linhas:
        c = ["x"] * 14
        c[9], c[12], c[13] = val, esp, desc
        corpo.append(";".join(c))
    caminho.write_text("\n".join([cab, *corpo]) + "\n", encoding="utf-8")
    return caminho


def _contrato(csv: Path, hash_csv: str = None) -> Contrato:
    return Contrato(
        competencia=COMP,
        procedencia=Procedencia(
            fonte=csv.name, hash_zip_sha256="b" * 64,
            hash_csv_sha256=hash_csv or hashlib.sha256(csv.read_bytes()).hexdigest(),
            publicado_em=COMP),
        layout=Layout(total_colunas=14, separador=";", encoding="utf-8",
                      posicoes={"especie": 12, "descricao_especie": 13, "vl_liquido": 9}),
        ancora=Ancora(count_linhas=3, sum_vl_liquido=Decimal("1234.86"),
                      min_vl_liquido=Decimal("0.10"), max_vl_liquido=Decimal("1234.56"),
                      linhas_invalidas=0, aprovado_por="teste", aprovado_em="2026-09-23"),
        cardinalidade=Cardinalidade(codigos_distintos=2, descricoes_distintas=2,
                                    colapsos=0, codigos_colapsados=0),
        defeitos_conhecidos=(),
        politica_decimal=PoliticaDecimal(modo="HALF_EVEN", escala=2, escala_maxima_intermediarios=3,
                                         precisao=14, nao_negativo=True, emax=999999, emin=-999999),
        particionamento=Particionamento(
            chave="competencia", caminho="s3a://landing/pda/beneficios-emitidos",
            formato="parquet", valores_medidos=(COMP,),
            objetos_auxiliares_ignorados=("_SUCCESS",)),
    )


def _lago(spark, tmp_path: Path, linhas=LINHAS_PARTICAO, esquema=ESQUEMA) -> Path:
    raiz = tmp_path / "lago"
    spark.createDataFrame(linhas, esquema).coalesce(1).write.mode("overwrite").parquet(
        str(raiz / f"competencia={COMP}"))
    return raiz


def _particao(raiz: Path) -> Path:
    return raiz / f"competencia={COMP}"


def _prova(raiz: Path) -> Path:
    return _particao(raiz) / "_PROCEDENCIA.json"


def _cenario(spark, tmp_path, **kw):
    csv = _csv(tmp_path)
    return csv, _contrato(csv), _lago(spark, tmp_path, **kw)


def _vincular(spark, contrato, csv, raiz, **kw):
    return vp.vincular(spark, contrato, csv, raiz=str(raiz), **kw)


# ---------------------------------------------------------------- eval_1


def test_hash_divergente_nao_grava(spark, tmp_path):
    csv, _, raiz = _cenario(spark, tmp_path)
    r = _vincular(spark, _contrato(csv, hash_csv="0" * 64), csv, raiz)
    assert r.veredito == vp.DIVERGE and r.motivo == "HASH_DO_CSV_DIVERGE"
    assert not _prova(raiz).exists()


def test_conteudo_divergente_nao_grava(spark, tmp_path):
    outras = [("01", "Aposentadoria", Decimal("1234.56")),
              ("02", "Pensao", Decimal("0.10")),
              ("01", "Aposentadoria", Decimal("0.21"))]
    csv, contrato, raiz = _cenario(spark, tmp_path, linhas=outras)
    r = _vincular(spark, contrato, csv, raiz)
    assert r.veredito == vp.DIVERGE and r.motivo == "CONTEUDO_DIFERE"
    assert not _prova(raiz).exists()


def test_conteudo_divergente_multiconjunto_com_mesma_soma_nao_grava(spark, tmp_path):
    # mesma contagem e mesma soma, valores trocados: só o multiconjunto acusa
    outras = [("01", "Aposentadoria", Decimal("1234.46")),
              ("02", "Pensao", Decimal("0.20")),
              ("01", "Aposentadoria", Decimal("0.20"))]
    csv, contrato, raiz = _cenario(spark, tmp_path, linhas=outras)
    r = _vincular(spark, contrato, csv, raiz)
    assert r.veredito == vp.DIVERGE
    assert not _prova(raiz).exists()


def test_grava_manifesto_hash_e_controles(spark, tmp_path):
    csv, contrato, raiz = _cenario(spark, tmp_path)
    antes = {p.name: p.read_bytes() for p in _particao(raiz).iterdir() if not p.name.startswith(".")}
    r = _vincular(spark, contrato, csv, raiz, id_execucao="exec-1")
    assert r.veredito == vp.GRAVADO
    prova = json.loads(_prova(raiz).read_text(encoding="utf-8"))
    assert prova["competencia"] == COMP
    assert prova["csv_sha256"] == hashlib.sha256(csv.read_bytes()).hexdigest()
    assert prova["id_execucao"] == "exec-1"
    assert prova["controles"] == {
        "count_linhas": "3", "linhas_invalidas": "0", "sum_vl_liquido": "1234.86",
        "min_vl_liquido": "0.10", "max_vl_liquido": "1234.56",
    }
    nomes = {o["nome"] for o in prova["manifesto"]}
    assert nomes == {n for n in antes if n not in ("_SUCCESS",)}
    for o in prova["manifesto"]:
        conteudo = antes[o["nome"]]
        assert o["tamanho"] == len(conteudo)
        assert o["sha256"] == hashlib.sha256(conteudo).hexdigest()
    # nunca toca nos objetos de dado
    depois = {p.name: p.read_bytes() for p in _particao(raiz).iterdir()
              if not p.name.startswith(".") and p.name != "_PROCEDENCIA.json"}
    assert depois == antes


def test_rele_o_que_gravou(spark, tmp_path, monkeypatch):
    csv, contrato, raiz = _cenario(spark, tmp_path)
    r = _vincular(spark, contrato, csv, raiz)
    assert r.veredito == vp.GRAVADO
    assert r.prova == json.loads(_prova(raiz).read_text(encoding="utf-8"))

    # gravação que sai diferente do que se quis gravar não passa por GRAVADO
    _prova(raiz).unlink()
    original = vp._gravar_prova

    def torta(armazem, uri, prova):
        original(armazem, uri, {**prova, "competencia": "1999-01"})

    monkeypatch.setattr(vp, "_gravar_prova", torta)
    r = _vincular(spark, contrato, csv, raiz)
    assert r.veredito == vp.DIVERGE and r.motivo == "RELEITURA_DIVERGE"


def test_manifesto_mudou_antes_de_gravar_diverge(spark, tmp_path, monkeypatch):
    csv, contrato, raiz = _cenario(spark, tmp_path)
    original = vp._comparar

    def comparar_e_mexer(fonte, particao):
        resultado = original(fonte, particao)
        (_particao(raiz) / "_extra.parquet").write_bytes(b"chegou depois da comparacao")
        return resultado

    monkeypatch.setattr(vp, "_comparar", comparar_e_mexer)
    r = _vincular(spark, contrato, csv, raiz)
    assert r.veredito == vp.DIVERGE and r.motivo == "MANIFESTO_MUDOU_ANTES_DE_GRAVAR"
    assert not _prova(raiz).exists()


# ---------------------------------------------------------------- eval_2


def test_valor_em_decimal_nunca_float(spark, tmp_path):
    csv, contrato, raiz = _cenario(spark, tmp_path)
    fonte = vp.ler_fonte(spark, csv, contrato)
    assert fonte.schema["vl_liquido"].dataType == DecimalType(14, 2)
    # 0,10 + 0,20 é exatamente 0,30 — em float seria 0.30000000000000004
    assert fonte.filter("vl_liquido < 1").agg({"vl_liquido": "sum"}).collect()[0][0] == Decimal("0.30")

    # partição com valor em double: recusada, nada gravado
    from pyspark.sql.types import DoubleType
    esquema = StructType([ESQUEMA[0], ESQUEMA[1], StructField("vl_liquido", DoubleType())])
    lago = tmp_path / "lago_float"
    spark.createDataFrame(
        [(e, d, float(v)) for e, d, v in LINHAS_PARTICAO], esquema
    ).coalesce(1).write.parquet(str(lago / f"competencia={COMP}"))
    r = _vincular(spark, contrato, csv, lago)
    assert r.veredito == vp.DIVERGE and r.motivo == "VALOR_DA_PARTICAO_NAO_E_DECIMAL"
    assert not _prova(lago).exists()


def test_zero_linhas_e_nao_medido(spark, tmp_path):
    # CSV só com cabeçalho e partição vazia: nada a provar
    csv = _csv(tmp_path, linhas=[], nome="vazio.csv")
    contrato = _contrato(csv)
    raiz = _lago(spark, tmp_path, linhas=[])
    r = _vincular(spark, contrato, csv, raiz)
    assert r.veredito == vp.NAO_MEDIDO
    assert not _prova(raiz).exists()

    # zero linhas só na partição, CSV com dados: também não é medido
    outro = tmp_path / "b"
    outro.mkdir()
    csv2, contrato2, raiz2 = _cenario(spark, outro, linhas=[])
    r2 = _vincular(spark, contrato2, csv2, raiz2)
    assert r2.veredito == vp.NAO_MEDIDO
    assert not _prova(raiz2).exists()


# ---------------------------------------------------------------- eval_3


def test_prova_identica_nao_regrava(spark, tmp_path):
    csv, contrato, raiz = _cenario(spark, tmp_path)
    assert _vincular(spark, contrato, csv, raiz).veredito == vp.GRAVADO
    bytes_antes = _prova(raiz).read_bytes()
    mtime_antes = _prova(raiz).stat().st_mtime_ns
    r = _vincular(spark, contrato, csv, raiz)
    assert r.veredito == vp.INTEGRO
    assert _prova(raiz).read_bytes() == bytes_antes
    assert _prova(raiz).stat().st_mtime_ns == mtime_antes


def test_prova_divergente_nao_sobrescreve(spark, tmp_path):
    csv, contrato, raiz = _cenario(spark, tmp_path)
    assert _vincular(spark, contrato, csv, raiz).veredito == vp.GRAVADO
    bytes_antes = _prova(raiz).read_bytes()

    (_particao(raiz) / "_extra.parquet").write_bytes(b"objeto a mais")
    r = _vincular(spark, contrato, csv, raiz)
    assert r.veredito == vp.DIVERGE
    assert any("acrescentado" in d and "_extra.parquet" in d for d in r.diferencas)
    assert _prova(raiz).read_bytes() == bytes_antes

    (_particao(raiz) / "_extra.parquet").unlink()
    parte = next(p for p in _particao(raiz).iterdir() if p.suffix == ".parquet")
    parte.write_bytes(parte.read_bytes() + b"\0")
    r = _vincular(spark, contrato, csv, raiz)
    assert r.veredito == vp.DIVERGE
    assert any("alterado" in d for d in r.diferencas)
    assert _prova(raiz).read_bytes() == bytes_antes


def test_reexecucao_com_outro_id_e_identica(spark, tmp_path):
    csv, contrato, raiz = _cenario(spark, tmp_path)
    assert _vincular(spark, contrato, csv, raiz, id_execucao="exec-1").veredito == vp.GRAVADO
    bytes_antes = _prova(raiz).read_bytes()
    r = _vincular(spark, contrato, csv, raiz, id_execucao="exec-2")
    assert r.veredito == vp.INTEGRO
    assert _prova(raiz).read_bytes() == bytes_antes
    assert json.loads(bytes_antes)["id_execucao"] == "exec-1"
