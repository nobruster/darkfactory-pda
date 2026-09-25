"""Gold por assuntos: fat_especie e kpis_nacionais, lidas SÓ da Silver nomeada pela Gold principal.

Estados distintos, os mesmos das outras camadas: INTEGRO, DIVERGE, NAO_MEDIDO, ERRO_LEITURA.
Sem Gold principal publicada ou sem grupos_especie no contrato, o estado é NAO_MEDIDO. Código
fora do mapa ou soma que não fecha é DIVERGE, com a diferença nomeada. Em nenhum dos casos
publica — e a igualdade é EXATA: tolerância aqui seria afrouxar o oráculo.

A Silver lida é a versão que o commit da Gold principal nomeia (`versao_silver`), com
versionAsOf — nunca a mais recente. Os valores vindos da âncora são conferidos em Decimal.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType, StringType

from medalhao import bronze, silver

INTEGRO = bronze.INTEGRO
DIVERGE = bronze.DIVERGE
NAO_MEDIDO = bronze.NAO_MEDIDO
ERRO_LEITURA = bronze.ERRO_LEITURA

FAT_PADRAO = "s3a://gold/pda/assuntos/fat_especie"
KPIS_PADRAO = "s3a://gold/pda/assuntos/kpis_nacionais"
PREPARO_PADRAO = "s3a://gold/_preparo/pda/assuntos"
GOLD_PRINCIPAL_PADRAO = "s3a://gold/pda/beneficios-emitidos"
SILVER_PADRAO = "s3a://silver/pda/beneficios-emitidos"

# Precisão do percentil declarada: erro relativo de rank 1/PRECISAO_PERCENTIL. Vai no commit.
PRECISAO_PERCENTIL = 10000
ESCALA_PERCENTUAL = 4

FAT_COLUNAS = (
    "especie_codigo", "especie_descricao", "grupo_especie", "competencia",
    "qtd_beneficios", "vl_total", "vl_minimo", "vl_maximo", "qtd_vl_zero", "vl_medio",
    "vl_mediano_aprox", "vl_p90_aprox", "rank_no_grupo", "pct_qtd_nacional", "pct_vl_nacional",
    "nome_oficial",
)
KPIS_COLUNAS = (
    "competencia", "total_beneficios", "vl_total", "vl_medio", "vl_minimo", "vl_maximo",
    "total_especies_ativas", "qtd_vl_zero", "vl_mediano_aprox", "vl_p90_aprox",
)
MONETARIAS_FAT = ("vl_total", "vl_minimo", "vl_maximo", "vl_medio", "vl_mediano_aprox", "vl_p90_aprox")
MONETARIAS_KPIS = MONETARIAS_FAT

_diferenca = bronze._diferenca
_historico = bronze._historico
_ler_versao = bronze._ler_versao
_delta_table = bronze._delta_table
_versao_atual = bronze._versao_atual


@dataclass(frozen=True)
class GoldAssuntos:
    """A capacidade 'gold por assuntos'."""

    estado: str
    competencia: str
    motivo: str = ""
    diferencas: Tuple[dict, ...] = ()
    controles: Dict[str, Any] = field(default_factory=dict)
    fat_especie: Optional[DataFrame] = None
    kpis_nacionais: Optional[DataFrame] = None
    versao_silver: Optional[int] = None
    versao_gold_principal: Optional[int] = None
    silver_especie: Optional[dict] = None  # {caminho, versao} da Silver especie que deu o nome; None = sem nome
    gravacao: Optional[dict] = None


# ---------------------------------------------------------------- agregação


def _tipo(politica) -> DecimalType:
    return bronze.tipo_acumulador(politica)


def _mapa_de_grupos(spark: SparkSession, grupos_especie) -> DataFrame:
    """Códigos TEXTO do contrato: '01' não é 1."""
    pares = [(c, g.grupo) for g in grupos_especie.grupos for c in g.codigos]
    return spark.createDataFrame(pares, "especie_codigo string, grupo_especie string")


def _dividir(numerador, denominador, escala: int):
    """Divisão em escala alta e UM arredondamento meio-para-par (bround) no fim."""
    alto = F.col(numerador).cast(DecimalType(38, 18)) / F.col(denominador).cast(DecimalType(20, 0))
    return F.bround(alto, escala)


def montar_fat_especie(
    linhas: DataFrame, grupos: DataFrame, competencia: str, politica, nomes: Optional[DataFrame] = None
) -> DataFrame:
    """Um ÚNICO groupBy por especie_codigo; grão (especie_codigo, competencia).

    O nome oficial entra num left join DEPOIS de tudo montado — antes, multiplicaria linhas e
    mexeria nos controles. Sem `nomes`, a coluna existe e é nula em toda linha.
    """
    acc = _tipo(politica)
    vl = F.col("vl_liquido").cast(acc)
    base = (
        linhas.groupBy("especie_codigo")
        .agg(
            F.min("especie_descricao").alias("especie_descricao"),
            F.count(F.lit(1)).alias("qtd_beneficios"),
            F.sum(vl).cast(acc).alias("vl_total"),
            F.min(vl).cast(acc).alias("vl_minimo"),
            F.max(vl).cast(acc).alias("vl_maximo"),
            F.sum(F.when(vl == 0, 1).otherwise(0)).cast("long").alias("qtd_vl_zero"),
            F.percentile_approx(vl, 0.5, PRECISAO_PERCENTIL).cast(acc).alias("vl_mediano_aprox"),
            F.percentile_approx(vl, 0.9, PRECISAO_PERCENTIL).cast(acc).alias("vl_p90_aprox"),
        )
        .withColumn("vl_medio", _dividir("vl_total", "qtd_beneficios", politica.escala).cast(acc))
        .join(grupos, "especie_codigo", "left")
        .withColumn("competencia", F.lit(competencia))
    )
    nacional = Window.partitionBy("competencia")
    no_grupo = Window.partitionBy("competencia", "grupo_especie").orderBy(
        F.col("vl_total").desc(), F.col("especie_codigo")
    )
    total_qtd = F.sum("qtd_beneficios").over(nacional)
    total_vl = F.sum("vl_total").over(nacional)
    pct = DecimalType(9, ESCALA_PERCENTUAL)
    fat = (
        base.withColumn("rank_no_grupo", F.row_number().over(no_grupo).cast("int"))
        .withColumn(
            "pct_qtd_nacional",
            F.when(total_qtd == 0, F.lit(0))
            .otherwise(F.bround(F.col("qtd_beneficios").cast(DecimalType(38, 18)) * 100 / total_qtd, ESCALA_PERCENTUAL))
            .cast(pct),
        )
        .withColumn(
            "pct_vl_nacional",
            F.when(total_vl == 0, F.lit(0))
            .otherwise(F.bround(F.col("vl_total").cast(DecimalType(38, 18)) * 100 / total_vl, ESCALA_PERCENTUAL))
            .cast(pct),
        )
    )
    if nomes is None:
        fat = fat.withColumn("nome_oficial", F.lit(None).cast(StringType()))
    else:
        fat = fat.join(nomes.select("especie_codigo", "nome_oficial"), "especie_codigo", "left")
    return fat.select(*FAT_COLUNAS)


def montar_kpis_nacionais(fat: DataFrame, linhas: DataFrame, competencia: str, politica) -> DataFrame:
    """Uma linha por competência, a partir de fat_especie. O médio é bround(vl_total / total), nunca a média das médias.

    Só os percentis nacionais exigem outra passada — sobre as linhas da Silver.
    """
    acc = _tipo(politica)
    vl = F.col("vl_liquido").cast(acc)
    soma = fat.agg(
        F.sum("qtd_beneficios").cast("long").alias("total_beneficios"),
        F.sum("vl_total").cast(acc).alias("vl_total"),
        F.min("vl_minimo").cast(acc).alias("vl_minimo"),
        F.max("vl_maximo").cast(acc).alias("vl_maximo"),
        F.count(F.when(F.col("qtd_beneficios") > 0, 1)).cast("long").alias("total_especies_ativas"),
        F.sum("qtd_vl_zero").cast("long").alias("qtd_vl_zero"),
    )
    percentis = linhas.agg(
        F.percentile_approx(vl, 0.5, PRECISAO_PERCENTIL).cast(acc).alias("vl_mediano_aprox"),
        F.percentile_approx(vl, 0.9, PRECISAO_PERCENTIL).cast(acc).alias("vl_p90_aprox"),
    )
    return (
        soma.crossJoin(percentis)
        .withColumn("vl_medio", _dividir("vl_total", "total_beneficios", politica.escala).cast(acc))
        .withColumn("competencia", F.lit(competencia))
        .select(*KPIS_COLUNAS)
    )


# ---------------------------------------------------------------- fechamento EXATO


def conferir_fechamento(fat: DataFrame, kpis: DataFrame, contrato) -> List[dict]:
    """Os CINCO controles contra a âncora, kpis com os mesmos totais, códigos e grupos. Igualdade exata."""
    anc = contrato.ancora
    dif: List[dict] = []
    linhas = fat.select("especie_codigo", "grupo_especie", "qtd_beneficios", "vl_total", "vl_minimo", "vl_maximo").collect()
    for r in sorted(linhas, key=lambda x: x["especie_codigo"]):
        if r["grupo_especie"] is None:
            dif.append(_diferenca("mapa", f"codigo_fora_do_mapa:{r['especie_codigo']}", "código em um grupo", None))
    qtd = sum(int(r["qtd_beneficios"]) for r in linhas)
    total = sum((Decimal(r["vl_total"]) for r in linhas), Decimal(0))
    menor = min((Decimal(r["vl_minimo"]) for r in linhas), default=None)
    maior = max((Decimal(r["vl_maximo"]) for r in linhas), default=None)
    if qtd != anc.count_linhas:
        dif.append(_diferenca("ancora", "count_linhas", anc.count_linhas, qtd))
    if total != anc.sum_vl_liquido:
        dif.append(_diferenca("ancora", "sum_vl_liquido", anc.sum_vl_liquido, total))
    if menor != anc.min_vl_liquido:
        dif.append(_diferenca("ancora", "min_vl_liquido", anc.min_vl_liquido, menor))
    if maior != anc.max_vl_liquido:
        dif.append(_diferenca("ancora", "max_vl_liquido", anc.max_vl_liquido, maior))
    if anc.linhas_invalidas != 0:
        dif.append(_diferenca("ancora", "linhas_invalidas", 0, anc.linhas_invalidas))
    codigos = contrato.cardinalidade.codigos_distintos
    if len(linhas) != codigos:
        dif.append(_diferenca("cardinalidade", "codigos_distintos", codigos, len(linhas)))
    k = kpis.collect()
    if len(k) != 1:
        dif.append(_diferenca("grao", "kpis_uma_linha", 1, len(k)))
    else:
        k = k[0]
        if int(k["total_beneficios"]) != qtd:
            dif.append(_diferenca("kpis", "total_beneficios", qtd, k["total_beneficios"]))
        if Decimal(k["vl_total"]) != total:
            dif.append(_diferenca("kpis", "vl_total", total, k["vl_total"]))
        if k["vl_minimo"] != menor or k["vl_maximo"] != maior:
            dif.append(_diferenca("kpis", "extremos", (menor, maior), (k["vl_minimo"], k["vl_maximo"])))
    return dif


# ---------------------------------------------------------------- leitura por versão


def _dono_ate(spark: SparkSession, destino: str, competencia: str, versao: int) -> Optional[dict]:
    """Metadados do ÚLTIMO commit até `versao` que nomeia a competência."""
    for v, meta in sorted(_historico(spark, destino), key=lambda t: t[0], reverse=True):
        if v > versao or not meta:
            continue
        try:
            corpo = json.loads(meta)
        except ValueError:
            continue
        if isinstance(corpo, dict) and corpo.get("competencia") == competencia:
            return corpo
    return None


def _e_delta(spark: SparkSession, caminho: str) -> bool:
    from delta.tables import DeltaTable

    try:
        return DeltaTable.isDeltaTable(spark, caminho)
    except Exception:  # noqa: BLE001 — caminho ilegível é o mesmo que ausente para esta pergunta
        return False


def _gold_principal(spark: SparkSession, destino: str, competencia: str):
    """(versão, dono) da Gold principal publicada da competência, ou (None, motivo)."""
    if not _e_delta(spark, destino):
        return None, "SEM_GOLD_PRINCIPAL_PUBLICADA"
    historico = _historico(spark, destino)
    versao = max(v for v, _ in historico)
    dono = _dono_ate(spark, destino, competencia, versao)
    if dono is None or dono.get("estado") != INTEGRO:
        return None, "SEM_GOLD_PRINCIPAL_PUBLICADA"
    if dono.get("versao_silver") is None:
        return None, "GOLD_PRINCIPAL_SEM_VERSAO_DA_SILVER"
    return (versao, dono), ""


def _ler_silver_nomeada(spark: SparkSession, destino: str, competencia: str, versao: int):
    """Linhas da Silver NA versão nomeada (versionAsOf) e o estado do commit dono dela."""
    dono = _dono_ate(spark, destino, competencia, versao)
    if dono is None:
        return None, NAO_MEDIDO, "SILVER_SEM_METADADOS_DA_COMPETENCIA"
    estado = dono.get("estado") or NAO_MEDIDO
    if estado != INTEGRO:
        return None, estado, f"SILVER_{estado}"
    dados = _ler_versao(spark, destino, versao).where(F.col("competencia") == competencia)
    return dados.select(*silver.SILVER_COLUNAS), INTEGRO, ""


# ---------------------------------------------------------------- Delta


def _garantir_tabela(spark: SparkSession, caminho: str, schema, chaves: Tuple[str, ...], monetarias: Tuple[str, ...]):
    """Tabela com o DecimalType do contrato, NOT NULL nas chaves e CHECK >= 0 em cada coluna monetária."""
    from delta.tables import DeltaTable

    construtor = DeltaTable.createIfNotExists(spark).location(caminho)
    for campo in schema:
        construtor = construtor.addColumn(campo.name, campo.dataType, nullable=campo.name not in chaves)
    for coluna in monetarias:  # os CHECK nascem NO CREATE: um commit em vez de um por coluna
        construtor = construtor.property(f"delta.constraints.{coluna}_nao_negativo", f"{coluna} >= 0")
    construtor.partitionedBy("competencia").execute()
    propriedades = _delta_table(spark, caminho).detail().select("properties").first()[0] or {}
    for coluna in monetarias:
        nome = f"{coluna}_nao_negativo"
        if f"delta.constraints.{nome}" not in propriedades:
            spark.sql(f"ALTER TABLE delta.`{caminho}` ADD CONSTRAINT {nome} CHECK ({coluna} >= 0)")


def _conferir_tabela(spark: SparkSession, caminho: str, versao: int, esperado: DataFrame, competencia: str):
    """RELÊ a versão commitada e compara o MULTICONJUNTO de todas as colunas, nos dois sentidos."""
    cols = esperado.columns
    lido = _ler_versao(spark, caminho, versao).where(F.col("competencia") == competencia).select(*cols)
    so_esperado, so_lido = bronze._diferenca_numa_passada(esperado.select(*cols), lido)
    return so_esperado == 0 and so_lido == 0, {"versao": versao, "so_no_esperado": so_esperado, "so_no_lido": so_lido}


def _ler_nomes_da_especie(spark: SparkSession, especie: dict, competencia: str) -> DataFrame:
    """Silver especie NO caminho e NA versão que a Gold principal registrou — nunca um padrão."""
    return (
        _ler_versao(spark, especie["caminho"], int(especie["versao"]))
        .where(F.col("competencia") == competencia)
        .select("especie_codigo", "nome_oficial")
    )


def _metadados(r: GoldAssuntos, tabela: str, id_execucao: str) -> dict:
    if tabela != "fat_especie":
        nome = {}
    elif r.silver_especie:
        nome = {"silver_especie": r.silver_especie}
    else:
        nome = {"nome_oficial": NAO_MEDIDO, "motivo_nome_oficial": "SEM_SILVER_ESPECIE"}
    return {
        **nome,
        "estado": INTEGRO,
        "competencia": r.competencia,
        "tabela": tabela,
        "versao_silver": r.versao_silver,
        "versao_gold_principal": r.versao_gold_principal,
        "controles": {k: str(v) for k, v in r.controles.items()},
        "precisao_percentil": PRECISAO_PERCENTIL,
        "id_execucao": id_execucao,
    }


def _falha(r: GoldAssuntos, estado: str, motivo: str, dif=()) -> GoldAssuntos:
    return replace(r, estado=estado, motivo=motivo, diferencas=r.diferencas + tuple(dif),
                   fat_especie=None, kpis_nacionais=None)


def _publicar_tabela(spark, r, tabela, destino, linhas, chaves, monetarias, id_execucao, evolucao_aditiva):
    """UM commit (overwrite + replaceWhere na competência); reconfere e reverte SÓ a competência se falhar."""
    _garantir_tabela(spark, destino, linhas.schema, chaves, monetarias)
    existia = bronze._competencia_existe(spark, destino, r.competencia)
    anterior = _versao_atual(spark, destino)
    meta = _metadados(r, tabela, id_execucao)
    bronze.publicar_competencia(spark, linhas, destino, r.competencia, meta, evolucao_aditiva=evolucao_aditiva)
    versao = _versao_atual(spark, destino)
    ok, detalhe = _conferir_tabela(spark, destino, versao, linhas, r.competencia)
    if not ok:
        bronze._reverter_competencia(spark, destino, r.competencia, existia, anterior, meta)
        return None, _diferenca("gravacao", f"reconferencia_publicada:{tabela}", "multiconjunto igual",
                                json.dumps(detalhe, default=str)), (existia, anterior, meta)
    return versao, None, (existia, anterior, meta)


# ---------------------------------------------------------------- execução


def executar_gold_assuntos(spark: SparkSession, **kwargs) -> GoldAssuntos:
    """Monta, fecha com a âncora e só então publica — e libera todo cache em QUALQUER caminho."""
    persistidos: List[DataFrame] = []
    try:
        return _executar_gold_assuntos(spark, persistidos, **kwargs)
    finally:
        bronze._liberar(*persistidos)


def _executar_gold_assuntos(
    spark: SparkSession,
    persistidos: List[DataFrame],
    *,
    caminho_contrato,
    silver_destino: str = SILVER_PADRAO,
    gold_principal_destino: str = GOLD_PRINCIPAL_PADRAO,
    fat_destino: str = FAT_PADRAO,
    kpis_destino: str = KPIS_PADRAO,
    preparo_raiz: str = PREPARO_PADRAO,
    id_execucao: Optional[str] = None,
    evolucao_aditiva: bool = False,
) -> GoldAssuntos:
    """Monta, fecha com a âncora e só então publica fat_especie e kpis_nacionais."""
    from pda import contrato as contrato_mod

    contrato = contrato_mod.carregar_contrato(caminho_contrato)
    competencia = contrato.competencia
    if not re.fullmatch(r"[A-Za-z0-9._-]+", competencia or ""):
        return GoldAssuntos(ERRO_LEITURA, str(competencia), motivo="COMPETENCIA_INVALIDA")
    r = GoldAssuntos(INTEGRO, competencia)
    if contrato.grupos_especie is None:
        return _falha(r, NAO_MEDIDO, "SEM_GRUPOS_ESPECIE")
    spark.conf.set("spark.sql.ansi.enabled", "true")

    try:
        achado, motivo = _gold_principal(spark, gold_principal_destino, competencia)
        if achado is None:
            return _falha(r, NAO_MEDIDO, motivo)
        versao_gold, dono = achado
        versao_silver = int(dono["versao_silver"])
        r = replace(r, versao_silver=versao_silver, versao_gold_principal=versao_gold)
        linhas, estado, motivo = _ler_silver_nomeada(spark, silver_destino, competencia, versao_silver)
        if linhas is None:
            return _falha(r, estado, motivo)
        especie = dono.get("silver_especie")
        nomes = None
        if especie:
            especie = {"caminho": especie["caminho"], "versao": int(especie["versao"])}
            r = replace(r, silver_especie=especie)
            nomes = _ler_nomes_da_especie(spark, especie, competencia)
        pol = contrato.politica_decimal
        grupos = _mapa_de_grupos(spark, contrato.grupos_especie)
        id_execucao = id_execucao or uuid.uuid4().hex
        fat = montar_fat_especie(linhas, grupos, competencia, pol, nomes).persist()
        persistidos.append(fat)
        if nomes is not None:
            sem_nome = sorted(
                x[0] for x in fat.where(F.col("nome_oficial").isNull()).select("especie_codigo").collect()
            )
            if sem_nome:
                d = _diferenca("nome_oficial", "NOME_OFICIAL_AUSENTE", "nome na Silver especie", sem_nome)
                return _falha(r, DIVERGE, "DIVERGE", [d])
        kpis = montar_kpis_nacionais(fat, linhas, competencia, pol)
        preparo = f"{preparo_raiz.rstrip('/')}/execucao={id_execucao}"
        destinos = (("fat_especie", f"{preparo}/fat_especie", fat, ("especie_codigo", "competencia"), MONETARIAS_FAT),
                    ("kpis_nacionais", f"{preparo}/kpis_nacionais", kpis, ("competencia",), MONETARIAS_KPIS))
        relidos = {}
        for tabela, caminho, df, chaves, monetarias in destinos:
            _garantir_tabela(spark, caminho, df.schema, chaves, monetarias)
            bronze.publicar_competencia(spark, df, caminho, competencia, {"competencia": competencia, "estado": "PREPARO"})
            versao = _versao_atual(spark, caminho)
            ok, detalhe = _conferir_tabela(spark, caminho, versao, df, competencia)
            if not ok:
                d = _diferenca("gravacao", f"reconferencia_no_preparo:{tabela}", "multiconjunto igual",
                               json.dumps(detalhe, default=str))
                return _falha(r, DIVERGE, "DIVERGE", [d])
            relidos[tabela] = _ler_versao(spark, caminho, versao).where(F.col("competencia") == competencia).select(*df.columns)
        dif = conferir_fechamento(relidos["fat_especie"], relidos["kpis_nacionais"], contrato)
    except Exception as exc:  # noqa: BLE001 — não conseguiu medir: não é NAO_MEDIDO
        return _falha(r, ERRO_LEITURA, f"{type(exc).__name__}: {exc}")
    if dif:
        return _falha(r, DIVERGE, "DIVERGE", dif)

    anc = contrato.ancora
    r = replace(r, controles={
        "count_linhas": anc.count_linhas, "sum_vl_liquido": anc.sum_vl_liquido,
        "min_vl_liquido": anc.min_vl_liquido, "max_vl_liquido": anc.max_vl_liquido, "linhas_invalidas": 0,
    })
    v_fat, d_fat, undo_fat = _publicar_tabela(
        spark, r, "fat_especie", fat_destino, relidos["fat_especie"], ("especie_codigo", "competencia"),
        MONETARIAS_FAT, id_execucao, evolucao_aditiva,
    )
    if d_fat is not None:
        return _falha(r, DIVERGE, "DIVERGE", [d_fat])
    v_kpis, d_kpis, _ = _publicar_tabela(
        spark, r, "kpis_nacionais", kpis_destino, relidos["kpis_nacionais"], ("competencia",),
        MONETARIAS_KPIS, id_execucao, evolucao_aditiva,
    )
    if d_kpis is not None:
        existia, anterior, meta = undo_fat
        bronze._reverter_competencia(spark, fat_destino, competencia, existia, anterior, meta)
        return _falha(r, DIVERGE, "DIVERGE", [d_kpis])
    return replace(
        r, fat_especie=relidos["fat_especie"], kpis_nacionais=relidos["kpis_nacionais"],
        gravacao={"fat_especie": {"destino": fat_destino, "versao": v_fat},
                  "kpis_nacionais": {"destino": kpis_destino, "versao": v_kpis},
                  "id_execucao": id_execucao},
    )
