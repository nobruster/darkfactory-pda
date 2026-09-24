"""Testes de performance da Bronze e da Silver — a saída não muda, só o custo.

Rodam DENTRO do contêiner pda-spark. O tempo NÃO é medido aqui (instável dentro de
eval): o PERF=MELHOR contra perf/ é verificação pós-assentamento, com a skill spark-perf.
Aqui se prova o comportamento declarado: memória declarada e conferida, cache liberado
em todo caminho, e a reconferência numa passada acusando exatamente o que as duas acusavam.
"""

from __future__ import annotations

import inspect
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pyspark.sql import functions as F  # noqa: E402
from pyspark.sql.types import DecimalType  # noqa: E402

from medalhao import bronze, silver  # noqa: E402
from test_bronze import (  # noqa: E402
    COMP,
    ESQUEMA,
    _contrato,
    _lago,
    _ler_e_gravar,
    _politica,
)

LINHAS = [("01", "A", Decimal(v)) for v in ("10.00", "20.00", "30.00", "40.00")]


@pytest.fixture(scope="module")
def spark():
    sessao = bronze.criar_sessao("teste-performance")
    yield sessao
    sessao.conf.set("spark.sql.adaptive.enabled", "true")
    sessao.conf.set("spark.sql.shuffle.partitions", "4")


def _df(spark, linhas):
    return spark.createDataFrame(linhas, ESQUEMA).withColumn("competencia", F.lit(COMP))


def _publicar(spark, tmp_path, lido_linhas):
    caminho = str(tmp_path / "tab")
    pol = _politica()
    bronze._garantir_tabela(spark, caminho, pol)
    bronze.publicar_competencia(spark, _df(spark, lido_linhas), caminho, COMP, {"competencia": COMP})
    return caminho, pol


def _conferir(spark, tmp_path, esperado_linhas, lido_linhas):
    caminho, pol = _publicar(spark, tmp_path, lido_linhas)
    esperado = _df(spark, esperado_linhas)
    controles, _ = bronze.medir_controles(esperado, pol)
    return bronze._conferir_tabela(
        spark, caminho, bronze._versao_atual(spark, caminho), esperado, controles, COMP, pol
    )


def _duas_passadas(esperado, lido):
    cols = list(bronze.COLUNAS)
    e, l = esperado.select(*cols), lido.select(*cols)
    return e.exceptAll(l).count(), l.exceptAll(e).count()


# ---------------------------------------------------------------- eval_1


def test_sessao_declara_memoria_e_shuffle(spark):
    padroes = inspect.signature(bronze.criar_sessao).parameters
    for nome in ("memoria_driver", "adaptativo", "particoes_shuffle"):
        assert padroes[nome].default is not inspect.Parameter.empty  # padrão explícito, nunca herdado

    s = bronze.criar_sessao("teste-performance", adaptativo=False, particoes_shuffle=5)
    assert s.conf.get("spark.sql.adaptive.enabled") == "false"
    assert s.conf.get("spark.sql.shuffle.partitions") == "5"
    assert s.sparkContext.getConf().get("spark.driver.memory") is not None
    assert silver.criar_sessao is bronze.criar_sessao


def test_sessao_com_memoria_herdada_recusada(spark):
    with pytest.raises(bronze.SessaoRecusada):
        bronze.criar_sessao("teste-performance", memoria_driver="4096g")


def test_heap_efetivo_conferido_pela_jvm(spark):
    maximo = spark._jvm.java.lang.Runtime.getRuntime().maxMemory()
    assert bronze.heap_efetivo(spark) == maximo
    assert bronze._bytes_de("2g") == 2 * 1024**3
    assert bronze._bytes_de("512m") == 512 * 1024**2
    corpo = inspect.getsource(bronze.criar_sessao)
    assert "heap_efetivo" in corpo and "PYSPARK_SUBMIT_ARGS" not in corpo


def test_unpersist_depois_de_publicar(spark, tmp_path, monkeypatch):
    eventos = []
    conferir, liberar = bronze._conferir_tabela, bronze._liberar

    def conferindo(*a, **kw):
        eventos.append("conferiu")
        return conferir(*a, **kw)

    def liberando(*dfs):
        eventos.append("liberou")
        return liberar(*dfs)

    monkeypatch.setattr(bronze, "_conferir_tabela", conferindo)
    monkeypatch.setattr(bronze, "_liberar", liberando)
    raiz = _lago(spark, tmp_path)
    r = _ler_e_gravar(spark, tmp_path, _contrato(), COMP, raiz, "exec-perf-ok")
    assert r.estado == bronze.INTEGRO and r.gravacao
    assert eventos == ["conferiu", "conferiu", "liberou"]  # nunca antes da reconferência
    assert r.cache is not None and not r.cache.is_cached


def _capturando_medir(monkeypatch):
    medidos, original = [], bronze._medir

    def capturando(*a, **kw):
        medidos.append(original(*a, **kw))
        return medidos[-1]

    monkeypatch.setattr(bronze, "_medir", capturando)
    return medidos


def test_unpersist_tambem_na_falha(spark, tmp_path, monkeypatch):
    medidos = _capturando_medir(monkeypatch)

    def explode(*a, **kw):
        raise OSError("falha de escrita")

    monkeypatch.setattr(bronze, "publicar_competencia", explode)
    raiz = _lago(spark, tmp_path)
    with pytest.raises(OSError):
        _ler_e_gravar(spark, tmp_path, _contrato(), COMP, raiz, "exec-perf-falha")
    assert medidos[0].cache is not None and not medidos[0].cache.is_cached


def test_unpersist_tambem_no_check_que_recusou(spark, tmp_path, monkeypatch):
    medidos = _capturando_medir(monkeypatch)
    original = bronze._gravar_preparo

    def adulterado(spark_, linhas, preparo, competencia, metadados):
        mexido = linhas.withColumn(
            "vl_liquido", (F.col("vl_liquido") + F.lit(Decimal("0.01"))).cast(DecimalType(14, 2))
        )
        original(spark_, mexido, preparo, competencia, metadados)

    monkeypatch.setattr(bronze, "_gravar_preparo", adulterado)
    raiz = _lago(spark, tmp_path)
    r = _ler_e_gravar(spark, tmp_path, _contrato(), COMP, raiz, "exec-perf-check")
    assert r.estado == bronze.DIVERGE
    assert not (tmp_path / "dest").exists()  # nada foi publicado
    assert medidos[0].cache is not None and not medidos[0].cache.is_cached


# ---------------------------------------------------------------- eval_2


def test_uma_passada_igual_a_duas(spark):
    casos = [
        (LINHAS, LINHAS),
        (LINHAS, LINHAS[:3]),
        (LINHAS[:3], LINHAS),
        (LINHAS, LINHAS[:3] + [("01", "A", Decimal("41.00"))]),
        (LINHAS, LINHAS + LINHAS[:1]),  # duplicata: multiconjunto, não conjunto
        (LINHAS, [("01", "A", Decimal("10.00"))] * 4),
    ]
    for esperado_linhas, lido_linhas in casos:
        e, l = _df(spark, esperado_linhas), _df(spark, lido_linhas)
        assert bronze._diferenca_numa_passada(e.select(*bronze.COLUNAS), l.select(*bronze.COLUNAS)) == _duas_passadas(
            e, l
        )


def test_linha_trocada_diverge(spark, tmp_path):
    lido = [LINHAS[0], ("01", "A", Decimal("21.00")), ("01", "A", Decimal("29.00")), LINHAS[3]]
    ok, detalhe = _conferir(spark, tmp_path, LINHAS, lido)
    assert detalhe["controles_divergentes"] == ()  # 20/30 por 21/29 preserva os cinco
    assert (detalhe["so_no_esperado"], detalhe["so_no_lido"]) == (2, 2)
    assert ok is False


def test_centavo_a_mais_diverge(spark, tmp_path):
    lido = LINHAS[:3] + [("01", "A", Decimal("40.01"))]
    ok, detalhe = _conferir(spark, tmp_path, LINHAS, lido)
    assert (detalhe["so_no_esperado"], detalhe["so_no_lido"]) == (1, 1)
    assert "sum_vl_liquido" in detalhe["controles_divergentes"]
    assert ok is False


def test_linha_a_menos_diverge(spark, tmp_path):
    ok, detalhe = _conferir(spark, tmp_path, LINHAS, LINHAS[:3])
    assert (detalhe["so_no_esperado"], detalhe["so_no_lido"]) == (1, 0)
    assert ok is False


def test_linha_a_mais_diverge(spark, tmp_path):
    ok, detalhe = _conferir(spark, tmp_path, LINHAS[:3], LINHAS)
    assert (detalhe["so_no_esperado"], detalhe["so_no_lido"]) == (0, 1)
    assert ok is False


def test_silver_reconfere_numa_passada(spark):
    fonte = inspect.getsource(silver._conferir_tabela)
    assert "_diferenca_numa_passada" in fonte and fonte.count("exceptAll") == 0


# ---------------------------------------------------------------- memória do driver (JVM nova)

_SRC = str(Path(__file__).resolve().parent.parent / "src")


def _em_jvm_nova(codigo, submit_args=None):
    """Roda `codigo` num processo filho: só numa JVM ainda não iniciada o builder muda o heap."""
    import os
    import subprocess

    env = dict(os.environ)
    env.pop("PYSPARK_SUBMIT_ARGS", None)
    if submit_args:
        env["PYSPARK_SUBMIT_ARGS"] = submit_args
    prelude = f"import sys; sys.path.insert(0, {_SRC!r})\nfrom medalhao import bronze\n"
    return subprocess.run(
        [sys.executable, "-c", prelude + codigo], capture_output=True, text=True, env=env, timeout=300
    )


def _heap_impresso(saida):
    return int(next(l for l in saida.splitlines() if l.startswith("HEAP=")).split("=")[1])


def test_memoria_padrao_e_seis_gigas():
    assert bronze.MEMORIA_DRIVER_PADRAO == "6g"
    assert inspect.signature(bronze.criar_sessao).parameters["memoria_driver"].default == "6g"
    r = _em_jvm_nova(
        "s = bronze.criar_sessao('filho')\n"
        "print('DRIVER=' + s.sparkContext.getConf().get('spark.driver.memory'))\n"
    )
    assert r.returncode == 0, r.stderr[-2000:]
    assert "DRIVER=6g" in r.stdout


def test_heap_efetivo_do_padrao():
    r = _em_jvm_nova(
        "s = bronze.criar_sessao('filho')\n"
        "print('HEAP=%d' % bronze.heap_efetivo(s))\n"
    )
    assert r.returncode == 0, r.stderr[-2000:]
    assert _heap_impresso(r.stdout) >= bronze.FOLGA_DO_HEAP * bronze._bytes_de("6g")


def test_heap_menor_que_declarado_recusado():
    r = _em_jvm_nova(
        "try:\n"
        "    bronze.criar_sessao('filho')\n"
        "    print('SEM_RECUSA')\n"
        "except bronze.SessaoRecusada as e:\n"
        "    print('RECUSADA=' + str(e))\n",
        submit_args="--driver-memory 2g pyspark-shell",
    )
    assert r.returncode == 0, r.stderr[-2000:]
    saida = next((l for l in r.stdout.splitlines() if l.startswith(("RECUSADA=", "SEM_RECUSA"))), "")
    assert saida.startswith("RECUSADA="), r.stdout[-2000:]
    assert "declarado" in saida and "efetivo" in saida


def test_pedido_explicito_prevalece():
    r = _em_jvm_nova(
        "s = bronze.criar_sessao('filho', memoria_driver='2g')\n"
        "print('DRIVER=' + s.sparkContext.getConf().get('spark.driver.memory'))\n"
        "print('HEAP=%d' % bronze.heap_efetivo(s))\n"
    )
    assert r.returncode == 0, r.stderr[-2000:]
    assert "DRIVER=2g" in r.stdout
    heap = _heap_impresso(r.stdout)
    assert heap >= bronze.FOLGA_DO_HEAP * bronze._bytes_de("2g")
    assert heap < bronze.FOLGA_DO_HEAP * bronze._bytes_de("6g")
