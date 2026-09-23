"""Testes do carregador de contrato — âncora, procedência, layout e política decimal.

Cada teste constrói o seu próprio YAML em `tmp_path`: o carregador é uma
função pura de caminho -> Contrato | NAO_MEDIDO, e nenhum teste depende do
contrato real da competência 2026-01 estar no disco.
"""

from __future__ import annotations

import copy
import sys
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pda.contrato import (  # noqa: E402
    NAO_MEDIDO,
    ContratoRecusado,
    carregar_contrato,
)


def _contrato_valido() -> dict:
    return {
        "competencia": "2026-01",
        "procedencia": {
            "fonte": "D.SDA.PDA.003.EMI.202601.CSV.ZIP",
            "publicado_em": "2026-02-25",
            "hash_zip_sha256": "428626857daf30a3e6a4c1b9d0e2f5a7b8c3d6e9f1a2b4c5d7e8f9a0b1c2d3e4",
            "hash_csv_sha256": "7d1e2c3b4a5968f7e6d5c4b3a291807f6e5d4c3b2a1908f7e6d5c4b3a29180f",
        },
        "layout": {
            "total_colunas": 14,
            "separador": ";",
            "encoding": "latin-1",
            "posicoes": {"vl_liquido": 9, "especie": 12, "descricao_especie": 13},
        },
        "ancora": {
            "count_linhas": 41572553,
            "sum_vl_liquido": "78521752562.12",
            "min_vl_liquido": "0.00",
            "max_vl_liquido": "183725.76",
            "linhas_invalidas": 0,
            "aprovado_por": "nobru",
            "aprovado_em": "2026-09-21",
        },
        "cardinalidade": {
            "codigos_distintos": 65,
            "descricoes_distintas": 52,
            "colapsos": 11,
            "codigos_colapsados": 24,
        },
        "defeitos_conhecidos": [
            {
                "tipo": "CONFIRMED_SOURCE_DEFECT",
                "descricao": "11 descricoes cobrem 24 codigos (identidade colapsada, ADR 0008)",
                "quantidade": 11,
                "aprovador": "nobru",
                "aprovado_em": "2026-09-21",
            }
        ],
        "politica_decimal": {
            "modo": "HALF_EVEN",
            "granularidade": "total",
            "escala": 2,
            "escala_maxima_intermediarios": 3,
            "precisao": 14,
            "nao_negativo": True,
        },
    }


def _escrever(tmp_path: Path, dados: dict, nome: str = "contrato.yaml") -> Path:
    caminho = tmp_path / nome
    caminho.write_text(yaml.safe_dump(dados, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return caminho


def _sem(dados: dict, *chave_pontilhada: str) -> dict:
    dados = copy.deepcopy(dados)
    alvo = dados
    for parte in chave_pontilhada[:-1]:
        alvo = alvo[parte]
    del alvo[chave_pontilhada[-1]]
    return dados


# ---------------------------------------------------------------------------
# eval_1: contrato ancorado carrega; os dois hashes; política ausente vira
# NAO_MEDIDO; política que contradiz o ADR é recusada.
# ---------------------------------------------------------------------------


def test_ancorada_carrega_contrato_completo(tmp_path):
    caminho = _escrever(tmp_path, _contrato_valido())

    contrato = carregar_contrato(caminho)

    assert contrato != NAO_MEDIDO
    assert contrato.competencia == "2026-01"
    assert contrato.ancora.count_linhas == 41572553
    assert contrato.ancora.sum_vl_liquido == Decimal("78521752562.12")
    assert isinstance(contrato.ancora.sum_vl_liquido, Decimal)
    assert contrato.ancora.linhas_invalidas == 0
    assert contrato.cardinalidade.codigos_distintos == 65
    assert contrato.cardinalidade.colapsos == 11
    assert contrato.cardinalidade.codigos_colapsados == 24
    assert len(contrato.defeitos_conhecidos) == 1
    assert contrato.defeitos_conhecidos[0].tipo == "CONFIRMED_SOURCE_DEFECT"
    assert contrato.defeitos_conhecidos[0].quantidade == 11
    assert contrato.politica_decimal.modo == "HALF_EVEN"
    assert contrato.politica_decimal.precisao == 14


def test_ancorada_recusa_float_em_campo_monetario(tmp_path):
    dados = _contrato_valido()
    dados["ancora"]["sum_vl_liquido"] = 78521752562.12  # sem aspas -> float
    caminho = _escrever(tmp_path, dados)

    with pytest.raises(ContratoRecusado):
        carregar_contrato(caminho)


def test_ancorada_recusa_controle_nao_finito(tmp_path):
    dados = _contrato_valido()
    dados["ancora"]["max_vl_liquido"] = "Infinity"
    caminho = _escrever(tmp_path, dados)

    with pytest.raises(ContratoRecusado):
        carregar_contrato(caminho)


def test_ancorada_recusa_contagem_negativa_ou_booleana(tmp_path):
    negativa = _contrato_valido()
    negativa["ancora"]["linhas_invalidas"] = -1
    with pytest.raises(ContratoRecusado):
        carregar_contrato(_escrever(tmp_path, negativa, "negativa.yaml"))

    booleana = _contrato_valido()
    booleana["cardinalidade"]["colapsos"] = False
    with pytest.raises(ContratoRecusado):
        carregar_contrato(_escrever(tmp_path, booleana, "booleana.yaml"))


def test_hash_zip_e_csv_sao_distintos(tmp_path):
    caminho = _escrever(tmp_path, _contrato_valido())

    contrato = carregar_contrato(caminho)

    assert contrato.procedencia.hash_zip_sha256 != contrato.procedencia.hash_csv_sha256
    assert contrato.procedencia.hash_zip_sha256
    assert contrato.procedencia.hash_csv_sha256


def test_hash_zip_e_csv_iguais_e_recusado(tmp_path):
    dados = _contrato_valido()
    dados["procedencia"]["hash_csv_sha256"] = dados["procedencia"]["hash_zip_sha256"]
    caminho = _escrever(tmp_path, dados)

    with pytest.raises(ContratoRecusado):
        carregar_contrato(caminho)


def test_hash_zip_e_csv_falta_hash_do_csv_e_nao_medido(tmp_path):
    dados = _sem(_contrato_valido(), "procedencia", "hash_csv_sha256")
    caminho = _escrever(tmp_path, dados)

    assert carregar_contrato(caminho) == NAO_MEDIDO


def test_sem_politica_decimal_retorna_nao_medido(tmp_path):
    dados = _sem(_contrato_valido(), "politica_decimal")
    arquivos_antes = set(tmp_path.iterdir())
    caminho = _escrever(tmp_path, dados)

    resultado = carregar_contrato(caminho)

    assert resultado == NAO_MEDIDO
    assert set(tmp_path.iterdir()) == arquivos_antes | {caminho}


def test_politica_contradiz_adr_modo_half_up_e_recusada(tmp_path):
    dados = _contrato_valido()
    dados["politica_decimal"]["modo"] = "HALF_UP"
    caminho = _escrever(tmp_path, dados)

    with pytest.raises(ContratoRecusado):
        carregar_contrato(caminho)


def test_politica_contradiz_adr_granularidade_por_campo_e_recusada(tmp_path):
    dados = _contrato_valido()
    dados["politica_decimal"]["granularidade"] = "por_campo"
    caminho = _escrever(tmp_path, dados)

    with pytest.raises(ContratoRecusado):
        carregar_contrato(caminho)


def test_politica_contradiz_adr_precisao_insuficiente_e_recusada(tmp_path):
    dados = _contrato_valido()
    dados["politica_decimal"]["precisao"] = 13  # representa o total, mas não soma sob ele (ADR 0007)
    caminho = _escrever(tmp_path, dados)

    with pytest.raises(ContratoRecusado):
        carregar_contrato(caminho)


def test_politica_contradiz_adr_dominio_negativo_e_recusada(tmp_path):
    dados = _contrato_valido()
    dados["politica_decimal"]["nao_negativo"] = False
    caminho = _escrever(tmp_path, dados)

    with pytest.raises(ContratoRecusado):
        carregar_contrato(caminho)


# ---------------------------------------------------------------------------
# eval_2: sem âncora, o carregador retorna NAO_MEDIDO como valor — sem
# gravar nada em disco e sem encerrar o processo.
# ---------------------------------------------------------------------------


def test_sem_ancora_retorna_nao_medido_sem_gravar(tmp_path):
    dados = _sem(_contrato_valido(), "ancora")
    arquivos_antes = set(tmp_path.iterdir())
    caminho = _escrever(tmp_path, dados)

    resultado = carregar_contrato(caminho)

    assert resultado == NAO_MEDIDO
    # nada além do próprio arquivo de entrada foi gravado
    assert set(tmp_path.iterdir()) == arquivos_antes | {caminho}


def test_sem_ancora_nao_encerra_o_processo(tmp_path):
    dados = _sem(_contrato_valido(), "ancora")
    caminho = _escrever(tmp_path, dados)

    # a chamada retorna normalmente — nenhuma exceção, nenhum sys.exit
    resultado = carregar_contrato(caminho)
    assert resultado == NAO_MEDIDO


def test_ancora_sem_aprovador_ou_data_e_nao_medido(tmp_path):
    sem_aprovador = _sem(_contrato_valido(), "ancora", "aprovado_por")
    assert carregar_contrato(_escrever(tmp_path, sem_aprovador, "sem_aprovador.yaml")) == NAO_MEDIDO

    sem_data = _sem(_contrato_valido(), "ancora", "aprovado_em")
    assert carregar_contrato(_escrever(tmp_path, sem_data, "sem_data.yaml")) == NAO_MEDIDO


def test_contrato_vazio_e_nao_medido(tmp_path):
    caminho = tmp_path / "vazio.yaml"
    caminho.write_text("", encoding="utf-8")

    assert carregar_contrato(caminho) == NAO_MEDIDO


# ---------------------------------------------------------------------------
# eval_3: o layout declara as 14 posições, com Espécie em 12 e 13.
# ---------------------------------------------------------------------------


def test_layout_declara_14_posicoes_com_especie_em_12_e_13(tmp_path):
    caminho = _escrever(tmp_path, _contrato_valido())

    contrato = carregar_contrato(caminho)

    assert contrato.layout.total_colunas == 14
    assert contrato.layout.posicoes["especie"] == 12
    assert contrato.layout.posicoes["descricao_especie"] == 13
    assert contrato.layout.posicoes["vl_liquido"] == 9


def test_layout_recusa_total_de_colunas_diferente_de_14(tmp_path):
    dados = _contrato_valido()
    dados["layout"]["total_colunas"] = 13
    caminho = _escrever(tmp_path, dados)

    with pytest.raises(ContratoRecusado):
        carregar_contrato(caminho)


def test_layout_recusa_especie_fora_dos_indices_12_e_13(tmp_path):
    dados = _contrato_valido()
    dados["layout"]["posicoes"]["descricao_especie"] = 6
    caminho = _escrever(tmp_path, dados)

    with pytest.raises(ContratoRecusado):
        carregar_contrato(caminho)


def test_layout_recusa_declaracao_por_nome_em_vez_de_indice(tmp_path):
    dados = _contrato_valido()
    dados["layout"]["posicoes"]["especie"] = "Espécie"  # nome, não índice
    caminho = _escrever(tmp_path, dados)

    with pytest.raises(ContratoRecusado):
        carregar_contrato(caminho)


# --- Extensão: particionamento, limites de expoente e mapa de colapsos ---

CONTRATO_REAL = Path(__file__).resolve().parent.parent / "contracts" / "competencia-202601.yaml"


def _com_blocos_novos() -> dict:
    d = _contrato_valido()
    d["politica_decimal"]["emax"] = 999999
    d["politica_decimal"]["emin"] = -999999
    d["particionamento"] = {
        "chave": "competencia",
        "caminho": "s3a://landing/pda/beneficios-emitidos",
        "formato": "parquet",
        "valores_medidos": ["2026-01", "fatia-teste"],
        "objetos_auxiliares_ignorados": ["_SUCCESS"],
    }
    d["mapa_colapsos"] = {
        "grupos": [{"descricao": "APOSENTADORIA", "codigos": ["01", "02"]}],
        "aprovado_por": "nobru",
        "aprovado_em": "2026-09-23",
    }
    return d


def _recusa(tmp_path, mutar):
    d = _com_blocos_novos()
    mutar(d)
    with pytest.raises(ContratoRecusado):
        carregar_contrato(_escrever(tmp_path, d))


def test_expoe_particionamento(tmp_path):
    p = carregar_contrato(_escrever(tmp_path, _com_blocos_novos())).particionamento
    assert p.chave == "competencia"
    assert p.caminho == "s3a://landing/pda/beneficios-emitidos"
    assert p.formato == "parquet"
    assert p.valores_medidos == ("2026-01", "fatia-teste")
    assert p.objetos_auxiliares_ignorados == ("_SUCCESS",)


def test_expoe_limites_de_expoente(tmp_path):
    c = carregar_contrato(_escrever(tmp_path, _com_blocos_novos()))
    assert c.politica_decimal.emax == 999999
    assert c.politica_decimal.emin == -999999


def test_expoe_mapa_de_colapsos(tmp_path):
    m = carregar_contrato(_escrever(tmp_path, _com_blocos_novos())).mapa_colapsos
    assert m.aprovado_por == "nobru" and m.aprovado_em == "2026-09-23"
    assert m.grupos[0].descricao == "APOSENTADORIA"
    assert m.grupos[0].codigos == ("01", "02")


def test_campos_novos_sao_opcionais(tmp_path):
    c = carregar_contrato(_escrever(tmp_path, _contrato_valido()))
    assert c.particionamento is None
    assert c.mapa_colapsos is None


def test_ausencia_vira_none_nao_zero(tmp_path):
    c = carregar_contrato(_escrever(tmp_path, _contrato_valido()))
    assert c.politica_decimal.emax is None
    assert c.politica_decimal.emin is None


def test_fixture_sem_campos_novos(tmp_path):
    c = carregar_contrato(_escrever(tmp_path, _contrato_valido()))
    assert c != NAO_MEDIDO
    assert c.ancora.count_linhas == 41572553


def test_suite_selada_continua_passando(tmp_path):
    # O comportamento selado segue intacto com os blocos novos presentes.
    c = carregar_contrato(_escrever(tmp_path, _com_blocos_novos()))
    assert c.politica_decimal.precisao == 14
    assert c.ancora.sum_vl_liquido == Decimal("78521752562.12")


def test_contrato_real_expoe_os_dois():
    c = carregar_contrato(CONTRATO_REAL)
    assert c.particionamento.chave == "competencia"
    assert "fatia-teste" in c.particionamento.valores_medidos
    assert c.politica_decimal.emax == 999999
    assert c.politica_decimal.emin == -999999


def test_limites_que_estouram_a_ancora_recusados(tmp_path):
    _recusa(tmp_path, lambda d: d["politica_decimal"].update(emax=9, emin=-10))


def test_nao_relaxa_recusa_de_float(tmp_path):
    _recusa(tmp_path, lambda d: d["ancora"].update(sum_vl_liquido=78521752562.12))


def test_nao_muda_precisao_derivada(tmp_path):
    _recusa(tmp_path, lambda d: d["politica_decimal"].update(precisao=13))


def test_nao_le_o_yaml_duas_vezes(tmp_path, monkeypatch):
    import pda.contrato as mod

    chamadas = []
    original = mod.yaml.safe_load
    monkeypatch.setattr(
        mod.yaml, "safe_load", lambda *a, **k: chamadas.append(1) or original(*a, **k)
    )
    carregar_contrato(_escrever(tmp_path, _com_blocos_novos()))
    assert len(chamadas) == 1


def test_bloco_presente_e_invalido_recusado_emax_nao_inteiro(tmp_path):
    _recusa(tmp_path, lambda d: d["politica_decimal"].update(emax="999999"))


def test_bloco_presente_e_invalido_recusado_emin_maior_que_emax(tmp_path):
    _recusa(tmp_path, lambda d: d["politica_decimal"].update(emax=-5, emin=5))


def test_bloco_presente_e_invalido_recusado_particionamento_sem_chave(tmp_path):
    _recusa(tmp_path, lambda d: d["particionamento"].pop("chave"))


def test_bloco_presente_e_invalido_recusado_grupo_de_um_codigo(tmp_path):
    _recusa(tmp_path, lambda d: d["mapa_colapsos"]["grupos"][0].update(codigos=["01"]))


def test_bloco_presente_e_invalido_recusado_codigo_repetido(tmp_path):
    _recusa(
        tmp_path,
        lambda d: d["mapa_colapsos"]["grupos"].append(
            {"descricao": "PENSAO", "codigos": ["02", "03"]}
        ),
    )


def test_bloco_presente_e_invalido_recusado_sem_aprovador(tmp_path):
    _recusa(tmp_path, lambda d: d["mapa_colapsos"].pop("aprovado_por"))


def test_bloco_presente_e_invalido_recusado_sem_data(tmp_path):
    _recusa(tmp_path, lambda d: d["mapa_colapsos"].pop("aprovado_em"))
