"""Prova que o juiz FALHA quando deve falhar.

Este é o teste mais importante da fábrica inteira.

Um portão que nunca falhou não é um portão — é decoração que dá falsa
confiança. Antes de confiar que o verde significa algo, é preciso provar
que o vermelho acontece.

Cada teste aqui corrompe os dados de propósito e exige que o juiz acuse.

    pytest tests/test_judge_fails_red.py -v
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from judge.golden_match import (  # noqa: E402
    APPROVED_BEHAVIOR_CHANGE,
    CONFIRMED_LEGACY_DEFECT,
    MODERN_DEFECT,
    GoldenMatchError,
    compare_aggregate,
    compare_records,
)

MONEY = ("valor_total", "valor_liquido")


# ==========================================================================
# GRUPO 1 — o juiz precisa ACUSAR quando o número está errado
# ==========================================================================


def test_um_centavo_a_menos_e_pego():
    """O caso que justifica a fábrica inteira.

    Um centavo. Bem-formado, determinístico, estável — e errado.
    """
    contrato = {"batch_id": "B001", "linhas": "2", "valor_total": "173.45"}
    produzido = {"batch_id": "B001", "linhas": "2", "valor_total": "173.44"}

    r = compare_aggregate(
        batch_id="B001", actual=produzido, contract=contrato, money_fields=MONEY
    )

    assert not r.business_correct, "o juiz NÃO pegou um centavo de diferença"
    assert not r.resolved, "um centavo inexplicado passou pelo portão"
    assert r.status == "STALLED"
    assert r.unexplained_count == 1
    assert r.differences[0].classification == MODERN_DEFECT


def test_arredondamento_errado_e_pego():
    """HALF_EVEN vs HALF_UP — o erro que parece estruturalmente verde.

    Python arredonda HALF_EVEN por padrão. Se o negócio exige HALF_UP,
    o resultado diverge num centavo e nada no código parece errado.
    """
    contrato = {"taxa": "0.04"}       # HALF_UP sobre 3.50 * 0.01
    produzido = {"taxa": "0.03"}      # HALF_EVEN — o default da linguagem

    r = compare_aggregate(
        batch_id="B002", actual=produzido, contract=contrato,
        money_fields=("taxa",)
    )

    assert not r.resolved, "arredondamento errado passou"
    assert r.differences[0].classification == MODERN_DEFECT


def test_contagem_de_linhas_errada_e_pega():
    contrato = {"linhas": "1000", "valor_total": "50000.00"}
    produzido = {"linhas": "999", "valor_total": "50000.00"}

    r = compare_aggregate(
        batch_id="B003", actual=produzido, contract=contrato, money_fields=MONEY
    )

    assert not r.resolved, "linha faltando passou"


def test_linha_faltando_e_pega():
    contrato = [
        {"id": "1", "valor_liquido": "10.00"},
        {"id": "2", "valor_liquido": "20.00"},
    ]
    produzido = [{"id": "1", "valor_liquido": "10.00"}]

    r = compare_records(
        batch_id="B004", actual=produzido, contract=contrato,
        key_fields=("id",), money_fields=MONEY,
    )

    assert not r.resolved, "linha ausente passou"
    assert any(d.actual == "<ausente>" for d in r.differences)


def test_linha_extra_e_pega():
    """Duplicata — o bug mais comum de reprocessamento."""
    contrato = [{"id": "1", "valor_liquido": "10.00"}]
    produzido = [
        {"id": "1", "valor_liquido": "10.00"},
        {"id": "2", "valor_liquido": "20.00"},
    ]

    r = compare_records(
        batch_id="B005", actual=produzido, contract=contrato,
        key_fields=("id",), money_fields=MONEY,
    )

    assert not r.resolved, "linha duplicada passou"
    assert any(d.actual == "<extra>" for d in r.differences)


# ==========================================================================
# GRUPO 2 — o juiz precisa saber QUEM errou
# ==========================================================================


def test_sistema_atual_errado_e_classificado_como_legacy_defect():
    """O desfecho do bootcamp: o sistema em que você confiava está errado.

    Você bate com o contrato. O sistema atual não bate. Logo, o atual é o errado.
    """
    contrato = {"valor_total": "1.01"}
    produzido = {"valor_total": "1.01"}   # você está certo
    atual = {"valor_total": "1.00"}       # a produção está errada

    r = compare_aggregate(
        batch_id="B006", actual=produzido, contract=contrato,
        reference=atual, money_fields=MONEY,
    )

    assert r.business_correct, "você bate com o contrato"
    assert r.parity_with_reference is False, "e NÃO bate com o sistema atual"
    assert r.differences[0].classification == CONFIRMED_LEGACY_DEFECT
    # Explicado: o item empaca, mas não é bug seu.
    assert r.resolved
    assert r.status == "RESOLVED"


def test_copiar_o_erro_do_sistema_atual_e_classificado_como_bug_seu():
    """Se você bate com o atual mas não com o contrato, você copiou o bug.

    É por isso que se lê o CONTRATO, nunca o código antigo.
    """
    contrato = {"valor_total": "1.01"}
    produzido = {"valor_total": "1.00"}   # copiou o erro
    atual = {"valor_total": "1.00"}

    r = compare_aggregate(
        batch_id="B007", actual=produzido, contract=contrato,
        reference=atual, money_fields=MONEY,
    )

    assert not r.business_correct
    assert not r.resolved, "copiar o bug do legado não é explicação"
    assert r.differences[0].classification == MODERN_DEFECT


def test_mudanca_aprovada_nao_bloqueia():
    contrato = {"formato_data": "2026-01-01"}
    produzido = {"formato_data": "01/01/2026"}

    r = compare_aggregate(
        batch_id="B008", actual=produzido, contract=contrato,
        approved_changes=("formato_data",),
    )

    assert r.differences[0].classification == APPROVED_BEHAVIOR_CHANGE
    assert r.resolved, "mudança aprovada não deve bloquear"


# ==========================================================================
# GRUPO 3 — o juiz precisa se RECUSAR a julgar sem base
# ==========================================================================


def test_float_em_campo_monetario_e_recusado():
    """float perde centavos em silêncio. 0.1 + 0.2 != 0.3."""
    with pytest.raises(GoldenMatchError, match="float proibido"):
        compare_aggregate(
            batch_id="B009",
            actual={"valor_total": 173.45},   # float — proibido
            contract={"valor_total": "173.45"},
            money_fields=MONEY,
        )


def test_comparar_registros_sem_chave_e_recusado():
    """Comparar por posição é prova falsa — a ordem pode mudar."""
    with pytest.raises(GoldenMatchError, match="key_fields"):
        compare_records(
            batch_id="B010", actual=[], contract=[], key_fields=(),
        )


# ==========================================================================
# GRUPO 4 — o verde precisa ser possível (senão o teste é inútil)
# ==========================================================================


def test_resultado_correto_passa():
    contrato = {"batch_id": "B011", "linhas": "2", "valor_total": "173.45"}
    produzido = {"batch_id": "B011", "linhas": "2", "valor_total": "173.45"}

    r = compare_aggregate(
        batch_id="B011", actual=produzido, contract=contrato, money_fields=MONEY
    )

    assert r.business_correct
    assert r.resolved
    assert r.status == "MATCHED"
    assert r.unexplained_count == 0


def test_decimal_e_string_sao_equivalentes():
    """173.45 como Decimal ou string dá no mesmo. 173.450 também."""
    r = compare_aggregate(
        batch_id="B012",
        actual={"valor_total": Decimal("173.450")},
        contract={"valor_total": "173.45"},
        money_fields=MONEY,
    )
    assert r.resolved, "Decimal('173.450') deve igualar '173.45'"
