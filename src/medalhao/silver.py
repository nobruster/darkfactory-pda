"""Silver: normaliza a FORMA, classifica a identidade colapsada e só então grava em Delta.

Cinco estados, distintos — e a PRECEDÊNCIA de Silver é DIVERGE, depois
BLOQUEADO, depois NAO_MEDIDO: o estado reporta a falha MEDIDA mais próxima da
fonte, e o que não se mediu não esconde o que se mediu.

- INTEGRO       conservação provada, cada colapso classificado contra o mapa aprovado
- DIVERGE       cardinalidade diferente do contrato, mapa parcial, ou conservação quebrada
- BLOQUEADO     colapso sem classificação, UNRESOLVED, ou colapso criado pela própria camada
- NAO_MEDIDO    o contrato não declara o mapa código→descrição: valor conservado, identidade em aberto
- ERRO_LEITURA  não conseguiu medir

Silver só transforma sobre Bronze INTEGRO; qualquer outro estado de Bronze
PARA a cadeia aqui e é propagado sem tradução.

A chave é o CÓDIGO (ADR 0008), nunca a descrição. As três cardinalidades que
dependem de descrição são medidas sobre a descrição ORIGINAL — a base em que o
contrato as mediu. A prova de que a normalização não fundiu identidades é
comparar, código a código, o grupo antes e depois de normalizar; contar grupos
não basta. Toda comparação de linhas roda NO MOTOR (exceptAll), sem coletar.

O que governa a aritmética é o DecimalType do acumulador, declarado a partir
da politica_decimal do contrato, com spark.sql.ansi.enabled=true declarado.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field, replace
from decimal import Decimal, localcontext
from typing import Any, Dict, List, Optional, Tuple

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType

from medalhao import bronze
from pda import juizo

INTEGRO = bronze.INTEGRO
DIVERGE = bronze.DIVERGE
NAO_MEDIDO = bronze.NAO_MEDIDO
ERRO_LEITURA = bronze.ERRO_LEITURA
BLOQUEADO = "BLOQUEADO"

PROCEDENCIA_NAO_VINCULADA = bronze.PROCEDENCIA_NAO_VINCULADA
CONTROLES = bronze.CONTROLES
CLASSIFICACOES = bronze.CLASSIFICACOES

# Nomes que Gold consome — os mesmos, sem tradução.
SILVER_COLUNAS = (
    "especie_codigo",
    "especie_descricao",
    "especie_descricao_normalizada",
    "vl_liquido",
    "competencia",
    "classificacao",
)
COLUNAS_DE_CONSERVACAO = ("especie_codigo", "especie_descricao", "vl_liquido")

DESTINO_PADRAO = "s3a://silver/pda/beneficios-emitidos"
PREPARO_PADRAO = "s3a://silver/_preparo/pda/beneficios-emitidos"

TIPO_COLAPSO = "IDENTIDADE_COLAPSADA"
# O contrato pré-classifica IDENTIDADE_COLAPSADA como CONFIRMED_SOURCE_DEFECT,
# com aprovador e data; o carregador não traz o campo `classificacao`, então a
# leitura vale só para este tipo e só com aprovador e data presentes.
CLASSIFICACAO_DO_TIPO_CONHECIDO = {TIPO_COLAPSO: juizo.CONFIRMED_SOURCE_DEFECT}

ESTADOS_QUE_GRAVAM = (INTEGRO, NAO_MEDIDO)
TIPOS_QUE_DIVERGEM = frozenset({"cardinalidade", "mapa", "conservacao", "gravacao"})

EvolucaoRecusada = bronze.EvolucaoRecusada


@dataclass(frozen=True)
class SilverClassificado:
    """A capacidade 'silver classificado' — com forma, não só nome."""

    estado: str
    competencia: str
    controles: Dict[str, Any] = field(default_factory=dict)
    total_por_codigo: Dict[str, Decimal] = field(default_factory=dict)
    marcas: Tuple[str, ...] = ()
    hash_procedencia: Optional[str] = None
    linhas: Optional[DataFrame] = None
    defeitos: Tuple[dict, ...] = ()
    diferencas: Tuple[dict, ...] = ()
    bloqueios: Tuple[str, ...] = ()
    cobertura: Optional[dict] = None
    medidas: Dict[str, Any] = field(default_factory=dict)
    motivo: str = ""
    versao_bronze: Optional[int] = None
    gravacao: Optional[dict] = None


# ---------------------------------------------------------------- reexportes do motor de Bronze

criar_sessao = bronze.criar_sessao
contexto_declarado = bronze.contexto_declarado
tipo_acumulador = bronze.tipo_acumulador
classificar = bronze.classificar
bloqueia = bronze.bloqueia
verificar_evolucao = bronze.verificar_evolucao
publicar_competencia = bronze.publicar_competencia
ler_competencia_publicada = bronze.ler_competencia_publicada
_delta_table = bronze._delta_table
_versao_atual = bronze._versao_atual
_historico = bronze._historico
_ler_versao = bronze._ler_versao
_diferenca = bronze._diferenca


# ---------------------------------------------------------------- normalização e medidas


def _normalizar(df: DataFrame) -> DataFrame:
    """Normaliza a FORMA — espaços à borda e caixa da descrição. Jamais o valor monetário."""
    normalizada = F.upper(F.regexp_replace(F.col("especie_descricao"), r"^\s+|\s+$", ""))
    return df.select(
        "especie_codigo",
        "especie_descricao",
        normalizada.alias("especie_descricao_normalizada"),
        "vl_liquido",
        "competencia",
    )


def _com_classificacao(df: DataFrame, por_codigo: Dict[str, str]) -> DataFrame:
    """Anexa `classificacao` por CÓDIGO; linha fora de colapso fica nula."""
    coluna = None
    for codigo in sorted(por_codigo):
        cond = F.col("especie_codigo") == F.lit(codigo)
        coluna = (
            F.when(cond, F.lit(por_codigo[codigo]))
            if coluna is None
            else coluna.when(cond, F.lit(por_codigo[codigo]))
        )
    valor = F.lit(None).cast(StringType()) if coluna is None else coluna
    return df.withColumn("classificacao", valor).select(*SILVER_COLUNAS)


def _pares(df: DataFrame) -> List[Tuple[Any, Any, Any]]:
    """(código, descrição original, descrição normalizada) DISTINTOS — limitados pela cardinalidade."""
    linhas = df.select("especie_codigo", "especie_descricao", "especie_descricao_normalizada").distinct().collect()
    return [(r[0], r[1], r[2]) for r in linhas]


def _grupos(pares, indice: int) -> Dict[Any, set]:
    grupos: Dict[Any, set] = {}
    for par in pares:
        grupos.setdefault(par[indice], set()).add(par[0])
    return grupos


def _cardinalidades(pares, indice: int) -> Tuple[Dict[str, int], Dict[Any, set]]:
    grupos = _grupos(pares, indice)
    colapsados = {d: c for d, c in grupos.items() if len(c) > 1}
    uniao = set().union(*colapsados.values()) if colapsados else set()
    return (
        {
            "codigos_distintos": len({p[0] for p in pares}),
            "descricoes_distintas": len(grupos),
            "colapsos": len(colapsados),
            "codigos_colapsados": len(uniao),
        },
        colapsados,
    )


def _codigos_com_grupo_alterado(pares) -> List[str]:
    """Códigos cujo conjunto de códigos-irmãos mudou ao normalizar — colapso criado pela camada."""
    antes, depois = _grupos(pares, 1), _grupos(pares, 2)
    a: Dict[Any, set] = {}
    d: Dict[Any, set] = {}
    for codigo, original, normalizada in pares:
        a.setdefault(codigo, set()).update(antes[original])
        d.setdefault(codigo, set()).update(depois[normalizada])
    return sorted(c for c in a if a[c] != d[c])


def _codigos_com_varias_descricoes(pares) -> Dict[Any, List[Any]]:
    por_codigo: Dict[Any, set] = {}
    for codigo, original, _ in pares:
        por_codigo.setdefault(codigo, set()).add(original)
    return {c: sorted(ds, key=str) for c, ds in por_codigo.items() if len(ds) > 1}


def _diferenca_multiconjunto(bronze_df: DataFrame, silver_df: DataFrame) -> Tuple[int, int]:
    """Diferença simétrica dos multiconjuntos (código, descrição original, valor), NO MOTOR."""
    cols = list(COLUNAS_DE_CONSERVACAO)
    b, s = bronze_df.select(*cols), silver_df.select(*cols)
    return b.exceptAll(s).count(), s.exceptAll(b).count()


def _classificacao_do_contrato(contrato) -> Tuple[str, Optional[dict]]:
    for d in contrato.defeitos_conhecidos:
        tipo = getattr(d, "tipo", None)
        aprovador, aprovado_em = getattr(d, "aprovador", None), getattr(d, "aprovado_em", None)
        if tipo in CLASSIFICACAO_DO_TIPO_CONHECIDO and aprovador and aprovado_em:
            proposta = getattr(d, "classificacao", None) or CLASSIFICACAO_DO_TIPO_CONHECIDO[tipo]
            return classificar(tipo, (proposta,)), {"aprovador": aprovador, "aprovado_em": str(aprovado_em)}
    return juizo.UNRESOLVED, None


def _registros_de_colapso(colapsos: Dict[Any, set], contrato) -> Tuple[List[dict], List[dict]]:
    """UM registro por GRUPO colapsado: descrição ORIGINAL e lista ordenada dos códigos."""
    mapa = contrato.mapa_colapsos
    classificacao, aprovacao = _classificacao_do_contrato(contrato)
    declarados = (
        {(g.descricao, tuple(sorted(str(c) for c in g.codigos))) for g in mapa.grupos} if mapa else set()
    )
    registros: List[dict] = []
    diferencas: List[dict] = []
    medidos = set()
    for descricao in sorted(colapsos, key=str):
        codigos = sorted(colapsos[descricao])
        chave = (descricao, tuple(str(c) for c in codigos))
        medidos.add(chave)
        registro = {
            "tipo": TIPO_COLAPSO,
            "identidade": f"colapso:{descricao}",
            "descricao_original": descricao,
            "codigos": codigos,
        }
        if mapa is None:
            registro.update(classificacao=None, referencial="NAO_MEDIDO")
        elif chave in declarados:
            registro.update(classificacao=classificacao, referencial="MAPA_APROVADO", **(aprovacao or {}))
        else:
            registro.update(classificacao=juizo.UNRESOLVED, referencial="FORA_DO_MAPA")
            diferencas.append(
                _diferenca(
                    "identidade", f"colapso_fora_do_mapa:{descricao}",
                    "grupo declarado no mapa aprovado", f"{descricao}: {codigos}",
                )
            )
        registros.append(registro)
    if mapa is not None:
        for g in mapa.grupos:
            chave = (g.descricao, tuple(sorted(str(c) for c in g.codigos)))
            if chave not in medidos:
                diferencas.append(
                    _diferenca(
                        "identidade", f"mapa_grupo_nao_medido:{g.descricao}",
                        f"{g.descricao}: {list(chave[1])}", "ausente na fonte",
                    )
                )
    return registros, diferencas


def _diferencas_de_mapa(contrato) -> List[dict]:
    """Mapa presente e aprovado mas INCOMPLETO é DIVERGE, nunca identidade medida."""
    mapa, card = contrato.mapa_colapsos, contrato.cardinalidade
    if mapa is None:
        return []
    grupos = len(mapa.grupos)
    codigos = len({str(c) for g in mapa.grupos for c in g.codigos})
    diferencas = []
    if grupos != card.colapsos:
        diferencas.append(_diferenca("mapa", "mapa_parcial:grupos", card.colapsos, grupos))
    if codigos != card.codigos_colapsados:
        diferencas.append(_diferenca("mapa", "mapa_parcial:codigos", card.codigos_colapsados, codigos))
    return diferencas


def _cobertura(pares, registros: List[dict], contrato) -> dict:
    """Códigos verificados pelo mapa e códigos só por cardinalidade — a limitação fica na evidência."""
    todos = sorted({p[0] for p in pares})
    verificados = sorted(
        {c for r in registros if r["referencial"] == "MAPA_APROVADO" for c in r["codigos"]}
    )
    return {
        "verificados_pelo_mapa": verificados,
        "so_por_cardinalidade": [c for c in todos if c not in set(verificados)],
        "conteudo_dos_nao_colapsados_verificado": False,
    }


# ---------------------------------------------------------------- Delta


def _garantir_tabela(spark: SparkSession, caminho: str, politica) -> None:
    """Tabela com o DecimalType do contrato, NOT NULL nas chaves e CHECK >= 0 no dinheiro."""
    from delta.tables import DeltaTable

    (
        DeltaTable.createIfNotExists(spark)
        .location(caminho)
        .addColumn("especie_codigo", StringType(), nullable=False)
        .addColumn("especie_descricao", StringType())
        .addColumn("especie_descricao_normalizada", StringType())
        .addColumn("vl_liquido", tipo_acumulador(politica))
        .addColumn("competencia", StringType(), nullable=False)
        .addColumn("classificacao", StringType())
        .partitionedBy("competencia")
        .execute()
    )
    propriedades = _delta_table(spark, caminho).detail().select("properties").first()[0] or {}
    if "delta.constraints.vl_nao_negativo" not in propriedades:
        spark.sql(f"ALTER TABLE delta.`{caminho}` ADD CONSTRAINT vl_nao_negativo CHECK (vl_liquido >= 0)")


def _gravar_preparo(spark: SparkSession, linhas: DataFrame, preparo: str, competencia: str, metadados: dict):
    publicar_competencia(spark, linhas, preparo, competencia, metadados)


def _conferir_tabela(
    spark: SparkSession, caminho: str, versao: int, esperado: DataFrame, controles: Dict[str, Any],
    competencia: str, politica, defeitos: Tuple[dict, ...] = (),
) -> Tuple[bool, dict]:
    """RELÊ a versão commitada e compara o MULTICONJUNTO de TODAS as colunas, nos dois sentidos.

    Inclui a descrição normalizada e a classificação, esta também contra os defeitos.
    """
    cols = list(SILVER_COLUNAS)
    lido = _ler_versao(spark, caminho, versao).where(F.col("competencia") == competencia).select(*cols)
    so_esperado = esperado.select(*cols).exceptAll(lido).count()
    so_lido = lido.exceptAll(esperado.select(*cols)).count()
    observados, _ = bronze.medir_controles(lido, politica)
    divergentes = bronze._controles_iguais(observados, controles, politica)

    esperadas = {(c, d["classificacao"]) for d in defeitos if d.get("classificacao") for c in d["codigos"]}
    lidas = {
        (r[0], r[1])
        for r in lido.where(F.col("classificacao").isNotNull())
        .select("especie_codigo", "classificacao").distinct().collect()
    }
    classificacao_divergente = tuple(sorted(esperadas ^ lidas))
    detalhe = {
        "versao": versao,
        "so_no_esperado": so_esperado,
        "so_no_lido": so_lido,
        "controles_divergentes": divergentes,
        "classificacao_divergente": classificacao_divergente,
    }
    ok = so_esperado == 0 and so_lido == 0 and not divergentes and not classificacao_divergente
    return ok, detalhe


def _metadados_do_commit(r: SilverClassificado, id_execucao: str, versao_camada_anterior) -> dict:
    return {
        "estado": r.estado,
        "competencia": r.competencia,
        "hash_procedencia": r.hash_procedencia,
        "controles": {k: (None if v is None else str(v)) for k, v in r.controles.items()},
        "marcas": list(r.marcas),
        "defeitos": list(r.defeitos),
        "total_por_codigo": {str(k): str(v) for k, v in sorted(r.total_por_codigo.items())},
        "cobertura_referencial": r.cobertura,
        "motivo": r.motivo,
        "id_execucao": id_execucao,
        "versao_camada_anterior": versao_camada_anterior,
    }


# ---------------------------------------------------------------- leitura de Bronze por versão


def _controles_de_texto(controles: Dict[str, Any]) -> Dict[str, Any]:
    saida: Dict[str, Any] = {}
    for nome, valor in controles.items():
        if valor is None:
            saida[nome] = None
        elif nome in ("count_linhas", "linhas_invalidas"):
            saida[nome] = int(valor)
        else:
            saida[nome] = Decimal(str(valor))
    return saida


def ler_bronze(spark: SparkSession, bronze_destino: str, competencia: str):
    """Resolve a versão de Bronze UMA vez; só os metadados da competência dizem o estado.

    Devolve (BronzeConferido, versão lida). Só INTEGRO traz linhas.
    """
    try:
        dados, dono, versao = ler_competencia_publicada(spark, bronze_destino, competencia)
    except Exception as exc:  # não conseguiu ler: não é NAO_MEDIDO
        return bronze._erro(competencia, f"BRONZE_ILEGIVEL: {type(exc).__name__}: {exc}"), None
    if dono is None:
        return bronze._nao_medido(competencia, "BRONZE_SEM_METADADOS_DA_COMPETENCIA"), versao
    estado = dono.get("estado") or NAO_MEDIDO
    controles = _controles_de_texto(dono.get("controles") or {})
    total = {str(k): Decimal(str(v)) for k, v in (dono.get("total_por_codigo") or {}).items()}
    comum = dict(
        competencia=competencia,
        controles=controles,
        total_por_codigo=total,
        marcas=tuple(dono.get("marcas") or ()),
        hash_procedencia=dono.get("hash_procedencia"),
    )
    if estado != INTEGRO:
        return bronze.BronzeConferido(estado=estado, motivo=f"BRONZE_{estado}", **comum), versao
    return bronze.BronzeConferido(estado=INTEGRO, linhas=dados.select(*bronze.COLUNAS), **comum), versao


# ---------------------------------------------------------------- classificação


def _propagado(b, competencia: str, versao) -> SilverClassificado:
    """Estado de Bronze que não é INTEGRO PARA a cadeia aqui — propagado sem tradução."""
    return SilverClassificado(
        estado=b.estado,
        competencia=b.competencia or competencia,
        controles=b.controles,
        total_por_codigo=b.total_por_codigo,
        marcas=b.marcas,
        hash_procedencia=b.hash_procedencia,
        motivo=b.motivo or f"BRONZE_{b.estado}",
        versao_bronze=versao,
    )


def _classificar(spark: SparkSession, contrato, b, versao_bronze) -> SilverClassificado:
    pol = contrato.politica_decimal
    card = contrato.cardinalidade
    diferencas: List[dict] = []

    normalizado = _normalizar(b.linhas)
    pares = _pares(normalizado)

    # As três cardinalidades que dependem de descrição, sobre a ORIGINAL — a base do contrato.
    medidas, colapsos = _cardinalidades(pares, 1)
    for nome in ("codigos_distintos", "descricoes_distintas", "colapsos", "codigos_colapsados"):
        if medidas[nome] != getattr(card, nome):
            diferencas.append(_diferenca("cardinalidade", nome, getattr(card, nome), medidas[nome]))

    for codigo, descricoes in sorted(_codigos_com_varias_descricoes(pares).items()):
        diferencas.append(
            _diferenca("identidade", f"codigo_com_varias_descricoes:{codigo}", "uma descrição", descricoes)
        )

    # A normalização não pode ter fundido identidades: grupo antes x depois, CÓDIGO A CÓDIGO.
    medidas_norm, _ = _cardinalidades(pares, 2)
    introduzidos = _codigos_com_grupo_alterado(pares)
    for codigo in introduzidos:
        diferencas.append(
            _diferenca(
                "identidade", f"colapso_introduzido_pela_camada:{codigo}",
                "grupo inalterado pela normalização", "grupo alterado",
                classificacao=juizo.MODERN_DEFECT,
            )
        )
    if introduzidos:
        for nome in ("descricoes_distintas", "colapsos", "codigos_colapsados"):
            if medidas_norm[nome] != medidas[nome]:
                diferencas.append(
                    _diferenca(
                        "identidade", f"normalizacao:{nome}", medidas[nome], medidas_norm[nome],
                        classificacao=juizo.MODERN_DEFECT,
                    )
                )

    registros, dif_registros = _registros_de_colapso(colapsos, contrato)
    diferencas += dif_registros + _diferencas_de_mapa(contrato)

    por_codigo = {c: r["classificacao"] for r in registros if r["classificacao"] for c in r["codigos"]}
    silver = _com_classificacao(normalizado, por_codigo)

    # Conservação — no motor, sobre o multiconjunto, o total e o mapa CÓDIGO A CÓDIGO.
    controles_b = b.controles or bronze.medir_controles(b.linhas, pol)[0]
    mapa_b = b.total_por_codigo or bronze.medir_controles(b.linhas, pol)[1]
    so_bronze, so_silver = _diferenca_multiconjunto(b.linhas, silver)
    if so_bronze or so_silver:
        diferencas.append(
            _diferenca(
                "conservacao", "multiconjunto_de_linhas", "diferença simétrica vazia",
                f"so_bronze={so_bronze}, so_silver={so_silver}",
            )
        )
    controles_s, mapa_s = bronze.medir_controles(silver, pol)
    for nome in bronze._controles_iguais(controles_s, controles_b, pol):
        diferencas.append(_diferenca("conservacao", f"controle:{nome}", controles_b.get(nome), controles_s.get(nome)))
    for codigo in sorted(set(mapa_b) | set(mapa_s)):
        if mapa_b.get(codigo) != mapa_s.get(codigo):
            diferencas.append(
                _diferenca("conservacao", f"total_por_codigo:{codigo}", mapa_b.get(codigo), mapa_s.get(codigo))
            )

    bloqueios = list(
        dict.fromkeys(
            [d["identidade"] for d in diferencas if d["tipo"] == "identidade" and bloqueia(d["classificacao"])]
            + [r["identidade"] for r in registros if r["classificacao"] and bloqueia(r["classificacao"])]
        )
    )
    motivo = ""
    if any(d["tipo"] in TIPOS_QUE_DIVERGEM for d in diferencas):
        estado, motivo = DIVERGE, "DIVERGE"
    elif bloqueios:
        estado, motivo = BLOQUEADO, "DEFEITO_BLOQUEANTE"
    elif contrato.mapa_colapsos is None:
        estado, motivo = NAO_MEDIDO, "MAPA_NAO_DECLARADO"
    else:
        estado = INTEGRO

    return SilverClassificado(
        estado=estado,
        competencia=b.competencia,
        controles=controles_b,
        total_por_codigo=mapa_s,
        marcas=b.marcas,
        hash_procedencia=b.hash_procedencia,
        linhas=silver if estado != DIVERGE else None,
        defeitos=tuple(registros),
        diferencas=tuple(diferencas),
        bloqueios=tuple(bloqueios),
        cobertura=_cobertura(pares, registros, contrato),
        medidas=medidas,
        motivo=motivo,
        versao_bronze=versao_bronze,
    )


def executar_classificacao(
    spark: SparkSession,
    contrato,
    entrada=None,
    *,
    bronze_destino: Optional[str] = None,
    competencia: Optional[str] = None,
    gravar: bool = True,
    destino: str = DESTINO_PADRAO,
    preparo_raiz: str = PREPARO_PADRAO,
    id_execucao: Optional[str] = None,
    versao_camada_anterior: Optional[int] = None,
    evolucao_aditiva: bool = False,
) -> SilverClassificado:
    """Classifica a competência a partir de Bronze (objeto `entrada` ou tabela `bronze_destino`).

    Nunca encerra o processo: o desfecho é um valor. Falha de gravação levanta.
    """
    competencia = competencia or contrato.competencia
    if not re.fullmatch(r"[A-Za-z0-9._-]+", competencia or ""):
        return SilverClassificado(ERRO_LEITURA, str(competencia), motivo="COMPETENCIA_INVALIDA")
    if contrato.competencia != competencia:
        return SilverClassificado(NAO_MEDIDO, competencia, motivo="CONTRATO_DE_OUTRA_COMPETENCIA")
    if contrato.politica_decimal.emax is None or contrato.politica_decimal.emin is None:
        return SilverClassificado(NAO_MEDIDO, competencia, motivo="CONTRATO_SEM_LIMITES_DE_EXPOENTE")

    spark.conf.set("spark.sql.ansi.enabled", "true")
    versao = versao_camada_anterior
    if entrada is None:
        if bronze_destino is None:
            return SilverClassificado(NAO_MEDIDO, competencia, motivo="SEM_ENTRADA_DE_BRONZE")
        entrada, versao = ler_bronze(spark, bronze_destino, competencia)

    if entrada.estado != INTEGRO:
        return _propagado(entrada, competencia, versao)
    if entrada.competencia != competencia:
        return SilverClassificado(NAO_MEDIDO, competencia, motivo="BRONZE_DE_OUTRA_COMPETENCIA")
    if entrada.linhas is None:
        return SilverClassificado(NAO_MEDIDO, competencia, motivo="BRONZE_SEM_LINHAS")

    try:
        resultado = _classificar(spark, contrato, entrada, versao)
    except Exception as exc:  # não conseguiu medir: não é NAO_MEDIDO
        return SilverClassificado(ERRO_LEITURA, competencia, motivo=f"{type(exc).__name__}: {exc}")

    if resultado.estado not in ESTADOS_QUE_GRAVAM or not gravar:
        return resultado
    return _gravar(
        spark, contrato, resultado, destino, preparo_raiz,
        id_execucao or uuid.uuid4().hex, versao, evolucao_aditiva,
    )


def _gravar(spark, contrato, r, destino, preparo_raiz, id_execucao, versao_bronze, evolucao):
    pol = contrato.politica_decimal
    comp = r.competencia
    meta = _metadados_do_commit(r, id_execucao, versao_bronze)
    linhas = r.linhas.select(*SILVER_COLUNAS)
    preparo = f"{preparo_raiz.rstrip('/')}/execucao={id_execucao}"

    def _diverge(identidade: str, detalhe: dict) -> SilverClassificado:
        d = _diferenca("gravacao", identidade, "multiconjunto e controles iguais", json.dumps(detalhe, default=str))
        return replace(r, estado=DIVERGE, diferencas=r.diferencas + (d,), linhas=None, motivo="DIVERGE")

    _garantir_tabela(spark, preparo, pol)
    _gravar_preparo(spark, linhas, preparo, comp, meta)
    ok, detalhe = _conferir_tabela(
        spark, preparo, _versao_atual(spark, preparo), linhas, r.controles, comp, pol, r.defeitos
    )
    if not ok:
        return _diverge("reconferencia_no_preparo", detalhe)

    _garantir_tabela(spark, destino, pol)
    existia = bronze._competencia_existe(spark, destino, comp)
    versao_anterior = _versao_atual(spark, destino)
    publicar_competencia(spark, linhas, destino, comp, meta, evolucao_aditiva=evolucao)
    versao = _versao_atual(spark, destino)
    ok, detalhe = _conferir_tabela(spark, destino, versao, linhas, r.controles, comp, pol, r.defeitos)
    if not ok:
        bronze._reverter_competencia(spark, destino, comp, existia, versao_anterior, meta)
        return _diverge("reconferencia_publicada", detalhe)

    return replace(
        r, gravacao={"destino": destino, "preparo": preparo, "versao": versao, "id_execucao": id_execucao}
    )
