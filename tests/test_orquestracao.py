"""Testes da orquestração — dá dono ao fluxo, do contrato ao veredito.

Cobre a Exit Check da tarefa T-20260921-orquestra-desfecho:

- eval_1: os quatro desfechos gravam pacote com código próprio; R-7 numa
  prova só (byte alterado + sha256 reancorado, âncora monetária original);
  competência solicitada divergente nunca autoriza
  ("desfechos", "r7_centavo_reancorado", "competencia_divergente")
- eval_2: exceção real vira ERRO; o tempo é medido do início da leitura ao
  veredito, nunca por etapa ("excecao", "tempo_total")
- eval_3: só ACEITO autoriza publicar ("autoriza")
"""

from __future__ import annotations

import csv
import hashlib
import os
import sys
import time
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pda import evidencia  # noqa: E402
from pda import juizo as juizo_mod  # noqa: E402
from pda import orquestracao  # noqa: E402
from pda.agregacao import Registro, agregar  # noqa: E402
from pda.contrato import NAO_MEDIDO, carregar_contrato  # noqa: E402
from pda.leitura import ler_competencia  # noqa: E402
from pda.orquestracao import InsumosExecucao, conduzir  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "competencia-min.csv"
ENCODING = "utf-8"
SEPARADOR = ";"
IDX_VALOR = 9
IDX_ESPECIE = 12

SUM_ORIGINAL = Decimal("2011.00")
MIN_ORIGINAL = Decimal("5.00")
MAX_ORIGINAL = Decimal("1621.00")


# ---------------------------------------------------------------------------
# Fixtures de apoio — contrato YAML e CSV protegido, construídos por teste,
# nunca lidos de um estado global.
# ---------------------------------------------------------------------------


def _sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def _contrato_valido(*, competencia: str, hash_csv_sha256: str, **overrides) -> dict:
    dados = {
        "competencia": competencia,
        "procedencia": {
            "fonte": "fixture-teste",
            "publicado_em": "2026-09-22",
            "hash_zip_sha256": "a" * 64,
            "hash_csv_sha256": hash_csv_sha256,
        },
        "layout": {
            "total_colunas": 14,
            "separador": SEPARADOR,
            "encoding": ENCODING,
            "posicoes": {"vl_liquido": IDX_VALOR, "especie": IDX_ESPECIE, "descricao_especie": 13},
        },
        "ancora": {
            "count_linhas": 7,
            "sum_vl_liquido": str(SUM_ORIGINAL),
            "min_vl_liquido": str(MIN_ORIGINAL),
            "max_vl_liquido": str(MAX_ORIGINAL),
            "linhas_invalidas": 0,
            "aprovado_por": "nobru",
            "aprovado_em": "2026-09-21",
        },
        "cardinalidade": {
            "codigos_distintos": 7,
            "descricoes_distintas": 3,
            "colapsos": 2,
            "codigos_colapsados": 6,
        },
        "defeitos_conhecidos": [],
        "politica_decimal": {
            "modo": "HALF_EVEN",
            "granularidade": "total",
            "escala": 2,
            "escala_maxima_intermediarios": 3,
            "precisao": 14,
            "nao_negativo": True,
        },
    }
    dados.update(overrides)
    return dados


def _escrever_yaml(tmp_path: Path, dados: dict, nome: str = "contrato.yaml") -> Path:
    caminho = tmp_path / nome
    caminho.write_text(yaml.safe_dump(dados, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return caminho


def _copiar_csv_protegido(tmp_path: Path, *, alterar: bool = False, nome: str = "competencia.csv") -> Path:
    tmp_path = Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    conteudo = FIXTURE.read_bytes()
    if alterar:
        # Um centavo alterado NOS BYTES do arquivo — "1.621,00" -> "1.621,01".
        assert b"1.621,00" in conteudo
        conteudo = conteudo.replace(b"1.621,00", b"1.621,01", 1)
    caminho = tmp_path / nome
    caminho.write_bytes(conteudo)
    os.chmod(caminho, 0o444)
    return caminho


def _ler_registros(caminho_csv: Path) -> list:
    """Parse independente do CSV, à parte de `leitura.ler_competencia` — o
    mesmo dado, por um caminho de código diferente, para alimentar
    `agregacao.agregar` sem herdar um eventual defeito da leitura."""
    registros = []
    with open(caminho_csv, encoding=ENCODING, newline="") as arquivo:
        leitor = csv.reader(arquivo, delimiter=SEPARADOR)
        next(leitor)  # cabeçalho
        for linha in leitor:
            codigo = linha[IDX_ESPECIE].strip()
            bruto_valor = linha[IDX_VALOR].strip()
            valor = Decimal(bruto_valor.replace(".", "").replace(",", "."))
            registros.append(Registro(codigo=codigo, valor=valor))
    return registros


def _executar_leitura_real(caminho_csv: Path, *, competencia_envelope=None, atraso: float = 0.0):
    """Constrói um `executar_leitura` real: leitura + agregação independentes,
    hash observado igual ao declarado (produtor honesto)."""

    def _executar(contrato):
        if atraso:
            time.sleep(atraso)
        resultado_leitura = ler_competencia(caminho_csv, contrato)
        registros = _ler_registros(caminho_csv)
        agregado = agregar(registros, contrato)
        defeitos_leitura = [
            {"tipo": "VALOR_ILEGIVEL", "valor_original": li.valor_original, "posicao": li.posicao}
            for li in resultado_leitura.linhas_invalidas
        ]
        return InsumosExecucao(
            competencia_contrato=contrato.competencia,
            competencia_envelope=(
                contrato.competencia if competencia_envelope is None else competencia_envelope
            ),
            hash_ancorado=contrato.procedencia.hash_csv_sha256,
            hash_observado=resultado_leitura.sha256_depois,
            hash_declarado=resultado_leitura.sha256_depois,
            agregado=agregado,
            diferencas=(),
            defeitos_leitura=defeitos_leitura,
            defeitos_envelope=defeitos_leitura,
            totais_leitura=resultado_leitura.total_por_codigo,
            totais_envelope=agregado.total_por_codigo,
        )

    return _executar


def _montar_bate(tmp_path: Path, *, competencia="2026-03", competencia_envelope=None, atraso=0.0):
    """Uma execução cujo agregado bate com a âncora — ACEITO esperado."""
    caminho_csv = _copiar_csv_protegido(tmp_path)
    hash_csv = _sha256(caminho_csv)
    dados = _contrato_valido(competencia=competencia, hash_csv_sha256=hash_csv)
    caminho_contrato = _escrever_yaml(tmp_path, dados)
    executar = _executar_leitura_real(
        caminho_csv, competencia_envelope=competencia_envelope, atraso=atraso
    )
    return caminho_contrato, executar


def _montar_r7(tmp_path: Path, *, competencia="2026-03"):
    """R-7 numa prova só: byte alterado + sha256 reancorado, âncora monetária original."""
    caminho_csv = _copiar_csv_protegido(tmp_path, alterar=True)
    hash_csv_reancorado = _sha256(caminho_csv)  # reancora o sha256 do arquivo ALTERADO
    dados = _contrato_valido(competencia=competencia, hash_csv_sha256=hash_csv_reancorado)
    # a âncora monetária NÃO é tocada — continua a de _contrato_valido (SUM_ORIGINAL)
    caminho_contrato = _escrever_yaml(tmp_path, dados)
    executar = _executar_leitura_real(caminho_csv)
    return caminho_contrato, executar


# ---------------------------------------------------------------------------
# eval_1 — desfechos: os quatro caminhos gravam pacote com código próprio
# ---------------------------------------------------------------------------


def test_quatro_desfechos_gravam_pacote_com_codigos_de_saida_distintos(tmp_path):
    diretorio = tmp_path / "evidencia"

    # 1) sem âncora
    dados_sem_ancora = _contrato_valido(competencia="2026-04", hash_csv_sha256="b" * 64)
    del dados_sem_ancora["ancora"]
    caminho_sem_ancora = _escrever_yaml(tmp_path, dados_sem_ancora, nome="sem-ancora.yaml")
    assert carregar_contrato(caminho_sem_ancora) == NAO_MEDIDO
    desfecho_sem_ancora = conduzir(
        diretorio_evidencia=diretorio,
        competencia_solicitada="2026-04",
        caminho_contrato=caminho_sem_ancora,
        executar_leitura=lambda contrato: pytest.fail("não deve chegar à leitura"),
    )

    # 2) bate
    caminho_bate, executar_bate = _montar_bate(tmp_path / "bate", competencia="2026-03")
    (tmp_path / "bate").mkdir(exist_ok=True)
    desfecho_bate = conduzir(
        diretorio_evidencia=diretorio,
        competencia_solicitada="2026-03",
        caminho_contrato=caminho_bate,
        executar_leitura=executar_bate,
    )

    # 3) R-7: byte alterado + sha reancorado, âncora monetária original
    (tmp_path / "r7").mkdir(exist_ok=True)
    caminho_r7, executar_r7 = _montar_r7(tmp_path / "r7", competencia="2026-05")
    desfecho_r7 = conduzir(
        diretorio_evidencia=diretorio,
        competencia_solicitada="2026-05",
        caminho_contrato=caminho_r7,
        executar_leitura=executar_r7,
    )

    # 4) exceção real dentro da leitura
    caminho_erro, _ = _montar_bate(tmp_path / "erro", competencia="2026-06")
    (tmp_path / "erro").mkdir(exist_ok=True)

    def _leitura_com_excecao(contrato):
        raise RuntimeError("disco cheio durante a leitura")

    desfecho_erro = conduzir(
        diretorio_evidencia=diretorio,
        competencia_solicitada="2026-06",
        caminho_contrato=caminho_erro,
        executar_leitura=_leitura_com_excecao,
    )

    desfechos = {
        evidencia.ACEITO_SEM_ANCORA: desfecho_sem_ancora,
        evidencia.ACEITO: desfecho_bate,
        evidencia.RECUSADO: desfecho_r7,
        evidencia.ERRO: desfecho_erro,
    }

    for esperado, desfecho in desfechos.items():
        assert desfecho.veredito == esperado, desfecho
        assert desfecho.caminho_pacote is not None
        assert desfecho.caminho_pacote.exists()
        pacote = evidencia.ler_pacote(desfecho.caminho_pacote)
        assert pacote["veredito_gravado"] == esperado

    codigos = [d.codigo_saida for d in desfechos.values()]
    assert len(set(codigos)) == 4, "os quatro desfechos precisam ter código de saída distinto"

    assert desfecho_sem_ancora.autorizado_publicar is False
    assert desfecho_r7.autorizado_publicar is False
    assert desfecho_erro.autorizado_publicar is False
    assert desfecho_bate.autorizado_publicar is True


# ---------------------------------------------------------------------------
# eval_1 — r7_centavo_reancorado
# ---------------------------------------------------------------------------


def test_r7_centavo_reancorado_e_recusado_pelo_juizo_contra_a_ancora_original(tmp_path):
    caminho_contrato, executar = _montar_r7(tmp_path, competencia="2026-05")

    desfecho = conduzir(
        diretorio_evidencia=tmp_path / "evidencia",
        competencia_solicitada="2026-05",
        caminho_contrato=caminho_contrato,
        executar_leitura=executar,
    )

    assert desfecho.veredito == evidencia.RECUSADO
    assert desfecho.autorizado_publicar is False
    pacote = evidencia.ler_pacote(desfecho.caminho_pacote)
    # a fronteira (hash) bate — foi reancorada — a recusa é do juízo, contra
    # a âncora monetária, que nunca foi tocada.
    assert pacote["hash_ancorado"] == pacote["hash_observado"] == pacote["hash_declarado"]
    assert pacote["agregado_controles"]["sum_vl_liquido"]["texto"] != str(SUM_ORIGINAL)
    assert pacote["ancora_controles"]["sum_vl_liquido"]["texto"] == str(SUM_ORIGINAL)


def test_r7_centavo_reancorado_recusa_mesmo_com_juizo_permissivo_injetado(tmp_path, monkeypatch):
    # Ainda que o juízo que RODA nesta chamada seja permissivo, a rederivação
    # independente em `evidencia` (que compara os cinco controles gravados,
    # não o rótulo do juízo) continua a recusar — a prova não depende de
    # confiar numa única decisão.
    caminho_contrato, executar = _montar_r7(tmp_path, competencia="2026-05")

    def _juizo_permissivo(resultado, contrato, diferencas=()):
        return juizo_mod.Veredito(aceito=True, classificacoes={})

    monkeypatch.setattr(orquestracao.juizo_mod, "julgar", _juizo_permissivo)

    desfecho = conduzir(
        diretorio_evidencia=tmp_path / "evidencia",
        competencia_solicitada="2026-05",
        caminho_contrato=caminho_contrato,
        executar_leitura=executar,
    )

    assert desfecho.veredito == evidencia.RECUSADO
    assert desfecho.autorizado_publicar is False


def test_r7_sem_reancorar_recusaria_pelo_sha_antes_do_juizo_comparar(tmp_path):
    # Contraste: sem reancorar o sha256 no contrato, a fronteira (hash) já
    # recusaria sozinha, e o teste acima provaria só metade do que R-7
    # escreve. Aqui o hash_ancorado é o do arquivo ORIGINAL (não alterado),
    # mas o arquivo lido é o ALTERADO — hash_ancorado diverge de
    # hash_observado antes de qualquer comparação monetária.
    caminho_original = _copiar_csv_protegido(tmp_path, nome="original.csv")
    hash_original = _sha256(caminho_original)
    caminho_alterado = _copiar_csv_protegido(tmp_path, alterar=True, nome="alterado.csv")

    dados = _contrato_valido(competencia="2026-05", hash_csv_sha256=hash_original)
    caminho_contrato = _escrever_yaml(tmp_path, dados)
    executar = _executar_leitura_real(caminho_alterado)

    desfecho = conduzir(
        diretorio_evidencia=tmp_path / "evidencia",
        competencia_solicitada="2026-05",
        caminho_contrato=caminho_contrato,
        executar_leitura=executar,
    )

    assert desfecho.veredito == evidencia.RECUSADO
    pacote = evidencia.ler_pacote(desfecho.caminho_pacote)
    assert pacote["hash_ancorado"] != pacote["hash_observado"]


# ---------------------------------------------------------------------------
# eval_1 — competencia_divergente
# ---------------------------------------------------------------------------


def test_competencia_divergente_nunca_autoriza_mesmo_com_veredito_aceito(tmp_path):
    # O contrato e o envelope declaram "2026-01" — artefatos internamente
    # coerentes entre si — mas a execução foi pedida para "2026-02". Hashes,
    # totais e controles concordam; só a competência solicitada, gravada à
    # parte, expõe o problema.
    caminho_contrato, executar = _montar_bate(
        tmp_path, competencia="2026-01", competencia_envelope="2026-01"
    )

    desfecho = conduzir(
        diretorio_evidencia=tmp_path / "evidencia",
        competencia_solicitada="2026-02",
        caminho_contrato=caminho_contrato,
        executar_leitura=executar,
    )

    assert desfecho.veredito == evidencia.ACEITO  # o juízo, sozinho, aprovaria
    assert desfecho.autorizado_publicar is False  # a orquestração não autoriza


def test_competencia_concordante_autoriza_publicar(tmp_path):
    caminho_contrato, executar = _montar_bate(tmp_path, competencia="2026-07")

    desfecho = conduzir(
        diretorio_evidencia=tmp_path / "evidencia",
        competencia_solicitada="2026-07",
        caminho_contrato=caminho_contrato,
        executar_leitura=executar,
    )

    assert desfecho.veredito == evidencia.ACEITO
    assert desfecho.autorizado_publicar is True


# ---------------------------------------------------------------------------
# eval_2 — excecao: exceção real vira ERRO, com pacote gravado
# ---------------------------------------------------------------------------


def test_excecao_real_na_leitura_vira_erro_com_pacote_gravado(tmp_path):
    caminho_contrato, _ = _montar_bate(tmp_path, competencia="2026-08")

    def _leitura_com_excecao(contrato):
        raise PermissionError("permissão negada ao abrir o csv")

    desfecho = conduzir(
        diretorio_evidencia=tmp_path / "evidencia",
        competencia_solicitada="2026-08",
        caminho_contrato=caminho_contrato,
        executar_leitura=_leitura_com_excecao,
    )

    assert desfecho.veredito == evidencia.ERRO
    assert desfecho.causa == "EXECUCAO_INTERROMPIDA"
    assert desfecho.caminho_pacote is not None
    assert desfecho.caminho_pacote.exists()
    assert desfecho.autorizado_publicar is False

    pacote = evidencia.ler_pacote(desfecho.caminho_pacote)
    assert pacote["evento_falha"]["tipo"] == "PermissionError"


def test_contrato_half_up_recusa_sem_chegar_a_leitura(tmp_path):
    # B-2: contrato com política HALF_UP — contradiz o ADR 0001 — termina
    # RECUSADO, com pacote gravado, e a leitura NUNCA é chamada (caminho
    # exercido aqui, não só declarado no contrato).
    dados = _contrato_valido(competencia="2026-09", hash_csv_sha256="c" * 64)
    dados["politica_decimal"]["modo"] = "HALF_UP"
    caminho_contrato = _escrever_yaml(tmp_path, dados)

    desfecho = conduzir(
        diretorio_evidencia=tmp_path / "evidencia",
        competencia_solicitada="2026-09",
        caminho_contrato=caminho_contrato,
        executar_leitura=lambda contrato: pytest.fail("HALF_UP nunca deve chegar à leitura"),
    )

    assert desfecho.veredito == evidencia.RECUSADO
    assert desfecho.causa == "CONTRATO_RECUSADO"
    assert desfecho.caminho_pacote is not None
    assert desfecho.autorizado_publicar is False

    pacote = evidencia.ler_pacote(desfecho.caminho_pacote)
    assert "HALF_EVEN" in pacote["clausula_adr_violada"]


def test_gravador_falha_devolve_erro_sem_pacote_e_escreve_na_saida_de_erro(tmp_path, capsys):
    caminho_contrato, executar = _montar_bate(tmp_path, competencia="2026-10")

    def _gravar_pacote_falha(*args, **kwargs):
        raise OSError("disco cheio")

    import pda.orquestracao as orquestracao_mod

    monkeypatch_alvo = orquestracao_mod.evidencia_mod
    original = monkeypatch_alvo.gravar_pacote
    monkeypatch_alvo.gravar_pacote = _gravar_pacote_falha
    try:
        desfecho = conduzir(
            diretorio_evidencia=tmp_path / "evidencia",
            competencia_solicitada="2026-10",
            caminho_contrato=caminho_contrato,
            executar_leitura=executar,
        )
    finally:
        monkeypatch_alvo.gravar_pacote = original

    assert desfecho.veredito == evidencia.ERRO
    assert desfecho.caminho_pacote is None
    assert desfecho.autorizado_publicar is False
    saida_erro = capsys.readouterr().err
    assert "disco cheio" in saida_erro


# ---------------------------------------------------------------------------
# eval_2 — tempo_total: medido do início da leitura ao veredito, nunca zero,
# nunca vira recusa
# ---------------------------------------------------------------------------


def test_tempo_total_e_medido_do_inicio_da_leitura_ao_veredito_e_gravado(tmp_path):
    atraso = 0.05
    caminho_contrato, executar = _montar_bate(tmp_path, competencia="2026-11", atraso=atraso)

    desfecho = conduzir(
        diretorio_evidencia=tmp_path / "evidencia",
        competencia_solicitada="2026-11",
        caminho_contrato=caminho_contrato,
        executar_leitura=executar,
    )

    # o atraso está DENTRO da leitura, não numa etapa isolada — se a duração
    # só somasse uma etapa "rápida" e ignorasse o resto, este limiar falharia
    assert desfecho.duracao_segundos >= atraso
    # nunca vira recusa por si só (R-9 é should)
    assert desfecho.veredito == evidencia.ACEITO

    pacote = evidencia.ler_pacote(desfecho.caminho_pacote)
    assert pacote["duracao_segundos"] >= atraso


def test_tempo_total_e_registrado_mesmo_quando_o_veredito_nao_e_aceito(tmp_path):
    atraso = 0.03
    caminho_contrato, executar = _montar_r7(tmp_path, competencia="2026-12")

    def _executar_com_atraso(contrato):
        time.sleep(atraso)
        return executar(contrato)

    desfecho = conduzir(
        diretorio_evidencia=tmp_path / "evidencia",
        competencia_solicitada="2026-12",
        caminho_contrato=caminho_contrato,
        executar_leitura=_executar_com_atraso,
    )

    assert desfecho.veredito == evidencia.RECUSADO
    assert desfecho.duracao_segundos >= atraso


# ---------------------------------------------------------------------------
# eval_3 — autoriza: só ACEITO autoriza publicar
# ---------------------------------------------------------------------------


def test_autoriza_apenas_no_veredito_aceito_com_competencia_concordante(tmp_path):
    diretorio = tmp_path / "evidencia"

    # ACEITO_SEM_ANCORA nunca autoriza
    dados_sem_ancora = _contrato_valido(competencia="2026-13", hash_csv_sha256="d" * 64)
    del dados_sem_ancora["ancora"]
    caminho_sem_ancora = _escrever_yaml(tmp_path, dados_sem_ancora, nome="sem-ancora.yaml")
    desfecho_sem_ancora = conduzir(
        diretorio_evidencia=diretorio,
        competencia_solicitada="2026-13",
        caminho_contrato=caminho_sem_ancora,
        executar_leitura=lambda contrato: pytest.fail("não deve chegar à leitura"),
    )
    assert desfecho_sem_ancora.veredito == evidencia.ACEITO_SEM_ANCORA
    assert desfecho_sem_ancora.autorizado_publicar is False

    # RECUSADO nunca autoriza
    (tmp_path / "r7").mkdir()
    caminho_r7, executar_r7 = _montar_r7(tmp_path / "r7", competencia="2026-14")
    desfecho_r7 = conduzir(
        diretorio_evidencia=diretorio,
        competencia_solicitada="2026-14",
        caminho_contrato=caminho_r7,
        executar_leitura=executar_r7,
    )
    assert desfecho_r7.veredito == evidencia.RECUSADO
    assert desfecho_r7.autorizado_publicar is False

    # ERRO nunca autoriza
    (tmp_path / "erro").mkdir()
    caminho_erro, _ = _montar_bate(tmp_path / "erro", competencia="2026-15")

    def _leitura_com_excecao(contrato):
        raise RuntimeError("falha real")

    desfecho_erro = conduzir(
        diretorio_evidencia=diretorio,
        competencia_solicitada="2026-15",
        caminho_contrato=caminho_erro,
        executar_leitura=_leitura_com_excecao,
    )
    assert desfecho_erro.veredito == evidencia.ERRO
    assert desfecho_erro.autorizado_publicar is False

    # ACEITO com competência concordante autoriza
    (tmp_path / "bate").mkdir()
    caminho_bate, executar_bate = _montar_bate(tmp_path / "bate", competencia="2026-16")
    desfecho_bate = conduzir(
        diretorio_evidencia=diretorio,
        competencia_solicitada="2026-16",
        caminho_contrato=caminho_bate,
        executar_leitura=executar_bate,
    )
    assert desfecho_bate.veredito == evidencia.ACEITO
    assert desfecho_bate.autorizado_publicar is True

    autorizacoes = {
        d.veredito: d.autorizado_publicar
        for d in (desfecho_sem_ancora, desfecho_r7, desfecho_erro, desfecho_bate)
    }
    assert sum(1 for autorizado in autorizacoes.values() if autorizado) == 1
    assert autorizacoes[evidencia.ACEITO] is True


def test_autoriza_recusa_quando_competencia_do_envelope_diverge_mesmo_contrato_batendo(tmp_path):
    caminho_contrato, executar = _montar_bate(
        tmp_path, competencia="2026-17", competencia_envelope="2026-18"
    )

    desfecho = conduzir(
        diretorio_evidencia=tmp_path / "evidencia",
        competencia_solicitada="2026-17",
        caminho_contrato=caminho_contrato,
        executar_leitura=executar,
    )

    assert desfecho.veredito == evidencia.ACEITO
    assert desfecho.autorizado_publicar is False
