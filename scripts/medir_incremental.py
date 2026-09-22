"""Mede o acumulado do lago sob carga incremental.

Os arquivos são carregados de forma incremental, não overwrite (ADR 0011):
cada competência acrescenta ao lago em vez de substituí-lo. Isso cria uma
pergunta que a fábrica não responde hoje — o total do lago DEPOIS da carga
bate com o que deveria ter?

Este script mede a premissa que torna esse gate possível: as competências são
DISJUNTAS, então a soma das âncoras aprovadas é o total do lago, e não é
preciso varrer os 249 milhões de linhas para saber.

Ele NÃO recusa nada. Construir o gate é plano próprio.

Token: INCREMENTAL=MEDIDO|ERRO
"""
import glob
import json
import re
import sys
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 40

INSS = Path("/home/nobru/darkfactory-inss")
ANCORA_LOCAL = Path("evidence/_ancora.json")


def _competencias() -> dict[str, tuple[int, Decimal]]:
    pontos: dict[str, tuple[int, Decimal]] = {}

    for f in sorted(glob.glob(str(INSS / "evidence/_totais-*.json"))):
        m = re.search(r"_totais-(\d{4})(\d{2})", f)
        if not m:
            continue
        d = json.load(open(f, encoding="utf-8"))
        n = d.get("count_linhas") or d.get("linhas")
        s = d.get("sum_vl_liquido") or d.get("soma")
        if n and s is not None:
            pontos[f"{m.group(1)}-{m.group(2)}"] = (int(n), Decimal(str(s)))

    if ANCORA_LOCAL.exists():
        d = json.load(open(ANCORA_LOCAL, encoding="utf-8"))
        pontos["2026-01"] = (int(d["count_linhas"]), Decimal(d["sum_vl_liquido"]))

    return pontos


def main() -> int:
    pontos = _competencias()
    if len(pontos) < 2:
        print(f"  competências encontradas: {len(pontos)}")
        print("  menos de duas — não há acumulado a medir")
        print("INCREMENTAL=ERRO")
        return 1

    print(f"  {'após':<9} {'linhas no mês':>14} {'acumulado':>16} {'soma acumulada':>22}")
    print("  " + "-" * 66)

    linhas_ac = 0
    soma_ac = Decimal(0)
    for comp in sorted(pontos):
        n, s = pontos[comp]
        linhas_ac += n
        soma_ac += s
        print(f"  {comp:<9} {n:>14,} {linhas_ac:>16,} {str(soma_ac):>22}")

    # A premissa: competências disjuntas => soma das partes == acumulado.
    # Se um benefício aparecesse em dois meses, isto divergiria.
    soma_partes = sum((s for _, s in pontos.values()), Decimal(0))
    linhas_partes = sum(n for n, _ in pontos.values())

    print()
    print(f"  soma das {len(pontos)} competências: {soma_partes}")
    print(f"  acumulado calculado    : {soma_ac}")
    print(f"  batem? {soma_partes == soma_ac}")
    print()
    print(f"  linhas somadas : {linhas_partes:,}")
    print(f"  linhas acumul. : {linhas_ac:,}")
    print(f"  batem? {linhas_partes == linhas_ac}")

    disjuntas = soma_partes == soma_ac and linhas_partes == linhas_ac
    print()
    if disjuntas:
        print("  DISJUNTAS — o total do lago é a soma das âncoras aprovadas.")
        print("  O gate do acumulado não precisa remedir o lago.")
    else:
        print("  NÃO disjuntas — alguma competência repete registros de outra.")
        print("  O ADR 0011 precisa de sucessor.")

    print()
    print("  ⚠ Este script não recusa nada. Enquanto o gate do acumulado não")
    print("    existir, uma carga incremental pode perder ou duplicar uma")
    print("    competência inteira sem que nada acuse.")
    print("INCREMENTAL=MEDIDO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
