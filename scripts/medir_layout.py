"""Mede o layout e o critério de truncamento na competência INTEIRA.

Duas afirmações do plano nunca foram conferidas no arquivo todo:

  1. "as 14 posições do layout"        — toda linha tem 14 campos?
  2. "o campo BRUTO ocupa 20 caracteres" — é esse o critério de truncamento?

As três falhas anteriores (51 códigos, prec=13, gramática de ponto)
tinham a mesma causa: número declarado sem conferir na fonte.

Token: LAYOUT=MEDIDO|ERRO
"""
import sys
import time
from collections import Counter

# O caminho do CSV vem por argumento; o default é a competência ancorada.
# Antes isto era uma constante fixa, e os medidores devolviam MEDIDO tendo
# varrido o arquivo ERRADO quando chamados para outra competência.
_PADRAO = "_raw/D.SDA.PDA.003.EMI.202601.csv"
CSV = sys.argv[1] if len(sys.argv) > 1 else _PADRAO
IDX_CODIGO = 12
IDX_DESCRICAO = 13


def main() -> int:
    t0 = time.time()
    larguras: Counter[int] = Counter()
    desc_brutas: Counter[int] = Counter()
    cod_brutos: Counter[int] = Counter()
    por_codigo: dict[str, set[str]] = {}
    linhas = 0

    try:
        with open(CSV, encoding="latin-1", newline="") as f:
            cabecalho = next(f).rstrip("\r\n").split(";")
            for linha in f:
                campos = linha.rstrip("\r\n").split(";")
                larguras[len(campos)] += 1
                linhas += 1
                if len(campos) <= IDX_DESCRICAO:
                    continue
                cod_brutos[len(campos[IDX_CODIGO])] += 1
                desc_brutas[len(campos[IDX_DESCRICAO])] += 1
                por_codigo.setdefault(campos[IDX_CODIGO].strip(), set()).add(
                    campos[IDX_DESCRICAO]
                )
    except FileNotFoundError:
        print(f"erro: {CSV} não encontrado", file=sys.stderr)
        print("LAYOUT=ERRO")
        return 1

    print(f"  campos no cabeçalho : {len(cabecalho)}")
    print(f"  linhas lidas        : {linhas:,}")
    print(f"  segundos            : {time.time() - t0:.0f}")
    print()
    print("  campos por linha (largura -> ocorrências):")
    for w, n in sorted(larguras.items()):
        marca = "  <-- diverge do cabeçalho" if w != len(cabecalho) else ""
        print(f"    {w:>3} -> {n:>12,}{marca}")

    print()
    print("  largura BRUTA do campo descrição (índice 13):")
    for w, n in sorted(desc_brutas.items()):
        print(f"    {w:>3} -> {n:>12,}")

    print()
    print("  largura BRUTA do campo código (índice 12):")
    for w, n in sorted(cod_brutos.items()):
        print(f"    {w:>3} -> {n:>12,}")

    ambiguos = {c: d for c, d in por_codigo.items() if len(d) > 1}
    print()
    print(f"  códigos com MAIS DE UMA descrição bruta: {len(ambiguos)}")
    for c, d in list(ambiguos.items())[:5]:
        print(f"    {c!r}: {sorted(d)}")

    print("LAYOUT=MEDIDO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
