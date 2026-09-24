"""Adoção do produtor Spark e do gravador do lago — descreve o que JÁ existe.

O landing de 2026-01 foi gravado por este código e fecha com a âncora. Aqui não
se corrige nada (Regra 4): o comportamento atual fica FIXADO, e onde ele difere
do juiz Python o achado é registrado para decisão do dono:

* DIVERGÊNCIA 1 — '1,5' (uma casa decimal): o produtor conta em
  `linhas_invalidas`; o juiz Python o aceita.
* DIVERGÊNCIA 2 — '-5,00' (negativo): o produtor aceita e soma; o juiz Python
  o recusa (o contrato declara `nao_negativo`).
* DEFEITO — código de espécie vazio: o valor entra nos cinco controles, mas
  fica fora de `total_por_codigo`.
* DEFEITO LATENTE — `gravar_lago` grava com append sem conferir se a partição
  já existe: uma segunda carga da mesma competência duplica e o gate acusa
  DIVERGE, mas os arquivos da primeira ficam.

`produzir` e `main` chamam `spark.stop()` e derrubariam a JVM compartilhada da
suíte: rodam SÓ em processo filho, sem as variáveis S3_*, com toda saída em
tmp_path. Nenhum cenário toca o MinIO.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / "src"
CONTRATO = RAIZ / "contracts" / "competencia-202601.yaml"
COMPETENCIA = "2026-01"
DESTINO_DE_HOJE = "s3a://landing/pda/beneficios-emitidos"
TIMEOUT = 300

sys.path.insert(0, str(SRC))

from pyspark.sql import SparkSession  # noqa: E402

from pda import contrato as cm  # noqa: E402
from produtor import gravar_lago as gl  # noqa: E402

CONTROLES = (
    "count_linhas",
    "linhas_invalidas",
    "sum_vl_liquido",
    "min_vl_liquido",
    "max_vl_liquido",
)

DESC_PENSAO = "Pensão por Morte de "
DESC_APOSENT = "Aposentadoria Invali"

# (código, descrição, valor como aparece no CSV, valor esperado ou None)
LINHAS = [
    ("01", DESC_PENSAO, "        1.518,00", "1518.00"),
    ("03", DESC_PENSAO, "    2.000,50", "2000.50"),
    ("01", DESC_PENSAO, "0,00", "0.00"),
    ("02", DESC_APOSENT, "10,25", "10.25"),
    ("02", DESC_APOSENT, "  1.234.567,89", "1234567.89"),
    ("04", "Auxilio Doenca", "0,00", "0.00"),
    ("04", "Auxilio Doenca", "1,5", None),      # fora da gramática
    ("05", "Amparo", "-5,00", "-5.00"),         # negativo: aceito hoje
    ("05", "Amparo", "abc", None),              # fora da gramática
    ("", "Sem codigo", "7,00", "7.00"),         # código vazio
]

# Calculados À MÃO a partir de LINHAS — nunca pelo código sob teste.
#   válidos: 1518,00 + 2000,50 + 0,00 + 10,25 + 1234567,89 + 0,00 - 5,00 + 7,00
ESPERADO = {
    "count_linhas": Decimal("10"),
    "linhas_invalidas": Decimal("2"),
    "sum_vl_liquido": Decimal("1238098.64"),
    "min_vl_liquido": Decimal("-5.00"),
    "max_vl_liquido": Decimal("1234567.89"),
}
ESPERADO_POR_CODIGO = {
    "01": Decimal("1518.00"),
    "03": Decimal("2000.50"),
    "02": Decimal("1234578.14"),
    "04": Decimal("0.00"),
    "05": Decimal("-5.00"),
}

CABECALHO = [
    "Competencia", "UF", "Municipio", "Grupo", "Sexo", "Idade", "Clientela",
    "Forma", "Situacao", "VlLiquido", "DtInicio", "Banco", "Espécie", "Espécie",
]


def _linha(codigo: str, descricao: str, valor: str) -> str:
    campos = ["202601", "SP", "Sao Paulo", "G", "M", "65", "U", "1", "A",
              valor, "20260101", "001", codigo, descricao]
    assert len(campos) == 14
    return ";".join(campos)


def _escrever_csv(destino: Path, linhas=LINHAS) -> Path:
    texto = "\n".join([";".join(CABECALHO)] + [_linha(c, d, v) for c, d, v, _ in linhas])
    destino.write_bytes((texto + "\n").encode("latin-1"))
    return destino


def _env_filho() -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("S3_")}
    env["PYSPARK_SUBMIT_ARGS"] = (
        "--master local[1] --conf spark.ui.enabled=false "
        "--conf spark.sql.shuffle.partitions=1 pyspark-shell"
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _filho(codigo: str, args: list, cwd: Path, env: dict | None = None):
    return subprocess.run(
        [sys.executable, "-c", codigo, *[str(a) for a in args]],
        cwd=cwd, env=env or _env_filho(), capture_output=True, text=True,
        timeout=TIMEOUT,
    )


_FILHO_PRODUZIR = r"""
import json, sys
from pathlib import Path
src, contrato, csv, competencia, saida = sys.argv[1:6]
sys.path.insert(0, src)
from pda import contrato as cm
from produtor import spark_produtor as sp
env = sp.produzir(Path(csv), cm.carregar_contrato(contrato), competencia)
Path(saida).write_text(json.dumps(env), encoding="utf-8")
"""

_FILHO_MAIN = r"""
import json, sys
from decimal import Decimal
src, substituicao, *resto = sys.argv[1:]
sys.path.insert(0, src)
from pyspark.sql import SparkSession
from pyspark.sql.types import DecimalType, StringType, StructField, StructType
from produtor import gravar_lago as gl

class _Leitor:
    def __init__(self, real, df):
        self._real, self._df = real, df
    def parquet(self, *a, **k):
        return self._df
    def __getattr__(self, nome):
        return getattr(self._real, nome)

class _Sessao:
    def __init__(self, real, df):
        self._real = real
        self.read = _Leitor(real.read, df)
    def __getattr__(self, nome):
        return getattr(self._real, nome)

def _sessao(nome):
    real = SparkSession.builder.appName(nome).getOrCreate()
    real.sparkContext.setLogLevel("WARN")
    if substituicao == "-":
        return real
    esquema = StructType([
        StructField("especie_codigo", StringType(), True),
        StructField("especie_descricao", StringType(), True),
        StructField("vl_liquido", DecimalType(14, 2), True),
    ])
    linhas = json.load(open(substituicao))
    df = real.createDataFrame(
        [(c, d, None if v is None else Decimal(v)) for c, d, v in linhas], esquema)
    return _Sessao(real, df)

gl._sessao = _sessao
sys.argv = ["gravar_lago"] + resto
raise SystemExit(gl.main())
"""

_FILHO_DEFAULTS = r"""
import argparse, json, sys
sys.path.insert(0, sys.argv[1])
from produtor import gravar_lago as gl

def _captura(self, *a, **k):
    print(json.dumps({x.dest: x.default for x in self._actions}))
    raise SystemExit(0)

argparse.ArgumentParser.parse_args = _captura
gl.main()
"""

_FILHO_SEM_S3 = r"""
import json, os, sys
sys.path.insert(0, sys.argv[1])
from produtor import gravar_lago as gl
from produtor import spark_produtor as sp
achados = {"s3_no_ambiente": sorted(k for k in os.environ if k.startswith("S3_"))}
try:
    gl._sessao("sem-credencial")
    achados["gravador"] = "SESSAO_CRIADA"
except KeyError as erro:
    achados["gravador"] = "KeyError:" + str(erro.args[0])
spark = sp._sessao("sem-credencial")
achados["endpoint_s3a"] = spark.conf.get("spark.hadoop.fs.s3a.endpoint", "AUSENTE")
print(json.dumps(achados))
"""


@pytest.fixture(scope="module")
def spark():
    # Sessão compartilhada da suíte: NUNCA parada aqui.
    return (
        SparkSession.builder.master("local[1]").appName("teste-produtor")
        .config("spark.ui.enabled", "false").getOrCreate()
    )


@pytest.fixture(scope="module")
def csv_fixture(tmp_path_factory) -> Path:
    return _escrever_csv(tmp_path_factory.mktemp("fonte") / "fixture.csv")


@pytest.fixture(scope="module")
def envelope(csv_fixture, tmp_path_factory) -> dict:
    pasta = tmp_path_factory.mktemp("produtor")
    saida = pasta / "envelope.json"
    r = _filho(_FILHO_PRODUZIR, [SRC, CONTRATO, csv_fixture, COMPETENCIA, saida], pasta)
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(saida.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def contratos(tmp_path_factory) -> dict:
    pasta = tmp_path_factory.mktemp("contratos")
    bruto = yaml.safe_load(CONTRATO.read_text(encoding="utf-8"))
    bruto["ancora"].update(
        count_linhas=10, sum_vl_liquido="1238098.64", min_vl_liquido="-5.00",
        max_vl_liquido="1234567.89", linhas_invalidas=2,
    )
    ancorado = pasta / "ancorado.yaml"
    ancorado.write_text(yaml.safe_dump(bruto, allow_unicode=True, sort_keys=False),
                        encoding="utf-8")
    del bruto["ancora"]
    nao_medido = pasta / "nao-medido.yaml"
    nao_medido.write_text(yaml.safe_dump(bruto, allow_unicode=True, sort_keys=False),
                          encoding="utf-8")
    assert cm.carregar_contrato(nao_medido) == cm.NAO_MEDIDO
    return {"ancorado": ancorado, "nao_medido": nao_medido}


def _rodar_main(pasta: Path, csv: Path, contrato: Path, destino: Path, out: Path,
                substituicao: Path | None = None):
    return _filho(
        _FILHO_MAIN,
        [SRC, substituicao or "-", csv, "--contrato", contrato,
         "--competencia", COMPETENCIA, "--destino", destino, "--out", out],
        pasta,
    )


def _dec(x) -> Decimal:
    return Decimal(str(x))


# ---------------------------------------------------------------- B-1: produtor


def test_produtor_totais_literais_da_fixture(envelope):
    controles = envelope["controles"]
    for nome in CONTROLES:
        assert _dec(controles[nome]) == ESPERADO[nome], nome


def test_codigos_com_mesma_descricao_somam_separados(envelope):
    total = envelope["total_por_codigo"]
    assert _dec(total["01"]) == Decimal("1518.00")
    assert _dec(total["03"]) == Decimal("2000.50")
    # nunca pela descrição, que é a mesma para os dois (R-3, ADR 0008)
    assert DESC_PENSAO not in total
    assert {k: _dec(v) for k, v in total.items()} == ESPERADO_POR_CODIGO


def test_gramatica_atual_fixada(envelope):
    controles = envelope["controles"]
    total = envelope["total_por_codigo"]
    # '1,5' e 'abc' são inválidas — e nunca viram zero
    assert controles["linhas_invalidas"] == 2
    assert _dec(total["04"]) == Decimal("0.00")   # só o 0,00 válido; o '1,5' fora
    # '-5,00' é ACEITO e somado (o juiz Python o recusaria: divergência registrada)
    assert _dec(controles["min_vl_liquido"]) == Decimal("-5.00")
    assert _dec(total["05"]) == Decimal("-5.00")


def test_codigo_vazio_fora_do_total_fixado(envelope):
    assert "" not in envelope["total_por_codigo"]
    assert None not in envelope["total_por_codigo"]
    # o 7,00 do código vazio ESTÁ nos controles, mas em nenhum código
    assert _dec(envelope["controles"]["sum_vl_liquido"]) - sum(
        _dec(v) for v in envelope["total_por_codigo"].values()) == Decimal("7.00")


def test_sha256_e_motor_no_envelope(envelope, csv_fixture):
    assert envelope["motor"] == "spark"
    assert envelope["sha256_arquivo_lido"] == hashlib.sha256(
        csv_fixture.read_bytes()).hexdigest()
    assert envelope["competencia"] == COMPETENCIA
    assert envelope["defeitos"] == []


def _sem_float(no):
    if isinstance(no, float):
        raise AssertionError(f"float no envelope: {no!r}")
    if isinstance(no, dict):
        for v in no.values():
            _sem_float(v)
    elif isinstance(no, list):
        for v in no:
            _sem_float(v)


def test_envelope_sem_float(envelope, tmp_path):
    _sem_float(envelope)
    texto = json.dumps(envelope)

    def recusa(valor):
        raise AssertionError(f"número JSON com ponto no envelope: {valor}")

    json.loads(texto, parse_float=recusa)


# ---------------------------------------------------------------- B-2: gravador


def test_gravador_mede_igual_ao_produtor(spark, csv_fixture, envelope):
    carregado = cm.carregar_contrato(CONTRATO)
    medido = gl._controles(gl._ler_fonte(spark, csv_fixture, carregado))
    for nome in CONTROLES:
        assert _dec(medido[nome]) == ESPERADO[nome], nome
        assert _dec(medido[nome]) == _dec(envelope["controles"][nome]), nome


def test_contrato_nao_medido_recusa(tmp_path, csv_fixture, contratos):
    destino = tmp_path / "lago"
    r = _rodar_main(tmp_path, csv_fixture, contratos["nao_medido"], destino,
                    tmp_path / "prova.json")
    assert "LAGO=RECUSADO" in r.stdout, r.stderr[-2000:]
    assert r.returncode == 1
    assert not destino.exists()


def test_zero_linhas_nao_grava(tmp_path, contratos):
    vazio = _escrever_csv(tmp_path / "vazio.csv", linhas=[])
    destino = tmp_path / "lago"
    r = _rodar_main(tmp_path, vazio, contratos["ancorado"], destino,
                    tmp_path / "prova.json")
    assert "LAGO=RECUSADO" in r.stdout, r.stderr[-2000:]
    assert r.returncode == 1
    assert not destino.exists()


def _arquivos(raiz: Path) -> set:
    return {str(p.relative_to(raiz)) for p in raiz.rglob("*") if p.is_file()}


def test_primeira_grava_segunda_diverge_sem_apagar(tmp_path, csv_fixture, contratos):
    destino = tmp_path / "lago"
    r1 = _rodar_main(tmp_path, csv_fixture, contratos["ancorado"], destino,
                     tmp_path / "prova1.json")
    assert "LAGO=GRAVADO" in r1.stdout, r1.stdout[-2000:] + r1.stderr[-2000:]
    assert r1.returncode == 0
    prova1 = json.loads((tmp_path / "prova1.json").read_text(encoding="utf-8"))
    assert prova1["controles_lago"]["count_linhas"] == 10
    assert prova1["fonte_bate_lago"] is True and prova1["lago_bate_ancora"] is True
    primeiros = _arquivos(destino)
    assert primeiros

    # defeito latente FIXADO: append sem conferir partição vazia
    r2 = _rodar_main(tmp_path, csv_fixture, contratos["ancorado"], destino,
                     tmp_path / "prova2.json")
    assert "LAGO=DIVERGE" in r2.stdout, r2.stdout[-2000:] + r2.stderr[-2000:]
    assert r2.returncode == 1
    prova2 = json.loads((tmp_path / "prova2.json").read_text(encoding="utf-8"))
    assert prova2["controles_fonte"]["count_linhas"] == 10
    assert prova2["controles_lago"]["count_linhas"] == 20
    assert _dec(prova2["controles_lago"]["sum_vl_liquido"]) == Decimal("2476197.28")
    assert primeiros <= _arquivos(destino)


def _valores() -> list:
    return [None if v is None else Decimal(v) for _, _, _, v in LINHAS]


def _controles_py(valores: list) -> dict:
    validos = [v for v in valores if v is not None]
    return {
        "count_linhas": Decimal(len(valores)),
        "linhas_invalidas": Decimal(len(valores) - len(validos)),
        "sum_vl_liquido": sum(validos, Decimal(0)),
        "min_vl_liquido": min(validos),
        "max_vl_liquido": max(validos),
    }


def _alterar(controle: str) -> list:
    """Valores da releitura com UM único controle diferente da fonte."""
    v = _valores()
    if controle == "count_linhas":
        v.append(Decimal("0.00"))                        # +1 linha, soma intacta
    elif controle == "linhas_invalidas":
        v[2] = None                                      # o 0,00 vira inválido
    elif controle == "sum_vl_liquido":
        v[3] += Decimal("0.01")                          # 10,25 -> 10,26
    elif controle == "min_vl_liquido":
        v[7] = Decimal("-6.00")                          # -5,00 -> -6,00
        v[3] += Decimal("1.00")                          # compensa a soma
    elif controle == "max_vl_liquido":
        v[4] += Decimal("0.01")                          # 1234567,89 -> ,90
        v[3] -= Decimal("0.01")                          # compensa a soma
    return v


@pytest.mark.parametrize("controle", CONTROLES)
def test_cada_controle_divergente_acusa(controle, tmp_path, csv_fixture, contratos):
    valores = _alterar(controle)
    esperado, alterado = _controles_py(_valores()), _controles_py(valores)
    assert esperado == ESPERADO
    assert [k for k in CONTROLES if esperado[k] != alterado[k]] == [controle]

    linhas = [(c, d, None if v is None else str(v))
              for (c, d, _, _), v in zip(LINHAS, valores)]
    if controle == "count_linhas":
        linhas.append(("99", "Extra", str(valores[-1])))
    substituicao = tmp_path / "releitura.json"
    substituicao.write_text(json.dumps(linhas), encoding="utf-8")

    r = _rodar_main(tmp_path, csv_fixture, contratos["ancorado"], tmp_path / "lago",
                    tmp_path / "prova.json", substituicao)
    assert "LAGO=DIVERGE" in r.stdout, r.stdout[-2000:] + r.stderr[-2000:]
    assert r.returncode == 1
    veredito = {
        k: l.split()[-1] for l in r.stdout.splitlines() for k in CONTROLES
        if l.strip().startswith(k)
    }
    assert veredito == {k: ("DIVERGE" if k == controle else "BATE") for k in CONTROLES}


# ------------------------------------------------- sem mudar e sem tocar o MinIO


def test_destino_padrao_e_o_landing_de_hoje(tmp_path):
    assert gl.CAMINHO == DESTINO_DE_HOJE
    r = _filho(_FILHO_DEFAULTS, [SRC], tmp_path)
    assert r.returncode == 0, r.stderr[-2000:]
    padroes = json.loads(r.stdout.strip().splitlines()[-1])
    assert padroes["destino"] == DESTINO_DE_HOJE


def test_filho_sem_credencial_s3(tmp_path, csv_fixture, contratos):
    r = _filho(_FILHO_SEM_S3, [SRC], tmp_path)
    assert r.returncode == 0, r.stderr[-2000:]
    achados = json.loads(r.stdout.strip().splitlines()[-1])
    assert achados["s3_no_ambiente"] == []
    assert achados["gravador"] == "KeyError:S3_ENDPOINT"
    assert achados["endpoint_s3a"] == "AUSENTE"

    # o gravador de verdade, sem o patch de sessão: falha em vez de gravar
    destino = tmp_path / "lago"
    r = subprocess.run(
        [sys.executable, str(SRC / "produtor" / "gravar_lago.py"), str(csv_fixture),
         "--contrato", str(contratos["ancorado"]), "--destino", str(destino),
         "--out", str(tmp_path / "prova.json")],
        cwd=tmp_path, env=_env_filho(), capture_output=True, text=True, timeout=TIMEOUT,
    )
    assert r.returncode != 0
    assert "LAGO=GRAVADO" not in r.stdout
    assert "S3_ENDPOINT" in r.stderr
    assert not destino.exists()


def test_produzir_e_main_so_em_processo_filho():
    arvore = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    chamados = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Call):
            f = no.func
            nome = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
            if nome in ("produzir", "main"):
                chamados.append((nome, no.lineno))
    assert chamados == []
    # e o teste não se isenta: nenhum cenário pula
    proibidos = {"skip", "xfail", "importorskip", "skipif"}
    usados = {
        no.attr for no in ast.walk(arvore)
        if isinstance(no, ast.Attribute) and isinstance(no.value, ast.Name)
        and no.value.id == "pytest" and no.attr in proibidos
    }
    assert usados == set()


def test_controles_em_texto(spark, csv_fixture, envelope):
    medido = gl._controles(gl._ler_fonte(spark, csv_fixture, cm.carregar_contrato(CONTRATO)))
    for origem in (envelope["controles"], medido):
        for nome in ("sum_vl_liquido", "min_vl_liquido", "max_vl_liquido"):
            assert isinstance(origem[nome], str), nome
        for nome in ("count_linhas", "linhas_invalidas"):
            assert isinstance(origem[nome], int) and not isinstance(origem[nome], bool)
        for nome in CONTROLES:
            assert not isinstance(origem[nome], float), nome
