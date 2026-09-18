#!/usr/bin/env python3
"""Projeta as lanes planas do Seamwise na forma de diretório que o Converge gateia.

Por que existe
--------------
As duas ferramentas discordam do layout, e a discordância é silenciosa de um
lado:

    seamwise emite : swimlanes/LANE-CONTRATO.md          (arquivo plano)
    converge espera: swimlanes/<seam>/_lane.md           (diretório + PRD)

Medido no código:
  - check-consensus-gate.sh:189  procura <dir>/_lane.md, falha com
    "no swimlane PRDs — nothing to gate"     -> o gate ACUSA
  - dispatch-review.sh:86        varre "$SKETCH_DIR"/*/*.md, acha zero
    arquivos e monta o prompt vazio          -> o dispatcher NÃO acusa

O segundo é o perigoso: o adversário produziria objeções sobre nada, e o gate
recusaria depois por outro motivo — resultado certo pela razão errada.

Por que projeta em vez de mover
-------------------------------
O Seamwise regrava `swimlanes/` a cada `plan`. Mover quebraria o `compile`.
A projeção é derivada e descartável: apague e rode de novo.

Por que copia em vez de symlink
-------------------------------
`git config core.symlinks` é **false** neste repositório (Windows). Um symlink
viraria um arquivo de texto com o caminho dentro, e o gate leria o caminho
como se fosse o PRD.

Como a cópia não mente
----------------------
`--check` recompara o sha256 de cada origem contra o que foi projetado. Se o
Seamwise regravou uma lane e a projeção ficou para trás, isso **falha** em vez
de passar despercebido — que é o defeito que esta ponte existe para não criar.

Uso
---
    python3 fabrica/ponte/lanes_para_converge.py \\
        --de   cvg/swimlanes/workspace/seamwise/swimlanes \\
        --para cvg/swimlanes/lanes

    python3 fabrica/ponte/lanes_para_converge.py --check ...   # só verifica

Token final estável (última linha), para um harness greppar uma linha só:
    PONTE_LANES=OK | STALE | EMPTY | ERROR
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

# O Converge exige esta linha nas 15 primeiras de todo PRD de lane.
# É um token de compatibilidade CONGELADO, não uma escolha: o fork foi
# aposentado na v3.4 e a única rota é B (task-driven).
# Ver converge/skills/sketch-plans-adversarial-review/references/the-fork.md
FORK_LINE = "FORK: B (task-driven)"
FORK_REASON = (
    "rota única desde a v3.4 — o consenso sempre entrega à decomposição "
    "por tarefas; não é uma escolha desta fábrica."
)

# O mesmo regex que check-consensus-gate.sh:205 aplica.
FORK_RE = re.compile(r"FORK[:\s]*[AB]\b", re.I)
DRIVEN_RE = re.compile(r"plan-driven|task-driven", re.I)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seam_de(lane: Path) -> str:
    """LANE-CONTRATO.md -> contrato. O nome do diretório não identifica a lane
    para o gate (ele procura o PRD dentro), mas um nome legível ajuda humanos."""
    nome = lane.stem
    return (nome[5:] if nome.upper().startswith("LANE-") else nome).lower()


def legs_da_lane(lane: Path) -> list[str]:
    """Os ids de leg listados no frontmatter da lane."""
    ids: list[str] = []
    dentro = False
    for linha in lane.read_text(encoding="utf-8").splitlines():
        if linha.strip() == "legs:":
            dentro = True
            continue
        if dentro:
            m = re.match(r"^\s*-\s+(\S+)", linha)
            if m:
                ids.append(m.group(1))
            else:
                break
    return ids


def projetar(origem: Path, destino: Path, pasta_legs: Path | None) -> tuple[str, str]:
    """Escreve <destino>/<seam>/_lane.md com a linha FORK no topo, e ao lado
    dele os LEG-*.md que a lane referencia.

    Levar os legs junto não é cosmético: o dispatcher varre `<dir>/*/*.md` e
    o adversário revisa o que encontrar. Projetar só o índice fez o Pass 4
    atacar cabeçalhos sem o conteúdo que será implementado — objeção C1, de
    2026-09-17.

    Devolve (seam, sha256 da ORIGEM) — é o hash da origem que prova de onde
    veio, não o do arquivo projetado.
    """
    seam = seam_de(origem)
    pasta = destino / seam
    pasta.mkdir(parents=True, exist_ok=True)

    corpo = origem.read_text(encoding="utf-8")
    origem_sha = sha256(origem)

    cabecalho = (
        f"{FORK_LINE} — {FORK_REASON}\n"
        f"\n"
        f"> Projetado de `{origem.name}` pelo Seamwise.\n"
        f"> **Não edite aqui** — edite a recipe e rode `seamwise plan`.\n"
        f"> origem sha256: `{origem_sha}`\n"
        f"\n"
        f"---\n\n"
    )
    (pasta / "_lane.md").write_text(cabecalho + corpo, encoding="utf-8")

    if pasta_legs is not None:
        for leg_id in legs_da_lane(origem):
            leg = pasta_legs / f"{leg_id}.md"
            if not leg.exists():
                continue
            leg_sha = sha256(leg)
            nota = (
                f"> Projetado de `{leg.name}` pelo Seamwise.\n"
                f"> **Não edite aqui** — edite a recipe e rode `seamwise plan`.\n"
                f"> origem sha256: `{leg_sha}`\n\n---\n\n"
            )
            (pasta / leg.name).write_text(
                nota + leg.read_text(encoding="utf-8"), encoding="utf-8"
            )

    return seam, origem_sha


def sha_registrado(prd: Path) -> str | None:
    for linha in prd.read_text(encoding="utf-8").splitlines()[:15]:
        m = re.search(r"origem sha256: `([0-9a-f]{64})`", linha)
        if m:
            return m.group(1)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--de", required=True, help="pasta das lanes planas do seamwise")
    ap.add_argument("--para", required=True, help="pasta destino, no layout do converge")
    ap.add_argument(
        "--legs",
        help="pasta dos LEG-*.md (padrão: ../legs ao lado de --de). "
        "Sem eles o adversário revisa só os índices — objeção C1.",
    )
    ap.add_argument("--check", action="store_true", help="só verifica; não escreve")
    args = ap.parse_args()

    de, para = Path(args.de), Path(args.para)
    pasta_legs = Path(args.legs) if args.legs else de.parent / "legs"
    if not pasta_legs.is_dir():
        pasta_legs = None

    if not de.is_dir():
        print(f"erro: origem não existe: {de}", file=sys.stderr)
        print("PONTE_LANES=ERROR")
        return 2

    origens = sorted(de.glob("*.md"))
    if not origens:
        print(f"nenhuma lane em {de} — rode `seamwise plan` primeiro")
        print("PONTE_LANES=EMPTY")
        return 1

    if args.check:
        problemas: list[str] = []
        for origem in origens:
            prd = para / seam_de(origem) / "_lane.md"
            if not prd.exists():
                problemas.append(f"  FALTA    {origem.name} -> {prd}")
                continue
            registrado = sha_registrado(prd)
            atual = sha256(origem)
            if registrado != atual:
                problemas.append(
                    f"  DEFASADO {origem.name} — a origem mudou desde a projeção"
                )
                continue
            cab = "".join(prd.read_text(encoding="utf-8").splitlines(True)[:15])
            if not (FORK_RE.search(cab) and DRIVEN_RE.search(cab)):
                problemas.append(f"  SEM FORK {prd}")
                continue

            # os legs também: um leg defasado é conteúdo desatualizado sendo
            # revisado como se fosse o atual
            falhou_leg = False
            if pasta_legs is not None:
                for leg_id in legs_da_lane(origem):
                    leg = pasta_legs / f"{leg_id}.md"
                    if not leg.exists():
                        continue
                    proj = prd.parent / leg.name
                    if not proj.exists():
                        problemas.append(f"  FALTA    {leg.name} -> {proj}")
                        falhou_leg = True
                    elif sha_registrado(proj) != sha256(leg):
                        problemas.append(
                            f"  DEFASADO {leg.name} — a origem mudou desde a projeção"
                        )
                        falhou_leg = True
            if falhou_leg:
                continue

            n_legs = len(list(prd.parent.glob("LEG-*.md")))
            print(f"  ok       {origem.name} -> {prd.parent.name}/ (+{n_legs} leg)")

        if problemas:
            print("\n".join(problemas))
            print(f"\n{len(problemas)} de {len(origens)} lane(s) fora de dia.")
            print("PONTE_LANES=STALE")
            return 1

        print(f"\n{len(origens)} lane(s) projetadas e conferidas contra a origem.")
        print("PONTE_LANES=OK")
        return 0

    if pasta_legs is None:
        print("  AVISO: pasta de legs não encontrada — só os índices serão")
        print("         projetados, e o adversário revisará menos (ver C1).")

    for origem in origens:
        seam, _ = projetar(origem, para, pasta_legs)
        n = len(list((para / seam).glob("LEG-*.md")))
        print(f"  {origem.name} -> {para}/{seam}/ (_lane.md + {n} leg)")

    print(f"\n{len(origens)} lane(s) projetadas.")
    print(f"Confira com: --check --de {de} --para {para}")
    print("PONTE_LANES=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
