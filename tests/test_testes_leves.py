"""Cenário de teste montado uma vez por módulo — e a prova de que nenhum teste mudou por isso.

Rodam DENTRO do contêiner pda-spark. Só os auxiliares e as fixtures de `test_gold.py` e
`test_gold_assuntos.py` mudaram; o corpo de cada função `test_*` é o do commit anterior
(9f12b3b, gravado em `ANTES`), comparado pela AST — não por texto, para que reformatar não passe por mudança
e mudar uma asserção não passe despercebido.
"""

from __future__ import annotations

import ast
import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_gold as tg  # noqa: E402
from test_gold import cadeias_por_modulo, spark  # noqa: E402,F401  (a mesma sessão de teste)
from medalhao import gold, silver  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
MODULOS = ("tests/test_gold.py", "tests/test_gold_assuntos.py")

# Cada função test_* do commit anterior (9f12b3b): impressão da AST (16 hex de sha256 do ast.dump) e
# quantos ids o pytest coleta dela. O contêiner só monta tests/, sem git — por isso o baseline é gravado aqui.
# commit_carrega_a_forma: nome_oficial na tupla — DEC-NOME-OFICIAL-NA-GOLD, 2026-09-25
_ANTES_GOLD = """
arredonda_uma_vez 175fa76a6c75d003 1|half_even_do_contrato 0509cc919af81456 1|nao_arredonda_por_campo 579ff04e0b7c4742 1
traps_declaradas 6d1aa9405c484787 1|recusa_sob_procedencia_nao_vinculada 88b29099becd1c73 1
ansi_declarado_estouro_nao_vira_nulo 949b6d1b7658ce29 1|cobertura_anexada_ao_pacote e467a2649c27e8b7 1
publica_em_um_unico_commit ccd95826a776d652 1|interrompida_antes_do_commit_nao_publica 831d60e8a9071347 1
reconfere_multiconjunto_das_linhas 572ef3a39028b25c 1|commit_carrega_a_forma 942ea6bcdf6c9ad3 1
resolve_versao_uma_vez 4b5bf7fc71566819 1|schema_evolucao_so_aditiva 48a4c90b8fc56033 1|check_nao_negativo 292575a6142be9d2 1
reconfere_no_preparo_antes_de_publicar 5786ec891eb775d1 1|reverte_so_a_competencia a11da0e2791acffd 1
metadados_do_commit_dono_da_competencia 17fe424fc7bbc2c8 1|reconcilia_recalculando 1ec8edf359913b0e 1
mapa_por_codigo 104902f8b66cc8ab 1|redistribuicao_compensada a6be7ce2bca6acf5 1|contagem_de_codigos 145a284bf6690e1f 1
competencia_bate_com_o_contrato ea19d51eeb1269ba 1|uma_linha_por_codigo b4d6a1db5421b53e 1
recusa_silver_nao_integro b3cc5f26f291c1d4 4|consome_saida_real_de_silver 932730898fe1b334 1
publica_so_com_autorizado_publicar e4ce3b1e16ea796a 1|descricao_publicada_bate_com_a_original 21a0e98ab676c3b7 1
publica_so_com_pacote_em_disco 67b74066dbab31ef 1|envelope_so_defeitos_de_linha 8c3ab0fc4d71740d 1
envelope_validado_antes_dos_insumos c18b57e949282931 1|envelope_positivo_sem_defeitos_de_linha 27b831940a0a338e 1
diverge_nao_publica adab8fd84d921c53 1|sem_ancora_gold_nao_invocado 7c1bcaef819c19ab 1
destino_inalterado_durante 02b2cb64b033f41c 1|classifica_diferenca_das_seis 75ec5fa8558bbda3 1
orcamento_leitura_ao_veredito_medido 00783c2f358ded15 1|parada_antecipada_grava_evidencia 847c29469d574977 1
diagnostico_estruturado_no_pacote 590a40b332e01637 1|marca_de_procedencia_vira_evidencia 693ef375e2ef79c9 1
gold_le_so_a_silver 5a8829f8bbb8e937 1|nao_abre_landing_nem_csv 3fe536eb44256150 1
linhagem_ate_pacote_aceito 38017568cba4c069 1|sha256_do_pacote_conferido e9fc41df17e37b95 1
gold_da_silver_fecha_com_a_ancora 7e2bb0137194ebaa 1|commit_nomeia_silver_e_pacote 3fae53702ec9f1b0 1
sem_pacote_aceito_nao_medido 82058cdf47c2a9b4 1|silver_nao_integra_nao_publica 9e6f95a12a05a4af 1
gold_soma_que_nao_fecha_diverge 16b1eab78b5a5ffa 1
"""
_ANTES_ASSUNTOS = """
fat_especie_fecha_com_a_ancora 98d8c2bff7133dc5 1|kpis_somam_fat_especie 119ed0fe2ed6d5c9 1
medio_arredonda_meio_para_par 3f879f144a4ddc18 1|percentis_rotulados_aprox e1822710d9d0d156 1
le_silver_por_versao 8ac7e3c1bdcad84d 1|usa_a_silver_nomeada_pela_gold df569590531d0f44 1
extremos_conferem_com_a_ancora e0479a492973f18b 1|medio_nacional_nao_e_media_das_medias 96e860d69800e7f0 1
publica_com_replacewhere a255bb393c73dc7e 1|check_nao_negativo_monetario 9d034411f1eb19e4 1
commit_nomeia_versoes_lidas c51eb15c42d1995c 1|sem_gold_principal_nao_medido c560d45767f95758 1
sem_grupos_nao_medido bb17cdcde05a5b3c 1|codigo_fora_do_mapa_diverge 988ebd3b11680abf 1
soma_que_nao_fecha_diverge d943d6dcc1817f53 1
"""


def _ler_antes(arquivo, bloco):
    saida = {}
    for item in bloco.replace("\n", "|").split("|"):
        if item.strip():
            nome, impressao, quantos = item.split()
            saida[f"{arquivo}::test_{nome}"] = (impressao, int(quantos))
    return saida


ANTES = {**_ler_antes("test_gold.py", _ANTES_GOLD), **_ler_antes("test_gold_assuntos.py", _ANTES_ASSUNTOS)}


# ---------------------------------------------------------------- apoio


def _funcoes_test(fonte):
    return {n.name: n for n in ast.parse(fonte).body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}


def _impressao_da_funcao(no):
    return hashlib.sha256(ast.dump(no).encode()).hexdigest()


def _quantos_ids(no):
    """Quantos ids o pytest coleta desta função: o tamanho da lista do `parametrize`, ou 1."""
    total = 1
    for dec in no.decorator_list:
        if isinstance(dec, ast.Call) and getattr(dec.func, "attr", "") == "parametrize":
            lista = dec.args[1]
            assert isinstance(lista, (ast.List, ast.Tuple)), "parametrize que não é lista literal"
            total *= len(lista.elts)
    return total


def _ids_coletados(modulo):
    coletados = []

    class Coletor:
        def pytest_collection_modifyitems(self, items):
            coletados.extend(i.nodeid for i in items)

    codigo = pytest.main(["--collect-only", "-q", "-p", "no:cacheprovider", str(RAIZ / modulo)], plugins=[Coletor()])
    assert codigo == 0, f"a coleta de {modulo} falhou (código {codigo})"
    return coletados


def _impressao_da_arvore(raiz, *, sem_cenario=False):
    raiz = Path(raiz)
    return {
        str(p.relative_to(raiz)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(raiz.rglob("*"))
        if p.is_file() and not (sem_cenario and p.relative_to(raiz).parts[0].startswith("c-"))
    }


# ---------------------------------------------------------------- eval_2


def test_mesmos_ids_coletados():
    for modulo in MODULOS:
        arquivo = Path(modulo).name
        esperado = {k.split("::", 1)[1]: n for k, (_, n) in ANTES.items() if k.startswith(arquivo + "::")}
        obtido = {}
        for nodeid in _ids_coletados(modulo):
            nome = nodeid.split("::", 1)[1].split("[", 1)[0]
            obtido[nome] = obtido.get(nome, 0) + 1
        assert obtido == esperado, modulo


def test_corpo_das_funcoes_test_intacto():
    for modulo in MODULOS:
        arquivo = Path(modulo).name
        antes = {k.split("::", 1)[1]: h for k, (h, _) in ANTES.items() if k.startswith(arquivo + "::")}
        agora = _funcoes_test((RAIZ / modulo).read_text(encoding="utf-8"))
        assert set(agora) == set(antes), (modulo, set(agora) ^ set(antes))
        mudaram = [n for n in antes if _impressao_da_funcao(agora[n])[:16] != antes[n]]
        assert not mudaram, (modulo, mudaram)


def test_nenhum_skip_ou_xfail():
    for modulo in MODULOS:
        for no in ast.walk(ast.parse((RAIZ / modulo).read_text(encoding="utf-8"))):
            if isinstance(no, ast.Attribute) and no.attr in {"skip", "skipif", "xfail", "importorskip"}:
                pytest.fail(f"{modulo}:{no.lineno} usa {no.attr}")


def test_copia_isolada_do_cenario_base(spark, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    cen_a = tg._cenario(spark, a)
    d_a, s_a, _ = tg._cadeia_publicada(spark, a, cen_a)
    cen_b = tg._cenario(spark, b)
    d_b, s_b, _ = tg._cadeia_publicada(spark, b, cen_b)
    assert s_a.estado == s_b.estado == silver.INTEGRO
    assert d_a["silver"] != d_b["silver"]

    bases = {chave: _impressao_da_arvore(v[0]) for chave, v in tg._CADEIAS.items()}
    copia_b = _impressao_da_arvore(b, sem_cenario=True)

    g = tg._gold_da_silver(spark, cen_a, d_a)  # republica numa cópia
    assert g.estado == gold.INTEGRO
    assert Path(d_a["gold"]).exists()

    assert {chave: _impressao_da_arvore(v[0]) for chave, v in tg._CADEIAS.items()} == bases
    assert not Path(d_b["gold"]).exists()
    assert _impressao_da_arvore(b, sem_cenario=True) == copia_b
