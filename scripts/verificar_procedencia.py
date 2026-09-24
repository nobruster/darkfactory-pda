"""Confere que todo código em src/ foi autorizado por uma Task-Spec.

A cerca responde "posso escrever aqui?". Ela não responde a inversa — "este
arquivo foi autorizado por alguém?" (Regra 11). No PDA, dezesseis arquivos
foram escritos direto, sem BRD, costura, adversário, selo ou escopo, e nada
reprovou.

Este script fecha isso: lista o código em `src/` e acusa o que nenhuma
Task-Spec SELADA declara em `creates_paths` ou `touches_paths`.

⚠ Até 2026-09-24 ele lia só `cvg/tasks/`, e toda composição arquivada
(`cvg/composicao-*/tasks/`, para a raiz servir a seguinte) sumia da conta:
acusava 9 de 16 arquivos, seis deles autorizados. Um token sempre vermelho
não distingue o arquivo novo sem autorização — é o verificador que nunca
reprova, pelo avesso. Agora lê as duas, e só folha com `signed_off_sig`
autoriza: folha sem selo não passou pelo Pass 5.

E confere `.yaml` além de `.py`: a ontologia (ADR 0014) é dado versionado em
src/ e governa as projeções tanto quanto código.

Token: PROCEDENCIA=OK|SEM_AUTORIZACAO|ERRO
"""
import re
import sys
from pathlib import Path

FONTES = ["cvg/tasks/T-*.md", "cvg/composicao-*/tasks/T-*.md"]
RAIZES = ["src"]
SUFIXOS = (".py", ".yaml")

# Código de apoio que não nasce de tarefa por natureza. Cada isenção é
# nomeada, não um padrão amplo: uma isenção genérica devolveria o mesmo
# furo com outro nome.
ISENTOS = {
    "src/pda/__init__.py",
    "src/produtor/__init__.py",
}


def _folhas() -> list[Path]:
    return sorted(p for padrao in FONTES for p in Path(".").glob(padrao))


def _autorizados(folhas: list[Path]) -> tuple[dict[str, str], list[Path]]:
    """Todo caminho que alguma Task-Spec SELADA declara, e qual delas."""
    mapa: dict[str, str] = {}
    sem_selo = []
    for spec in folhas:
        texto = spec.read_text(encoding="utf-8", errors="replace")
        if "signed_off_sig" not in texto:
            sem_selo.append(spec)
            continue
        origem = spec.stem if spec.parent == Path("cvg/tasks") else f"{spec.parent.parent.name}/{spec.stem}"
        for campo in ("creates_paths", "touches_paths"):
            for m in re.finditer(rf"{campo}:\s*\[([^\]]*)\]", texto):
                for caminho in m.group(1).split(","):
                    c = caminho.strip().strip("'\"")
                    if c:
                        mapa.setdefault(c, origem)
    return mapa, sem_selo


def main() -> int:
    if not Path("cvg").is_dir():
        print("  cvg/ não existe — rode da raiz do repositório", file=sys.stderr)
        print("PROCEDENCIA=ERRO")
        return 1

    folhas = _folhas()
    autorizados, sem_selo = _autorizados(folhas)
    print(f"  folhas: {len(folhas)}  seladas: {len(folhas) - len(sem_selo)}")
    for f in sem_selo:
        print(f"  sem selo, não autoriza: {f}")
    if not autorizados:
        print("  nenhuma Task-Spec selada declara caminhos")
        print("  — sem isso, não há o que conferir contra")
        print("PROCEDENCIA=ERRO")
        return 1

    arquivos = sorted(
        str(p) for raiz in RAIZES
        for p in Path(raiz).rglob("*")
        if p.is_file() and p.suffix in SUFIXOS and "__pycache__" not in str(p)
    )
    if not arquivos:
        print(f"  nenhum {SUFIXOS} em {RAIZES}")
        print("  — nada a conferir não é o mesmo que tudo autorizado")
        print("PROCEDENCIA=ERRO")
        return 1

    sem = []
    for f in arquivos:
        if f in ISENTOS:
            print(f"  isento     {f}")
            continue
        if f in autorizados:
            print(f"  ok         {f:<40} {autorizados[f]}")
        else:
            print(f"  SEM SPEC   {f}")
            sem.append(f)

    print()
    if sem:
        print(f"  {len(sem)} de {len(arquivos)} sem Task-Spec selada:")
        for f in sem:
            print(f"    {f}")
        print()
        print("  Código sem Task-Spec não passou por costura, adversário,")
        print("  selo HMAC nem escopo de escrita declarado. O Pass 8 aplica")
        print("  path_policy só DENTRO do loop — por fora dele, nada pega.")
        print("PROCEDENCIA=SEM_AUTORIZACAO")
        return 1

    print(f"  {len(arquivos)} arquivo(s), todos autorizados por Task-Spec selada")
    print("PROCEDENCIA=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
