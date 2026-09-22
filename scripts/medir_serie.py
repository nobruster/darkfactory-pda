"""Mede a série da média por benefício entre competências vizinhas.

O ADR 0001 nomeia a lacuna: *"Nenhum gate compara competências vizinhas. Um
salto na média passa sem que nada acuse — a fábrica vê um centavo errado
DENTRO de uma competência e não vê isto."*

Este script mostra o que a fábrica não vê. Ele NÃO recusa nada: com seis
pontos não há base para declarar o que é variação normal, e escolher um
limiar por conforto seria inventar o gate em vez de medi-lo (Regra 9).

As competências vêm de dois repositórios independentes:
  darkfactory-inss  5 competências, medidas por outro código
  darkfactory-pda   2026-01, a nossa

Token: SERIE=MEDIDA|ERRO
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

# acima disto o script marca; não é limiar de recusa, é só onde olhar
DESTAQUE_PCT = Decimal("5")


def _competencias() -> list[tuple[str, int, Decimal]]:
    pontos: dict[str, tuple[int, Decimal]] = {}

    # DUAS origens: o darkfactory-inss, que mediu cinco competências com
    # outro código, e a evidência local, onde as que baixamos são gravadas.
    # Ler só uma delas esconde metade da série.
    fontes = [
        str(INSS / "evidence/_totais-*.json"),
        "evidence/_totais-*.json",
    ]

    for padrao in fontes:
        for f in sorted(glob.glob(padrao)):
            m = re.search(r"_totais-(\d{4})(\d{2})", f)
            if not m:
                continue
            d = json.load(open(f, encoding="utf-8"))
            n = d.get("count_linhas") or d.get("linhas")
            s = d.get("sum_vl_liquido") or d.get("soma")
            if not n or s is None:
                continue
            pontos[f"{m.group(1)}-{m.group(2)}"] = (int(n), Decimal(str(s)))

    if ANCORA_LOCAL.exists():
        d = json.load(open(ANCORA_LOCAL, encoding="utf-8"))
        pontos["2026-01"] = (int(d["count_linhas"]), Decimal(d["sum_vl_liquido"]))

    return [(c, *pontos[c]) for c in sorted(pontos)]


def main() -> int:
    serie = _competencias()
    if len(serie) < 2:
        print(f"  competências encontradas: {len(serie)}")
        print("  menos de duas — não há série a medir")
        print("SERIE=ERRO")
        return 1

    print(f"  {'competência':<13} {'linhas':>12} {'média/benefício':>16} {'variação':>10}")
    print("  " + "-" * 56)

    anterior: Decimal | None = None
    saltos: list[tuple[str, Decimal]] = []

    for comp, n, soma in serie:
        media = soma / n
        var_txt = ""
        if anterior:
            var = (media - anterior) / anterior * 100
            var_txt = f"{var:+.2f}%"
            if abs(var) > DESTAQUE_PCT:
                saltos.append((comp, var))
                var_txt += "  <--"
        print(f"  {comp:<13} {n:>12,} {media:>16.2f} {var_txt:>10}")
        anterior = media

    print()
    if saltos:
        print(f"  {len(saltos)} variação(ões) acima de {DESTAQUE_PCT}%:")
        for comp, var in saltos:
            print(f"    {comp}  {var:+.2f}%")
    else:
        print(f"  nenhuma variação acima de {DESTAQUE_PCT}%")

    print()
    print("  ⚠ A fábrica julga cada competência contra a PRÓPRIA âncora.")
    print("    Toda linha acima passaria como ACEITO — é a lacuna do ADR 0001.")
    print("SERIE=MEDIDA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
