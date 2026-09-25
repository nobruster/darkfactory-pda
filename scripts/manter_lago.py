"""Manutenção do lago: retenção de cinco anos e OPTIMIZE nas tabelas publicadas.

Por padrão só MEDE — diz o que faria, sem commit. Só altera com --aplicar.
A lista é FECHADA e literal: varrer o bucket tocaria o que ninguém nomeou.
Sem VACUUM (ADR 0017). O procedimento de publicação do dono chama este script
ao fim de cada carga.

Token por tabela: MANUTENCAO=<caminho> RETENCAO=<...> OPTIMIZE=<...>
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

TABELAS = [
    "s3a://bronze/pda/beneficios-emitidos",
    "s3a://bronze/pda/referencia/dicionario_especies",
    "s3a://bronze/pda/referencia/glossario",
    "s3a://silver/pda/beneficios-emitidos",
    "s3a://silver/pda/especie",
    "s3a://silver/pda/glossario",
    "s3a://gold/pda/beneficios-emitidos",
    "s3a://gold/pda/assuntos/fat_especie",
    "s3a://gold/pda/assuntos/kpis_nacionais",
    "s3a://gold/pda/referencia/dim_especie",
    "s3a://gold/pda/referencia/dim_termo",
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aplicar", action="store_true", help="altera de verdade (padrão: só mede)")
    args = ap.parse_args(argv)

    from medalhao import bronze, manutencao

    spark = bronze.criar_sessao("manter-lago")
    ruim = False
    for caminho in TABELAS:
        if args.aplicar:
            ret = manutencao.garantir_retencao(spark, caminho)["resultado"]
            opt = manutencao.otimizar(spark, caminho)["resultado"]
        else:
            ret = "MEDIDO_" + manutencao.planejar_retencao(spark, caminho)["resultado"]
            opt = "NAO_EXECUTADO"
        ruim = ruim or ret == "NAO_MEDIDO" or opt in ("DIVERGE", "NAO_MEDIDO")
        print(f"MANUTENCAO={caminho} RETENCAO={ret} OPTIMIZE={opt}")
    return 1 if ruim else 0


if __name__ == "__main__":
    sys.exit(main())
