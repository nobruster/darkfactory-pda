> Projetado de `LEG-RETIRA-REGRA-ANTIGA.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `f15622f21181cf5a474b7e1d75e99d460899dd8a0fccbbca0826c9db3b985f25`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-RETIRA-REGRA-ANTIGA
seam_id: SEAM-RETIRA-REGRA-ANTIGA
swimlane_id: LANE-RETIRA-REGRA-ANTIGA
observable_state: Suíte sem teste contraditório
proof: Guarda da lista e suíte verde.
requires: []
produces:
- suite coerente
tasks:
- id: T-20260924-retira-regra-antiga-limpeza
  title: Retirar o teste selado que codifica a regra antiga da limpeza
  goal: 'Deixar a suíte coerente com a regra aprovada: execução substituída e conferida tem o preparo
    apagado. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml
    exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.'
  done_condition: test_commit_seguido_de_outro_preserva não existe mais; os demais testes de tests/test_limpeza.py
    são exatamente os de antes e passam; um teste-guarda confere a lista de testes do módulo; o módulo
    inteiro passa.
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
  touches_paths:
  - tests/test_limpeza.py
  creates_paths: []
  behavior:
  - id: B-1
    given: o teste selado test_commit_seguido_de_outro_preserva, cujo cenário é idêntico ao de test_substituida_conferida_apaga
      com a expectativa oposta
    when: a regra aprovada — substituída e conferida apaga — vale
    then: test_commit_seguido_de_outro_preserva é RETIRADO do módulo, sem ser reescrito, porque reescrito
      seria uma duplicata de test_substituida_conferida_apaga, que já cobre o mesmo cenário com a expectativa
      nova; nenhuma outra função test_* do módulo muda; src/medalhao/limpeza.py fica FORA do escopo de
      escrita — o comportamento entregue governa, e o path_policy recusa qualquer escrita nele.
  - id: B-2
    given: o módulo depois da retirada
    when: é coletado e executado inteiro
    then: 'um teste-guarda, test_lista_de_testes_da_limpeza, confere que o módulo tem EXATAMENTE os testes
      test_apaga_preparo_de_execucao_publicada, test_publicada_intacta_depois, test_id_vazio_recusado,
      test_caminho_fora_do_preparo_recusado, test_execucao_nao_publicada_preserva, test_commit_revertido_preserva,
      test_outra_execucao_intacta, test_substituida_conferida_apaga, test_publicada_intacta_apos_limpar_substituida,
      test_revertida_preserva, test_sem_commit_preserva, test_execucao_ativa_preserva, test_prefixo_montado_de_partes_validadas
      e ele mesmo — nem um a mais, nem um a menos; os casos que a regra antiga ainda governa seguem preservando:
      revertida, sem commit, execução ativa; todos passam.'
  evals:
  - id: eval_1
    description: A regra nova governa o cenário
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in substituida_conferida_apaga
      publicada_intacta_apos_limpar_substituida; do python3 -m pytest --collect-only -q tests/test_limpeza.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_limpeza.py -k "substituida_conferida_apaga or publicada_intacta_apos_limpar_substituida"'
    verifies:
    - B-1
  - id: eval_2
    description: A lista de testes é exatamente a esperada
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in lista_de_testes_da_limpeza
      revertida_preserva sem_commit_preserva execucao_ativa_preserva; do python3 -m pytest --collect-only
      -q tests/test_limpeza.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
      exit 1; }; done; python3 -m pytest -q tests/test_limpeza.py -k "lista_de_testes_da_limpeza or revertida_preserva
      or sem_commit_preserva or execucao_ativa_preserva"'
    verifies:
    - B-2
  - id: eval_3
    description: O resto do módulo segue verde
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in apaga_preparo_de_execucao_publicada
      commit_revertido_preserva caminho_fora_do_preparo_recusado publicada_intacta_depois id_vazio_recusado
      execucao_nao_publicada_preserva outra_execucao_intacta prefixo_montado_de_partes_validadas; do python3
      -m pytest --collect-only -q tests/test_limpeza.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
      exit 1; }; done; python3 -m pytest -q tests/test_limpeza.py -k "apaga_preparo_de_execucao_publicada
      or commit_revertido_preserva or caminho_fora_do_preparo_recusado or publicada_intacta_depois or
      id_vazio_recusado or execucao_nao_publicada_preserva or outra_execucao_intacta or prefixo_montado_de_partes_validadas"'
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: reescrever test_commit_seguido_de_outro_preserva para esperar APAGADO
    reason: vira duplicata de um teste que já existe
    instead: retirar e manter a guarda da lista
  - action: mudar src/medalhao/limpeza.py para o teste antigo voltar a passar
    reason: desfaz a regra aprovada pelo dono
    instead: o comportamento entregue governa
  - action: retirar ou editar qualquer outro teste
    reason: a exceção é para exatamente um teste
    instead: a guarda confere a lista inteira
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  - contracts
  - src/pda
  rollback: Restaurar tests/test_limpeza.py do commit assentado.
  observability: testes selados que contradizem uma regra aprovada
source_seam_sha256: a878760508eedfa75361511b7b88d1be1f07cc02e7cb2da7f2f2dccfff795375
---
# Suíte sem teste contraditório

## Observable proof

Guarda da lista e suíte verde.

## Runnable leaves

- `T-20260924-retira-regra-antiga-limpeza` — Retirar o teste selado que codifica a regra antiga da limpeza: test_commit_seguido_de_outro_preserva não existe mais; os demais testes de tests/test_limpeza.py são exatamente os de antes e passam; um teste-guarda confere a lista de testes do módulo; o módulo inteiro passa.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
