"""Testes da Silver — normaliza a forma, classifica a identidade colapsada, grava em Delta.

Rodam DENTRO do contêiner pda-spark. Silver consome a saída REAL de Bronze
(`bronze.executar_leitura` sobre um lago de teste), nunca uma fixture escrita à
mão. Nada grava no destino real: os destinos Delta vivem sob `tmp_path`.
"""

from __future__ import annotations

import dataclasses
import decimal
import json
import sys
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pyspark.sql import functions as F  # noqa: E402
from pyspark.sql.types import (  # noqa: E402
    DecimalType,
    DoubleType,
    StringType,
    StructField,
    StructType,
)

from medalhao import bronze, silver  # noqa: E402
from pda import juizo  # noqa: E402
from pda.contrato import (  # noqa: E402
    Ancora,
    Cardinalidade,
    Contrato,
    DefeitoConhecido,
    GrupoColapso,
    Layout,
    MapaColapsos,
    Particionamento,
    PoliticaDecimal,
    Procedencia,
)

RAIZ_REPO = Path(__file__).resolve().parent.parent
COMP = "2026-01"
HASH_CSV = "a" * 64
HASH_ZIP = "b" * 64

ESQUEMA = StructType(
    [
        StructField("especie_codigo", StringType()),
        StructField("especie_descricao", StringType()),
        StructField("vl_liquido", DecimalType(14, 2)),
    ]
)

# 4 códigos, 3 descrições, 1 colapso (APOSENTADORIA: 01 e 02), 2 códigos colapsados.
LINHAS = [
    ("01", "APOSENTADORIA", Decimal("10.00")),
    ("02", "APOSENTADORIA", Decimal("20.00")),
    ("03", "PENSAO", Decimal("30.00")),
    ("01", "APOSENTADORIA", Decimal("5.00")),
    ("04", "AUXILIO", Decimal("0.00")),
]
GRUPO = GrupoColapso(descricao="APOSENTADORIA", codigos=("01", "02"))
MAPA = MapaColapsos(grupos=(GRUPO,), aprovado_por="teste", aprovado_em="2026-09-23")
DEFEITO = DefeitoConhecido(
    tipo=silver.TIPO_COLAPSO,
    descricao="identidade colapsada na origem",
    quantidade=1,
    aprovador="teste",
    aprovado_em="2026-09-23",
)


# ---------------------------------------------------------------- apoio


@pytest.fixture(scope="session")
def spark():
    sessao = bronze.criar_sessao("teste-silver")
    sessao.conf.set("spark.sql.shuffle.partitions", "4")
    yield sessao
    sessao.stop()


def _politica(**kw) -> PoliticaDecimal:
    base = dict(
        modo="HALF_EVEN",
        escala=2,
        escala_maxima_intermediarios=3,
        precisao=14,
        nao_negativo=True,
        emax=999999,
        emin=-999999,
    )
    base.update(kw)
    return PoliticaDecimal(**base)


def _totais(linhas):
    valores = [v for _, _, v in linhas]
    return dict(
        count_linhas=len(valores),
        sum_vl_liquido=sum(valores, Decimal("0")),
        min_vl_liquido=min(valores),
        max_vl_liquido=max(valores),
    )


def _contrato(linhas=None, mapa=MAPA, defeitos=(DEFEITO,), cardinalidade=None, competencia=COMP) -> Contrato:
    linhas = LINHAS if linhas is None else linhas
    ancora = dict(linhas_invalidas=0, aprovado_por="teste", aprovado_em="2026-09-23", **_totais(linhas))
    card = cardinalidade or Cardinalidade(
        codigos_distintos=4, descricoes_distintas=3, colapsos=1, codigos_colapsados=2
    )
    return Contrato(
        competencia=competencia,
        procedencia=Procedencia(
            fonte="teste.csv", hash_zip_sha256=HASH_ZIP, hash_csv_sha256=HASH_CSV, publicado_em=competencia
        ),
        layout=Layout(total_colunas=14, separador=";", encoding="utf-8", posicoes={"especie": 12}),
        ancora=Ancora(**ancora),
        cardinalidade=card,
        defeitos_conhecidos=tuple(defeitos),
        politica_decimal=_politica(),
        particionamento=Particionamento(
            chave="competencia",
            caminho="s3a://landing/pda/beneficios-emitidos",
            formato="parquet",
            valores_medidos=(competencia,),
            objetos_auxiliares_ignorados=("_SUCCESS",),
        ),
        mapa_colapsos=mapa,
    )


def _bronze_real(spark, tmp_path: Path, linhas=None, contrato=None, procedencia=None):
    """A saída REAL de Bronze — produzida pelo módulo de Bronze sobre um lago de teste."""
    linhas = LINHAS if linhas is None else linhas
    raiz = tmp_path / "lago"
    spark.createDataFrame(linhas, ESQUEMA).coalesce(1).write.mode("overwrite").parquet(
        str(raiz / f"competencia={COMP}")
    )
    b = bronze.executar_leitura(
        spark, contrato or _contrato(linhas), raiz=str(raiz), gravar=False, procedencia=procedencia
    )
    assert b.estado == bronze.INTEGRO, (b.estado, b.motivo, b.diferencas)
    return b


def _classificar(spark, tmp_path, linhas=None, contrato=None, **kw):
    linhas = LINHAS if linhas is None else linhas
    contrato = contrato or _contrato(linhas)
    b = _bronze_real(spark, tmp_path, linhas, contrato, kw.pop("procedencia", None))
    kw.setdefault("gravar", False)
    return silver.executar_classificacao(spark, contrato, b, **kw), b


def _gravar(spark, tmp_path, contrato=None, linhas=None, competencia=COMP, id_execucao="e1", **kw):
    linhas = LINHAS if linhas is None else linhas
    contrato = contrato or _contrato(linhas)
    b = _bronze_real(spark, tmp_path, linhas, contrato)
    return silver.executar_classificacao(
        spark,
        contrato,
        b,
        gravar=True,
        destino=str(tmp_path / "dest"),
        preparo_raiz=str(tmp_path / "prep"),
        id_execucao=id_execucao,
        **kw,
    )


def _nomes(r):
    return {d["identidade"] for d in r.diferencas}


def _adulterado(spark, linhas):
    return spark.createDataFrame(linhas, ESQUEMA).withColumn("competencia", F.lit(COMP))


# ---------------------------------------------------------------- eval_1


def test_chave_e_codigo(spark, tmp_path):
    r, b = _classificar(spark, tmp_path)
    assert r.estado == silver.INTEGRO, (r.motivo, r.diferencas)
    # agrupar por descrição fundiria 01 e 02 em APOSENTADORIA (35.00); a chave é o código
    assert r.total_por_codigo == {
        "01": Decimal("15.00"),
        "02": Decimal("20.00"),
        "03": Decimal("30.00"),
        "04": Decimal("0.00"),
    }
    assert r.total_por_codigo == b.total_por_codigo
    assert len(r.total_por_codigo) == r.medidas["codigos_distintos"]


def test_multiconjunto_identico(spark, tmp_path):
    r, b = _classificar(spark, tmp_path)
    so_bronze, so_silver = silver._diferenca_multiconjunto(b.linhas, r.linhas)
    assert (so_bronze, so_silver) == (0, 0)
    assert r.linhas.count() == b.linhas.count() == len(LINHAS)


def test_linhas_irmas_com_valores_trocados(spark, tmp_path):
    # mesmo código e mesma descrição: 10.00/20.00 virando 11.00/19.00 preserva contagem, soma e mapa
    irmas = [("01", "A", Decimal("10.00")), ("01", "A", Decimal("20.00"))]
    trocadas = [("01", "A", Decimal("11.00")), ("01", "A", Decimal("19.00"))]
    b = spark.createDataFrame(irmas, ESQUEMA)
    s = spark.createDataFrame(trocadas, ESQUEMA)
    assert silver._diferenca_multiconjunto(b, s) == (2, 2)


def test_linha_de_valor_zero_nao_some(spark, tmp_path):
    r, b = _classificar(spark, tmp_path)
    zeros = r.linhas.where(F.col("vl_liquido") == 0)
    assert zeros.count() == 1
    sem_a_de_zero = b.linhas.where(F.col("vl_liquido") != 0)
    # soma e mapa por código idênticos sem a linha de zero — só o multiconjunto a acusa
    assert silver._diferenca_multiconjunto(b.linhas, sem_a_de_zero) == (1, 0)
    assert r.controles["count_linhas"] == len(LINHAS)


def test_mapa_por_codigo_preservado(spark, tmp_path):
    r, b = _classificar(spark, tmp_path)
    assert r.total_por_codigo == b.total_por_codigo
    assert all(isinstance(v, Decimal) for v in r.total_por_codigo.values())
    assert r.controles["sum_vl_liquido"] == Decimal("65.00")

    # troca de valores entre dois códigos: soma e chaves iguais, mapa diferente
    ctr = _contrato()
    b2 = _bronze_real(spark, tmp_path, contrato=ctr)
    trocado = replace(b2, total_por_codigo={**b2.total_por_codigo, "01": Decimal("20.00"), "02": Decimal("15.00")})
    r2 = silver.executar_classificacao(spark, ctr, trocado, gravar=False)
    assert r2.estado == silver.DIVERGE
    assert {"total_por_codigo:01", "total_por_codigo:02"} <= _nomes(r2)


def test_contexto_declarado(spark, tmp_path):
    pol = _politica()
    ctx = silver.contexto_declarado(pol)
    assert (ctx.prec, ctx.Emax, ctx.Emin) == (14, 999999, -999999)
    assert ctx.rounding == decimal.ROUND_HALF_EVEN
    assert not any(ctx.traps.values())

    antigo = decimal.getcontext().copy()
    try:
        decimal.getcontext().prec = 3
        decimal.getcontext().Emax = 5
        r, _ = _classificar(spark, tmp_path)
        assert r.estado == silver.INTEGRO
        assert r.controles["sum_vl_liquido"] == Decimal("65.00")
        assert silver.contexto_declarado(pol).prec == 14
    finally:
        decimal.setcontext(antigo)


def test_entrega_as_linhas_normalizadas(spark, tmp_path):
    r, _ = _classificar(spark, tmp_path)
    assert r.linhas is not None and not isinstance(r.linhas, (list, tuple))
    assert tuple(r.linhas.columns) == silver.SILVER_COLUNAS
    assert set(silver.SILVER_COLUNAS) >= {
        "especie_codigo", "especie_descricao", "especie_descricao_normalizada",
        "vl_liquido", "competencia", "classificacao",
    }
    assert dict(r.linhas.dtypes)["vl_liquido"] == "decimal(14,2)"
    assert {x[0] for x in r.linhas.select("competencia").distinct().collect()} == {COMP}


def test_descricao_trocada_entre_codigos(spark, tmp_path):
    b = spark.createDataFrame([("01", "A", Decimal("10")), ("03", "B", Decimal("20"))], ESQUEMA)
    s = spark.createDataFrame([("01", "B", Decimal("10")), ("03", "A", Decimal("20"))], ESQUEMA)
    # o multiconjunto de (código, valor) é o mesmo; com a descrição original dentro, não é
    assert b.select("especie_codigo", "vl_liquido").exceptAll(s.select("especie_codigo", "vl_liquido")).count() == 0
    assert silver._diferenca_multiconjunto(b, s) == (2, 2)


def test_multiconjunto_sem_coletar(spark, tmp_path):
    fonte = (RAIZ_REPO / "src" / "medalhao" / "silver.py").read_text(encoding="utf-8")
    corpo = fonte.split("def _diferenca_multiconjunto", 1)[1].split("\ndef ", 1)[0]
    assert "exceptAll" in corpo
    assert ".collect(" not in corpo and ".toPandas(" not in corpo


def test_ansi_declarado_estouro_nao_vira_nulo(spark, tmp_path):
    spark.conf.set("spark.sql.ansi.enabled", "false")
    try:
        _classificar(spark, tmp_path)
        assert spark.conf.get("spark.sql.ansi.enabled") == "true"
    finally:
        spark.conf.set("spark.sql.ansi.enabled", "true")
    with pytest.raises(Exception):
        spark.sql("SELECT CAST(CAST('99999999999999.99' AS DECIMAL(16,2)) AS DECIMAL(14,2)) AS v").collect()


def test_consome_saida_real_de_bronze(spark, tmp_path):
    b = _bronze_real(spark, tmp_path)
    assert isinstance(b, bronze.BronzeConferido)
    r = silver.executar_classificacao(spark, _contrato(), b, gravar=False)
    assert r.estado == silver.INTEGRO
    assert list(b.linhas.columns) == list(bronze.COLUNAS)
    assert r.competencia == b.competencia == COMP


def test_le_bronze_por_versao(spark, tmp_path):
    ctr = _contrato()
    raiz = tmp_path / "lago"
    spark.createDataFrame(LINHAS, ESQUEMA).coalesce(1).write.mode("overwrite").parquet(
        str(raiz / f"competencia={COMP}")
    )
    bdest = str(tmp_path / "bronze")
    gravado = bronze.executar_leitura(
        spark, ctr, raiz=str(raiz), destino=bdest, preparo_raiz=str(tmp_path / "bprep"), id_execucao="b1"
    )
    assert gravado.estado == bronze.INTEGRO

    r = silver.executar_classificacao(spark, ctr, bronze_destino=bdest, gravar=False)
    assert r.estado == silver.INTEGRO
    assert r.versao_bronze == bronze._versao_atual(spark, bdest)
    assert r.hash_procedencia == gravado.hash_procedencia

    lido, versao = silver.ler_bronze(spark, bdest, COMP)
    assert versao == r.versao_bronze and lido.estado == bronze.INTEGRO


def test_grava_silver_com_estado_no_commit(spark, tmp_path):
    r = _gravar(spark, tmp_path)
    assert r.estado == silver.INTEGRO, (r.motivo, r.diferencas)
    assert r.gravacao["id_execucao"] == "e1"
    dest = str(tmp_path / "dest")
    publicado = spark.read.format("delta").load(dest).where(F.col("competencia") == COMP)
    assert publicado.count() == len(LINHAS)
    assert dict(publicado.dtypes)["vl_liquido"] == "decimal(14,2)"
    _, dono, _ = bronze.ler_competencia_publicada(spark, dest, COMP)
    assert dono["estado"] == silver.INTEGRO


def test_reconfere_multiconjunto_das_linhas(spark, tmp_path):
    pol = _politica()
    esperado = _adulterado(spark, [("01", "A", Decimal(v)) for v in ("10.00", "20.00", "30.00", "40.00")])
    lido = _adulterado(spark, [("01", "A", Decimal(v)) for v in ("10.00", "21.00", "29.00", "40.00")])

    def completo(df):
        return (
            df.withColumn("especie_descricao_normalizada", F.upper(F.col("especie_descricao")))
            .withColumn("classificacao", F.lit(None).cast(StringType()))
            .select(*silver.SILVER_COLUNAS)
        )

    caminho = str(tmp_path / "tab")
    silver._garantir_tabela(spark, caminho, pol)
    silver.publicar_competencia(spark, completo(lido), caminho, COMP, {"competencia": COMP})
    controles, _ = bronze.medir_controles(esperado, pol)
    ok, detalhe = silver._conferir_tabela(
        spark, caminho, silver._versao_atual(spark, caminho), completo(esperado), controles, COMP, pol
    )
    assert detalhe["controles_divergentes"] == ()  # 10/20 por 11/19 preserva os cinco controles
    assert detalhe["so_no_esperado"] == 2 and detalhe["so_no_lido"] == 2
    assert ok is False


def test_commit_carrega_a_forma(spark, tmp_path):
    r = _gravar(spark, tmp_path)
    campos = {f.name for f in dataclasses.fields(r)}
    assert {
        "estado", "competencia", "controles", "total_por_codigo", "marcas",
        "hash_procedencia", "linhas", "defeitos", "cobertura",
    } <= campos
    _, dono, _ = bronze.ler_competencia_publicada(spark, str(tmp_path / "dest"), COMP)
    assert set(dono) >= {
        "estado", "competencia", "hash_procedencia", "controles", "marcas", "defeitos",
        "total_por_codigo", "cobertura_referencial", "id_execucao", "versao_camada_anterior",
    }
    assert dono["total_por_codigo"]["01"] == "15.00"
    assert dono["controles"]["sum_vl_liquido"] == "65.00"
    assert dono["cobertura_referencial"]["verificados_pelo_mapa"] == ["01", "02"]


def _duas(spark, tmp_path):
    """Duas competências em Bronze, gravadas em Silver por execuções separadas."""
    resultados = {}
    for comp, exec_id in (("2026-01", "e1"), ("2026-02", "e2")):
        ctr = _contrato(competencia=comp)
        raiz = tmp_path / f"lago-{comp}"
        spark.createDataFrame(LINHAS, ESQUEMA).coalesce(1).write.mode("overwrite").parquet(
            str(raiz / f"competencia={comp}")
        )
        b = bronze.executar_leitura(spark, ctr, raiz=str(raiz), gravar=False)
        resultados[comp] = silver.executar_classificacao(
            spark, ctr, b, gravar=True, destino=str(tmp_path / "dest"),
            preparo_raiz=str(tmp_path / "prep"), id_execucao=exec_id,
        )
    return str(tmp_path / "dest"), resultados


def test_resolve_versao_uma_vez(spark, tmp_path):
    dest, _ = _duas(spark, tmp_path)
    dados, _, versao = silver.ler_competencia_publicada(spark, dest, "2026-01")
    assert versao == max(v for v, _ in silver._historico(spark, dest))
    assert dados.count() == len(LINHAS)
    assert {x[0] for x in dados.select("competencia").distinct().collect()} == {"2026-01"}


def test_schema_evolucao_so_aditiva(spark, tmp_path):
    atual = StructType(ESQUEMA.fields + [StructField("competencia", StringType())])
    with pytest.raises(silver.EvolucaoRecusada):
        silver.verificar_evolucao(atual, StructType([StructField("vl_liquido", DoubleType())]))
    with pytest.raises(silver.EvolucaoRecusada):
        silver.verificar_evolucao(atual, StructType([StructField("vl_liquido", DecimalType(14, 3))]))
    assert silver.verificar_evolucao(atual, StructType(atual.fields + [StructField("nova", StringType())])) == ("nova",)

    fonte = (RAIZ_REPO / "src" / "medalhao" / "silver.py").read_text(encoding="utf-8")
    assert 'option("overwriteSchema"' not in fonte


def test_check_nao_negativo(spark, tmp_path):
    caminho = str(tmp_path / "tab")
    silver._garantir_tabela(spark, caminho, _politica())
    esquema = StructType(
        [
            StructField("especie_codigo", StringType()),
            StructField("especie_descricao", StringType()),
            StructField("especie_descricao_normalizada", StringType()),
            StructField("vl_liquido", DecimalType(14, 2)),
            StructField("competencia", StringType()),
            StructField("classificacao", StringType()),
        ]
    )
    negativo = spark.createDataFrame([("01", "A", "A", Decimal("-1.00"), COMP, None)], esquema)
    with pytest.raises(Exception):
        negativo.write.format("delta").mode("append").save(caminho)
    sem_chave = spark.createDataFrame([(None, "A", "A", Decimal("1.00"), COMP, None)], esquema)
    with pytest.raises(Exception):
        sem_chave.write.format("delta").mode("append").save(caminho)


def test_reconfere_no_preparo_antes_de_publicar(spark, tmp_path, monkeypatch):
    original = silver._gravar_preparo

    def adulterado(spark_, linhas, preparo, competencia, metadados):
        mexido = linhas.withColumn(
            "vl_liquido", (F.col("vl_liquido") + F.lit(Decimal("0.01"))).cast(DecimalType(14, 2))
        )
        original(spark_, mexido, preparo, competencia, metadados)

    monkeypatch.setattr(silver, "_gravar_preparo", adulterado)
    r = _gravar(spark, tmp_path)
    assert r.estado == silver.DIVERGE
    assert "reconferencia_no_preparo" in _nomes(r)
    assert not (tmp_path / "dest").exists()  # nada foi publicado


def test_reverte_so_a_competencia(spark, tmp_path, monkeypatch):
    dest = str(tmp_path / "dest")
    ctr1 = _contrato(competencia="2026-01")
    raiz1 = tmp_path / "lago-2026-01"
    spark.createDataFrame(LINHAS, ESQUEMA).coalesce(1).write.mode("overwrite").parquet(
        str(raiz1 / "competencia=2026-01")
    )
    b1 = bronze.executar_leitura(spark, ctr1, raiz=str(raiz1), gravar=False)
    silver.executar_classificacao(
        spark, ctr1, b1, gravar=True, destino=dest, preparo_raiz=str(tmp_path / "prep"), id_execucao="e1"
    )
    raiz = tmp_path / "lago-2026-02"
    spark.createDataFrame(LINHAS, ESQUEMA).coalesce(1).write.mode("overwrite").parquet(
        str(raiz / "competencia=2026-02")
    )
    original = silver._conferir_tabela

    def reprova_a_publicada(spark_, caminho, *args, **kw):
        if caminho == dest:
            return False, {"so_no_esperado": 1, "so_no_lido": 0, "controles_divergentes": ()}
        return original(spark_, caminho, *args, **kw)

    monkeypatch.setattr(silver, "_conferir_tabela", reprova_a_publicada)
    ctr = _contrato(competencia="2026-02")
    b = bronze.executar_leitura(spark, ctr, raiz=str(raiz), gravar=False)
    r = silver.executar_classificacao(
        spark, ctr, b, gravar=True, destino=dest, preparo_raiz=str(tmp_path / "prep"), id_execucao="e3"
    )
    assert r.estado == silver.DIVERGE
    assert "reconferencia_publicada" in _nomes(r)

    tabela = spark.read.format("delta").load(dest)
    assert tabela.where("competencia = '2026-02'").count() == 0  # revertida
    assert tabela.where("competencia = '2026-01'").count() == len(LINHAS)  # intacta
    operacoes = [x[0] for x in silver._delta_table(spark, dest).history().select("operation").collect()]
    assert "RESTORE" not in operacoes


def test_metadados_do_commit_dono_da_competencia(spark, tmp_path):
    dest, _ = _duas(spark, tmp_path)
    _, dono, versao = silver.ler_competencia_publicada(spark, dest, "2026-01")
    historico = dict(silver._historico(spark, dest))
    assert json.loads(historico[versao])["competencia"] == "2026-02"  # o commit V é de OUTRA
    assert dono["competencia"] == "2026-01"
    assert dono["id_execucao"] == "e1"


# ---------------------------------------------------------------- eval_2


def test_colapso_classificado(spark, tmp_path):
    r, _ = _classificar(spark, tmp_path)
    assert len(r.defeitos) == 1
    d = r.defeitos[0]
    assert d["classificacao"] == juizo.CONFIRMED_SOURCE_DEFECT
    assert d["classificacao"] in silver.CLASSIFICACOES
    assert d["aprovador"] == "teste" and d["aprovado_em"] == "2026-09-23"
    linhas = {(x[0], x[1]) for x in r.linhas.select("especie_codigo", "classificacao").distinct().collect()}
    assert ("01", juizo.CONFIRMED_SOURCE_DEFECT) in linhas and ("02", juizo.CONFIRMED_SOURCE_DEFECT) in linhas
    assert ("03", None) in linhas


def test_quatro_cardinalidades(spark, tmp_path):
    r, _ = _classificar(spark, tmp_path)
    assert r.medidas == {
        "codigos_distintos": 4, "descricoes_distintas": 3, "colapsos": 1, "codigos_colapsados": 2,
    }
    # contrato com 3 colapsos e 4 colapsados nas demais, uma a uma
    for campo, valor in (
        ("codigos_distintos", 5), ("descricoes_distintas", 2), ("colapsos", 2), ("codigos_colapsados", 3),
    ):
        card = dataclasses.replace(_contrato().cardinalidade, **{campo: valor})
        ctr = _contrato(cardinalidade=card)
        b = _bronze_real(spark, tmp_path, contrato=ctr)
        r = silver.executar_classificacao(spark, ctr, b, gravar=False)
        assert r.estado == silver.DIVERGE, campo
        assert f"{campo}" in _nomes(r), campo


def test_classificacao_unica(spark, tmp_path):
    assert silver.classificar("x", ()) == juizo.UNRESOLVED
    assert silver.classificar("x", (juizo.MODERN_DEFECT, juizo.UNRESOLVED)) == juizo.UNRESOLVED
    assert silver.classificar("x", ("INVENTADA",)) == juizo.UNRESOLVED
    assert silver.classificar("x", (juizo.CONFIRMED_SOURCE_DEFECT,)) == juizo.CONFIRMED_SOURCE_DEFECT
    r, _ = _classificar(spark, tmp_path)
    for d in r.defeitos:
        assert d["classificacao"] in silver.CLASSIFICACOES
        assert isinstance(d["classificacao"], str)


def test_colapsos_na_descricao_original(spark, tmp_path):
    # 'ABC' (01,02) e 'abc' (03): normalizadas, viram um grupo só de 3 — a fonte publica DOIS grupos/um colapso
    linhas = [
        ("01", "ABC", Decimal("1.00")),
        ("02", "ABC", Decimal("2.00")),
        ("03", "abc", Decimal("3.00")),
    ]
    grupo = GrupoColapso(descricao="ABC", codigos=("01", "02"))
    mapa = MapaColapsos(grupos=(grupo,), aprovado_por="teste", aprovado_em="2026-09-23")
    card = Cardinalidade(codigos_distintos=3, descricoes_distintas=2, colapsos=1, codigos_colapsados=2)
    ctr = _contrato(linhas, mapa=mapa, cardinalidade=card)
    r, _ = _classificar(spark, tmp_path, linhas, ctr)
    assert r.medidas == {"codigos_distintos": 3, "descricoes_distintas": 2, "colapsos": 1, "codigos_colapsados": 2}
    assert r.defeitos[0]["descricao_original"] == "ABC"  # a original, nunca a normalizada
    assert r.defeitos[0]["codigos"] == ["01", "02"]


def test_colapso_da_normalizacao_classificado(spark, tmp_path):
    linhas = [
        ("01", "ABC", Decimal("1.00")),
        ("02", "ABC", Decimal("2.00")),
        ("03", "abc", Decimal("3.00")),
    ]
    grupo = GrupoColapso(descricao="ABC", codigos=("01", "02"))
    mapa = MapaColapsos(grupos=(grupo,), aprovado_por="teste", aprovado_em="2026-09-23")
    card = Cardinalidade(codigos_distintos=3, descricoes_distintas=2, colapsos=1, codigos_colapsados=2)
    ctr = _contrato(linhas, mapa=mapa, cardinalidade=card)
    r, _ = _classificar(spark, tmp_path, linhas, ctr)
    introduzido = [d for d in r.diferencas if d["identidade"].startswith("colapso_introduzido_pela_camada:")]
    assert {d["identidade"].split(":")[1] for d in introduzido} == {"01", "02", "03"}
    assert all(d["classificacao"] == juizo.MODERN_DEFECT for d in introduzido)
    assert r.estado == silver.BLOQUEADO
    # a descrição ORIGINAL sobrevive na saída: ABC e abc seguem distinguíveis
    originais = {x[0] for x in r.linhas.select("especie_descricao").distinct().collect()}
    assert originais == {"ABC", "abc"}
    normalizadas = {x[0] for x in r.linhas.select("especie_descricao_normalizada").distinct().collect()}
    assert normalizadas == {"ABC"}


def test_recusa_bronze_nao_integro(spark, tmp_path):
    b = _bronze_real(spark, tmp_path)
    for estado in (bronze.DIVERGE, bronze.NAO_MEDIDO, bronze.ERRO_LEITURA):
        entrada = replace(b, estado=estado, motivo=f"BRONZE_{estado}")
        r = silver.executar_classificacao(spark, _contrato(), entrada, gravar=True, destino=str(tmp_path / "d"))
        assert r.estado == estado  # propagado sem tradução
        assert r.linhas is None
        assert r.controles == b.controles and r.hash_procedencia == b.hash_procedencia
    assert not (tmp_path / "d").exists()


def test_colapso_introduzido_por_codigo_bloqueia(spark, tmp_path):
    # 'ABC' cobre 01 e 02; 'abc' cobre 03: um grupo colapsado antes e um depois — a contagem não muda,
    # mas o 03 perdeu identidade
    pares = [("01", "ABC", "ABC"), ("02", "ABC", "ABC"), ("03", "abc", "ABC")]
    assert silver._codigos_com_grupo_alterado(pares) == ["01", "02", "03"]
    # e sem fusão, nenhum código é apontado
    assert silver._codigos_com_grupo_alterado([("01", "A", "A"), ("02", "A", "A"), ("03", "B", "B")]) == []

    linhas = [
        ("01", "ABC", Decimal("1.00")),
        ("02", "ABC", Decimal("2.00")),
        ("03", "abc", Decimal("3.00")),
    ]
    grupo = GrupoColapso(descricao="ABC", codigos=("01", "02"))
    mapa = MapaColapsos(grupos=(grupo,), aprovado_por="teste", aprovado_em="2026-09-23")
    card = Cardinalidade(codigos_distintos=3, descricoes_distintas=2, colapsos=1, codigos_colapsados=2)
    r, _ = _classificar(spark, tmp_path, linhas, _contrato(linhas, mapa=mapa, cardinalidade=card))
    assert r.estado == silver.BLOQUEADO
    assert {"colapso_introduzido_pela_camada:01", "colapso_introduzido_pela_camada:03"} <= set(r.bloqueios)


def test_precedencia_dos_estados_de_falha(spark, tmp_path):
    linhas = [
        ("01", "ABC", Decimal("1.00")),
        ("02", "ABC", Decimal("2.00")),
        ("03", "abc", Decimal("3.00")),
    ]
    card = Cardinalidade(codigos_distintos=3, descricoes_distintas=2, colapsos=1, codigos_colapsados=2)

    # DIVERGE (cardinalidade) vence BLOQUEADO (colapso introduzido) e NAO_MEDIDO (sem mapa)
    errada = dataclasses.replace(card, colapsos=7)
    r, _ = _classificar(spark, tmp_path, linhas, _contrato(linhas, mapa=None, cardinalidade=errada))
    assert r.estado == silver.DIVERGE
    assert "colapsos" in _nomes(r)
    assert any(n.startswith("colapso_introduzido_pela_camada:") for n in _nomes(r))  # toda falha medida sai nomeada

    # BLOQUEADO vence NAO_MEDIDO
    r, _ = _classificar(spark, tmp_path, linhas, _contrato(linhas, mapa=None, cardinalidade=card))
    assert r.estado == silver.BLOQUEADO

    # só o mapa ausente: NAO_MEDIDO
    r, _ = _classificar(spark, tmp_path)
    assert r.estado == silver.INTEGRO
    r, _ = _classificar(spark, tmp_path, contrato=_contrato(mapa=None))
    assert r.estado == silver.NAO_MEDIDO


# ---------------------------------------------------------------- eval_3


def test_nao_classificado_bloqueia(spark, tmp_path):
    # mapa aprovado, mas o contrato NÃO traz o defeito aprovado: ninguém aprovou a classificação
    r, _ = _classificar(spark, tmp_path, contrato=_contrato(defeitos=()))
    assert r.estado == silver.BLOQUEADO
    assert r.defeitos[0]["classificacao"] == juizo.UNRESOLVED
    assert r.estado != silver.INTEGRO
    assert r.bloqueios


def test_valor_intacto(spark, tmp_path):
    r, b = _classificar(spark, tmp_path, contrato=_contrato(defeitos=()))
    assert r.estado == silver.BLOQUEADO
    assert silver._diferenca_multiconjunto(b.linhas, r.linhas) == (0, 0)
    assert r.total_por_codigo == b.total_por_codigo
    assert r.controles["sum_vl_liquido"] == Decimal("65.00")


def test_atravessa_sem_descartar(spark, tmp_path):
    r, b = _classificar(spark, tmp_path, contrato=_contrato(mapa=None, defeitos=()))
    assert r.linhas.count() == b.linhas.count() == len(LINHAS)
    assert r.linhas.where(F.col("vl_liquido") == Decimal("20.00")).count() == 1  # não corrigida


def test_unresolved_bloqueia(spark, tmp_path):
    # grupo medido fora do mapa aprovado: UNRESOLVED, e bloqueia mesmo com o valor conservado
    outro = GrupoColapso(descricao="OUTRA COISA", codigos=("01", "02"))
    mapa = MapaColapsos(grupos=(outro,), aprovado_por="teste", aprovado_em="2026-09-23")
    r, _ = _classificar(spark, tmp_path, contrato=_contrato(mapa=mapa))
    assert r.estado in (silver.BLOQUEADO, silver.DIVERGE)
    assert any(d["classificacao"] == juizo.UNRESOLVED for d in r.defeitos)
    assert r.estado != silver.INTEGRO
    assert silver.bloqueia(juizo.UNRESOLVED)


def test_marca_atravessa(spark, tmp_path):
    r, b = _classificar(spark, tmp_path)  # sem procedência apresentada: Bronze emite a marca
    assert silver.PROCEDENCIA_NAO_VINCULADA in b.marcas
    assert silver.PROCEDENCIA_NAO_VINCULADA in r.marcas
    assert r.marcas == b.marcas


def test_sem_mapa_entrega_estado_nao_medido(spark, tmp_path):
    r, _ = _classificar(spark, tmp_path, contrato=_contrato(mapa=None))
    assert r is not None and isinstance(r, silver.SilverClassificado)
    assert r.estado == silver.NAO_MEDIDO
    assert r.motivo == "MAPA_NAO_DECLARADO"
    assert r.linhas is not None  # a capacidade é entregue, com o estado dizendo por que a cadeia para
    assert all(d["classificacao"] is None and d["referencial"] == "NAO_MEDIDO" for d in r.defeitos)
    # e NAO_MEDIDO ainda grava (valor conservado), com o estado nos metadados
    g = _gravar(spark, tmp_path, contrato=_contrato(mapa=None))
    assert g.estado == silver.NAO_MEDIDO and g.gravacao is not None
    _, dono, _ = bronze.ler_competencia_publicada(spark, str(tmp_path / "dest"), COMP)
    assert dono["estado"] == silver.NAO_MEDIDO


def test_bloqueio_sai_como_bloqueado(spark, tmp_path):
    r, _ = _classificar(spark, tmp_path, contrato=_contrato(defeitos=()))
    assert r.estado == silver.BLOQUEADO and r.estado != silver.INTEGRO
    assert r.motivo == "DEFEITO_BLOQUEANTE"
    assert r.bloqueios and all(isinstance(x, str) for x in r.bloqueios)
    # BLOQUEADO não grava
    g = _gravar(spark, tmp_path, contrato=_contrato(defeitos=()))
    assert g.estado == silver.BLOQUEADO and g.gravacao is None
    assert not (tmp_path / "dest").exists()


def test_controles_e_hash_atravessam(spark, tmp_path):
    r, b = _classificar(spark, tmp_path, procedencia={"hash_csv_sha256": HASH_CSV})
    assert set(r.controles) == set(silver.CONTROLES)
    assert r.controles == b.controles  # os do DETALHE medidos por Bronze, não os das linhas agregadas
    assert r.hash_procedencia == b.hash_procedencia == HASH_CSV
    assert r.competencia == b.competencia
    assert silver.PROCEDENCIA_NAO_VINCULADA not in r.marcas


def test_colapso_um_registro_por_grupo(spark, tmp_path):
    r, _ = _classificar(spark, tmp_path)
    assert len(r.defeitos) == 1  # um por GRUPO — nem por linha (3) nem por código (2)
    d = r.defeitos[0]
    assert d["descricao_original"] == "APOSENTADORIA"
    assert d["codigos"] == ["01", "02"]  # ordenada


def test_cobertura_do_referencial_declarada(spark, tmp_path):
    r, _ = _classificar(spark, tmp_path)
    assert r.cobertura["verificados_pelo_mapa"] == ["01", "02"]
    assert r.cobertura["so_por_cardinalidade"] == ["03", "04"]
    assert r.cobertura["conteudo_dos_nao_colapsados_verificado"] is False


def test_mapa_parcial_recusado(spark, tmp_path):
    # mapa aprovado que declara só 1 dos 2 grupos / códigos do contrato
    card = Cardinalidade(codigos_distintos=4, descricoes_distintas=3, colapsos=2, codigos_colapsados=4)
    ctr = _contrato(cardinalidade=card)
    b = _bronze_real(spark, tmp_path, contrato=ctr)
    r = silver.executar_classificacao(spark, ctr, b, gravar=False)
    assert r.estado == silver.DIVERGE
    assert {"mapa_parcial:grupos", "mapa_parcial:codigos"} <= _nomes(r)
