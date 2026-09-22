"""Mede a gramática monetária REAL da fonte, e a escala dos valores.

O adversário (R10-C1) apontou que a gramática declarada no plano —
"dígitos com ponto decimal" — recusaria a competência inteira, porque a
fonte publica no formato brasileiro. Isto mede o formato de verdade.

Também responde R10-C3: a escala não pode ser assumida, tem de ser medida.

Token: GRAMATICA=MEDIDA|ERRO
"""
import re
import sys
import time
from decimal import Decimal

# O caminho do CSV vem por argumento; o default é a competência ancorada.
# Antes isto era uma constante fixa, e os medidores devolviam MEDIDO tendo
# varrido o arquivo ERRADO quando chamados para outra competência.
_PADRAO = "_raw/D.SDA.PDA.003.EMI.202601.csv"
CSV = sys.argv[1] if len(sys.argv) > 1 else _PADRAO
IDX_VALOR = 9

# formato brasileiro: milhar com ponto, decimal com vírgula, 2 casas
GRAMATICA = re.compile(r"^-?\d{1,3}(\.\d{3})*,\d{2}$")


def normalizar(bruto: str) -> Decimal | None:
    """Retira o preenchimento, exige o padrão, e só então converte."""
    s = bruto.strip()
    if not GRAMATICA.match(s):
        return None
    return Decimal(s.replace(".", "").replace(",", "."))


def main() -> int:
    t0 = time.time()
    aceitos = recusados = 0
    escalas: set[int] = set()
    exemplos: list[str] = []

    try:
        with open(CSV, encoding="latin-1", newline="") as f:
            next(f)
            for linha in f:
                campos = linha.rstrip("\r\n").split(";")
                if len(campos) <= IDX_VALOR:
                    continue
                v = normalizar(campos[IDX_VALOR])
                if v is None:
                    recusados += 1
                    if len(exemplos) < 10:
                        exemplos.append(campos[IDX_VALOR])
                else:
                    aceitos += 1
                    escalas.add(-v.as_tuple().exponent)
    except FileNotFoundError:
        print(f"erro: {CSV} não encontrado", file=sys.stderr)
        print("GRAMATICA=ERRO")
        return 1

    print(f"  aceitos   : {aceitos:,}")
    print(f"  recusados : {recusados:,}")
    print(f"  escalas   : {sorted(escalas)}")
    print(f"  segundos  : {time.time() - t0:.0f}")
    print()
    print("  Decimal(bruto) recusaria TODA linha legítima:")
    print("    '        1.621,00' — ponto de milhar, vírgula decimal")
    print("  a normalização é parte da gramática, não um passo implícito")

    if exemplos:
        print()
        print("  exemplos fora da gramática:")
        for e in exemplos:
            print(f"    {e!r}")

    print("GRAMATICA=MEDIDA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
