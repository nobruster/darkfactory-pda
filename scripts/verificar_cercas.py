"""Confere que as DUAS cercas concordam.

`.claude/settings.json` restringe o agente. `.cvg/gate.yaml` restringe o
gate. As duas precisam proteger os mesmos caminhos — duas cercas que
discordam são uma cerca com buraco, e ninguém sabe qual metade vale.

No darkfactory-inss uma auditoria achou as duas discordando, com
`docs/adrs/` e `evidence/` faltando de um lado. Aqui, até 21/09/2026, a
segunda cerca NÃO EXISTIA e a primeira era cópia byte-a-byte da bancada:
protegia `fabrica/contracts/` e deixava `_raw/` com 12 GB aberto.

⚠ E confere que o caminho protegido EXISTE. Cerca que casa com zero
arquivo existe no papel e não protege nada — foi a objeção #11 do inss,
onde `evidence/*-run.json` não casava com nenhum packet real.

Token: CERCAS=OK|DIVERGEM|ERRO
"""
import io
import json
import re
import sys
from pathlib import Path

SETTINGS = Path(".claude/settings.json")
GATE = Path(".cvg/gate.yaml")

# os caminhos que a doutrina manda cercar numa fábrica gerada
EXIGIDOS = [
    "_raw",
    "contracts",
    "cvg/docs/adrs",
    "evidence",
]


def do_settings() -> set[str]:
    d = json.loads(io.open(SETTINGS, encoding="utf-8").read())
    alvos = set()
    for regra in d["permissions"]["deny"]:
        m = re.match(r"(?:Write|Edit)\((.+)\)$", regra)
        if m:
            alvos.add(m.group(1).rstrip("/*").rstrip("/"))
    return alvos


def do_gate() -> set[str]:
    alvos = set()
    for linha in io.open(GATE, encoding="utf-8"):
        m = re.match(r'\s*-\s*"([^"]+)"', linha)
        if m:
            alvos.add(m.group(1).rstrip("/*").rstrip("/"))
    return alvos


def main() -> int:
    if not SETTINGS.exists():
        print(f"  AUSENTE {SETTINGS}")
        print("CERCAS=ERRO")
        return 1
    if not GATE.exists():
        print(f"  AUSENTE {GATE} — a segunda cerca não existe")
        print("  sem ela não há teto permanente de autoridade")
        print("CERCAS=ERRO")
        return 1

    s, g = do_settings(), do_gate()
    problemas = 0

    print("  os quatro caminhos da doutrina:")
    for caminho in EXIGIDOS:
        no_s = any(a == caminho or a.startswith(caminho) for a in s)
        no_g = any(a == caminho or a.startswith(caminho) for a in g)
        existe = Path(caminho).exists()

        if no_s and no_g and existe:
            estado = "ok"
        elif not existe:
            estado = "NÃO EXISTE no disco"
            problemas += 1
        else:
            falta = []
            if not no_s:
                falta.append("settings.json")
            if not no_g:
                falta.append("gate.yaml")
            estado = "FALTA em " + " e ".join(falta)
            problemas += 1

        print(f"    {caminho:<20} {estado}")

    print()
    print("  cercas que apontam para caminho inexistente:")
    mortas = 0
    for alvo in sorted(s | g):
        if alvo.startswith("**") or "*" in alvo.split("/")[0]:
            continue
        base = alvo.split("*")[0].rstrip("/")
        if not base:
            continue
        # com glob no nome do arquivo, o que importa é o diretório existir
        # E haver pelo menos um arquivo casando
        if "*" in alvo:
            pai = Path(base).parent if not Path(base).is_dir() else Path(base)
            padrao = alvo[len(str(pai)) :].lstrip("/") if pai != Path(".") else alvo
            casou = pai.is_dir() and any(pai.glob(padrao))
            if not casou:
                print(f"    {alvo}  — casa com ZERO arquivo")
                mortas += 1
        elif not Path(base).exists():
            print(f"    {alvo}  — casa com ZERO arquivo")
            mortas += 1
    if not mortas:
        print("    nenhuma")

    print()
    if problemas:
        print(f"  {problemas} divergência(s) entre as cercas")
        print("CERCAS=DIVERGEM")
        return 1

    print(f"  as duas cercas concordam nos {len(EXIGIDOS)} caminhos da doutrina")
    print("CERCAS=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
