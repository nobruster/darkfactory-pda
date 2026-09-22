"""Juízo: compara os cinco controles do agregado contra a âncora do contrato
e classifica toda diferença — separando a decisão de aceitar da produção do
número (SEAM-JUIZO).

Regra 3 (AGENTS.md): quando um controle diverge, o trabalho é investigar,
nunca ajustar a âncora nem inventar uma classificação para "destravar" o
veredito. `julgar` nunca importa nem calcula o que a âncora deveria ter
sido — compara o que está no contrato contra o que o agregado produziu.

B-1: os cinco controles (count_linhas, linhas_invalidas, sum_vl_liquido,
min_vl_liquido, max_vl_liquido) são comparados INDIVIDUALMENTE. Soma e
contagem batendo não bastam: uma redistribuição de valores que preserva as
duas, mas altera o mínimo ou o máximo, ainda é uma divergência e recusa.

B-2: a classificação de cada diferença vem do CONTRATO
(`contrato.defeitos_conhecidos`), nunca inventada pelo juízo — inventar
seria tomar decisão de negócio sem autoridade. Cada diferença carrega
exatamente uma classificação: zero bloqueia (defeito sem classificação) e
duas também bloqueiam (duas permitiriam escolher a mais branda na hora de
ler). Uma classificação fora da lista aprovada no contrato bloqueia, em vez
de o juízo aceitar uma classificação que ninguém aprovou. Das seis
classificações, três (CONFIRMED_SOURCE_DEFECT, CONFIRMED_LEGACY_DEFECT,
APPROVED_BEHAVIOR_CHANGE) apenas registram a diferença; três
(MODERN_DEFECT, CONTRACT_AMBIGUITY, UNRESOLVED) bloqueiam mesmo sendo a
única classificação e mesmo aprovadas no contrato — CONFIRMED explica a
diferença, nunca a aprova sozinho para as três que continuam abertas.
Divergência em qualquer um dos cinco controles tem PRECEDÊNCIA sobre
qualquer classificação: nenhuma diferença classificada salva um controle
divergente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple

CONFIRMED_SOURCE_DEFECT = "CONFIRMED_SOURCE_DEFECT"
CONFIRMED_LEGACY_DEFECT = "CONFIRMED_LEGACY_DEFECT"
APPROVED_BEHAVIOR_CHANGE = "APPROVED_BEHAVIOR_CHANGE"
MODERN_DEFECT = "MODERN_DEFECT"
CONTRACT_AMBIGUITY = "CONTRACT_AMBIGUITY"
UNRESOLVED = "UNRESOLVED"

CLASSIFICACOES_QUE_REGISTRAM = frozenset(
    {CONFIRMED_SOURCE_DEFECT, CONFIRMED_LEGACY_DEFECT, APPROVED_BEHAVIOR_CHANGE}
)
CLASSIFICACOES_QUE_BLOQUEIAM = frozenset({MODERN_DEFECT, CONTRACT_AMBIGUITY, UNRESOLVED})
CLASSIFICACOES_VALIDAS = CLASSIFICACOES_QUE_REGISTRAM | CLASSIFICACOES_QUE_BLOQUEIAM

CONTROLES = (
    "count_linhas",
    "linhas_invalidas",
    "sum_vl_liquido",
    "min_vl_liquido",
    "max_vl_liquido",
)


class JuizoRecusado(Exception):
    """Um dos cinco controles diverge da âncora — recusa mesmo classificada."""


class JuizoBloqueado(Exception):
    """Uma diferença sem classificação única e aprovada, ou classificada como
    MODERN_DEFECT/CONTRACT_AMBIGUITY/UNRESOLVED — bloqueia a publicação."""


@dataclass(frozen=True)
class Diferenca:
    """Uma diferença observada, com as classificações propostas para ela.

    `classificacoes` não é o veredito — é o que se propõe classificar essa
    diferença como. O juízo só aceita quando há exatamente uma, e quando
    ela está entre os tipos que `contrato.defeitos_conhecidos` aprova.
    """

    identidade: str
    classificacoes: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Veredito:
    aceito: bool
    classificacoes: Dict[str, str]


def _tipos_aprovados(contrato) -> frozenset:
    return frozenset(defeito.tipo for defeito in contrato.defeitos_conhecidos)


def classificar(diferenca: Diferenca, contrato) -> str:
    """Devolve a classificação de `diferenca`, vinda do CONTRATO.

    Levanta `JuizoBloqueado` quando a diferença não carrega exatamente uma
    classificação, quando essa classificação não está entre os tipos que o
    contrato aprova em `defeitos_conhecidos`, ou quando é uma das três que
    bloqueiam por natureza (MODERN_DEFECT, CONTRACT_AMBIGUITY, UNRESOLVED).
    """
    quantidade = len(diferenca.classificacoes)
    if quantidade == 0:
        raise JuizoBloqueado(
            f"diferença {diferenca.identidade!r} sem classificação alguma — bloqueia"
        )
    if quantidade > 1:
        raise JuizoBloqueado(
            f"diferença {diferenca.identidade!r} com {quantidade} classificações "
            f"({', '.join(diferenca.classificacoes)}) — exatamente uma é exigida, "
            "para não permitir escolher a mais branda na hora de ler"
        )

    classificacao = diferenca.classificacoes[0]
    if classificacao not in _tipos_aprovados(contrato):
        raise JuizoBloqueado(
            f"diferença {diferenca.identidade!r} classificada como {classificacao!r}, "
            "fora dos defeitos conhecidos aprovados no contrato — o juízo não inventa "
            "classificação para um defeito que ninguém aprovou"
        )
    if classificacao in CLASSIFICACOES_QUE_BLOQUEIAM:
        raise JuizoBloqueado(
            f"diferença {diferenca.identidade!r} classificada como {classificacao!r} "
            "bloqueia a publicação — CONFIRMED explica a diferença, não a aprova"
        )

    return classificacao


def julgar(resultado, contrato, diferencas: Tuple[Diferenca, ...] = ()) -> Veredito:
    """Julga `resultado` (o agregado) contra `contrato.ancora`.

    Primeiro compara os cinco controles individualmente — `CONTROLES` — e
    recusa (`JuizoRecusado`) se algum divergir, ANTES de olhar para
    qualquer classificação: essa recusa tem precedência (B-2). Só então
    classifica cada diferença em `diferencas` (ver `classificar`);
    qualquer diferença que bloqueie interrompe o julgamento.
    """
    ancora = contrato.ancora
    divergentes = tuple(
        controle for controle in CONTROLES if getattr(resultado, controle) != getattr(ancora, controle)
    )
    if divergentes:
        raise JuizoRecusado(
            f"controles divergentes contra a âncora: {', '.join(divergentes)} — recusa mesmo "
            "que alguma diferença esteja classificada"
        )

    classificacoes: Dict[str, str] = {}
    for diferenca in diferencas:
        classificacoes[diferenca.identidade] = classificar(diferenca, contrato)

    return Veredito(aceito=True, classificacoes=classificacoes)
