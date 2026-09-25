"""Gold: agrega por CÓDIGO, reconcilia com a âncora e só então publica em Delta.

Cinco estados, distintos: INTEGRO, DIVERGE, BLOQUEADO, NAO_MEDIDO, ERRO_LEITURA.
Gold só agrega sobre 'silver classificado' INTEGRO; qualquer outro estado PARA a
cadeia aqui e é propagado VERBATIM, sem tradução.

Arredondamento: UMA vez, sobre o total, HALF_EVEN, no contexto CONSTRUÍDO DO
ZERO a partir da politica_decimal do contrato (prec, rounding, traps=[], Emax,
Emin) — nunca herdado do global, que é mutável.

Reconciliação: soma das linhas de Gold == âncora ao centavo, e o MAPA
total_por_codigo == mapa da camada anterior, código a código, em soma exata
não quantizada. Recalculada sobre as linhas CANDIDATAS (preparo privado), nunca
herdada de Bronze. Gold que não reconcilia devolve DIVERGE e NÃO publica.

A publicação é um passo POSTERIOR, condicionado a Desfecho.autorizado_publicar,
ao pacote em disco e ao anexo de cobertura conferido contra o sha256 do pacote:
um único commit Delta (overwrite + replaceWhere na competência).
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field, replace
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType

from medalhao import bronze, silver
from pda import envelope as envelope_mod
from pda import evidencia, juizo, leitura, orquestracao

INTEGRO = bronze.INTEGRO
DIVERGE = bronze.DIVERGE
NAO_MEDIDO = bronze.NAO_MEDIDO
ERRO_LEITURA = bronze.ERRO_LEITURA
BLOQUEADO = silver.BLOQUEADO
PROCEDENCIA_NAO_VINCULADA = bronze.PROCEDENCIA_NAO_VINCULADA

GOLD_COLUNAS = ("especie_codigo", "especie_descricao", "vl_liquido_total", "competencia", "nome_oficial")
MOTOR = "spark-delta"

DESTINO_PADRAO = "s3a://gold/pda/beneficios-emitidos"
PREPARO_PADRAO = "s3a://gold/_preparo/pda/beneficios-emitidos"

EvolucaoRecusada = bronze.EvolucaoRecusada
contexto_declarado = bronze.contexto_declarado
tipo_acumulador = bronze.tipo_acumulador
classificar = bronze.classificar
bloqueia = bronze.bloqueia
criar_sessao = bronze.criar_sessao
verificar_evolucao = bronze.verificar_evolucao
ler_competencia_publicada = bronze.ler_competencia_publicada
_delta_table = bronze._delta_table
_versao_atual = bronze._versao_atual
_historico = bronze._historico
_ler_versao = bronze._ler_versao
_diferenca = bronze._diferenca


def publicar_competencia(
    spark: SparkSession,
    linhas: DataFrame,
    destino: str,
    competencia: str,
    metadados: dict,
    evolucao_aditiva: bool = False,
) -> None:
    """Como a da Bronze, mas a Gold de 4 colunas é publicada na tabela de 5: só `nome_oficial` ausente vira nulo.

    Qualquer outra coluna removida, e toda troca de tipo, segue recusada por `verificar_evolucao`.
    """
    alvo = spark.read.format("delta").load(destino).schema
    if "nome_oficial" in alvo.names and "nome_oficial" not in linhas.columns:
        linhas = linhas.withColumn("nome_oficial", F.lit(None).cast(alvo["nome_oficial"].dataType))
    bronze.publicar_competencia(spark, linhas, destino, competencia, metadados, evolucao_aditiva=evolucao_aditiva)


@dataclass(frozen=True)
class GoldReconciliado:
    """A capacidade 'gold reconciliado' — com forma e colunas nomeadas."""

    estado: str
    competencia: str
    controles: Dict[str, Any] = field(default_factory=dict)
    total_por_codigo: Dict[str, Decimal] = field(default_factory=dict)
    marcas: Tuple[str, ...] = ()
    hash_procedencia: Optional[str] = None
    linhas: Optional[DataFrame] = None
    defeitos: Tuple[dict, ...] = ()
    diferencas: Tuple[dict, ...] = ()
    cobertura: Optional[dict] = None
    reconciliacao: Optional[str] = None
    motivo: str = ""
    versao_silver: Optional[int] = None
    gravacao: Optional[dict] = None
    cache: Optional[DataFrame] = None  # o persistido das candidatas; quem publica (ou encerra) libera
    silver_especie: Optional[dict] = None  # {caminho, versao} da Silver especie que deu o nome; None = sem nome


class CadeiaParou(Exception):
    """Uma camada parou a cadeia. A MENSAGEM é o diagnóstico estruturado em JSON."""


# ---------------------------------------------------------------- aritmética


def total_arredondado(valores, politica) -> Decimal:
    """Soma EXATA e arredonda UMA vez, sobre o total, no contexto declarado do zero."""
    with localcontext(contexto_declarado(politica)):
        return _soma_exata(valores, politica).quantize(Decimal(1).scaleb(-politica.escala))


def _exato(valor) -> Decimal:
    if isinstance(valor, (float, bool)):
        raise TypeError("dinheiro é Decimal ou string, nunca float (Regra 5)")
    return Decimal(valor)


def _soma_exata(valores, politica) -> Decimal:
    """Soma EXATA, não quantizada, no contexto declarado do zero."""
    with localcontext(contexto_declarado(politica)):
        total = Decimal(0)
        for v in valores:
            total = total + _exato(v)
        return total


# ---------------------------------------------------------------- agregação


def _agregar(linhas_silver: DataFrame, competencia: str, politica, nomes: Optional[DataFrame] = None) -> DataFrame:
    """Uma linha por código, NO MOTOR. O acumulador é o DecimalType declarado.

    O nome oficial entra num left join DEPOIS do groupBy — antes, multiplicaria linhas.
    Sem `nomes`, a coluna existe e é nula em toda linha.
    """
    acc = tipo_acumulador(politica)
    agregado = (
        linhas_silver.groupBy("especie_codigo")
        .agg(
            F.min("especie_descricao").alias("especie_descricao"),
            F.sum(F.col("vl_liquido").cast(acc)).cast(acc).alias("vl_liquido_total"),
        )
        .withColumn("competencia", F.lit(competencia))
    )
    if nomes is None:
        agregado = agregado.withColumn("nome_oficial", F.lit(None).cast(StringType()))
    else:
        agregado = agregado.join(nomes, "especie_codigo", "left")
    return agregado.select(*GOLD_COLUNAS)


def _ler_nomes_da_especie(spark: SparkSession, especie_destino: str, competencia: str):
    """Silver especie lida numa versão V fixada UMA vez: (nomes, V)."""
    versao = _versao_atual(spark, especie_destino)
    nomes = (
        _ler_versao(spark, especie_destino, versao)
        .where(F.col("competencia") == competencia)
        .select("especie_codigo", "nome_oficial")
    )
    return nomes, versao


def _mapa_e_soma(candidatas: DataFrame, politica) -> Tuple[Dict[str, Decimal], Decimal, int, List[str]]:
    """Só as linhas agregadas saem do motor (uma por código, ≤ 65)."""
    linhas = candidatas.select("especie_codigo", "vl_liquido_total").collect()
    codigos = [r[0] for r in linhas]
    mapa: Dict[str, Decimal] = {}
    for codigo, valor in ((r[0], r[1]) for r in linhas):
        mapa[codigo] = mapa[codigo] + valor if codigo in mapa else valor
    duplicados = sorted({c for c in codigos if codigos.count(c) > 1})
    soma = total_arredondado(mapa.values(), politica)
    return mapa, soma, len(linhas), duplicados


def _reconciliar(
    candidatas: DataFrame, contrato, silver_entrada, competencia: str
) -> Tuple[List[dict], Dict[str, Decimal], Decimal]:
    """RECALCULA a partir das linhas candidatas — nunca herda a conta de outra camada."""
    pol = contrato.politica_decimal
    mapa, soma, n_linhas, duplicados = _mapa_e_soma(candidatas, pol)
    dif: List[dict] = []
    for codigo in duplicados:
        dif.append(_diferenca("grao", f"codigo_duplicado:{codigo}", "uma linha por código", "várias"))
    if soma != contrato.ancora.sum_vl_liquido:
        dif.append(_diferenca("ancora", "soma_das_linhas", contrato.ancora.sum_vl_liquido, soma))
    if n_linhas != contrato.cardinalidade.codigos_distintos or len(mapa) != contrato.cardinalidade.codigos_distintos:
        dif.append(
            _diferenca("cardinalidade", "codigos_distintos", contrato.cardinalidade.codigos_distintos, n_linhas)
        )
    anterior = silver_entrada.total_por_codigo
    for codigo in sorted(set(mapa) | set(anterior)):
        if mapa.get(codigo) != anterior.get(codigo):
            dif.append(_diferenca("mapa", f"total_por_codigo:{codigo}", anterior.get(codigo), mapa.get(codigo)))
    # A descrição publicada de cada código é a ORIGINAL que Silver entregou.
    originais = {
        r[0]: r[1]
        for r in silver_entrada.linhas.select("especie_codigo", "especie_descricao").distinct().collect()
    }
    publicadas = {r[0]: r[1] for r in candidatas.select("especie_codigo", "especie_descricao").collect()}
    for codigo in sorted(set(originais) | set(publicadas)):
        if originais.get(codigo) != publicadas.get(codigo):
            dif.append(
                _diferenca(
                    "descricao", f"descricao_publicada:{codigo}", originais.get(codigo), publicadas.get(codigo)
                )
            )
    return dif, mapa, soma


# ---------------------------------------------------------------- Delta


def _garantir_tabela(spark: SparkSession, caminho: str, politica) -> None:
    """Tabela com o DecimalType do contrato, NOT NULL nas chaves e CHECK >= 0 no TOTAL agregado."""
    from delta.tables import DeltaTable

    (
        DeltaTable.createIfNotExists(spark)
        .location(caminho)
        .addColumn("especie_codigo", StringType(), nullable=False)
        .addColumn("especie_descricao", StringType())
        .addColumn("vl_liquido_total", tipo_acumulador(politica))
        .addColumn("competencia", StringType(), nullable=False)
        .addColumn("nome_oficial", StringType())
        .partitionedBy("competencia")
        .execute()
    )
    propriedades = _delta_table(spark, caminho).detail().select("properties").first()[0] or {}
    if "delta.constraints.vl_total_nao_negativo" not in propriedades:
        spark.sql(
            f"ALTER TABLE delta.`{caminho}` ADD CONSTRAINT vl_total_nao_negativo CHECK (vl_liquido_total >= 0)"
        )


def _gravar_preparo(spark: SparkSession, linhas: DataFrame, preparo: str, competencia: str, metadados: dict):
    bronze.publicar_competencia(spark, linhas, preparo, competencia, metadados)  # preparo é privado: fora do seam do destino


def _conferir_tabela(
    spark: SparkSession, caminho: str, versao: int, esperado: DataFrame, controles: Dict[str, Any],
    competencia: str, politica, com_nome: bool = False,
) -> Tuple[bool, dict]:
    """RELÊ a versão commitada e compara o MULTICONJUNTO de TODAS as colunas, nos dois sentidos.

    Com `com_nome`, as 5 colunas (nome_oficial incluído). Sem ele, as colunas do esperado —
    e o nome_oficial publicado tem de ser nulo em toda linha.
    """
    cols = list(GOLD_COLUNAS) if com_nome else list(esperado.columns)
    lido_todo = _ler_versao(spark, caminho, versao).where(F.col("competencia") == competencia)
    lido = lido_todo.select(*cols)
    so_esperado, so_lido = bronze._diferenca_numa_passada(esperado.select(*cols), lido)
    total_lido = lido.agg(F.sum("vl_liquido_total")).collect()[0][0]
    divergentes = () if total_lido == controles.get("sum_vl_liquido") else ("sum_vl_liquido",)
    nomes_nao_nulos = 0
    if not com_nome and "nome_oficial" in lido_todo.columns:
        nomes_nao_nulos = lido_todo.where(F.col("nome_oficial").isNotNull()).count()
    ok = so_esperado == 0 and so_lido == 0 and not divergentes and nomes_nao_nulos == 0
    return ok, {
        "versao": versao,
        "so_no_esperado": so_esperado,
        "so_no_lido": so_lido,
        "controles_divergentes": divergentes,
        "nomes_nao_nulos": nomes_nao_nulos,
    }


def _metadados_do_commit(r: GoldReconciliado, id_execucao: str) -> dict:
    nome = (
        {"silver_especie": r.silver_especie}
        if r.silver_especie
        else {"nome_oficial": NAO_MEDIDO, "motivo_nome_oficial": "SEM_SILVER_ESPECIE"}
    )
    return {
        **nome,
        "estado": r.estado,
        "competencia": r.competencia,
        "hash_procedencia": r.hash_procedencia,
        "controles": {k: (None if v is None else str(v)) for k, v in r.controles.items()},
        "marcas": list(r.marcas),
        "defeitos": list(r.defeitos),
        "total_por_codigo": {str(k): str(v) for k, v in sorted(r.total_por_codigo.items())},
        "cobertura_referencial": r.cobertura,
        "reconciliacao": r.reconciliacao,
        "id_execucao": id_execucao,
        "versao_camada_anterior": r.versao_silver,
    }


# ---------------------------------------------------------------- leitura de Silver por versão


def ler_silver(spark: SparkSession, silver_destino: str, competencia: str):
    """Resolve a versão de Silver UMA vez; só os metadados da competência dizem o estado."""
    try:
        dados, dono, versao = ler_competencia_publicada(spark, silver_destino, competencia)
    except Exception as exc:  # não conseguiu ler: não é NAO_MEDIDO
        return silver.SilverClassificado(ERRO_LEITURA, competencia, motivo=f"SILVER_ILEGIVEL: {type(exc).__name__}: {exc}"), None
    if dono is None:
        return silver.SilverClassificado(NAO_MEDIDO, competencia, motivo="SILVER_SEM_METADADOS_DA_COMPETENCIA"), versao
    comum = dict(
        competencia=dono.get("competencia") or competencia,
        controles=silver._controles_de_texto(dono.get("controles") or {}),
        total_por_codigo={str(k): Decimal(str(v)) for k, v in (dono.get("total_por_codigo") or {}).items()},
        marcas=tuple(dono.get("marcas") or ()),
        hash_procedencia=dono.get("hash_procedencia"),
        defeitos=tuple(dono.get("defeitos") or ()),
        cobertura=dono.get("cobertura_referencial"),
        versao_bronze=dono.get("versao_camada_anterior"),
    )
    estado = dono.get("estado") or NAO_MEDIDO
    if estado != INTEGRO:
        return silver.SilverClassificado(estado=estado, motivo=f"SILVER_{estado}", **comum), versao
    return silver.SilverClassificado(estado=INTEGRO, linhas=dados.select(*silver.SILVER_COLUNAS), **comum), versao


# ---------------------------------------------------------------- agregação e reconciliação


def _propagado(s, competencia: str, versao) -> GoldReconciliado:
    """Estado de Silver que não é INTEGRO PARA a cadeia aqui — VERBATIM."""
    return GoldReconciliado(
        estado=s.estado,
        competencia=s.competencia or competencia,
        controles=s.controles,
        total_por_codigo=s.total_por_codigo,
        marcas=s.marcas,
        hash_procedencia=s.hash_procedencia,
        defeitos=tuple(s.defeitos),
        diferencas=tuple(s.diferencas),
        cobertura=s.cobertura,
        motivo=s.motivo or f"SILVER_{s.estado}",
        versao_silver=versao,
    )


def _diverge(r: GoldReconciliado, diferencas: List[dict], motivo: str = "DIVERGE") -> GoldReconciliado:
    return replace(
        r, estado=DIVERGE, diferencas=r.diferencas + tuple(diferencas), linhas=None,
        reconciliacao=DIVERGE, motivo=motivo,
    )


def agregar(
    spark: SparkSession,
    contrato,
    entrada=None,
    *,
    silver_destino: Optional[str] = None,
    competencia: Optional[str] = None,
    preparo_raiz: Optional[str] = None,
    id_execucao: Optional[str] = None,
    versao_camada_anterior: Optional[int] = None,
    especie_destino: Optional[str] = None,
) -> GoldReconciliado:
    """Agrega e reconcilia as CANDIDATAS. Nunca publica e nunca toca o destino.

    Com `preparo_raiz`, as candidatas são materializadas num Delta PRIVADO, relidas e
    reconferidas ANTES de qualquer publicação; a reconciliação vale sobre o relido.
    """
    competencia = competencia or contrato.competencia
    if not re.fullmatch(r"[A-Za-z0-9._-]+", competencia or ""):
        return GoldReconciliado(ERRO_LEITURA, str(competencia), motivo="COMPETENCIA_INVALIDA")
    if contrato.competencia != competencia:
        return GoldReconciliado(NAO_MEDIDO, competencia, motivo="CONTRATO_DE_OUTRA_COMPETENCIA")
    pol = contrato.politica_decimal
    if pol.emax is None or pol.emin is None:
        return GoldReconciliado(NAO_MEDIDO, competencia, motivo="CONTRATO_SEM_LIMITES_DE_EXPOENTE")

    spark.conf.set("spark.sql.ansi.enabled", "true")
    versao = versao_camada_anterior
    if entrada is None:
        if silver_destino is None:
            return GoldReconciliado(NAO_MEDIDO, competencia, motivo="SEM_ENTRADA_DE_SILVER")
        entrada, versao = ler_silver(spark, silver_destino, competencia)

    if entrada.estado != INTEGRO:
        return _propagado(entrada, competencia, versao)
    base = GoldReconciliado(
        estado=INTEGRO, competencia=competencia, controles=entrada.controles,
        total_por_codigo=entrada.total_por_codigo, marcas=entrada.marcas,
        hash_procedencia=entrada.hash_procedencia, defeitos=tuple(entrada.defeitos),
        cobertura=entrada.cobertura, versao_silver=versao,
    )
    if entrada.competencia != competencia:
        return _diverge(
            base,
            [_diferenca("competencia", "competencia_silver", competencia, entrada.competencia)],
            "COMPETENCIA_DIVERGE",
        )
    if entrada.linhas is None:
        return GoldReconciliado(NAO_MEDIDO, competencia, motivo="SILVER_SEM_LINHAS")

    persistida = None
    try:
        nomes = None
        if especie_destino is not None:
            nomes, versao_especie = _ler_nomes_da_especie(spark, especie_destino, competencia)
            base = replace(base, silver_especie={"caminho": especie_destino, "versao": versao_especie})
        de_outra = entrada.linhas.where(F.col("competencia") != competencia).limit(1).count()
        if de_outra:
            return _diverge(
                base, [_diferenca("competencia", "linhas_de_outra_competencia", competencia, "outra")],
                "COMPETENCIA_DIVERGE",
            )
        candidatas = persistida = _agregar(entrada.linhas, competencia, pol, nomes).persist()
        if nomes is not None:
            sem_nome = sorted(
                r[0] for r in candidatas.where(F.col("nome_oficial").isNull()).select("especie_codigo").collect()
            )
            if sem_nome:
                bronze._liberar(persistida)
                return _diverge(
                    base, [_diferenca("nome_oficial", "NOME_OFICIAL_AUSENTE", "nome na Silver especie", sem_nome)]
                )
        controles = {"sum_vl_liquido": candidatas.agg(F.sum("vl_liquido_total")).collect()[0][0]}
        if preparo_raiz:
            preparo = f"{preparo_raiz.rstrip('/')}/execucao={id_execucao or uuid.uuid4().hex}"
            _garantir_tabela(spark, preparo, pol)
            _gravar_preparo(spark, candidatas, preparo, competencia, {"competencia": competencia, "estado": "PREPARO"})
            ok, detalhe = _conferir_tabela(
                spark, preparo, _versao_atual(spark, preparo), candidatas, controles, competencia, pol,
                com_nome=nomes is not None,
            )
            if not ok:
                d = _diferenca("gravacao", "reconferencia_no_preparo", "multiconjunto igual", json.dumps(detalhe, default=str))
                bronze._liberar(persistida)
                return _diverge(base, [d])
            candidatas = _ler_versao(spark, preparo, _versao_atual(spark, preparo)).where(
                F.col("competencia") == competencia
            ).select(*GOLD_COLUNAS)
            base = replace(base, gravacao={"preparo": preparo})
        dif, mapa, soma = _reconciliar(candidatas, contrato, entrada, competencia)
    except Exception as exc:  # não conseguiu medir: não é NAO_MEDIDO
        bronze._liberar(persistida)
        return GoldReconciliado(ERRO_LEITURA, competencia, motivo=f"{type(exc).__name__}: {exc}")

    controles_gold = dict(entrada.controles)
    controles_gold["sum_vl_liquido"] = soma
    resultado = replace(base, controles=controles_gold, total_por_codigo=mapa)
    if dif:
        bronze._liberar(persistida)
        return _diverge(resultado, dif)
    return replace(resultado, linhas=candidatas, reconciliacao=INTEGRO, cache=persistida)


# ---------------------------------------------------------------- envelope e diagnóstico


def diagnostico(camada: str, r, contrato=None) -> str:
    """O diagnóstico ESTRUTURADO, serializado em JSON — é a MENSAGEM da exceção."""
    divergiram = [
        {
            "controle": d.get("identidade"), "observado": d.get("observado"),
            "ancorado": d.get("esperado"), "tipo": d.get("tipo"),
        }
        for d in getattr(r, "diferencas", ())
    ]
    return json.dumps(
        {
            "camada": camada,
            "estado": r.estado,
            "motivo": getattr(r, "motivo", ""),
            "controles_divergentes": divergiram,
            "classificacoes": {
                d["identidade"]: d.get("classificacao") for d in getattr(r, "diferencas", ())
            },
            "marcas": list(getattr(r, "marcas", ())),
            "cobertura_referencial": getattr(r, "cobertura", None),
        },
        ensure_ascii=False, sort_keys=True, default=str,
    )


def montar_envelope(gold: GoldReconciliado) -> dict:
    """Envelope da SEAM-FRONTEIRA: controles de DETALHE e sha256 recebidos de Bronze — nunca recalculados."""
    c = gold.controles
    texto = lambda v: None if v is None else str(v)  # noqa: E731
    return {
        "competencia": gold.competencia,
        "motor": MOTOR,
        "sha256_arquivo_lido": gold.hash_procedencia,
        "controles": {
            "count_linhas": int(c["count_linhas"]),
            "linhas_invalidas": int(c["linhas_invalidas"]),
            "sum_vl_liquido": str(c["sum_vl_liquido"]),
            "min_vl_liquido": texto(c.get("min_vl_liquido")),
            "max_vl_liquido": texto(c.get("max_vl_liquido")),
        },
        # No único caminho que emite envelope (cadeia INTEGRO, linhas_invalidas == 0) não há defeito de LINHA.
        "defeitos": [],
        "total_por_codigo": {k: str(v) for k, v in sorted(gold.total_por_codigo.items())},
    }


@dataclass(frozen=True)
class Agregado:
    """Formato de `agregacao.ResultadoAgregacao` que o juízo compara com a âncora."""

    count_linhas: int
    linhas_invalidas: int
    sum_vl_liquido: Decimal
    min_vl_liquido: Any
    max_vl_liquido: Any


def _defeitos_da_leitura(res) -> List[dict]:
    return [
        {"tipo": envelope_mod.VALOR_ILEGIVEL, "valor_original": li.valor_original, "posicao": li.posicao}
        for li in res.linhas_invalidas
    ]


def montar_leitura_da_cadeia(
    spark: SparkSession,
    *,
    caminho_csv,
    raiz: str,
    procedencia: Optional[dict] = None,
    bronze_kwargs: Optional[dict] = None,
    silver_kwargs: Optional[dict] = None,
    gold_kwargs: Optional[dict] = None,
    resultado: Optional[dict] = None,
) -> Callable:
    """O `executar_leitura` que `orquestracao.conduzir` recebe: roda a cadeia INTEIRA.

    Bronze, Silver e Gold rodam DENTRO dele. O envelope é validado ANTES dos insumos,
    porque `conduzir` NÃO valida o envelope. Qualquer parada sobe como `CadeiaParou`.
    """

    def executar(contrato) -> orquestracao.InsumosExecucao:
        b = bronze.executar_leitura(
            spark, contrato, raiz=raiz, procedencia=procedencia, **{"gravar": False, **(bronze_kwargs or {})}
        )
        if b.estado != INTEGRO:
            raise CadeiaParou(diagnostico("bronze", b))
        s = silver.executar_classificacao(spark, contrato, b, **{"gravar": False, **(silver_kwargs or {})})
        if s.estado != INTEGRO:
            raise CadeiaParou(diagnostico("silver", s))
        g = agregar(spark, contrato, s, **(gold_kwargs or {}))
        if resultado is not None:
            resultado["gold"] = g
        if g.estado != INTEGRO:
            raise CadeiaParou(diagnostico("gold", g))

        if PROCEDENCIA_NAO_VINCULADA in g.marcas:  # antes do envelope: sem hash ele recusaria por outro motivo
            raise CadeiaParou(
                json.dumps(
                    {
                        "camada": "gold", "estado": DIVERGE, "motivo": PROCEDENCIA_NAO_VINCULADA,
                        "marcas": list(g.marcas), "classificacoes": {},
                    },
                    ensure_ascii=False, sort_keys=True,
                )
            )
        lida = leitura.ler_competencia(caminho_csv, contrato)
        defeitos = _defeitos_da_leitura(lida)
        capacidade = envelope_mod.CapacidadeLeitura(
            sha256_computado=lida.sha256_depois,
            total_por_codigo=lida.total_por_codigo,
            defeitos=tuple(
                envelope_mod.DefeitoLeitura(d["tipo"], d["valor_original"], d["posicao"]) for d in defeitos
            ),
        )
        env = montar_envelope(g)
        try:
            validado = envelope_mod.validar_envelope(env, capacidade, contrato)
        except envelope_mod.EnvelopeRecusado as exc:
            raise CadeiaParou(
                json.dumps(
                    {"camada": "envelope", "estado": DIVERGE, "motivo": str(exc), "classificacoes": {}},
                    ensure_ascii=False, sort_keys=True,
                )
            ) from exc
        agregado = Agregado(
            count_linhas=validado.count_linhas,
            linhas_invalidas=validado.linhas_invalidas,
            sum_vl_liquido=validado.sum_vl_liquido,
            min_vl_liquido=validado.min_vl_liquido,
            max_vl_liquido=validado.max_vl_liquido,
        )
        return orquestracao.InsumosExecucao(
            competencia_contrato=contrato.competencia,
            competencia_envelope=env["competencia"],
            hash_ancorado=contrato.procedencia.hash_csv_sha256,
            hash_observado=lida.sha256_depois,
            hash_declarado=env["sha256_arquivo_lido"],
            agregado=agregado,
            diferencas=(),
            defeitos_leitura=defeitos,
            defeitos_envelope=list(env["defeitos"]),
            totais_leitura=dict(lida.total_por_codigo),
            totais_envelope=dict(validado.total_por_codigo),
        )

    return executar


# ---------------------------------------------------------------- publicação


def gravar_anexo(caminho_pacote: Path, gold: GoldReconciliado) -> Path:
    """Anexo ao lado do pacote: sha256 do pacote e as duas listas de códigos da cobertura."""
    cobertura = gold.cobertura or {}
    anexo = {
        "sha256_pacote": hashlib.sha256(Path(caminho_pacote).read_bytes()).hexdigest(),
        "verificados_pelo_mapa": list(cobertura.get("verificados_pelo_mapa", [])),
        "so_por_cardinalidade": list(cobertura.get("so_por_cardinalidade", [])),
    }
    caminho = Path(str(caminho_pacote) + ".cobertura.json")
    caminho.write_text(json.dumps(anexo, indent=2, sort_keys=True), encoding="utf-8")
    return caminho


def anexo_confere(caminho_pacote: Path, gold: GoldReconciliado) -> bool:
    caminho = Path(str(caminho_pacote) + ".cobertura.json")
    if not caminho.exists():
        return False
    anexo = json.loads(caminho.read_text(encoding="utf-8"))
    cobertura = gold.cobertura or {}
    return (
        anexo.get("sha256_pacote") == hashlib.sha256(Path(caminho_pacote).read_bytes()).hexdigest()
        and anexo.get("verificados_pelo_mapa") == list(cobertura.get("verificados_pelo_mapa", []))
        and anexo.get("so_por_cardinalidade") == list(cobertura.get("so_por_cardinalidade", []))
    )


def publicar(
    spark: SparkSession,
    contrato,
    gold: GoldReconciliado,
    desfecho,
    *,
    destino: str = DESTINO_PADRAO,
    id_execucao: Optional[str] = None,
    evolucao_aditiva: bool = True,
    metadados_extra: Optional[dict] = None,
) -> GoldReconciliado:
    """Passo POSTERIOR: publica se e somente se autorizado E pacote em disco E anexo conferido.

    A publicação é UM commit Delta (overwrite + replaceWhere) — visível inteiro ou não visível.
    """
    if gold.estado != INTEGRO or gold.linhas is None:
        return gold
    caminho = desfecho.caminho_pacote
    if not desfecho.autorizado_publicar or caminho is None or not Path(caminho).exists():
        return gold
    gravar_anexo(caminho, gold)
    if not anexo_confere(caminho, gold):
        return gold

    pol = contrato.politica_decimal
    comp = gold.competencia
    id_execucao = id_execucao or uuid.uuid4().hex
    meta = {**_metadados_do_commit(gold, id_execucao), **(metadados_extra or {})}
    linhas = gold.linhas.select(*GOLD_COLUNAS)
    controles = {"sum_vl_liquido": gold.controles["sum_vl_liquido"]}

    try:
        _garantir_tabela(spark, destino, pol)
        existia = bronze._competencia_existe(spark, destino, comp)
        versao_anterior = _versao_atual(spark, destino)
        publicar_competencia(spark, linhas, destino, comp, meta, evolucao_aditiva=evolucao_aditiva)
        versao = _versao_atual(spark, destino)
        ok, detalhe = _conferir_tabela(
            spark, destino, versao, linhas, controles, comp, pol, com_nome=gold.silver_especie is not None
        )
        if not ok:
            bronze._reverter_competencia(spark, destino, comp, existia, versao_anterior, meta)
            d = _diferenca("gravacao", "reconferencia_publicada", "multiconjunto igual", json.dumps(detalhe, default=str))
            return _diverge(gold, [d])
        return replace(gold, gravacao={**(gold.gravacao or {}), "destino": destino, "versao": versao, "id_execucao": id_execucao})
    finally:
        bronze._liberar(gold.cache)  # só depois da reconferência, em todo caminho


def executar_gold(
    spark: SparkSession,
    *,
    diretorio_evidencia,
    competencia_solicitada: str,
    caminho_contrato,
    caminho_csv,
    raiz: str,
    procedencia: Optional[dict] = None,
    destino: str = DESTINO_PADRAO,
    preparo_raiz: str = PREPARO_PADRAO,
    id_execucao: Optional[str] = None,
    bronze_kwargs: Optional[dict] = None,
    silver_kwargs: Optional[dict] = None,
    evolucao_aditiva: bool = True,
    especie_destino: Optional[str] = None,
):
    """Cadeia inteira sob `orquestracao.conduzir`; publica só com autorização, pacote e anexo."""
    from pda import contrato as contrato_mod

    id_execucao = id_execucao or uuid.uuid4().hex
    guardado: dict = {}
    executar = montar_leitura_da_cadeia(
        spark, caminho_csv=caminho_csv, raiz=raiz, procedencia=procedencia,
        bronze_kwargs=bronze_kwargs, silver_kwargs=silver_kwargs,
        gold_kwargs={"preparo_raiz": preparo_raiz, "id_execucao": id_execucao, "especie_destino": especie_destino},
        resultado=guardado,
    )
    desfecho = orquestracao.conduzir(
        diretorio_evidencia=diretorio_evidencia,
        competencia_solicitada=competencia_solicitada,
        caminho_contrato=caminho_contrato,
        executar_leitura=executar,
    )
    gold = guardado.get("gold")
    if gold is None or not desfecho.autorizado_publicar:
        if gold is not None:
            bronze._liberar(gold.cache)
        return desfecho, gold
    contrato = contrato_mod.carregar_contrato(caminho_contrato)
    return desfecho, publicar(
        spark, contrato, gold, desfecho, destino=destino, id_execucao=id_execucao,
        evolucao_aditiva=evolucao_aditiva,
    )


# ---------------------------------------------------------------- Gold a partir da Silver (SEAM-GOLD-LE-SILVER)


def _commit_da_bronze(spark: SparkSession, bronze_destino: str, competencia: str, versao: int) -> Optional[dict]:
    """Metadados do ÚLTIMO commit da Bronze até `versao` que nomeia a competência."""
    for v, meta in sorted(_historico(spark, bronze_destino), key=lambda t: t[0], reverse=True):
        if v > versao or not meta:
            continue
        try:
            corpo = json.loads(meta)
        except ValueError:
            continue
        if isinstance(corpo, dict) and corpo.get("competencia") == competencia:
            return corpo
    return None


def _conferir_linhagem(spark: SparkSession, competencia: str, s, versao_silver, bronze_destino: str):
    """Segue a Silver até o pacote ACEITO. Devolve (caminho, sha256_pacote) ou uma GoldReconciliado que para."""

    def falha(estado, motivo, dif=()):
        return GoldReconciliado(
            estado=estado, competencia=competencia, controles=s.controles,
            total_por_codigo=s.total_por_codigo, marcas=s.marcas, hash_procedencia=s.hash_procedencia,
            diferencas=tuple(dif), motivo=motivo, versao_silver=versao_silver,
        )

    if s.versao_bronze is None:
        return falha(NAO_MEDIDO, "SILVER_SEM_VERSAO_DA_BRONZE")
    try:
        commit = _commit_da_bronze(spark, bronze_destino, competencia, int(s.versao_bronze))
    except Exception as exc:  # não conseguiu ler: não é NAO_MEDIDO
        return falha(ERRO_LEITURA, f"BRONZE_ILEGIVEL: {type(exc).__name__}: {exc}")
    if commit is None or not commit.get("caminho_pacote") or not commit.get("sha256_pacote"):
        return falha(NAO_MEDIDO, "SEM_PACOTE_ACEITO_NA_LINHAGEM")
    caminho = Path(commit["caminho_pacote"])
    if not caminho.is_file():
        return falha(NAO_MEDIDO, "PACOTE_DA_LINHAGEM_AUSENTE")
    observado = hashlib.sha256(caminho.read_bytes()).hexdigest()  # os BYTES, não o que o pacote diz de si
    if observado != commit["sha256_pacote"]:
        return falha(
            DIVERGE, "PACOTE_DA_LINHAGEM_ADULTERADO",
            [_diferenca("procedencia", "sha256_pacote", commit["sha256_pacote"], observado)],
        )
    pacote = evidencia.ler_pacote(caminho)
    try:
        veredito, _ = evidencia.rederivar_veredito(pacote)
    except evidencia.EvidenciaRecusada:
        veredito = None
    if veredito != evidencia.ACEITO:
        return falha(NAO_MEDIDO, "SEM_PACOTE_ACEITO_NA_LINHAGEM")
    if pacote.get("competencia_contrato") != competencia:
        return falha(
            DIVERGE, "PACOTE_DE_OUTRA_COMPETENCIA",
            [_diferenca("competencia", "competencia_do_pacote", competencia, pacote.get("competencia_contrato"))],
        )
    if not s.hash_procedencia:
        return falha(NAO_MEDIDO, "SILVER_SEM_SHA256_DO_CSV")
    if pacote.get("hash_observado") != s.hash_procedencia:
        return falha(
            DIVERGE, "PACOTE_DE_OUTRO_CSV",
            [_diferenca("procedencia", "sha256_csv", s.hash_procedencia, pacote.get("hash_observado"))],
        )
    return caminho, observado


def executar_gold_da_silver(
    spark: SparkSession,
    *,
    caminho_contrato,
    silver_destino: str,
    bronze_destino: str,
    destino: str = DESTINO_PADRAO,
    preparo_raiz: str = PREPARO_PADRAO,
    id_execucao: Optional[str] = None,
    evolucao_aditiva: bool = True,
    especie_destino: Optional[str] = None,
) -> GoldReconciliado:
    """Gold principal lendo SÓ a Silver publicada — nunca a landing nem o CSV.

    Resolve a versão da Silver UMA vez, segue a versão da Bronze registrada nos
    metadados dela e confere que o commit da Bronze nomeia um pacote ACEITO da mesma
    competência e do mesmo sha256 do CSV. Sem essa linhagem, nada é publicado.
    """
    from pda import contrato as contrato_mod

    contrato = contrato_mod.carregar_contrato(caminho_contrato)
    competencia = contrato.competencia
    if not re.fullmatch(r"[A-Za-z0-9._-]+", competencia or ""):
        return GoldReconciliado(ERRO_LEITURA, str(competencia), motivo="COMPETENCIA_INVALIDA")
    s, versao_silver = ler_silver(spark, silver_destino, competencia)
    if s.estado != INTEGRO:
        return _propagado(s, competencia, versao_silver)
    linhagem = _conferir_linhagem(spark, competencia, s, versao_silver, bronze_destino)
    if isinstance(linhagem, GoldReconciliado):
        return linhagem
    caminho_pacote, sha_pacote = linhagem

    id_execucao = id_execucao or uuid.uuid4().hex
    g = agregar(
        spark, contrato, s, preparo_raiz=preparo_raiz, id_execucao=id_execucao,
        versao_camada_anterior=versao_silver, especie_destino=especie_destino,
    )
    if g.estado != INTEGRO:
        return g
    desfecho = orquestracao.Desfecho(
        veredito=evidencia.ACEITO, causa="JULGADO", codigo_saida=0,
        caminho_pacote=caminho_pacote, duracao_segundos=0.0, autorizado_publicar=True,
    )
    try:
        return publicar(
            spark, contrato, g, desfecho, destino=destino, id_execucao=id_execucao,
            evolucao_aditiva=evolucao_aditiva,
            metadados_extra={
                "versao_silver": versao_silver,
                "caminho_pacote": str(caminho_pacote),
                "sha256_pacote": sha_pacote,
            },
        )
    finally:
        bronze._liberar(g.cache)
