"""Testes da leitura posicional — sha256 inalterado, proteção W-1, colunas
trocadas, gramática monetária, defeitos classificados e identidade colapsada.

Cada teste monta o seu próprio arquivo em `tmp_path`, a partir do conteúdo do
fixture `tests/fixtures/competencia-min.csv` — o fixture nunca é editado nem
tem seu modo alterado; cópias em `tmp_path` recebem chmod conforme o cenário.
"""

from __future__ import annotations

import csv
import decimal
import hashlib
import os
import stat
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pda.contrato import (  # noqa: E402
    Ancora,
    Cardinalidade,
    Contrato,
    Layout,
    PoliticaDecimal,
    Procedencia,
)
from pda.leitura import (  # noqa: E402
    IDENTIDADE_COLAPSADA,
    LeituraRecusada,
    ler_competencia,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "competencia-min.csv"
ENCODING = "utf-8"
SEPARADOR = ";"
IDX_VALOR = 9
IDX_ESPECIE = 12
IDX_DESCRICAO = 13


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
            posicoes={"vl_liquido": IDX_VALOR, "especie": IDX_ESPECIE, "descricao_especie": IDX_DESCRICAO},
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


def _ler_linhas_base():
    with open(FIXTURE, encoding=ENCODING, newline="") as arquivo:
        leitor = csv.reader(arquivo, delimiter=SEPARADOR)
        cabecalho = next(leitor)
        linhas = [list(linha) for linha in leitor]
    return cabecalho, linhas


def _escrever_csv(caminho: Path, cabecalho, linhas) -> Path:
    with open(caminho, "w", encoding=ENCODING, newline="") as arquivo:
        escritor = csv.writer(arquivo, delimiter=SEPARADOR)
        escritor.writerow(cabecalho)
        escritor.writerows(linhas)
    return caminho


def _protegido(caminho: Path) -> Path:
    os.chmod(caminho, 0o444)
    return caminho


def _fixture_protegida(tmp_path: Path, linhas_extra=()) -> Path:
    cabecalho, linhas = _ler_linhas_base()
    linhas = linhas + list(linhas_extra)
    caminho = _escrever_csv(tmp_path / "competencia.csv", cabecalho, linhas)
    return _protegido(caminho)


def _linha_extra(codigo, descricao, valor):
    desc20 = descricao.ljust(20)[:20]
    return [
        "D1", "M", "U", "B1", "SP",
        "1", "001", "SPAULO", "SPAULO",
        valor, "0", "20260101",
        codigo, desc20,
    ]


# ---------------------------------------------------------------------------
# eval_1: leitura posicional; _raw sem 444 bloqueia; Espécie 12/13 trocadas
# ---------------------------------------------------------------------------


def test_leitura_normal_produz_sha256_identico_e_totais_corretos_sob_contexto_decimal_adverso(
    tmp_path,
):
    caminho = _fixture_protegida(tmp_path)
    hash_esperado = hashlib.sha256(caminho.read_bytes()).hexdigest()
    contrato = _contrato_minimo()

    contexto_ambiente = decimal.getcontext()
    salvo = contexto_ambiente.copy()
    try:
        contexto_ambiente.prec = 5
        contexto_ambiente.Emax = 5
        contexto_ambiente.Emin = -5
        contexto_ambiente.traps[decimal.Inexact] = True
        contexto_ambiente.traps[decimal.Overflow] = True

        resultado = ler_competencia(caminho, contrato)
    finally:
        decimal.setcontext(salvo)

    assert resultado.sha256_antes == hash_esperado
    assert resultado.sha256_depois == hash_esperado
    assert resultado.registros_lidos == 7
    assert resultado.linhas_invalidas == []
    assert resultado.total_por_codigo == {
        "01": Decimal("1621.00"),
        "03": Decimal("100.00"),
        "23": Decimal("50.00"),
        "59": Decimal("25.00"),
        "04": Decimal("200.00"),
        "83": Decimal("10.00"),
        "02": Decimal("5.00"),
    }
    assert sum(resultado.total_por_codigo.values()) == Decimal("2011.00")
    # a origem continua byte a byte igual depois da leitura
    assert hashlib.sha256(caminho.read_bytes()).hexdigest() == hash_esperado


def test_w1_protecao_recusa_arquivo_sem_444(tmp_path):
    cabecalho, linhas = _ler_linhas_base()
    caminho = _escrever_csv(tmp_path / "competencia.csv", cabecalho, linhas)
    os.chmod(caminho, 0o644)
    contrato = _contrato_minimo()

    with pytest.raises(LeituraRecusada):
        ler_competencia(caminho, contrato)


def test_w1_protecao_recusa_mesmo_com_sha256_estavel(tmp_path):
    # hash antes/depois não prova proteção (W-1): um arquivo em 0666 pode
    # nunca ser escrito durante a leitura e ainda assim não está protegido.
    cabecalho, linhas = _ler_linhas_base()
    caminho = _escrever_csv(tmp_path / "competencia.csv", cabecalho, linhas)
    os.chmod(caminho, 0o666)
    hash_estavel = hashlib.sha256(caminho.read_bytes()).hexdigest()
    contrato = _contrato_minimo()

    with pytest.raises(LeituraRecusada):
        ler_competencia(caminho, contrato)

    assert hashlib.sha256(caminho.read_bytes()).hexdigest() == hash_estavel


def test_especie_12_13_trocadas_bloqueia_leitura(tmp_path):
    cabecalho, linhas = _ler_linhas_base()
    trocadas = []
    for linha in linhas:
        linha = list(linha)
        linha[IDX_ESPECIE], linha[IDX_DESCRICAO] = linha[IDX_DESCRICAO], linha[IDX_ESPECIE]
        trocadas.append(linha)
    # o cabeçalho permanece byte a byte igual — as duas colunas chamam-se
    # "Espécie" — só a posição pode distinguir a troca
    assert cabecalho[IDX_ESPECIE] == cabecalho[IDX_DESCRICAO] == "Espécie"

    caminho = _escrever_csv(tmp_path / "trocada.csv", cabecalho, trocadas)
    _protegido(caminho)
    contrato = _contrato_minimo()

    with pytest.raises(LeituraRecusada):
        ler_competencia(caminho, contrato)


def test_especie_12_13_trocadas_de_nomes_diferentes_nao_e_o_que_bloqueia(tmp_path):
    # o gate confere FORMATO por posição, não header — trocar colunas de
    # NOMES diferentes (ex.: Vl Líquido <-> Ramo Atividade) não é o cenário
    # do ADR 0002 e não deve satisfazer este teste sozinho: a leitura só
    # bloqueia quando o formato medido nas posições 12/13 diverge do índice.
    cabecalho, linhas = _ler_linhas_base()
    trocadas = []
    for linha in linhas:
        linha = list(linha)
        linha[10], linha[11] = linha[11], linha[10]
        trocadas.append(linha)

    caminho = _escrever_csv(tmp_path / "outra_troca.csv", cabecalho, trocadas)
    _protegido(caminho)
    contrato = _contrato_minimo()

    # essa troca não mexe nas posições 12/13 — a leitura continua e produz
    # os mesmos totais por código, sem levantar LeituraRecusada
    resultado = ler_competencia(caminho, contrato)
    assert resultado.registros_lidos == 7


# ---------------------------------------------------------------------------
# eval_2: ilegível vira inválida; NaN também; descrição que colapsa acusa
# ---------------------------------------------------------------------------


def test_valor_monetario_ilegivel_entra_em_linhas_invalidas(tmp_path):
    extra = _linha_extra("99", "Ilegivel Teste", "XYZ")
    caminho = _fixture_protegida(tmp_path, linhas_extra=[extra])
    contrato = _contrato_minimo()

    resultado = ler_competencia(caminho, contrato)

    assert resultado.registros_lidos == 8
    assert len(resultado.linhas_invalidas) == 1
    invalida = resultado.linhas_invalidas[0]
    assert invalida.identidade == 8
    assert invalida.valor_original == "XYZ"
    assert invalida.posicao == IDX_VALOR
    assert "99" not in resultado.total_por_codigo


def test_valores_especiais_viram_linhas_invalidas_sem_derrubar_a_leitura(tmp_path):
    especiais = [
        ("90", "Nan Teste", "NaN"),
        ("91", "Infinity Teste", "Infinity"),
        ("92", "Underscore Teste", "1_000"),
        ("93", "Cientifica Teste", "1e3"),
    ]
    extras = [_linha_extra(codigo, descricao, valor) for codigo, descricao, valor in especiais]
    caminho = _fixture_protegida(tmp_path, linhas_extra=extras)
    contrato = _contrato_minimo()

    # nenhum dos quatro derruba a execução inteira — cada um vira UMA linha
    # inválida, nunca um erro do processo (um NaN vivo até um min()/max()
    # levantaria InvalidOperation e transformaria defeito de linha em erro)
    resultado = ler_competencia(caminho, contrato)

    assert resultado.registros_lidos == 7 + len(especiais)
    assert len(resultado.linhas_invalidas) == len(especiais)
    valores_originais = {linha.valor_original for linha in resultado.linhas_invalidas}
    assert valores_originais == {"NaN", "Infinity", "1_000", "1e3"}
    for codigo, _, _ in especiais:
        assert codigo not in resultado.total_por_codigo


def test_gramatica_monetaria_normaliza_formato_brasileiro_e_recusa_decimal_bruto(tmp_path):
    # a gramática exige preenchimento à esquerda + ponto de milhar + vírgula
    # decimal (medido na fonte); Decimal(bruto) ingênuo recusaria a linha
    # legítima "1.621,00" e aceitaria "1621.00" (ponto decimal, nunca
    # publicado pela fonte) — o oposto do que a leitura deve fazer.
    # a linha "1.621,00" (formato BR legítimo) já está no fixture-base
    extra_invalido = _linha_extra("98", "Decimal Bruto Teste", "1621.00")
    caminho = _fixture_protegida(tmp_path, linhas_extra=[extra_invalido])
    contrato = _contrato_minimo()

    resultado = ler_competencia(caminho, contrato)

    # a linha original em formato BR, com milhar e vírgula, converteu certo
    assert resultado.total_por_codigo["01"] == Decimal("1621.00")
    # a variante em ponto decimal (nunca publicada pela fonte) é ilegível
    invalidos = {linha.valor_original for linha in resultado.linhas_invalidas}
    assert "1621.00" in invalidos
    assert "98" not in resultado.total_por_codigo


def test_valor_negativo_e_fora_de_escala_entram_em_linhas_invalidas(tmp_path):
    extras = [
        _linha_extra("94", "Negativo Teste", "-100,00"),
        _linha_extra("95", "Fora De Escala Teste", "     10,555"),
    ]
    caminho = _fixture_protegida(tmp_path, linhas_extra=extras)
    contrato = _contrato_minimo()

    resultado = ler_competencia(caminho, contrato)

    assert len(resultado.linhas_invalidas) == 2
    assert "94" not in resultado.total_por_codigo
    assert "95" not in resultado.total_por_codigo
    valores = {linha.valor_original for linha in resultado.linhas_invalidas}
    assert "-100,00" in valores
    assert "     10,555" in valores


def test_identidade_colapsada_acusa_descricao_que_cobre_mais_de_um_codigo(tmp_path):
    caminho = _fixture_protegida(tmp_path)
    contrato = _contrato_minimo()

    resultado = ler_competencia(caminho, contrato)

    assert len(resultado.defeitos_identidade_colapsada) == 2
    por_descricao = {
        defeito.descricao: defeito for defeito in resultado.defeitos_identidade_colapsada
    }
    assert set(por_descricao) == {"Pensão por Morte de", "Aposentadoria por In"}

    pensao = por_descricao["Pensão por Morte de"]
    assert pensao.tipo == IDENTIDADE_COLAPSADA
    assert pensao.codigos == ("01", "03", "23", "59")

    aposentadoria = por_descricao["Aposentadoria por In"]
    assert aposentadoria.codigos == ("04", "83")

    # a descrição única (largura também 20/16, mas identidade preservada)
    # nunca aparece como colapso — largura não é critério (ADR 0008)
    assert "Auxílio Reclusão" not in por_descricao

    # as linhas colapsadas continuam válidas: o defeito é da descrição, não
    # da linha, e o valor monetário entra normalmente na soma (Regra 4)
    assert resultado.total_por_codigo["01"] == Decimal("1621.00")
    assert resultado.linhas_invalidas == []


def test_identidade_colapsada_confere_contagem_medida_do_contrato(tmp_path):
    # a contagem de colapsos observada na leitura é conferida contra a
    # contagem MEDIDA que o contrato carrega — um contrato que discorda do
    # que a própria leitura mediu é recusado, nunca silenciosamente aceito.
    caminho = _fixture_protegida(tmp_path)
    contrato = _contrato_minimo(
        cardinalidade=Cardinalidade(
            codigos_distintos=7,
            descricoes_distintas=3,
            colapsos=99,
            codigos_colapsados=99,
        )
    )

    with pytest.raises(LeituraRecusada):
        ler_competencia(caminho, contrato)


# ---------------------------------------------------------------------------
# eval_3: a leitura reporta sua duração para a orquestração medir o total
# ---------------------------------------------------------------------------


def test_leitura_reporta_duracao_em_segundos(tmp_path):
    caminho = _fixture_protegida(tmp_path)
    contrato = _contrato_minimo()

    resultado = ler_competencia(caminho, contrato)

    assert isinstance(resultado.duracao_segundos, float)
    assert resultado.duracao_segundos >= 0.0
