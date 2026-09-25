---
adr: "0017"
status: accepted
date: 2026-09-25
ground: brownfield
converge_pass: 2
spec_ref: "R-2"
supersedes: ""
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0017 — delta practices: additive evolution by default, five-year retention, optimize after load

## Context

Publicar o `nome_oficial` na Gold (receita D) exigiu passar
`evolucao_aditiva=True` à mão: o padrão era `False` em 9 funções. O dono
pediu, em 2026-09-25: *"sempre ative schema evolution e outras melhores
práticas das camadas medalhão"*. A auditoria contra o KB
`.claude/kb/delta-lake/quick-reference.md` achou, além disso: três
configurações de sessão não declaradas, nenhuma retenção declarada em tabela
alguma, e nenhum `OPTIMIZE`.

## Decision

1. **Evolução de schema ligada por padrão, só aditiva.** As funções de
   entrada de cada camada passam a ter `evolucao_aditiva=True` por padrão.
   A guarda `bronze.verificar_evolucao` continua **antes** do `mergeSchema`:
   coluna nova entra; troca de tipo ou coluna removida é recusada e vira ADR
   novo. `bronze.publicar_competencia` mantém `False` — chamadas internas
   (preparos, `especie`) declaram o que querem.
2. **A sessão declara o que antes herdava:** `schema.autoMerge.enabled=false`,
   `retentionDurationCheck.enabled=true`, `replaceWhere.constraintCheck.enabled=true`,
   e as propriedades padrão de tabela nova.
3. **Retenção de 5 anos em toda tabela Delta** (`delta.logRetentionDuration`
   e `delta.deletedFileRetentionDuration` = `interval 1825 days`). Tabela nova
   ganha pela sessão (`spark.databricks.delta.properties.defaults.*`, medido
   em 2026-09-25 no Delta 3.2.1: a tabela nova recebe, a existente não muda e
   a reentrada não cria commit); tabela já publicada ganha por `ALTER TABLE`,
   idempotente.
4. **`OPTIMIZE` ao fim de cada carga**, com prova: multiconjunto e controles
   da versão anterior iguais aos da versão compactada.
5. **`VACUUM` só sob pedido explícito do dono**, e sempre respeitando os 5
   anos.

## Rejected reading

**`mergeSchema` livre ("schema evolution" sem guarda).** Aceitaria
`vl_liquido` virando `double` em silêncio (Regra 5).

**`VACUUM` ao fim de cada carga "para deixar estável".** Pedido do dono,
reconsiderado por ele mesmo: `VACUUM` é irreversível e, com 5 anos de
retenção, não apagaria nada hoje; com retenção curta, apagaria as versões
anteriores — que são evidência.

**Retenção declarada em cada `_garantir_tabela`.** Tocaria 8 módulos, e um
`ALTER` na reentrada quebraria `test_tabela_existente_reconhecida` (reentrar
não cria commit). A propriedade padrão da sessão resolve a tabela nova num
lugar só.

## Consequences

- Receita E: sessão e padrões na Bronze; padrão das entradas nas camadas;
  módulo de manutenção (retenção por `ALTER` e `OPTIMIZE` com prova).
- Dois testes da receita D que esperavam recusa sem o sinalizador mudam por
  exceção nomeada: agora a recusa só ocorre com `evolucao_aditiva=False`
  explícito.
