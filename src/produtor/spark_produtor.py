"""O produtor Spark: lê o CSV, agrega, e DECLARA o envelope que o juiz lê.

O ADR 0005 decidiu que Spark grava e Python puro confere — e o ADR 0006
separou os entregáveis. Este é o produtor que faltava. Ele não julga nada:
produz o envelope e a fronteira decide.

Três decisões que não são de conveniência:

1. **`DecimalType`, nunca `DoubleType`.** O legado lia com `inferSchema` e
   deixava o Spark escolher — e a escolha para dinheiro com vírgula é
   `StringType` ou `DoubleType`, que perde o centavo. Aqui o schema é
   declarado, e o monetário vira `Decimal` com a precisão do contrato.

2. **Leitura posicional.** O cabeçalho traz `Espécie` duas vezes (ADR 0002);
   ler por nome perde uma das duas em silêncio. O Spark recebe `header=false`
   e nomes sintéticos por posição.

3. **O envelope declara `motor`, e a fronteira o ignora.** Está lá para o
   pacote de evidência registrar quem produziu, não para mudar a regra —
   `validar_envelope` nunca inspeciona esse campo (ADR 0006).

Token: PRODUTOR=OK|RECUSADO|ERRO
"""
import argparse
import hashlib
import json
import os
import sys
from decimal import Decimal, localcontext
from pathlib import Path

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import DecimalType, StringType, StructField, StructType

MOTOR = "spark"

# O contrato declara o encoding com o nome do Python — "latin-1" — porque
# foi lá que a fonte foi medida. A JVM não conhece esse rótulo e levanta
# UnsupportedEncodingException; ela chama o MESMO encoding de ISO-8859-1.
#
# O mapa fica AQUI, no produtor, e não no contrato: mudar o contrato para
# agradar a JVM faria o oráculo se ajustar ao motor, que é a direção que a
# Regra 3 proíbe. Quem se adapta é quem lê.
_ENCODING_JVM = {
    "latin-1": "ISO-8859-1",
    "latin1": "ISO-8859-1",
    "iso-8859-1": "ISO-8859-1",
    "utf-8": "UTF-8",
    "utf8": "UTF-8",
}


def _sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _sessao(nome: str) -> SparkSession:
    """SparkSession com S3A apontando para o MinIO — credenciais do ambiente.

    O legado trazia minioadmin/minioadmin escrito no meio do builder. O BRD
    nomeou isso como defeito; aqui vêm de variáveis que o compose injeta.
    """
    endpoint = os.environ.get("S3_ENDPOINT", "")
    chave = os.environ.get("S3_ACCESS_KEY", "")
    segredo = os.environ.get("S3_SECRET_KEY", "")

    b = SparkSession.builder.appName(nome)
    if endpoint and chave and segredo:
        b = (
            b.config("spark.hadoop.fs.s3a.endpoint", endpoint)
            .config("spark.hadoop.fs.s3a.access.key", chave)
            .config("spark.hadoop.fs.s3a.secret.key", segredo)
            .config("spark.hadoop.fs.s3a.path.style.access", "true")
            .config("spark.hadoop.fs.s3a.impl",
                    "org.apache.hadoop.fs.s3a.S3AFileSystem")
        )
    spark = b.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark


def _schema_posicional(total_colunas: int) -> StructType:
    """Nomes sintéticos por posição — nunca o cabeçalho.

    `Espécie` aparece duas vezes (ADR 0002). Com header=true o Spark
    resolveria o conflito renomeando, e a coluna certa viraria sorte.

    TUDO entra como string. O monetário é convertido depois, pela gramática
    brasileira: a fonte publica `        1.621,00`, e `DecimalType` no
    schema espera ponto decimal — deixar o Spark converter devolveria NULL
    em toda linha, e o produtor declararia zero como se fosse medição.
    """
    return StructType([
        StructField(f"c{i}", StringType(), True) for i in range(total_colunas)
    ])


def _para_decimal(col, precisao: int, escala: int):
    """Converte o formato brasileiro em Decimal exato, ou NULL.

    `1.621,00` -> `1621.00`: tira o ponto de milhar, troca a vírgula por
    ponto. A gramática é a mesma de `scripts/medir_gramatica.py`, que mediu
    41.572.553 aceitos e 0 recusados — o que não casar vira NULL e conta
    como linha inválida, nunca como zero.
    """
    limpo = F.trim(col)
    so_valido = F.when(
        limpo.rlike(r"^-?\d{1,3}(\.\d{3})*,\d{2}$"), limpo
    ).otherwise(F.lit(None))
    sem_milhar = F.regexp_replace(so_valido, r"\.", "")
    com_ponto = F.regexp_replace(sem_milhar, ",", ".")
    return com_ponto.cast(DecimalType(precisao, escala))


def produzir(csv: Path, contrato, competencia: str) -> dict:
    layout = contrato.layout
    pol = contrato.politica_decimal
    idx_valor = layout.posicoes["vl_liquido"]
    idx_especie = layout.posicoes["especie"]

    spark = _sessao(f"produtor-pda-{competencia}")
    try:
        bruto = (
            spark.read.option("header", "true")   # descarta o cabeçalho
            .option("sep", layout.separador)
            .option("encoding", _ENCODING_JVM.get(
                layout.encoding.lower(), layout.encoding))
            .option("mode", "PERMISSIVE")
            .schema(_schema_posicional(layout.total_colunas))
            .csv(str(csv))
        )

        df = bruto.withColumn(
            "_valor",
            _para_decimal(F.col(f"c{idx_valor}"), pol.precisao, pol.escala),
        )

        col_valor = F.col("_valor")
        col_especie = F.trim(F.col(f"c{idx_especie}"))

        # Os cinco controles, numa passada. O valor já é Decimal pelo schema:
        # nada de float em ponto nenhum (Regra 5).
        agg = df.agg(
            F.count(F.lit(1)).alias("count_linhas"),
            F.sum(F.when(col_valor.isNull(), 1).otherwise(0)).alias("invalidas"),
            F.sum(col_valor).alias("soma"),
            F.min(col_valor).alias("minimo"),
            F.max(col_valor).alias("maximo"),
        ).collect()[0]

        por_codigo = (
            df.filter(col_valor.isNotNull())
            .groupBy(col_especie.alias("codigo"))
            .agg(F.sum(col_valor).alias("total"))
            .collect()
        )
    finally:
        spark.stop()

    invalidas = int(agg["invalidas"] or 0)
    with localcontext() as ctx:
        ctx.prec = pol.precisao
        soma = Decimal(str(agg["soma"])) if agg["soma"] is not None else Decimal(0)

    return {
        "competencia": competencia,
        "motor": MOTOR,
        "sha256_arquivo_lido": _sha256(csv),
        "controles": {
            "count_linhas": int(agg["count_linhas"] or 0),
            "linhas_invalidas": invalidas,
            # string, nunca número JSON — R5-C1 da fronteira
            "sum_vl_liquido": str(soma),
            "min_vl_liquido": str(agg["minimo"]) if agg["minimo"] is not None else None,
            "max_vl_liquido": str(agg["maximo"]) if agg["maximo"] is not None else None,
        },
        # O produtor não classifica defeito de identidade: isso é da leitura,
        # que tem o conjunto inteiro (R12-C3). Declara lista vazia e a
        # fronteira confere contra o que a leitura observou.
        "defeitos": [],
        "total_por_codigo": {
            r["codigo"]: str(r["total"]) for r in por_codigo if r["codigo"]
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv")
    ap.add_argument("--contrato", default="contracts/competencia-202601.yaml")
    ap.add_argument("--competencia", default="2026-01")
    ap.add_argument("--out", default="envelope.json")
    args = ap.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from pda import contrato as contrato_mod

    csv = Path(args.csv)
    if not csv.exists():
        print(f"  {csv} não encontrado", file=sys.stderr)
        print("PRODUTOR=ERRO")
        return 1

    carregado = contrato_mod.carregar_contrato(args.contrato)
    if carregado == contrato_mod.NAO_MEDIDO:
        print("  contrato NAO_MEDIDO — sem âncora não se produz (Regra 2)")
        print("PRODUTOR=RECUSADO")
        return 1

    env = produzir(csv, carregado, args.competencia)
    c = env["controles"]

    # Regra 9 — "li e não havia nada" NÃO é produção. A primeira versão
    # deste script declarou PRODUTOR=OK com count_linhas=0 sobre 50 mil
    # linhas: tinha lido tudo e convertido nada, porque o DecimalType do
    # Spark não entende `1.621,00`. Um envelope de zeros passaria adiante
    # como se fosse medição.
    validas = c["count_linhas"] - c["linhas_invalidas"]
    if c["count_linhas"] == 0 or validas == 0:
        print(f"  linhas lidas   : {c['count_linhas']:,}")
        print(f"  linhas válidas : {validas:,}")
        print()
        print("  nenhuma linha válida — não há envelope a declarar")
        print("PRODUTOR=RECUSADO")
        return 1

    Path(args.out).write_text(json.dumps(env, indent=2, ensure_ascii=False),
                              encoding="utf-8")
    print(f"  motor            : {env['motor']}")
    print(f"  count_linhas     : {c['count_linhas']:,}")
    print(f"  linhas_invalidas : {c['linhas_invalidas']:,}")
    print(f"  sum_vl_liquido   : {c['sum_vl_liquido']}")
    print(f"  códigos          : {len(env['total_por_codigo'])}")
    print(f"  envelope         : {args.out}")
    print("PRODUTOR=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
