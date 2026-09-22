"""Pré-voo da receita: pega a armadilha do ': ' antes do map.

Um ': ' dentro de escalar sem aspas vira mapa, e o seamwise devolve
recipe_unreadable. Custou cinco ciclos nesta descida. Isto acusa antes.

Token: YAML_RECEITA=OK|SUSPEITO|ERRO
"""
import io
import re
import sys

RECEITA = "cvg/swimlanes/pda-recipe.yaml"

# ': ' em texto livre, fora de uma chave YAML legítima no início da linha
SUSPEITO = re.compile(r"\S: \S")
CHAVE = re.compile(r"^\s*-?\s*[\w_]+:\s")


def main() -> int:
    caminho = sys.argv[1] if len(sys.argv) > 1 else RECEITA
    try:
        linhas = io.open(caminho, encoding="utf-8").read().split("\n")
    except FileNotFoundError:
        print(f"erro: {caminho} não encontrado", file=sys.stderr)
        print("YAML_RECEITA=ERRO")
        return 1

    # Só interessa o ': ' em escalar de UMA linha (given/when/then/description),
    # onde ele quebra. Dentro de bloco '>-' o YAML já o trata como texto.
    ESCALAR = re.compile(r"^\s*(-\s+)?(given|when|then|description|reason|instead|goal|summary|rationale|title|name):\s+(?!>-|\|)(.+)$")

    achados: list[tuple[int, str]] = []
    for n, linha in enumerate(linhas, 1):
        m = ESCALAR.match(linha)
        if not m:
            continue
        valor = m.group(3)
        if valor.startswith(("'", '"')):
            continue
        for s in SUSPEITO.finditer(valor):
            trecho = valor[max(0, s.start() - 30) : s.start() + 30]
            achados.append((n, trecho.strip()))

    # PyYAML é OBRIGATÓRIO. O safe_load é o único mecanismo que pega a
    # quebra de verdade — a camada de regex abaixo tem cobertura parcial.
    # Tratar a ausência como sucesso seria verde permanente num CI enxuto.
    try:
        import yaml
    except ImportError:
        print("  PyYAML ausente — sem ele não há verificação de verdade")
        print("  instale: pip install pyyaml")
        print("YAML_RECEITA=ERRO")
        return 1

    try:
        yaml.safe_load(io.open(caminho, encoding="utf-8"))
        parseou = True
    except Exception as e:
        parseou = False
        print(f"  yaml.safe_load FALHOU: {e}")

    if achados:
        print(f"  {len(achados)} ocorrência(s) de ': ' em texto livre:")
        for n, t in achados[:20]:
            print(f"    linha {n}: …{t}…")
        print()
        print("  troque por travessão — ': ' vira mapa e o map reprova")

    if parseou is False:
        print("YAML_RECEITA=ERRO")
        return 1
    if achados:
        print("YAML_RECEITA=SUSPEITO")
        return 1

    print(f"  {caminho} parseia e não tem ': ' solto")
    print("YAML_RECEITA=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
