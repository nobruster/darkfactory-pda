"""Orquestração: dá dono ao fluxo, do contrato ao veredito, em todo caminho (SEAM-ORQUESTRACAO).

Este módulo é o único lugar que decide QUAL desfecho uma execução teve — os
outros (contrato, leitura, agregacao, envelope, juizo, evidencia) só
respondem perguntas locais. `conduzir` percorre os quatro caminhos possíveis
e GRAVA PACOTE nos quatro, porque autorização sem evidência é exatamente o
que esta fábrica existe para impedir:

- contrato NAO_MEDIDO  -> ACEITO_SEM_ANCORA
- contrato ContratoRecusado (ex.: política HALF_UP) -> RECUSADO, sem chegar
  à leitura
- exceção real dentro da leitura -> ERRO
- leitura concluída -> o JUÍZO (`juizo.julgar`) decide ACEITO ou RECUSADO

B-1 (Regra 3): a comparação contra a âncora monetária é sempre feita pelo
juízo real, nunca por uma heurística local — `conduzir` chama
`juizo.julgar`, e além disso grava os cinco controles do contrato e do
agregado SEPARADAMENTE no pacote, para que `evidencia.rederivar_veredito`
confira de novo, por um caminho independente, sem confiar no juízo que
rodou nesta chamada. Um juízo permissivo injetado no lugar do real não basta
sozinho para produzir ACEITO: a rederivação a partir dos controles brutos
continua divergente.

B-1 (autorização): só ACEITO autoriza publicar, e a autorização declara a
competência SOLICITADA — recusa quando o contrato ou o envelope carregam
outra, mesmo que hashes, totais e defeitos concordem entre si (o caso de uma
execução de 2026-02 que recebe, por engano, os artefatos coerentes de
2026-01).

B-2 (Regra 4): o tempo é medido do início da leitura ao veredito — nunca por
etapa — e SEMPRE registrado no pacote, mesmo quando o veredito não é ACEITO;
nunca vira motivo de recusa por si só (R-9 é should).

B-2: se o próprio gravador de evidência falhar (permissão negada, disco
cheio), o desfecho é ERRO, sem pacote, e a falha vai para a saída de erro —
nunca se devolve ACEITO sem pacote gravado.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple, Union

from . import contrato as contrato_mod
from . import evidencia as evidencia_mod
from . import juizo as juizo_mod

CODIGO_SAIDA: Dict[str, int] = {
    evidencia_mod.ACEITO: 0,
    evidencia_mod.RECUSADO: 1,
    evidencia_mod.ACEITO_SEM_ANCORA: 2,
    evidencia_mod.ERRO: 3,
}


class OrquestracaoFalhou(Exception):
    """O gravador de evidência falhou ao gravar o pacote — nunca autoriza ACEITO sem pacote."""


@dataclass(frozen=True)
class InsumosExecucao:
    """O que a leitura (e o produtor do envelope) produziram para esta execução.

    `agregado` precisa expor `count_linhas`, `linhas_invalidas`,
    `sum_vl_liquido`, `min_vl_liquido` e `max_vl_liquido` — o mesmo formato
    de `agregacao.ResultadoAgregacao` — porque é contra ele que o juízo
    compara a âncora do contrato.
    """

    competencia_contrato: Any = evidencia_mod.CHAVE_AUSENTE
    competencia_envelope: Any = evidencia_mod.CHAVE_AUSENTE
    hash_ancorado: Any = evidencia_mod.CHAVE_AUSENTE
    hash_observado: Any = evidencia_mod.CHAVE_AUSENTE
    hash_declarado: Any = evidencia_mod.CHAVE_AUSENTE
    agregado: Any = None
    diferencas: Tuple[juizo_mod.Diferenca, ...] = ()
    defeitos_leitura: List[dict] = field(default_factory=list)
    defeitos_envelope: List[dict] = field(default_factory=list)
    totais_leitura: Dict[str, Any] = field(default_factory=dict)
    totais_envelope: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Desfecho:
    veredito: str
    causa: str
    codigo_saida: int
    caminho_pacote: Union[Path, None]
    duracao_segundos: float
    autorizado_publicar: bool


def _classificacoes_brutas(diferencas: Tuple[juizo_mod.Diferenca, ...]) -> Dict[str, str]:
    """Registra a classificação tentada de cada diferença, mesmo quando o juízo bloqueia.

    Nunca inventa uma classificação aprovada: quando há zero ou mais de uma,
    grava um rótulo que não pertence a `CLASSIFICACOES_QUE_REGISTRAM`, para
    que `evidencia.rederivar_veredito` também recuse — por um caminho
    independente do juízo que rodou aqui.
    """
    brutas: Dict[str, str] = {}
    for diferenca in diferencas:
        if len(diferenca.classificacoes) == 1:
            brutas[diferenca.identidade] = diferenca.classificacoes[0]
        else:
            brutas[diferenca.identidade] = "SEM_CLASSIFICACAO_UNICA"
    return brutas


def _autoriza_publicar(veredito: str, competencia_solicitada: str, pacote: dict) -> bool:
    """Só ACEITO autoriza — e só quando contrato e envelope declaram a competência SOLICITADA.

    Um pacote ACEITO cujo `competencia_contrato`/`competencia_envelope`
    divergem da competência pedida por quem chamou não autoriza publicar:
    hashes, totais e defeitos podem concordar entre si e ainda assim serem
    os artefatos coerentes de OUTRA competência.
    """
    if veredito != evidencia_mod.ACEITO:
        return False
    competencia_contrato = pacote.get("competencia_contrato", evidencia_mod.CHAVE_AUSENTE)
    competencia_envelope = pacote.get("competencia_envelope", evidencia_mod.CHAVE_AUSENTE)
    if competencia_contrato in (evidencia_mod.CHAVE_AUSENTE, None):
        return False
    if competencia_envelope in (evidencia_mod.CHAVE_AUSENTE, None):
        return False
    return (
        competencia_contrato == competencia_solicitada
        and competencia_envelope == competencia_solicitada
    )


def _gravar_desfecho(
    diretorio_evidencia: Path,
    *,
    competencia_solicitada: str,
    duracao_segundos: float,
    **kwargs_pacote: Any,
) -> Desfecho:
    """Grava o pacote e rederiva o veredito a partir dele — nunca confia no rótulo local.

    Se o próprio gravador falhar, o desfecho é ERRO sem pacote, e a falha
    vai para a saída de erro — nunca ACEITO sem pacote gravado.
    """
    try:
        caminho = evidencia_mod.gravar_pacote(
            diretorio_evidencia,
            competencia_solicitada=competencia_solicitada,
            duracao_segundos=duracao_segundos,
            **kwargs_pacote,
        )
    except Exception as exc:  # gravador falhou: permissão negada, disco cheio, etc.
        sys.stderr.write(
            f"orquestracao: gravador de evidência falhou para "
            f"{competencia_solicitada!r}: {exc}\n"
        )
        return Desfecho(
            veredito=evidencia_mod.ERRO,
            causa="GRAVADOR_FALHOU",
            codigo_saida=CODIGO_SAIDA[evidencia_mod.ERRO],
            caminho_pacote=None,
            duracao_segundos=duracao_segundos,
            autorizado_publicar=False,
        )

    pacote = evidencia_mod.ler_pacote(caminho)
    veredito, causa = evidencia_mod.rederivar_veredito(pacote)
    autorizado = _autoriza_publicar(veredito, competencia_solicitada, pacote)

    return Desfecho(
        veredito=veredito,
        causa=causa,
        codigo_saida=CODIGO_SAIDA[veredito],
        caminho_pacote=caminho,
        duracao_segundos=pacote.get("duracao_segundos", duracao_segundos),
        autorizado_publicar=autorizado,
    )


def conduzir(
    *,
    diretorio_evidencia: Union[str, Path],
    competencia_solicitada: str,
    caminho_contrato: Union[str, Path],
    executar_leitura: Callable[[contrato_mod.Contrato], InsumosExecucao],
) -> Desfecho:
    """Conduz uma execução do início (carregar o contrato) ao veredito, gravando pacote sempre.

    Nunca encerra o processo dentro de uma etapa (Anti-Pattern): sempre
    devolve um `Desfecho` com pacote gravado, em qualquer um dos quatro
    caminhos.
    """
    diretorio_evidencia = Path(diretorio_evidencia)

    try:
        carregado = contrato_mod.carregar_contrato(caminho_contrato)
    except contrato_mod.ContratoRecusado as exc:
        # Terceiro caminho antecipado (ADR 0005 do pacote de evidência):
        # o contrato TEM conteúdo mas contradiz uma decisão vinculante —
        # termina RECUSADO sem jamais chegar à leitura.
        return _gravar_desfecho(
            diretorio_evidencia,
            competencia_solicitada=competencia_solicitada,
            duracao_segundos=0.0,
            contrato_status=evidencia_mod.CONTRATO_RECUSADO,
            politica_recusada={"caminho_contrato": str(caminho_contrato)},
            clausula_adr_violada=str(exc),
        )

    if carregado == contrato_mod.NAO_MEDIDO:
        return _gravar_desfecho(
            diretorio_evidencia,
            competencia_solicitada=competencia_solicitada,
            duracao_segundos=0.0,
            contrato_status=evidencia_mod.CONTRATO_NAO_MEDIDO,
        )

    contrato_carregado = carregado

    inicio = time.monotonic()
    try:
        insumos = executar_leitura(contrato_carregado)
    except Exception as exc:  # exceção real dentro da leitura -> ERRO
        duracao = time.monotonic() - inicio
        return _gravar_desfecho(
            diretorio_evidencia,
            competencia_solicitada=competencia_solicitada,
            duracao_segundos=duracao,
            contrato_status=evidencia_mod.CONTRATO_OK,
            evento_falha={"tipo": type(exc).__name__, "mensagem": str(exc)},
        )

    try:
        veredito_juizo = juizo_mod.julgar(insumos.agregado, contrato_carregado, insumos.diferencas)
        classificacoes = veredito_juizo.classificacoes
    except (juizo_mod.JuizoRecusado, juizo_mod.JuizoBloqueado):
        classificacoes = _classificacoes_brutas(insumos.diferencas)

    duracao = time.monotonic() - inicio

    ancora = contrato_carregado.ancora
    ancora_controles = {
        "count_linhas": ancora.count_linhas,
        "linhas_invalidas": ancora.linhas_invalidas,
        "sum_vl_liquido": ancora.sum_vl_liquido,
        "min_vl_liquido": ancora.min_vl_liquido,
        "max_vl_liquido": ancora.max_vl_liquido,
    }
    agregado_controles = {
        "count_linhas": insumos.agregado.count_linhas,
        "linhas_invalidas": insumos.agregado.linhas_invalidas,
        "sum_vl_liquido": insumos.agregado.sum_vl_liquido,
        "min_vl_liquido": insumos.agregado.min_vl_liquido,
        "max_vl_liquido": insumos.agregado.max_vl_liquido,
    }

    return _gravar_desfecho(
        diretorio_evidencia,
        competencia_solicitada=competencia_solicitada,
        duracao_segundos=duracao,
        contrato_status=evidencia_mod.CONTRATO_OK,
        competencia_contrato=insumos.competencia_contrato,
        competencia_envelope=insumos.competencia_envelope,
        aprovador=ancora.aprovado_por,
        aprovado_em=ancora.aprovado_em,
        politica_decimal_modo=contrato_carregado.politica_decimal.modo,
        escala=contrato_carregado.politica_decimal.escala,
        hash_ancorado=insumos.hash_ancorado,
        hash_observado=insumos.hash_observado,
        hash_declarado=insumos.hash_declarado,
        ancora_controles=ancora_controles,
        agregado_controles=agregado_controles,
        classificacoes=classificacoes,
        defeitos_leitura=insumos.defeitos_leitura,
        defeitos_envelope=insumos.defeitos_envelope,
        totais_leitura=insumos.totais_leitura,
        totais_envelope=insumos.totais_envelope,
    )
