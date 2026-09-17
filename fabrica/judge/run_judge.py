#!/usr/bin/env python3
"""Runner do juiz — Fase 0 (intake) + Fase 6 (golden-match).

Julga UMA execução do pipeline contra seu oráculo aprovado, escreve o pacote
de evidência, e sai com código 0 (verde) ou 1 (empacado).

Este script nunca constrói nada e nunca edita uma árvore congelada: executa o
que existe, reporta o que não existe, e empaca no primeiro portão que falha.

    python judge/run_judge.py --oracle contracts/oracles/exemplo-lote-001.json \
                              --actual saida/resultado.json

    python judge/run_judge.py --oracle ... --actual ... --reference atual.json

Saída: evidence/<batch_id>/golden-match.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from judge.golden_match import (  # noqa: E402
    GoldenMatchError,
    compare_aggregate,
    compare_records,
    load_oracle,
)

REPO = Path(__file__).resolve().parents[1]

PASS, STALL = "PASS ", "STALL"

# O console do Windows usa cp1252 por padrão e engasga com acento.
# Sem isto, a saída do juiz fica ilegível justamente quando ele acusa um erro.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


class Stall(Exception):
    """Um portão recusou. Nada a jusante é inventado."""


def gate(name: str, ok: bool, detail: str = "") -> None:
    mark = PASS if ok else STALL
    line = f"  [{mark}] {name}"
    if detail:
        line += f" — {detail}"
    print(line)
    if not ok:
        raise Stall(f"{name}: {detail}")


def load_json(path: Path, what: str) -> dict:
    if not path.exists():
        raise Stall(f"{what} ausente: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Stall(f"{what} não é JSON válido: {exc}") from exc


def main() -> int:
    ap = argparse.ArgumentParser(description="Julga uma execução contra o oráculo.")
    ap.add_argument("--oracle", required=True, type=Path,
                    help="o oráculo aprovado (a resposta certa)")
    ap.add_argument("--actual", required=True, type=Path,
                    help="o que o pipeline produziu")
    ap.add_argument("--reference", type=Path,
                    help="o que o sistema atual produziu (opcional)")
    ap.add_argument("--evidence-dir", type=Path, default=REPO / "evidence")
    args = ap.parse_args()

    print("\n" + "=" * 62)
    print("  FASE 0 — INTAKE")
    print("=" * 62)

    try:
        # O portão mais barato do sistema: falha em segundos, em vez de
        # falhar depois de um build que ninguém consegue validar.
        gate("oráculo existe", args.oracle.exists(), str(args.oracle))
        oracle = load_oracle(args.oracle)
        gate("oráculo tem aprovação", True,
             f"por {oracle.get('approved_by')} em {oracle.get('approved_at')}")
        gate("oráculo tem saída esperada",
             bool(oracle.get("aggregate") or oracle.get("records")),
             "aggregate ou records")

        actual = load_json(args.actual, "resultado do pipeline")
        gate("resultado do pipeline existe", True, str(args.actual))

        reference = None
        if args.reference:
            reference = load_json(args.reference, "resultado do sistema atual")
            gate("referência do sistema atual existe", True, str(args.reference))

    except (Stall, GoldenMatchError) as exc:
        print(f"\n  RECUSADO NA FASE 0: {exc}\n")
        print("  Sem oráculo, não se constrói. Nenhum trabalho foi feito.\n")
        return 1

    batch_id = oracle.get("batch_id", "sem-id")
    money = tuple(oracle.get("money_fields", ()))
    keys = tuple(oracle.get("key_fields", ()))
    approved = tuple(oracle.get("approved_changes", ()))

    print("\n" + "=" * 62)
    print("  FASE 6 — GOLDEN-MATCH")
    print("=" * 62)

    results = []

    if oracle.get("aggregate"):
        agg = compare_aggregate(
            batch_id=batch_id,
            actual=actual.get("aggregate", actual),
            contract=oracle["aggregate"],
            reference=(reference or {}).get("aggregate") if reference else None,
            money_fields=money,
            approved_changes=approved,
        )
        results.append(("agregado", agg))

    if oracle.get("records") and keys:
        rec = compare_records(
            batch_id=batch_id,
            actual=actual.get("records", []),
            contract=oracle["records"],
            key_fields=keys,
            money_fields=money,
            approved_changes=approved,
        )
        results.append(("registros", rec))

    if not results:
        print("\n  RECUSADO: o oráculo não define nem aggregate nem records.\n")
        return 1

    total_unexplained = 0
    for scope, r in results:
        icon = "OK  " if r.resolved else "STALL"
        print(f"  [{icon}] {scope}: {r.status} "
              f"({r.unexplained_count} inexplicada(s))")
        total_unexplained += r.unexplained_count

        for d in r.differences:
            flag = "!" if d.classification not in ("APPROVED_BEHAVIOR_CHANGE",) else " "
            print(f"        {flag} {d.field_name}: "
                  f"obtido={d.actual} esperado={d.reference} "
                  f"[{d.classification}]")

    # Evidência — sem pacote, não liquida.
    out = args.evidence_dir / batch_id / "golden-match.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "batch_id": batch_id,
        "oracle": str(args.oracle),
        "approved_by": oracle.get("approved_by"),
        "resolved": total_unexplained == 0,
        "unexplained_count": total_unexplained,
        "scopes": {scope: r.as_dict() for scope, r in results},
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 62)
    if total_unexplained == 0:
        print(f"  RESOLVIDO — zero diferenças inexplicadas")
        print(f"  evidência: {out}")
        print("=" * 62 + "\n")
        return 0

    print(f"  EMPACADO — {total_unexplained} diferença(s) inexplicada(s)")
    print(f"  evidência: {out}")
    print()
    print("  Não existe tolerância nesta fase. Classifique a diferença")
    print("  ou corrija o pipeline. NÃO edite o oráculo para ficar verde.")
    print("=" * 62 + "\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
