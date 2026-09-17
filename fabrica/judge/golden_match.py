"""Golden-match: compara o resultado do pipeline com o oráculo aprovado.

Toda comparação responde duas perguntas SEPARADAS:

1. **Correção de negócio** — o resultado satisfaz o contrato aprovado?
2. **Paridade com a referência** — o resultado bate com o sistema atual?

Um defeito na fonte faz essas respostas DIVERGIREM. É por isso que elas são
respondidas separadamente e toda diferença é classificada, em vez de
compensada (netted out).

NÃO EXISTE TOLERÂNCIA NESTE MÓDULO. Isso é deliberado: o portão de release não
permite diferença financeira inexplicada, e uma tolerância configurável é
exatamente como um centavo inexplicado vira um centavo aceito.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

# --------------------------------------------------------------------------
# Classificações — os seis códigos. Toda diferença recebe exatamente um.
# --------------------------------------------------------------------------

CONFIRMED_SOURCE_DEFECT = "CONFIRMED_SOURCE_DEFECT"
CONFIRMED_LEGACY_DEFECT = "CONFIRMED_LEGACY_DEFECT"
MODERN_DEFECT = "MODERN_DEFECT"
APPROVED_BEHAVIOR_CHANGE = "APPROVED_BEHAVIOR_CHANGE"
CONTRACT_AMBIGUITY = "CONTRACT_AMBIGUITY"
UNRESOLVED = "UNRESOLVED"

CLASSIFICATIONS = (
    CONFIRMED_SOURCE_DEFECT,
    CONFIRMED_LEGACY_DEFECT,
    MODERN_DEFECT,
    APPROVED_BEHAVIOR_CHANGE,
    CONTRACT_AMBIGUITY,
    UNRESOLVED,
)

# Uma diferença só é "explicada" se sua classificação for uma dessas.
# MODERN_DEFECT não está aqui de propósito: seu código errado não é
# uma explicação, é um bug. O portão bloqueia.
EXPLAINED = (
    CONFIRMED_SOURCE_DEFECT,
    CONFIRMED_LEGACY_DEFECT,
    APPROVED_BEHAVIOR_CHANGE,
)


class GoldenMatchError(RuntimeError):
    """A comparação não pôde ser feita contra as referências exigidas."""


# --------------------------------------------------------------------------
# Estruturas
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Difference:
    """Uma diferença classificada entre dois resultados."""

    scope: str           # "registro" | "agregado"
    key: str             # a chave do registro (ou "-" no agregado)
    field_name: str      # qual campo divergiu
    actual: str          # o que o pipeline produziu
    reference: str       # o que a referência dizia
    reference_name: str  # "contrato" | "sistema-atual"
    classification: str

    def as_dict(self) -> dict[str, str]:
        return {
            "scope": self.scope,
            "key": self.key,
            "field": self.field_name,
            "actual": self.actual,
            "reference": self.reference,
            "reference_name": self.reference_name,
            "classification": self.classification,
        }


@dataclass(slots=True)
class MatchResult:
    """O veredito de uma execução."""

    batch_id: str
    business_correct: bool           # pergunta 1: bate com o contrato?
    parity_with_reference: bool | None  # pergunta 2: bate com o atual? (None = não comparado)
    differences: list[Difference] = field(default_factory=list)

    @property
    def unexplained(self) -> list[Difference]:
        return [d for d in self.differences if d.classification not in EXPLAINED]

    @property
    def unexplained_count(self) -> int:
        return len(self.unexplained)

    @property
    def resolved(self) -> bool:
        """O portão. Zero diferenças inexplicadas — sem tolerância."""
        return self.unexplained_count == 0

    @property
    def status(self) -> str:
        if not self.differences:
            return "MATCHED"
        if self.resolved:
            return "RESOLVED"
        return "STALLED"

    def as_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "status": self.status,
            "business_correct": self.business_correct,
            "parity_with_reference": self.parity_with_reference,
            "resolved": self.resolved,
            "unexplained_count": self.unexplained_count,
            "differences": [d.as_dict() for d in self.differences],
        }

    def write_evidence(self, path: Path) -> Path:
        """Grava o pacote de evidência. Sem pacote, não liquida."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.as_dict(), indent=2, ensure_ascii=False))
        return path


# --------------------------------------------------------------------------
# Normalização — dinheiro é Decimal exato, nunca float
# --------------------------------------------------------------------------


def as_decimal(value: Any) -> Decimal:
    """Converte para Decimal exato.

    float é proibido: 0.1 + 0.2 != 0.3 em binário, e é assim que um
    centavo some sem ninguém ver.
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        raise GoldenMatchError(
            f"float proibido em campo monetário: {value!r}. "
            "Use str ou Decimal — float perde centavos silenciosamente."
        )
    return Decimal(str(value).strip())


def normalize(value: Any, *, money: bool = False) -> str:
    """Normaliza um valor para comparação estável.

    Dinheiro é comparado por VALOR, não por texto. Decimal("173.450") e
    "173.45" são o mesmo dinheiro — normalize() remove o zero à direita
    para que a comparação de string não invente uma diferença que não existe.

    Um juiz que acusa diferença onde não há é tão inútil quanto um que
    deixa passar: as duas falhas destroem a confiança no portão.
    """
    if value is None:
        return ""
    if money:
        return _canonical_money(as_decimal(value))
    return str(value).strip()


def _canonical_money(amount: Decimal) -> str:
    """Forma canônica de um valor monetário: sem zeros à direita supérfluos.

    173.450 → 173.45     173.00 → 173     0E-8 → 0
    O que importa é o valor, e valores iguais precisam da mesma string.
    """
    normalized = amount.normalize()
    # normalize() vira notação científica em inteiros grandes (1E+3).
    # to_integral_value() recupera a forma posicional.
    if normalized == normalized.to_integral_value():
        normalized = normalized.quantize(Decimal(1))
    return format(normalized, "f")


# --------------------------------------------------------------------------
# Classificação — a decisão de QUEM está errado
# --------------------------------------------------------------------------


def classify(
    *,
    matches_contract: bool,
    matches_reference: bool,
    source_declared_wrong: bool = False,
    approved_change: bool = False,
) -> str:
    """Decide quem está errado quando há uma diferença.

    A tabela-verdade:

    | bate contrato | bate atual | significa                              |
    |---------------|------------|---------------------------------------|
    | sim           | não        | o sistema ATUAL está errado           |
    | não           | sim        | o código NOVO copiou o erro do atual  |
    | não           | não        | o código NOVO está errado sozinho     |
    """
    if approved_change:
        return APPROVED_BEHAVIOR_CHANGE
    if source_declared_wrong:
        return CONFIRMED_SOURCE_DEFECT
    if matches_contract and not matches_reference:
        # Você bate com a verdade, o sistema atual não. O atual é o errado.
        return CONFIRMED_LEGACY_DEFECT
    if not matches_contract:
        # Você não bate com a verdade. O bug é seu.
        return MODERN_DEFECT
    return UNRESOLVED


# --------------------------------------------------------------------------
# Comparação — agregado
# --------------------------------------------------------------------------


def compare_aggregate(
    *,
    batch_id: str,
    actual: Mapping[str, Any],
    contract: Mapping[str, Any],
    reference: Mapping[str, Any] | None = None,
    money_fields: Sequence[str] = (),
    approved_changes: Sequence[str] = (),
) -> MatchResult:
    """Compara o número final contra o contrato e (opcionalmente) o sistema atual.

    Este é o coração: a tabela agregada é onde o número errado aparece.

    Args:
        actual: o que seu pipeline produziu
        contract: o oráculo — a resposta certa aprovada
        reference: o que o sistema atual produziu (opcional)
        money_fields: campos que são dinheiro (viram Decimal exato)
        approved_changes: campos onde divergir é esperado e aprovado
    """
    differences: list[Difference] = []
    money = set(money_fields)
    approved = set(approved_changes)

    business_correct = True
    parity = None if reference is None else True

    for field_name in sorted(set(contract) | set(actual)):
        is_money = field_name in money
        got = normalize(actual.get(field_name), money=is_money)
        want = normalize(contract.get(field_name), money=is_money)

        matches_contract = got == want
        if not matches_contract:
            business_correct = False

        matches_reference = True
        if reference is not None:
            ref = normalize(reference.get(field_name), money=is_money)
            matches_reference = got == ref
            if not matches_reference:
                parity = False

        if matches_contract and matches_reference:
            continue

        # Há divergência. Classifique — não compense.
        code = classify(
            matches_contract=matches_contract,
            matches_reference=matches_reference,
            approved_change=field_name in approved,
        )

        if not matches_contract:
            differences.append(
                Difference(
                    scope="agregado",
                    key="-",
                    field_name=field_name,
                    actual=got,
                    reference=want,
                    reference_name="contrato",
                    classification=code,
                )
            )
        if reference is not None and not matches_reference:
            differences.append(
                Difference(
                    scope="agregado",
                    key="-",
                    field_name=field_name,
                    actual=got,
                    reference=normalize(reference.get(field_name), money=is_money),
                    reference_name="sistema-atual",
                    classification=code,
                )
            )

    return MatchResult(
        batch_id=batch_id,
        business_correct=business_correct,
        parity_with_reference=parity,
        differences=differences,
    )


# --------------------------------------------------------------------------
# Comparação — registro a registro
# --------------------------------------------------------------------------


def compare_records(
    *,
    batch_id: str,
    actual: Iterable[Mapping[str, Any]],
    contract: Iterable[Mapping[str, Any]],
    key_fields: Sequence[str],
    money_fields: Sequence[str] = (),
    approved_changes: Sequence[str] = (),
) -> MatchResult:
    """Compara linha a linha contra o oráculo, casando pela chave de negócio."""
    if not key_fields:
        raise GoldenMatchError(
            "key_fields é obrigatório: sem chave de negócio não há como casar "
            "as linhas, e comparar por posição é uma prova falsa."
        )

    money = set(money_fields)
    approved = set(approved_changes)

    def keyof(row: Mapping[str, Any]) -> str:
        return "|".join(normalize(row.get(k)) for k in key_fields)

    actual_by_key = {keyof(r): r for r in actual}
    contract_by_key = {keyof(r): r for r in contract}

    differences: list[Difference] = []
    business_correct = True

    for key in sorted(set(contract_by_key) | set(actual_by_key)):
        got_row = actual_by_key.get(key)
        want_row = contract_by_key.get(key)

        if got_row is None:
            business_correct = False
            differences.append(
                Difference("registro", key, "*", "<ausente>", "<esperado>",
                           "contrato", MODERN_DEFECT)
            )
            continue

        if want_row is None:
            business_correct = False
            differences.append(
                Difference("registro", key, "*", "<extra>", "<não esperado>",
                           "contrato", MODERN_DEFECT)
            )
            continue

        for field_name in sorted(set(want_row) | set(got_row)):
            is_money = field_name in money
            got = normalize(got_row.get(field_name), money=is_money)
            want = normalize(want_row.get(field_name), money=is_money)
            if got == want:
                continue
            business_correct = False
            code = (APPROVED_BEHAVIOR_CHANGE if field_name in approved
                    else MODERN_DEFECT)
            differences.append(
                Difference("registro", key, field_name, got, want,
                           "contrato", code)
            )

    return MatchResult(
        batch_id=batch_id,
        business_correct=business_correct,
        parity_with_reference=None,
        differences=differences,
    )


# --------------------------------------------------------------------------
# Carregamento de oráculo
# --------------------------------------------------------------------------


def load_oracle(path: Path) -> dict[str, Any]:
    """Carrega um oráculo aprovado do disco.

    O oráculo é a fonte de correção. Nunca o edite para um portão passar.
    """
    if not path.exists():
        raise GoldenMatchError(
            f"oráculo ausente: {path}\n"
            "Sem oráculo, não se constrói. Consiga a saída esperada aprovada "
            "antes de rodar o pipeline."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    if "approved_by" not in data:
        raise GoldenMatchError(
            f"oráculo sem aprovação: {path}\n"
            "Um oráculo precisa de 'approved_by' — alguém que entende do "
            "negócio confirmou que este é o resultado certo."
        )
    return data
