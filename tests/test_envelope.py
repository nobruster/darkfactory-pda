"""Testes da fronteira entre produtor e juiz — validação do envelope.

Cobre B-1 (vínculo do sha256 com a leitura que de fato abriu o arquivo) e
B-2 (linhas_invalidas por tipo, domínio monetário, identidade dos defeitos,
total por código conferido por valor exato contra a referência da leitura).
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pda.envelope import (  # noqa: E402
    CapacidadeLeitura,
    DefeitoLeitura,
    EnvelopeRecusado,
    validar_envelope,
)

SHA_LIDO = "a" * 64
SHA_OUTRO_ARQUIVO = "b" * 64
SHA_ANCORADO = "c" * 64  # hash que o contrato ancora — nunca o mesmo do arquivo lido nos testes


def _contrato(codigos_distintos=3, escala=2, escala_maxima_intermediarios=3):
    return SimpleNamespace(
        politica_decimal=SimpleNamespace(
            escala=escala,
            escala_maxima_intermediarios=escala_maxima_intermediarios,
        ),
        cardinalidade=SimpleNamespace(codigos_distintos=codigos_distintos),
    )


def _envelope_base(**overrides):
    envelope = {
        "competencia": "2026-01",
        "motor": "juiz-python",
        "sha256_arquivo_lido": SHA_LIDO,
        "controles": {
            "count_linhas": 10,
            "linhas_invalidas": 1,
            "sum_vl_liquido": "150.00",
            "min_vl_liquido": "50.00",
            "max_vl_liquido": "100.00",
        },
        "defeitos": [
            {"tipo": "VALOR_ILEGIVEL", "valor_original": "abc", "posicao": 5},
            {
                "tipo": "IDENTIDADE_COLAPSADA",
                "valor_original": "Pensão por Morte de ",
                "posicao": 13,
            },
        ],
        "total_por_codigo": {
            "01": "100.00",
            "02": "50.005",
            "03": None,
        },
    }
    envelope.update(overrides)
    return envelope


def _capacidade_base(**overrides):
    base = dict(
        sha256_computado=SHA_LIDO,
        total_por_codigo={
            "01": Decimal("100.00"),
            "02": Decimal("50.005"),
            "03": None,
        },
        defeitos=(
            DefeitoLeitura(tipo="VALOR_ILEGIVEL", valor_original="abc", posicao=5),
            DefeitoLeitura(
                tipo="IDENTIDADE_COLAPSADA",
                valor_original="Pensão por Morte de ",
                posicao=13,
            ),
        ),
    )
    base.update(overrides)
    return CapacidadeLeitura(**base)


def test_envelope_valido_e_aceito():
    resultado = validar_envelope(_envelope_base(), _capacidade_base(), _contrato())
    assert resultado.sum_vl_liquido == Decimal("150.00")
    assert resultado.total_por_codigo["03"] is None


# ---------------------------------------------------------------------------
# eval_1 — sha_ausente / sha_divergente / sha_copiado_outro_arquivo


def test_sha_ausente_e_recusado():
    envelope = _envelope_base()
    del envelope["sha256_arquivo_lido"]
    with pytest.raises(EnvelopeRecusado):
        validar_envelope(envelope, _capacidade_base(), _contrato())


def test_sha_divergente_e_recusado():
    envelope = _envelope_base(sha256_arquivo_lido=SHA_OUTRO_ARQUIVO)
    with pytest.raises(EnvelopeRecusado):
        validar_envelope(envelope, _capacidade_base(), _contrato())


def test_sha_copiado_outro_arquivo_e_recusado():
    # O envelope copia o hash ANCORADO no contrato, não o hash do arquivo que
    # a leitura de fato abriu (que produziu outro hash). Copiar o ancorado
    # não é prova de vínculo com a leitura que rodou.
    envelope = _envelope_base(sha256_arquivo_lido=SHA_ANCORADO)
    capacidade = _capacidade_base(sha256_computado=SHA_OUTRO_ARQUIVO)
    with pytest.raises(EnvelopeRecusado):
        validar_envelope(envelope, capacidade, _contrato())


# ---------------------------------------------------------------------------
# eval_2 — invalidas_por_tipo / float_em_todo_monetario / defeito_por_identidade / total_por_codigo


def test_invalidas_por_tipo_diverge_e_recusado():
    envelope = _envelope_base()
    envelope["controles"]["linhas_invalidas"] = 2  # só há 1 defeito VALOR_ILEGIVEL
    with pytest.raises(EnvelopeRecusado):
        validar_envelope(envelope, _capacidade_base(), _contrato())


def test_invalidas_por_tipo_zero_com_colapso_e_aceito():
    # Competência 2026-01: linhas_invalidas=0 com 11 defeitos de colapso —
    # identidade colapsada é defeito numa linha VÁLIDA, nunca soma na conta.
    envelope = _envelope_base(
        controles={
            "count_linhas": 10,
            "linhas_invalidas": 0,
            "sum_vl_liquido": "150.00",
            "min_vl_liquido": "50.00",
            "max_vl_liquido": "100.00",
        },
        defeitos=[
            {"tipo": "IDENTIDADE_COLAPSADA", "valor_original": "Pensão por Morte de ", "posicao": 13},
            {"tipo": "IDENTIDADE_COLAPSADA", "valor_original": "Aposentadoria por In", "posicao": 13},
        ],
    )
    capacidade = _capacidade_base(
        defeitos=(
            DefeitoLeitura(tipo="IDENTIDADE_COLAPSADA", valor_original="Pensão por Morte de ", posicao=13),
            DefeitoLeitura(tipo="IDENTIDADE_COLAPSADA", valor_original="Aposentadoria por In", posicao=13),
        )
    )
    resultado = validar_envelope(envelope, capacidade, _contrato())
    assert resultado.linhas_invalidas == 0


def test_float_em_todo_monetario_sum_e_recusado():
    envelope = _envelope_base()
    envelope["controles"]["sum_vl_liquido"] = 150.0
    with pytest.raises(EnvelopeRecusado):
        validar_envelope(envelope, _capacidade_base(), _contrato())


def test_float_em_todo_monetario_min_max_e_recusado():
    envelope = _envelope_base()
    envelope["controles"]["min_vl_liquido"] = 50.0
    with pytest.raises(EnvelopeRecusado):
        validar_envelope(envelope, _capacidade_base(), _contrato())


def test_float_em_todo_monetario_total_por_codigo_e_recusado():
    envelope = _envelope_base()
    envelope["total_por_codigo"] = {"01": 100.0, "02": "50.005", "03": None}
    with pytest.raises(EnvelopeRecusado):
        validar_envelope(envelope, _capacidade_base(), _contrato())


def test_float_em_todo_monetario_negativo_e_recusado():
    # ADR 0009: não-negatividade vale para o produtor externo — '-0.01'
    # é recusado pelo domínio antes de qualquer conversão, nunca aceito e
    # comparado depois.
    envelope = _envelope_base()
    envelope["controles"]["sum_vl_liquido"] = "-0.01"
    with pytest.raises(EnvelopeRecusado):
        validar_envelope(envelope, _capacidade_base(), _contrato())


@pytest.mark.parametrize("literal", ["NaN", "sNaN", "Infinity", "1e10"])
def test_float_em_todo_monetario_nao_finito_e_recusado(literal):
    envelope = _envelope_base()
    envelope["controles"]["sum_vl_liquido"] = literal
    with pytest.raises(EnvelopeRecusado):
        validar_envelope(envelope, _capacidade_base(), _contrato())


def test_float_em_todo_monetario_inclui_contagem_fracionaria_e_booleana():
    # Os dois controles de CONTAGEM são inteiros não negativos: 41572553.0 ==
    # 41572553 e False == 0 em Python, então a comparação por igualdade
    # aceitaria float/bool onde só inteiro vale — a recusa precisa ser por tipo.
    envelope_float = _envelope_base()
    envelope_float["controles"]["count_linhas"] = 10.0
    with pytest.raises(EnvelopeRecusado):
        validar_envelope(envelope_float, _capacidade_base(), _contrato())

    envelope_bool = _envelope_base()
    envelope_bool["controles"]["linhas_invalidas"] = False
    with pytest.raises(EnvelopeRecusado):
        validar_envelope(envelope_bool, _capacidade_base(), _contrato())


def test_defeito_por_identidade_substituicao_e_recusado():
    # Dois defeitos do mesmo tipo: A duplicado, B omitido — contagem e tipo
    # preservados, só a identidade (valor original + posição) expõe a troca.
    envelope = _envelope_base(
        defeitos=[
            {"tipo": "VALOR_ILEGIVEL", "valor_original": "abc", "posicao": 5},
            {"tipo": "VALOR_ILEGIVEL", "valor_original": "abc", "posicao": 5},
        ],
        controles={
            "count_linhas": 10,
            "linhas_invalidas": 2,
            "sum_vl_liquido": "150.00",
            "min_vl_liquido": "50.00",
            "max_vl_liquido": "100.00",
        },
    )
    capacidade = _capacidade_base(
        defeitos=(
            DefeitoLeitura(tipo="VALOR_ILEGIVEL", valor_original="abc", posicao=5),
            DefeitoLeitura(tipo="VALOR_ILEGIVEL", valor_original="xyz", posicao=9),
        )
    )
    with pytest.raises(EnvelopeRecusado):
        validar_envelope(envelope, capacidade, _contrato())


def test_defeito_por_identidade_e_aceito_quando_bate():
    resultado = validar_envelope(_envelope_base(), _capacidade_base(), _contrato())
    assert resultado.linhas_invalidas == 1


def test_total_por_codigo_diverge_por_valor_e_recusado():
    envelope = _envelope_base()
    envelope["total_por_codigo"]["01"] = "999.00"
    with pytest.raises(EnvelopeRecusado):
        validar_envelope(envelope, _capacidade_base(), _contrato())


def test_total_por_codigo_agrupador_desloca_valor_entre_codigos_e_recusado():
    # Um produtor que zera um código e joga o total no outro mantém chaves e
    # controles globais idênticos — só a comparação por VALOR pega (R-3).
    envelope = _envelope_base()
    envelope["total_por_codigo"] = {"01": "150.005", "02": "0.00", "03": None}
    with pytest.raises(EnvelopeRecusado):
        validar_envelope(envelope, _capacidade_base(), _contrato())


def test_total_por_codigo_nao_quantiza_antes_de_comparar():
    # 2,345 chega 2,345 dos dois lados — quantizar um só faria a fronteira
    # recusar dois lados corretos.
    envelope = _envelope_base()
    envelope["total_por_codigo"] = {"01": "2.345", "02": "50.005", "03": None}
    capacidade = _capacidade_base(
        total_por_codigo={
            "01": Decimal("2.345"),
            "02": Decimal("50.005"),
            "03": None,
        }
    )
    resultado = validar_envelope(envelope, capacidade, _contrato())
    assert resultado.total_por_codigo["01"] == Decimal("2.345")


def test_total_por_codigo_cardinalidade_diverge_do_contrato_ancorado_e_recusado():
    # A cardinalidade é medida e ancorada no contrato — nunca um número fixo
    # em código (o ADR 0004 tinha 51, esta competência tem 65: qualquer dos
    # dois pode ser a cardinalidade ancorada, e é ela que vale).
    contrato = _contrato(codigos_distintos=5)
    with pytest.raises(EnvelopeRecusado):
        validar_envelope(_envelope_base(), _capacidade_base(), contrato)


def test_total_por_codigo_codigo_totalmente_invalido_aparece_com_chave_e_null():
    envelope = _envelope_base()
    envelope["total_por_codigo"]["03"] = None
    resultado = validar_envelope(envelope, _capacidade_base(), _contrato())
    assert "03" in resultado.total_por_codigo
    assert resultado.total_por_codigo["03"] is None


def test_total_por_codigo_zero_em_vez_de_null_e_recusado():
    # Zero inventaria dinheiro que ninguém recebeu — o código sem valor
    # legível tem que chegar como null, nunca como 0.00.
    envelope = _envelope_base()
    envelope["total_por_codigo"]["03"] = "0.00"
    with pytest.raises(EnvelopeRecusado):
        validar_envelope(envelope, _capacidade_base(), _contrato())


def test_total_por_codigo_chave_omitida_e_recusado():
    envelope = _envelope_base()
    del envelope["total_por_codigo"]["03"]
    with pytest.raises(EnvelopeRecusado):
        validar_envelope(envelope, _capacidade_base(), _contrato())


# ---------------------------------------------------------------------------
# eval_3 — produtor_agnostico


@pytest.mark.parametrize("motor", ["juiz-python", "spark-3.5.0", "produtor-externo-desconhecido"])
def test_produtor_agnostico_aceita_qualquer_motor(motor):
    envelope = _envelope_base(motor=motor)
    resultado = validar_envelope(envelope, _capacidade_base(), _contrato())
    assert resultado.motor == motor


def test_produtor_agnostico_nao_importa_nada_do_motor_declarado():
    # Um motor com um nome hostil/arbitrário não deve alterar o caminho de
    # validação nem levantar exceção por não ser reconhecido — o juiz não
    # importa nada do produtor.
    envelope = _envelope_base(motor="motor-que-nao-existe-em-lugar-nenhum-42")
    resultado = validar_envelope(envelope, _capacidade_base(), _contrato())
    assert resultado.motor == "motor-que-nao-existe-em-lugar-nenhum-42"
