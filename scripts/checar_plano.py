"""Confere o PLANO antes de despachar o adversário — os defeitos que eu
mesmo introduzo ao corrigir.

Nasceu de um erro real: um regex que atualizava o piso dos evals casou o
`-k "$c"` do próprio laço em vez do seletor, e os nove viraram
`for c in $c` — um laço que itera sobre NADA. Laço vazio não reprova
ninguém: os nove evals passariam por vacuidade, que é exatamente o
defeito que o piso existe para pegar.

Peguei por sorte, lendo o relatório. Este script pega sempre.

Cinco rodadas seguidas o adversário achou defeito que eu tinha acabado de
criar. Ele custa ~15 minutos por rodada; isto custa um segundo.

Token: PLANO=OK|REPROVADO|ERRO
"""
import re
import sys
from pathlib import Path

import yaml

RECEITA = Path("cvg/swimlanes/medalhao-recipe.yaml")

LIMITE_ESFORCO = {"XS": 1, "S": 2, "M": 3, "L": 5}
SEIS = {"CONFIRMED_SOURCE_DEFECT", "CONFIRMED_LEGACY_DEFECT",
        "APPROVED_BEHAVIOR_CHANGE", "MODERN_DEFECT", "CONTRACT_AMBIGUITY",
        "UNRESOLVED"}


def main() -> int:
    if not RECEITA.is_file():
        print(f"  {RECEITA} não existe — rode da raiz do repositório",
              file=sys.stderr)
        print("PLANO=ERRO")
        return 1

    texto = RECEITA.read_text(encoding="utf-8")
    if not texto.strip():
        print("  receita vazia")
        print("PLANO=ERRO")
        return 1

    try:
        d = yaml.safe_load(texto)
    except yaml.YAMLError as e:
        print(f"  YAML inválido: {e}")
        print("PLANO=ERRO")
        return 1

    seams = d.get("seams") or []
    if not seams:
        # Regra 9: nada a conferir não é o mesmo que tudo certo
        print("  zero costuras na receita")
        print("  — nada a conferir não é o mesmo que tudo certo")
        print("PLANO=ERRO")
        return 1

    falhas = []

    for s in seams:
        sid = s.get("id", "<sem id>")
        for leg in s.get("swimlane", {}).get("legs", []):
            for t in leg.get("tasks", []):
                _tarefa(sid, t, falhas)

    _grafo(seams, falhas)
    _simetria(seams, falhas)

    print()
    if falhas:
        print(f"  {len(falhas)} problema(s):")
        for f in falhas:
            print(f"    {f}")
        print("PLANO=REPROVADO")
        return 1

    print(f"  {len(seams)} costuras, schema e evals íntegros")
    print("PLANO=OK")
    return 0


def _tarefa(sid, t, falhas):
    tid = t.get("id", "<sem id>")
    beh = t.get("behavior", [])
    evals = t.get("evals", [])
    anti = t.get("anti_patterns", [])
    cria = t.get("creates_paths", [])
    toca = t.get("touches_paths", [])
    esforco = t.get("effort", "?")

    print(f"  {sid} · {tid}")

    # contagens exatas — minItems e maxItems iguais no schema
    if len(beh) != 2:
        falhas.append(f"{tid}: behavior={len(beh)}, exige 2")
    if len(evals) != 3:
        falhas.append(f"{tid}: evals={len(evals)}, exige 3")
    if len(anti) != 3:
        falhas.append(f"{tid}: anti_patterns={len(anti)}, exige 3")

    limite = LIMITE_ESFORCO.get(esforco)
    if limite is None:
        falhas.append(f"{tid}: effort '{esforco}' desconhecido")
    elif len(cria) + len(toca) > limite:
        falhas.append(f"{tid}: {len(cria) + len(toca)} caminhos, "
                      f"{esforco} permite {limite}")

    ids_beh = {b.get("id") for b in beh}
    cobertos = set()

    for e in evals:
        eid = e.get("id", "?")
        bash = e.get("bash", "")

        for v in e.get("verifies", []):
            cobertos.add(v)
            if v not in ids_beh:
                falhas.append(f"{tid} {eid}: verifica {v} inexistente")

        _eval(tid, eid, bash, falhas)

    for b in sorted(ids_beh):
        if b not in cobertos:
            falhas.append(f"{tid}: behavior {b} sem eval que o cubra")


def _eval(tid, eid, bash, falhas):
    """O piso do eval precisa iterar sobre os cenários REAIS."""
    seletores = re.findall(r'-k "([^"]+)"', bash)
    if not seletores:
        falhas.append(f"{tid} {eid}: sem -k")
        return

    # o seletor de verdade é o último; o primeiro pode ser o "$c" do laço
    sel = seletores[-1]
    cenarios = [x.strip() for x in sel.split(" or ") if x.strip()]

    laco = re.search(r"for c in ([^;]+);", bash)
    if not laco:
        falhas.append(f"{tid} {eid}: sem laço de cobertura — um eval sem "
                      f"piso aprova obra pela metade")
        return

    itens = laco.group(1).split()

    # o defeito que motivou este script
    if any("$" in x for x in itens):
        falhas.append(f"{tid} {eid}: o laço itera sobre variável "
                      f"({' '.join(itens)}) — laço vazio não reprova ninguém")
        return

    if itens != cenarios:
        falhas.append(f"{tid} {eid}: laço tem {len(itens)} cenários e o -k "
                      f"tem {len(cenarios)} — divergem")
        return

    if len(cenarios) < 2:
        falhas.append(f"{tid} {eid}: só {len(cenarios)} cenário")

    print(f"    {eid}: {len(cenarios)} cenários, laço confere um a um")


def _simetria(seams, falhas):
    """A doutrina que vale numa camada vale nas outras.

    Três vezes o autor corrigiu a camada que o adversário apontou e
    deixou as outras — o mapa em Gold sem Bronze, o contexto decimal em
    Bronze e Gold sem Silver, a forma da capacidade em Bronze sem
    Silver. A rodada seguinte achou o que sobrou, todas as vezes.

    Este bloco mede a assimetria antes do despacho. Ele NÃO exige que
    toda camada diga tudo: exige que, quando a maioria diz, quem não diz
    apareça nomeado — para ser corrigido ou justificado.
    """
    # termo -> quem legitimamente pode não ter, e por quê
    ISENTAS = {
        "estado INTEGRO": {
            # Bronze lê o lago; não consome capacidade anterior
            "SEAM-BRONZE": "lê o lago, não consome capacidade anterior",
        },
    }

    TERMOS = ["FORMA declarada", "estado INTEGRO", "traps=[]",
              "uma das seis", "NO MOTOR", "ansi.enabled", "especie_codigo",
              "versionAsOf", "RELÊ", "replaceWhere",
              "mergeSchema", "RESTORE"]

    # A simetria vale entre as CAMADAS DE DADO do medalhão — são elas que
    # somam dinheiro, rodam no motor e trocam linhas entre si. Costura que
    # não é camada fica FORA, nomeada, com o motivo: isenção genérica
    # devolveria o mesmo furo com outro nome (Regra 11).
    CAMADAS = {"SEAM-BRONZE", "SEAM-SILVER", "SEAM-GOLD"}
    FORA = {
        "SEAM-CONTRATO-EXT": "estende o carregador do contrato; não soma "
                             "dinheiro, não roda no motor, não troca linhas",
    }
    for s in seams:
        sid = s.get("id")
        if sid not in CAMADAS and sid not in FORA:
            falhas.append(f"{sid}: costura nova sem classificação — é camada "
                          f"de dado ou fica fora da simetria? Declare em "
                          f"CAMADAS ou em FORA, com o motivo")

    corpos = {}
    for s in seams:
        sid = s.get("id", "?")
        if sid not in CAMADAS:
            continue
        texto = []
        for leg in s.get("swimlane", {}).get("legs", []):
            for t in leg.get("tasks", []):
                for b in t.get("behavior", []):
                    texto.append(str(b.get("then", "")))
                    texto.append(str(b.get("given", "")))
        # sem caixa: o plano grita ênfase em maiúsculas ("EXATAMENTE UMA
        # das seis"), e comparar com caixa acusou Gold de não ter o que
        # ele tinha desde a R3. Falso positivo — verificador que reprova à
        # toa corrói a confiança tanto quanto o que aprova à toa.
        corpos[sid] = " ".join(texto).lower()

    if len(corpos) < 2:
        return

    print()
    print("  simetria entre as camadas:")
    for s in seams:
        if s.get("id") in FORA:
            print(f"    -- {s.get('id')} fora da simetria: {FORA[s.get('id')]}")
    for termo in TERMOS:
        tem = {sid for sid, c in corpos.items() if termo.lower() in c}
        se_nao = set(corpos) - tem
        isentas = set(ISENTAS.get(termo, {}))
        faltam = se_nao - isentas

        marca = "ok " if not faltam else "!! "
        quem = ", ".join(sorted(s.replace("SEAM-", "") for s in tem)) or "—"
        print(f"    {marca}{termo:<18} em: {quem}")

        # TERMOS é a lista CURADA de doutrinas que valem em toda camada.
        # A primeira versão só acusava quando a maioria tinha e a minoria
        # não — e ficou cega para o caso mais comum do padrão que este
        # bloco existe para pegar: a correção introduzida em UMA camada.
        # Com "NO MOTOR" só em Silver, marcou "!!" e devolveu PLANO=OK.
        # Para doutrina curada, qualquer camada não isenta sem ela reprova.
        if faltam:
            falhas.append(
                f"assimetria: '{termo}' aparece em "
                f"{', '.join(sorted(tem))} e falta em "
                f"{', '.join(sorted(faltam))} — corrija ou declare a isenção")


def _grafo(seams, falhas):
    """Todo requires precisa de produtor, e nenhum estado com dois."""
    produz = {}
    for s in seams:
        for leg in s.get("swimlane", {}).get("legs", []):
            for p in leg.get("produces", []):
                produz.setdefault(p, []).append(leg.get("id"))

    for estado, quem in produz.items():
        if len(quem) > 1:
            falhas.append(f"estado '{estado}' tem {len(quem)} produtores: "
                          f"{', '.join(quem)}")

    for s in seams:
        for leg in s.get("swimlane", {}).get("legs", []):
            for r in leg.get("requires", []):
                if r not in produz:
                    falhas.append(f"{leg.get('id')} requer '{r}' — "
                                  f"sem produtor nesta receita")

    print()
    print(f"  grafo: {len(produz)} estado(s) produzido(s)")


if __name__ == "__main__":
    raise SystemExit(main())
