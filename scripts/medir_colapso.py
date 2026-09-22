"""Mede a PERDA DE IDENTIDADE na competência inteira.

O critério de largura não funciona: todas as 41.572.553 descrições têm 20
caracteres brutos, então "bruto == 20" marcaria toda linha como truncada.
E len(strip()) == 20 deixa de fora 'Pensão por Morte de ' (strip=19), que
colapsa quatro códigos.

O defeito real é uma descrição cobrir MAIS DE UM código — perda de
identidade, não largura de campo.

Token: COLAPSO=MEDIDO|ERRO
"""
import sys
import time
from collections import defaultdict

CSV = "_raw/D.SDA.PDA.003.EMI.202601.csv"
IDX_CODIGO = 12
IDX_DESCRICAO = 13


def main() -> int:
    t0 = time.time()
    por_descricao: dict[str, set[str]] = defaultdict(set)
    por_codigo: dict[str, set[str]] = defaultdict(set)

    try:
        with open(CSV, encoding="latin-1", newline="") as f:
            next(f)
            for linha in f:
                campos = linha.rstrip("\r\n").split(";")
                if len(campos) <= IDX_DESCRICAO:
                    continue
                cod = campos[IDX_CODIGO].strip()
                desc = campos[IDX_DESCRICAO]
                por_descricao[desc].add(cod)
                por_codigo[cod].add(desc)
    except FileNotFoundError:
        print(f"erro: {CSV} não encontrado", file=sys.stderr)
        print("COLAPSO=ERRO")
        return 1

    colapsos = {d: c for d, c in por_descricao.items() if len(c) > 1}
    afetados = {cod for cods in colapsos.values() for cod in cods}

    print(f"  códigos distintos    : {len(por_codigo)}")
    print(f"  descrições distintas : {len(por_descricao)}")
    print(f"  segundos             : {time.time() - t0:.0f}")
    print()
    print(f"  descrições que cobrem >1 código: {len(colapsos)}")
    print(f"  códigos que perdem identidade  : {len(afetados)}")
    print()

    for desc, cods in sorted(colapsos.items(), key=lambda x: -len(x[1])):
        print(f"    {desc!r}")
        print(f"      strip={len(desc.strip()):>2}  cobre {len(cods)}: {sorted(cods)}")

    largura_falharia = sum(1 for d in colapsos if len(d.strip()) != 20)
    print()
    print(f"  colapsos que len(strip())==20 NÃO pegaria: {largura_falharia}")
    print("COLAPSO=MEDIDO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
