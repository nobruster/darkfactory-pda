"""Agregação exata: soma sob contexto decimal próprio e agrupamento pelo código.

Regra 5 (AGENTS.md): dinheiro é Decimal, nunca float. `agregar` é a última
fronteira antes do total — mesmo que quem chame já tenha convertido a fonte,
um float que chegue aqui é recusado explicitamente, nunca silenciosamente
aceito ou truncado.

Regra 4: um registro ilegível (valor ausente/não convertido a montante) é
EXCLUÍDO da soma, do mínimo e do máximo — nunca tratado como 0.00. Preencher
com 0.00 não muda soma nem máximo, e o mínimo da fonte já é 0.00: os três
controles passariam despercebidos por um agregador que zerasse em vez de
excluir. Por isso `count_linhas` e `linhas_invalidas` são os únicos dois
controles de contagem, e um agregador correto só pode ser distinguido de um
que zera olhando para os TRÊS controles monetários e para a exclusão da
chave — nunca comparando apenas os totais globais.

ADR 0004: o total arredonda uma vez, no fim — nunca por soma parcial nem por
campo. ADR 0001: o modo é sempre HALF_EVEN, a duas casas. ADR 0006: a
precisão do contexto decimal é declarada aqui, nunca herdada do ambiente —
`with localcontext()` fixa precisão, Emax, Emin, traps e arredondamento,
porque uma biblioteca importada em qualquer lugar do processo pode ter
alterado o contexto global antes desta chamada.

A agregação agrupa pelo CÓDIGO (posição 12 do contrato), nunca pela
descrição (posição 13): a descrição pode cobrir mais de um código
(identidade colapsada, ADR 0008), e agrupar por ela colapsaria espécies
distintas numa única linha sem que nenhum controle global acusasse — o total
bate, a contagem bate, só o agrupamento por código expõe o defeito.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from typing import Iterable, Optional, Union

AUSENTE = "AUSENTE"


class AgregacaoRecusada(Exception):
    """A agregação recusa um valor ou um resultado — nunca ajusta em silêncio."""


@dataclass(frozen=True)
class Registro:
    """Uma linha já triada: `valor` é Decimal quando legível, None quando ilegível.

    Nunca é float — essa é a fronteira que `agregar` defende (Regra 5).
    """

    codigo: str
    valor: Optional[Decimal]


@dataclass(frozen=True)
class ResultadoAgregacao:
    count_linhas: int
    linhas_invalidas: int
    sum_vl_liquido: Decimal
    min_vl_liquido: Union[Decimal, str]
    max_vl_liquido: Union[Decimal, str]
    total_por_codigo: dict


def agregar(registros: Iterable[Registro], contrato) -> ResultadoAgregacao:
    """Agrega registros sob contexto decimal próprio, agrupando pelo código.

    Levanta `AgregacaoRecusada` se algum `valor` for float (Regra 5) ou se a
    quantidade de códigos distintos observada divergir da cardinalidade que o
    contrato ancora (Regra 3 — a expectativa não se ajusta ao resultado
    medido; a comparação é sempre contra o contrato, nunca contra um número
    fixo no código).
    """
    politica = contrato.politica_decimal

    count_linhas = 0
    linhas_invalidas = 0
    total_por_codigo: dict[str, Decimal] = {}
    soma_bruta = Decimal(0)
    minimo: Optional[Decimal] = None
    maximo: Optional[Decimal] = None

    # Contexto decimal PRÓPRIO e COMPLETO (ADR 0006/0007/0009): precisão,
    # arredondamento, Emax, Emin e traps são todos declarados aqui, mesmo que
    # o contexto ambiente vigente no momento da chamada seja hostil.
    with localcontext() as ctx:
        ctx.prec = politica.precisao
        ctx.Emax = 999999999
        ctx.Emin = -999999999
        for sinal in list(ctx.traps):
            ctx.traps[sinal] = False
        ctx.rounding = ROUND_HALF_EVEN

        for registro in registros:
            count_linhas += 1
            valor = registro.valor

            if isinstance(valor, float):
                raise AgregacaoRecusada(
                    f"valor monetário da linha {count_linhas} (código "
                    f"{registro.codigo!r}) chegou como float — dinheiro é "
                    "Decimal, nunca float (Regra 5)"
                )

            if valor is None:
                linhas_invalidas += 1
                continue

            soma_bruta += valor
            total_por_codigo[registro.codigo] = (
                total_por_codigo.get(registro.codigo, Decimal(0)) + valor
            )
            if minimo is None or valor < minimo:
                minimo = valor
            if maximo is None or valor > maximo:
                maximo = valor

        # Arredonda-se UMA VEZ, aqui, sobre o total e sobre cada total por
        # código já somado exato — nunca a cada soma parcial (ADR 0004).
        quantum = Decimal("1." + "0" * politica.escala) if politica.escala > 0 else Decimal("1")
        sum_vl_liquido = soma_bruta.quantize(quantum, rounding=ROUND_HALF_EVEN)
        total_por_codigo = {
            codigo: total.quantize(quantum, rounding=ROUND_HALF_EVEN)
            for codigo, total in total_por_codigo.items()
        }
        min_vl_liquido: Union[Decimal, str] = (
            minimo.quantize(quantum, rounding=ROUND_HALF_EVEN) if minimo is not None else AUSENTE
        )
        max_vl_liquido: Union[Decimal, str] = (
            maximo.quantize(quantum, rounding=ROUND_HALF_EVEN) if maximo is not None else AUSENTE
        )

    codigos_esperados = getattr(contrato.cardinalidade, "codigos_distintos", None)
    if codigos_esperados is not None and len(total_por_codigo) != codigos_esperados:
        raise AgregacaoRecusada(
            f"códigos distintos medidos na agregação ({len(total_por_codigo)}) "
            f"divergem da cardinalidade que o contrato ancora ({codigos_esperados})"
        )

    return ResultadoAgregacao(
        count_linhas=count_linhas,
        linhas_invalidas=linhas_invalidas,
        sum_vl_liquido=sum_vl_liquido,
        min_vl_liquido=min_vl_liquido,
        max_vl_liquido=max_vl_liquido,
        total_por_codigo=total_por_codigo,
    )
