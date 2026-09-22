"""Mede sinal e magnitude na competência inteira.

O ADR 0007 deriva a precisão do total ancorado. Isso pressupõe que nenhum
acumulador intermediário exceda o total — verdadeiro se, e só se, não há
valores negativos, porque aí a soma é monotônica crescente.

O adversário (R12-C2) mostrou o contraexemplo: com um negativo grande,
prec=14 devolve .12 onde prec=40 devolve .13.

Token: SINAL=MEDIDO|ERRO
"""
import re
import sys
import time
from decimal import Decimal, localcontext

# Precisão DECLARADA, nunca herdada — é a primeira camada do ADR 0009 (via
# 0003), e este é o script que mede a premissa daquele ADR. Somar aqui com a
# precisão global seria verde pelo motivo errado: hoje o default é 28, maior
# que os 14 derivados, e o número calharia de estar certo.
PRECISAO = 40

CSV = "_raw/D.SDA.PDA.003.EMI.202601.csv"
IDX_VALOR = 9

GRAMATICA = re.compile(r"^-?\d{1,3}(\.\d{3})*,\d{2}$")


def main() -> int:
    t0 = time.time()
    negativos = zeros = n = 0
    descartados_curtos = descartados_gramatica = 0
    maior: Decimal | None = None
    menor: Decimal | None = None
    acumulado = Decimal(0)
    pico = Decimal(0)

    try:
        with localcontext() as ctx:
            ctx.prec = PRECISAO
            with open(CSV, encoding="latin-1", newline="") as f:
                next(f)
                for linha in f:
                    campos = linha.rstrip("\r\n").split(";")
                    if len(campos) <= IDX_VALOR:
                        descartados_curtos += 1
                        continue
                    s = campos[IDX_VALOR].strip()
                    if not GRAMATICA.match(s):
                        descartados_gramatica += 1
                        continue
                    v = Decimal(s.replace(".", "").replace(",", "."))
                    n += 1
                    if v < 0:
                        negativos += 1
                    elif v == 0:
                        zeros += 1
                    if maior is None or v > maior:
                        maior = v
                    if menor is None or v < menor:
                        menor = v
                    acumulado += v
                    if acumulado > pico:
                        pico = acumulado
    except FileNotFoundError:
        print(f"erro: {CSV} não encontrado", file=sys.stderr)
        print("SINAL=ERRO")
        return 1

    # Regra 2 — "li e não havia nada" NÃO é sucesso. Sem valor lido, a
    # premissa do ADR 0009 não foi medida, e afirmar que ela vale a partir
    # de zero observações é indistinguível de um palpite.
    if n == 0:
        print(f"  valores lidos : 0")
        print(f"  descartados   : {descartados_curtos:,} curtos, "
              f"{descartados_gramatica:,} fora da gramática")
        print()
        print("  nenhum valor legível — a premissa NÃO foi medida")
        print("SINAL=NAO_MEDIDO")
        return 1

    print(f"  valores lidos : {n:,}")
    print(f"  descartados   : {descartados_curtos:,} curtos, "
          f"{descartados_gramatica:,} fora da gramática")
    print(f"  negativos     : {negativos:,}")
    print(f"  zeros         : {zeros:,}")
    print(f"  maior valor   : {maior}")
    print(f"  menor valor   : {menor}")
    print(f"  precisão      : {PRECISAO} (declarada, não herdada)")
    print(f"  segundos      : {time.time() - t0:.0f}")
    print()
    print(f"  total          : {acumulado}")
    print(f"  pico do acumulador: {pico}")
    print(f"  pico > total? {pico > acumulado}")
    print()

    if negativos == 0:
        di_total = len(str(int(acumulado)))
        di_pico = len(str(int(pico)))
        print("  sem negativos -> soma MONOTÔNICA crescente")
        print(f"  dígitos inteiros do total: {di_total}")
        print(f"  dígitos inteiros do pico : {di_pico}")
        print("  nenhum acumulador excede o total, e a fórmula do ADR vale")
    else:
        print("  HÁ NEGATIVOS -> a soma não é monotônica")
        print("  um acumulador pode exceder o total: a fórmula NÃO basta")

    print("SINAL=MEDIDO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
