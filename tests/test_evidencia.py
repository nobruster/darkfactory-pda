"""Testes do pacote de evidência: rederivação sem confiar no rótulo, e não-sobrescrita.

Cobre a Exit Check da tarefa T-20260921-evidencia-packet:

- eval_1: rederiva ("rederiva", "rotulo_adulterado", "tres_hashes", "precedencia_sem_ancora")
- eval_2: duas execuções coexistem ("nao_sobrescreve")
- eval_3: os quatro vereditos terminais são distinguíveis ("vereditos")
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pda import evidencia  # noqa: E402
from pda.evidencia import (
    ACEITO,
    ACEITO_SEM_ANCORA,
    CHAVE_AUSENTE,
    ERRO,
    RECUSADO,
    EvidenciaRecusada,
    gravar_pacote,
    ler_pacote,
    listar_execucoes,
    par_monetario,
    rederivar_veredito,
)


def _controles(count, invalidas, soma, minimo, maximo):
    return {
        "count_linhas": count,
        "linhas_invalidas": invalidas,
        "sum_vl_liquido": soma,
        "min_vl_liquido": minimo,
        "max_vl_liquido": maximo,
    }


def _pacote_aceito_kwargs(tmp_path):
    controles = _controles(10, 1, Decimal("100.00"), Decimal("1.00"), Decimal("50.00"))
    totais = {"01": Decimal("60.00"), "02": Decimal("40.00")}
    defeitos = [{"tipo": "VALOR_ILEGIVEL", "valor_original": "x", "posicao": 5}]
    return dict(
        diretorio=tmp_path,
        competencia_solicitada="2026-03",
        contrato_status="OK",
        competencia_contrato="2026-03",
        competencia_envelope="2026-03",
        aprovador="fulano",
        aprovado_em="2026-01-01",
        politica_decimal_modo="HALF_EVEN",
        escala=2,
        hash_ancorado="a" * 64,
        hash_observado="a" * 64,
        hash_declarado="a" * 64,
        ancora_controles=controles,
        agregado_controles=controles,
        classificacoes={"d1": "CONFIRMED_SOURCE_DEFECT"},
        defeitos_leitura=defeitos,
        defeitos_envelope=defeitos,
        totais_leitura=totais,
        totais_envelope=totais,
        duracao_segundos=1.5,
    )


# ---------------------------------------------------------------------------
# eval_1: rederiva
# ---------------------------------------------------------------------------


def test_rederiva_pacote_consistente_como_aceito(tmp_path):
    caminho = gravar_pacote(**_pacote_aceito_kwargs(tmp_path))
    pacote = ler_pacote(caminho)

    veredito, causa = rederivar_veredito(pacote)

    assert veredito == ACEITO
    assert causa == "JULGADO"
    assert pacote["veredito_gravado"] == ACEITO


def test_rederiva_recusa_quando_controle_diverge(tmp_path):
    kwargs = _pacote_aceito_kwargs(tmp_path)
    kwargs["agregado_controles"] = _controles(
        10, 1, Decimal("999.00"), Decimal("1.00"), Decimal("50.00")
    )
    caminho = gravar_pacote(**kwargs)
    pacote = ler_pacote(caminho)

    veredito, causa = rederivar_veredito(pacote)

    assert veredito == RECUSADO
    assert causa == "DIVERGENCIA"


def test_rederiva_recusa_quando_envelope_transfere_valor_entre_codigos(tmp_path):
    """Um envelope que move 1,00 do código A para o B mantém chaves, controles
    globais, hashes e defeitos idênticos — só a divergência entre os dois
    mapas de total por código explica a recusa (B-1)."""
    kwargs = _pacote_aceito_kwargs(tmp_path)
    kwargs["totais_envelope"] = {"01": Decimal("59.00"), "02": Decimal("41.00")}
    caminho = gravar_pacote(**kwargs)
    pacote = ler_pacote(caminho)

    veredito, _ = rederivar_veredito(pacote)

    assert veredito == RECUSADO


def test_rederiva_recusa_quando_defeito_omitido_no_envelope(tmp_path):
    kwargs = _pacote_aceito_kwargs(tmp_path)
    kwargs["defeitos_envelope"] = []
    caminho = gravar_pacote(**kwargs)
    pacote = ler_pacote(caminho)

    veredito, _ = rederivar_veredito(pacote)

    assert veredito == RECUSADO


def test_rederiva_preserva_snan_sem_falhar_o_gravador(tmp_path):
    kwargs = _pacote_aceito_kwargs(tmp_path)
    kwargs["agregado_controles"] = _controles(
        10, 1, Decimal("sNaN"), Decimal("1.00"), Decimal("50.00")
    )
    caminho = gravar_pacote(**kwargs)
    pacote = ler_pacote(caminho)

    assert pacote["agregado_controles"]["sum_vl_liquido"] == {"tipo": "Decimal", "texto": "sNaN"}
    veredito, _ = rederivar_veredito(pacote)
    assert veredito == RECUSADO


def test_par_monetario_distingue_tipo_recebido():
    assert par_monetario(Decimal("0.00")) == {"tipo": "Decimal", "texto": "0.00"}
    assert par_monetario("0.00") == {"tipo": "str", "texto": "0.00"}
    assert par_monetario(0.0) == {"tipo": "float", "texto": "0.0"}
    assert par_monetario(None) is None


def test_rotulo_adulterado_e_ignorado_na_rederivacao(tmp_path):
    """Um pacote onde só o rótulo do veredito foi trocado é recusado, porque
    `rederivar_veredito` nunca lê `veredito_gravado`."""
    kwargs = _pacote_aceito_kwargs(tmp_path)
    caminho = gravar_pacote(**kwargs)

    bruto = json.loads(caminho.read_text(encoding="utf-8"))
    assert bruto["veredito_gravado"] == ACEITO
    bruto["veredito_gravado"] = ACEITO_SEM_ANCORA
    bruto["causa_gravada"] = "NAO_MEDIDO"
    caminho.write_text(json.dumps(bruto), encoding="utf-8")

    pacote_adulterado = ler_pacote(caminho)
    veredito, _ = rederivar_veredito(pacote_adulterado)

    assert veredito == ACEITO
    assert veredito != pacote_adulterado["veredito_gravado"]


def test_rotulo_adulterado_em_execucao_legitimamente_recusada(tmp_path):
    """Uma execução RECUSADA de verdade, com o rótulo trocado para ACEITO,
    ainda rederiva RECUSADO — o rótulo não muda o que os insumos produzem."""
    kwargs = _pacote_aceito_kwargs(tmp_path)
    kwargs["hash_declarado"] = "b" * 64
    caminho = gravar_pacote(**kwargs)

    bruto = json.loads(caminho.read_text(encoding="utf-8"))
    assert bruto["veredito_gravado"] == RECUSADO
    bruto["veredito_gravado"] = ACEITO
    caminho.write_text(json.dumps(bruto), encoding="utf-8")

    pacote_adulterado = ler_pacote(caminho)
    veredito, _ = rederivar_veredito(pacote_adulterado)

    assert veredito == RECUSADO


def test_tres_hashes_gravados_e_conferidos_na_rederivacao(tmp_path):
    kwargs = _pacote_aceito_kwargs(tmp_path)
    caminho = gravar_pacote(**kwargs)
    pacote = ler_pacote(caminho)

    assert pacote["hash_ancorado"] == "a" * 64
    assert pacote["hash_observado"] == "a" * 64
    assert pacote["hash_declarado"] == "a" * 64
    veredito, _ = rederivar_veredito(pacote)
    assert veredito == ACEITO


def test_tres_hashes_dois_batendo_um_divergente_nao_aceita(tmp_path):
    """Ancorado == observado, declarado diverge: com só dois hashes
    conferidos isso rederivaria ACEITO por engano — a tarefa exige os TRÊS."""
    kwargs = _pacote_aceito_kwargs(tmp_path)
    kwargs["hash_declarado"] = "c" * 64
    caminho = gravar_pacote(**kwargs)
    pacote = ler_pacote(caminho)

    veredito, causa = rederivar_veredito(pacote)

    assert veredito == RECUSADO
    assert causa == "DIVERGENCIA"


def test_tres_hashes_hash_observado_ausente_sem_evento_falha_recusa(tmp_path):
    kwargs = _pacote_aceito_kwargs(tmp_path)
    kwargs["hash_observado"] = CHAVE_AUSENTE
    caminho = gravar_pacote(**kwargs)
    pacote = ler_pacote(caminho)

    veredito, _ = rederivar_veredito(pacote)

    assert veredito == RECUSADO


def test_precedencia_sem_ancora_decide_antes_de_qualquer_hash(tmp_path):
    """Contrato NAO_MEDIDO dá ACEITO_SEM_ANCORA mesmo com hash ancorado
    presente e nenhum hash observado produzido (ADR 0005)."""
    caminho = gravar_pacote(
        diretorio=tmp_path,
        competencia_solicitada="2026-04",
        contrato_status="NAO_MEDIDO",
        hash_ancorado="d" * 64,
        hash_observado=CHAVE_AUSENTE,
        hash_declarado=CHAVE_AUSENTE,
    )
    pacote = ler_pacote(caminho)

    veredito, causa = rederivar_veredito(pacote)

    assert veredito == ACEITO_SEM_ANCORA
    assert causa == "NAO_MEDIDO"


def test_precedencia_sem_ancora_ignora_chaves_ausentes_distintas_de_null(tmp_path):
    caminho = gravar_pacote(
        diretorio=tmp_path,
        competencia_solicitada="2026-05",
        contrato_status="NAO_MEDIDO",
        aprovador=None,
    )
    pacote = ler_pacote(caminho)

    assert pacote["contrato_validade"]["aprovador"] is None
    assert pacote["contrato_validade"]["aprovado_em"] == CHAVE_AUSENTE
    veredito, _ = rederivar_veredito(pacote)
    assert veredito == ACEITO_SEM_ANCORA


# ---------------------------------------------------------------------------
# eval_2: nao_sobrescreve
# ---------------------------------------------------------------------------


def test_duas_execucoes_nao_sobrescreve(tmp_path):
    kwargs = _pacote_aceito_kwargs(tmp_path)
    primeiro = gravar_pacote(**kwargs)
    conteudo_primeiro_antes = primeiro.read_text(encoding="utf-8")

    kwargs2 = _pacote_aceito_kwargs(tmp_path)
    kwargs2["duracao_segundos"] = 9.9
    segundo = gravar_pacote(**kwargs2)

    assert primeiro != segundo
    assert primeiro.exists()
    assert segundo.exists()
    assert primeiro.read_text(encoding="utf-8") == conteudo_primeiro_antes

    execucoes = listar_execucoes(kwargs["diretorio"], "2026-03")
    assert len(execucoes) == 2
    assert set(execucoes) == {primeiro, segundo}


def test_nao_sobrescreve_grava_id_de_execucao_distinto(tmp_path):
    kwargs = _pacote_aceito_kwargs(tmp_path)
    primeiro = ler_pacote(gravar_pacote(**kwargs))
    segundo = ler_pacote(gravar_pacote(**kwargs))

    assert primeiro["execucao_id"] != segundo["execucao_id"]


# ---------------------------------------------------------------------------
# eval_3: vereditos
# ---------------------------------------------------------------------------


def test_quatro_vereditos_terminais_sao_distinguiveis(tmp_path):
    aceito = ler_pacote(gravar_pacote(**_pacote_aceito_kwargs(tmp_path)))

    kwargs_recusado = _pacote_aceito_kwargs(tmp_path)
    kwargs_recusado["hash_declarado"] = "f" * 64
    recusado = ler_pacote(gravar_pacote(**kwargs_recusado))

    sem_ancora = ler_pacote(
        gravar_pacote(
            diretorio=tmp_path,
            competencia_solicitada="2026-06",
            contrato_status="NAO_MEDIDO",
        )
    )

    erro = ler_pacote(
        gravar_pacote(
            diretorio=tmp_path,
            competencia_solicitada="2026-07",
            contrato_status="OK",
            hash_ancorado="e" * 64,
            hash_observado=CHAVE_AUSENTE,
            evento_falha={"tipo": "TIMEOUT", "mensagem": "leitura interrompida"},
        )
    )

    vereditos = {
        rederivar_veredito(aceito)[0],
        rederivar_veredito(recusado)[0],
        rederivar_veredito(sem_ancora)[0],
        rederivar_veredito(erro)[0],
    }

    assert vereditos == {ACEITO, RECUSADO, ACEITO_SEM_ANCORA, ERRO}
    assert len(evidencia.VEREDITOS_TERMINAIS) == 4


def test_vereditos_contrato_recusado_exige_politica_e_clausula_gravadas(tmp_path):
    caminho = gravar_pacote(
        diretorio=tmp_path,
        competencia_solicitada="2026-08",
        contrato_status="RECUSADO",
        politica_recusada={"modo": "HALF_UP"},
        clausula_adr_violada="ADR 0001 — meio-para-par",
    )
    pacote = ler_pacote(caminho)

    veredito, causa = rederivar_veredito(pacote)

    assert veredito == RECUSADO
    assert causa == "CONTRATO_RECUSADO"


def test_vereditos_contrato_recusado_sem_prova_e_pacote_malformado(tmp_path):
    """RECUSADO por contrato exige a política gravada (precedência declarada
    na tarefa) — sem ela a rederivação recusa por falta de prova, nunca
    supõe a causa."""
    pacote_malformado = {
        "competencia_solicitada": "2026-09",
        "contrato_status": "RECUSADO",
        "politica_recusada": None,
        "clausula_adr_violada": None,
    }

    with pytest.raises(EvidenciaRecusada):
        rederivar_veredito(pacote_malformado)


def test_vereditos_erro_exige_evento_de_falha_gravado(tmp_path):
    """Hash observado ausente SEM evento de falha não é ERRO — cai no
    julgamento normal e recusa por falta de hash."""
    caminho = gravar_pacote(
        diretorio=tmp_path,
        competencia_solicitada="2026-10",
        contrato_status="OK",
        hash_ancorado="e" * 64,
        hash_observado=CHAVE_AUSENTE,
    )
    pacote = ler_pacote(caminho)

    veredito, causa = rederivar_veredito(pacote)

    assert veredito == RECUSADO
    assert causa == "DIVERGENCIA"
