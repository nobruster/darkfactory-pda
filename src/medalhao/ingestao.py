"""Ingestão julgada: a Bronze só publica com o juízo do segundo motor (SEAM-JUIZO-NA-INGESTAO).

O arquivo bruto é lido UMA vez, aqui, pelos dois motores: o Spark mede a Bronze
(sem gravar) e o leitor posicional em Python — já selado — lê o CSV. Quem decide
é `orquestracao.conduzir`, reusado, nunca reimplementado.

- O que publica é o MESMO resultado medido dentro do `executar_leitura`; a landing
  não é lida uma segunda vez.
- Só `Desfecho.autorizado_publicar` publica, pelo protocolo que já existe
  (preparo, replaceWhere, reconferência). O `userMetadata` do commit nomeia o
  `caminho_pacote` e o `sha256_pacote` do juízo.
- A reconferência depois de publicar compara a Bronze publicada com os cinco
  controles e o `total_por_codigo` que o pacote JULGOU.
- Sem autorização (RECUSADO, ERRO, ACEITO_SEM_ANCORA) nada publica; o pacote
  fica como evidência e o veredito do orquestrador volta sem tradução.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Callable, Optional

from pyspark.sql import SparkSession

from medalhao import bronze, gold
from pda import contrato as contrato_mod
from pda import envelope as envelope_mod
from pda import evidencia, leitura, orquestracao

INTEGRO = bronze.INTEGRO


def _envelope_da_bronze(b: bronze.BronzeConferido) -> dict:
    """Envelope da fronteira montado do que o Spark MEDIU — o segundo motor o confere."""
    c = b.controles
    texto = lambda v: None if v is None else str(v)  # noqa: E731
    return {
        "competencia": b.competencia,
        "motor": gold.MOTOR,
        "sha256_arquivo_lido": b.hash_procedencia,
        "controles": {
            "count_linhas": int(c["count_linhas"]),
            "linhas_invalidas": int(c["linhas_invalidas"]),
            "sum_vl_liquido": str(c["sum_vl_liquido"]),
            "min_vl_liquido": texto(c.get("min_vl_liquido")),
            "max_vl_liquido": texto(c.get("max_vl_liquido")),
        },
        "defeitos": [],
        "total_por_codigo": {k: str(v) for k, v in sorted(b.total_por_codigo.items())},
    }


def _parou(camada: str, motivo: str, marcas=()) -> gold.CadeiaParou:
    return gold.CadeiaParou(
        json.dumps(
            {"camada": camada, "estado": bronze.DIVERGE, "motivo": motivo, "marcas": list(marcas), "classificacoes": {}},
            ensure_ascii=False, sort_keys=True,
        )
    )


def montar_leitura(
    spark: SparkSession,
    *,
    caminho_csv,
    raiz: str,
    procedencia: Optional[dict] = None,
    bronze_kwargs: Optional[dict] = None,
    resultado: Optional[dict] = None,
) -> Callable:
    """O `executar_leitura` que `conduzir` recebe: mede a Bronze SEM gravar e lê o CSV pelo segundo motor."""

    def executar(contrato) -> orquestracao.InsumosExecucao:
        b = bronze.executar_leitura(
            spark, contrato, raiz=raiz, procedencia=procedencia, **{**(bronze_kwargs or {}), "gravar": False}
        )
        if resultado is not None:
            resultado["bronze"] = b
        # Só divergir da âncora (tipo "controle") é assunto do juízo: ele decide RECUSADO.
        so_ancora = (
            b.estado == bronze.DIVERGE
            and bool(b.diferencas)
            and not b.defeitos
            and all(d["tipo"] == "controle" for d in b.diferencas)
        )
        if b.estado != INTEGRO and not so_ancora:
            raise gold.CadeiaParou(gold.diagnostico("bronze", b))
        if bronze.PROCEDENCIA_NAO_VINCULADA in b.marcas:  # sem hash o envelope recusaria por outro motivo
            raise _parou("bronze", bronze.PROCEDENCIA_NAO_VINCULADA, b.marcas)

        lida = leitura.ler_competencia(caminho_csv, contrato)
        defeitos = gold._defeitos_da_leitura(lida)
        capacidade = envelope_mod.CapacidadeLeitura(
            sha256_computado=lida.sha256_depois,
            total_por_codigo=lida.total_por_codigo,
            defeitos=tuple(
                envelope_mod.DefeitoLeitura(d["tipo"], d["valor_original"], d["posicao"]) for d in defeitos
            ),
        )
        env = _envelope_da_bronze(b)
        try:
            validado = envelope_mod.validar_envelope(env, capacidade, contrato)
        except envelope_mod.EnvelopeRecusado as exc:
            raise _parou("envelope", str(exc)) from exc
        agregado = gold.Agregado(
            count_linhas=validado.count_linhas,
            linhas_invalidas=validado.linhas_invalidas,
            sum_vl_liquido=validado.sum_vl_liquido,
            min_vl_liquido=validado.min_vl_liquido,
            max_vl_liquido=validado.max_vl_liquido,
        )
        return orquestracao.InsumosExecucao(
            competencia_contrato=contrato.competencia,
            competencia_envelope=env["competencia"],
            hash_ancorado=contrato.procedencia.hash_csv_sha256,
            hash_observado=lida.sha256_depois,
            hash_declarado=env["sha256_arquivo_lido"],
            agregado=agregado,
            diferencas=(),
            defeitos_leitura=defeitos,
            defeitos_envelope=list(env["defeitos"]),
            totais_leitura=dict(lida.total_por_codigo),
            totais_envelope=dict(validado.total_por_codigo),
        )

    return executar


def _decimal_do_par(par) -> Optional[Decimal]:
    if par is None:
        return None
    return Decimal(par["texto"])


def _julgado_do_pacote(pacote: dict) -> dict:
    """Os cinco controles e o total por código que o pacote JULGOU — o termo da reconferência."""
    c = pacote["agregado_controles"]
    return {
        "controles": {
            "count_linhas": c["count_linhas"],
            "linhas_invalidas": c["linhas_invalidas"],
            "sum_vl_liquido": _decimal_do_par(c["sum_vl_liquido"]),
            "min_vl_liquido": _decimal_do_par(c["min_vl_liquido"]),
            "max_vl_liquido": _decimal_do_par(c["max_vl_liquido"]),
        },
        "total_por_codigo": {k: _decimal_do_par(v) for k, v in pacote["totais_leitura"].items()},
    }


def executar_ingestao(
    spark: SparkSession,
    *,
    diretorio_evidencia,
    competencia_solicitada: str,
    caminho_contrato,
    caminho_csv,
    raiz: str,
    procedencia: Optional[dict] = None,
    destino: str = bronze.DESTINO_PADRAO,
    preparo_raiz: str = bronze.PREPARO_PADRAO,
    id_execucao: Optional[str] = None,
    bronze_kwargs: Optional[dict] = None,
    evolucao_aditiva: bool = True,
):
    """Julga sob `orquestracao.conduzir`; publica a Bronze só com autorização. Devolve (Desfecho, Bronze)."""
    id_execucao = id_execucao or uuid.uuid4().hex
    guardado: dict = {}
    executar = montar_leitura(
        spark, caminho_csv=caminho_csv, raiz=raiz, procedencia=procedencia,
        bronze_kwargs=bronze_kwargs, resultado=guardado,
    )
    desfecho = orquestracao.conduzir(
        diretorio_evidencia=diretorio_evidencia,
        competencia_solicitada=competencia_solicitada,
        caminho_contrato=caminho_contrato,
        executar_leitura=executar,
    )
    medido = guardado.get("bronze")
    caminho = desfecho.caminho_pacote
    if medido is None:  # o juízo parou antes de pedir a leitura (ex.: sem âncora): nada foi medido
        medido = bronze._nao_medido(competencia_solicitada, "NAO_JULGADO_SEM_LEITURA")
    if not desfecho.autorizado_publicar or caminho is None or not Path(caminho).exists():
        return desfecho, medido

    pacote = evidencia.ler_pacote(caminho)
    contrato = contrato_mod.carregar_contrato(caminho_contrato)
    publicado = bronze.publicar_bronze(
        spark, contrato, medido,
        destino=destino, preparo_raiz=preparo_raiz, id_execucao=id_execucao,
        evolucao_aditiva=evolucao_aditiva,
        metadados_extra={
            "caminho_pacote": str(caminho),
            "sha256_pacote": hashlib.sha256(Path(caminho).read_bytes()).hexdigest(),
        },
        julgado=_julgado_do_pacote(pacote),
    )
    return desfecho, publicado
