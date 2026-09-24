---
adr: "0011"
status: accepted
date: 2026-09-22
ground: brownfield
converge_pass: 2
spec_ref: "R-1, R-5"
supersedes: ""
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0011 — competências are disjoint, so the lake total is the sum of approved anchors

## Context

O BRD nomeou `mode("overwrite")` como defeito: *"ela destrói a execução
anterior; não há como responder meses depois o que foi publicado"*. A fábrica
resolveu isso na **evidência** — pacote por `execucao_id`, nada sobrescreve
nada, e os dois pacotes de 2026-01 provam.

Mas a decisão de negócio é mais ampla: **os arquivos serão carregados de forma
incremental, não overwrite.** Cada competência acrescenta ao lago em vez de
substituí-lo.

Isso muda o que o juízo precisa responder. Hoje ele responde uma pergunta:

> *o agregado desta competência bate com a âncora desta competência?*

A carga incremental cria uma segunda:

> *o total do lago DEPOIS da carga bate com o que deveria ter?*

E a fábrica não responde a segunda.

## Decision

**As competências são disjuntas, e o total do lago é a soma das âncoras
aprovadas — não uma medição nova do lago.**

Medido nas seis competências disponíveis:

| após | linhas no mês | acumulado | soma acumulada |
|---|---|---|---|
| 2025-10 | 41.472.336 | 41.472.336 | 73.718.590.003,86 |
| 2025-11 | 41.643.003 | 83.115.339 | 149.724.645.214,99 |
| 2025-12 | 41.641.943 | 124.757.282 | 223.918.611.286,51 |
| 2026-01 | 41.572.553 | 166.329.835 | 302.440.363.848,63 |
| 2026-02 | 41.522.152 | 207.851.987 | 380.881.738.804,02 |
| 2026-03 | 41.719.140 | 249.571.127 | **459.653.295.372,74** |

A soma das seis partes é **idêntica** ao acumulado. Nenhum benefício aparece
em duas competências; cada arquivo é um recorte fechado de um mês.

Disso decorre que o gate do acumulado é **barato e exato**: somar âncoras já
aprovadas, sem varrer os 249 milhões de linhas do lago. Um lago que não bate
com essa soma tem registro a mais ou a menos, e isso é detectável sem remedir
a fonte.

**Este ADR não constrói esse gate.** Ele registra o fato que o torna possível
e a lacuna que ele fecharia. Construir é trabalho de plano próprio, contra o
envelope que a `SEAM-FRONTEIRA` já contrata.

## Rejected reading

**Que o total do lago exigisse remedir o lago.**

É a leitura conservadora: se o lago é a verdade publicada, confira o lago.
Medir 249 milhões de linhas leva minutos, e a cada competência nova cresce.

O que a mata é a disjunção medida. Se as competências fossem sobrepostas — um
benefício aparecendo em dois meses — a soma das partes divergiria do
acumulado, e só remedir resolveria. Elas não são: a soma fecha exatamente, nos
seis pontos.

E remedir o lago tem um defeito pior que o custo: mede **o que o pipeline
produziu**, não o que a fonte publicou. É o mesmo erro que o ADR 0001 rejeitou
ao recusar derivar a âncora do Parquet — um defeito comum às duas execuções
ficaria invisível.

## Evidence

```sh
python3 scripts/medir_incremental.py
```

observed output:

```
  soma das 6 competencias: 459653295372.74
  acumulado calculado    : 459653295372.74
  batem? True
```

E a não-sobrescrita, já implementada na evidência:

```sh
ls evidence/2026-01/*.json | wc -l
```

observed output:

```
2
```

Duas execuções da mesma competência — a real e a do teste de R-7 — coexistindo
por `execucao_id`. O defeito que o BRD nomeou no `mode("overwrite")` não se
repete aqui.

## Consequences

- O juízo continua julgando **por competência**. Uma execução de 2026-01
  devolve `ACEITO` comparando contra a âncora de 2026-01, e isso permanece
  correto.
- O gate do acumulado é trabalho **declarado e não feito**. Enquanto não
  existir, uma carga incremental pode perder ou duplicar uma competência
  inteira sem que nada acuse — a fábrica veria cada mês certo e o lago errado.
- A disjunção é **premissa medida**, não suposta. Se uma competência futura
  republicar registros de outra, a soma das partes deixa de fechar e este ADR
  precisa de sucessor.
- Junto com o ADR 0010, define o que falta para fechar a lacuna do ADR 0001:
  0010 mediu a variação **entre** competências, 0011 mede o **acumulado**
  delas. Os dois são fatos; nenhum é gate.
- Re-verify when: uma competência for republicada, ou a fonte mudar o recorte
  mensal — aí a disjunção precisa ser medida de novo.
