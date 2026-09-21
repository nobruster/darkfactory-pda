#!/usr/bin/env python3
"""Confere se as dependências dos evals existem, ANTES de gastar tentativas.

Por que existe
--------------
O `cvg doctor host` verifica git, bash, python3, shellcheck e sha256 — o que
a *máquina* precisa. Ele não confere o que os **evals da tarefa** importam.

Medido no Pass 8 desta fábrica: três dos quatro bloqueios foram ambientais,
não de lógica.

    pytest: command not found          -> eval quebrado, não falha limpa
    fatal: empty ident name            -> settlement recusado
    ModuleNotFoundError: No module 'yaml'

O custo não é o erro — é o que ele faz o loop fazer. O agente gastou uma
tentativa inteira de LLM tentando consertar código que estava correto,
porque a mensagem que chegou até ele foi `ModuleNotFoundError`, não
"falta uma dependência no ambiente".

O que confere
-------------
1. `required_tools` do frontmatter — cada um tem de estar no PATH
2. Todo `import X` / `from X import` dentro dos arquivos de teste que os
   evals invocam — tem de importar de verdade
3. Identidade git (`user.name` e `user.email`) — o settlement commita

Uso
---
    python3 fabrica/ponte/checar_deps.py cvg/tasks/T-*.md

Token final estável: DEPS=OK | DEPS=MISSING | DEPS=ERROR
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

# módulos que vêm com o Python — não valem como dependência ausente
STDLIB = {
    "json", "os", "sys", "re", "pathlib", "typing", "dataclasses", "decimal",
    "datetime", "hashlib", "subprocess", "collections", "itertools", "math",
    "unittest", "tempfile", "shutil", "argparse", "textwrap", "io", "csv",
    "functools", "enum", "abc", "contextlib", "glob", "time", "logging",
}

IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][\w]*)", re.M)
# indentado no frontmatter da folha — âncorar em ^ não casa
TOOLS_RE = re.compile(r"^\s*required_tools:\s*\[([^\]]*)\]", re.M)
# o comando do eval cita o arquivo de teste; pode ou não existir ainda
EVAL_PATH_RE = re.compile(r"(?:pytest|python3?)\s[^\n]*?([\w/]+/test_[\w]+\.py)")


def frontmatter_tools(texto: str) -> list[str]:
    m = TOOLS_RE.search(texto)
    if not m:
        return []
    return [t.strip().strip("\"'") for t in m.group(1).split(",") if t.strip()]


def modulo_importa(nome: str) -> bool:
    r = subprocess.run(
        [sys.executable, "-c", f"import {nome}"],
        capture_output=True, text=True, check=False,
    )
    return r.returncode == 0


def git_tem_identidade(repo: Path) -> tuple[bool, str]:
    def cfg(k: str) -> str:
        r = subprocess.run(["git", "-C", str(repo), "config", "--get", k],
                           capture_output=True, text=True, check=False)
        return r.stdout.strip()
    nome, email = cfg("user.name"), cfg("user.email")
    if nome and email:
        return True, f"{nome} <{email}>"
    faltando = " e ".join(x for x, v in (("user.name", nome), ("user.email", email)) if not v)
    return False, f"falta {faltando}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("specs", nargs="+", help="as Task-Specs a conferir")
    ap.add_argument("--repo", default=".", help="raiz do repositório")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    faltas: list[str] = []

    ok, detalhe = git_tem_identidade(repo)
    print(f"  {'ok  ' if ok else 'FALTA'} identidade git — {detalhe}")
    if not ok:
        faltas.append("identidade git (o settlement commita)")

    ferramentas: set[str] = set()
    modulos: set[str] = set()
    pendentes: set[str] = set()

    for s in args.specs:
        p = Path(s)
        if not p.is_file():
            print(f"  ERRO  spec não encontrada: {s}", file=sys.stderr)
            print("DEPS=ERROR")
            return 2
        texto = p.read_text(encoding="utf-8")
        ferramentas.update(frontmatter_tools(texto))
        # os arquivos de teste que os evals invocam. Antes do trabalho existir
        # eles ainda não foram escritos — nesse caso não há import a conferir,
        # e é a lista de required_tools que segura a verificação.
        for rel in set(EVAL_PATH_RE.findall(texto)):
            alvo = repo / rel
            if alvo.is_file():
                for mod in set(IMPORT_RE.findall(alvo.read_text(encoding="utf-8"))):
                    if mod not in STDLIB:
                        modulos.add(mod)
            else:
                pendentes.add(rel)

    for t in sorted(ferramentas):
        achou = shutil.which(t) is not None
        print(f"  {'ok  ' if achou else 'FALTA'} ferramenta {t}")
        if not achou:
            faltas.append(f"ferramenta {t}")

    for m in sorted(modulos):
        achou = modulo_importa(m)
        print(f"  {'ok  ' if achou else 'FALTA'} módulo {m}")
        if not achou:
            faltas.append(f"módulo python {m}")

    if pendentes:
        print()
        print(f"  nota  {len(pendentes)} teste(s) ainda não escrito(s) — os imports")
        print("        deles só podem ser conferidos depois que o loop rodar:")
        for t in sorted(pendentes):
            print(f"          {t}")
        print("        até lá, required_tools é o que segura a verificação.")

    print()
    if faltas:
        print(f"{len(faltas)} dependência(s) ausente(s):")
        for f in faltas:
            print(f"  - {f}")
        print()
        print("Resolva ANTES de rodar o loop: cada uma custa uma tentativa de LLM")
        print("gasta consertando código que provavelmente está correto.")
        print("DEPS=MISSING")
        return 1

    print(f"{len(ferramentas)} ferramenta(s) e {len(modulos)} módulo(s) disponíveis.")
    print("DEPS=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
