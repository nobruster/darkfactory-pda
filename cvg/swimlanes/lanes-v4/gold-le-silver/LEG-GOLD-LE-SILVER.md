> Projetado de `LEG-GOLD-LE-SILVER.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `7fafdc72bca620ed7571e1f00a88d9aff8ce66357615f8d701f07fc492ef15e7`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-GOLD-LE-SILVER
seam_id: SEAM-GOLD-LE-SILVER
swimlane_id: LANE-GOLD-LE-SILVER
observable_state: A Gold principal publicada nomeia a versão da Silver e o pacote da ingestão
proof: A Gold publica sem ler landing nem CSV, e a linhagem chega ao pacote ACEITO.
requires:
- bronze julgada
produces:
- gold principal publicada
tasks:
- id: T-20260923-gold-le-silver
  title: Gold principal a partir da versão da Silver
  goal: Tirar da Gold a leitura do arquivo inteiro.
  done_condition: Sobre a Silver INTEGRO cuja Bronze tem pacote ACEITO, a Gold principal publica fechando
    exato com a âncora sem ler landing nem CSV; sem essa linhagem, nada é publicado.
  effort: S
  profile: standard
  execution_backend: any
  required_tools:
  - git
  - bash
  - python3
  - pytest
  - docker
  depends_on:
  - T-20260923-ingestao-julgada
  touches_paths:
  - src/medalhao/gold.py
  - tests/test_gold.py
  creates_paths: []
  behavior:
  - id: B-1
    given: a Silver publicada INTEGRO e a Bronze que ela leu, com pacote ACEITO no commit
    when: a Gold principal roda pela entrada nova
    then: resolve UMA vez a versão da Silver, lê com versionAsOf, segue a versão da Bronze nos metadados
      da Silver e confere que o commit dessa Bronze nomeia um pacote ACEITO da mesma competência e do
      mesmo sha256 do CSV; agrega por código reusando agregar, confere exato contra os controles persistidos
      da Silver e a âncora, e publica pelo protocolo que já existe, com o userMetadata nomeando a versão
      da Silver e o pacote. NÃO abre a landing nem o CSV.
  - id: B-2
    given: uma Silver sem linhagem até um pacote ACEITO, ou com estado diferente de INTEGRO
    when: a Gold principal roda pela entrada nova
    then: devolve NAO_MEDIDO sem pacote ACEITO na linhagem e DIVERGE quando a soma não fecha, sem publicar
      nada; a entrada antiga continua existindo para os testes selados, e nenhum teste já existente de
      tests/test_gold.py é editado.
  evals:
  - id: eval_1
    description: Lê só a Silver e segue a linhagem
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in gold_le_so_a_silver
      nao_abre_landing_nem_csv linhagem_ate_pacote_aceito; do python3 -m pytest --collect-only -q tests/test_gold.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_gold.py -k "gold_le_so_a_silver or nao_abre_landing_nem_csv or linhagem_ate_pacote_aceito"'
    verifies:
    - B-1
  - id: eval_2
    description: Fecha exato e nomeia as versões
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in gold_da_silver_fecha_com_a_ancora
      commit_nomeia_silver_e_pacote; do python3 -m pytest --collect-only -q tests/test_gold.py -k "$c"
      2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest
      -q tests/test_gold.py -k "gold_da_silver_fecha_com_a_ancora or commit_nomeia_silver_e_pacote"'
    verifies:
    - B-1
  - id: eval_3
    description: Sem linhagem, nada publica
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in sem_pacote_aceito_nao_medido
      silver_nao_integra_nao_publica gold_soma_que_nao_fecha_diverge; do python3 -m pytest --collect-only
      -q tests/test_gold.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit
      1; }; done; python3 -m pytest -q tests/test_gold.py -k "sem_pacote_aceito_nao_medido or silver_nao_integra_nao_publica
      or gold_soma_que_nao_fecha_diverge"'
    verifies:
    - B-2
  anti_patterns:
  - action: chamar leitura.ler_competencia na Gold
    reason: é a leitura do arquivo inteiro que a decisão tirou daqui
    instead: confiar no pacote ACEITO da ingestão, pela linhagem
  - action: recalcular Bronze e Silver da landing
    reason: ignora a Silver publicada e perde a linhagem
    instead: ler a Silver por versionAsOf
  - action: editar um teste já existente de tests/test_gold.py
    reason: teste selado que precisa mudar denuncia mudança de comportamento
    instead: acrescentar a entrada nova e testes novos
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  - contracts
  - src/pda
  rollback: Reverter src/medalhao/gold.py e tests/test_gold.py ao commit assentado.
  observability: publicações da Gold sem versão da Silver no commit
source_seam_sha256: d332e6bb04f71dc13b190bd31813925be9648cdacc2268b6c5449d246e203171
---
# A Gold principal publicada nomeia a versão da Silver e o pacote da ingestão

## Observable proof

A Gold publica sem ler landing nem CSV, e a linhagem chega ao pacote ACEITO.

## Runnable leaves

- `T-20260923-gold-le-silver` — Gold principal a partir da versão da Silver: Sobre a Silver INTEGRO cuja Bronze tem pacote ACEITO, a Gold principal publica fechando exato com a âncora sem ler landing nem CSV; sem essa linhagem, nada é publicado.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
