"""Leitura posicional da competência: extrai registros preservando bytes e defeito de origem.

Regra 4 (AGENTS.md): a leitura classifica, nunca corrige. Um valor monetário
malformado, fora de escala ou negativo tem o MESMO destino do ilegível — vira
linha inválida, nunca vira número silenciosamente ajustado.

ADR 0002: Espécie aparece duas vezes no cabeçalho (índices 12 e 13). Ler por
nome perderia uma das duas em silêncio; esta leitura é sempre posicional, e
confere o FORMATO medido de cada posição antes de aceitar os índices do
contrato — cabeçalho idêntico não distingue uma coluna trocada.

ADR 0004/0008: a coluna 13 é rótulo, nunca chave. Uma descrição que cobre mais
de um código emite defeito de identidade colapsada, medido no conjunto, nunca
por linha.

ADR 0007/0009: a soma por código roda em contexto decimal próprio e completo
— precisão, arredondamento, Emax, Emin e traps todos declarados dentro do
`with localcontext()`, porque um contexto global adverso não pode alterar o
resultado de uma leitura correta.
"""

from __future__ import annotations

import csv
import hashlib
import os
import re
import stat
import time
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Union

VALOR_ILEGIVEL = "VALOR_ILEGIVEL"
IDENTIDADE_COLAPSADA = "IDENTIDADE_COLAPSADA"

_PROTECAO_ESPERADA = 0o444

# Gramática monetária MEDIDA na fonte (ADR 0002): preenchimento à esquerda,
# ponto de milhar, vírgula decimal — nunca ponto decimal, nunca notação
# científica, nunca separador de milhar por sublinhado.
_PADRAO_MONETARIO_BR = re.compile(r"^-?\d{1,3}(\.\d{3})*,\d+$")

# Formato medido nas 41.572.553 linhas (ADR 0002/0008): a coluna do código é
# sempre só dígitos, largura 2 após strip; a da descrição é sempre textual.
_PADRAO_ESPECIE = re.compile(r"^\d{2}$")


class LeituraRecusada(Exception):
    """A leitura recusa começar ou prosseguir — nunca lê e corrige em silêncio."""


@dataclass(frozen=True)
class LinhaInvalida:
    identidade: int
    valor_original: str
    posicao: int


@dataclass(frozen=True)
class DefeitoIdentidadeColapsada:
    tipo: str
    descricao: str
    codigos: tuple


@dataclass
class ResultadoLeitura:
    sha256_antes: str
    sha256_depois: str
    registros_lidos: int
    total_por_codigo: dict
    linhas_invalidas: list
    defeitos_identidade_colapsada: list
    duracao_segundos: float


def _conferir_protecao_escrita(caminho: Path) -> None:
    # W-1: hash antes/depois não prova proteção — um arquivo em 0666 passa
    # nesse teste quando ninguém escreve durante a leitura. A proteção real é
    # o modo do arquivo, conferido ANTES de qualquer leitura começar.
    modo = stat.S_IMODE(os.stat(caminho).st_mode)
    if modo != _PROTECAO_ESPERADA:
        raise LeituraRecusada(
            f"{caminho} precisa estar chmod 444 antes da leitura (W-1) — veio {oct(modo)}"
        )


def _sha256(caminho: Path) -> str:
    digest = hashlib.sha256()
    with open(caminho, "rb") as bruto:
        for bloco in iter(lambda: bruto.read(1 << 20), b""):
            digest.update(bloco)
    return digest.hexdigest()


def _especie_valida(bruto: str) -> bool:
    return bool(_PADRAO_ESPECIE.match(bruto.strip()))


def _descricao_valida(bruto: str) -> bool:
    limpa = bruto.strip()
    return bool(limpa) and not limpa.isdigit()


def _converter_monetario(bruto: str, escala: int) -> Union[Decimal, None]:
    """Converte a gramática monetária BR medida na fonte, ou retorna None se ilegível.

    Nunca usa `Decimal(bruto)` direto: a fonte publica com vírgula decimal, e
    esse construtor aceitaria 'NaN', 'Infinity' ou notação científica como se
    fossem legíveis — exatamente os valores que o ADR 0004 exige recusar.
    """
    limpo = bruto.strip()
    if not _PADRAO_MONETARIO_BR.match(limpo):
        return None
    sem_milhar = limpo.replace(".", "")
    com_ponto = sem_milhar.replace(",", ".")
    try:
        valor = Decimal(com_ponto)
    except InvalidOperation:
        return None
    expoente = valor.as_tuple().exponent
    casas = -expoente if expoente < 0 else 0
    if casas > escala:
        return None
    if valor < 0:
        return None
    return valor


def ler_competencia(caminho_csv: Union[str, Path], contrato) -> ResultadoLeitura:
    """Lê a competência por posição, sem alterar a fonte e sem corrigir defeitos.

    Levanta `LeituraRecusada` se `caminho_csv` não estiver protegido (W-1), se
    o cabeçalho não tiver o total de colunas do contrato, ou se o formato
    medido de espécie/descrição não bater na posição declarada (colunas
    possivelmente trocadas — ADR 0002).
    """
    caminho_csv = Path(caminho_csv)
    _conferir_protecao_escrita(caminho_csv)

    inicio = time.monotonic()
    sha_antes = _sha256(caminho_csv)

    layout = contrato.layout
    posicoes = layout.posicoes
    idx_valor = posicoes["vl_liquido"]
    idx_especie = posicoes["especie"]
    idx_descricao = posicoes["descricao_especie"]

    politica = contrato.politica_decimal
    escala = politica.escala

    registros_lidos = 0
    linhas_invalidas: list[LinhaInvalida] = []
    total_por_codigo: dict[str, Decimal] = {}
    descricao_para_codigos: dict[str, set] = {}

    # Contexto decimal PRÓPRIO e COMPLETO (ADR 0007/0009): localcontext()
    # copia o contexto global vigente e tudo que não for sobrescrito aqui
    # ficaria herdado — por isso precisão, arredondamento, Emax, Emin e traps
    # são todos declarados, mesmo que o contexto ambiente seja hostil.
    with localcontext() as ctx:
        ctx.prec = politica.precisao
        ctx.Emax = 999999999
        ctx.Emin = -999999999
        for sinal in list(ctx.traps):
            ctx.traps[sinal] = False
        ctx.rounding = ROUND_HALF_EVEN

        with open(caminho_csv, encoding=layout.encoding, newline="") as arquivo:
            leitor = csv.reader(arquivo, delimiter=layout.separador)
            cabecalho = next(leitor)
            if len(cabecalho) != layout.total_colunas:
                raise LeituraRecusada(
                    f"cabeçalho tem {len(cabecalho)} colunas, contrato declara "
                    f"{layout.total_colunas}"
                )

            for numero_linha, linha in enumerate(leitor, start=1):
                bruto_especie = linha[idx_especie]
                bruto_descricao = linha[idx_descricao]

                if not _especie_valida(bruto_especie) or not _descricao_valida(bruto_descricao):
                    raise LeituraRecusada(
                        "formato medido nas posições 12/13 (dígitos vs. texto) não bate "
                        "com o índice declarado — colunas possivelmente trocadas (ADR 0002); "
                        "cabeçalho idêntico não é prova de posição"
                    )

                codigo = bruto_especie.strip()
                descricao = bruto_descricao.strip()
                descricao_para_codigos.setdefault(descricao, set()).add(codigo)

                bruto_valor = linha[idx_valor]
                valor = _converter_monetario(bruto_valor, escala)

                if valor is None:
                    linhas_invalidas.append(
                        LinhaInvalida(
                            identidade=numero_linha,
                            valor_original=bruto_valor,
                            posicao=idx_valor,
                        )
                    )
                else:
                    total_por_codigo[codigo] = total_por_codigo.get(codigo, Decimal(0)) + valor

                registros_lidos += 1

        quantum = Decimal("1." + "0" * escala) if escala > 0 else Decimal("1")
        total_por_codigo = {
            codigo: total.quantize(quantum) for codigo, total in total_por_codigo.items()
        }

    sha_depois = _sha256(caminho_csv)
    if sha_antes != sha_depois:
        raise LeituraRecusada("os bytes de origem mudaram durante a leitura")

    defeitos_colapso = [
        DefeitoIdentidadeColapsada(
            tipo=IDENTIDADE_COLAPSADA,
            descricao=descricao,
            codigos=tuple(sorted(codigos)),
        )
        for descricao, codigos in descricao_para_codigos.items()
        if len(codigos) > 1
    ]

    colapsos_esperados = getattr(contrato.cardinalidade, "colapsos", None)
    if colapsos_esperados is not None and len(defeitos_colapso) != colapsos_esperados:
        raise LeituraRecusada(
            f"colapsos medidos na leitura ({len(defeitos_colapso)}) divergem da "
            f"contagem que o contrato carrega ({colapsos_esperados}) — Regra 3: a "
            "expectativa não se ajusta ao resultado medido"
        )

    duracao = time.monotonic() - inicio

    return ResultadoLeitura(
        sha256_antes=sha_antes,
        sha256_depois=sha_depois,
        registros_lidos=registros_lidos,
        total_por_codigo=total_por_codigo,
        linhas_invalidas=linhas_invalidas,
        defeitos_identidade_colapsada=defeitos_colapso,
        duracao_segundos=duracao,
    )
