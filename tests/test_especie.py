"""Testes da tabela Delta `especie` — o nome oficial ao lado do texto da fonte.

Rodam DENTRO do contêiner pda-spark. Tudo grava só em `tmp_path`, nunca no MinIO; os cenários da
Silver real leem o MinIO UMA vez, numa fixture de escopo de módulo. Nada aqui pula: MinIO ou
Silver indisponível FALHA o teste.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pyspark.sql import functions as F  # noqa: E402

from medalhao import bronze, especie  # noqa: E402
from medalhao.ontologia import Ontologia, carregar_ontologia  # noqa: E402

COMP = "2026-01"
OUTRA = "2026-02"
NOME_A = "APOSENTADORIA POR IDADE DO TRABALHADOR RURAL"
NOME_B = "PENSAO POR MORTE PREVIDENCIARIA"
NOME_C = "AUXILIO DOENCA"
SILVER_REAL = "s3a://silver/pda/beneficios-emitidos"


# ---------------------------------------------------------------- apoio


@pytest.fixture(scope="module")
def spark():
    sessao = bronze.criar_sessao("teste-especie")
    sessao.conf.set("spark.sql.shuffle.partitions", "4")
    yield sessao
    sessao.stop()


def _ontologia(*, extra=()):
    especies = [
        {"codigo": "01", "nome": NOME_A, "grupo": "Aposentadoria"},
        {"codigo": "02", "nome": NOME_B, "grupo": "Pensao"},
        {"codigo": "03", "nome": NOME_C, "grupo": "Auxilio"},
        *extra,
    ]
    return Ontologia(fontes={}, colunas=(), termos=(), especies=tuple(especies), sha256="ab" * 32)


def _silver(spark, base, linhas, nome="silver"):
    """Silver Delta mínima, com as colunas que a tarefa lê. `linhas`: (codigo, descricao, competencia)."""
    caminho = str(Path(base) / nome)
    df = spark.createDataFrame(linhas, "especie_codigo string, especie_descricao string, competencia string")
    df.write.format("delta").partitionBy("competencia").save(caminho)
    return caminho


def _linhas_ok(comp=COMP):
    # o texto da fonte: 01 é o prefixo de 20 caracteres; 02 tem espaços à direita; 03 é outro texto
    return [
        ("01", NOME_A[:20], comp), ("01", NOME_A[:20], comp), ("02", NOME_B[:20] + "   ", comp),
        ("03", "TEXTO QUE NAO BATE", comp),
    ]


def _lido(spark, destino, comp=COMP):
    return spark.read.format("delta").load(destino).where(F.col("competencia") == comp)


def _versao(spark, caminho):
    return bronze._versao_atual(spark, caminho)


def _publicar(spark, base, linhas=None, **kw):
    silver = _silver(spark, base, linhas if linhas is not None else _linhas_ok())
    destino = str(Path(base) / "especie")
    r = especie.publicar_especie(spark, _ontologia(), silver, destino, COMP, **kw)
    return r, silver, destino


# ---------------------------------------------------------------- eval_1


def test_grava_nome_oficial_e_texto_da_fonte(spark, tmp_path):
    r, _, destino = _publicar(spark, tmp_path, id_execucao="e1")
    assert r.estado == especie.INTEGRO, (r.estado, r.motivo, r.diferencas)
    lido = _lido(spark, destino)
    assert tuple(lido.columns) == especie.COLUNAS
    linhas = {x["especie_codigo"]: x for x in lido.collect()}
    assert set(linhas) == {"01", "02", "03"}  # uma linha por código, mesmo com 01 repetido na Silver
    assert lido.count() == 3
    assert linhas["01"]["nome_oficial"] == NOME_A and linhas["01"]["grupo"] == "Aposentadoria"
    assert linhas["01"]["descricao_fonte"] == NOME_A[:20]
    assert linhas["03"]["nome_oficial"] == NOME_C and linhas["03"]["descricao_fonte"] == "TEXTO QUE NAO BATE"
    assert {c: x["texto_fonte_confere_prefixo"] for c, x in linhas.items()} == {"01": True, "02": True, "03": False}
    assert all(x["competencia"] == COMP for x in linhas.values())
    assert lido.schema["texto_fonte_confere_prefixo"].dataType.simpleString() == "boolean"


def test_descricao_fonte_como_veio_com_espacos_a_direita(spark, tmp_path):
    r, _, destino = _publicar(spark, tmp_path)
    assert r.estado == especie.INTEGRO
    dois = _lido(spark, destino).where(F.col("especie_codigo") == "02").first()
    assert dois["descricao_fonte"] == NOME_B[:20] + "   "  # o defeito da fonte preservado, Regra 4
    assert dois["descricao_fonte"] != dois["descricao_fonte"].rstrip()
    assert dois["nome_oficial"] == NOME_B  # nada do nome oficial vazou para o texto da fonte


def test_reconferencia_acusa_linha_alterada(spark, tmp_path):
    r, _, destino = _publicar(spark, tmp_path, id_execucao="e2")
    assert r.estado == especie.INTEGRO
    esperado = _lido(spark, destino).select(*especie.COLUNAS)
    ok, detalhe = especie.reconferir_especie(spark, destino, "e2", esperado, COMP)
    assert ok and detalhe["so_no_esperado"] == 0 and detalhe["so_no_lido"] == 0
    alterado = esperado.withColumn(
        "descricao_fonte",
        F.when(F.col("especie_codigo") == "03", F.lit("OUTRO TEXTO")).otherwise(F.col("descricao_fonte")),
    )
    ok, detalhe = especie.reconferir_especie(spark, destino, "e2", alterado, COMP)
    assert not ok and detalhe["so_no_esperado"] == 1 and detalhe["so_no_lido"] == 1
    ok, detalhe = especie.reconferir_especie(spark, destino, "nao-existe", esperado, COMP)
    assert not ok and detalhe["motivo"] == "COMMIT_NAO_ACHADO"


def test_reconferencia_le_a_versao_do_proprio_commit_e_nao_a_atual(spark, tmp_path):
    r, _, destino = _publicar(spark, tmp_path, id_execucao="e3")
    esperado = spark.createDataFrame(_lido(spark, destino).select(*especie.COLUNAS).collect(), especie.SCHEMA)
    from delta.tables import DeltaTable

    DeltaTable.forPath(spark, destino).update(F.col("especie_codigo") == "03", {"grupo": F.lit("Adulterado")})
    assert _versao(spark, destino) > r.gravacao["versao"]
    ok, detalhe = especie.reconferir_especie(spark, destino, "e3", esperado, COMP)
    assert ok and detalhe["versao"] == r.gravacao["versao"]


def test_outra_competencia_intacta(spark, tmp_path):
    silver = _silver(spark, tmp_path, _linhas_ok(COMP) + _linhas_ok(OUTRA))
    destino = str(Path(tmp_path) / "especie")
    o = _ontologia()
    assert especie.publicar_especie(spark, o, silver, destino, OUTRA, id_execucao="o1").estado == especie.INTEGRO
    antes = _lido(spark, destino, OUTRA).select(*especie.COLUNAS).collect()
    assert especie.publicar_especie(spark, o, silver, destino, COMP, id_execucao="o2").estado == especie.INTEGRO
    assert especie.publicar_especie(spark, o, silver, destino, COMP, id_execucao="o3").estado == especie.INTEGRO
    depois = _lido(spark, destino, OUTRA).select(*especie.COLUNAS).collect()
    assert sorted(map(tuple, antes)) == sorted(map(tuple, depois))
    assert _lido(spark, destino, COMP).count() == 3  # a regravação é idempotente: não duplica


def test_linhagem_no_commit(spark, tmp_path):
    r, silver, destino = _publicar(spark, tmp_path, id_execucao="l1")
    assert r.estado == especie.INTEGRO and r.gravacao["id_execucao"] == "l1"
    meta = {v: json.loads(m) for v, m in bronze._historico(spark, destino) if m}
    commit = meta[r.gravacao["versao"]]
    assert commit["versao_silver"] == bronze._versao_atual(spark, silver) == r.versao_silver
    assert commit["ontologia_sha256"] == _ontologia().sha256
    assert commit["id_execucao"] == "l1" and commit["competencia"] == COMP


def test_le_a_silver_na_versao_fixada_no_inicio(spark, tmp_path):
    r, silver, _ = _publicar(spark, tmp_path)
    assert r.versao_silver == 0
    from delta.tables import DeltaTable

    DeltaTable.forPath(spark, silver).delete(F.col("especie_codigo") == "03")
    nova = especie.publicar_especie(spark, _ontologia(), silver, str(Path(tmp_path) / "outro"), COMP)
    assert nova.estado == especie.DIVERGE and nova.versao_silver == 1  # a versão fixada é a atual, e não confere


# ---------------------------------------------------------------- eval_2


def _recusou_sem_gravar(spark, tmp_path, linhas, ontologia=None):
    silver = _silver(spark, tmp_path, linhas)
    destino = str(Path(tmp_path) / "especie")
    r = especie.publicar_especie(spark, ontologia or _ontologia(), silver, destino, COMP)
    assert not especie._e_delta(spark, destino), "a recusa criou o destino"
    assert "destino sem versão nova" in r.motivo
    assert r.linhas is None
    return r


def test_codigo_fora_da_ontologia_recusa(spark, tmp_path):
    r = _recusou_sem_gravar(spark, tmp_path, _linhas_ok() + [("99", "DESCONHECIDA", COMP)])
    assert r.estado == especie.DIVERGE and r.motivo.startswith("CODIGO_FORA_DA_ONTOLOGIA")
    dif = {d["identidade"]: d for d in r.diferencas}
    assert "99" in dif["CODIGO_FORA_DA_ONTOLOGIA"]["observado"]


def test_codigo_ausente_recusa(spark, tmp_path):
    r = _recusou_sem_gravar(spark, tmp_path, [x for x in _linhas_ok() if x[0] != "03"])
    assert r.estado == especie.DIVERGE and r.motivo.startswith("CODIGO_AUSENTE_DA_COMPETENCIA")
    dif = {d["identidade"]: d for d in r.diferencas}
    assert "03" in dif["CODIGO_AUSENTE_DA_COMPETENCIA"]["observado"]


def test_duas_descricoes_recusa(spark, tmp_path):
    r = _recusou_sem_gravar(spark, tmp_path, _linhas_ok() + [("03", "OUTRA DESCRICAO", COMP)])
    assert r.estado == especie.DIVERGE and r.motivo.startswith("CODIGO_COM_MAIS_DE_UMA_DESCRICAO")
    dif = {d["identidade"]: d for d in r.diferencas}
    observado = dif["CODIGO_COM_MAIS_DE_UMA_DESCRICAO"]["observado"]
    assert "03" in observado and "OUTRA DESCRICAO" in observado and "TEXTO QUE NAO BATE" in observado


def test_recusa_nao_da_versao_nova_a_um_destino_que_ja_existe(spark, tmp_path):
    r, silver, destino = _publicar(spark, tmp_path)
    assert r.estado == especie.INTEGRO
    antes = _versao(spark, destino)
    from delta.tables import DeltaTable

    DeltaTable.forPath(spark, silver).delete(F.col("especie_codigo") == "03")
    recusa = especie.publicar_especie(spark, _ontologia(), silver, destino, COMP)
    assert recusa.estado == especie.DIVERGE
    assert _versao(spark, destino) == antes
    assert f"versão {antes}" in recusa.motivo


def test_competencia_vazia_nao_medido(spark, tmp_path):
    r = _recusou_sem_gravar(spark, tmp_path, _linhas_ok(OUTRA))  # a Silver só tem outra competência
    assert r.estado == especie.NAO_MEDIDO and r.estado != especie.INTEGRO
    assert r.motivo.startswith("SILVER_SEM_LINHAS_NA_COMPETENCIA")
    assert r.diferencas == ()


def test_ontologia_nao_medida_nao_publica(spark, tmp_path):
    from medalhao.ontologia import NaoMedido

    silver = _silver(spark, tmp_path, _linhas_ok())
    destino = str(Path(tmp_path) / "especie")
    r = especie.publicar_especie(spark, NaoMedido("FONTE_AUSENTE:x"), silver, destino, COMP)
    assert r.estado == especie.NAO_MEDIDO and not especie._e_delta(spark, destino)


# ---------------------------------------------------------------- eval_3: a Silver real


@pytest.fixture(scope="module")
def real(spark, tmp_path_factory):
    """A Silver real de 2026-01, lida do MinIO UMA vez; o resultado grava em tmp."""
    ontologia = carregar_ontologia()
    assert not isinstance(ontologia, str), f"ontologia: {getattr(ontologia, 'motivo', ontologia)}"
    destino = str(tmp_path_factory.mktemp("especie-real") / "especie")
    r = especie.publicar_especie(spark, ontologia, SILVER_REAL, destino, COMP, id_execucao="real")
    return r, destino, ontologia


def test_especie_real_2026_01(spark, real):
    r, destino, ontologia = real
    assert r.estado == especie.INTEGRO, (r.estado, r.motivo, r.diferencas)
    lido = _lido(spark, destino)
    assert lido.count() == 65
    assert lido.select("nome_oficial").distinct().count() == 65
    assert lido.select("especie_codigo").distinct().count() == 65
    assert lido.where(F.col("texto_fonte_confere_prefixo")).count() == 43
    oficial = {e["codigo"]: e["nome"] for e in ontologia.especies}
    assert {x["especie_codigo"]: x["nome_oficial"] for x in lido.collect()} == oficial
    ok, detalhe = especie.reconferir_especie(spark, destino, "real", r.linhas, COMP)
    assert ok and detalhe["so_no_esperado"] == 0 and detalhe["so_no_lido"] == 0


def test_colapsos_desfeitos_pelo_nome(spark, real):
    """O contrato mede 52 descrições para 65 códigos: o nome oficial desfaz o colapso, o texto da fonte não."""
    r, destino, _ = real
    assert r.estado == especie.INTEGRO
    lido = _lido(spark, destino)
    assert lido.select("descricao_fonte").distinct().count() == 52
    assert lido.select("nome_oficial").distinct().count() == 65
    por_texto = lido.groupBy("descricao_fonte").agg(F.count(F.lit(1)).alias("n"))
    colapsados = por_texto.where(F.col("n") > 1)
    assert colapsados.count() == 11
    assert colapsados.agg(F.sum("n")).first()[0] == 24
    for x in lido.collect():
        assert x["descricao_fonte"] is not None and x["nome_oficial"]  # nada corrigido em silêncio nem perdido
