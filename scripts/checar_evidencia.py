"""Confere cada sha256 declarado na receita contra o arquivo em disco.

Um ADR superseded muda de frontmatter, e o hash fixado na receita para de
bater — o seamwise devolve local_source_hash_mismatch. Isto acusa antes,
e diz qual é o hash certo.

Token: EVIDENCIA=OK|DIVERGE|ERRO
"""
import hashlib
import io
import re
import sys
from pathlib import Path

RECEITA = "cvg/swimlanes/pda-recipe.yaml"


def main() -> int:
    caminho = sys.argv[1] if len(sys.argv) > 1 else RECEITA
    try:
        texto = io.open(caminho, encoding="utf-8").read()
    except FileNotFoundError:
        print(f"erro: {caminho} não encontrado", file=sys.stderr)
        print("EVIDENCIA=ERRO")
        return 1

    pares = re.findall(
        r"uri:\s*(\S+)\s*\n\s*captured_at:.*\n\s*sha256:\s*\"([0-9a-f]{64})\"",
        texto,
    )

    if not pares:
        print("  nenhuma evidência com sha256 declarado")
        print("EVIDENCIA=OK")
        return 0

    divergem = 0
    for uri, declarado in pares:
        p = Path(uri)
        if not p.exists():
            print(f"  AUSENTE  {uri}")
            divergem += 1
            continue
        real = hashlib.sha256(p.read_bytes()).hexdigest()
        if real == declarado:
            print(f"  ok       {uri}")
        else:
            divergem += 1
            print(f"  DIVERGE  {uri}")
            print(f"           declarado {declarado}")
            print(f"           real      {real}")

    print()
    if divergem:
        print(f"  {divergem} de {len(pares)} evidência(s) fora de dia")
        print("  um ADR superseded muda de frontmatter e o hash muda junto")
        print("EVIDENCIA=DIVERGE")
        return 1

    print(f"  {len(pares)} evidência(s) conferidas")
    print("EVIDENCIA=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
