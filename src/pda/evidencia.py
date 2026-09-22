"""Pacote de evidência por execução: grava sem sobrescrever, rederiva sem confiar no rótulo.

Regra 3 (AGENTS.md): o veredito gravado no pacote (`veredito_gravado`) é
sempre RECALCULADO na leitura por `rederivar_veredito` — nunca lido do
rótulo. Um pacote onde só o rótulo foi trocado é detectado porque
`rederivar_veredito` nem olha esse campo: reconstrói o veredito a partir dos
cinco controles, dos três hashes (ANCORADO, OBSERVADO, DECLARADO), das
classificações, e dos PARES de listas/mapas de origens distintas (leitura x
envelope) gravados separadamente.

Regra 4: campos que a orquestração não percorreu ficam marcados com o
sentinela `CHAVE_AUSENTE` — nunca zerados nem omitidos por um `dict.get()`
que tornaria "chave ausente" e "valor null" indistinguíveis.

Regra 5: cada campo monetário é gravado como um PAR declarado — o tipo
Python recebido e o texto exato dos bytes — nunca normalizado para uma
string única. Isso é o que permite gravar um `Decimal('sNaN')` recusado sem
que o próprio gravador falhe: `str(Decimal('sNaN'))` não dispara nenhuma
operação aritmética, só formata.

`gravar_pacote` nunca reabre o pipeline (leitura/contrato/juízo) para
conferir o que grava — apenas registra os insumos que o chamador já produziu
e computa o veredito UMA VEZ, com a mesma função (`rederivar_veredito`) que
a leitura usará depois. Isso é o que torna a rederivação uma prova: escrita
e leitura passam pelo mesmo caminho de decisão, sem uma segunda lógica
paralela que pudesse divergir dela.
"""

from __future__ import annotations

import json
import time
import uuid
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from . import juizo as juizo_mod

CHAVE_AUSENTE = "__CHAVE_AUSENTE__"

ACEITO = "ACEITO"
RECUSADO = "RECUSADO"
ACEITO_SEM_ANCORA = "ACEITO_SEM_ANCORA"
ERRO = "ERRO"

VEREDITOS_TERMINAIS = frozenset({ACEITO, RECUSADO, ACEITO_SEM_ANCORA, ERRO})

CONTRATO_OK = "OK"
CONTRATO_NAO_MEDIDO = "NAO_MEDIDO"
CONTRATO_RECUSADO = "RECUSADO"


class EvidenciaRecusada(Exception):
    """O pacote não pode ser gravado ou rederivado com confiança — nunca ajustado em silêncio."""


def par_monetario(valor: Any) -> Optional[Dict[str, str]]:
    """Grava `valor` como o par (tipo recebido, texto exato) — nunca normalizado.

    `str(Decimal('sNaN'))` é formatação, não aritmética: não dispara o trap
    de InvalidOperation, então um Decimal recusado por ser sinalizante ainda
    pode ser gravado sem que o gravador em si falhe.
    """
    if valor is None:
        return None
    if isinstance(valor, bool):
        return {"tipo": "bool", "texto": str(valor)}
    if isinstance(valor, Decimal):
        return {"tipo": "Decimal", "texto": str(valor)}
    if isinstance(valor, float):
        return {"tipo": "float", "texto": repr(valor)}
    if isinstance(valor, int):
        return {"tipo": "int", "texto": str(valor)}
    if isinstance(valor, str):
        return {"tipo": "str", "texto": valor}
    return {"tipo": type(valor).__name__, "texto": str(valor)}


def _decimal_de_par(par: Any) -> Optional[Decimal]:
    if not isinstance(par, dict):
        return None
    texto = par.get("texto")
    try:
        candidato = Decimal(texto)
    except (InvalidOperation, TypeError, ValueError):
        return None
    return candidato


def _decimais_iguais(a: Optional[Decimal], b: Optional[Decimal]) -> bool:
    """Compara dois Decimal sem deixar um sNaN derrubar o gravador (Regra 5).

    `Decimal('sNaN') == outro` levanta `InvalidOperation` sob o contexto
    padrão — comparar é operação aritmética, ao contrário de formatar. Um
    sinalizante nunca é igual a nada, inclusive a si mesmo: é sempre
    divergência, nunca uma exceção que impeça de registrar a recusa.
    """
    if a is None or b is None:
        return False
    try:
        return bool(a == b)
    except InvalidOperation:
        return False


def _controles_batem(ancora: Any, agregado: Any) -> bool:
    if not isinstance(ancora, dict) or not isinstance(agregado, dict):
        return False
    for chave in ("count_linhas", "linhas_invalidas"):
        if ancora.get(chave, CHAVE_AUSENTE) != agregado.get(chave, CHAVE_AUSENTE):
            return False
    for chave in ("sum_vl_liquido", "min_vl_liquido", "max_vl_liquido"):
        va = _decimal_de_par(ancora.get(chave))
        vb = _decimal_de_par(agregado.get(chave))
        if not _decimais_iguais(va, vb):
            return False
    return True


def _totais_batem(totais_leitura: Any, totais_envelope: Any) -> bool:
    if not isinstance(totais_leitura, dict) or not isinstance(totais_envelope, dict):
        return False
    if set(totais_leitura) != set(totais_envelope):
        return False
    for codigo, par_leitura in totais_leitura.items():
        va = _decimal_de_par(par_leitura)
        vb = _decimal_de_par(totais_envelope.get(codigo))
        if not _decimais_iguais(va, vb):
            return False
    return True


def _identidade_defeito(defeito: dict) -> tuple:
    return (defeito.get("tipo"), defeito.get("valor_original"), defeito.get("posicao"))


def _defeitos_batem(defeitos_leitura: Any, defeitos_envelope: Any) -> bool:
    if not isinstance(defeitos_leitura, list) or not isinstance(defeitos_envelope, list):
        return False
    return Counter(map(_identidade_defeito, defeitos_leitura)) == Counter(
        map(_identidade_defeito, defeitos_envelope)
    )


def _classificacoes_ok(classificacoes: Any) -> bool:
    if classificacoes is None:
        return True
    if not isinstance(classificacoes, dict):
        return False
    return all(v in juizo_mod.CLASSIFICACOES_QUE_REGISTRAM for v in classificacoes.values())


def _hashes_batem(ancorado: Any, observado: Any, declarado: Any) -> bool:
    valores = (ancorado, observado, declarado)
    if any(v in (CHAVE_AUSENTE, None) for v in valores):
        return False
    return ancorado == observado == declarado


def _rederivar_julgamento(pacote: dict) -> Tuple[str, str]:
    """Rederiva o caminho normal (contrato medido, sem evento de falha).

    Compara os TRÊS hashes, os cinco controles, os dois pares de defeitos e
    de totais por código, e as classificações — todos gravados
    separadamente. Faltar qualquer um dos três hashes, ou eles divergirem
    entre si, já basta para recusar: dois hashes batendo e um terceiro
    ausente ou diferente não é aceitação (ver `tres_hashes`).
    """
    hash_ancorado = pacote.get("hash_ancorado", CHAVE_AUSENTE)
    hash_observado = pacote.get("hash_observado", CHAVE_AUSENTE)
    hash_declarado = pacote.get("hash_declarado", CHAVE_AUSENTE)

    ok = (
        _hashes_batem(hash_ancorado, hash_observado, hash_declarado)
        and _controles_batem(pacote.get("ancora_controles"), pacote.get("agregado_controles"))
        and _defeitos_batem(pacote.get("defeitos_leitura"), pacote.get("defeitos_envelope"))
        and _totais_batem(pacote.get("totais_leitura"), pacote.get("totais_envelope"))
        and _classificacoes_ok(pacote.get("classificacoes"))
    )
    if ok:
        return ACEITO, "JULGADO"
    return RECUSADO, "DIVERGENCIA"


def rederivar_veredito(pacote: dict) -> Tuple[str, str]:
    """Rederiva (veredito, causa) do `pacote` — nunca lê `pacote["veredito_gravado"]`.

    Precedência declarada (não deduzida), na ordem exigida pela tarefa:

    1. `contrato_status == NAO_MEDIDO` decide antes de qualquer outra coisa
       — mesmo com hash ancorado presente e nenhum observado produzido —
       e dá sempre ACEITO_SEM_ANCORA, causa NAO_MEDIDO (ADR 0005).
    2. `contrato_status == RECUSADO` (o terceiro caminho antecipado) exige a
       política recusada e a cláusula do ADR violada GRAVADAS — sem elas o
       pacote é malformado e a rederivação recusa, em vez de supor uma causa.
    3. Hash observado ausente COM evento de falha gravado é execução
       interrompida — ERRO — antes de qualquer comparação de controles.
    4. Só então o julgamento normal (`_rederivar_julgamento`).
    """
    contrato_status = pacote.get("contrato_status", CHAVE_AUSENTE)

    if contrato_status == CONTRATO_NAO_MEDIDO:
        return ACEITO_SEM_ANCORA, "NAO_MEDIDO"

    if contrato_status == CONTRATO_RECUSADO:
        if not pacote.get("politica_recusada") or not pacote.get("clausula_adr_violada"):
            raise EvidenciaRecusada(
                "pacote declara contrato RECUSADO sem a política recusada e a cláusula do "
                "ADR violada gravadas — a causa precisa vir com a prova, não só o rótulo"
            )
        return RECUSADO, "CONTRATO_RECUSADO"

    hash_observado = pacote.get("hash_observado", CHAVE_AUSENTE)
    evento_falha = pacote.get("evento_falha")
    if hash_observado in (CHAVE_AUSENTE, None) and evento_falha:
        return ERRO, "EXECUCAO_INTERROMPIDA"

    return _rederivar_julgamento(pacote)


def _agora_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _com_sentinela(valor: Any) -> Any:
    return CHAVE_AUSENTE if valor is CHAVE_AUSENTE else valor


def gravar_pacote(
    diretorio: Union[str, Path],
    *,
    competencia_solicitada: str,
    contrato_status: str,
    competencia_contrato: Any = CHAVE_AUSENTE,
    competencia_envelope: Any = CHAVE_AUSENTE,
    aprovador: Any = CHAVE_AUSENTE,
    aprovado_em: Any = CHAVE_AUSENTE,
    politica_decimal_modo: Any = CHAVE_AUSENTE,
    escala: Any = CHAVE_AUSENTE,
    politica_recusada: Optional[dict] = None,
    clausula_adr_violada: Optional[str] = None,
    hash_ancorado: Any = CHAVE_AUSENTE,
    hash_observado: Any = CHAVE_AUSENTE,
    hash_declarado: Any = CHAVE_AUSENTE,
    evento_falha: Optional[dict] = None,
    ancora_controles: Optional[Dict[str, Any]] = None,
    agregado_controles: Optional[Dict[str, Any]] = None,
    classificacoes: Optional[Dict[str, str]] = None,
    defeitos_leitura: Optional[List[dict]] = None,
    defeitos_envelope: Optional[List[dict]] = None,
    totais_leitura: Optional[Dict[str, Any]] = None,
    totais_envelope: Optional[Dict[str, Any]] = None,
    duracao_segundos: float = 0.0,
) -> Path:
    """Grava um pacote de evidência NOVO — nunca sobrescreve um existente (B-2).

    Cada chamada recebe um `execucao_id` próprio (uuid4) e grava em
    `diretorio/<competencia_solicitada>/<execucao_id>.json`; duas execuções
    da mesma competência produzem dois arquivos distintos que coexistem.
    """

    def _controles(bruto: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if bruto is None:
            return None
        return {
            "count_linhas": bruto.get("count_linhas", CHAVE_AUSENTE),
            "linhas_invalidas": bruto.get("linhas_invalidas", CHAVE_AUSENTE),
            "sum_vl_liquido": par_monetario(bruto.get("sum_vl_liquido")),
            "min_vl_liquido": par_monetario(bruto.get("min_vl_liquido")),
            "max_vl_liquido": par_monetario(bruto.get("max_vl_liquido")),
        }

    def _totais(bruto: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if bruto is None:
            return None
        return {codigo: par_monetario(valor) for codigo, valor in bruto.items()}

    pacote: Dict[str, Any] = {
        "competencia_solicitada": competencia_solicitada,
        "competencia_contrato": _com_sentinela(competencia_contrato),
        "competencia_envelope": _com_sentinela(competencia_envelope),
        "contrato_status": contrato_status,
        "contrato_validade": {
            "aprovador": _com_sentinela(aprovador),
            "aprovado_em": _com_sentinela(aprovado_em),
            "politica_decimal_modo": _com_sentinela(politica_decimal_modo),
            "escala": _com_sentinela(escala),
        },
        "politica_recusada": politica_recusada,
        "clausula_adr_violada": clausula_adr_violada,
        "hash_ancorado": _com_sentinela(hash_ancorado),
        "hash_observado": _com_sentinela(hash_observado),
        "hash_declarado": _com_sentinela(hash_declarado),
        "evento_falha": evento_falha,
        "ancora_controles": _controles(ancora_controles),
        "agregado_controles": _controles(agregado_controles),
        "classificacoes": classificacoes,
        "defeitos_leitura": defeitos_leitura,
        "defeitos_envelope": defeitos_envelope,
        "totais_leitura": _totais(totais_leitura),
        "totais_envelope": _totais(totais_envelope),
        "duracao_segundos": duracao_segundos,
    }

    veredito, causa = rederivar_veredito(pacote)
    pacote["veredito_gravado"] = veredito
    pacote["causa_gravada"] = causa

    execucao_id = uuid.uuid4().hex
    pacote["execucao_id"] = execucao_id
    pacote["gravado_em"] = _agora_iso()

    destino_dir = Path(diretorio) / competencia_solicitada
    destino_dir.mkdir(parents=True, exist_ok=True)
    caminho = destino_dir / f"{execucao_id}.json"
    if caminho.exists():
        raise EvidenciaRecusada(f"{caminho} já existe — gravar não sobrescreve (B-2)")

    caminho.write_text(json.dumps(pacote, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    return caminho


def ler_pacote(caminho: Union[str, Path]) -> dict:
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def listar_execucoes(diretorio: Union[str, Path], competencia_solicitada: str) -> List[Path]:
    destino_dir = Path(diretorio) / competencia_solicitada
    if not destino_dir.exists():
        return []
    return sorted(destino_dir.glob("*.json"))
