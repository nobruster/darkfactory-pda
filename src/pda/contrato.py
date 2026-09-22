"""Carregador do contrato de competência: âncora, procedência, layout e política decimal.

Regra 2 (AGENTS.md): sem âncora, a fábrica recusa rodar. `carregar_contrato`
nunca gera um número que ninguém mediu — se a prova não está no contrato, o
retorno é o valor sentinela NAO_MEDIDO, sem gravar nada e sem encerrar o
processo. Regra 3: um contrato presente mas que contradiz uma decisão
vinculante (ADR) é RECUSADO no carregamento, nunca "corrigido" para passar.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Union

import yaml

NAO_MEDIDO = "NAO_MEDIDO"

MODO_DECIMAL_PERMITIDO = "HALF_EVEN"
GRANULARIDADE_PERMITIDA = "total"


class ContratoRecusado(Exception):
    """O contrato foi lido, mas viola uma decisão vinculante — é recusado, nunca ajustado."""


@dataclass(frozen=True)
class Procedencia:
    fonte: str
    hash_zip_sha256: str
    hash_csv_sha256: str
    publicado_em: str


@dataclass(frozen=True)
class Layout:
    total_colunas: int
    separador: str
    encoding: str
    posicoes: dict


@dataclass(frozen=True)
class Ancora:
    count_linhas: int
    sum_vl_liquido: Decimal
    min_vl_liquido: Decimal
    max_vl_liquido: Decimal
    linhas_invalidas: int
    aprovado_por: str
    aprovado_em: str


@dataclass(frozen=True)
class Cardinalidade:
    codigos_distintos: int
    descricoes_distintas: int
    colapsos: int
    codigos_colapsados: int


@dataclass(frozen=True)
class DefeitoConhecido:
    tipo: str
    descricao: str
    quantidade: int
    aprovador: str
    aprovado_em: str


@dataclass(frozen=True)
class PoliticaDecimal:
    modo: str
    escala: int
    escala_maxima_intermediarios: int
    precisao: int
    nao_negativo: bool


@dataclass(frozen=True)
class Contrato:
    competencia: str
    procedencia: Procedencia
    layout: Layout
    ancora: Ancora
    cardinalidade: Cardinalidade
    defeitos_conhecidos: tuple
    politica_decimal: PoliticaDecimal


def _inteiro_nao_negativo(valor: Any, campo: str) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ContratoRecusado(f"{campo} precisa ser inteiro não negativo, veio {valor!r}")
    if valor < 0:
        raise ContratoRecusado(f"{campo} precisa ser inteiro não negativo, veio {valor!r}")
    return valor


def _decimal_monetario(valor: Any, campo: str) -> Decimal:
    # A recusa é do carregamento, antes de qualquer conversão (ADR 0003/0006):
    # um valor sem aspas no YAML chega aqui como float, e nem Decimal(str(v))
    # (apagaria a origem) nem Decimal(v) (traria a aproximação binária) são
    # aceitáveis — o valor é recusado, nunca reparado.
    if isinstance(valor, float):
        raise ContratoRecusado(
            f"{campo} veio como float no contrato — dinheiro é Decimal, nunca float"
        )
    if isinstance(valor, bool) or not isinstance(valor, (str, int)):
        raise ContratoRecusado(f"{campo} precisa ser string ou inteiro, veio {valor!r}")
    numero = Decimal(valor)
    if not numero.is_finite():
        raise ContratoRecusado(f"{campo} precisa ser finito, veio {valor!r}")
    return numero


def _digitos_inteiros(valor: Decimal) -> int:
    return len(str(int(valor)))


def carregar_contrato(caminho: Union[str, Path]) -> Union[Contrato, str]:
    """Carrega e valida o contrato de uma competência.

    Retorna NAO_MEDIDO — nunca levanta, nunca grava, nunca encerra o processo —
    quando a prova básica (âncora, aprovação, hashes, política decimal) está
    ausente: um contrato sem prova é indistinguível de um palpite (Regra 2).

    Levanta ContratoRecusado quando o contrato TEM conteúdo mas contradiz uma
    decisão vinculante: float em campo monetário, contagem negativa ou não
    inteira, layout fora das 14 posições medidas, política decimal diferente
    de HALF_EVEN/total, ou precisão insuficiente para a soma (ADR 0007/0009).
    """
    caminho = Path(caminho)
    bruto = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}

    ancora_bruta = bruto.get("ancora")
    politica_bruta = bruto.get("politica_decimal")
    procedencia_bruta = bruto.get("procedencia") or {}

    if not ancora_bruta:
        return NAO_MEDIDO
    if not politica_bruta:
        return NAO_MEDIDO
    if not ancora_bruta.get("aprovado_por") or not ancora_bruta.get("aprovado_em"):
        return NAO_MEDIDO
    if not procedencia_bruta.get("hash_zip_sha256") or not procedencia_bruta.get("hash_csv_sha256"):
        return NAO_MEDIDO

    ancora = Ancora(
        count_linhas=_inteiro_nao_negativo(ancora_bruta.get("count_linhas"), "ancora.count_linhas"),
        sum_vl_liquido=_decimal_monetario(ancora_bruta.get("sum_vl_liquido"), "ancora.sum_vl_liquido"),
        min_vl_liquido=_decimal_monetario(ancora_bruta.get("min_vl_liquido"), "ancora.min_vl_liquido"),
        max_vl_liquido=_decimal_monetario(ancora_bruta.get("max_vl_liquido"), "ancora.max_vl_liquido"),
        linhas_invalidas=_inteiro_nao_negativo(
            ancora_bruta.get("linhas_invalidas"), "ancora.linhas_invalidas"
        ),
        aprovado_por=ancora_bruta["aprovado_por"],
        aprovado_em=ancora_bruta["aprovado_em"],
    )

    procedencia = Procedencia(
        fonte=procedencia_bruta.get("fonte", ""),
        hash_zip_sha256=procedencia_bruta["hash_zip_sha256"],
        hash_csv_sha256=procedencia_bruta["hash_csv_sha256"],
        publicado_em=procedencia_bruta.get("publicado_em", ""),
    )
    if procedencia.hash_zip_sha256 == procedencia.hash_csv_sha256:
        raise ContratoRecusado(
            "hash do ZIP publicado e hash do CSV extraído não podem ser iguais — "
            "são dois artefatos distintos e a âncora foi medida sobre o CSV"
        )

    layout_bruto = bruto.get("layout") or {}
    posicoes = dict(layout_bruto.get("posicoes") or {})
    layout = Layout(
        total_colunas=_inteiro_nao_negativo(layout_bruto.get("total_colunas"), "layout.total_colunas"),
        separador=layout_bruto.get("separador", ";"),
        encoding=layout_bruto.get("encoding", "latin-1"),
        posicoes=posicoes,
    )
    if layout.total_colunas != 14:
        raise ContratoRecusado("layout precisa declarar as 14 posições da competência (ADR 0002)")
    if posicoes.get("especie") != 12 or posicoes.get("descricao_especie") != 13:
        raise ContratoRecusado(
            "Espécie precisa estar declarada por posição, nos índices 12 e 13 (ADR 0002)"
        )

    cardinalidade_bruta = bruto.get("cardinalidade") or {}
    cardinalidade = Cardinalidade(
        codigos_distintos=_inteiro_nao_negativo(
            cardinalidade_bruta.get("codigos_distintos"), "cardinalidade.codigos_distintos"
        ),
        descricoes_distintas=_inteiro_nao_negativo(
            cardinalidade_bruta.get("descricoes_distintas"), "cardinalidade.descricoes_distintas"
        ),
        colapsos=_inteiro_nao_negativo(cardinalidade_bruta.get("colapsos"), "cardinalidade.colapsos"),
        codigos_colapsados=_inteiro_nao_negativo(
            cardinalidade_bruta.get("codigos_colapsados"), "cardinalidade.codigos_colapsados"
        ),
    )

    defeitos = []
    for bruto_defeito in bruto.get("defeitos_conhecidos") or []:
        if not bruto_defeito.get("aprovador") or not bruto_defeito.get("aprovado_em"):
            raise ContratoRecusado("defeito conhecido sem aprovador ou data de aprovação")
        defeitos.append(
            DefeitoConhecido(
                tipo=bruto_defeito["tipo"],
                descricao=bruto_defeito.get("descricao", ""),
                quantidade=_inteiro_nao_negativo(
                    bruto_defeito.get("quantidade"), "defeitos_conhecidos[].quantidade"
                ),
                aprovador=bruto_defeito["aprovador"],
                aprovado_em=bruto_defeito["aprovado_em"],
            )
        )

    modo = politica_bruta.get("modo")
    if modo != MODO_DECIMAL_PERMITIDO:
        raise ContratoRecusado(
            f"política decimal com modo {modo!r} contradiz o ADR 0003 — só HALF_EVEN é aceito"
        )
    granularidade = politica_bruta.get("granularidade", GRANULARIDADE_PERMITIDA)
    if granularidade != GRANULARIDADE_PERMITIDA:
        raise ContratoRecusado(
            f"granularidade {granularidade!r} contradiz o ADR 0003 — arredonda-se uma vez, no total"
        )
    if politica_bruta.get("nao_negativo") is not True:
        raise ContratoRecusado(
            "política decimal precisa declarar o domínio como não negativo (ADR 0009) — "
            "é essa premissa que sustenta a precisão derivada"
        )

    escala = _inteiro_nao_negativo(politica_bruta.get("escala"), "politica_decimal.escala")
    escala_intermediarios = _inteiro_nao_negativo(
        politica_bruta.get("escala_maxima_intermediarios"),
        "politica_decimal.escala_maxima_intermediarios",
    )
    precisao = _inteiro_nao_negativo(politica_bruta.get("precisao"), "politica_decimal.precisao")

    minimo = _digitos_inteiros(ancora.sum_vl_liquido) + escala_intermediarios
    if precisao < minimo:
        raise ContratoRecusado(
            f"precisão declarada ({precisao}) é insuficiente para somar sob a âncora — "
            f"mínimo derivado (ADR 0007) é {minimo}"
        )

    politica_decimal = PoliticaDecimal(
        modo=modo,
        escala=escala,
        escala_maxima_intermediarios=escala_intermediarios,
        precisao=precisao,
        nao_negativo=True,
    )

    return Contrato(
        competencia=bruto.get("competencia", ""),
        procedencia=procedencia,
        layout=layout,
        ancora=ancora,
        cardinalidade=cardinalidade,
        defeitos_conhecidos=tuple(defeitos),
        politica_decimal=politica_decimal,
    )
