"""Acrescenta ao .claude/settings.json os caminhos REAIS do PDA.

O settings.json veio byte-a-byte da bancada e protege as pastas dela —
`fabrica/contracts/`, `fabrica/judge/` — deixando desprotegidos os quatro
caminhos que a doutrina manda cercar NUMA FÁBRICA GERADA:

  _raw/  contracts/  cvg/docs/adrs/  evidence/

O próprio arquivo previa este erro nas linhas 31-35 e nomeava o remédio.
Este script executa esse remédio, preservando as regras que já existem.

Roda uma vez. Idempotente — não duplica regra já presente.
"""
import io
import json
from pathlib import Path

SETTINGS = Path(".claude/settings.json")

NOVAS = [
    # a fonte: 12,2 GB, chmod 444 + sha256 (W-1)
    "Write(_raw/**)",
    "Edit(_raw/**)",
    # o juiz desta fábrica
    "Write(contracts/**)",
    "Edit(contracts/**)",
    # ⚠ cvg/docs/adrs/, NÃO docs/adrs/ — o padrão do inss casaria com zero
    "Write(cvg/docs/adrs/**)",
    "Edit(cvg/docs/adrs/**)",
    # os requisitos que os ADRs aterram
    "Write(cvg/docs/tech-spec/**)",
    "Edit(cvg/docs/tech-spec/**)",
    # _ancora.json é o oráculo
    "Write(evidence/**)",
    "Edit(evidence/**)",
    # quem mede a âncora não pode ser editado por quem é julgado por ela
    "Write(scripts/medir_*.py)",
    "Edit(scripts/medir_*.py)",
    # os caminhos equivalentes por shell
    "Bash(tee _raw/*)",
    "Bash(tee contracts/*)",
    "Bash(tee cvg/docs/adrs/*)",
    "Bash(tee evidence/*)",
    "Bash(chmod *_raw/*)",
    "Bash(rm -rf contracts*)",
    "Bash(rm -rf evidence*)",
    "Bash(rm -rf cvg/docs*)",
]


def main() -> int:
    d = json.loads(io.open(SETTINGS, encoding="utf-8").read())
    deny = d["permissions"]["deny"]
    antes = len(deny)

    for regra in NOVAS:
        if regra not in deny:
            deny.append(regra)

    d["_comentario"] = [
        "CERCA DO AGENTE — fábrica PDA, competência 2026-01.",
        "",
        "Precisa CONCORDAR com .cvg/gate.yaml. Duas cercas que discordam são",
        "uma cerca com buraco, e ninguém sabe qual metade vale.",
        "Confere: python3 scripts/verificar_cercas.py",
        "",
        "Os quatro caminhos da doutrina, com os nomes REAIS deste projeto:",
        "  _raw/            bytes originais, chmod 444 + sha256 (W-1)",
        "  contracts/       o juiz desta fábrica",
        "  cvg/docs/adrs/   decisões vinculantes — NÃO é docs/adrs/",
        "  evidence/        _ancora.json e os pacotes por execução",
        "",
        "As regras de fabrica/ e converge/ vieram da bancada e continuam",
        "valendo: aquelas pastas existem aqui como cópia vendorizada.",
    ]

    io.open(SETTINGS, "w", encoding="utf-8").write(
        json.dumps(d, indent=2, ensure_ascii=False) + "\n"
    )

    print(f"  regras antes : {antes}")
    print(f"  regras depois: {len(deny)}")
    print(f"  acrescentadas: {len(deny) - antes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
