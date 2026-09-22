---
adr: "0006"
status: accepted
date: 2026-09-21
ground: brownfield
converge_pass: 2
spec_ref: "R-1, R-5, R-7"
supersedes: "0005"
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0006 — the judge ships before the spark producer that it will judge

## Context

O ADR 0005 decidiu **qual motor julga** — Spark grava, Python puro confere —
e essa parte continua valendo. Mas ele foi além: na linha 90 declarou que
montar a infraestrutura *"faz parte do escopo, e entra como tarefa no plano
do Pass 3"*.

A receita das costuras diz o contrário, no `out_of_scope`: o carregamento ao
lago *"entra como plano próprio depois deste"*.

**Os dois não podem valer ao mesmo tempo.** Um planejador do Pass 3 que lesse
só o ADR montaria Spark; um que lesse só a receita não montaria. Esta é
exatamente a pergunta que um ADR existe para tirar da mesa.

A contradição foi levantada por um adversário cross-family em **três rodadas
seguidas** do Pass 4. Nas duas primeiras foi tratada como defeito de plano —
uma delas gerou a sétima costura. Na terceira ficou claro que nenhuma
correção de costura resolve: o que estava em conflito era a doutrina.

## Decision

**O juízo não tem dependência de Spark, e a ausência de infra não o impede
de ser construído nem de ser provado.**

É um fato sobre o terreno, verificável hoje: a receita inteira das sete
costuras não menciona `pyspark` nem `SparkSession`, e a âncora contra a qual
tudo é medido foi produzida por um script sequencial de Python puro, em 64
segundos sobre 41.572.553 linhas.

Disso decorre que o juízo e o produtor são **entregáveis separáveis**, e a
ordem entre eles é livre. A parte de escopo do ADR 0005 — que prendia a
infraestrutura ao mesmo plano — deixa de valer, e o `out_of_scope` da receita
passa a ser a leitura correta.

A separação de motores do ADR 0005 permanece intacta: ela é o *motivo* pelo
qual a ordem é livre.

## Rejected reading

**Que "os motores são separados" implicasse "a infra entra no mesmo plano".**

Foi a leitura que o próprio ADR 0005 registrou, e é plausível: se o juiz
existe para conferir o produtor, parece natural que os dois nasçam juntos.

O que a mata é a independência que o 0005 estabelece. Um juiz construído no
mesmo plano do produtor é escrito por quem já sabe como o produtor resolveu
cada caso — e passa a testar o que o produtor faz, não o que o contrato
exige. É a mesma razão pela qual o Pass 4 exige adversário de família
diferente: um revisor que compartilha os pontos cegos do autor confirma o
erro em vez de acusá-lo.

Construir os dois juntos **apagaria** a independência que o 0005 comprou.

## Evidence

A infra continua ausente nesta máquina:

```sh
python3 -c "import pyspark"
timeout 5 bash -c "</dev/tcp/localhost/9000"
```

observed output:

```
ModuleNotFoundError: No module named 'pyspark'
bash: connect: Connection refused
```

E o juízo não depende dela:

```sh
grep -rl "pyspark\|SparkSession" cvg/swimlanes/pda-recipe.yaml
python3 -c "import json; d=json.load(open('evidence/_ancora.json')); \
  print(d['count_linhas'], d['segundos'], d['medido_por'])"
```

observed output:

```
(vazio — a receita das 7 costuras não menciona Spark)
41572553 64 scripts/medir_ancora.py — independente do pipeline
```

A contradição em si, nos dois documentos:

```sh
sed -n '90,91p' cvg/docs/adrs/0005-*.md
sed -n '25,27p' cvg/swimlanes/pda-recipe.yaml
```

observed output:

```
⚠️ **A infra não existe nesta máquina.** Montá-la faz parte do escopo, e
entra como tarefa no plano do Pass 3.
---
    - O carregamento ao lago em Spark e MinIO. Não é incógnita - o ADR 0005
      decidiu que os motores são separados, e o juízo precisa existir antes
      de haver o que julgar. Entra como plano próprio depois deste.
```

## Consequences

- Planos do Pass 3 **não** incluem tarefa de Spark, MinIO ou escrita no lago.
  O `out_of_scope` da receita é a leitura correta; a linha 90 do ADR 0005
  está superseded por este.
- O produtor Spark entra como **plano próprio**, e nasce contra o envelope
  que a `SEAM-FRONTEIRA` já contrata — não contra o que o juiz por acaso
  aceita.
- Enquanto o produtor não existir, o juízo é exercido com envelope declarado.
  Isso **não** é um substituto da prova contra dado real: a fábrica continua
  sem ter julgado uma execução de produtor de verdade, e dizer o contrário
  seria verde pelo motivo errado.
- O carregamento atual segue rodando em paralelo, intocado (Regra 4).
- Re-verify when: o produtor Spark for construído, ou a infra subir nesta
  máquina — o que torna verificável a parte que hoje é só contrato.
