---
id: T-20260924-ontologia-versionada
title: "Ontologia versionada dos benefícios emitidos, reconferida contra os bytes do INSS"
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: (none)
depends_on: []
supersedes: (none)
touches_paths: []
creates_paths: [src/ontologia/beneficios-emitidos.yaml, src/medalhao/ontologia.py, tests/test_ontologia.py]
source_note: "seamwise/legs/LEG-ONTOLOGIA.md#T-20260924-ontologia-versionada"
created: "2026-09-24T00:00:00Z"
tags: []
owner: (none)
priority: P2
severity: feature
due_date: (none)
precondition: (none)
blocked_reason: (none)
security_class: (none)
source_action_item: (none)
tracker_ref: (none)
execution_backend: any
signed_off: true
signed_off_by: nobru
signed_off_at: 2026-09-24T22:52:43Z
accepted: true
accepted_by: converge-loop
accepted_at: 2026-09-24T22:56:27Z
signed_off_sig: hmac-sha256-v3:85d3c104:08c0d6d57ecd2cd90dcd639dc9317027bab43f9336ee5d59d80ebda84bc640c3
accepted_tier: 1
accepted_attempt_id: 080f644d-8d29-4e82-aa6e-7e0cbc69e241
accepted_authorization_ref: hmac-sha256-v3:85d3c104:08c0d6d57ecd2cd90dcd639dc9317027bab43f9336ee5d59d80ebda84bc640c3
acceptance_record_digest: sha256:2d39704859ce6a10c028de5d10d13eae2d0e9020f33cec65d4bc8c7b6c7bd74e
---

# Ontologia versionada dos benefícios emitidos, reconferida contra os bytes do INSS

> **Why:** Ter num arquivo versionado os conceitos da fonte — colunas, termos do glossário, espécies com o nome oficial e o grupo de cada uma — e um carregador que só aceita a ontologia se ela confere com os bytes de _raw/. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Goal

Ter num arquivo versionado os conceitos da fonte — colunas, termos do glossário, espécies com o nome oficial e o grupo de cada uma — e um carregador que só aceita a ontologia se ela confere com os bytes de _raw/. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.

## Context

Intent DI-PDA-ONTOLOGIA; seam SEAM-ONTOLOGIA; swimlane LANE-ONTOLOGIA; capability leg LEG-ONTOLOGIA. Done condition: src/ontologia/beneficios-emitidos.yaml existe; carregar_ontologia devolve a ontologia com 14 colunas, 13 termos e 65 espécies quando ela confere com os dois .xlsx de /dados/_raw e com o contrato, e recusa em qualquer divergência ou ausência; os testes de tests/test_ontologia.py passam.

## Behavior

- **B-1** — GIVEN os bytes oficiais em /dados/_raw (dicionario-especies-beneficio.xlsx e glossario-beneficios-emitidos.xlsx, com sha256 em /dados/_raw/CHECKSUMS.txt) e o contrato contracts/competencia-202601.yaml com grupos_especie WHEN carregar_ontologia lê src/ontologia/beneficios-emitidos.yaml THEN devolve a ontologia com: as duas fontes e o sha256 de cada, que confere com o arquivo e com a linha do CHECKSUMS.txt — cujas linhas têm o formato '<sha256>  _raw/<arquivo>', casadas pelo NOME do arquivo, porque no contêiner o diretório é /dados/_raw; as 14 colunas do CSV, cada uma por POSIÇÃO de 0 a 13 com o cabeçalho e o termo do glossário que representa — o cabeçalho declarado de cada posição é IGUAL ao da primeira linha do CSV que o CONTRATO declara como fonte (contrato.procedencia.fonte, hoje _raw/D.SDA.PDA.003.EMI.202601.csv, achado em /dados/_raw pelo nome), lida com contrato.layout.encoding e contrato.layout.separador, e o total de colunas é contrato.layout.total_colunas — NUNCA o de todo CSV de _raw: medido em 2026-09-24, 2025-07 e 2025-08 têm OUTRO layout (13 colunas, uma só 'Espécie', na posição 0), e a ontologia descreve o layout do contrato; as posições 12 e 13 são as duas 'Espécie', com papel codigo e descricao_truncada (ADR 0002), e nenhuma ligação é feita pelo nome; os 13 termos com a descrição IGUAL à do glossário; as 65 espécies, código de 2 dígitos em texto, com o nome oficial IGUAL, caractere a caractere e sem normalização, ao texto extraído do dicionário (medido: nenhum dos 65 tem espaço nas pontas nem está fora de NFC), e o grupo de cada uma lido de contrato.grupos_especie.grupos, por referência. O atributo sha256 da ontologia é o sha256 do JSON canônico (chaves ordenadas, sem espaços) do conteúdo RESOLVIDO — fontes, colunas, termos, espécies com o grupo vindo do contrato —, para que uma mudança de grupo no contrato mude a versão. Os .xlsx são lidos só com a biblioteca padrão (zipfile e xml), sem openpyxl, porque o contêiner não tem rede.
- **B-2** — GIVEN uma ontologia, uma fonte ou um contrato que não conferem, ou que não foram lidos WHEN carregar_ontologia confere THEN recusa, nunca devolve ontologia parcial: sha256 divergente do arquivo ou do CHECKSUMS.txt, código a mais ou a menos que o dicionário, nome diferente do dicionário, código sem grupo ou em dois grupos, termo que o glossário não tem ou com descrição diferente, cabeçalho diferente do CSV na mesma posição, posição de coluna faltando ou repetida, carregar_contrato devolvendo a string NAO_MEDIDO ou grupos_especie ausente — cada caso com o motivo nomeado; um CSV de OUTRO layout em /dados/_raw não é motivo de recusa nem é lido; zero espécies lidas, zero termos lidos, o CSV da fonte do contrato ausente ou arquivo ausente devolvem NAO_MEDIDO, não OK (Regra 9). Os cenários de recusa usam cópias em tmp_path, nunca alteram /dados/_raw. Nenhum cenário usa skip, xfail ou importorskip, nem retorna antes de afirmar: fonte ausente no ambiente de teste FALHA o teste.

## Success Criteria

```bash
# eval_1: A ontologia real confere com o INSS e com o contrato
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in ontologia_real_confere sessenta_e_cinco_especies catorze_colunas_por_posicao sha256_cobre_os_grupos; do python3 -m pytest --collect-only -q tests/test_ontologia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_ontologia.py -k "ontologia_real_confere or sessenta_e_cinco_especies or catorze_colunas_por_posicao or sha256_cobre_os_grupos"'
}

# eval_2: Divergência recusa com motivo
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in sha256_divergente_recusa checksums_divergente_recusa nome_diferente_recusa codigo_sem_grupo_recusa codigo_em_dois_grupos_recusa termo_fora_do_glossario_recusa descricao_de_termo_diferente_recusa cabecalho_trocado_recusa posicao_repetida_recusa csv_de_outro_layout_ignorado; do python3 -m pytest --collect-only -q tests/test_ontologia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_ontologia.py -k "sha256_divergente_recusa or checksums_divergente_recusa or nome_diferente_recusa or codigo_sem_grupo_recusa or codigo_em_dois_grupos_recusa or termo_fora_do_glossario_recusa or descricao_de_termo_diferente_recusa or cabecalho_trocado_recusa or posicao_repetida_recusa or csv_de_outro_layout_ignorado"'
}

# eval_3: Ausência não é medição
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in dicionario_vazio_nao_medido fonte_ausente_nao_medido contrato_nao_medido_recusa le_xlsx_sem_dependencia; do python3 -m pytest --collect-only -q tests/test_ontologia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_ontologia.py -k "dicionario_vazio_nao_medido or fonte_ausente_nao_medido or contrato_nao_medido_recusa or le_xlsx_sem_dependencia"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "A ontologia real confere com o INSS e com o contrato"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Divergência recusa com motivo"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Ausência não é medição"
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2]
    terminal: true
    expected_duration_sec: 10
retry_policy:
  max_iterations: 15
  circuit_breaker_no_progress: 3
  on_terminal_failure: park_with_context
agent_contract:
  version: 2
  read: [intent, behavior, contract, guardrails]
  produce: [code, tests]
  required_tools: [git, bash, python3, pytest, docker]
  timeout_minutes: 30
  sandbox_type: host
  output_artifacts: []
  mcp_dependencies: []
  emit: [pass, fail, retry_with_reason, parked_with_context]
  backend_metadata: {}
```

## Exit Check

```bash
eval_1 && eval_2 && eval_3
```

## Rollback Plan

Remover os três arquivos criados; nada mais depende deles até a próxima tarefa.

## Observability Hooks

ontologia recusada por divergência com os bytes do INSS

## Anti-Patterns

- Do not ligar coluna a termo pelo nome do cabeçalho: os nomes divergem e as duas Espécie têm cabeçalho idêntico (ADR 0002); instead ligar pela posição de 0 a 13.
- Do not copiar os grupos de espécie para dentro da ontologia: duas fontes do mesmo fato divergem em silêncio; instead referenciar grupos_especie do contrato e conferir a cobertura.
- Do not corrigir ou abreviar o nome oficial para caber em 20 caracteres: o nome oficial é o que a ontologia acrescenta; o truncado já está na Silver; instead guardar o nome exatamente como o dicionário publica.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`
- `contracts`
- `src/pda`
- `infra`

## Open Questions

(none — this task is fully specified)
