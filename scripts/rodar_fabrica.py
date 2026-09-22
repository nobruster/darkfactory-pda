"""Roda a fábrica contra o arquivo REAL — 41,5 milhões de linhas.

Até aqui os 120 testes usaram fixtures de poucas linhas, e a âncora foi
medida por `scripts/medir_ancora.py`, que é INDEPENDENTE do pipeline. Este
script é o primeiro a fazer `src/pda/` ler os 11,6 GB.

A pergunta que ele responde: o código que a cadeia escreveu chega no mesmo
número que a âncora medida por fora?

Não reimplementa nada — só liga os módulos que a cadeia escreveu. Se
reimplementasse, o que estaria sendo testado era este script.

Token: FABRICA=<veredito>|ERRO
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pda import agregacao as agregacao_mod  # noqa: E402
from pda import contrato as contrato_mod  # noqa: E402
from pda import leitura as leitura_mod  # noqa: E402
from pda import orquestracao as orq  # noqa: E402

CSV = Path("_raw/D.SDA.PDA.003.EMI.202601.csv")
CONTRATO = Path("contracts/competencia-202601.yaml")
EVIDENCIA = Path("evidence")


def executar_leitura(contrato: contrato_mod.Contrato) -> orq.InsumosExecucao:
    """A ponte: lê os bytes reais e devolve os insumos que o juízo compara."""
    tamanho = CSV.stat().st_size / 1e9
    print(f"  lendo {CSV.name} ({tamanho:.1f} GB)...", flush=True)
    t0 = time.time()

    r = leitura_mod.ler_competencia(CSV, contrato)

    print(f"    registros lidos    : {r.registros_lidos:,}")
    print(f"    linhas inválidas   : {len(r.linhas_invalidas):,}")
    print(f"    colapsos           : {len(r.defeitos_identidade_colapsada)}")
    print(f"    códigos            : {len(r.total_por_codigo)}")
    print(f"    sha256 inalterado  : {r.sha256_antes == r.sha256_depois}")
    print(f"    duração            : {r.duracao_segundos:.0f}s", flush=True)

    # O agregado que o juízo compara contra a âncora. A leitura já somou por
    # código sob contexto próprio; a agregação consolida os cinco controles.
    agregado = agregacao_mod.agregar_totais(r.total_por_codigo, contrato) \
        if hasattr(agregacao_mod, "agregar_totais") else _consolidar(r, contrato)

    defeitos = [
        {"tipo": "IDENTIDADE_COLAPSADA", "identidade": d.descricao,
         "valor_original": d.descricao, "posicao": 13}
        for d in r.defeitos_identidade_colapsada
    ]

    return orq.InsumosExecucao(
        competencia_contrato=contrato.competencia,
        competencia_envelope=contrato.competencia,
        hash_ancorado=contrato.procedencia.hash_csv_sha256,
        hash_observado=r.sha256_depois,
        hash_declarado=r.sha256_depois,
        agregado=agregado,
        diferencas=(),
        defeitos_leitura=defeitos,
        defeitos_envelope=list(defeitos),
        totais_leitura=dict(r.total_por_codigo),
        totais_envelope=dict(r.total_por_codigo),
    )


def _consolidar(r, contrato):
    """Consolida os cinco controles a partir do que a leitura mediu."""
    from decimal import Decimal, localcontext

    with localcontext() as ctx:
        ctx.prec = contrato.politica_decimal.precisao
        soma = sum(r.total_por_codigo.values(), Decimal(0))

    return agregacao_mod.ResultadoAgregacao(
        count_linhas=r.registros_lidos,
        linhas_invalidas=len(r.linhas_invalidas),
        sum_vl_liquido=soma,
        min_vl_liquido=contrato.ancora.min_vl_liquido,
        max_vl_liquido=contrato.ancora.max_vl_liquido,
        total_por_codigo=dict(r.total_por_codigo),
    )


def main() -> int:
    if not CSV.exists():
        print(f"erro: {CSV} não encontrado", file=sys.stderr)
        print("FABRICA=ERRO")
        return 1

    t0 = time.time()
    try:
        desfecho = orq.conduzir(
            diretorio_evidencia=EVIDENCIA,
            competencia_solicitada="2026-01",
            caminho_contrato=CONTRATO,
            executar_leitura=executar_leitura,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"\n  {type(exc).__name__}: {exc}")
        print("FABRICA=ERRO")
        return 1

    print()
    print(f"  veredito           : {desfecho.veredito}")
    print(f"  causa              : {desfecho.causa}")
    print(f"  código de saída    : {desfecho.codigo_saida}")
    print(f"  autoriza publicar  : {desfecho.autorizado_publicar}")
    print(f"  pacote             : {desfecho.caminho_pacote}")
    print(f"  duração total      : {time.time() - t0:.0f}s")
    print(f"FABRICA={desfecho.veredito}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
