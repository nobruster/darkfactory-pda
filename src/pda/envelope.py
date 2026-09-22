"""Validação do envelope na fronteira entre produtor e juiz.

Regra 3 (AGENTS.md): a fronteira é um contrato escrito, não o que o juiz por
acaso aceita. `validar_envelope` nunca importa o motor produtor — ele valida
o envelope como dado, seja qual for a origem (ADR 0006 permite produtor
externo).

O vínculo entre o envelope e o arquivo que foi de fato lido não é um segundo
campo do envelope repetindo a âncora: é uma capacidade PRÓPRIA da leitura —
`CapacidadeLeitura.sha256_computado`, o hash que a leitura calculou sobre os
bytes que ela mesma abriu — comparada contra o que o produtor declara. Um
envelope que apenas copia o hash ancorado, mas foi produzido lendo outro
arquivo, diverge dessa capacidade e é recusado; só a leitura, nunca o
envelope, pode fornecer o termo de comparação.

Regra 5: todo campo monetário do envelope é string ou Decimal FINITO, NÃO
NEGATIVO, dentro da escala do contrato — nunca float. A recusa é do domínio,
antes de qualquer conversão: `Decimal(str(v))` apagaria a prova de que um
float chegou onde só dinheiro-como-texto é aceito.

ADR 0008: `linhas_invalidas` confere só contra defeitos VALOR_ILEGIVEL —
identidade colapsada é defeito numa linha válida, nunca soma em
`linhas_invalidas`.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional, Union

VALOR_ILEGIVEL = "VALOR_ILEGIVEL"

# Gramática monetária do ENVELOPE: string não negativa, ponto decimal — este
# é o formato de saída do contrato, não a gramática BR da fonte (que a
# leitura já resolveu). '-0.01', 'NaN', 'sNaN', 'Infinity' e notação
# científica nunca casam, e são recusados antes de qualquer Decimal(...).
_PADRAO_MONETARIO = re.compile(r"^\d+(\.\d+)?$")

# Schema estrutural do envelope — embutido aqui porque o caminho canônico
# `contracts/envelope-produtor.schema.json` está sob a cerca permanente
# deste repositório (.claude/settings.json + .cvg/gate.yaml negam escrita em
# `contracts/**`: é o juiz da fábrica, e a autoridade de uma tarefa só
# estreita essa cerca, nunca a alarga). O schema é produtor-agnóstico por
# construção: nada aqui referencia um motor específico.
ENVELOPE_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Envelope de produtor - fronteira SEAM-FRONTEIRA",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "competencia",
        "motor",
        "sha256_arquivo_lido",
        "controles",
        "defeitos",
        "total_por_codigo",
    ],
    "properties": {
        "competencia": {"type": "string", "minLength": 1},
        "motor": {"type": "string", "minLength": 1},
        "sha256_arquivo_lido": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "controles": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "count_linhas",
                "linhas_invalidas",
                "sum_vl_liquido",
                "min_vl_liquido",
                "max_vl_liquido",
            ],
            "properties": {
                "count_linhas": {"type": "integer", "minimum": 0},
                "linhas_invalidas": {"type": "integer", "minimum": 0},
                "sum_vl_liquido": {"type": "string"},
                "min_vl_liquido": {"type": ["string", "null"]},
                "max_vl_liquido": {"type": ["string", "null"]},
            },
        },
        "defeitos": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["tipo", "valor_original", "posicao"],
                "properties": {
                    "tipo": {"type": "string", "minLength": 1},
                    "valor_original": {"type": "string"},
                    "posicao": {"type": "integer", "minimum": 0},
                },
            },
        },
        "total_por_codigo": {
            "type": "object",
            "additionalProperties": {"type": ["string", "null"]},
        },
    },
}


class EnvelopeRecusado(Exception):
    """O envelope foi lido, mas viola a fronteira — é recusado, nunca ajustado."""


@dataclass(frozen=True)
class DefeitoLeitura:
    """Um defeito na identidade que a leitura observou, com valor original e posição."""

    tipo: str
    valor_original: str
    posicao: int


@dataclass(frozen=True)
class CapacidadeLeitura:
    """O que só a leitura pode fornecer — nunca reconstruído a partir do envelope.

    `sha256_computado` é o hash calculado sobre os bytes que a leitura de
    fato abriu. `total_por_codigo` é a soma EXATA por código, não quantizada
    — o termo de referência contra o qual o mapa do envelope é conferido por
    valor. `defeitos` é a lista de defeitos que a leitura observou, cada um
    com sua identidade própria (tipo, valor original, posição).
    """

    sha256_computado: str
    total_por_codigo: dict
    defeitos: tuple


@dataclass(frozen=True)
class ResultadoValidacaoEnvelope:
    competencia: str
    motor: str
    sha256_arquivo_lido: str
    count_linhas: int
    linhas_invalidas: int
    sum_vl_liquido: Decimal
    min_vl_liquido: Union[Decimal, None]
    max_vl_liquido: Union[Decimal, None]
    total_por_codigo: dict


_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


def _e_inteiro_json(valor: Any) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _validar_schema(envelope: dict) -> None:
    """Confere a forma estrutural do envelope contra `ENVELOPE_SCHEMA`, sem depender
    de uma biblioteca externa de JSON Schema — a mesma forma que o schema declara,
    verificada campo a campo, produtor-agnóstica por construção.
    """
    if not isinstance(envelope, dict):
        raise EnvelopeRecusado("envelope precisa ser um objeto")

    campos_schema = set(ENVELOPE_SCHEMA["properties"])
    extras = set(envelope) - campos_schema
    if extras:
        raise EnvelopeRecusado(f"envelope declara campos fora do schema: {sorted(extras)}")

    for campo in ENVELOPE_SCHEMA["required"]:
        if campo not in envelope:
            raise EnvelopeRecusado(f"envelope não declara o campo obrigatório {campo!r}")

    if not isinstance(envelope.get("competencia"), str) or not envelope["competencia"]:
        raise EnvelopeRecusado("competencia precisa ser string não vazia")
    if not isinstance(envelope.get("motor"), str) or not envelope["motor"]:
        raise EnvelopeRecusado("motor precisa ser string não vazia")
    sha = envelope.get("sha256_arquivo_lido")
    if not isinstance(sha, str) or not _SHA256_HEX.match(sha):
        raise EnvelopeRecusado("sha256_arquivo_lido precisa ser string hexadecimal de 64 caracteres")

    controles = envelope.get("controles")
    if not isinstance(controles, dict):
        raise EnvelopeRecusado("controles precisa ser um objeto")
    campos_controles = set(ENVELOPE_SCHEMA["properties"]["controles"]["properties"])
    extras_controles = set(controles) - campos_controles
    if extras_controles:
        raise EnvelopeRecusado(f"controles declara campos fora do schema: {sorted(extras_controles)}")
    for campo in ENVELOPE_SCHEMA["properties"]["controles"]["required"]:
        if campo not in controles:
            raise EnvelopeRecusado(f"controles não declara o campo obrigatório {campo!r}")
    for campo in ("sum_vl_liquido",):
        if not isinstance(controles.get(campo), str):
            raise EnvelopeRecusado(f"controles.{campo} precisa ser string")
    for campo in ("min_vl_liquido", "max_vl_liquido"):
        if controles.get(campo) is not None and not isinstance(controles.get(campo), str):
            raise EnvelopeRecusado(f"controles.{campo} precisa ser string ou null")

    defeitos = envelope.get("defeitos")
    if not isinstance(defeitos, list):
        raise EnvelopeRecusado("defeitos precisa ser uma lista")
    campos_defeito = set(ENVELOPE_SCHEMA["properties"]["defeitos"]["items"]["properties"])
    for item in defeitos:
        if not isinstance(item, dict):
            raise EnvelopeRecusado("cada defeito precisa ser um objeto")
        extras_defeito = set(item) - campos_defeito
        if extras_defeito:
            raise EnvelopeRecusado(f"defeito declara campos fora do schema: {sorted(extras_defeito)}")
        for campo in ENVELOPE_SCHEMA["properties"]["defeitos"]["items"]["required"]:
            if campo not in item:
                raise EnvelopeRecusado(f"defeito não declara o campo obrigatório {campo!r}")
        if not isinstance(item.get("tipo"), str) or not item["tipo"]:
            raise EnvelopeRecusado("defeito.tipo precisa ser string não vazia")
        if not isinstance(item.get("valor_original"), str):
            raise EnvelopeRecusado("defeito.valor_original precisa ser string")
        if not _e_inteiro_json(item.get("posicao")) or item["posicao"] < 0:
            raise EnvelopeRecusado("defeito.posicao precisa ser inteiro não negativo")

    total_por_codigo = envelope.get("total_por_codigo")
    if not isinstance(total_por_codigo, dict):
        raise EnvelopeRecusado("total_por_codigo precisa ser um objeto")
    for codigo, valor in total_por_codigo.items():
        if valor is not None and not isinstance(valor, str):
            raise EnvelopeRecusado(f"total_por_codigo[{codigo!r}] precisa ser string ou null")


def _inteiro_estrito_nao_negativo(valor: Any, campo: str) -> int:
    # ADR 0009 / Regra 5: em Python 41572553.0 == 41572553 e False == 0 —
    # comparar por igualdade aceitaria float e booleano onde só inteiro vale.
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise EnvelopeRecusado(f"{campo} precisa ser inteiro não negativo, veio {valor!r}")
    if valor < 0:
        raise EnvelopeRecusado(f"{campo} precisa ser inteiro não negativo, veio {valor!r}")
    return valor


def _monetario_obrigatorio(valor: Any, campo: str, escala_maxima: int) -> Decimal:
    resultado = _monetario_opcional(valor, campo, escala_maxima)
    if resultado is None:
        raise EnvelopeRecusado(f"{campo} não pode ser omitido nem nulo")
    return resultado


def _monetario_opcional(valor: Any, campo: str, escala_maxima: int) -> Optional[Decimal]:
    """Converte um campo monetário do envelope, ou recusa antes de qualquer conversão.

    Aceita string (gramática do contrato) ou Decimal já construído (produtor
    externo integrado em Python — ADR 0006). Nunca aceita float nem bool: são
    recusados pelo TIPO, antes de qualquer tentativa de Decimal(str(v)), que
    apagaria a prova de que um float chegou onde só dinheiro-como-texto vale.
    `None` (o `null` do JSON) é a única representação de ausência aceita.
    """
    if valor is None:
        return None

    if isinstance(valor, bool):
        raise EnvelopeRecusado(f"{campo} veio como booleano — dinheiro nunca é bool")

    if isinstance(valor, float):
        raise EnvelopeRecusado(
            f"{campo} veio como float — dinheiro é string ou Decimal, nunca float (Regra 5)"
        )

    if isinstance(valor, str):
        if not _PADRAO_MONETARIO.match(valor):
            raise EnvelopeRecusado(
                f"{campo} não é uma string monetária válida: {valor!r} — "
                "negativo, notação científica e NaN/Infinity não casam com a gramática"
            )
        candidato = Decimal(valor)
    elif isinstance(valor, Decimal):
        candidato = valor
    else:
        raise EnvelopeRecusado(f"{campo} precisa ser string ou Decimal, veio {type(valor).__name__}")

    if not candidato.is_finite():
        raise EnvelopeRecusado(f"{campo} precisa ser finito, veio {valor!r}")
    if candidato < 0:
        raise EnvelopeRecusado(f"{campo} precisa ser não negativo (ADR 0009), veio {valor!r}")

    expoente = candidato.as_tuple().exponent
    casas = -expoente if isinstance(expoente, int) and expoente < 0 else 0
    if casas > escala_maxima:
        raise EnvelopeRecusado(
            f"{campo} tem {casas} casas decimais, além da escala do contrato ({escala_maxima})"
        )

    return candidato


def validar_envelope(
    envelope: dict,
    capacidade_leitura: CapacidadeLeitura,
    contrato,
) -> ResultadoValidacaoEnvelope:
    """Valida o envelope declarado pelo produtor contra a fronteira do contrato.

    Nunca importa nem inspeciona `envelope["motor"]` para decidir a regra —
    o mesmo caminho de validação vale para qualquer produtor (ADR 0006).

    Levanta `EnvelopeRecusado` quando:

    - o schema estrutural não bate (`ENVELOPE_SCHEMA`);
    - `sha256_arquivo_lido` está ausente ou diverge do hash que a leitura
      computou sobre os bytes que ela mesma abriu — inclusive quando o valor
      declarado é idêntico ao hash ancorado no contrato, mas a leitura leu
      outro arquivo;
    - `count_linhas` ou `linhas_invalidas` não são inteiros não negativos
      estritos (float e bool são recusados mesmo com o mesmo valor numérico);
    - qualquer campo monetário (os três controles globais e cada entrada de
      `total_por_codigo`) não é string/Decimal finito, não negativo e dentro
      da escala do contrato;
    - `linhas_invalidas` diverge da contagem de defeitos do tipo
      VALOR_ILEGIVEL (ADR 0008 — identidade colapsada não entra nessa conta);
    - os defeitos declarados divergem, por IDENTIDADE (tipo, valor original,
      posição), dos defeitos que a leitura observou — substituir um defeito
      por outro do mesmo tipo preserva contagem e tipo, mas não identidade;
    - a cardinalidade de `total_por_codigo` diverge da cardinalidade ANCORADA
      no contrato (medida na competência, nunca um número fixo);
    - algum código diverge, por VALOR EXATO (não quantizado), do total de
      referência que a leitura produziu para o mesmo código.
    """
    _validar_schema(envelope)

    escala = contrato.politica_decimal.escala
    escala_maxima = contrato.politica_decimal.escala_maxima_intermediarios

    sha_declarado = envelope.get("sha256_arquivo_lido")
    if not sha_declarado:
        raise EnvelopeRecusado("sha256_arquivo_lido ausente — a fronteira exige o hash do arquivo lido")
    if sha_declarado != capacidade_leitura.sha256_computado:
        raise EnvelopeRecusado(
            "sha256_arquivo_lido diverge do hash computado pela leitura sobre os bytes que ela "
            "de fato abriu — copiar o hash ancorado não substitui o vínculo com a leitura"
        )

    controles = envelope.get("controles") or {}
    count_linhas = _inteiro_estrito_nao_negativo(controles.get("count_linhas"), "controles.count_linhas")
    linhas_invalidas = _inteiro_estrito_nao_negativo(
        controles.get("linhas_invalidas"), "controles.linhas_invalidas"
    )
    sum_vl_liquido = _monetario_obrigatorio(controles.get("sum_vl_liquido"), "controles.sum_vl_liquido", escala)
    min_vl_liquido = _monetario_opcional(controles.get("min_vl_liquido"), "controles.min_vl_liquido", escala)
    max_vl_liquido = _monetario_opcional(controles.get("max_vl_liquido"), "controles.max_vl_liquido", escala)

    defeitos_brutos = envelope.get("defeitos") or []
    contagem_valor_ilegivel = sum(1 for d in defeitos_brutos if d.get("tipo") == VALOR_ILEGIVEL)
    if linhas_invalidas != contagem_valor_ilegivel:
        raise EnvelopeRecusado(
            f"controles.linhas_invalidas ({linhas_invalidas}) diverge da contagem de defeitos "
            f"{VALOR_ILEGIVEL} declarados ({contagem_valor_ilegivel}) — ADR 0008: identidade "
            "colapsada não entra nessa conta"
        )

    declarados = Counter(
        (d.get("tipo"), d.get("valor_original"), d.get("posicao")) for d in defeitos_brutos
    )
    referencia = Counter(
        (d.tipo, d.valor_original, d.posicao) for d in capacidade_leitura.defeitos
    )
    if declarados != referencia:
        raise EnvelopeRecusado(
            "os defeitos declarados divergem, por identidade, dos defeitos que a leitura "
            "observou — R-6: a conferência é por identidade, nunca por contagem e tipo"
        )

    total_bruto = envelope.get("total_por_codigo") or {}
    cardinalidade_ancorada = contrato.cardinalidade.codigos_distintos
    if len(total_bruto) != cardinalidade_ancorada:
        raise EnvelopeRecusado(
            f"total_por_codigo declara {len(total_bruto)} códigos, o contrato ancora "
            f"{cardinalidade_ancorada} (R-4/ADR 0004) — a cardinalidade é medida, nunca fixada"
        )

    total_por_codigo: dict[str, Optional[Decimal]] = {}
    for codigo, valor in total_bruto.items():
        total_por_codigo[codigo] = _monetario_opcional(
            valor, f"total_por_codigo[{codigo!r}]", escala_maxima
        )

    referencia_totais = capacidade_leitura.total_por_codigo
    if set(total_por_codigo) != set(referencia_totais):
        raise EnvelopeRecusado(
            "as chaves de total_por_codigo divergem do mapa de referência produzido pela leitura"
        )
    for codigo, valor in total_por_codigo.items():
        valor_referencia = referencia_totais[codigo]
        if valor != valor_referencia:
            raise EnvelopeRecusado(
                f"total_por_codigo[{codigo!r}] = {valor!r} diverge do valor exato de referência "
                f"({valor_referencia!r}) que a leitura produziu (R-3: prova-se por valor, não por forma)"
            )

    return ResultadoValidacaoEnvelope(
        competencia=envelope.get("competencia", ""),
        motor=envelope.get("motor", ""),
        sha256_arquivo_lido=sha_declarado,
        count_linhas=count_linhas,
        linhas_invalidas=linhas_invalidas,
        sum_vl_liquido=sum_vl_liquido,
        min_vl_liquido=min_vl_liquido,
        max_vl_liquido=max_vl_liquido,
        total_por_codigo=total_por_codigo,
    )
