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

    # Casar as três linhas em ordem rígida ignorava em silêncio toda
    # evidência com os campos reordenados, sem aspas, ou com hash em
    # maiúscula — e um arquivo sem nenhum par casando devolvia OK. Agora
    # cada bloco `source:` é lido inteiro e a AUSÊNCIA de sha256 acusa.
    pares: list[tuple[str, str]] = []
    sem_hash: list[str] = []
    for m_uri in re.finditer(r"uri:\s*[\"']?([^\s\"']+)[\"']?", texto):
        uri = m_uri.group(1)
        # janela das 4 linhas seguintes — cobre qualquer ordem dos campos
        resto = "\n".join(texto[m_uri.end():].split("\n")[:4])
        m = re.search(r"sha256:\s*[\"']?([0-9a-fA-F]{64})[\"']?", resto)
        if m:
            pares.append((uri, m.group(1).lower()))
        else:
            sem_hash.append(uri)

    if sem_hash:
        print("  evidência SEM sha256 declarado:")
        for u in sem_hash:
            print(f"    {u}")
        print()

    if not pares:
        print("  nenhuma evidência com sha256 declarado")
        print("  — se a receita declara evidência, isto é defeito, não sucesso")
        print("EVIDENCIA=DIVERGE")
        return 1

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
