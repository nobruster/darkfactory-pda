"""Grava no lago e PROVA que o que está lá é o que foi julgado.

O BRD nomeou `mode("overwrite")` como defeito: *"ela destrói a execução
anterior; não há como responder meses depois o que foi publicado"*. Aqui a
gravação é **incremental** (ADR 0011), particionada por competência — e uma
partição já ocupada RECUSA a carga: nada é sobrescrito nem apagado, e a
retomada depois de uma tentativa que falhou é decisão do dono. Premissa: um
escritor por competência; se outra carga entrar entre a conferência e a
escrita, a releitura acusa DIVERGE.

A parte que importa não é gravar — é **provar**. Depois de escrever, este
script RELÊ do lago e recalcula os cinco controles. Confiar na escrita
seria o mesmo erro que o ADR 0001 rejeitou ao recusar derivar a âncora do
Parquet: medir o que o pipeline produziu, não o que ele deveria ter
produzido.

A TABELA leva todas as linhas do CSV (a de valor inválido com vl_liquido
NULL). Os rejeitos são uma CÓPIA a mais — as linhas de valor inválido, com as
colunas brutas do CSV como vieram — num diretório FORA da tabela, para a
Bronze não os ler como dado.

Token: LAGO=GRAVADO|DIVERGE|RECUSADO|ERRO
"""
import argparse
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pyspark.sql import SparkSession, functions as F  # noqa: E402
from pyspark.sql.types import StringType, StructField, StructType  # noqa: E402

from produtor import gramatica  # noqa: E402
from produtor.spark_produtor import fora_da_precisao  # noqa: E402

BUCKET = "landing"
CAMINHO = f"s3a://{BUCKET}/pda/beneficios-emitidos"
CAMINHO_REJEITOS = f"s3a://{BUCKET}/pda/beneficios-emitidos-rejeitos"

MOTIVO_REJEITO = "VALOR_FORA_DA_GRAMATICA"

_ENCODING_JVM = {
    "latin-1": "ISO-8859-1", "latin1": "ISO-8859-1",
    "iso-8859-1": "ISO-8859-1", "utf-8": "UTF-8", "utf8": "UTF-8",
}


def _sessao(nome: str) -> SparkSession:
    endpoint = os.environ["S3_ENDPOINT"]
    chave = os.environ["S3_ACCESS_KEY"]
    segredo = os.environ["S3_SECRET_KEY"]

    spark = (
        SparkSession.builder.appName(nome)
        .config("spark.sql.ansi.enabled", "true")
        .config("spark.hadoop.fs.s3a.endpoint", endpoint)
        .config("spark.hadoop.fs.s3a.access.key", chave)
        .config("spark.hadoop.fs.s3a.secret.key", segredo)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl",
                "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        .config("spark.hadoop.fs.s3a.aws.credentials.provider",
                "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


def _ler_bruto(spark, csv: Path, contrato):
    """O CSV por posição, tudo como texto — as colunas COMO VIERAM."""
    layout = contrato.layout
    schema = StructType([
        StructField(f"c{i}", StringType(), True)
        for i in range(layout.total_colunas)
    ])
    return (
        spark.read.option("header", "true")
        .option("sep", layout.separador)
        .option("encoding", _ENCODING_JVM.get(
            layout.encoding.lower(), layout.encoding))
        .schema(schema)
        .csv(str(csv))
    )


def _valor(contrato):
    """O valor pela gramática do juiz: Decimal, ou NULL se ela recusa."""
    pol = contrato.politica_decimal
    idx_valor = contrato.layout.posicoes["vl_liquido"]
    return gramatica.valor_decimal(F.col(f"c{idx_valor}"), pol.precisao, pol.escala)


def _especie_invalida(contrato):
    idx_especie = contrato.layout.posicoes["especie"]
    return ~gramatica.especie_valida(F.col(f"c{idx_especie}"))


def _projetar(bruto, contrato):
    layout = contrato.layout
    idx_especie = layout.posicoes["especie"]
    idx_descricao = layout.posicoes["descricao_especie"]
    return bruto.select(
        F.trim(F.col(f"c{idx_especie}")).alias("especie_codigo"),
        F.col(f"c{idx_descricao}").alias("especie_descricao"),
        _valor(contrato).alias("vl_liquido"),
    )


def _ler_fonte(spark, csv: Path, contrato):
    """Lê o CSV por posição, com a gramática do juiz — igual ao produtor."""
    return _projetar(_ler_bruto(spark, csv, contrato), contrato)


def _controles(df) -> dict:
    """Os cinco controles. A mesma função serve para a fonte e para o lago —
    se medisse de formas diferentes, a comparação não provaria nada."""
    a = df.agg(
        F.count(F.lit(1)).alias("count_linhas"),
        F.sum(F.when(F.col("vl_liquido").isNull(), 1).otherwise(0)).alias("invalidas"),
        F.sum("vl_liquido").alias("soma"),
        F.min("vl_liquido").alias("minimo"),
        F.max("vl_liquido").alias("maximo"),
    ).collect()[0]
    return {
        "count_linhas": int(a["count_linhas"] or 0),
        "linhas_invalidas": int(a["invalidas"] or 0),
        "sum_vl_liquido": str(a["soma"]) if a["soma"] is not None else "0",
        "min_vl_liquido": str(a["minimo"]) if a["minimo"] is not None else None,
        "max_vl_liquido": str(a["maximo"]) if a["maximo"] is not None else None,
    }


def _objetos_em(spark, caminho: str) -> int:
    """Quantos objetos há sob o prefixo — qualquer um conta."""
    sc = spark.sparkContext
    p = sc._jvm.org.apache.hadoop.fs.Path(caminho)
    fs = p.getFileSystem(sc._jsc.hadoopConfiguration())
    if not fs.exists(p):
        return 0
    return len(fs.listStatus(p))


def _contar_rejeitos(spark, caminho: str) -> int:
    return spark.read.parquet(caminho).count()


def _recusa(motivo: str) -> int:
    print(f"  recusado: {motivo}")
    print("LAGO=RECUSADO")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv")
    ap.add_argument("--contrato", default="/app/contracts/competencia-202601.yaml")
    ap.add_argument("--competencia", default="2026-01")
    ap.add_argument("--out", default="/tmp/prova-lago.json")
    ap.add_argument("--destino", default=CAMINHO)
    ap.add_argument("--rejeitos", default=CAMINHO_REJEITOS)
    args = ap.parse_args()

    from pda import contrato as cm

    csv = Path(args.csv)
    if not csv.exists():
        print(f"  {csv} não encontrado", file=sys.stderr)
        print("LAGO=ERRO")
        return 1

    c = cm.carregar_contrato(args.contrato)
    if c == cm.NAO_MEDIDO:
        print("  contrato NAO_MEDIDO — sem âncora não se grava (Regra 2)")
        print("LAGO=RECUSADO")
        return 1

    destino = f"{args.destino}/competencia={args.competencia}"
    destino_rejeitos = f"{args.rejeitos}/competencia={args.competencia}"

    spark = _sessao(f"gravar-lago-{args.competencia}")
    try:
        # Antes de qualquer leitura ou escrita: partição ocupada recusa, e o
        # que já está lá é evidência — nada é sobrescrito nem apagado.
        for caminho, motivo in ((destino, "PARTICAO_JA_CARREGADA"),
                                (destino_rejeitos, "REJEITOS_JA_OCUPADOS")):
            if _objetos_em(spark, caminho):
                return _recusa(f"{motivo} — {caminho}")

        print("  lendo a fonte...", flush=True)
        bruto = _ler_bruto(spark, csv, c)

        fora_do_padrao = bruto.filter(_especie_invalida(c)).count()
        if fora_do_padrao:
            return _recusa(f"ESPECIE_FORA_DO_PADRAO — {fora_do_padrao:,} linhas")

        df = _projetar(bruto, c).cache()
        try:
            antes = _controles(df)
        except Exception as erro:  # noqa: BLE001
            if fora_da_precisao(erro):
                return _recusa("VALOR_FORA_DA_PRECISAO")
            raise
        print(f"    {antes['count_linhas']:,} linhas · {antes['sum_vl_liquido']}")

        # Regra 9 — zero linhas não é gravação.
        if antes["count_linhas"] == 0:
            print("  nenhuma linha lida — nada a gravar")
            print("LAGO=RECUSADO")
            return 1

        invalidas = antes["linhas_invalidas"]
        if invalidas:
            print(f"  gravando {invalidas:,} rejeitos em {destino_rejeitos}", flush=True)
            (bruto.filter(_valor(c).isNull())
             .withColumn("motivo", F.lit(MOTIVO_REJEITO))
             .write.mode("errorifexists").parquet(destino_rejeitos))

        print(f"  gravando em {destino}", flush=True)
        # append, NUNCA overwrite: o BRD nomeou o overwrite como defeito, e
        # o ADR 0011 decidiu carga incremental. A partição já foi conferida
        # vazia acima; se outra carga entrou depois, a releitura acusa.
        df.write.mode("append").parquet(destino)

        print("  RELENDO do lago para conferir...", flush=True)
        # A prova: relê o que foi escrito, e mede de novo. Confiar na
        # escrita seria medir o que o pipeline diz ter feito.
        do_lago = spark.read.parquet(destino)
        depois = _controles(do_lago)
        print(f"    {depois['count_linhas']:,} linhas · {depois['sum_vl_liquido']}")
        rejeitos_lidos = _contar_rejeitos(spark, destino_rejeitos) if invalidas else 0
    finally:
        spark.stop()

    print()
    print(f"  {'controle':<18} {'fonte':>18} {'lago':>18}")
    print("  " + "-" * 58)
    todos = True
    for k in ("count_linhas", "linhas_invalidas", "sum_vl_liquido",
              "min_vl_liquido", "max_vl_liquido"):
        def n(x):
            try:
                return str(Decimal(str(x)))
            except Exception:  # noqa: BLE001
                return str(x)
        ok = n(antes[k]) == n(depois[k])
        todos &= ok
        print(f"  {k:<18} {str(antes[k]):>18} {str(depois[k]):>18}  "
              f"{'BATE' if ok else 'DIVERGE'}")

    # Os rejeitos relidos têm de ser exatamente as linhas inválidas da fonte
    rejeitos_ok = rejeitos_lidos == invalidas
    print(f"  {'rejeitos':<18} {invalidas:>18} {rejeitos_lidos:>18}  "
          f"{'BATE' if rejeitos_ok else 'DIVERGE'}")

    # E contra a âncora, que é a verdade de fora
    anc = c.ancora
    bate_ancora = (
        depois["count_linhas"] == anc.count_linhas
        and Decimal(depois["sum_vl_liquido"]) == anc.sum_vl_liquido
    )

    prova = {
        "competencia": args.competencia,
        "destino": destino,
        "destino_rejeitos": destino_rejeitos if invalidas else None,
        "controles_fonte": antes,
        "controles_lago": depois,
        "rejeitos_fonte": invalidas,
        "rejeitos_lago": rejeitos_lidos,
        "fonte_bate_lago": todos,
        "rejeitos_batem": rejeitos_ok,
        "lago_bate_ancora": bate_ancora,
    }
    Path(args.out).write_text(json.dumps(prova, indent=2, ensure_ascii=False),
                              encoding="utf-8")

    print()
    print(f"  lago == âncora? {bate_ancora}")
    print(f"  prova gravada em {args.out}")
    if todos and rejeitos_ok and bate_ancora:
        print("LAGO=GRAVADO")
        return 0
    print("LAGO=DIVERGE")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
