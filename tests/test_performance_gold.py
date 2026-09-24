"""Testes de performance da Gold e dos assuntos — a saída não muda, só o custo.

Rodam DENTRO do contêiner pda-spark. O tempo NÃO é medido aqui (instável dentro de
eval): o PERF=MELHOR contra perf/ é verificação pós-assentamento, com a skill spark-perf.
Aqui se prova o comportamento declarado: cache liberado em todo caminho, CHECK por coluna
no próprio CREATE e a reconferência numa passada acusando o que as duas acusavam.
"""

from __future__ import annotations

import inspect
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pyspark.sql.types import DecimalType, StringType, StructField, StructType  # noqa: E402

import test_gold as tg  # noqa: E402
from test_gold import spark  # noqa: E402,F401  (a mesma sessão de teste)
from medalhao import bronze, gold, gold_assuntos as ga  # noqa: E402

COMP = tg.COMP
CHAVES = ("especie_codigo", "competencia")


def _schema_fat() -> StructType:
    campos = [StructField("especie_codigo", StringType(), False), StructField("competencia", StringType(), False)]
    campos += [StructField(c, DecimalType(14, 2)) for c in ga.MONETARIAS_FAT]
    return StructType(campos)


def _operacoes(spark, caminho):
    return [h["operation"] for h in bronze._delta_table(spark, caminho).history().select("operation").collect()]


def _propriedades(spark, caminho):
    return bronze._delta_table(spark, caminho).detail().select("properties").first()[0] or {}


def _eventos(monkeypatch):
    eventos = []
    conferir, liberar = gold._conferir_tabela, bronze._liberar

    def conferindo(*a, **kw):
        eventos.append("conferiu")
        return conferir(*a, **kw)

    def liberando(*dfs):
        if any(df is not None for df in dfs):
            eventos.append("liberou")
        return liberar(*dfs)

    monkeypatch.setattr(gold, "_conferir_tabela", conferindo)
    monkeypatch.setattr(bronze, "_liberar", liberando)
    return eventos


# ---------------------------------------------------------------- eval_1


def test_gold_unpersist_depois_de_publicar(spark, tmp_path, monkeypatch):
    contrato, _, g = tg._gold_de(spark, tmp_path)
    assert g.cache is not None and g.cache.is_cached
    eventos = _eventos(monkeypatch)
    r = gold.publicar(spark, contrato, g, tg._desfecho_autorizado(tmp_path), destino=str(tmp_path / "dest"),
                      id_execucao="perf-ok")
    assert r.gravacao
    assert eventos == ["conferiu", "liberou"]  # nunca antes da reconferência
    assert not g.cache.is_cached


def test_gold_unpersist_tambem_na_falha(spark, tmp_path, monkeypatch):
    contrato, _, g = tg._gold_de(spark, tmp_path)

    def explode(*a, **kw):
        raise OSError("falha de escrita")

    monkeypatch.setattr(gold, "publicar_competencia", explode)
    with pytest.raises(OSError):
        gold.publicar(spark, contrato, g, tg._desfecho_autorizado(tmp_path), destino=str(tmp_path / "dest"),
                      id_execucao="perf-falha")
    assert not g.cache.is_cached


def test_gold_unpersist_tambem_na_divergencia(spark, tmp_path, monkeypatch):
    contrato, _, g = tg._gold_de(spark, tmp_path)
    monkeypatch.setattr(gold, "_conferir_tabela", lambda *a, **kw: (False, {"versao": 0}))
    r = gold.publicar(spark, contrato, g, tg._desfecho_autorizado(tmp_path), destino=str(tmp_path / "dest"),
                      id_execucao="perf-diverge")
    assert r.estado == gold.DIVERGE
    assert not g.cache.is_cached


def test_checks_no_proprio_create(spark, tmp_path):
    caminho = str(tmp_path / "fat")
    ga._garantir_tabela(spark, caminho, _schema_fat(), CHAVES, ga.MONETARIAS_FAT)
    assert _operacoes(spark, caminho) == ["CREATE TABLE"]  # um commit em vez de sete
    propriedades = _propriedades(spark, caminho)
    for coluna in ga.MONETARIAS_FAT:
        assert propriedades[f"delta.constraints.{coluna}_nao_negativo"] == f"{coluna} >= 0"


def test_tabela_existente_reconhecida(spark, tmp_path):
    caminho = str(tmp_path / "fat")
    ga._garantir_tabela(spark, caminho, _schema_fat(), CHAVES, ga.MONETARIAS_FAT)
    antes, props = _operacoes(spark, caminho), _propriedades(spark, caminho)
    ga._garantir_tabela(spark, caminho, _schema_fat(), CHAVES, ga.MONETARIAS_FAT)  # reentrada
    assert _operacoes(spark, caminho) == antes
    assert _propriedades(spark, caminho) == props

    legada = str(tmp_path / "legada")  # criada como antes: sem CHECK, e eles vêm por ALTER
    from delta.tables import DeltaTable

    b = DeltaTable.createIfNotExists(spark).location(legada)
    for campo in _schema_fat():
        b = b.addColumn(campo.name, campo.dataType, nullable=campo.nullable)
    b.partitionedBy("competencia").execute()
    for coluna in ga.MONETARIAS_FAT:
        spark.sql(f"ALTER TABLE delta.`{legada}` ADD CONSTRAINT {coluna}_nao_negativo CHECK ({coluna} >= 0)")
    antes = _operacoes(spark, legada)
    ga._garantir_tabela(spark, legada, _schema_fat(), CHAVES, ga.MONETARIAS_FAT)
    assert _operacoes(spark, legada) == antes  # reconhecida como protegida: nada novo, nada perdido


def test_assuntos_liberam_o_cache_em_todo_caminho(spark, tmp_path, monkeypatch):
    persistidos = []
    original = ga._executar_gold_assuntos

    def capturando(spark_, lista, **kw):
        try:
            return original(spark_, lista, **kw)
        finally:
            persistidos.extend(lista)

    monkeypatch.setattr(ga, "_executar_gold_assuntos", capturando)
    _, d, contrato = _preparar_assuntos(spark, tmp_path)
    r = ga.executar_gold_assuntos(
        spark, caminho_contrato=contrato, silver_destino=d["silver"], gold_principal_destino=d["gold"],
        fat_destino=str(tmp_path / "fat"), kpis_destino=str(tmp_path / "kpis"),
        preparo_raiz=str(tmp_path / "prep_assuntos"), id_execucao="p1",
    )
    assert r.estado == ga.INTEGRO and persistidos
    assert all(not df.is_cached for df in persistidos)


def _preparar_assuntos(spark, tmp_path):
    import test_gold_assuntos as tga

    return tga._preparar(spark, tmp_path)


# ---------------------------------------------------------------- eval_2


def test_checks_do_create_recusam_negativo(spark, tmp_path):
    caminho = str(tmp_path / "fat")
    ga._garantir_tabela(spark, caminho, _schema_fat(), CHAVES, ga.MONETARIAS_FAT)
    for coluna in ga.MONETARIAS_FAT:
        valores = {c: Decimal("1.00") for c in ga.MONETARIAS_FAT}
        valores[coluna] = Decimal("-1.00")
        linha = ("01", COMP) + tuple(valores[c] for c in ga.MONETARIAS_FAT)
        negativo = spark.createDataFrame([linha], _schema_fat())
        with pytest.raises(Exception):
            negativo.write.format("delta").mode("append").save(caminho)
    assert spark.read.format("delta").load(caminho).count() == 0


def test_gold_uma_passada_diverge_linha_trocada(spark, tmp_path):
    pol = tg._politica()
    valores = ("10.00", "20.00", "30.00", "40.00")
    esperado = tg._df_gold(spark, [("01", "A", v) for v in valores])
    lido = tg._df_gold(spark, [("01", "A", v) for v in ("10.00", "21.00", "29.00", "40.00")])
    caminho = str(tmp_path / "tab")
    gold._garantir_tabela(spark, caminho, pol)
    gold.publicar_competencia(spark, lido, caminho, COMP, {"competencia": COMP})
    ok, detalhe = gold._conferir_tabela(
        spark, caminho, gold._versao_atual(spark, caminho), esperado, {"sum_vl_liquido": Decimal("100.00")}, COMP, pol
    )
    assert detalhe["controles_divergentes"] == ()  # 20/30 por 21/29 preserva a soma
    assert (detalhe["so_no_esperado"], detalhe["so_no_lido"]) == (2, 2)
    assert ok is False
    assert "exceptAll" not in inspect.getsource(gold._conferir_tabela)
    assert "exceptAll" not in inspect.getsource(ga._conferir_tabela)


def test_gold_uma_passada_igual_a_duas(spark):
    base = [("01", "A", v) for v in ("10.00", "20.00", "30.00", "40.00")]
    casos = [(base, base), (base, base[:3]), (base[:3], base), (base, base + base[:1]),
             (base, [("01", "A", "10.00")] * 4)]
    for esperado_linhas, lido_linhas in casos:
        e, l = tg._df_gold(spark, esperado_linhas), tg._df_gold(spark, lido_linhas)
        assert bronze._diferenca_numa_passada(e, l) == (e.exceptAll(l).count(), l.exceptAll(e).count())
