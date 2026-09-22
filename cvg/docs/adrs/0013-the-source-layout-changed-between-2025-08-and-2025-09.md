---
adr: "0013"
status: accepted
date: 2026-09-22
ground: brownfield
converge_pass: 2
spec_ref: "R-2, R-3"
supersedes: ""
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0013 — the source layout changed between 2025-08 and 2025-09

## Context

O ADR 0002 registrou que `Espécie` aparece **duas vezes** no cabeçalho, nos
índices 12 e 13, e que por isso as colunas são lidas por posição. Esse fato
foi medido em 2026-01.

Ao baixar competências mais antigas para dar base à série (ADR 0010), o
`medir_ancora.py` recusou 2025-07 e 2025-08 com `ANCORA=NAO_MEDIDO` — zero
linhas válidas — enquanto 2025-09 mediu normalmente. Mesmo script, mesma
coluna declarada.

Não era defeito do script. Era a fonte.

## Decision

**A fonte mudou de layout entre agosto e setembro de 2025.**

| | 2025-07 e 2025-08 | 2025-09 em diante |
|---|---|---|
| total de campos | **13** | **14** |
| `Espécie` | **uma** vez, índice 0 | **duas** vezes, índices 12 e 13 |
| `Vl Líquido` | índice **10** | índice **9** |
| `Dt início validade` | índice 12 | índice 11 |

A coluna `Espécie` saiu do começo e virou **duas** colunas no fim — o código
e a descrição truncada que o ADR 0008 classifica. É a mudança que criou o
defeito de identidade colapsada.

Disso decorre que **o layout é por competência, não do arquivo**. O contrato
já declara as posições; o que este ADR fixa é que elas **não valem para toda
a série**, e um contrato de 2026-01 aplicado a 2025-07 lê município no lugar
de dinheiro.

## Rejected reading

**Que o script estivesse quebrado**, por recusar dois arquivos que existem e
são legíveis.

É a suspeita imediata: dois de três falharam, com o mesmo comando. E eu
tinha acabado de corrigir um defeito real nos medidores, então havia
precedente para desconfiar do código.

O que a mata é o conteúdo da coluna. Na posição 9 de 2025-07 está
`02040-Al-Junqueiro` — um município. A gramática monetária o rejeita, e com
zero valores válidos o script devolve `NAO_MEDIDO`, que é o comportamento
que a Regra 9 exige. **O script agiu certo ao recusar**; a posição declarada
é que estava errada para aquele arquivo.

## Evidence

```sh
for c in 202507 202509; do
  head -1 "_raw/D.SDA.PDA.003.EMI.${c}.csv" | tr ';' '\n' | wc -l
done
```

observed output:

```
13
14
```

E o conteúdo da coluna 9 em cada um:

```sh
sed -n '2p' _raw/D.SDA.PDA.003.EMI.202507.csv | cut -d';' -f10
sed -n '2p' _raw/D.SDA.PDA.003.EMI.202509.csv | cut -d';' -f10
```

observed output:

```
02040-Al-Junqueiro
        1.518,00
```

O cabeçalho de 2025-07 traz `Espécie` no índice 0 e `Vl Líquido` no 10; o de
2025-09 traz `Vl Líquido` no 9 e `Espécie` duplicada em 12 e 13.

## Consequences

- O contrato declara o layout **por competência**. Um contrato de 2026-01
  aplicado a 2025-07 lê município no lugar de dinheiro — e a gramática
  monetária o recusa, o que é a proteção funcionando.
- O ADR 0002 permanece válido **para 2025-09 em diante**. Antes disso,
  `Espécie` é uma coluna só e não há identidade colapsada a classificar.
- O ADR 0008 (identidade colapsada) só se aplica ao layout novo. O defeito
  que ele classifica **nasceu** com a duplicação da coluna.
- A série do ADR 0010 pode incluir 2025-07 e 2025-08, desde que medidas com
  `--coluna-valor 10`. O número é comparável; o layout que o produz, não.
- ⚠️ **A fonte pode mudar de novo.** Nada garante que o layout de 2026-03
  valha para 2026-04. Um contrato por competência não é burocracia — é o que
  impede ler a coluna errada em silêncio.
- Re-verify when: qualquer competência nova for baixada. Conferir o cabeçalho
  antes de declarar a posição é mais barato que descobrir depois.
