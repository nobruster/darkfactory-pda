"""Manutenção: retenção de cinco anos e OPTIMIZE com prova.

Rodam DENTRO do contêiner pda-spark. Só gravam em `tmp_path`, nunca no MinIO,
e nenhuma função para a sessão Spark da suíte.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from medalhao import bronze, manutencao  # noqa: E402

LOG = "delta.logRetentionDuration"
ARQ = "delta.deletedFileRetentionDuration"
ALVO = "interval 1825 days"


@pytest.fixture(scope="module")
def spark():
    # a sessão é da suíte: getOrCreate reaproveita e ninguém a para
    return bronze.criar_sessao("teste-manutencao")


def _tabela(spark, tmp_path, nome="t", props=None, lotes=3) -> str:
    """Delta com `lotes` commits pequenos; as propriedades de retenção são as pedidas."""
    caminho = str(tmp_path / nome)
    for i in range(lotes):
        spark.createDataFrame([(i * 10 + j, f"v{i}{j}") for j in range(3)], "id INT, txt STRING").coalesce(
            1
        ).write.format("delta").mode("append").save(caminho)
    spark.sql(f"ALTER TABLE delta.`{caminho}` UNSET TBLPROPERTIES IF EXISTS ('{LOG}', '{ARQ}')")
    if props:
        lista = ", ".join(f"'{k}' = '{v}'" for k, v in props.items())
        spark.sql(f"ALTER TABLE delta.`{caminho}` SET TBLPROPERTIES ({lista})")
    return caminho


def _props(spark, caminho) -> dict:
    return manutencao._propriedades(spark, caminho)


def _versao(spark, caminho) -> int:
    return bronze._versao_atual(spark, caminho)


def test_retencao_aplicada_em_tabela_sem(spark, tmp_path):
    caminho = _tabela(spark, tmp_path)
    v = _versao(spark, caminho)
    r = manutencao.garantir_retencao(spark, caminho)
    assert r["resultado"] == "ALTERADA"
    assert r["anteriores"] == {LOG: None, ARQ: None}
    p = _props(spark, caminho)
    assert p[LOG] == ALVO and p[ARQ] == ALVO
    assert _versao(spark, caminho) == v + 1  # ÚNICA ALTER


def test_retencao_ja_presente_sem_commit(spark, tmp_path):
    caminho = _tabela(spark, tmp_path, props={LOG: ALVO, ARQ: ALVO})
    v = _versao(spark, caminho)
    r = manutencao.garantir_retencao(spark, caminho)
    assert r["resultado"] == "JA_TINHA"
    assert _versao(spark, caminho) == v


def test_retencao_divergente_corrigida_e_registrada(spark, tmp_path):
    caminho = _tabela(spark, tmp_path, props={LOG: "interval 30 days", ARQ: "interval 7 days"})
    r = manutencao.garantir_retencao(spark, caminho)
    assert r["resultado"] == "CORRIGIDA"
    assert r["anteriores"] == {LOG: "interval 30 days", ARQ: "interval 7 days"}
    p = _props(spark, caminho)
    assert p[LOG] == ALVO and p[ARQ] == ALVO


def test_retencao_parcial_completada(spark, tmp_path):
    caminho = _tabela(spark, tmp_path, props={LOG: ALVO})
    r = manutencao.garantir_retencao(spark, caminho)
    assert r["resultado"] == "ALTERADA"
    assert r["anteriores"] == {LOG: ALVO, ARQ: None}
    assert _props(spark, caminho)[ARQ] == ALVO


def test_retencao_maior_nunca_encurta(spark, tmp_path):
    caminho = _tabela(spark, tmp_path, props={LOG: "interval 3650 days", ARQ: "interval 1825 days"})
    v = _versao(spark, caminho)
    r = manutencao.garantir_retencao(spark, caminho)
    assert r["resultado"] == "JA_TINHA"
    assert _props(spark, caminho)[LOG] == "interval 3650 days"
    assert _versao(spark, caminho) == v


def test_retencao_ilegivel_nao_medido(spark, tmp_path):
    # o Delta aceita o intervalo em semanas; o módulo só lê 'interval N days'
    caminho = _tabela(spark, tmp_path, props={LOG: "interval 260 weeks"})
    v = _versao(spark, caminho)
    r = manutencao.garantir_retencao(spark, caminho)
    assert r["resultado"] == "NAO_MEDIDO"
    assert r["propriedade"] == LOG and LOG in r["motivo"]
    assert _props(spark, caminho).get(LOG) == "interval 260 weeks"
    assert _props(spark, caminho).get(ARQ) is None
    assert _versao(spark, caminho) == v


def test_optimize_nao_muda_o_dado(spark, tmp_path):
    caminho = _tabela(spark, tmp_path)
    antes = sorted(spark.read.format("delta").load(caminho).collect())
    r = manutencao.otimizar(spark, caminho)
    assert r["resultado"] == "OTIMIZADA"
    assert r["versao_depois"] == r["versao_antes"] + 1
    assert sorted(spark.read.format("delta").load(caminho).collect()) == antes


def test_optimize_sem_nada_a_compactar(spark, tmp_path):
    caminho = _tabela(spark, tmp_path, lotes=1)
    v = _versao(spark, caminho)
    r = manutencao.otimizar(spark, caminho)
    assert r["resultado"] == "SEM_MUDANCA"
    assert _versao(spark, caminho) == v


def test_optimize_acusa_dado_mudado(spark, tmp_path, monkeypatch):
    caminho = _tabela(spark, tmp_path)
    original = manutencao._ler_versao

    def lida(sp, cam, versao):
        df = original(sp, cam, versao)
        if versao != r_antes["v"]:
            return df.union(sp.createDataFrame([(999, "extra")], "id INT, txt STRING"))
        return df

    r_antes = {"v": _versao(spark, caminho)}
    monkeypatch.setattr(manutencao, "_ler_versao", lida)
    assert manutencao.otimizar(spark, caminho)["resultado"] == "DIVERGE"


def test_optimize_com_escrita_concorrente_nao_medido(spark, tmp_path, monkeypatch):
    caminho = _tabela(spark, tmp_path)
    original = manutencao._compactar

    def compactar_e_escrever(sp, cam):
        res = original(sp, cam)
        sp.createDataFrame([(500, "alheio")], "id INT, txt STRING").write.format("delta").mode("append").save(cam)
        return res

    monkeypatch.setattr(manutencao, "_compactar", compactar_e_escrever)
    r = manutencao.otimizar(spark, caminho)
    assert r["resultado"] == "NAO_MEDIDO"
    assert r["resultado"] != "DIVERGE"


def test_modulo_sem_vacuum():
    arvore = ast.parse((RAIZ / "src" / "medalhao" / "manutencao.py").read_text())
    for no in ast.walk(arvore):
        if isinstance(no, ast.Call):
            f = no.func
            nome = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            assert "vacuum" not in nome.lower()
            for arg in no.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    assert "vacuum" not in arg.value.lower()
        if isinstance(no, ast.JoinedStr):
            assert "vacuum" not in ast.unparse(no).lower()


def test_script_mede_por_padrao_e_lista_e_fechada(spark, tmp_path, monkeypatch, capsys):
    caminho_script = RAIZ / "scripts" / "manter_lago.py"
    arvore = ast.parse(caminho_script.read_text())
    atrib = [
        n for n in arvore.body if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "TABELAS" for t in n.targets)
    ]
    assert len(atrib) == 1
    lista = ast.literal_eval(atrib[0].value)  # literal: falha se for calculada
    assert len(lista) == 11 and len(set(lista)) == 11
    assert all(t.startswith("s3a://") for t in lista)

    espec = importlib.util.spec_from_file_location("manter_lago", caminho_script)
    mod = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(mod)
    caminho = _tabela(spark, tmp_path, props={LOG: "interval 30 days"})
    v = _versao(spark, caminho)
    monkeypatch.setattr(mod, "TABELAS", [caminho])
    monkeypatch.setattr(bronze, "criar_sessao", lambda *a, **k: spark)
    mod.main([])
    assert _versao(spark, caminho) == v
    assert "MEDIDO_CORRIGIDA" in capsys.readouterr().out
    mod.main(["--aplicar"])
    assert _props(spark, caminho)[LOG] == ALVO
