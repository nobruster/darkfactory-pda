"""Confere que todo código em src/ foi autorizado por uma Task-Spec.

A cerca (`.cvg/gate.yaml` + `.claude/settings.json`) impede EDITAR o oráculo.
Ela responde "posso escrever aqui?". Não responde a pergunta inversa:

    este arquivo foi autorizado por alguém?

E foi por aí que 16 arquivos entraram neste repositório sem passar por
costura, objeção de adversário, selo HMAC ou escopo de escrita declarado —
entre eles o produtor Spark, que gravou 50 mil linhas de teste no mesmo
caminho do dado real.

O Pass 8 aplica `path_policy` e bloqueia arquivo fora do `creates_paths` —
mas só DENTRO do loop. Código escrito por fora nunca encontra esse gate.

Este script fecha isso: lista o código em `src/` e acusa o que nenhuma
Task-Spec declara em `creates_paths` ou `touches_paths`.

Token: PROCEDENCIA=OK|SEM_AUTORIZACAO|ERRO
"""
import re
import sys
from pathlib import Path

TAREFAS = Path("cvg/tasks")
RAIZES = ["src"]

# Código de apoio que não nasce de tarefa por natureza. Cada isenção é
# nomeada, não um padrão amplo: uma isenção genérica devolveria o mesmo
# furo com outro nome.
ISENTOS = {
    "src/pda/__init__.py",
    "src/produtor/__init__.py",
}


def _autorizados() -> dict[str, str]:
    """Todo caminho que alguma Task-Spec declara, e qual delas."""
    mapa: dict[str, str] = {}
    if not TAREFAS.is_dir():
        return mapa

    for spec in sorted(TAREFAS.glob("T-*.md")):
        texto = spec.read_text(encoding="utf-8", errors="replace")
        for campo in ("creates_paths", "touches_paths"):
            for m in re.finditer(rf"{campo}:\s*\[([^\]]*)\]", texto):
                for caminho in m.group(1).split(","):
                    c = caminho.strip().strip("'\"")
                    if c:
                        mapa.setdefault(c, spec.stem)
    return mapa


def main() -> int:
    if not TAREFAS.is_dir():
        print(f"  {TAREFAS} não existe — rode da raiz do repositório",
              file=sys.stderr)
        print("PROCEDENCIA=ERRO")
        return 1

    autorizados = _autorizados()
    if not autorizados:
        print("  nenhuma Task-Spec declara caminhos")
        print("  — sem isso, não há o que conferir contra")
        print("PROCEDENCIA=ERRO")
        return 1

    arquivos = sorted(
        str(p) for raiz in RAIZES
        for p in Path(raiz).rglob("*.py")
        if "__pycache__" not in str(p)
    )
    if not arquivos:
        print(f"  nenhum .py em {RAIZES}")
        print("  — nada a conferir não é o mesmo que tudo autorizado")
        print("PROCEDENCIA=ERRO")
        return 1

    sem = []
    for f in arquivos:
        if f in ISENTOS:
            print(f"  isento     {f}")
            continue
        if f in autorizados:
            print(f"  ok         {f:<36} {autorizados[f]}")
        else:
            print(f"  SEM SPEC   {f}")
            sem.append(f)

    print()
    if sem:
        print(f"  {len(sem)} de {len(arquivos)} sem Task-Spec:")
        for f in sem:
            print(f"    {f}")
        print()
        print("  Código sem Task-Spec não passou por costura, adversário,")
        print("  selo HMAC nem escopo de escrita declarado. O Pass 8 aplica")
        print("  path_policy só DENTRO do loop — por fora dele, nada pega.")
        print("PROCEDENCIA=SEM_AUTORIZACAO")
        return 1

    print(f"  {len(arquivos)} arquivo(s), todos autorizados por Task-Spec")
    print("PROCEDENCIA=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
