---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-ESPECIE-SILVER
seam_id: SEAM-ESPECIE-SILVER
swimlane_id: LANE-ESPECIE-SILVER
observable_state: Tabela especie publicada e reconferida
proof: 65 linhas na competência real, 65 nomes distintos, multiconjunto 0/0.
requires:
- ontologia carregada
produces:
- especie na silver
tasks:
- id: T-20260924-especie-silver
  title: 'Tabela Delta especie: o nome oficial ao lado do texto da fonte'
  goal: Publicar, por competência, uma tabela Delta com cada código de espécie, o nome oficial da ontologia,
    o grupo e o texto que a fonte publicou, sem corrigir nada. Para rodar testes, o ÚNICO comando liberado
    ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo>
    -k <cenarios>`.
  done_condition: publicar_especie grava a tabela com uma linha por código da competência, reconfere o
    que gravou, e recusa sem gravar quando a Silver e a ontologia não conferem; os testes de tests/test_especie.py
    passam.
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
  - T-20260924-ontologia-versionada
  touches_paths: []
  creates_paths:
  - src/medalhao/especie.py
  - tests/test_especie.py
  behavior:
  - id: B-1
    given: a ontologia carregada e uma Silver Delta com especie_codigo e especie_descricao da competência
    when: publicar_especie(spark, ontologia, silver, destino, competencia) roda
    then: 'lê a Silver UMA vez, na versão V fixada no início (versionAsOf), e usa essa mesma leitura para
      conferir e calcular; grava em Delta, por replaceWhere da competência — que deixa as outras competências
      intactas —, numa tabela criada pela própria tarefa com o seu schema (não o _garantir_tabela da Silver),
      uma linha por código com: especie_codigo, nome_oficial, grupo, descricao_fonte (o texto da Silver
      COMO VEIO, espaços à direita inclusive, Regra 4), texto_fonte_confere_prefixo (verdadeiro quando
      descricao_fonte sem espaços à direita é igual aos 20 primeiros caracteres do nome oficial sem espaços
      à direita — medido: 43 de 65 na 2026-01, com ou sem NFC) e competencia; o commit leva em userMetadata
      a versão V, o sha256 da ontologia e um id_execucao; a reconferência lê o destino na versão do PRÓPRIO
      commit, achada pelo id_execucao no histórico, nunca a versão atual, e confere o multiconjunto nos
      dois sentidos contra o calculado, numa função reconferir_especie que acusa uma linha alterada. Sobre
      a Silver real de 2026-01 o resultado tem 65 linhas, 65 nomes oficiais distintos e 43 linhas com
      texto_fonte_confere_prefixo verdadeiro.'
  - id: B-2
    given: uma Silver que não confere com a ontologia, ou vazia
    when: publicar_especie confere antes de gravar
    then: 'recusa SEM gravar nada: código na Silver que a ontologia não tem, código da ontologia ausente
      da competência, código com mais de uma descrição na competência — cada um com o motivo e os códigos;
      competência sem nenhuma linha devolve NAO_MEDIDO (Regra 9); cada recusa afirma que o destino não
      ganhou versão nova. Os testes gravam só em tmp_path, nunca no MinIO; os cenários da Silver real
      leem o MinIO UMA vez, numa fixture de escopo de módulo, e gravam em tmp_path. Nenhum cenário usa
      skip, xfail ou importorskip: MinIO ou Silver indisponível FALHA o teste.'
  evals:
  - id: eval_1
    description: A tabela guarda os dois textos e fecha com a Silver
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in grava_nome_oficial_e_texto_da_fonte
      descricao_fonte_como_veio reconferencia_acusa_linha_alterada outra_competencia_intacta linhagem_no_commit;
      do python3 -m pytest --collect-only -q tests/test_especie.py -k "$c" 2>/dev/null | grep -q "::"
      || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_especie.py
      -k "grava_nome_oficial_e_texto_da_fonte or descricao_fonte_como_veio or reconferencia_acusa_linha_alterada
      or outra_competencia_intacta or linhagem_no_commit"'
    verifies:
    - B-1
  - id: eval_2
    description: Divergência recusa sem gravar
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in codigo_fora_da_ontologia_recusa
      codigo_ausente_recusa duas_descricoes_recusa competencia_vazia_nao_medido; do python3 -m pytest
      --collect-only -q tests/test_especie.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
      exit 1; }; done; python3 -m pytest -q tests/test_especie.py -k "codigo_fora_da_ontologia_recusa
      or codigo_ausente_recusa or duas_descricoes_recusa or competencia_vazia_nao_medido"'
    verifies:
    - B-2
  - id: eval_3
    description: A Silver real de 2026-01
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in especie_real_2026_01
      colapsos_desfeitos_pelo_nome; do python3 -m pytest --collect-only -q tests/test_especie.py -k "$c"
      2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest
      -q tests/test_especie.py -k "especie_real_2026_01 or colapsos_desfeitos_pelo_nome"'
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: sobrescrever especie_descricao da Silver com o nome oficial
    reason: o texto truncado é a prova do defeito da fonte (Regra 4)
    instead: guardar os dois lado a lado
  - action: escolher uma descrição quando o código tem duas
    reason: escolher é decidir em silêncio
    instead: recusar com o código e as descrições
  - action: gravar e só depois conferir a cobertura de códigos
    reason: publica uma tabela que a conferência reprovaria
    instead: conferir antes, gravar, e reconferir o gravado
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  - contracts
  - src/pda
  - infra
  - src/ontologia/beneficios-emitidos.yaml
  - src/medalhao/ontologia.py
  rollback: Remover os dois arquivos criados; a tabela especie de produção só é publicada fora do loop.
  observability: códigos de espécie que a ontologia não conhece
source_seam_sha256: 4252c9999bf37047bcabbc9dbf11b9b2be11befc420564e592104fe82db3f2dc
---
# Tabela especie publicada e reconferida

## Observable proof

65 linhas na competência real, 65 nomes distintos, multiconjunto 0/0.

## Runnable leaves

- `T-20260924-especie-silver` — Tabela Delta especie: o nome oficial ao lado do texto da fonte: publicar_especie grava a tabela com uma linha por código da competência, reconfere o que gravou, e recusa sem gravar quando a Silver e a ontologia não conferem; os testes de tests/test_especie.py passam.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
