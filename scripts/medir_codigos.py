"""Mede a cardinalidade REAL de códigos de espécie na competência inteira.

O ADR 0004 mediu 51 códigos em ~3 milhões de linhas — uma amostra.
O adversário (R7-C1) apontou que tratar 51 como o universo pode recusar
uma competência correta. Isto mede o arquivo todo.

Token: CODIGOS=MEDIDO|ERRO
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
    codigos: Counter[str] = Counter()
    pares: set[tuple[str, str]] = set()
    linhas = 0

    try:
        with open(CSV, encoding="latin-1", newline="") as f:
            next(f)  # cabeçalho
            for linha in f:
                campos = linha.rstrip("\r\n").split(";")
                if len(campos) <= IDX_DESCRICAO:
                    continue
                cod = campos[IDX_CODIGO].strip()
                desc = campos[IDX_DESCRICAO]
                codigos[cod] += 1
                pares.add((cod, desc))
                linhas += 1
    except FileNotFoundError:
        print(f"erro: {CSV} não encontrado", file=sys.stderr)
        print("CODIGOS=ERRO")
        return 1

    descricoes = {d for _, d in pares}

    print(f"  linhas lidas       : {linhas:,}")
    print(f"  códigos distintos  : {len(codigos)}")
    print(f"  descrições distintas: {len(descricoes)}")
    print(f"  segundos           : {time.time() - t0:.0f}")
    print()
    print("  o ADR 0004 mediu 51 códigos em ~3 milhões de linhas")
    print(f"  na competência INTEIRA são {len(codigos)}")
    print()

    raros = [(c, n) for c, n in codigos.most_common() if n < 100_000]
    if raros:
        print(f"  {len(raros)} código(s) com menos de 100 mil ocorrências:")
        for c, n in raros[:15]:
            print(f"    {c!r:>6} {n:>12,}")

    print("CODIGOS=MEDIDO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
