#!/usr/bin/env python3
"""Mede a âncora de uma competência DIRETO na fonte, sem pipeline.

Por que existe
--------------
A âncora é o número contra o qual o agregado do pipeline é comparado. Medi-la
*com* o pipeline seria o pipeline conferindo a si mesmo: qualquer defeito
comum às duas execuções ficaria invisível.

Este script não usa Spark, não lê Parquet, não importa nada do `src/`. Ele
varre o CSV linha a linha e soma com `Decimal`, precisão declarada.

Leitura POSICIONAL
------------------
O cabeçalho traz `Espécie` duas vezes (posições 13 e 14, medido). Ler por
nome perde uma das duas em silêncio — por isso aqui se lê por índice, e o
índice da coluna monetária é passado explicitamente.

Uso
---
    python3 scripts/medir_ancora.py _raw/<arquivo>.csv --coluna-valor 9

Token final: ANCORA=MEDIDA | ANCORA=ERRO
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path

# precisão declarada, não herdada: em prec baixa um centavo some ANTES do
# arredondamento, e quantizar depois não recupera
PRECISAO = 40


def para_decimal(bruto: str) -> Decimal | None:
    """Converte o texto da fonte em Decimal exato, ou devolve None.

    A fonte usa vírgula decimal. Nada de float em nenhum ponto: `float(x)`
    aqui perderia o centavo antes de qualquer soma.
    """
    t = (bruto or "").strip().replace(".", "").replace(",", ".")
    if not t:
        return None
    try:
        return Decimal(t)
    except InvalidOperation:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_path")
    ap.add_argument("--coluna-valor", type=int, required=True,
                    help="índice 0-based da coluna monetária (posicional)")
    ap.add_argument("--sep", default=";")
    ap.add_argument("--encoding", default="latin-1")
    ap.add_argument("--out", default="evidence/_ancora.json")
    args = ap.parse_args()

    caminho = Path(args.csv_path)
    if not caminho.is_file():
        print(f"erro: não encontrei {caminho}", file=sys.stderr)
        print("ANCORA=ERRO")
        return 2

    t0 = time.time()
    with localcontext() as ctx:
        ctx.prec = PRECISAO

        soma = Decimal(0)
        n_linhas = 0
        n_invalidas = 0
        menor: Decimal | None = None
        maior: Decimal | None = None
        cabecalho: list[str] = []

        with caminho.open("r", encoding=args.encoding, newline="") as f:
            leitor = csv.reader(f, delimiter=args.sep)
            cabecalho = next(leitor, [])
            for linha in leitor:
                n_linhas += 1
                if args.coluna_valor >= len(linha):
                    n_invalidas += 1
                    continue
                v = para_decimal(linha[args.coluna_valor])
                if v is None:
                    n_invalidas += 1
                    continue
                soma += v
                if menor is None or v < menor:
                    menor = v
                if maior is None or v > maior:
                    maior = v
                if n_linhas % 5_000_000 == 0:
                    print(f"  ... {n_linhas:,} linhas ({time.time()-t0:.0f}s)",
                          flush=True)

    segundos = round(time.time() - t0)
    ancora = {
        "arquivo": caminho.name,
        "coluna_valor_indice": args.coluna_valor,
        "coluna_valor_nome": cabecalho[args.coluna_valor] if args.coluna_valor < len(cabecalho) else "?",
        "count_linhas": n_linhas,
        "linhas_invalidas": n_invalidas,
        "sum_vl_liquido": str(soma),
        "min_vl_liquido": str(menor) if menor is not None else None,
        "max_vl_liquido": str(maior) if maior is not None else None,
        "precisao_decimal": PRECISAO,
        "segundos": segundos,
        "medido_por": "scripts/medir_ancora.py — independente do pipeline",
    }

    saida = Path(args.out)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(ancora, indent=2, ensure_ascii=False),
                     encoding="utf-8")

    print()
    for k, v in ancora.items():
        print(f"  {k}: {v}")
    print()
    print(f"gravado em {saida}")
    print("ANCORA=MEDIDA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
