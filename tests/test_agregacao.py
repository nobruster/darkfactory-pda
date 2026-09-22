"""Testes da agregação exata — float recusado, ilegível excluído (nunca
zerado), extremos ausentes no limite, HALF_EVEN contra HALF_UP, contexto
próprio e completo, arredondamento único no total e agrupamento pelo código
conferido contra a leitura.
"""

from __future__ import annotations

import decimal
import os
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pda.agregacao import (  # noqa: E402
    AUSENTE,
    AgregacaoRecusada,
    Registro,
    agregar,
)
from pda.contrato import (  # noqa: E402
    Ancora,
    Cardinalidade,
    Contrato,
    Layout,
    PoliticaDecimal,
    Procedencia,
)
from pda.leitura import ler_competencia  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "competencia-min.csv"
ENCODING = "utf-8"
SEPARADOR = ";"


def _contrato_minimo(**overrides) -> Contrato:
    base = dict(
        competencia="TESTE-MIN",
        procedencia=Procedencia(
            fonte="fixture-teste",
            hash_zip_sha256="a" * 64,
            hash_csv_sha256="b" * 64,
            publicado_em="2026-09-22",
        ),
        layout=Layout(
            total_colunas=14,
            separador=SEPARADOR,
            encoding=ENCODING,
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
            colapsos=2,
            codigos_colapsados=6,
        ),
        defeitos_conhecidos=(),
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


# ---------------------------------------------------------------------------
# eval_1: float recusado; ilegível excluído (nunca zerado); nenhum legível
# marca os extremos ausentes.
# ---------------------------------------------------------------------------


def test_recusa_float_com_erro_explicito():
    contrato = _contrato_minimo(cardinalidade=Cardinalidade(1, 1, 0, 0))
    registros = [Registro(codigo="01", valor=1234.56)]  # float, nunca Decimal

    with pytest.raises(AgregacaoRecusada):
        agregar(registros, contrato)


def test_recusa_float_mesmo_misturado_a_registros_legiveis():
    contrato = _contrato_minimo(cardinalidade=Cardinalidade(2, 2, 0, 0))
    registros = [
        Registro(codigo="01", valor=Decimal("10.00")),
        Registro(codigo="02", valor=0.1),  # float escondido no meio do lote
    ]

    with pytest.raises(AgregacaoRecusada):
        agregar(registros, contrato)


def test_ilegivel_excluido_nao_zerado_das_tres_monetarias():
    # Preencher o ilegível com 0.00 NÃO mudaria soma nem máximo, e o mínimo
    # da fonte já é 0.00 — por isso a prova de exclusão não compara totais:
    # ela confere que a CHAVE do registro ilegível nunca aparece na saída, e
    # que a contagem de inválidas isola exatamente esse registro.
    contrato = _contrato_minimo(cardinalidade=Cardinalidade(2, 2, 0, 0))
    registros = [
        Registro(codigo="01", valor=Decimal("0.00")),
        Registro(codigo="02", valor=Decimal("50.00")),
        Registro(codigo="99", valor=None),  # ilegível — nunca vira 0.00
    ]

    resultado = agregar(registros, contrato)

    assert resultado.count_linhas == 3
    assert resultado.linhas_invalidas == 1
    assert "99" not in resultado.total_por_codigo
    assert resultado.sum_vl_liquido == Decimal("50.00")
    assert resultado.min_vl_liquido == Decimal("0.00")
    assert resultado.max_vl_liquido == Decimal("50.00")


def test_nenhum_legivel_extremos_ausentes_soma_zero_e_invalidas_igual_lidas():
    contrato = _contrato_minimo(cardinalidade=Cardinalidade(0, 0, 0, 0))
    registros = [
        Registro(codigo="01", valor=None),
        Registro(codigo="02", valor=None),
        Registro(codigo="03", valor=None),
    ]

    resultado = agregar(registros, contrato)

    assert resultado.count_linhas == 3
    assert resultado.linhas_invalidas == 3
    assert resultado.count_linhas == resultado.linhas_invalidas
    assert resultado.sum_vl_liquido == Decimal("0.00")
    assert resultado.min_vl_liquido == AUSENTE
    assert resultado.max_vl_liquido == AUSENTE
    assert resultado.total_por_codigo == {}


# ---------------------------------------------------------------------------
# eval_2: HALF_EVEN recusa o que HALF_UP daria; contexto próprio e completo;
# arredonda uma vez, no total.
# ---------------------------------------------------------------------------


def test_recusa_half_up_no_empate_exato():
    contrato = _contrato_minimo(cardinalidade=Cardinalidade(1, 1, 0, 0))
    # 1.005 é exatamente o meio entre 1.00 e 1.01 — HALF_UP arredondaria para
    # cima sempre; HALF_EVEN escolhe o dígito par (0), então 1.00.
    registros = [Registro(codigo="01", valor=Decimal("1.005"))]

    resultado = agregar(registros, contrato)

    valor_half_up = Decimal("1.005").quantize(Decimal("1.00"), rounding=ROUND_HALF_UP)
    assert valor_half_up == Decimal("1.01")
    assert resultado.sum_vl_liquido == Decimal("1.00")
    assert resultado.sum_vl_liquido != valor_half_up


def test_precisao_declarada_sobrevive_a_contexto_global_adverso_nos_tres_eixos():
    contrato = _contrato_minimo(cardinalidade=Cardinalidade(1, 1, 0, 0))
    registros = [Registro(codigo="01", valor=Decimal("1.005"))]

    contexto_ambiente = decimal.getcontext()
    salvo = contexto_ambiente.copy()
    try:
        # três eixos adversos: precisão baixa, Emax/Emin apertados, e o modo
        # de arredondamento oposto (HALF_UP) — nenhum deve vazar para dentro
        # do `with localcontext()` de `agregar` (ADR 0006).
        contexto_ambiente.prec = 3
        contexto_ambiente.Emax = 2
        contexto_ambiente.Emin = -2
        contexto_ambiente.rounding = ROUND_HALF_UP

        resultado = agregar(registros, contrato)
    finally:
        decimal.setcontext(salvo)

    assert resultado.sum_vl_liquido == Decimal("1.00")


def test_granularidade_arredonda_uma_vez_no_total_nao_por_campo():
    # exemplo do AGENTS.md: 2,345 + 2,345 dá 4,68 por campo (cada 2.345
    # arredonda para baixo, 4 é par) e 4,69 no total (soma exata primeiro,
    # quantiza uma vez) — ambos são HALF_EVEN legítimo, mas só um é o que o
    # ADR 0004 exige.
    contrato = _contrato_minimo(cardinalidade=Cardinalidade(1, 1, 0, 0))
    registros = [
        Registro(codigo="01", valor=Decimal("2.345")),
        Registro(codigo="01", valor=Decimal("2.345")),
    ]

    resultado = agregar(registros, contrato)

    por_campo = Decimal("2.345").quantize(Decimal("1.00"), rounding=decimal.ROUND_HALF_EVEN)
    assert por_campo == Decimal("2.34")
    total_por_campo = por_campo + por_campo
    assert total_por_campo == Decimal("4.68")

    assert resultado.sum_vl_liquido == Decimal("4.69")
    assert resultado.total_por_codigo["01"] == Decimal("4.69")
    assert resultado.sum_vl_liquido != total_por_campo


# ---------------------------------------------------------------------------
# eval_3: a saída preserva a cardinalidade ancorada; agrupar pela chave
# código, conferido valor a valor contra a leitura — não só a chave presente.
# ---------------------------------------------------------------------------


def _totais_da_leitura(tmp_path) -> dict:
    conteudo = FIXTURE.read_bytes()
    caminho = tmp_path / "competencia.csv"
    caminho.write_bytes(conteudo)
    os.chmod(caminho, 0o444)
    contrato = _contrato_minimo()
    resultado = ler_competencia(caminho, contrato)
    return resultado.total_por_codigo


def test_agrega_pela_chave_e_codigo_conferindo_cada_valor_contra_a_leitura(tmp_path):
    totais_leitura = _totais_da_leitura(tmp_path)
    assert totais_leitura == {
        "01": Decimal("1621.00"),
        "03": Decimal("100.00"),
        "23": Decimal("50.00"),
        "59": Decimal("25.00"),
        "04": Decimal("200.00"),
        "83": Decimal("10.00"),
        "02": Decimal("5.00"),
    }

    contrato = _contrato_minimo()
    # os mesmos registros que a leitura extraiu do fixture, agora agregados
    # de forma independente, agrupados pelo CÓDIGO (nunca pela descrição) —
    # um agregador que somasse por descrição e atribuísse tudo ao primeiro
    # código deixaria "03", "23" e "59" ausentes ou zerados aqui.
    registros = [
        Registro(codigo="01", valor=Decimal("1621.00")),
        Registro(codigo="03", valor=Decimal("100.00")),
        Registro(codigo="23", valor=Decimal("50.00")),
        Registro(codigo="59", valor=Decimal("25.00")),
        Registro(codigo="04", valor=Decimal("200.00")),
        Registro(codigo="83", valor=Decimal("10.00")),
        Registro(codigo="02", valor=Decimal("5.00")),
    ]

    resultado = agregar(registros, contrato)

    # confere cada VALOR por código contra a leitura, não só as chaves
    assert resultado.total_por_codigo == totais_leitura
    for codigo, total in totais_leitura.items():
        assert resultado.total_por_codigo[codigo] == total


def test_cardinalidade_ancorada_no_contrato_nao_um_numero_fixo_no_codigo():
    # a cardinalidade vem do contrato desta competência (7, no fixture) — não
    # de um número fixo no código; um contrato com 65 códigos (a competência
    # real inteira) aceitaria 65 igualmente, mas aqui provamos que a
    # contagem SEGUE o contrato, trocando-a e observando a recusa.
    contrato_ok = _contrato_minimo(cardinalidade=Cardinalidade(3, 3, 0, 0))
    registros = [
        Registro(codigo="01", valor=Decimal("10.00")),
        Registro(codigo="02", valor=Decimal("20.00")),
        Registro(codigo="03", valor=Decimal("30.00")),
    ]

    resultado = agregar(registros, contrato_ok)
    assert len(resultado.total_por_codigo) == 3
    assert resultado.total_por_codigo.keys() == {"01", "02", "03"}

    contrato_divergente = _contrato_minimo(cardinalidade=Cardinalidade(51, 51, 0, 0))
    with pytest.raises(AgregacaoRecusada):
        agregar(registros, contrato_divergente)

    contrato_real_65 = _contrato_minimo(cardinalidade=Cardinalidade(65, 52, 11, 24))
    with pytest.raises(AgregacaoRecusada):
        agregar(registros, contrato_real_65)
