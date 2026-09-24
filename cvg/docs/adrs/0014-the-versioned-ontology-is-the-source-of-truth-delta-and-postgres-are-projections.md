---
adr: "0014"
status: accepted
date: 2026-09-24
ground: brownfield
converge_pass: 2
spec_ref: "R-2"
supersedes: ""
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0014 — the versioned ontology is the source of truth; Delta and Postgres are projections

> **Renumerado de 0010 para 0014 em 2026-09-24**, sem mudar a decisão: a linha `pds`
> já tinha um ADR 0010 (a média do benefício sobe entre 2025-12 e 2026-01), e as
> duas linhas foram reunidas. A receita da ontologia e as folhas seladas citam
> `ADR-0010-ONTOLOGIA-FONTE` — é este ADR; ficam como estavam, porque são histórico.

## Context

A fonte publica a descrição da espécie em 20 caracteres, e 11 descrições
cobrem 24 códigos — o defeito é identidade colapsada, não largura de campo
(ADR 0008, que substituiu o 0004; `CONFIRMED_SOURCE_DEFECT`). A
fábrica preserva o código e nunca funde — mas até aqui não tinha o **nome**
de cada espécie, só o texto cortado.

O INSS publica, no Portal de Dados Abertos, dois arquivos que dão esse nome:
o glossário dos benefícios emitidos (13 termos) e o dicionário de espécies
(código → nome). Estão em `_raw/` desde `51cc9f0`, em 444 com sha256 em
`CHECKSUMS.txt` (W-1).

O dono decidiu, em 2026-09-24, que a ontologia será consultada **fora do
Spark** — por agentes e BI —, e pediu um Postgres para isso.

## Decision

A ontologia é um **arquivo versionado**, `src/ontologia/beneficios-emitidos.yaml`,
e é a única fonte da verdade sobre conceitos e relações:

- as 14 colunas do CSV ligadas aos 13 termos do glossário **por posição**
  (as duas "Espécie", 12 e 13, são código e descrição truncada — ADR 0002;
  R-2 da tech-spec: leitura por posição declarada);
- as 65 espécies com o nome oficial do dicionário, byte a byte;
- cada espécie no seu grupo, **por referência** a `grupos_especie` do
  contrato — a ontologia não redefine grupos.

Delta (`silver/pda/especie`) e Postgres (`pda-postgres`) são **projeções**:
carregadas a partir da ontologia pela cadeia, e reconferidas linha a linha
contra ela. Nenhuma das duas é editada à mão.

O carregador reconfere a ontologia contra os bytes de `_raw/`: sha256
declarado, os 65 nomes, os 13 termos. Se o INSS publicar outro dicionário, o
sha256 acusa e o carregador recusa — a ontologia muda por tarefa nova, não
por ajuste do verificador (Regra 3).

## Rejected reading

**Postgres como fonte da verdade.** Editar conceitos direto no banco é mais
ágil, e foi oferecido ao dono como opção. Rejeitado: uma linha alterada no
banco não passa por costura, adversário, selo nem escopo — é exatamente o
furo da Regra 11, com dado no lugar de código. E não haveria o que
reconferir: a projeção seria o original.

**Corrigir a descrição da Silver com o nome oficial.** Rejeitado pela Regra 4:
o texto truncado é a prova do defeito da fonte. A tabela `especie` guarda os
dois — o nome oficial e o texto como veio.

**Classificar cada uma das 22 divergências de texto (abreviação ou
renomeação).** Adiado: é julgamento de negócio. A ontologia registra só o
fato medido — o texto da fonte confere ou não com o prefixo do nome oficial.

**Ligar coluna a termo pelo nome.** Rejeitado: os nomes divergem ("Vl
Líquido" × "Valor líquido", "Dt início validade" × "Data do início de
validade", "Sexo." × "Sexo"), e as duas "Espécie" têm cabeçalho idêntico
(ADR 0002). Só a posição distingue.

## Evidence

Medido em 2026-09-24 por `scripts/medir_dicionario.py` contra a Silver real
2026-01 (41.572.553 linhas) — reproduzível com
`docker compose -f infra/docker-compose.yml exec -T spark python3 scripts/medir_dicionario.py`.
O "43 de 65" dá o mesmo com a regra do prefixo com ou sem NFC e com `strip`
dos dois lados: nenhum nome do dicionário tem espaço nas pontas nem está fora
de NFC.

| Conferência | Resultado |
|---|---|
| códigos no dicionário × no dado | 65 = 65, nenhum sobrando |
| nome oficial cortado em 20 = texto do CSV | 43 de 65 |
| colapsos desfeitos pelo nome oficial | 11 de 11 |
| termos do glossário × colunas do CSV | 13 × 14 (Espécie duas vezes) |

sha256 dos bytes de origem:

```
fbd909cb40512559d5e934286f600fe042bbac37f409d0caddf90b252f2e62d7  _raw/dicionario-especies-beneficio.xlsx
a564f5d7235c944439f99eb6cc49748ab928798d3a89615057d490695915e2a9  _raw/glossario-beneficios-emitidos.xlsx
```

## Consequences

- Três costuras, nesta ordem: a ontologia com o carregador; a projeção
  Delta `especie`; a projeção Postgres.
- O Postgres é infra (`54e6d30`), credenciais só no `.env`, porta só em
  `127.0.0.1`.
- Quem consulta o Postgres lê uma cópia. A carga grava o sha256 da ontologia
  que a gerou; uma consulta pode saber de qual versão veio.
- `grupos_especie` continua no contrato. Rever onde o RMV (30, 40) cai — o
  dicionário o lista entre os Amparos — é decisão separada, com ADR próprio.
