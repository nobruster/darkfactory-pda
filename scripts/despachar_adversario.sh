#!/usr/bin/env bash
# Despacha o adversario do Pass 4 SEM poder atacar texto defasado.
#
# Nasceu de uma rodada desperdicada: a R17 leu lanes projetadas do compile
# da R15, porque eu reprojetei sem rodar a cadeia antes. O task-plan em
# /tmp era das 10:54 e a receita das 11:45. O adversario acusou, com
# razao, dois defeitos que eu ja tinha corrigido — no texto que ele NAO
# recebeu.
#
# Lembrar da ordem nao basta: eu esqueci. Aqui a ordem e o script.
#
#   1. checar_plano.py      o plano esta integro?
#   2. cadeia               map -> plan -> review -> compile, sobre a receita ATUAL
#   3. ponte                reprojeta as lanes do compile que acabou de rodar
#   4. impressao digital    as lanes contem o texto da receita? se nao, ABORTA
#   5. adversario
#
# Token: DESPACHO=OK|ABORTADO
set -u
cd "$HOME/darkfactory-pda" || exit 1
export PATH="$HOME/.local/bin:$PATH"
export CVG_TASKSPEC_BIN="$PWD/task-spec-3.8.1/bin/taskspec"
export CVG_SEAMWISE_BIN="$PWD/.bin/seamwise"

RODADA="${1:-?}"
RECEITA=cvg/swimlanes/medalhao-recipe.yaml
W=/tmp/ws-medalhao
LANES=cvg/swimlanes/lanes-medalhao

aborta() { echo "  $1"; echo "DESPACHO=ABORTADO"; exit 1; }

echo "=== 1. o plano ==="
python3 scripts/checar_plano.py > /tmp/plano.out 2>&1
tail -1 /tmp/plano.out | sed 's/^/  /'
grep -q "^PLANO=OK" /tmp/plano.out || aborta "o plano nao esta integro"

echo
echo "=== 2. a cadeia, sobre a receita ATUAL ==="
bash "$HOME/cadeia_medalhao.sh" > /tmp/cadeia.out 2>&1
grep -E "TASK_GRAPH=|INTACTA|MUDOU" /tmp/cadeia.out | sed 's/^/  /'
grep -q "TASK_GRAPH=READY" /tmp/cadeia.out || aborta "a cadeia nao chegou a READY"

echo
echo "=== 3. o task-plan e mais novo que a receita? ==="
TP=$(stat -c %Y "$W/seamwise/task-plan.json" 2>/dev/null || echo 0)
RC=$(stat -c %Y "$RECEITA")
echo "  task-plan $(date -d @"$TP" +%H:%M:%S)   receita $(date -d @"$RC" +%H:%M:%S)"
[ "$TP" -ge "$RC" ] || aborta "task-plan mais velho que a receita — compile defasado"

echo
echo "=== 4. a ponte ==="
python3 fabrica/ponte/lanes_para_converge.py \
  --de "$W/seamwise/swimlanes" --legs "$W/seamwise/legs" \
  --para "$LANES" 2>&1 | tail -1 | sed 's/^/  /'

echo
echo "=== 5. impressao digital: as lanes carregam o texto da receita? ==="
# Pega frases distintivas de cada costura na RECEITA e exige que estejam
# nas lanes. Se a projecao for de outro compile, alguma falta.
python3 - "$RECEITA" "$LANES" <<'PY' || aborta "as lanes nao carregam o texto da receita"
import pathlib, re, sys, yaml
d = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
# A projecao escreve os escalares no estilo YAML de aspa simples, que
# DOBRA a aspa interna: 'bronze conferido' vira ''bronze conferido''. A
# primeira versao deste guarda comparava sem normalizar e acusou lanes
# em dia de defasadas — falso positivo. Normaliza aspa e espaco.
def norm(s):
    return re.sub(r"\s+", " ", s.replace("''", "'")).strip()
lanes = norm(" ".join(p.read_text(encoding="utf-8")
                      for p in pathlib.Path(sys.argv[2]).glob("*/*.md")))
faltam = 0
for s in d["seams"]:
    t = s["swimlane"]["legs"][0]["tasks"][0]
    for b in t["behavior"]:
        then = str(b.get("then", ""))
        # as ultimas 60 letras do then — mudam a cada edicao
        amostra = norm(then)[-60:].strip()
        ok = amostra in lanes
        faltam += not ok
        print(f"  {'ok ' if ok else '!! '}{s['id']:<14} {b['id']}")
sys.exit(1 if faltam else 0)
PY

echo
echo "=== 6. o adversario — rodada $RODADA ==="
echo "  bytes: $(cat "$LANES"/*/*.md | wc -c)"
timeout 1200 converge/bin/cvg review --adversary codex --timeout 900 \
  --dir "$LANES" 2>&1 | tail -4 | sed 's/^/  /'
echo "DESPACHO=OK"
