# Constraints (`CHECK` e `NOT NULL`)

> **Purpose**: Pôr a regra de domínio dentro da tabela, para que qualquer escritor — inclusive um futuro, que ninguém revisou — seja recusado
> **Confidence**: 0.95
> **MCP Validated**: 2026-09-23

## Overview

O Delta OSS impõe dois tipos de constraint em toda escrita:

- **`NOT NULL`** — declarado no schema, na criação. Escrita com `null` na
  coluna levanta `InvariantViolationException`.
- **`CHECK`** — expressão SQL booleana por linha. Ao **adicionar**, o Delta
  *"verifies that all existing rows satisfy the constraint before adding
  it"*; depois, toda escrita que viole é recusada inteira.

Ambos são **cerca**, não correção: a escrita falha, nada é ajustado. Isso é
a Regra 4 aplicada ao lago — o defeito aparece, não some.

## The Pattern

```python
# NOT NULL: declarado na criação (ver contract-table-bootstrap)
(DeltaTable.createIfNotExists(spark)
    .location(CAMINHO)
    .addColumn("competencia", "STRING", nullable=False)
    .addColumn("vl_liquido", "DECIMAL(14,2)", nullable=False)
    .partitionedBy("competencia")
    .execute())

# CHECK: domínio do contrato
spark.sql(f"""
  ALTER TABLE delta.`{CAMINHO}`
  ADD CONSTRAINT vl_liquido_nao_negativo CHECK (vl_liquido >= 0)
""")
spark.sql(f"""
  ALTER TABLE delta.`{CAMINHO}`
  ADD CONSTRAINT competencia_formato CHECK (competencia RLIKE '^[0-9]{{4}}-[0-9]{{2}}$')
""")
```

## Onde cada coisa aparece

| O quê | Onde |
|---|---|
| `CHECK` vigentes | `DESCRIBE DETAIL` e `SHOW TBLPROPERTIES` (`delta.constraints.<nome>`) |
| `NOT NULL` | `nullable=false` no schema da tabela |
| Efeito colateral | adicionar constraint **sobe o protocolo de escrita** da tabela |

⚠️ O protocolo subir significa que escritores Delta mais antigos deixam de
conseguir escrever. Numa fábrica com versão fixada (3.2.1), é irrelevante —
mas é mais um motivo para não misturar versões de Delta sobre a mesma tabela.

## A constraint é hipótese de domínio

"Valor não negativo" parece óbvio até a fonte trazer estorno. Antes de pôr
um `CHECK`, **meça a competência inteira** (Regra 9): se a fonte real tem
negativos legítimos, o `CHECK` recusaria o arquivo **correto** — o gate
calibrado contra a suposição. Se tem negativos ilegítimos, o `CHECK` na
silver os recusa, e a classificação deles (Regra 4) acontece **antes**,
na passagem bronze → silver, não por filtro calado.

| Camada | Constraints típicas |
|---|---|
| bronze | quase nenhuma — a bronze guarda o defeito como veio; `NOT NULL` só em metadados de ingestão |
| silver | `NOT NULL` do contrato, `CHECK` de domínio já medido |
| gold | `NOT NULL` nas chaves e totais; `CHECK` de coerência (ex.: `total >= 0` se o contrato assim diz) |

## Quick Reference

| Input | Output | Notes |
|-------|--------|-------|
| `ADD CONSTRAINT` com linha violando já gravada | erro; constraint não é criada | meça antes |
| escrita com uma linha violando | a escrita inteira é recusada | atômico |
| `DROP CONSTRAINT` | remove a cerca | é afrouxar o gate: ADR novo |

## Common Mistakes

### Wrong

```python
# filtrar para a constraint não reclamar — o defeito some sem registro
df.filter("vl_liquido >= 0").write.format("delta").mode("append").save(t)
```

### Correct

```python
invalidas = df.filter("vl_liquido < 0")
n = invalidas.count()
if n:
    registrar_classificacao(invalidas, "CONFIRMED_SOURCE_DEFECT")  # Regra 4
    raise SystemExit(f"{n} linhas negativas — classificadas, não gravadas na silver")
df.write.format("delta").mode("append").save(t)
```

## Related

- [schema-enforcement](schema-enforcement.md)
- [contract-table-bootstrap](../patterns/contract-table-bootstrap.md)
