> Projetado de `LEG-VINCULA-PROCEDENCIA.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `d8f7aa099661b8a1d86a9226e24b5ab73f59a66dbffe0f6d934a903fffd7beb0`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-VINCULA-PROCEDENCIA
seam_id: SEAM-VINCULA-PROCEDENCIA
swimlane_id: LANE-VINCULA-PROCEDENCIA
observable_state: A partição tem _PROCEDENCIA.json com hash, manifesto e controles
proof: O vinculador só grava quando hash e conteúdo conferem; senão não grava nada.
requires: []
produces:
- procedencia vinculada
tasks:
- id: T-20260923-vincula-procedencia
  title: Vincular a partição da landing ao CSV de origem
  goal: Gravar ao lado da partição a prova de que ela veio do CSV declarado.
  done_condition: Com o CSV cujo sha256 é o do contrato e a partição cujo conteúdo é a transformação dele,
    _PROCEDENCIA.json é gravado e relido; em qualquer divergência nada é gravado.
  effort: S
  profile: standard
  execution_backend: any
  required_tools:
  - git
  - bash
  - python3
  - pytest
  - docker
  depends_on: []
  touches_paths: []
  creates_paths:
  - src/produtor/vincular_procedencia.py
  - tests/test_vincular_procedencia.py
  behavior:
  - id: B-1
    given: o CSV em _raw/, o contrato com procedencia.hash_csv_sha256 e o layout posicional, e a partição
      competencia=<c> sob particionamento.caminho do contrato
    when: o vinculador roda para a competência
    then: calcula o sha256 dos bytes do CSV em fluxo e, se diferir do contrato, devolve DIVERGE sem gravar
      nada; lê o CSV no motor pelas posições do layout, com o DecimalType da politica_decimal e ansi.enabled=true,
      nunca float; e compara com a partição o MULTICONJUNTO de (especie_codigo, especie_descricao, vl_liquido)
      — um exceptAll e a igualdade das contagens, que juntos provam a igualdade. Conferindo, grava _PROCEDENCIA.json
      no prefixo da partição com competência, nome e sha256 do CSV, o MANIFESTO de todo objeto de dado
      da partição — nome, tamanho e sha256 do conteúdo —, os cinco controles como texto e o id da execução;
      relê o arquivo gravado e confere. Nunca toca nos objetos de dado. Zero linhas lidas de qualquer
      lado é NAO_MEDIDO.
  - id: B-2
    given: uma partição que já tem _PROCEDENCIA.json
    when: o vinculador roda de novo
    then: se a prova nova é idêntica à gravada, devolve INTEGRO sem regravar; se diverge — objeto acrescentado,
      removido ou alterado —, devolve DIVERGE nomeando a diferença e NUNCA sobrescreve em silêncio a prova
      anterior.
  evals:
  - id: eval_1
    description: Hash e conteúdo provados antes de gravar
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in hash_divergente_nao_grava
      conteudo_divergente_nao_grava grava_manifesto_hash_e_controles rele_o_que_gravou; do python3 -m
      pytest --collect-only -q tests/test_vincular_procedencia.py -k "$c" 2>/dev/null | grep -q "::" ||
      { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_vincular_procedencia.py
      -k "hash_divergente_nao_grava or conteudo_divergente_nao_grava or grava_manifesto_hash_e_controles
      or rele_o_que_gravou"'
    verifies:
    - B-1
  - id: eval_2
    description: Nunca float, nunca vazio
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in valor_em_decimal_nunca_float
      zero_linhas_e_nao_medido; do python3 -m pytest --collect-only -q tests/test_vincular_procedencia.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_vincular_procedencia.py -k "valor_em_decimal_nunca_float or zero_linhas_e_nao_medido"'
    verifies:
    - B-1
  - id: eval_3
    description: Rodar de novo não apaga a prova
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in prova_identica_nao_regrava
      prova_divergente_nao_sobrescreve; do python3 -m pytest --collect-only -q tests/test_vincular_procedencia.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_vincular_procedencia.py -k "prova_identica_nao_regrava or prova_divergente_nao_sobrescreve"'
    verifies:
    - B-2
  anti_patterns:
  - action: regravar a partição ou chamar o produtor
    reason: o produtor grava com append e a competência duplicaria
    instead: provar sobre os objetos que já estão lá
  - action: calcular o hash e gravar sem comparar o conteúdo
    reason: hash certo sem vínculo com a partição não prova nada
    instead: comparar o multiconjunto antes de gravar
  - action: importar _ler_fonte de gravar_lago.py
    reason: é código sem Task-Spec (Regra 11)
    instead: ler o CSV pelo layout do contrato neste módulo
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  - contracts
  - src/produtor/gravar_lago.py
  rollback: Remover o _PROCEDENCIA.json; os objetos de dado nunca foram tocados.
  observability: competências sem _PROCEDENCIA.json
source_seam_sha256: 2b30ea2b5c5bbdbbcdd566390a434c911d47de0e28ebfd950f2b616afc427b96
---
# A partição tem _PROCEDENCIA.json com hash, manifesto e controles

## Observable proof

O vinculador só grava quando hash e conteúdo conferem; senão não grava nada.

## Runnable leaves

- `T-20260923-vincula-procedencia` — Vincular a partição da landing ao CSV de origem: Com o CSV cujo sha256 é o do contrato e a partição cujo conteúdo é a transformação dele, _PROCEDENCIA.json é gravado e relido; em qualquer divergência nada é gravado.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
