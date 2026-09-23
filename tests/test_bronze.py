"""Testes da Bronze — lê a partição do lago, confere contra a âncora, grava em Delta.

Rodam DENTRO do contêiner pda-spark (pytest, pyspark e delta-spark lá). Cada
teste monta o seu próprio lago em `tmp_path`; nada grava no destino real — os
destinos Delta de teste vivem sob o prefixo do próprio teste.
"""

from __future__ import annotations

import dataclasses
import decimal
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pyspark.sql import functions as F  # noqa: E402
from pyspark.sql.types import (  # noqa: E402
    DecimalType,
    DoubleType,
    StringType,
    StructField,
    StructType,
)

from medalhao import bronze  # noqa: E402
from pda import contrato as contrato_mod  # noqa: E402
from pda import orquestracao  # noqa: E402
from pda.contrato import (  # noqa: E402
    Ancora,
    Cardinalidade,
    Contrato,
    Layout,
    Particionamento,
    PoliticaDecimal,
    Procedencia,
)

RAIZ_REPO = Path(__file__).resolve().parent.parent
COMP = "2026-01"
HASH_CSV = "a" * 64
HASH_ZIP = "b" * 64

LINHAS_BOAS = [
    ("01", "APOSENTADORIA", Decimal("10.00")),
    ("02", "PENSAO", Decimal("20.50")),
    ("01", "APOSENTADORIA", Decimal("30.25")),
]

ESQUEMA = StructType(
    [
        StructField("especie_codigo", StringType()),
        StructField("especie_descricao", StringType()),
        StructField("vl_liquido", DecimalType(14, 2)),
    ]
)


# ---------------------------------------------------------------- apoio


@pytest.fixture(scope="session")
def spark():
    sessao = bronze.criar_sessao("teste-bronze")
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


def _contrato(competencia: str = COMP, **ancora_kw) -> Contrato:
    ancora = dict(
        count_linhas=3,
        sum_vl_liquido=Decimal("60.75"),
        min_vl_liquido=Decimal("10.00"),
        max_vl_liquido=Decimal("30.25"),
        linhas_invalidas=0,
        aprovado_por="teste",
        aprovado_em="2026-09-23",
    )
    ancora.update(ancora_kw)
    return Contrato(
        competencia=competencia,
        procedencia=Procedencia(
            fonte="teste.csv", hash_zip_sha256=HASH_ZIP, hash_csv_sha256=HASH_CSV, publicado_em=competencia
        ),
        layout=Layout(total_colunas=14, separador=";", encoding="utf-8", posicoes={"especie": 12}),
        ancora=Ancora(**ancora),
        cardinalidade=Cardinalidade(
            codigos_distintos=2, descricoes_distintas=2, colapsos=0, codigos_colapsados=0
        ),
        defeitos_conhecidos=(),
        politica_decimal=_politica(),
        particionamento=Particionamento(
            chave="competencia",
            caminho="s3a://landing/pda/beneficios-emitidos",
            formato="parquet",
            valores_medidos=(competencia,),
            objetos_auxiliares_ignorados=("_SUCCESS",),
        ),
    )


def _escrever(spark, raiz: Path, particao: str, linhas, esquema=ESQUEMA) -> None:
    df = spark.createDataFrame(linhas, esquema)
    df.coalesce(1).write.mode("overwrite").parquet(str(raiz / f"competencia={particao}"))


def _lago(spark, tmp_path: Path, linhas=None, extras=None) -> Path:
    raiz = tmp_path / "lago"
    _escrever(spark, raiz, COMP, LINHAS_BOAS if linhas is None else linhas)
    for nome, ls in (extras or {}).items():
        _escrever(spark, raiz, nome, ls)
    return raiz


def _ler(spark, raiz: Path, contrato=None, **kw):
    kw.setdefault("gravar", False)
    return bronze.executar_leitura(spark, contrato or _contrato(), raiz=str(raiz), **kw)


def _ler_e_gravar(spark, tmp_path, contrato, competencia, raiz, id_execucao, **kw):
    return bronze.executar_leitura(
        spark,
        contrato,
        competencia=competencia,
        raiz=str(raiz),
        destino=str(tmp_path / "dest"),
        preparo_raiz=str(tmp_path / "prep"),
        id_execucao=id_execucao,
        **kw,
    )


def _duas_competencias(spark, tmp_path):
    raiz = tmp_path / "lago"
    _escrever(spark, raiz, "2026-01", LINHAS_BOAS)
    _escrever(spark, raiz, "2026-02", LINHAS_BOAS)
    return raiz, _contrato("2026-01"), _contrato("2026-02")


def _nomes_das_diferencas(r):
    return {d["identidade"] for d in r.diferencas}


# ---------------------------------------------------------------- eval_1


def test_cinco_controles_comparados_individualmente(spark, tmp_path):
    raiz = _lago(spark, tmp_path)
    r = _ler(spark, raiz)
    assert r.estado == bronze.INTEGRO
    assert set(r.controles) == set(bronze.CONTROLES)
    assert r.controles["count_linhas"] == 3
    assert r.controles["sum_vl_liquido"] == Decimal("60.75")
    assert r.controles["min_vl_liquido"] == Decimal("10.00")
    assert r.controles["max_vl_liquido"] == Decimal("30.25")
    assert r.controles["linhas_invalidas"] == 0

    variacoes = {
        "count_linhas": dict(count_linhas=4),
        "sum_vl_liquido": dict(sum_vl_liquido=Decimal("60.76")),
        "min_vl_liquido": dict(min_vl_liquido=Decimal("10.01")),
        "max_vl_liquido": dict(max_vl_liquido=Decimal("30.26")),
        "linhas_invalidas": dict(linhas_invalidas=1),
    }
    for controle, ancora in variacoes.items():
        r = _ler(spark, raiz, _contrato(**ancora))
        assert r.estado == bronze.DIVERGE, controle
        assert r.controles_divergentes == (controle,), controle
        assert r.linhas is None


def test_alteracao_compensada_e_vista_pelo_min_e_max(spark, tmp_path):
    # 10.00 -> 5.00 e 30.25 -> 35.25: contagem e soma intactas.
    raiz = _lago(
        spark,
        tmp_path,
        [("01", "A", Decimal("5.00")), ("02", "B", Decimal("20.50")), ("01", "A", Decimal("35.25"))],
    )
    r = _ler(spark, raiz)
    assert r.estado == bronze.DIVERGE
    assert r.controles["count_linhas"] == 3
    assert r.controles["sum_vl_liquido"] == Decimal("60.75")
    assert set(r.controles_divergentes) == {"min_vl_liquido", "max_vl_liquido"}


def test_isola_particao_e_conta_as_outras(spark, tmp_path):
    fatia = [("01", "A", Decimal("1.00")), ("01", "A", Decimal("2.00"))]
    raiz = _lago(spark, tmp_path, extras={"fatia-teste": fatia})
    r = _ler(spark, raiz)
    assert r.estado == bronze.INTEGRO
    assert r.particoes == {COMP: 3, "fatia-teste": 2}
    assert r.fechamento["fecha"] is True
    assert r.fechamento["total_listado"] == sum(r.particoes.values())


def test_nao_soma_uniao_das_particoes(spark, tmp_path):
    fatia = [("01", "A", Decimal("1.00"))] * 5
    raiz = _lago(spark, tmp_path, extras={"fatia-teste": fatia})
    r = _ler(spark, raiz)
    assert r.controles["count_linhas"] == 3  # e não 8
    assert r.controles["sum_vl_liquido"] == Decimal("60.75")
    assert r.linhas.count() == 3


def test_precisao_declarada_nao_herdada_do_contexto_global(spark, tmp_path):
    pol = _politica()
    ctx = bronze.contexto_declarado(pol)
    assert (ctx.prec, ctx.Emax, ctx.Emin) == (14, 999999, -999999)
    assert ctx.rounding == decimal.ROUND_HALF_EVEN
    assert not any(ctx.traps.values())
    assert bronze.tipo_acumulador(pol) == DecimalType(14, 2)

    raiz = _lago(spark, tmp_path)
    antigo = decimal.getcontext().copy()
    try:
        decimal.getcontext().prec = 3
        decimal.getcontext().Emax = 5
        r = _ler(spark, raiz)
        assert r.estado == bronze.INTEGRO
        assert r.controles["sum_vl_liquido"] == Decimal("60.75")
        # e o contexto declarado ignora o global corrompido
        assert bronze.contexto_declarado(pol).prec == 14
    finally:
        decimal.setcontext(antigo)


def test_entrega_as_linhas_conferidas_com_os_nomes_do_lago(spark, tmp_path):
    raiz = _lago(spark, tmp_path)
    r = _ler(spark, raiz)
    assert r.linhas is not None and not isinstance(r.linhas, (list, tuple))
    assert r.linhas.columns == ["especie_codigo", "especie_descricao", "vl_liquido", "competencia"]
    assert dict(r.linhas.dtypes)["vl_liquido"] == "decimal(14,2)"
    assert r.linhas.count() == 3
    assert {x[0] for x in r.linhas.select("competencia").distinct().collect()} == {COMP}
    assert r.total_por_codigo == {"01": Decimal("40.25"), "02": Decimal("20.50")}


def test_ansi_declarado_estouro_nao_vira_nulo(spark, tmp_path):
    assert spark.conf.get("spark.sql.ansi.enabled") == "true"
    with pytest.raises(Exception):
        spark.sql(
            "SELECT CAST(CAST('99999999999999.99' AS DECIMAL(16,2)) AS DECIMAL(14,2)) AS v"
        ).collect()

    # a leitura declara ANSI mesmo que a sessão tenha chegado com ele desligado
    raiz = _lago(spark, tmp_path)
    spark.conf.set("spark.sql.ansi.enabled", "false")
    try:
        _ler(spark, raiz)
        assert spark.conf.get("spark.sql.ansi.enabled") == "true"
    finally:
        spark.conf.set("spark.sql.ansi.enabled", "true")


def test_entrega_o_hash_da_procedencia(spark, tmp_path):
    raiz = _lago(spark, tmp_path)
    r = _ler(spark, raiz, procedencia={"hash_csv_sha256": HASH_CSV})
    assert r.estado == bronze.INTEGRO
    assert r.hash_procedencia == HASH_CSV
    assert bronze.PROCEDENCIA_NAO_VINCULADA not in r.marcas


def test_posicao_no_lago_nomeada_e_nunca_a_do_csv(spark, tmp_path):
    raiz = _lago(
        spark,
        tmp_path,
        [("01", "A", Decimal("10.00")), ("02", "B", Decimal("-5.00")), ("01", "A", Decimal("30.25"))],
    )
    r = _ler(spark, raiz)
    assert r.estado == bronze.DIVERGE
    assert len(r.defeitos) == 1
    d = r.defeitos[0]
    assert d["defeito"] == "VALOR_NEGATIVO"
    assert d["valor_original"] == "-5.00"
    assert set(d["posicao_lago"]) == {"objeto", "ordinal"}
    assert d["posicao_lago"]["objeto"].endswith(".parquet")
    assert isinstance(d["posicao_lago"]["ordinal"], int)
    assert "posicao" not in d  # o campo do envelope é a linha do CSV
    assert d["classificacao"] in bronze.CLASSIFICACOES


def test_grava_no_minio_e_reconfere(spark, tmp_path):
    raiz = _lago(spark, tmp_path)
    r = _ler_e_gravar(spark, tmp_path, _contrato(), COMP, raiz, "exec-1")
    assert r.estado == bronze.INTEGRO
    assert r.gravacao["id_execucao"] == "exec-1"
    assert (tmp_path / "prep" / "execucao=exec-1").exists()
    publicado = spark.read.format("delta").load(str(tmp_path / "dest"))
    assert publicado.where(F.col("competencia") == COMP).count() == 3
    assert dict(publicado.dtypes)["vl_liquido"] == "decimal(14,2)"


def test_divergente_nao_grava_nada(spark, tmp_path):
    raiz = _lago(spark, tmp_path)
    r = _ler_e_gravar(spark, tmp_path, _contrato(count_linhas=9), COMP, raiz, "exec-x")
    assert r.estado == bronze.DIVERGE
    assert not (tmp_path / "dest").exists()
    assert not (tmp_path / "prep").exists()


def test_replacewhere_nao_toca_outra_competencia(spark, tmp_path):
    raiz, c1, c2 = _duas_competencias(spark, tmp_path)
    dest = str(tmp_path / "dest")
    _ler_e_gravar(spark, tmp_path, c1, "2026-01", raiz, "e1")
    _ler_e_gravar(spark, tmp_path, c2, "2026-02", raiz, "e2")
    _ler_e_gravar(spark, tmp_path, c1, "2026-01", raiz, "e3")  # reexecução: idempotente

    tabela = spark.read.format("delta").load(dest)
    assert tabela.where("competencia = '2026-01'").count() == 3
    assert tabela.where("competencia = '2026-02'").count() == 3
    assert tabela.count() == 6


def test_reconfere_multiconjunto_das_linhas(spark, tmp_path):
    pol = _politica()
    esperado_linhas = [("01", "A", Decimal(v)) for v in ("10.00", "20.00", "30.00", "40.00")]
    lido_linhas = [("01", "A", Decimal(v)) for v in ("10.00", "21.00", "29.00", "40.00")]

    def com_competencia(linhas):
        return spark.createDataFrame(linhas, ESQUEMA).withColumn("competencia", F.lit(COMP))

    esperado = com_competencia(esperado_linhas)
    caminho = str(tmp_path / "tab")
    bronze._garantir_tabela(spark, caminho, pol)
    bronze.publicar_competencia(spark, com_competencia(lido_linhas), caminho, COMP, {"competencia": COMP})

    controles, _ = bronze.medir_controles(esperado, pol)
    ok, detalhe = bronze._conferir_tabela(
        spark, caminho, bronze._versao_atual(spark, caminho), esperado, controles, COMP, pol
    )
    assert detalhe["controles_divergentes"] == ()  # 10/20 por 11/19 preserva os cinco
    assert detalhe["so_no_esperado"] == 2 and detalhe["so_no_lido"] == 2
    assert ok is False


def test_commit_carrega_a_forma(spark, tmp_path):
    raiz = _lago(spark, tmp_path)
    r = _ler_e_gravar(spark, tmp_path, _contrato(), COMP, raiz, "exec-f", procedencia={"hash_csv_sha256": HASH_CSV})
    campos = {f.name for f in dataclasses.fields(r)}
    assert {"estado", "competencia", "controles", "total_por_codigo", "marcas", "hash_procedencia", "linhas"} <= campos

    _, dono, _ = bronze.ler_competencia_publicada(spark, str(tmp_path / "dest"), COMP)
    assert set(dono) >= {
        "estado", "competencia", "hash_procedencia", "controles", "marcas", "defeitos",
        "total_por_codigo", "cobertura_referencial", "id_execucao", "versao_camada_anterior",
    }
    assert dono["estado"] == bronze.INTEGRO
    assert dono["hash_procedencia"] == HASH_CSV
    assert dono["total_por_codigo"] == {"01": "40.25", "02": "20.50"}
    assert dono["controles"]["sum_vl_liquido"] == "60.75"


def test_resolve_versao_uma_vez(spark, tmp_path):
    raiz, c1, c2 = _duas_competencias(spark, tmp_path)
    dest = str(tmp_path / "dest")
    _ler_e_gravar(spark, tmp_path, c1, "2026-01", raiz, "e1")
    _ler_e_gravar(spark, tmp_path, c2, "2026-02", raiz, "e2")

    dados, _, versao = bronze.ler_competencia_publicada(spark, dest, "2026-01")
    ultima = max(v for v, _ in bronze._historico(spark, dest))
    assert versao == ultima
    assert dados.count() == 3
    assert {x[0] for x in dados.select("competencia").distinct().collect()} == {"2026-01"}


def test_metadados_do_commit_dono_da_competencia(spark, tmp_path):
    raiz, c1, c2 = _duas_competencias(spark, tmp_path)
    dest = str(tmp_path / "dest")
    _ler_e_gravar(spark, tmp_path, c1, "2026-01", raiz, "e1")
    _ler_e_gravar(spark, tmp_path, c2, "2026-02", raiz, "e2")

    _, dono, versao = bronze.ler_competencia_publicada(spark, dest, "2026-01")
    historico = dict(bronze._historico(spark, dest))
    assert json.loads(historico[versao])["competencia"] == "2026-02"  # o commit V é de OUTRA
    assert dono["competencia"] == "2026-01"
    assert dono["id_execucao"] == "e1"


def test_schema_evolucao_so_aditiva(spark, tmp_path):
    atual = StructType(ESQUEMA.fields + [StructField("competencia", StringType())])
    with pytest.raises(bronze.EvolucaoRecusada):
        bronze.verificar_evolucao(
            atual,
            StructType(
                [StructField("vl_liquido", DoubleType())]
            ),
        )
    with pytest.raises(bronze.EvolucaoRecusada):
        bronze.verificar_evolucao(atual, StructType([StructField("vl_liquido", DecimalType(14, 3))]))
    assert bronze.verificar_evolucao(atual, StructType(atual.fields + [StructField("nova", StringType())])) == ("nova",)

    fonte = (RAIZ_REPO / "src" / "medalhao" / "bronze.py").read_text(encoding="utf-8")
    assert 'option("overwriteSchema"' not in fonte

    pol = _politica()
    caminho = str(tmp_path / "tab")
    bronze._garantir_tabela(spark, caminho, pol)
    base = spark.createDataFrame(LINHAS_BOAS, ESQUEMA).withColumn("competencia", F.lit(COMP))
    bronze.publicar_competencia(spark, base, caminho, COMP, {"competencia": COMP})
    com_nova = base.withColumn("nova", F.lit("x"))
    with pytest.raises(bronze.EvolucaoRecusada):
        bronze.publicar_competencia(spark, com_nova, caminho, COMP, {"competencia": COMP})
    bronze.publicar_competencia(
        spark, com_nova, caminho, COMP, {"competencia": COMP}, evolucao_aditiva=True
    )
    assert "nova" in spark.read.format("delta").load(caminho).columns


def test_check_nao_negativo_e_not_null_nas_chaves(spark, tmp_path):
    caminho = str(tmp_path / "tab")
    bronze._garantir_tabela(spark, caminho, _politica())
    esquema = StructType(ESQUEMA.fields + [StructField("competencia", StringType())])

    negativo = spark.createDataFrame([("01", "A", Decimal("-1.00"), COMP)], esquema)
    with pytest.raises(Exception):
        negativo.write.format("delta").mode("append").save(caminho)

    sem_chave = spark.createDataFrame([(None, "A", Decimal("1.00"), COMP)], esquema)
    with pytest.raises(Exception):
        sem_chave.write.format("delta").mode("append").save(caminho)


def test_reconfere_no_preparo_antes_de_publicar(spark, tmp_path, monkeypatch):
    original = bronze._gravar_preparo

    def adulterado(spark_, linhas, preparo, competencia, metadados):
        mexido = linhas.withColumn(
            "vl_liquido", (F.col("vl_liquido") + F.lit(Decimal("0.01"))).cast(DecimalType(14, 2))
        )
        original(spark_, mexido, preparo, competencia, metadados)

    monkeypatch.setattr(bronze, "_gravar_preparo", adulterado)
    raiz = _lago(spark, tmp_path)
    r = _ler_e_gravar(spark, tmp_path, _contrato(), COMP, raiz, "exec-p")
    assert r.estado == bronze.DIVERGE
    assert "reconferencia_no_preparo" in _nomes_das_diferencas(r)
    assert not (tmp_path / "dest").exists()  # nada foi publicado


def test_reverte_so_a_competencia(spark, tmp_path, monkeypatch):
    raiz, c1, c2 = _duas_competencias(spark, tmp_path)
    dest = str(tmp_path / "dest")
    _ler_e_gravar(spark, tmp_path, c1, "2026-01", raiz, "e1")

    original = bronze._conferir_tabela

    def reprova_a_publicada(spark_, caminho, *args, **kw):
        if caminho == dest:
            return False, {"so_no_esperado": 1, "so_no_lido": 0, "controles_divergentes": ()}
        return original(spark_, caminho, *args, **kw)

    monkeypatch.setattr(bronze, "_conferir_tabela", reprova_a_publicada)
    r = _ler_e_gravar(spark, tmp_path, c2, "2026-02", raiz, "e2")
    assert r.estado == bronze.DIVERGE
    assert "reconferencia_publicada" in _nomes_das_diferencas(r)

    tabela = spark.read.format("delta").load(dest)
    assert tabela.where("competencia = '2026-02'").count() == 0  # revertida
    assert tabela.where("competencia = '2026-01'").count() == 3  # intacta
    operacoes = [
        x[0] for x in bronze._delta_table(spark, dest).history().select("operation").collect()
    ]
    assert "RESTORE" not in operacoes


# ---------------------------------------------------------------- eval_2


def test_particao_ausente_devolve_nao_medido(spark, tmp_path):
    raiz = _lago(spark, tmp_path)
    r = _ler(spark, raiz, _contrato("2026-02"), competencia="2026-02")
    assert r.estado == bronze.NAO_MEDIDO
    assert r.motivo == "PARTICAO_AUSENTE"
    assert r.linhas is None and r.gravacao is None


def test_particao_vazia_devolve_nao_medido(spark, tmp_path):
    raiz = tmp_path / "lago"
    _escrever(spark, raiz, COMP, [])
    r = _ler(spark, raiz)
    assert r.estado == bronze.NAO_MEDIDO
    assert r.motivo == "PARTICAO_VAZIA"

    so_marcador = tmp_path / "lago2" / f"competencia={COMP}"
    so_marcador.mkdir(parents=True)
    (so_marcador / "_SUCCESS").write_text("")
    r = _ler(spark, tmp_path / "lago2")
    assert r.estado == bronze.NAO_MEDIDO
    assert r.motivo == "PARTICAO_VAZIA"


def test_diverge_nao_e_nao_medido(spark, tmp_path):
    raiz = _lago(spark, tmp_path)
    r = _ler(spark, raiz, _contrato(sum_vl_liquido=Decimal("60.76")))
    assert r.estado == bronze.DIVERGE
    assert r.estado != bronze.NAO_MEDIDO
    assert r.controles  # DIVERGE é medição: os controles estão lá
    assert all(d["classificacao"] in bronze.CLASSIFICACOES for d in r.diferencas)


def test_objeto_orfao_na_listagem_reprova_o_fechamento(spark, tmp_path):
    raiz = _lago(spark, tmp_path)
    spark.createDataFrame([("01", "A", Decimal("1.00"))], ESQUEMA).coalesce(1).write.parquet(
        str(raiz / "orfao")
    )
    (raiz / "competencia=2026-01" / "_SUCCESS").write_text("")  # auxiliar: ignorado
    r = _ler(spark, raiz)
    assert r.estado == bronze.DIVERGE
    assert "fechamento_do_lago" in _nomes_das_diferencas(r)
    assert r.fechamento["fecha"] is False
    assert r.fechamento["fora_das_particoes"] == 1

    # chave de partição nula também não pertence a partição nenhuma
    raiz2 = _lago(spark, tmp_path / "b")
    _escrever(spark, raiz2, "__HIVE_DEFAULT_PARTITION__", [("01", "A", Decimal("1.00"))])
    r = _ler(spark, raiz2)
    assert r.estado == bronze.DIVERGE
    assert r.fechamento["fora_das_particoes"] == 1


def test_erro_leitura_nao_e_nao_medido(spark, tmp_path):
    # objeto ilegível: não consegui medir — não é ausência, não é zero linhas
    raiz = tmp_path / "lago"
    particao = raiz / f"competencia={COMP}"
    particao.mkdir(parents=True)
    (particao / "part-0.parquet").write_bytes(b"isto nao e parquet")
    r = _ler(spark, raiz)
    assert r.estado == bronze.ERRO_LEITURA
    assert r.estado != bronze.NAO_MEDIDO
    assert r.gravacao is None

    # esquema inesperado
    outro = StructType([StructField("outra", StringType())])
    raiz2 = tmp_path / "lago2"
    spark.createDataFrame([("x",)], outro).write.parquet(str(raiz2 / f"competencia={COMP}"))
    r = _ler(spark, raiz2)
    assert r.estado == bronze.ERRO_LEITURA
    assert "ESQUEMA_INESPERADO" in r.motivo


def test_sem_ancora_para_antes_de_bronze(spark, tmp_path):
    bruto = yaml.safe_load((RAIZ_REPO / "contracts" / "competencia-202601.yaml").read_text(encoding="utf-8"))
    del bruto["ancora"]
    sem_ancora = tmp_path / "sem-ancora.yaml"
    sem_ancora.write_text(yaml.safe_dump(bruto), encoding="utf-8")
    assert contrato_mod.carregar_contrato(sem_ancora) == contrato_mod.NAO_MEDIDO

    chamadas = []
    orquestracao.conduzir(
        diretorio_evidencia=tmp_path / "evidencia",
        competencia_solicitada=COMP,
        caminho_contrato=sem_ancora,
        executar_leitura=lambda contrato: chamadas.append(contrato),
    )
    assert chamadas == []  # Bronze nunca é invocado

    # contrato que o carregador aceita mas não declara o que Bronze exige
    raiz = _lago(spark, tmp_path)
    sem_particionamento = dataclasses.replace(_contrato(), particionamento=None)
    assert _ler(spark, raiz, sem_particionamento).estado == bronze.NAO_MEDIDO
    sem_limites = dataclasses.replace(_contrato(), politica_decimal=_politica(emax=None, emin=None))
    assert _ler(spark, raiz, sem_limites).estado == bronze.NAO_MEDIDO


# ---------------------------------------------------------------- eval_3


def test_centavo_a_mais_diverge_na_soma(spark, tmp_path):
    raiz = _lago(
        spark,
        tmp_path,
        [("01", "A", Decimal("10.00")), ("02", "B", Decimal("20.51")), ("01", "A", Decimal("30.25"))],
    )
    r = _ler(spark, raiz)
    assert r.estado == bronze.DIVERGE
    assert r.controles_divergentes == ("sum_vl_liquido",)  # igualdade exata, sem tolerância
    assert r.controles["sum_vl_liquido"] == Decimal("60.76")


def test_maximo_acima_do_ancorado(spark, tmp_path):
    raiz = _lago(
        spark,
        tmp_path,
        [("01", "A", Decimal("10.00")), ("02", "B", Decimal("15.00")), ("01", "A", Decimal("35.75"))],
    )
    r = _ler(spark, raiz)
    assert r.estado == bronze.DIVERGE
    assert "max_vl_liquido" in r.controles_divergentes
    assert r.controles["count_linhas"] == 3 and r.controles["sum_vl_liquido"] == Decimal("60.75")


def test_recusa_float_na_entrada_pelo_tipo(spark, tmp_path):
    esquema = StructType(
        [
            StructField("especie_codigo", StringType()),
            StructField("especie_descricao", StringType()),
            StructField("vl_liquido", DoubleType()),
        ]
    )
    raiz = tmp_path / "lago"
    _escrever(spark, raiz, COMP, [("01", "A", 1.25)], esquema)
    r = _ler(spark, raiz)
    assert r.estado == bronze.ERRO_LEITURA
    assert "RECUSA_TIPO_MONETARIO" in r.motivo
    assert r.linhas is None and r.controles == {}  # recusado antes de ler valor algum


def test_classificacao_das_seis(spark, tmp_path):
    assert set(bronze.CLASSIFICACOES) == {
        "CONFIRMED_SOURCE_DEFECT",
        "CONFIRMED_LEGACY_DEFECT",
        "APPROVED_BEHAVIOR_CHANGE",
        "MODERN_DEFECT",
        "CONTRACT_AMBIGUITY",
        "UNRESOLVED",
    }
    for c in bronze.CLASSIFICACOES:
        assert bronze.classificar("x", (c,)) == c
    # sem classificação única e válida: UNRESOLVED, que bloqueia — nunca em branco
    assert bronze.classificar("x") == "UNRESOLVED"
    assert bronze.classificar("x", ("MODERN_DEFECT", "UNRESOLVED")) == "UNRESOLVED"
    assert bronze.classificar("x", ("inventada",)) == "UNRESOLVED"
    assert bronze.bloqueia("UNRESOLVED")

    raiz = _lago(spark, tmp_path)
    r = _ler(spark, raiz, _contrato(count_linhas=4, sum_vl_liquido=Decimal("1.00")))
    assert r.diferencas
    assert all(d["classificacao"] in bronze.CLASSIFICACOES for d in r.diferencas)


def test_recusa_valor_negativo(spark, tmp_path):
    raiz = _lago(
        spark,
        tmp_path,
        [("01", "A", Decimal("10.00")), ("02", "B", Decimal("-20.50")), ("01", "A", Decimal("30.25"))],
    )
    r = _ler(spark, raiz)
    assert r.estado == bronze.DIVERGE
    assert r.controles["linhas_invalidas"] == 1
    assert r.controles["sum_vl_liquido"] == Decimal("40.25")  # o negativo não entra no acumulador
    assert [d["defeito"] for d in r.defeitos] == ["VALOR_NEGATIVO"]
    assert r.linhas is None


def test_recusa_valor_fora_da_escala(spark, tmp_path):
    esquema = StructType(
        [
            StructField("especie_codigo", StringType()),
            StructField("especie_descricao", StringType()),
            StructField("vl_liquido", DecimalType(14, 4)),
        ]
    )
    raiz = tmp_path / "lago"
    _escrever(spark, raiz, COMP, [("01", "A", Decimal("1.2345")), ("01", "A", Decimal("2.5000"))], esquema)
    r = _ler(spark, raiz)
    assert r.estado == bronze.DIVERGE
    assert r.controles["linhas_invalidas"] == 1
    assert [d["defeito"] for d in r.defeitos] == ["VALOR_FORA_DA_ESCALA"]
    assert r.defeitos[0]["valor_original"] == "1.2345"


def test_recusa_hash_divergente(spark, tmp_path):
    raiz = _lago(spark, tmp_path)
    r = _ler(spark, raiz, procedencia={"hash_csv_sha256": "c" * 64})
    assert r.estado == bronze.DIVERGE
    assert "hash_csv_sha256" in _nomes_das_diferencas(r)
    assert r.controles_divergentes == ()  # os controles batem; o arquivo é outro
    assert r.linhas is None


def test_emite_marca_sem_vinculo(spark, tmp_path):
    raiz = _lago(spark, tmp_path)
    r = _ler(spark, raiz)
    assert r.estado == bronze.INTEGRO
    assert bronze.PROCEDENCIA_NAO_VINCULADA in r.marcas
    assert r.hash_procedencia is None

    gravado = _ler_e_gravar(spark, tmp_path, _contrato(), COMP, raiz, "exec-m")
    assert bronze.PROCEDENCIA_NAO_VINCULADA in gravado.marcas
    _, dono, _ = bronze.ler_competencia_publicada(spark, str(tmp_path / "dest"), COMP)
    assert bronze.PROCEDENCIA_NAO_VINCULADA in dono["marcas"]


# ---------------------------------------------------------------- procedência lida do lago

import hashlib  # noqa: E402

CONTROLES_BOAS = {
    "count_linhas": "3",
    "linhas_invalidas": "0",
    "sum_vl_liquido": "60.75",
    "min_vl_liquido": "10.00",
    "max_vl_liquido": "30.25",
}


def _manifesto_do_disco(particao: Path) -> list:
    itens = []
    for p in sorted(particao.rglob("*")):
        if p.is_file() and not p.name.startswith(".") and p.name not in ("_SUCCESS", "_PROCEDENCIA.json"):
            dados = p.read_bytes()
            itens.append(
                {
                    "nome": str(p.relative_to(particao)),
                    "tamanho": len(dados),
                    "sha256": hashlib.sha256(dados).hexdigest(),
                }
            )
    return itens


def _vincular(raiz: Path, **troca) -> dict:
    particao = raiz / f"competencia={COMP}"
    prova = {
        "competencia": COMP,
        "csv_nome": "teste.csv",
        "csv_sha256": HASH_CSV,
        "manifesto": _manifesto_do_disco(particao),
        "controles": dict(CONTROLES_BOAS),
    }
    prova.update(troca)
    (particao / "_PROCEDENCIA.json").write_text(json.dumps(prova), encoding="utf-8")
    return prova


def test_procedencia_confere_tira_a_marca(spark, tmp_path):
    raiz = _lago(spark, tmp_path)
    _vincular(raiz)
    r = _ler(spark, raiz)
    assert r.estado == bronze.INTEGRO
    assert bronze.PROCEDENCIA_NAO_VINCULADA not in r.marcas
    assert r.hash_procedencia == HASH_CSV
    gravado = _ler_e_gravar(spark, tmp_path, _contrato(), COMP, raiz, "exec-p")
    assert gravado.gravacao is not None
    _, dono, _ = bronze.ler_competencia_publicada(spark, str(tmp_path / "dest"), COMP)
    assert dono["hash_procedencia"] == HASH_CSV
    assert bronze.PROCEDENCIA_NAO_VINCULADA not in dono["marcas"]


def test_manifesto_confere_objetos_listados(spark, tmp_path):
    raiz = _lago(spark, tmp_path)
    prova = _vincular(raiz)
    assert prova["manifesto"]
    (raiz / f"competencia={COMP}" / "_SUCCESS").touch()  # auxiliar nomeado no contrato
    r = _ler(spark, raiz)
    assert r.estado == bronze.INTEGRO
    assert r.diferencas == ()


def test_controles_da_procedencia_conferidos(spark, tmp_path):
    raiz = _lago(spark, tmp_path)
    _vincular(raiz, controles={**CONTROLES_BOAS, "sum_vl_liquido": "60.76"})
    r = _ler(spark, raiz)
    assert r.estado == bronze.DIVERGE
    assert "controle_da_prova:sum_vl_liquido" in _nomes_das_diferencas(r)
    assert r.linhas is None


def test_competencia_da_prova_conferida(spark, tmp_path):
    raiz = _lago(spark, tmp_path)
    _vincular(raiz, competencia="2025-12")
    r = _ler(spark, raiz)
    assert r.estado == bronze.DIVERGE
    assert "competencia" in _nomes_das_diferencas(r)


def test_sem_procedencia_mantem_a_marca(spark, tmp_path):
    raiz = _lago(spark, tmp_path)
    r = _ler(spark, raiz)
    assert r.estado == bronze.INTEGRO
    assert bronze.PROCEDENCIA_NAO_VINCULADA in r.marcas
    assert r.hash_procedencia is None


def test_procedencia_json_invalido_e_erro(spark, tmp_path):
    raiz = _lago(spark, tmp_path)
    (raiz / f"competencia={COMP}" / "_PROCEDENCIA.json").write_text("{nao e json", encoding="utf-8")
    r = _ler(spark, raiz)
    assert r.estado == bronze.ERRO_LEITURA
    assert "PROCEDENCIA_JSON_INVALIDO" in r.motivo
    assert r.linhas is None


def test_objeto_a_mais_diverge(spark, tmp_path):
    raiz = _lago(spark, tmp_path)
    _vincular(raiz)
    particao = raiz / f"competencia={COMP}"
    origem = next(p for p in particao.glob("*.parquet"))
    (particao / "part-extra.parquet").write_bytes(origem.read_bytes())
    r = _ler(spark, raiz)
    assert r.estado == bronze.DIVERGE
    assert "manifesto:part-extra.parquet" in _nomes_das_diferencas(r)
    assert r.linhas is None


def test_hash_da_procedencia_diverge(spark, tmp_path):
    raiz = _lago(spark, tmp_path)
    _vincular(raiz, csv_sha256="c" * 64)
    r = _ler(spark, raiz)
    assert r.estado == bronze.DIVERGE
    assert "hash_csv_sha256" in _nomes_das_diferencas(r)
    assert r.linhas is None


def test_objeto_com_underscore_a_mais_diverge(spark, tmp_path):
    raiz = _lago(spark, tmp_path)
    _vincular(raiz)
    particao = raiz / f"competencia={COMP}"
    origem = next(p for p in particao.glob("*.parquet"))
    (particao / "_extra.parquet").write_bytes(origem.read_bytes())
    r = _ler(spark, raiz)
    assert r.estado == bronze.DIVERGE
    assert "manifesto:_extra.parquet" in _nomes_das_diferencas(r)
