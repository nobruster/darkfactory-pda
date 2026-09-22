"""Testes do juízo — os cinco controles comparados individualmente contra a
âncora, divergência com precedência sobre qualquer classificação, e a
classificação de cada diferença vinda sempre do contrato, nunca inventada.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pda.contrato import (  # noqa: E402
    Ancora,
    Cardinalidade,
    Contrato,
    DefeitoConhecido,
    Layout,
    PoliticaDecimal,
    Procedencia,
)
from pda.juizo import (  # noqa: E402
    CLASSIFICACOES_QUE_BLOQUEIAM,
    CLASSIFICACOES_QUE_REGISTRAM,
    Diferenca,
    JuizoBloqueado,
    JuizoRecusado,
    Veredito,
    classificar,
    julgar,
)


def _contrato(**overrides) -> Contrato:
    base = dict(
        competencia="TESTE-JUIZO",
        procedencia=Procedencia(
            fonte="fixture-teste",
            hash_zip_sha256="a" * 64,
            hash_csv_sha256="b" * 64,
            publicado_em="2026-09-22",
        ),
        layout=Layout(
            total_colunas=14,
            separador=";",
            encoding="utf-8",
            posicoes={"vl_liquido": 9, "especie": 12, "descricao_especie": 13},
        ),
        ancora=Ancora(
            count_linhas=7,
            sum_vl_liquido=Decimal("2011.00"),
            min_vl_liquido=Decimal("5.00"),
            max_vl_liquido=Decimal("1621.00"),
            linhas_invalidas=0,
            aprovado_por="nobru",
            aprovado_em="2026-09-22",
        ),
        cardinalidade=Cardinalidade(
            codigos_distintos=7,
            descricoes_distintas=3,
            colapsos=11,
            codigos_colapsados=24,
        ),
        defeitos_conhecidos=(
            DefeitoConhecido(
                tipo="CONFIRMED_SOURCE_DEFECT",
                descricao="11 descrições cobrem 24 códigos (identidade colapsada, ADR 0008)",
                quantidade=11,
                aprovador="nobru",
                aprovado_em="2026-09-22",
            ),
        ),
        politica_decimal=PoliticaDecimal(
            modo="HALF_EVEN",
            escala=2,
            escala_maxima_intermediarios=3,
            precisao=14,
            nao_negativo=True,
        ),
    )
    base.update(overrides)
    return Contrato(**base)


def _resultado_igual_a_ancora(contrato: Contrato, **overrides):
    ancora = contrato.ancora
    campos = dict(
        count_linhas=ancora.count_linhas,
        linhas_invalidas=ancora.linhas_invalidas,
        sum_vl_liquido=ancora.sum_vl_liquido,
        min_vl_liquido=ancora.min_vl_liquido,
        max_vl_liquido=ancora.max_vl_liquido,
    )
    campos.update(overrides)

    class _Resultado:
        pass

    resultado = _Resultado()
    for campo, valor in campos.items():
        setattr(resultado, campo, valor)
    return resultado


# ---------------------------------------------------------------------------
# eval_1: linha a menos recusa; os cinco controles são comparados
# individualmente — soma e contagem iguais não bastam.
# ---------------------------------------------------------------------------


def test_linha_a_menos_recusa():
    contrato = _contrato()
    resultado = _resultado_igual_a_ancora(contrato, count_linhas=contrato.ancora.count_linhas - 1)

    with pytest.raises(JuizoRecusado):
        julgar(resultado, contrato)


def test_cinco_controles_soma_e_contagem_iguais_nao_bastam():
    contrato = _contrato()
    # Redistribui valores preservando soma e contagem, mas altera o extremo
    # mínimo: nenhum dos dois controles "óbvios" acusa, só o extremo.
    resultado = _resultado_igual_a_ancora(contrato, min_vl_liquido=Decimal("0.00"))

    with pytest.raises(JuizoRecusado):
        julgar(resultado, contrato)


def test_cinco_controles_extremo_maximo_alterado_tambem_recusa():
    contrato = _contrato()
    resultado = _resultado_igual_a_ancora(contrato, max_vl_liquido=Decimal("1999.00"))

    with pytest.raises(JuizoRecusado):
        julgar(resultado, contrato)


def test_cinco_controles_aceita_quando_os_cinco_batem():
    contrato = _contrato()
    resultado = _resultado_igual_a_ancora(contrato)

    veredito = julgar(resultado, contrato)

    assert isinstance(veredito, Veredito)
    assert veredito.aceito is True


# ---------------------------------------------------------------------------
# eval_2: precedência — um controle divergente recusa mesmo quando a
# diferença correspondente está classificada e aprovada no contrato.
# ---------------------------------------------------------------------------


def test_precedencia_controle_divergente_recusa_mesmo_classificado():
    contrato = _contrato()
    resultado = _resultado_igual_a_ancora(contrato, sum_vl_liquido=Decimal("1999.00"))
    diferenca = Diferenca(identidade="codigo-X", classificacoes=("CONFIRMED_SOURCE_DEFECT",))

    with pytest.raises(JuizoRecusado):
        julgar(resultado, contrato, diferencas=(diferenca,))


def test_precedencia_recusa_nao_menciona_classificacao_quando_controle_diverge():
    contrato = _contrato()
    resultado = _resultado_igual_a_ancora(contrato, linhas_invalidas=contrato.ancora.linhas_invalidas + 1)
    diferenca = Diferenca(identidade="codigo-Y", classificacoes=("APPROVED_BEHAVIOR_CHANGE",))

    # A recusa dos controles é decidida ANTES de qualquer classificação —
    # uma classificação inexistente no contrato não muda o resultado.
    with pytest.raises(JuizoRecusado):
        julgar(resultado, contrato, diferencas=(diferenca,))


# ---------------------------------------------------------------------------
# eval_3: defeito sem classificação bloqueia; duas classificações ao mesmo
# tempo também bloqueiam (classificação não é única).
# ---------------------------------------------------------------------------


def test_defeito_sem_classe_bloqueia():
    contrato = _contrato()
    diferenca = Diferenca(identidade="codigo-Z", classificacoes=())

    with pytest.raises(JuizoBloqueado):
        classificar(diferenca, contrato)


def test_defeito_sem_classe_bloqueia_o_julgamento_completo():
    contrato = _contrato()
    resultado = _resultado_igual_a_ancora(contrato)
    diferenca = Diferenca(identidade="codigo-Z", classificacoes=())

    with pytest.raises(JuizoBloqueado):
        julgar(resultado, contrato, diferencas=(diferenca,))


def test_classificacao_unica_zero_bloqueia():
    contrato = _contrato()
    diferenca = Diferenca(identidade="codigo-W", classificacoes=())

    with pytest.raises(JuizoBloqueado):
        classificar(diferenca, contrato)


def test_classificacao_unica_duas_ao_mesmo_tempo_bloqueia():
    contrato = _contrato(
        defeitos_conhecidos=(
            DefeitoConhecido(
                tipo="CONFIRMED_SOURCE_DEFECT",
                descricao="colapso conhecido",
                quantidade=11,
                aprovador="nobru",
                aprovado_em="2026-09-22",
            ),
            DefeitoConhecido(
                tipo="CONFIRMED_LEGACY_DEFECT",
                descricao="defeito legado conhecido",
                quantidade=1,
                aprovador="nobru",
                aprovado_em="2026-09-22",
            ),
        )
    )
    # Ambas aprovadas no contrato individualmente — mesmo assim, DUAS na
    # mesma diferença bloqueiam: permitiria escolher a mais branda na leitura.
    diferenca = Diferenca(
        identidade="codigo-V",
        classificacoes=("CONFIRMED_SOURCE_DEFECT", "CONFIRMED_LEGACY_DEFECT"),
    )

    with pytest.raises(JuizoBloqueado):
        classificar(diferenca, contrato)


def test_classificacao_unica_aprovada_e_registra():
    contrato = _contrato()
    diferenca = Diferenca(identidade="colapso-11", classificacoes=("CONFIRMED_SOURCE_DEFECT",))

    classificacao = classificar(diferenca, contrato)

    assert classificacao == "CONFIRMED_SOURCE_DEFECT"


# ---------------------------------------------------------------------------
# B-2 — as seis classificações: as três CONFIRMED/APPROVED só registram, as
# três (MODERN_DEFECT, CONTRACT_AMBIGUITY, UNRESOLVED) bloqueiam mesmo
# aprovadas no contrato e mesmo sendo a única classificação da diferença.
# ---------------------------------------------------------------------------


TODAS_AS_SEIS = (
    "CONFIRMED_SOURCE_DEFECT",
    "CONFIRMED_LEGACY_DEFECT",
    "APPROVED_BEHAVIOR_CHANGE",
    "MODERN_DEFECT",
    "CONTRACT_AMBIGUITY",
    "UNRESOLVED",
)


def _contrato_com_todas_as_seis() -> Contrato:
    return _contrato(
        defeitos_conhecidos=tuple(
            DefeitoConhecido(
                tipo=tipo,
                descricao=f"defeito de exemplo classificado como {tipo}",
                quantidade=1,
                aprovador="nobru",
                aprovado_em="2026-09-22",
            )
            for tipo in TODAS_AS_SEIS
        )
    )


@pytest.mark.parametrize("tipo", sorted(CLASSIFICACOES_QUE_REGISTRAM))
def test_classificacao_unica_das_tres_que_registram(tipo):
    contrato = _contrato_com_todas_as_seis()
    diferenca = Diferenca(identidade=f"diferenca-{tipo}", classificacoes=(tipo,))

    assert classificar(diferenca, contrato) == tipo


@pytest.mark.parametrize("tipo", sorted(CLASSIFICACOES_QUE_BLOQUEIAM))
def test_classificacao_unica_das_tres_que_bloqueiam(tipo):
    contrato = _contrato_com_todas_as_seis()
    diferenca = Diferenca(identidade=f"diferenca-{tipo}", classificacoes=(tipo,))

    with pytest.raises(JuizoBloqueado):
        classificar(diferenca, contrato)


def test_defeito_sem_classe_fora_da_lista_do_contrato_bloqueia():
    contrato = _contrato()  # só aprova CONFIRMED_SOURCE_DEFECT
    diferenca = Diferenca(identidade="codigo-nao-aprovado", classificacoes=("CONFIRMED_LEGACY_DEFECT",))

    with pytest.raises(JuizoBloqueado):
        classificar(diferenca, contrato)


def test_onze_colapsos_como_confirmed_source_defect_julgamento_completo():
    contrato = _contrato()
    resultado = _resultado_igual_a_ancora(contrato)
    diferencas = tuple(
        Diferenca(identidade=f"colapso-{indice}", classificacoes=("CONFIRMED_SOURCE_DEFECT",))
        for indice in range(contrato.cardinalidade.colapsos)
    )

    veredito = julgar(resultado, contrato, diferencas=diferencas)

    assert veredito.aceito is True
    assert len(veredito.classificacoes) == 11
    assert set(veredito.classificacoes.values()) == {"CONFIRMED_SOURCE_DEFECT"}
