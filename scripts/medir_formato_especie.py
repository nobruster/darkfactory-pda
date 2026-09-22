"""Mede o formato das DUAS colunas Espécie, índices 12 e 13.

O gate de layout promete distinguir as duas pelo FORMATO, porque o
cabeçalho é idêntico e não serve (ADR 0002). O plano afirma "índice 12
com código de 2 dígitos à direita e o 13 com descrição textual".

Se essa afirmação estiver errada, o gate que protege o ADR 0002 não
funciona — e seria a quarta vez que um número declarado não bate.

Token: FORMATO=MEDIDO|ERRO
"""
import re
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

SO_DIGITOS = re.compile(r"^\d+$")


def main() -> int:
    t0 = time.time()
    cod_padrao: Counter[str] = Counter()
    cod_larguras: Counter[int] = Counter()
    desc_padrao: Counter[str] = Counter()
    trocaveis = 0
    linhas = 0

    try:
        with open(CSV, encoding="latin-1", newline="") as f:
            next(f)
            for linha in f:
                campos = linha.rstrip("\r\n").split(";")
                if len(campos) <= IDX_DESCRICAO:
                    continue
                linhas += 1
                bruto_c = campos[IDX_CODIGO]
                bruto_d = campos[IDX_DESCRICAO]
                c, d = bruto_c.strip(), bruto_d.strip()

                if SO_DIGITOS.match(c):
                    cod_padrao["só dígitos"] += 1
                    cod_larguras[len(c)] += 1
                else:
                    cod_padrao["NÃO é só dígitos"] += 1

                desc_padrao["só dígitos" if SO_DIGITOS.match(d) else "textual"] += 1

                # o par seria indistinguível se AMBOS fossem só dígitos
                if SO_DIGITOS.match(c) and SO_DIGITOS.match(d):
                    trocaveis += 1

                # alinhamento: o código é preenchido à esquerda?
                if bruto_c.rstrip() != bruto_c and bruto_c.lstrip() == bruto_c:
                    cod_padrao["alinhado à ESQUERDA"] += 1
    except FileNotFoundError:
        print(f"erro: {CSV} não encontrado", file=sys.stderr)
        print("FORMATO=ERRO")
        return 1

    print(f"  linhas   : {linhas:,}")
    print(f"  segundos : {time.time() - t0:.0f}")
    print()
    print("  índice 12 (código):")
    for k, n in cod_padrao.most_common():
        print(f"    {k:<24} {n:>12,}")
    print("    larguras após strip:")
    for w, n in sorted(cod_larguras.items()):
        print(f"      {w} -> {n:,}")
    print()
    print("  índice 13 (descrição):")
    for k, n in desc_padrao.most_common():
        print(f"    {k:<24} {n:>12,}")
    print()
    print(f"  linhas em que AMBOS seriam só dígitos: {trocaveis:,}")
    if trocaveis:
        print("    ^ nessas, o formato NÃO distingue as duas colunas")
    else:
        print("    o formato distingue as duas em toda linha")

    print("FORMATO=MEDIDO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
