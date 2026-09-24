"""Testes da Gold por assuntos — fat_especie e kpis_nacionais, lidas da Silver nomeada pela Gold principal.

Rodam DENTRO do contêiner pda-spark. A cadeia é a REAL (ingestão julgada → Silver → Gold principal)
sobre um lago de teste; nada grava no destino real: os destinos Delta vivem sob `tmp_path`.
"""

from __future__ import annotations

import inspect
import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pyspark.sql import functions as F  # noqa: E402
from pyspark.sql.types import DecimalType  # noqa: E402

import test_gold as tg  # noqa: E402
from test_gold import cadeias_por_modulo, spark  # noqa: E402,F401  (a mesma sessão de teste)
from medalhao import bronze, gold_assuntos as ga, silver  # noqa: E402
from pda.contrato import carregar_contrato  # noqa: E402

COMP = tg.COMP
PENSAO = ["01", "02", "03", "23", "59"]
APOSENTADORIA = ["04", "83"]


# ---------------------------------------------------------------- apoio


def _contrato_com(cen, tmp_path, nome, *, grupos=True, mexer=None):
    """Copia do contrato do cenário, com grupos_especie (7 códigos) e um ajuste opcional."""
    dados = yaml.safe_load(Path(cen.contrato).read_text(encoding="utf-8"))
    if grupos:
        dados["grupos_especie"] = {
            "aprovado_por": "teste", "aprovado_em": "2026-09-23", "regra": "teste",
            "grupos": [
                {"grupo": "Pensao", "codigos": (grupos if isinstance(grupos, list) else PENSAO)},
                {"grupo": "Aposentadoria", "codigos": APOSENTADORIA},
            ],
        }
    if mexer:
        mexer(dados)
    caminho = Path(tmp_path) / f"{nome}.yaml"
    caminho.write_text(yaml.safe_dump(dados, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return caminho


def _preparar(spark, tmp_path, *, gold_principal=True):
    """Cadeia real até a Gold principal publicada. Devolve (cen, d, contrato_com_grupos)."""
    cen = tg._cenario(spark, tmp_path)
    d, s, _ = tg._cadeia_publicada(spark, tmp_path, cen)
    assert s.estado == silver.INTEGRO
    if gold_principal:
        _gold_principal_publicada(spark, tmp_path, cen, d)
    return cen, d, _contrato_com(cen, tmp_path, "com-grupos")


def _gold_principal_publicada(spark, tmp_path, cen, d):
    """Gold principal publicada sobre a cadeia — montada uma vez por módulo, copiada por teste."""
    def montar():
        g = tg._gold_da_silver(spark, cen, d)
        assert g.estado == ga.INTEGRO, (g.estado, g.motivo)

    texto_contrato = Path(cen.contrato).read_text(encoding="utf-8").replace(str(Path(tmp_path)), "<BASE>")
    tg._copiar_cenario_montado(("gold-principal", cen.comp, cen.hash, texto_contrato), tmp_path, montar)


def _rodar(spark, tmp_path, d, contrato, **kw):
    return ga.executar_gold_assuntos(
        spark, caminho_contrato=contrato, silver_destino=d["silver"], gold_principal_destino=d["gold"],
        fat_destino=str(Path(tmp_path) / "fat"), kpis_destino=str(Path(tmp_path) / "kpis"),
        preparo_raiz=str(Path(tmp_path) / "prep_assuntos"), id_execucao="a1", **kw,
    )


def _nomes(r):
    return {x["identidade"] for x in r.diferencas}


def _politica():
    return tg._politica()


def _grupos_df(spark, pares):
    return spark.createDataFrame(pares, "especie_codigo string, grupo_especie string")


def _linhas_df(spark, linhas):
    return spark.createDataFrame(
        [(c, "D", "d", Decimal(v), COMP, "x") for c, v in linhas],
        "especie_codigo string, especie_descricao string, especie_descricao_normalizada string, "
        "vl_liquido decimal(14,2), competencia string, classificacao string",
    )


def _lido(spark, caminho):
    return spark.read.format("delta").load(str(caminho)).where(F.col("competencia") == COMP)


# ---------------------------------------------------------------- eval_1


def test_fat_especie_fecha_com_a_ancora(spark, tmp_path):
    cen, d, contrato = _preparar(spark, tmp_path)
    r = _rodar(spark, tmp_path, d, contrato)
    assert r.estado == ga.INTEGRO, (r.estado, r.motivo, r.diferencas)
    fat = _lido(spark, tmp_path / "fat")
    assert tuple(fat.columns) == ga.FAT_COLUNAS
    assert fat.count() == 7
    assert fat.select("especie_codigo", "competencia").distinct().count() == 7  # grão
    assert fat.schema["vl_total"].dataType == DecimalType(14, 2)
    linha = {row["especie_codigo"]: row for row in fat.collect()}
    assert linha["01"]["grupo_especie"] == "Pensao" and linha["04"]["grupo_especie"] == "Aposentadoria"
    assert sum(x["qtd_beneficios"] for x in linha.values()) == 7
    assert sum(x["vl_total"] for x in linha.values()) == Decimal("2011.00")
    assert {c: x["vl_total"] for c, x in linha.items()} == tg.MAPA_ESPERADO
    assert linha["01"]["rank_no_grupo"] == 1 and linha["02"]["rank_no_grupo"] == 5


def test_kpis_somam_fat_especie(spark, tmp_path):
    cen, d, contrato = _preparar(spark, tmp_path)
    assert _rodar(spark, tmp_path, d, contrato).estado == ga.INTEGRO
    fat = _lido(spark, tmp_path / "fat")
    kpis = _lido(spark, tmp_path / "kpis")
    assert tuple(kpis.columns) == ga.KPIS_COLUNAS
    assert kpis.count() == 1
    k = kpis.first()
    soma = fat.agg(F.sum("qtd_beneficios"), F.sum("vl_total"), F.sum("qtd_vl_zero")).first()
    assert k["total_beneficios"] == soma[0] == 7
    assert k["vl_total"] == soma[1] == Decimal("2011.00")
    assert k["qtd_vl_zero"] == soma[2] == 0
    assert k["total_especies_ativas"] == 7
    assert k["vl_minimo"] == Decimal("5.00") and k["vl_maximo"] == Decimal("1621.00")


def test_medio_arredonda_meio_para_par(spark):
    pol = _politica()
    linhas = _linhas_df(spark, [("A", "2.00"), ("A", "2.01"), ("B", "2.01"), ("B", "2.02")])
    grupos = _grupos_df(spark, [("A", "G"), ("B", "G")])
    fat = {r["especie_codigo"]: r for r in ga.montar_fat_especie(linhas, grupos, COMP, pol).collect()}
    assert fat["A"]["vl_medio"] == Decimal("2.00")  # 2,005 → par; meio-para-cima daria 2,01
    assert fat["B"]["vl_medio"] == Decimal("2.02")  # 2,015 → par
    assert "round(" not in inspect.getsource(ga).replace("bround(", "")


def test_percentis_rotulados_aprox(spark):
    pol = _politica()
    linhas = _linhas_df(spark, [("A", f"{n}.00") for n in range(1, 11)])
    fat = ga.montar_fat_especie(linhas, _grupos_df(spark, [("A", "G")]), COMP, pol)
    kpis = ga.montar_kpis_nacionais(fat, linhas, COMP, pol)
    for df in (fat, kpis):
        assert "vl_mediano_aprox" in df.columns and "vl_p90_aprox" in df.columns
        assert not {"vl_mediano", "vl_p90", "vl_percentil"} & set(df.columns)
    a = fat.first()
    assert a["vl_mediano_aprox"] == Decimal("5.00") and a["vl_p90_aprox"] == Decimal("9.00")
    k = kpis.first()
    assert k["vl_mediano_aprox"] == Decimal("5.00") and k["vl_p90_aprox"] == Decimal("9.00")
    assert isinstance(ga.PRECISAO_PERCENTIL, int) and ga.PRECISAO_PERCENTIL > 0


def _republicar_silver_diferente(spark, d):
    """Uma versão MAIS RECENTE da Silver, com outra soma — quem lê a mais recente não fecha."""
    silver_atual = spark.read.format("delta").load(d["silver"]).where(F.col("competencia") == COMP)
    alterada = silver_atual.withColumn(
        "vl_liquido", F.when(F.col("especie_codigo") == "02", F.lit(Decimal("6.00"))).otherwise(F.col("vl_liquido"))
    )
    _, dono, _ = bronze.ler_competencia_publicada(spark, d["silver"], COMP)
    bronze.publicar_competencia(spark, alterada, d["silver"], COMP, dono)
    return bronze._versao_atual(spark, d["silver"])


def test_le_silver_por_versao(spark, tmp_path):
    cen, d, contrato = _preparar(spark, tmp_path)
    _, dono_gold, _ = bronze.ler_competencia_publicada(spark, d["gold"], COMP)
    nomeada = int(dono_gold["versao_silver"])
    nova = _republicar_silver_diferente(spark, d)
    assert nova > nomeada
    linhas, estado, _ = ga._ler_silver_nomeada(spark, d["silver"], COMP, nomeada)
    assert estado == ga.INTEGRO
    assert linhas.agg(F.sum("vl_liquido")).first()[0] == Decimal("2011.00")  # versionAsOf, não a mais recente
    recente, _, _ = ga._ler_silver_nomeada(spark, d["silver"], COMP, nova)
    assert recente.agg(F.sum("vl_liquido")).first()[0] == Decimal("2012.00")


def test_usa_a_silver_nomeada_pela_gold(spark, tmp_path):
    cen, d, contrato = _preparar(spark, tmp_path)
    _, dono_gold, _ = bronze.ler_competencia_publicada(spark, d["gold"], COMP)
    _republicar_silver_diferente(spark, d)
    r = _rodar(spark, tmp_path, d, contrato)
    assert r.estado == ga.INTEGRO, (r.estado, r.motivo, r.diferencas)  # a mais recente somaria 2012,00 e divergiria
    assert r.versao_silver == int(dono_gold["versao_silver"])
    assert _lido(spark, tmp_path / "fat").agg(F.sum("vl_total")).first()[0] == Decimal("2011.00")


def test_extremos_conferem_com_a_ancora(spark, tmp_path):
    cen, d, _ = _preparar(spark, tmp_path)
    for campo, valor in (("max_vl_liquido", "1622.00"), ("min_vl_liquido", "4.99")):
        contrato = _contrato_com(cen, tmp_path, f"ancora-{campo}", mexer=lambda x, c=campo, v=valor: x["ancora"].update({c: v}))
        r = _rodar(spark, tmp_path, d, contrato)
        assert r.estado == ga.DIVERGE and campo in _nomes(r), (campo, r.estado, _nomes(r))
    assert not (tmp_path / "fat").exists() and not (tmp_path / "kpis").exists()


def test_medio_nacional_nao_e_media_das_medias(spark):
    pol = _politica()
    linhas = _linhas_df(spark, [("A", "1.00"), ("B", "3.00"), ("B", "3.00"), ("B", "3.00")])
    fat = ga.montar_fat_especie(linhas, _grupos_df(spark, [("A", "G"), ("B", "G")]), COMP, pol)
    medias = {r["especie_codigo"]: r["vl_medio"] for r in fat.collect()}
    assert medias == {"A": Decimal("1.00"), "B": Decimal("3.00")}  # média das médias seria 2,00
    k = ga.montar_kpis_nacionais(fat, linhas, COMP, pol).first()
    assert k["vl_medio"] == Decimal("2.50")  # 10,00 / 4
    assert k["total_beneficios"] == 4 and k["vl_total"] == Decimal("10.00")


# ---------------------------------------------------------------- eval_2


def test_publica_com_replacewhere(spark, tmp_path):
    cen, d, contrato = _preparar(spark, tmp_path)
    assert _rodar(spark, tmp_path, d, contrato).estado == ga.INTEGRO
    for tabela in ("fat", "kpis"):
        historico = bronze._delta_table(spark, str(tmp_path / tabela)).history().select("operation", "operationParameters").collect()
        escritas = [h for h in historico if h["operation"] == "WRITE"]
        assert len(escritas) == 1
        assert COMP in str(escritas[0]["operationParameters"].get("predicate", ""))
    # outra competência no mesmo destino sobrevive à republicação da primeira
    fat = spark.read.format("delta").load(str(tmp_path / "fat"))
    fat.limit(1).withColumn("competencia", F.lit("2099-01")).write.format("delta").mode("append").save(str(tmp_path / "fat"))
    r = ga.executar_gold_assuntos(
        spark, caminho_contrato=contrato, silver_destino=d["silver"], gold_principal_destino=d["gold"],
        fat_destino=str(tmp_path / "fat"), kpis_destino=str(tmp_path / "kpis"),
        preparo_raiz=str(tmp_path / "prep_assuntos"), id_execucao="a2",
    )
    assert r.estado == ga.INTEGRO
    fat = spark.read.format("delta").load(str(tmp_path / "fat"))
    assert fat.where(F.col("competencia") == COMP).count() == 7  # idempotente
    assert fat.where(F.col("competencia") == "2099-01").count() == 1
    assert "overwriteSchema" not in inspect.getsource(ga)


def test_check_nao_negativo_monetario(spark, tmp_path):
    cen, d, contrato = _preparar(spark, tmp_path)
    assert _rodar(spark, tmp_path, d, contrato).estado == ga.INTEGRO
    for tabela, colunas in (("fat", ga.MONETARIAS_FAT), ("kpis", ga.MONETARIAS_KPIS)):
        caminho = str(tmp_path / tabela)
        propriedades = bronze._delta_table(spark, caminho).detail().select("properties").first()[0]
        base = spark.read.format("delta").load(caminho).limit(1)
        for coluna in colunas:
            assert f"delta.constraints.{coluna}_nao_negativo" in propriedades
            negativo = base.withColumn(coluna, F.lit(Decimal("-1.00")).cast(base.schema[coluna].dataType))
            with pytest.raises(Exception):
                negativo.write.format("delta").mode("append").save(caminho)


def test_commit_nomeia_versoes_lidas(spark, tmp_path):
    cen, d, contrato = _preparar(spark, tmp_path)
    _, dono_gold, versao_gold = bronze.ler_competencia_publicada(spark, d["gold"], COMP)
    r = _rodar(spark, tmp_path, d, contrato)
    assert r.estado == ga.INTEGRO
    assert r.versao_gold_principal == versao_gold
    for tabela in ("fat", "kpis"):
        _, dono, _ = bronze.ler_competencia_publicada(spark, str(tmp_path / tabela), COMP)
        assert dono["versao_silver"] == int(dono_gold["versao_silver"])
        assert dono["versao_gold_principal"] == versao_gold
        assert dono["precisao_percentil"] == ga.PRECISAO_PERCENTIL
        assert json.loads(json.dumps(dono))["estado"] == ga.INTEGRO


# ---------------------------------------------------------------- eval_3


def _nada_publicado(tmp_path):
    return not (tmp_path / "fat").exists() and not (tmp_path / "kpis").exists()


def test_sem_gold_principal_nao_medido(spark, tmp_path):
    cen, d, contrato = _preparar(spark, tmp_path, gold_principal=False)
    r = _rodar(spark, tmp_path, d, contrato)
    assert r.estado == ga.NAO_MEDIDO and r.motivo == "SEM_GOLD_PRINCIPAL_PUBLICADA"
    assert r.fat_especie is None and _nada_publicado(tmp_path)


def test_sem_grupos_nao_medido(spark, tmp_path):
    cen, d, _ = _preparar(spark, tmp_path)
    sem = _contrato_com(cen, tmp_path, "sem-grupos", grupos=False)
    r = _rodar(spark, tmp_path, d, sem)
    assert r.estado == ga.NAO_MEDIDO and r.motivo == "SEM_GRUPOS_ESPECIE"
    assert _nada_publicado(tmp_path)


def test_codigo_fora_do_mapa_diverge(spark, tmp_path):
    cen, d, _ = _preparar(spark, tmp_path)
    fora = _contrato_com(cen, tmp_path, "fora-do-mapa", grupos=["01", "03", "23", "59", "99"])  # o 02 ficou de fora
    r = _rodar(spark, tmp_path, d, fora)
    assert r.estado == ga.DIVERGE and "codigo_fora_do_mapa:02" in _nomes(r)
    assert _nada_publicado(tmp_path)


def test_soma_que_nao_fecha_diverge(spark, tmp_path):
    cen, d, _ = _preparar(spark, tmp_path)
    contrato = _contrato_com(cen, tmp_path, "soma", mexer=lambda x: x["ancora"].update({"sum_vl_liquido": "2011.01"}))
    r = _rodar(spark, tmp_path, d, contrato)
    assert r.estado == ga.DIVERGE and "sum_vl_liquido" in _nomes(r)
    assert _nada_publicado(tmp_path)
