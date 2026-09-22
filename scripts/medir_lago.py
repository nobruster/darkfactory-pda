"""Mede o lago POR PARTIÇÃO e confronta a partição real contra a âncora.

Existe porque eu errei o diagnóstico. Eu tinha reportado:

    linhas no lago  41.622.553
    âncora          41.572.553
    diferença           50.000   <- contaminação

Estava errado. As 50 mil linhas de teste nunca entraram no dado real — elas
estão em `competencia=fatia-teste`, partição própria. O número que eu citei
era a soma das DUAS partições lida como se fosse uma: medi a união e culpei
a parte.

    2026-01       41.572.553   soma 78.521.752.562,12  <- bate EXATO
    fatia-teste       50.000   soma      76.534.969,09  <- separada

Um agregado sem `GROUP BY` na coluna de partição não mede partição nenhuma.
Por isso este script **nunca** imprime um total sem quebrá-lo por competência.

Regra 9 — os pisos explícitos, todos devolvem NAO_MEDIDO:

  - zero linhas no lago inteiro
  - partição real ausente
  - partição real com zero linhas
  - coluna de partição ausente (sem ela não há como separar)

Token: LAGO=INTEGRO|DIVERGE|NAO_MEDIDO|ERRO
"""
import argparse
import os
import sys
from decimal import Decimal, localcontext

BASE = "s3a://landing/pda/beneficios-emitidos"

# ADR 0006: a precisão é DECLARADA, nunca herdada do contexto global.
PRECISAO = 40


def _sessao(nome: str):
    from pyspark.sql import SparkSession

    faltando = [
        v for v in ("S3_ENDPOINT", "S3_ACCESS_KEY", "S3_SECRET_KEY")
        if not os.environ.get(v)
    ]
    if faltando:
        print(f"  variáveis ausentes: {', '.join(faltando)}", file=sys.stderr)
        print("LAGO=ERRO")
        sys.exit(1)

    return (
        SparkSession.builder.appName(nome)
        .config("spark.hadoop.fs.s3a.endpoint", os.environ["S3_ENDPOINT"])
        .config("spark.hadoop.fs.s3a.access.key", os.environ["S3_ACCESS_KEY"])
        .config("spark.hadoop.fs.s3a.secret.key", os.environ["S3_SECRET_KEY"])
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        .config("spark.sql.parquet.enableVectorizedReader", "false")
        .getOrCreate()
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--competencia", default="2026-01",
                    help="a partição que carrega o dado real")
    ap.add_argument("--linhas", type=int, default=41_572_553,
                    help="âncora: linhas esperadas na partição real")
    ap.add_argument("--soma", default="78521752562.12",
                    help="âncora: soma esperada na partição real")
    args = ap.parse_args()

    from pyspark.sql import functions as F

    spark = _sessao(f"medir-lago-{args.competencia}")
    spark.sparkContext.setLogLevel("ERROR")

    try:
        df = spark.read.parquet(BASE)
    except Exception as e:  # noqa: BLE001 — queremos o motivo na tela
        print(f"  não consegui ler {BASE}: {e}", file=sys.stderr)
        print("LAGO=ERRO")
        return 1

    if "competencia" not in df.columns:
        print("  coluna 'competencia' ausente")
        print("  — sem ela não há como separar teste de dado real")
        print("LAGO=NAO_MEDIDO")
        return 1

    total = df.count()
    if total == 0:
        print("  zero linhas no lago inteiro")
        print("  — lago vazio não é lago íntegro")
        print("LAGO=NAO_MEDIDO")
        return 1

    # NUNCA um total sem quebrar por partição. Foi assim que eu errei.
    print("=== por partição ===")
    por_part = (
        df.groupBy("competencia")
        .agg(F.count("*").alias("linhas"),
             F.sum(F.col("vl_liquido").cast("decimal(38,2)")).alias("soma"))
        .orderBy("competencia")
        .collect()
    )

    with localcontext() as ctx:
        ctx.prec = PRECISAO
        for r in por_part:
            s = Decimal(str(r["soma"] or 0))
            print(f"  {r['competencia']:<20} {r['linhas']:>12,}  {s:>20,.2f}")
        print(f"  {'TOTAL (união)':<20} {total:>12,}")
    print()

    real = [r for r in por_part if r["competencia"] == args.competencia]
    if not real:
        print(f"  partição {args.competencia} AUSENTE")
        print("LAGO=NAO_MEDIDO")
        return 1

    n = real[0]["linhas"]
    if n == 0:
        print(f"  partição {args.competencia} tem zero linhas")
        print("LAGO=NAO_MEDIDO")
        return 1

    with localcontext() as ctx:
        ctx.prec = PRECISAO
        s = Decimal(str(real[0]["soma"] or 0))
        esperada = Decimal(args.soma)

        print(f"=== partição {args.competencia} contra a âncora ===")
        print(f"  linhas  lago {n:>14,}   âncora {args.linhas:>14,}"
              f"   dif {n - args.linhas:>+12,}")
        print(f"  soma    lago {s:>14,.2f}   âncora {esperada:>14,.2f}"
              f"   dif {s - esperada:>+12,.2f}")
        print()

        outras = [r["competencia"] for r in por_part
                  if r["competencia"] != args.competencia]
        if outras:
            print(f"  outras partições no lago: {', '.join(outras)}")
            print("  — isoladas; não entram na partição real")
            print()

        if n == args.linhas and s == esperada:
            print("  os DOIS controles batem")
            print("LAGO=INTEGRO")
            return 0

    print("  ao menos um controle NÃO bate")
    print("LAGO=DIVERGE")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
