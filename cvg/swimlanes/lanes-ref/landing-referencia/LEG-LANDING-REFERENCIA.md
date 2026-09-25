> Projetado de `LEG-LANDING-REFERENCIA.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `de1f5404b40e5f128709b1d735771cf15579acac24c77c45ad37b4da6967ef41`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-LANDING-REFERENCIA
seam_id: SEAM-LANDING-REFERENCIA
swimlane_id: LANE-LANDING-REFERENCIA
observable_state: Landing de referência
proof: Bytes relidos com o sha256 da prova.
requires:
- bronze com linhagem do landing
produces:
- referencia no landing
tasks:
- id: T-20260924-landing-referencia
  title: O dicionário e o glossário do INSS no landing, como vieram
  goal: Pôr no landing os bytes dos dois arquivos de referência do INSS, com prova de procedência — o
    primeiro passo do medalhão, que a especie v1 pulou. Para rodar testes, o ÚNICO comando liberado ao
    agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo> -k
    <cenarios>`.
  done_condition: src/produtor/landing_referencia.py copia os bytes dos dois .xlsx para o landing, prova,
    relê e confere; é idempotente; nunca sobrescreve; os testes de tests/test_landing_referencia.py passam.
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
  - T-20260924-bronze-nomeia-o-landing
  touches_paths: []
  creates_paths:
  - src/produtor/landing_referencia.py
  - tests/test_landing_referencia.py
  behavior:
  - id: B-1
    given: os arquivos dicionario-especies-beneficio.xlsx e glossario-beneficios-emitidos.xlsx num diretório
      de origem com CHECKSUMS.txt, e um destino
    when: landing_referencia.gravar(spark, origem, destino, arquivos) roda
    then: 'para cada arquivo: confere o sha256 dos bytes contra a linha do CHECKSUMS.txt (formato ''<sha256>  _raw/<arquivo>'',
      casada pelo NOME), e só então copia os bytes, SEM alterar nenhum, para <destino>/<nome sem extensão>/sha256=<sha256>/<arquivo>
      pelo FileSystem do Hadoop, grava ao lado a _PROCEDENCIA.json com arquivo, sha256, tamanho, origem
      e instante, relê os bytes gravados e confere o sha256; devolve GRAVADO por arquivo. O padrão do
      destino é s3a://landing/pda/referencia e o da origem é /dados/_raw. Uma segunda execução devolve
      INTEGRO sem regravar nada SÓ se os bytes E a _PROCEDENCIA.json existem e conferem entre si (sha256
      e tamanho).'
  - id: B-2
    given: uma origem ou um destino que não conferem
    when: landing_referencia.gravar roda
    then: 'sha256 divergente do CHECKSUMS.txt ou arquivo ausente devolvem NAO_MEDIDO sem gravar nada;
      no destino, objeto com bytes diferentes, bytes sem _PROCEDENCIA.json (tentativa interrompida) ou
      prova com sha256 ou tamanho divergente, ou prova existente SEM o arquivo, devolvem DIVERGE e NADA
      é sobrescrito nem apagado — nem a prova é recriada — a retomada é decisão do dono; os arquivos aceitos
      são só os dois nomeados — outro nome recusa. Cada arquivo é INDEPENDENTE e tem o seu resultado:
      um ausente ou recusado não desfaz nem impede o outro, e o resultado da chamada lista os dois. Nenhum
      cenário usa skip, xfail ou importorskip; os testes GRAVAM só em tmp_path, nunca no MinIO — LER o
      MinIO ou /dados/_raw é permitido onde o cenário pede, e MinIO indisponível FALHA o teste; a sessão
      Spark do teste é uma fixture de módulo ou sessão, e nenhuma função a para.'
  evals:
  - id: eval_1
    description: Bytes como vieram, com prova
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in grava_os_bytes_como_vieram
      prova_ao_lado_do_arquivo rele_e_confere_o_sha256; do python3 -m pytest --collect-only -q tests/test_landing_referencia.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_landing_referencia.py -k "grava_os_bytes_como_vieram or prova_ao_lado_do_arquivo
      or rele_e_confere_o_sha256"'
    verifies:
    - B-1
  - id: eval_2
    description: Idempotente e sem sobrescrever
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in segunda_execucao_integro_sem_regravar
      objeto_divergente_nao_sobrescreve bytes_sem_prova_diverge prova_sem_arquivo_diverge; do python3
      -m pytest --collect-only -q tests/test_landing_referencia.py -k "$c" 2>/dev/null | grep -q "::"
      || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_landing_referencia.py
      -k "segunda_execucao_integro_sem_regravar or objeto_divergente_nao_sobrescreve or bytes_sem_prova_diverge
      or prova_sem_arquivo_diverge"'
    verifies:
    - B-1
    - B-2
  - id: eval_3
    description: Recusas
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in sha256_divergente_nao_grava
      arquivo_ausente_nao_medido arquivo_fora_da_lista_recusa resultado_por_arquivo; do python3 -m pytest
      --collect-only -q tests/test_landing_referencia.py -k "$c" 2>/dev/null | grep -q "::" || { echo
      "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_landing_referencia.py
      -k "sha256_divergente_nao_grava or arquivo_ausente_nao_medido or arquivo_fora_da_lista_recusa or
      resultado_por_arquivo"'
    verifies:
    - B-2
  anti_patterns:
  - action: converter o .xlsx para CSV ou Parquet no landing
    reason: o landing guarda a fonte como veio
    instead: os bytes, iguais
  - action: sobrescrever um objeto existente
    reason: destrói a evidência
    instead: DIVERGE
  - action: ler de _raw em qualquer camada seguinte
    reason: o medalhão lê a camada anterior
    instead: só este módulo lê _raw
  do_not_touch:
  - _raw
  - contracts
  - cvg/docs/adrs
  - src/pda
  - src/ontologia
  - infra
  - src/medalhao/ontologia.py
  - src/medalhao/projecao_postgres.py
  - src/medalhao/bronze.py
  - tests/test_bronze.py
  - src/medalhao/especie.py
  - tests/test_especie.py
  rollback: Remover os dois arquivos criados.
  observability: referências recusadas por sha256
source_seam_sha256: 5b9e4ab4652a2661035ca7387787853f5b7d7ef517b3a5ef032f90727bac3ce7
---
# Landing de referência

## Observable proof

Bytes relidos com o sha256 da prova.

## Runnable leaves

- `T-20260924-landing-referencia` — O dicionário e o glossário do INSS no landing, como vieram: src/produtor/landing_referencia.py copia os bytes dos dois .xlsx para o landing, prova, relê e confere; é idempotente; nunca sobrescreve; os testes de tests/test_landing_referencia.py passam.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
