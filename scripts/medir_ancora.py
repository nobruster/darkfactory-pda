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
import re
import sys
import time
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path

# precisão declarada, não herdada: em prec baixa um centavo some ANTES do
# arredondamento, e quantizar depois não recupera
PRECISAO = 40

# A gramática monetária MEDIDA na fonte — formato brasileiro, ponto de
# milhar e vírgula decimal, duas casas. Sem ela, `replace(".", "")` aceita
# qualquer coisa e converte errado em silêncio:
#   "1.621"     -> 1621      inflação de 1000x
#   "1,621.00"  -> 1.62100   divisão por ~1000
# E `Decimal()` aceita "Infinity" e "NaN", que são construções válidas: o
# total do universo viraria Infinity com linhas_invalidas=0.
# É a mesma gramática de medir_gramatica.py e medir_sinal.py — duas
# gramáticas divergentes no mesmo diretório é que era o defeito.
GRAMATICA = re.compile(r"^-?\d{1,3}(\.\d{3})*,\d{2}$")


def para_decimal(bruto: str) -> Decimal | None:
    """Converte o texto da fonte em Decimal exato, ou devolve None.

    A fonte usa vírgula decimal. Nada de float em nenhum ponto: `float(x)`
    aqui perderia o centavo antes de qualquer soma. E nada de converter o
    que não casa a gramática — ilegível é ilegível, não é zero nem infinito.
    """
    t = (bruto or "").strip()
    if not GRAMATICA.match(t):
        return None
    try:
        return Decimal(t.replace(".", "").replace(",", "."))
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

    # Regra 2 — "li e não havia nada" NÃO é uma âncora. Um CSV vazio, ou só
    # com cabeçalho, ou com _raw montado errado, devolvia count_linhas=0 e
    # ANCORA=MEDIDA: o gate passaria a comparar contra zero. E uma âncora
    # sem NENHUMA linha válida é o mesmo palpite por outro caminho.
    validas = n_linhas - n_invalidas
    if n_linhas == 0 or validas == 0:
        print(f"  linhas lidas   : {n_linhas:,}")
        print(f"  linhas válidas : {validas:,}")
        print()
        print("  nenhuma linha válida — não há âncora a declarar")
        print("  um número que ninguém viu medir é indistinguível de um palpite")
        print("ANCORA=NAO_MEDIDO", flush=True)
        return 1

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
