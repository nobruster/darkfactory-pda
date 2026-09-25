"""Tabela Delta `especie`: o nome oficial da ontologia AO LADO do texto que a fonte publicou.

A Silver guarda `especie_descricao` truncada (o defeito da fonte, Regra 4); esta tabela não a
corrige nem a substitui: guarda os dois textos, um por coluna, e a marca de quando o texto da
fonte é o começo do nome oficial.

Estados, os mesmos das outras camadas: INTEGRO, DIVERGE, NAO_MEDIDO, ERRO_LEITURA.

- A Silver é lida UMA vez, na versão V fixada no início (versionAsOf); a mesma leitura confere e calcula.
- A conferência vem ANTES da gravação: divergência recusa e o destino não ganha versão nova.
- Competência sem nenhuma linha é NAO_MEDIDO (Regra 9), nunca INTEGRO com zero linhas.
- Gravado, o destino é relido NA versão do próprio commit (achada pelo id_execucao), nunca na atual.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field, replace
from types import SimpleNamespace
from typing import Dict, List, Optional, Tuple

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import BooleanType, StringType, StructField, StructType

from medalhao import bronze

INTEGRO = bronze.INTEGRO
DIVERGE = bronze.DIVERGE
NAO_MEDIDO = bronze.NAO_MEDIDO
ERRO_LEITURA = bronze.ERRO_LEITURA
RECUSADO = "RECUSADO"

SILVER_PADRAO = "s3a://silver/pda/beneficios-emitidos"
DESTINO_PADRAO = "s3a://silver/pda/especie"
LARGURA_DO_TEXTO_DA_FONTE = 20

COLUNAS = (
    "especie_codigo", "nome_oficial", "grupo", "descricao_fonte",
    "texto_fonte_confere_prefixo", "competencia",
)
SCHEMA = StructType([
    StructField("especie_codigo", StringType(), nullable=False),
    StructField("nome_oficial", StringType()),
    StructField("grupo", StringType()),
    StructField("descricao_fonte", StringType()),
    StructField("texto_fonte_confere_prefixo", BooleanType()),
    StructField("competencia", StringType(), nullable=False),
])

_direita = re.compile(r"\s+$")


@dataclass(frozen=True)
class EspecieResultado:
    """O resultado de publicar_especie: nunca um booleano solto."""

    estado: str
    competencia: str
    motivo: str = ""
    diferencas: Tuple[dict, ...] = ()
    linhas: Optional[DataFrame] = None
    versao_silver: Optional[int] = None
    gravacao: Optional[dict] = None
    controles: Dict[str, int] = field(default_factory=dict)


def _sem_direita(texto: Optional[str]) -> str:
    return _direita.sub("", texto or "")


def confere_prefixo(descricao_fonte: Optional[str], nome_oficial: str) -> bool:
    """O texto da fonte (sem espaços à direita) é os 20 primeiros caracteres do nome oficial (idem)?"""
    return _sem_direita(descricao_fonte) == _sem_direita((nome_oficial or "")[:LARGURA_DO_TEXTO_DA_FONTE])


def _versao_do_destino(spark: SparkSession, destino: str) -> Optional[int]:
    return bronze._versao_atual(spark, destino) if _e_delta(spark, destino) else None


def _e_delta(spark: SparkSession, caminho: str) -> bool:
    from delta.tables import DeltaTable

    try:
        return DeltaTable.isDeltaTable(spark, caminho)
    except Exception:  # noqa: BLE001 — caminho ilegível é o mesmo que ausente para esta pergunta
        return False


def conferir_silver(ontologia, pares: List[Tuple[str, Optional[str]]]) -> Tuple[str, List[dict]]:
    """Confere os pares (codigo, descricao) da competência contra a ontologia. ('', []) quando fecha.

    Devolve o PRIMEIRO motivo pela ordem de gravidade e todas as diferenças nomeadas, com os códigos.
    """
    if not pares:
        return NAO_MEDIDO, []
    oficiais = {e["codigo"] for e in ontologia.especies}
    da_silver = {c for c, _ in pares}
    descricoes: Dict[str, set] = {}
    for c, d in pares:
        descricoes.setdefault(c, set()).add(d)
    dif: List[dict] = []
    fora = sorted(da_silver - oficiais)
    if fora:
        dif.append(bronze._diferenca("especie", "CODIGO_FORA_DA_ONTOLOGIA", "codigo da ontologia", fora))
    ausentes = sorted(oficiais - da_silver)
    if ausentes:
        dif.append(bronze._diferenca("especie", "CODIGO_AUSENTE_DA_COMPETENCIA", "codigo na competencia", ausentes))
    varias = {c: sorted(d, key=lambda x: (x is None, x)) for c, d in sorted(descricoes.items()) if len(d) > 1}
    if varias:
        dif.append(bronze._diferenca("especie", "CODIGO_COM_MAIS_DE_UMA_DESCRICAO", "uma descricao por codigo", varias))
    return (dif[0]["identidade"] if dif else ""), dif


def calcular_especie(ontologia, pares: List[Tuple[str, Optional[str]]], competencia: str) -> List[tuple]:
    """Uma linha por código, ordenada; o texto da fonte entra COMO VEIO, espaços à direita inclusive."""
    descricao = dict(pares)
    linhas = []
    for e in sorted(ontologia.especies, key=lambda e: e["codigo"]):
        texto = descricao[e["codigo"]]
        linhas.append((e["codigo"], e["nome"], e["grupo"], texto, confere_prefixo(texto, e["nome"]), competencia))
    return linhas


def _garantir_tabela(spark: SparkSession, caminho: str) -> None:
    """Tabela criada por esta tarefa, com o seu schema — não a da Silver."""
    from delta.tables import DeltaTable

    construtor = DeltaTable.createIfNotExists(spark).location(caminho)
    for campo in SCHEMA:
        construtor = construtor.addColumn(campo.name, campo.dataType, nullable=campo.nullable)
    construtor.partitionedBy("competencia").execute()


def _versao_do_commit(spark: SparkSession, destino: str, id_execucao: str) -> Optional[int]:
    """Versão do commit cujo userMetadata nomeia o id_execucao — nunca a versão atual."""
    achadas = []
    for versao, meta in bronze._historico(spark, destino):
        try:
            corpo = json.loads(meta) if meta else None
        except ValueError:
            continue
        if isinstance(corpo, dict) and corpo.get("id_execucao") == id_execucao:
            achadas.append(versao)
    return max(achadas) if achadas else None


def reconferir_especie(
    spark: SparkSession, destino: str, id_execucao: str, esperado: DataFrame, competencia: str
) -> Tuple[bool, dict]:
    """RELÊ o destino na versão do PRÓPRIO commit e compara o multiconjunto, nos dois sentidos."""
    versao = _versao_do_commit(spark, destino, id_execucao)
    if versao is None:
        return False, {"versao": None, "motivo": "COMMIT_NAO_ACHADO", "id_execucao": id_execucao}
    lido = bronze._ler_versao(spark, destino, versao).where(F.col("competencia") == competencia).select(*COLUNAS)
    so_esperado, so_lido = bronze._diferenca_numa_passada(esperado.select(*COLUNAS), lido)
    return so_esperado == 0 and so_lido == 0, {"versao": versao, "so_no_esperado": so_esperado, "so_no_lido": so_lido}


def _ler_pares(spark: SparkSession, silver: str, competencia: str, versao: int) -> List[Tuple[str, Optional[str]]]:
    """A ÚNICA leitura da Silver, na versão fixada. O texto vai como veio."""
    lidas = (
        bronze._ler_versao(spark, silver, versao)
        .where(F.col("competencia") == competencia)
        .select("especie_codigo", "especie_descricao")
        .distinct()
        .collect()
    )
    return [(r["especie_codigo"], r["especie_descricao"]) for r in lidas]


def publicar_especie(
    spark: SparkSession,
    ontologia,
    silver: str,
    destino: str,
    competencia: str,
    id_execucao: Optional[str] = None,
) -> EspecieResultado:
    """Confere a Silver contra a ontologia, grava a competência em Delta e reconfere o gravado."""
    if not re.fullmatch(r"[A-Za-z0-9._-]+", competencia or ""):
        return EspecieResultado(ERRO_LEITURA, str(competencia), motivo="COMPETENCIA_INVALIDA")
    r = EspecieResultado(INTEGRO, competencia)
    if isinstance(ontologia, str):  # NAO_MEDIDO: sem ontologia não há nome oficial para gravar
        return replace(r, estado=NAO_MEDIDO, motivo=f"ONTOLOGIA_{getattr(ontologia, 'motivo', ontologia)}")
    id_execucao = id_execucao or uuid.uuid4().hex
    try:
        antes = _versao_do_destino(spark, destino)
        versao_silver = bronze._versao_atual(spark, silver)
        r = replace(r, versao_silver=versao_silver)
        pares = _ler_pares(spark, silver, competencia, versao_silver)
        motivo, dif = conferir_silver(ontologia, pares)
        if motivo:
            estado = NAO_MEDIDO if motivo == NAO_MEDIDO else DIVERGE
            detalhe = "SILVER_SEM_LINHAS_NA_COMPETENCIA" if estado == NAO_MEDIDO else motivo
            return replace(
                r, estado=estado, diferencas=tuple(dif), controles={"linhas_da_silver": len(pares)},
                motivo=f"{detalhe}: destino sem versão nova (versão {antes})",
            )
        calculadas = calcular_especie(ontologia, pares, competencia)
        linhas = spark.createDataFrame(calculadas, SCHEMA)
        _garantir_tabela(spark, destino)
        existia = bronze._competencia_existe(spark, destino, competencia)
        anterior = bronze._versao_atual(spark, destino)
        meta = {
            "estado": INTEGRO,
            "competencia": competencia,
            "versao_silver": versao_silver,
            "ontologia_sha256": ontologia.sha256,
            "id_execucao": id_execucao,
        }
        bronze.publicar_competencia(spark, linhas, destino, competencia, meta)
        ok, detalhe = reconferir_especie(spark, destino, id_execucao, linhas, competencia)
        if not ok:
            bronze._reverter_competencia(spark, destino, competencia, existia, anterior, meta)
            d = bronze._diferenca("gravacao", "reconferencia_publicada:especie", "multiconjunto igual",
                                  json.dumps(detalhe, default=str))
            return replace(r, estado=DIVERGE, motivo="DIVERGE", diferencas=(d,))
        lidas = bronze._ler_versao(spark, destino, detalhe["versao"]).where(F.col("competencia") == competencia)
        return replace(
            r,
            linhas=lidas.select(*COLUNAS),
            gravacao={"destino": destino, "versao": detalhe["versao"], "id_execucao": id_execucao},
            controles={"linhas": len(pares), "com_prefixo": sum(1 for x in calculadas if x[4])},
        )
    except Exception as exc:  # noqa: BLE001 — não conseguiu medir: não é NAO_MEDIDO
        return replace(r, estado=ERRO_LEITURA, motivo=f"{type(exc).__name__}: {exc}", linhas=None)


# ---------------------------------------------------------------- nomes lidos da Bronze do dicionário


class ConformacaoRecusada(Exception):
    """O dicionário da Bronze não se conforma — recusado, nunca gravado pela metade."""

    def __init__(self, motivo: str):
        super().__init__(motivo)
        self.motivo = motivo


def conformar_dicionario(
    registros: List[Tuple[Optional[str], Optional[str]]],
) -> Tuple[Dict[str, Optional[str]], Dict[str, int]]:
    """{codigo de 2 dígitos: nome oficial COMO VEIO} e os descartes contados. Levanta ConformacaoRecusada.

    Linha com as duas células vazias é descartada (`vazias`); linha com coluna_a não numérica é o
    cabeçalho (`cabecalho`). Dois códigos que colidem depois de conformados recusam — nenhum é escolhido.
    """
    nomes: Dict[str, Optional[str]] = {}
    origem: Dict[str, List[str]] = {}
    descartes = {"cabecalho": 0, "vazias": 0}
    for a, b in registros:
        bruto = (a or "").strip()
        if not bruto and not (b or "").strip():
            descartes["vazias"] += 1
        elif not bruto.isdigit():
            descartes["cabecalho"] += 1
        else:
            codigo = bruto.zfill(2)
            origem.setdefault(codigo, []).append(bruto)
            nomes[codigo] = b
    colididos = {c: v for c, v in sorted(origem.items()) if len(v) > 1}
    if colididos:
        raise ConformacaoRecusada(f"CODIGO_COLIDIDO: {colididos}")
    return nomes, descartes


def _ler_dicionario(spark: SparkSession, caminho: str, versao: int, sha: str) -> List[Tuple[Optional[str], Optional[str]]]:
    """A ÚNICA leitura da Bronze do dicionário: a versão fixada, SÓ o sha256 pedido, na ordem das linhas."""
    lidas = (
        bronze._ler_versao(spark, caminho, versao)
        .where(F.col("sha256_arquivo") == sha)
        .orderBy("linha")
        .select("coluna_a", "coluna_b")
        .collect()
    )
    return [(r["coluna_a"], r["coluna_b"]) for r in lidas]


def publicar_especie_da_bronze(
    spark: SparkSession,
    bronze_dicionario: str,
    sha256: str,
    sha256_aprovado: str,
    silver: str,
    destino: str,
    competencia: str,
    grupos,
    id_execucao: Optional[str] = None,
) -> EspecieResultado:
    """Como publicar_especie, mas o nome oficial vem da Bronze do dicionário e o grupo do contrato.

    `grupos` é contrato.grupos_especie. sha256 diferente do aprovado recusa SEM ler nem gravar;
    sha256 ausente da Bronze é NAO_MEDIDO; código colidido recusa SEM gravar.
    """
    if not re.fullmatch(r"[A-Za-z0-9._-]+", competencia or ""):
        return EspecieResultado(ERRO_LEITURA, str(competencia), motivo="COMPETENCIA_INVALIDA")
    r = EspecieResultado(INTEGRO, competencia)
    if sha256 != sha256_aprovado:
        return replace(r, estado=RECUSADO, motivo="DICIONARIO_NAO_APROVADO")
    if grupos is None:
        return replace(r, estado=NAO_MEDIDO, motivo="SEM_GRUPOS_ESPECIE")
    id_execucao = id_execucao or uuid.uuid4().hex
    try:
        if not _e_delta(spark, bronze_dicionario):
            return replace(r, estado=NAO_MEDIDO, motivo="BRONZE_AUSENTE")
        versao_bronze = bronze._versao_atual(spark, bronze_dicionario)
        registros = _ler_dicionario(spark, bronze_dicionario, versao_bronze, sha256)
        if not registros:
            return replace(r, estado=NAO_MEDIDO, motivo="SHA256_AUSENTE_DA_BRONZE")
        try:
            nomes, descartes = conformar_dicionario(registros)
        except ConformacaoRecusada as exc:
            return replace(r, estado=RECUSADO, motivo=exc.motivo)
        if not nomes:
            return replace(r, estado=NAO_MEDIDO, motivo="NENHUMA_ESPECIE", controles=dict(descartes))
        grupo_de = {c: g.grupo for g in grupos.grupos for c in g.codigos}
        ontologia = SimpleNamespace(
            especies=[{"codigo": c, "nome": n, "grupo": grupo_de.get(c)} for c, n in sorted(nomes.items())]
        )

        antes = _versao_do_destino(spark, destino)
        versao_silver = bronze._versao_atual(spark, silver)
        r = replace(r, versao_silver=versao_silver)
        pares = _ler_pares(spark, silver, competencia, versao_silver)
        motivo, dif = conferir_silver(ontologia, pares)
        if motivo:
            estado = NAO_MEDIDO if motivo == NAO_MEDIDO else DIVERGE
            detalhe = "SILVER_SEM_LINHAS_NA_COMPETENCIA" if estado == NAO_MEDIDO else motivo
            return replace(
                r, estado=estado, diferencas=tuple(dif), controles={"linhas_da_silver": len(pares)},
                motivo=f"{detalhe}: destino sem versão nova (versão {antes})",
            )
        calculadas = calcular_especie(ontologia, pares, competencia)
        linhas = spark.createDataFrame(calculadas, SCHEMA)
        _garantir_tabela(spark, destino)
        existia = bronze._competencia_existe(spark, destino, competencia)
        anterior = bronze._versao_atual(spark, destino)
        meta = {
            "estado": INTEGRO,
            "competencia": competencia,
            "versao_silver": versao_silver,
            "versao_bronze_dicionario": versao_bronze,
            "sha256_arquivo": sha256,
            "descartes": descartes,
            "id_execucao": id_execucao,
        }
        bronze.publicar_competencia(spark, linhas, destino, competencia, meta)
        ok, detalhe = reconferir_especie(spark, destino, id_execucao, linhas, competencia)
        if not ok:
            bronze._reverter_competencia(spark, destino, competencia, existia, anterior, meta)
            d = bronze._diferenca("gravacao", "reconferencia_publicada:especie", "multiconjunto igual",
                                  json.dumps(detalhe, default=str))
            return replace(r, estado=DIVERGE, motivo="DIVERGE", diferencas=(d,))
        lidas = bronze._ler_versao(spark, destino, detalhe["versao"]).where(F.col("competencia") == competencia)
        return replace(
            r,
            linhas=lidas.select(*COLUNAS),
            gravacao={"destino": destino, "versao": detalhe["versao"], "id_execucao": id_execucao},
            controles={
                "linhas": len(pares), "com_prefixo": sum(1 for x in calculadas if x[4]),
                "descartes_cabecalho": descartes["cabecalho"], "descartes_vazias": descartes["vazias"],
            },
        )
    except Exception as exc:  # noqa: BLE001 — não conseguiu medir: não é NAO_MEDIDO
        return replace(r, estado=ERRO_LEITURA, motivo=f"{type(exc).__name__}: {exc}", linhas=None)
