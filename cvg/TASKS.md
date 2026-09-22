# As 7 tarefas — do BRD ao código

Competência 2026-01 do PDA/INSS. Cada tarefa nasceu de uma costura do Pass 3,
foi selada em Tier 1 no Pass 5, ganhou contrato de runtime no Pass 7, e foi
escrita por um agente no Pass 8.

**Todas em Sonnet** (lane NORMAL), sem intervenção — o roteamento por lane
escolheu sozinho.

---

## Quadro geral

| # | Tarefa | Depende de | Tent. | Tempo | Linhas | Módulo |
|---|---|---|---|---|---|---|
| 1 | `contrato-ancora` | — | 1 | 516s | 569 | `contrato.py` |
| 2 | `leitura-posicional` | 1 | 1 ⚠ | 604s | 539 | `leitura.py` |
| 3 | `agregacao-exata` | 2 | 1 | 441s | 434 | `agregacao.py` |
| 4 | `envelope-fronteira` | 3 | **2** | 1204s | 729 | `envelope.py` |
| 5 | `juizo-classifica` | 4 | 1 | 287s | 465 | `juizo.py` |
| 6 | `evidencia-packet` | 5 | 1 ⚠⚠ | 453s | 756 | `evidencia.py` |
| 7 | `orquestra-desfecho` | 6 | 1 | 605s | 872 | `orquestracao.py` |

⚠ = bloqueou antes por `path_policy=fail` e precisou de re-run.
**120 testes** no total, todos passando.

---

## 1 · `contrato-ancora` — a fábrica recusa construir sem prova

**Costura:** `SEAM-CONTRATO` · **Cria:** `src/pda/contrato.py`,
`tests/test_contrato.py`, `contracts/competencia-202601.yaml`

Carrega a âncora, a procedência, o layout posicional, a política decimal e os
defeitos conhecidos — e **devolve `NAO_MEDIDO`** quando falta prova, em vez de
gerar o número para desbloquear (Regra 2).

O que as rodadas do Pass 4 acrescentaram aqui:

| Objeção | Virou |
|---|---|
| R2-C3 | os **dois** hashes — ZIP e CSV — porque a âncora foi medida no CSV |
| R6-C4 | política que contradiz o ADR é **recusada**, não validada |
| R8-C9 | precisão conferida por **suficiência**, não por estar declarada |
| R10-C3 | a verificação de escala é de quem **recebe o valor**, não do carregador |
| R12-C4 | a contagem de colapsos entra no contrato |
| R14-C1 | float na própria âncora é recusado **antes de qualquer conversão** |
| R15-C2 | âncora não finita e contagem booleana também |

**Defesa em profundidade:** duas guardas independentes pegam o float. Testado
removendo uma (a outra pega) e as duas (`FAILED`).

---

## 2 · `leitura-posicional` — lê por posição, nunca por nome

**Costura:** `SEAM-LEITURA` · **Cria:** `src/pda/leitura.py`,
`tests/test_leitura.py`, `tests/fixtures/competencia-min.csv`

O cabeçalho traz `Espécie` **duas vezes**, nos índices 12 e 13. Ler por nome
perde uma das duas em silêncio (ADR 0002). A leitura distingue pelo **formato
medido**: índice 12 é sempre 2 dígitos, 13 é sempre textual — verificado nas
41.572.553 linhas, zero ambíguas.

| Objeção | Virou |
|---|---|
| R4-C3 | o gate pega a troca entre as duas colunas de cabeçalho **idêntico** |
| R10-C1 | gramática monetária **brasileira** — `'        1.621,00'`, não ponto decimal |
| R11-C5 | confere `chmod 444` **antes** de ler; hash antes/depois não prova proteção |
| R12-C3 | colapso é propriedade do **conjunto**: emitido ao fim da varredura |
| R14-C2 | negativo e fora-de-escala têm o **mesmo destino** do ilegível |

⚠ **Bloqueou uma vez** por criar `run_evals.sh` fora do `creates_paths`.

---

## 3 · `agregacao-exata` — soma sem perder centavo

**Costura:** `SEAM-AGREGACAO` · **Cria:** `src/pda/agregacao.py`,
`tests/test_agregacao.py`

Contexto decimal **próprio e completo** — precisão, arredondamento, `Emax`,
`Emin` e traps — porque `localcontext()` herda do global tudo que não for dito,
e uma biblioteca externa transformaria execução válida em `ERRO`.

| Objeção | Virou |
|---|---|
| R3-C4 | são **2 de contagem e 3 monetários**; só `sum` é soma |
| R7-C1 | a cardinalidade é **ancorada**, não os 51 da amostra (são 65) |
| R8-C10 | nenhum registro legível → extremos **ausentes**, não zero |
| R15-C1 | contexto completo aqui também, não só na leitura |

---

## 4 · `envelope-fronteira` — o contrato do produtor externo

**Costura:** `SEAM-FRONTEIRA` · **Cria:** `src/pda/envelope.py`,
`tests/test_envelope.py`

A costura que o Pass 4 mais endureceu — quase toda objeção das rodadas 5 a 15
caiu aqui. É a borda que um produtor Spark futuro atravessa (ADR 0006).

| Objeção | Virou |
|---|---|
| R5-C1 | float recusado **na fronteira**, antes de qualquer conversão |
| R5-C2 | defeito **omitido** é recusado — o juiz não aprova lista vazia |
| R7-C5 | conferência **por identidade**, não por contagem (A duplicado + B omitido) |
| R8-C6 | os dois mapas vêm de **origens distintas** — comparar consigo mesmo não prova |
| R11-C4 | domínio monetário **finito**; `NaN` e `Infinity` satisfazem o tipo |
| R14-C4 | contagens como inteiros — em Python `41572553.0 == 41572553` |

⚠ **Precisou de 2 tentativas**: a primeira gastou os 600s sem criar os testes.

---

## 5 · `juizo-classifica` — classifica, nunca corrige

**Costura:** `SEAM-JUIZO` · **Cria:** `src/pda/juizo.py`,
`tests/test_juizo.py`

Compara os cinco controles **individualmente** e classifica toda diferença.
Divergência em qualquer um **recusa mesmo classificada** — a classificação
explica, nunca autoriza (Regra 4).

| Objeção | Virou |
|---|---|
| R2-C4 | **exatamente uma** classificação: zero bloqueia e duas também |
| R15-C5 | a classificação vem do **contrato**, não do juízo |

**A objeção que impedia a fábrica de rodar.** A competência tem 11 colapsos
reais; sem declarar quem classifica, ou a execução travava com os controles
corretos, ou o juízo inventava — decisão de negócio sem autoridade.

---

## 6 · `evidencia-packet` — o pacote que reconstrói sem reexecutar

**Costura:** `SEAM-EVIDENCIA` · **Cria:** `src/pda/evidencia.py`,
`tests/test_evidencia.py`

O veredito é **rederivado** dos insumos, nunca lido do rótulo.

| Objeção | Virou |
|---|---|
| R3-C3 | as **classificações** entre os insumos da rederivação |
| R5-C3 | os **três** hashes — ancorado, observado e declarado |
| R6-C2 | `NAO_MEDIDO` decide pela **causa**, não pela falta de hash |
| R11-C2 | distingue **chave ausente** de `null` explícito |
| R15-C4 | JSON não tem `Decimal` → par declarado `{texto, tipo}` |

⚠⚠ **Bloqueou duas vezes** por criar `t.py` fora do escopo.

---

## 7 · `orquestra-desfecho` — quatro desfechos, pacote sempre

**Costura:** `SEAM-ORQUESTRACAO` · **Cria:** `src/pda/orquestracao.py`,
`tests/test_orquestracao.py`

Conduz do carregamento ao veredito, gravando pacote em **qualquer** caminho.
Nunca encerra o processo dentro de uma etapa.

| Objeção | Virou |
|---|---|
| R6-C5 | R-7 numa prova **conjunta**: centavo alterado + hash reancorado |
| R6-C6 | R-9 **não** é declarado coberto — relógio simulado não prova orçamento |
| R12-C1 | a autorização declara a competência **solicitada** |

---

## A prova contra o arquivo real

`scripts/rodar_fabrica.py` liga os sete módulos e lê os 11,7 GB. Não
reimplementa nada — se reimplementasse, o testado seria o script.

```
registros lidos    : 41.572.553
linhas inválidas   : 0
colapsos           : 11
códigos            : 65
sha256 inalterado  : True
duração            : 116s

veredito           : ACEITO
FABRICA=ACEITO
```

**E o juiz acusa.** Deslocando a âncora em **um centavo** — sem tocar em
`_raw/` — contra os mesmos 41,5 milhões de linhas:

```
veredito          : RECUSADO
causa             : DIVERGENCIA
autoriza publicar : False
```

Um centavo em 78,5 bilhões bloqueou a publicação. É o que R-7 exige, provado
contra dado real e não contra fixture.
