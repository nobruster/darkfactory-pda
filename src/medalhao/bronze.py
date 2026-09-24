"""Bronze: lê a partição do lago, confere contra a âncora e só então grava em Delta.

A camada recusa nascer sobre dado que não bate. Quatro estados, distintos:

- INTEGRO       os cinco controles batem, o lago fecha, nenhum defeito de domínio
- DIVERGE       mediu e não bate — em qualquer controle, no hash, no fechamento
- NAO_MEDIDO    partição ausente ou vazia, ou contrato sem o que Bronze exige
- ERRO_LEITURA  não conseguiu medir (listagem, objeto, esquema, tipo float)

NAO_MEDIDO e ERRO_LEITURA não se colapsam: não conseguir listar não prova que
a partição está ausente. Só INTEGRO grava.

O que governa a aritmética é o DecimalType do acumulador, declarado a partir
da politica_decimal do contrato, com spark.sql.ansi.enabled=true declarado:
fora do modo ANSI o estouro devolve NULL sem erro. O Context do Python vale
só para o que roda fora do motor, e é construído INTEIRO a partir do contrato.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field, replace
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from typing import Any, Callable, Dict, List, Optional, Tuple

from pyspark import StorageLevel
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType, StringType, StructType

from pda import juizo

INTEGRO = "INTEGRO"
DIVERGE = "DIVERGE"
NAO_MEDIDO = "NAO_MEDIDO"
ERRO_LEITURA = "ERRO_LEITURA"

PROCEDENCIA_NAO_VINCULADA = "PROCEDENCIA_NAO_VINCULADA"

CONTROLES = juizo.CONTROLES
CLASSIFICACOES = (
    juizo.CONFIRMED_SOURCE_DEFECT,
    juizo.CONFIRMED_LEGACY_DEFECT,
    juizo.APPROVED_BEHAVIOR_CHANGE,
    juizo.MODERN_DEFECT,
    juizo.CONTRACT_AMBIGUITY,
    juizo.UNRESOLVED,
)

# Nomes MEDIDOS no lago (gravar_lago.py) — Silver consome pelos mesmos nomes.
COLUNAS = ("especie_codigo", "especie_descricao", "vl_liquido", "competencia")

DESTINO_PADRAO = "s3a://bronze/pda/beneficios-emitidos"
PREPARO_PADRAO = "s3a://bronze/_preparo/pda/beneficios-emitidos"

CHAVE_NULA_DO_SPARK = "__HIVE_DEFAULT_PARTITION__"
LIMITE_DEFEITOS_LISTADOS = 1000


class EvolucaoRecusada(Exception):
    """Evolução de schema que não é só aditiva e explícita — mudança de tipo, sobretudo monetário."""


@dataclass(frozen=True)
class BronzeConferido:
    """A capacidade 'bronze conferido' — com forma, não só nome."""

    estado: str
    competencia: str
    controles: Dict[str, Any] = field(default_factory=dict)
    total_por_codigo: Dict[str, Decimal] = field(default_factory=dict)
    marcas: Tuple[str, ...] = ()
    hash_procedencia: Optional[str] = None
    linhas: Optional[DataFrame] = None
    diferencas: Tuple[dict, ...] = ()
    defeitos: Tuple[dict, ...] = ()
    particoes: Dict[str, int] = field(default_factory=dict)
    fechamento: Optional[dict] = None
    motivo: str = ""
    gravacao: Optional[dict] = None
    cache: Optional[DataFrame] = field(default=None, repr=False, compare=False)

    @property
    def controles_divergentes(self) -> Tuple[str, ...]:
        return tuple(d["identidade"] for d in self.diferencas if d.get("tipo") == "controle")


# ---------------------------------------------------------------- sessão


# 6g é o valor com que as baselines de perf/ foram medidas (Bronze de 506s para 374s de
# executor); o 1g de antes estourava a suíte. Declarado aqui, no builder — nunca em
# PYSPARK_SUBMIT_ARGS ou spark-defaults.
MEMORIA_DRIVER_PADRAO = "6g"
ADAPTATIVO_PADRAO = True
PARTICOES_SHUFFLE_PADRAO = 8
# O heap efetivo (maxMemory) fica abaixo do -Xmx: a JVM desconta um espaço de sobrevivente.
FOLGA_DO_HEAP = 0.85


class SessaoRecusada(RuntimeError):
    """A sessão criada não tem o que o código declarou — não se roda sobre memória herdada."""


def _bytes_de(memoria: str) -> int:
    m = re.fullmatch(r"(\d+)([kmgt]?)b?", str(memoria).strip().lower())
    if not m:
        raise ValueError(f"memória ilegível: {memoria!r}")
    return int(m.group(1)) * 1024 ** ("kmgt".index(m.group(2)) + 1 if m.group(2) else 0)


def heap_efetivo(spark: SparkSession) -> int:
    """O heap que a JVM TEM — a propriedade de configuração não prova nada numa JVM já iniciada."""
    return int(spark._jvm.java.lang.Runtime.getRuntime().maxMemory())


def criar_sessao(
    nome: str = "bronze",
    memoria_driver: str = MEMORIA_DRIVER_PADRAO,
    adaptativo: bool = ADAPTATIVO_PADRAO,
    particoes_shuffle: int = PARTICOES_SHUFFLE_PADRAO,
) -> SparkSession:
    import os

    construtor = (
        SparkSession.builder.appName(nome)
        .config("spark.driver.memory", memoria_driver)
        .config("spark.sql.adaptive.enabled", str(bool(adaptativo)).lower())
        .config("spark.sql.shuffle.partitions", str(int(particoes_shuffle)))
        .config("spark.sql.ansi.enabled", "true")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    )
    if os.environ.get("S3_ENDPOINT"):
        construtor = (
            construtor.config("spark.hadoop.fs.s3a.endpoint", os.environ["S3_ENDPOINT"])
            .config("spark.hadoop.fs.s3a.access.key", os.environ["S3_ACCESS_KEY"])
            .config("spark.hadoop.fs.s3a.secret.key", os.environ["S3_SECRET_KEY"])
            .config("spark.hadoop.fs.s3a.path.style.access", "true")
            .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
            .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
            .config(
                "spark.hadoop.fs.s3a.aws.credentials.provider",
                "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
            )
        )
    spark = construtor.getOrCreate()
    spark.conf.set("spark.sql.ansi.enabled", "true")
    spark.conf.set("spark.sql.adaptive.enabled", str(bool(adaptativo)).lower())
    spark.conf.set("spark.sql.shuffle.partitions", str(int(particoes_shuffle)))
    spark.sparkContext.setLogLevel("WARN")
    efetivo, declarado = heap_efetivo(spark), _bytes_de(memoria_driver)
    if efetivo < declarado * FOLGA_DO_HEAP:
        raise SessaoRecusada(f"heap efetivo {efetivo} < declarado {declarado} ({memoria_driver})")
    return spark


def contexto_declarado(politica) -> Context:
    """Context construído INTEIRO do contrato — nunca herdado do global, que é mutável."""
    return Context(
        prec=politica.precisao,
        rounding=ROUND_HALF_EVEN,
        traps=[],
        Emax=politica.emax,
        Emin=politica.emin,
    )


def tipo_acumulador(politica) -> DecimalType:
    return DecimalType(politica.precisao, politica.escala)


# ---------------------------------------------------------------- classificação


def classificar(identidade: str, propostas: Tuple[str, ...] = ()) -> str:
    """Exatamente UMA das seis. O que a camada não sabe classificar é UNRESOLVED, que bloqueia."""
    if len(propostas) == 1 and propostas[0] in CLASSIFICACOES:
        return propostas[0]
    return juizo.UNRESOLVED


def bloqueia(classificacao: str) -> bool:
    return classificacao in juizo.CLASSIFICACOES_QUE_BLOQUEIAM


def _diferenca(tipo: str, identidade: str, esperado: Any, observado: Any, **extra) -> dict:
    return {
        "tipo": tipo,
        "identidade": identidade,
        "esperado": None if esperado is None else str(esperado),
        "observado": None if observado is None else str(observado),
        "classificacao": classificar(identidade),
        **extra,
    }


# ---------------------------------------------------------------- listagem do lago


def _listar_objetos(spark: SparkSession, raiz: str) -> List[Tuple[str, str]]:
    """(uri, caminho relativo à raiz) de TODO objeto sob a raiz — o universo independente."""
    jvm = spark._jvm
    caminho = jvm.org.apache.hadoop.fs.Path(raiz)
    fs = caminho.getFileSystem(spark._jsc.hadoopConfiguration())
    if not fs.exists(caminho):
        return []
    base = caminho.toUri().getPath().rstrip("/")
    achados = []
    it = fs.listFiles(caminho, True)
    while it.hasNext():
        p = it.next().getPath()
        relativo = p.toUri().getPath()[len(base):].lstrip("/")
        achados.append((p.toString(), relativo))
    return sorted(achados, key=lambda t: t[1])


def _e_dado(relativo: str, ignorados: Tuple[str, ...]) -> bool:
    nome = relativo.rsplit("/", 1)[-1]
    return not (nome in ignorados or nome.startswith("_") or nome.startswith("."))


NOME_PROVA = "_PROCEDENCIA.json"


class ProvaInvalida(Exception):
    """`_PROCEDENCIA.json` existe mas não é uma prova legível."""


def _fs_e_caminho(spark: SparkSession, uri: str):
    caminho = spark._jvm.org.apache.hadoop.fs.Path(uri)
    fs = caminho.getFileSystem(spark._jsc.hadoopConfiguration())
    # o sha256 do manifesto é a verificação; o .crc do FS local levantaria
    # ChecksumException em vez de deixar o manifesto acusar a diferença
    fs.setVerifyChecksum(False)
    return fs, caminho


def _sha256_e_tamanho(spark: SparkSession, uri: str) -> Tuple[str, int]:
    jvm = spark._jvm
    fs, caminho = _fs_e_caminho(spark, uri)
    resumo = jvm.java.security.MessageDigest.getInstance("SHA-256")
    saida = jvm.java.security.DigestOutputStream(jvm.java.io.OutputStream.nullOutputStream(), resumo)
    entrada = fs.open(caminho)
    try:
        jvm.org.apache.hadoop.io.IOUtils.copyBytes(entrada, saida, 65536, False)
    finally:
        entrada.close()
    return bytes(resumo.digest()).hex(), int(fs.getFileStatus(caminho).getLen())


def _ler_prova(spark: SparkSession, uri: str) -> dict:
    jvm = spark._jvm
    fs, caminho = _fs_e_caminho(spark, uri)
    saida = jvm.java.io.ByteArrayOutputStream()
    entrada = fs.open(caminho)
    try:
        jvm.org.apache.hadoop.io.IOUtils.copyBytes(entrada, saida, 65536, False)
    finally:
        entrada.close()
    try:
        prova = json.loads(bytes(saida.toByteArray()).decode("utf-8"))
    except ValueError as exc:
        raise ProvaInvalida(f"{NOME_PROVA} não é JSON: {exc}") from exc
    if not isinstance(prova, dict):
        raise ProvaInvalida(f"{NOME_PROVA} não é um objeto JSON")
    for chave, tipo in (("competencia", str), ("csv_sha256", str), ("manifesto", list), ("controles", dict)):
        if not isinstance(prova.get(chave), tipo):
            raise ProvaInvalida(f"{NOME_PROVA} sem '{chave}' válido")
    if not all(isinstance(o, dict) and isinstance(o.get("nome"), str) for o in prova["manifesto"]):
        raise ProvaInvalida(f"{NOME_PROVA} com manifesto malformado")
    return prova


def _manifesto_observado(
    spark: SparkSession, objetos: List[Tuple[str, str]], prefixo: str, ignorados: Tuple[str, ...]
) -> Dict[str, dict]:
    """Todo objeto sob a partição EXCETO os auxiliares nomeados e a prova — um a um, nunca por prefixo `_`."""
    isentos = set(ignorados) | {NOME_PROVA}
    observado: Dict[str, dict] = {}
    for uri, rel in objetos:
        if not rel.startswith(prefixo):
            continue
        nome = rel[len(prefixo):]
        if nome in isentos:
            continue
        sha, tamanho = _sha256_e_tamanho(spark, uri)
        observado[nome] = {"nome": nome, "tamanho": tamanho, "sha256": sha}
    return observado


def _numero(valor: Any) -> Optional[Decimal]:
    if valor is None or valor == "":
        return None
    try:
        return Decimal(str(valor))
    except ArithmeticError:
        return None


def _diferencas_da_prova(
    prova: dict, observado: Dict[str, dict], controles: Dict[str, Any], contrato, competencia: str
) -> List[dict]:
    difs: List[dict] = []
    if prova["csv_sha256"] != contrato.procedencia.hash_csv_sha256:
        difs.append(
            _diferenca("procedencia", "hash_csv_sha256", contrato.procedencia.hash_csv_sha256, prova["csv_sha256"])
        )
    if prova["competencia"] != competencia or prova["competencia"] != contrato.competencia:
        difs.append(_diferenca("procedencia", "competencia", competencia, prova["competencia"]))

    listado = {o["nome"]: o for o in prova["manifesto"]}
    for nome in sorted(listado.keys() | observado.keys()):
        if nome not in listado:
            difs.append(_diferenca("procedencia", f"manifesto:{nome}", None, "objeto a mais"))
        elif nome not in observado:
            difs.append(_diferenca("procedencia", f"manifesto:{nome}", "listado", "objeto a menos"))
        else:
            for campo in ("tamanho", "sha256"):
                if listado[nome].get(campo) != observado[nome][campo]:
                    difs.append(
                        _diferenca(
                            "procedencia", f"manifesto:{nome}:{campo}", listado[nome].get(campo), observado[nome][campo]
                        )
                    )

    gravados = prova["controles"]
    for nome in CONTROLES:
        medido = controles.get(nome)
        if nome == "sum_vl_liquido" and medido is None:
            medido = Decimal(0)
        esperado = _numero(gravados.get(nome))
        if esperado is None or _numero(medido) != esperado:
            difs.append(_diferenca("procedencia", f"controle_da_prova:{nome}", gravados.get(nome), medido))
    return difs


def _valor_da_particao(relativo: str, chave: str) -> Optional[str]:
    partes = relativo.split("/")
    if len(partes) >= 2 and partes[0].startswith(f"{chave}="):
        return partes[0][len(chave) + 1:]
    return None


def _ler_parquet(spark: SparkSession, arquivos: List[str]) -> DataFrame:
    return spark.read.option("mergeSchema", "true").parquet(*arquivos)


def _motivo_de_esquema(schema: StructType) -> Optional[str]:
    """Recusa pelo TIPO declarado, antes de ler valor algum. Float nunca é convertido."""
    nomes = {f.name: f.dataType for f in schema}
    faltam = [c for c in COLUNAS[:3] if c not in nomes]
    if faltam:
        return f"ESQUEMA_INESPERADO: faltam {', '.join(faltam)}"
    if not isinstance(nomes["vl_liquido"], DecimalType):
        return (
            f"RECUSA_TIPO_MONETARIO: vl_liquido veio como {nomes['vl_liquido'].simpleString()} "
            "— dinheiro é decimal, float é recusado e nunca convertido"
        )
    return None


# ---------------------------------------------------------------- controles no motor


def _valido(politica):
    v = F.col("vl_liquido")
    return (
        F.col("especie_codigo").isNotNull()
        & v.isNotNull()
        & (v >= 0)
        & (v == F.round(v, politica.escala))
    )


def medir_controles(df: DataFrame, politica) -> Tuple[Dict[str, Any], Dict[str, Decimal]]:
    """Os cinco controles e o mapa por código, NO MOTOR — só os agregados saem dele."""
    acc = tipo_acumulador(politica)
    valido = _valido(politica)
    valor = F.when(valido, F.col("vl_liquido").cast(acc))
    a = df.agg(
        F.count(F.lit(1)).alias("n"),
        F.sum(F.when(valido, 0).otherwise(1)).alias("invalidas"),
        F.sum(valor).alias("soma"),
        F.min(valor).alias("minimo"),
        F.max(valor).alias("maximo"),
    ).collect()[0]
    controles = {
        "count_linhas": int(a["n"]),
        "linhas_invalidas": int(a["invalidas"] or 0),
        "sum_vl_liquido": a["soma"],
        "min_vl_liquido": a["minimo"],
        "max_vl_liquido": a["maximo"],
    }
    por_codigo = {
        r["especie_codigo"]: r["total"]
        for r in df.where(valido)
        .groupBy("especie_codigo")
        .agg(F.sum(F.col("vl_liquido").cast(acc)).alias("total"))
        .collect()
    }
    return controles, por_codigo


def _controles_iguais(observado: Dict[str, Any], esperado: Dict[str, Any], politica) -> Tuple[str, ...]:
    """Igualdade EXATA — tolerância aqui seria afrouxar o oráculo."""
    with localcontext(contexto_declarado(politica)):
        return tuple(c for c in CONTROLES if observado.get(c) != esperado.get(c))


def _defeitos_de_dominio(spark: SparkSession, arquivos: List[str], politica) -> Tuple[int, List[dict]]:
    """Identidade, valor original e posição NO LAGO (objeto + ordinal) — nunca a linha do CSV."""
    valido = _valido(politica)
    base = _ler_parquet(spark, arquivos)
    objetos = sorted(
        r["o"]
        for r in base.where(~valido).select(F.input_file_name().alias("o")).distinct().collect()
    )
    defeitos: List[dict] = []
    total = 0
    for objeto in objetos:
        numerado = (
            spark.read.parquet(objeto).coalesce(1).withColumn("_ordinal", F.monotonically_increasing_id())
        )
        for r in numerado.where(~valido).collect():
            total += 1
            if len(defeitos) >= LIMITE_DEFEITOS_LISTADOS:
                continue
            valor = r["vl_liquido"]
            if r["especie_codigo"] is None:
                tipo = "CODIGO_NULO"
            elif valor is None:
                tipo = "VALOR_NULO"
            elif valor < 0:
                tipo = "VALOR_NEGATIVO"
            else:
                tipo = "VALOR_FORA_DA_ESCALA"
            nome = objeto.rsplit("/", 1)[-1]
            ordinal = int(r["_ordinal"])
            defeitos.append(
                {
                    "tipo": "dominio",
                    "identidade": f"dominio:{tipo}:{nome}#{ordinal}",
                    "defeito": tipo,
                    "valor_original": None if valor is None else str(valor),
                    "posicao_lago": {"objeto": nome, "ordinal": ordinal},
                    "classificacao": classificar(tipo),
                }
            )
    return total, defeitos


# ---------------------------------------------------------------- Delta


def _delta_table(spark: SparkSession, caminho: str):
    from delta.tables import DeltaTable

    return DeltaTable.forPath(spark, caminho)


def _garantir_tabela(spark: SparkSession, caminho: str, politica) -> None:
    """Tabela com o DecimalType do contrato, NOT NULL nas chaves e CHECK >= 0 no dinheiro."""
    from delta.tables import DeltaTable

    (
        DeltaTable.createIfNotExists(spark)
        .location(caminho)
        .addColumn("especie_codigo", StringType(), nullable=False)
        .addColumn("especie_descricao", StringType())
        .addColumn("vl_liquido", tipo_acumulador(politica))
        .addColumn("competencia", StringType(), nullable=False)
        .partitionedBy("competencia")
        .execute()
    )
    propriedades = _delta_table(spark, caminho).detail().select("properties").first()[0] or {}
    if "delta.constraints.vl_nao_negativo" not in propriedades:
        spark.sql(f"ALTER TABLE delta.`{caminho}` ADD CONSTRAINT vl_nao_negativo CHECK (vl_liquido >= 0)")


def _versao_atual(spark: SparkSession, caminho: str) -> int:
    return int(_delta_table(spark, caminho).history(1).select("version").first()[0])


def _historico(spark: SparkSession, caminho: str) -> List[Tuple[int, Optional[str]]]:
    linhas = _delta_table(spark, caminho).history().select("version", "userMetadata").collect()
    return [(int(r["version"]), r["userMetadata"]) for r in linhas]


def _ler_versao(spark: SparkSession, caminho: str, versao: int) -> DataFrame:
    return spark.read.format("delta").option("versionAsOf", versao).load(caminho)


def verificar_evolucao(schema_atual: StructType, schema_novo: StructType) -> Tuple[str, ...]:
    """Só ADITIVA: coluna nova passa; mudança de tipo de coluna existente é recusada."""
    atual = {f.name: f.dataType for f in schema_atual}
    for campo in schema_novo:
        if campo.name in atual and atual[campo.name] != campo.dataType:
            raise EvolucaoRecusada(
                f"{campo.name}: {atual[campo.name].simpleString()} -> {campo.dataType.simpleString()} "
                "— mudança de tipo é recusada"
            )
    return tuple(f.name for f in schema_novo if f.name not in atual)


def publicar_competencia(
    spark: SparkSession,
    linhas: DataFrame,
    destino: str,
    competencia: str,
    metadados: dict,
    evolucao_aditiva: bool = False,
) -> None:
    """Overwrite com replaceWhere na competência — atômico, idempotente, não toca as outras."""
    novas = verificar_evolucao(spark.read.format("delta").load(destino).schema, linhas.schema)
    if novas and not evolucao_aditiva:
        raise EvolucaoRecusada(f"colunas novas {novas} exigem evolução aditiva explícita (mergeSchema)")
    escritor = (
        linhas.write.format("delta")
        .mode("overwrite")
        .option("replaceWhere", f"competencia = '{competencia}'")
        .option("userMetadata", json.dumps(metadados, ensure_ascii=False, sort_keys=True))
    )
    if novas:
        escritor = escritor.option("mergeSchema", "true")
    escritor.save(destino)


def _gravar_preparo(spark: SparkSession, linhas: DataFrame, preparo: str, competencia: str, metadados: dict):
    publicar_competencia(spark, linhas, preparo, competencia, metadados)


def _competencia_existe(spark: SparkSession, destino: str, competencia: str) -> bool:
    return spark.read.format("delta").load(destino).where(F.col("competencia") == competencia).limit(1).count() > 0


def _diferenca_numa_passada(esperado: DataFrame, lido: DataFrame) -> Tuple[int, int]:
    """(só no esperado, só no lido) com UM exceptAll e as contagens.

    |B−A| = |B| − |A| + |A−B|: os mesmos dois números que os dois exceptAll davam.
    Multiconjuntos de mesmo tamanho em que um está contido no outro são iguais.
    """
    so_esperado = esperado.exceptAll(lido).count()
    return so_esperado, lido.count() - esperado.count() + so_esperado


def _liberar(*dfs) -> None:
    for df in dfs:
        if df is not None:
            df.unpersist()


def _conferir_tabela(
    spark: SparkSession, caminho: str, versao: int, esperado: DataFrame, controles: Dict[str, Any],
    competencia: str, politica, total_por_codigo: Optional[Dict[str, Decimal]] = None,
) -> Tuple[bool, dict]:
    """RELÊ a versão commitada e compara o MULTICONJUNTO de todas as colunas, nos dois sentidos.

    Trocar 10 e 20 por 11 e 19 preserva os cinco controles; exceptAll não.
    """
    cols = list(COLUNAS)
    lido = _ler_versao(spark, caminho, versao).where(F.col("competencia") == competencia).select(*cols)
    so_esperado, so_lido = _diferenca_numa_passada(esperado.select(*cols), lido)
    observados, por_codigo = medir_controles(lido, politica)
    divergentes = _controles_iguais(observados, controles, politica)
    if total_por_codigo is not None and por_codigo != total_por_codigo:
        divergentes = divergentes + ("total_por_codigo",)
    detalhe = {
        "versao": versao,
        "so_no_esperado": so_esperado,
        "so_no_lido": so_lido,
        "controles_divergentes": divergentes,
    }
    return (so_esperado == 0 and so_lido == 0 and not divergentes), detalhe


def _reverter_competencia(
    spark: SparkSession, destino: str, competencia: str, existia: bool, versao_anterior: int, meta: dict
) -> None:
    """Reverte SÓ a competência — nunca a tabela inteira, que desfaria outra competência."""
    condicao = f"competencia = '{competencia}'"
    meta_json = json.dumps({**meta, "estado": "REVERTIDO"}, ensure_ascii=False, sort_keys=True)
    if existia:
        anterior = _ler_versao(spark, destino, versao_anterior).where(F.col("competencia") == competencia)
        (
            anterior.write.format("delta").mode("overwrite")
            .option("replaceWhere", condicao)
            .option("userMetadata", meta_json)
            .save(destino)
        )
        return
    chave = "spark.databricks.delta.commitInfo.userMetadata"
    spark.conf.set(chave, meta_json)
    try:
        _delta_table(spark, destino).delete(condicao)
    finally:
        spark.conf.unset(chave)


def ler_competencia_publicada(spark: SparkSession, destino: str, competencia: str):
    """Resolve a versão V UMA vez; dados em V, metadados do ÚLTIMO commit até V que nomeia a competência.

    Nunca os metadados do commit V em si, que pode ser de outra competência.
    """
    historico = _historico(spark, destino)
    versao = max(v for v, _ in historico)
    dono = None
    for v, meta in sorted(historico, key=lambda t: t[0], reverse=True):
        if v > versao or not meta:
            continue
        try:
            corpo = json.loads(meta)
        except ValueError:
            continue
        if isinstance(corpo, dict) and corpo.get("competencia") == competencia:
            dono = corpo
            break
    dados = _ler_versao(spark, destino, versao).where(F.col("competencia") == competencia)
    return dados, dono, versao


def _metadados_do_commit(r: BronzeConferido, id_execucao: str, versao_camada_anterior) -> dict:
    return {
        "estado": r.estado,
        "competencia": r.competencia,
        "hash_procedencia": r.hash_procedencia,
        "controles": {k: (None if v is None else str(v)) for k, v in r.controles.items()},
        "marcas": list(r.marcas),
        "defeitos": [d["identidade"] for d in r.defeitos],
        "total_por_codigo": {str(k): str(v) for k, v in sorted(r.total_por_codigo.items())},
        "cobertura_referencial": None,
        "id_execucao": id_execucao,
        "versao_camada_anterior": versao_camada_anterior,
    }


# ---------------------------------------------------------------- leitura


def _nao_medido(competencia: str, motivo: str, **kw) -> BronzeConferido:
    return BronzeConferido(estado=NAO_MEDIDO, competencia=competencia, motivo=motivo, **kw)


def _erro(competencia: str, motivo: str) -> BronzeConferido:
    return BronzeConferido(estado=ERRO_LEITURA, competencia=competencia, motivo=motivo)


def _medir(spark, contrato, competencia, raiz, procedencia) -> BronzeConferido:
    part = contrato.particionamento
    pol = contrato.politica_decimal
    ignorados = tuple(part.objetos_auxiliares_ignorados)

    objetos = _listar_objetos(spark, raiz)
    dados = [(u, r) for u, r in objetos if _e_dado(r, ignorados)]
    particoes: Dict[str, List[str]] = {}
    fora: List[str] = []
    for uri, rel in dados:
        valor = _valor_da_particao(rel, part.chave)
        if valor is None or valor == CHAVE_NULA_DO_SPARK:
            fora.append(rel)
        else:
            particoes.setdefault(valor, []).append(uri)

    arquivos = particoes.get(competencia, [])
    if not arquivos:
        existe = any(r.startswith(f"{part.chave}={competencia}/") for _, r in objetos)
        return _nao_medido(competencia, "PARTICAO_VAZIA" if existe else "PARTICAO_AUSENTE")

    motivo = _motivo_de_esquema(_ler_parquet(spark, arquivos).schema)
    if motivo:
        return _erro(competencia, motivo)

    prefixo = f"{part.chave}={competencia}/"
    prova = None
    if procedencia is None and any(r == prefixo + NOME_PROVA for _, r in objetos):
        try:
            prova = _ler_prova(spark, next(u for u, r in objetos if r == prefixo + NOME_PROVA))
        except ProvaInvalida as exc:
            return _erro(competencia, f"PROCEDENCIA_JSON_INVALIDO: {exc}")

    bruto = _ler_parquet(spark, arquivos)
    base = bruto.select(
        "especie_codigo", "especie_descricao", "vl_liquido", F.lit(competencia).alias("competencia")
    ).persist(StorageLevel.MEMORY_AND_DISK)
    try:
        return _medir_persistido(
            spark, contrato, competencia, base, arquivos, particoes, dados, fora, objetos,
            prefixo, prova, procedencia, ignorados,
        )
    except BaseException:
        base.unpersist()
        raise


def _medir_persistido(
    spark, contrato, competencia, base, arquivos, particoes, dados, fora, objetos, prefixo, prova,
    procedencia, ignorados,
) -> BronzeConferido:
    pol = contrato.politica_decimal
    controles, por_codigo = medir_controles(base, pol)
    if controles["count_linhas"] == 0:
        base.unpersist()
        return _nao_medido(competencia, "PARTICAO_VAZIA")

    diferencas: List[dict] = []
    ancora = contrato.ancora
    esperado = {
        "count_linhas": ancora.count_linhas,
        "linhas_invalidas": ancora.linhas_invalidas,
        "sum_vl_liquido": ancora.sum_vl_liquido,
        "min_vl_liquido": ancora.min_vl_liquido,
        "max_vl_liquido": ancora.max_vl_liquido,
    }
    for nome in _controles_iguais(controles, esperado, pol):
        diferencas.append(_diferenca("controle", nome, esperado[nome], controles[nome]))

    defeitos: List[dict] = []
    if controles["linhas_invalidas"] > 0:
        _, defeitos = _defeitos_de_dominio(spark, arquivos, pol)

    marcas: List[str] = []
    hash_proc = None
    if prova is not None:
        hash_proc = prova["csv_sha256"]
        observado = _manifesto_observado(spark, objetos, prefixo, ignorados)
        diferencas.extend(_diferencas_da_prova(prova, observado, controles, contrato, competencia))
    elif procedencia is None:
        marcas.append(PROCEDENCIA_NAO_VINCULADA)
    else:
        hash_proc = procedencia.get("hash_csv_sha256")
        if hash_proc != contrato.procedencia.hash_csv_sha256:
            diferencas.append(
                _diferenca("procedencia", "hash_csv_sha256", contrato.procedencia.hash_csv_sha256, hash_proc)
            )

    # Fechamento: o total vem da LISTAGEM dos objetos, nunca da mesma leitura agrupada.
    contagens = {valor: int(_ler_parquet(spark, fs).count()) for valor, fs in particoes.items()}
    total = int(_ler_parquet(spark, [u for u, _ in dados]).count())
    soma = sum(contagens.values())
    fechamento = {
        "total_listado": total,
        "soma_particoes": soma,
        "fora_das_particoes": total - soma,
        "objetos_fora": sorted(fora),
        "fecha": soma == total,
    }
    if not fechamento["fecha"]:
        diferencas.append(_diferenca("fechamento", "fechamento_do_lago", total, soma))

    estado = INTEGRO if not (diferencas or defeitos) else DIVERGE
    if estado != INTEGRO:
        base.unpersist()
    return BronzeConferido(
        estado=estado,
        competencia=competencia,
        controles=controles,
        total_por_codigo=por_codigo,
        marcas=tuple(marcas),
        hash_procedencia=hash_proc,
        linhas=base.withColumn("vl_liquido", F.col("vl_liquido").cast(tipo_acumulador(pol)))
        if estado == INTEGRO
        else None,
        diferencas=tuple(diferencas),
        defeitos=tuple(defeitos),
        particoes=contagens,
        fechamento=fechamento,
        cache=base if estado == INTEGRO else None,
    )


def executar_leitura(
    spark: SparkSession,
    contrato,
    *,
    competencia: Optional[str] = None,
    procedencia: Optional[dict] = None,
    raiz: Optional[str] = None,
    gravar: bool = True,
    destino: str = DESTINO_PADRAO,
    preparo_raiz: str = PREPARO_PADRAO,
    id_execucao: Optional[str] = None,
    versao_camada_anterior: Optional[int] = None,
    evolucao_aditiva: bool = False,
) -> BronzeConferido:
    """Lê a partição SOLICITADA (nunca a raiz inteira), confere e, só se INTEGRO, grava.

    Nunca encerra o processo: o desfecho é um valor. Falha de gravação levanta —
    ela não é medição, e `conduzir` a transforma em ERRO.
    """
    competencia = competencia or contrato.competencia
    if not re.fullmatch(r"[A-Za-z0-9._-]+", competencia or ""):
        return _erro(str(competencia), "COMPETENCIA_INVALIDA")
    if contrato.competencia != competencia:
        return _nao_medido(competencia, "CONTRATO_DE_OUTRA_COMPETENCIA")
    if contrato.particionamento is None:
        return _nao_medido(competencia, "CONTRATO_SEM_PARTICIONAMENTO")
    if contrato.politica_decimal.emax is None or contrato.politica_decimal.emin is None:
        return _nao_medido(competencia, "CONTRATO_SEM_LIMITES_DE_EXPOENTE")

    spark.conf.set("spark.sql.ansi.enabled", "true")
    try:
        medido = _medir(spark, contrato, competencia, raiz or contrato.particionamento.caminho, procedencia)
    except Exception as exc:  # não conseguiu medir: não é NAO_MEDIDO
        return _erro(competencia, f"{type(exc).__name__}: {exc}")

    if medido.estado != INTEGRO or not gravar:
        return medido
    return _gravar(
        spark, contrato, medido, destino, preparo_raiz,
        id_execucao or uuid.uuid4().hex, versao_camada_anterior, evolucao_aditiva,
    )


def publicar_bronze(
    spark: SparkSession,
    contrato,
    medido: BronzeConferido,
    *,
    destino: str = DESTINO_PADRAO,
    preparo_raiz: str = PREPARO_PADRAO,
    id_execucao: Optional[str] = None,
    versao_camada_anterior: Optional[int] = None,
    evolucao_aditiva: bool = False,
    metadados_extra: Optional[dict] = None,
    julgado: Optional[dict] = None,
) -> BronzeConferido:
    """Publica um `medido` INTEGRO pelo protocolo de sempre — preparo, replaceWhere, reconferência.

    `julgado` ({"controles", "total_por_codigo"}) é o que um juízo já decidiu: as duas
    reconferências comparam contra ele, não só contra o próprio preparo.
    `metadados_extra` entra no userMetadata do commit.
    """
    if medido.estado != INTEGRO or medido.linhas is None:
        return medido
    return _gravar(
        spark, contrato, medido, destino, preparo_raiz, id_execucao or uuid.uuid4().hex,
        versao_camada_anterior, evolucao_aditiva, metadados_extra, julgado,
    )


def _gravar(
    spark, contrato, medido, destino, preparo_raiz, id_execucao, versao_camada_anterior, evolucao,
    metadados_extra=None, julgado=None,
):
    """Grava e reconfere; o cache só é liberado DEPOIS, em todo caminho (o finally)."""
    try:
        return _gravar_e_reconferir(
            spark, contrato, medido, destino, preparo_raiz, id_execucao, versao_camada_anterior, evolucao,
            metadados_extra, julgado,
        )
    finally:
        _liberar(medido.cache, medido.linhas)


def _gravar_e_reconferir(
    spark, contrato, medido, destino, preparo_raiz, id_execucao, versao_camada_anterior, evolucao,
    metadados_extra=None, julgado=None,
):
    pol = contrato.politica_decimal
    comp = medido.competencia
    meta = {**_metadados_do_commit(medido, id_execucao, versao_camada_anterior), **(metadados_extra or {})}
    controles = julgado["controles"] if julgado else medido.controles
    por_codigo = julgado["total_por_codigo"] if julgado else None
    linhas = medido.linhas.select(*COLUNAS)
    preparo = f"{preparo_raiz.rstrip('/')}/execucao={id_execucao}"

    def _diverge(identidade: str, detalhe: dict) -> BronzeConferido:
        d = _diferenca("gravacao", identidade, "multiconjunto e controles iguais", json.dumps(detalhe, default=str))
        return replace(medido, estado=DIVERGE, diferencas=medido.diferencas + (d,), linhas=None)

    _garantir_tabela(spark, preparo, pol)
    _gravar_preparo(spark, linhas, preparo, comp, meta)
    ok, detalhe = _conferir_tabela(
        spark, preparo, _versao_atual(spark, preparo), linhas, medido.controles, comp, pol
    )
    if not ok:
        return _diverge("reconferencia_no_preparo", detalhe)

    _garantir_tabela(spark, destino, pol)
    existia = _competencia_existe(spark, destino, comp)
    versao_anterior = _versao_atual(spark, destino)
    publicar_competencia(spark, linhas, destino, comp, meta, evolucao_aditiva=evolucao)
    versao = _versao_atual(spark, destino)
    ok, detalhe = _conferir_tabela(spark, destino, versao, linhas, controles, comp, pol, por_codigo)
    if not ok:
        _reverter_competencia(spark, destino, comp, existia, versao_anterior, meta)
        return _diverge("reconferencia_publicada", detalhe)

    return replace(
        medido,
        gravacao={"destino": destino, "preparo": preparo, "versao": versao, "id_execucao": id_execucao},
    )
