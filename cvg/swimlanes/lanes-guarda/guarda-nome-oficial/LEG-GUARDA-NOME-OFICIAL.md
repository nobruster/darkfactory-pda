> Projetado de `LEG-GUARDA-NOME-OFICIAL.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `fb232e94552d6730343a3b3c8f617b63307c231777d0e89ebef1c7824d379618`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-GUARDA-NOME-OFICIAL
seam_id: SEAM-GUARDA-NOME-OFICIAL
swimlane_id: LANE-GUARDA-NOME-OFICIAL
observable_state: Guarda atualizada
proof: Um token no diff.
requires: []
produces:
- guarda atualizada
tasks:
- id: T-20260925-guarda-registra-nome-oficial
  title: A guarda dos testes selados registra a mudança autorizada na Gold
  goal: Registrar na guarda test_testes_leves.py a impressão nova de test_commit_carrega_a_forma, a única
    mudança autorizada pelo dono num teste selado da Gold. Para rodar testes, o ÚNICO comando liberado
    ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo>
    -k <cenarios>`.
  done_condition: Em tests/test_testes_leves.py muda EXATAMENTE o token 'commit_carrega_a_forma a48ab419462c1eba
    1' para 'commit_carrega_a_forma 942ea6bcdf6c9ad3 1', mais um comentário que nomeia a exceção; os testes
    da guarda passam.
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
  - tests/test_testes_leves.py
  creates_paths: []
  behavior:
  - id: B-1
    given: a guarda, que acusa test_gold.py::test_commit_carrega_a_forma porque a sua tupla literal ganhou
      'nome_oficial' por exceção nomeada (receita D)
    when: a tarefa atualiza a guarda
    then: 'dentro de _ANTES_GOLD, o token ''commit_carrega_a_forma a48ab419462c1eba 1'' passa a ''commit_carrega_a_forma
      942ea6bcdf6c9ad3 1'' — a impressão medida no contêiner, com o mesmo método da guarda (16 hex do
      sha256 do ast.dump, Python 3.10.12) —, e uma linha de comentário acima de _ANTES_GOLD registra a
      exceção: ''commit_carrega_a_forma: nome_oficial na tupla — DEC-NOME-OFICIAL-NA-GOLD, 2026-09-25''.
      As outras 47 impressões, _ANTES_ASSUNTOS, MODULOS, as funções de apoio e os quatro test_* da guarda
      ficam EXATAMENTE como estão.'
  - id: B-2
    given: a guarda atualizada
    when: a guarda roda
    then: test_corpo_das_funcoes_test_intacto passa, e continua acusando qualquer OUTRA mudança em test_gold.py
      ou test_gold_assuntos.py; test_mesmos_ids_coletados, test_nenhum_skip_ou_xfail e test_copia_isolada_do_cenario_base
      passam sem edição. Nenhum cenário usa skip, xfail ou importorskip.
  evals:
  - id: eval_1
    description: A guarda aceita a mudança registrada
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in corpo_das_funcoes_test_intacto
      mesmos_ids_coletados; do python3 -m pytest --collect-only -q tests/test_testes_leves.py -k "$c"
      2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest
      -q tests/test_testes_leves.py -k "corpo_das_funcoes_test_intacto or mesmos_ids_coletados"'
    verifies:
    - B-1
    - B-2
  - id: eval_2
    description: O resto da guarda igual
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in nenhum_skip_ou_xfail
      copia_isolada_do_cenario_base; do python3 -m pytest --collect-only -q tests/test_testes_leves.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_testes_leves.py -k "nenhum_skip_ou_xfail or copia_isolada_do_cenario_base"'
    verifies:
    - B-2
  - id: eval_3
    description: Tudo da guarda
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in corpo_das_funcoes_test_intacto
      nenhum_skip_ou_xfail; do python3 -m pytest --collect-only -q tests/test_testes_leves.py -k "$c"
      2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest
      -q tests/test_testes_leves.py -k "corpo_das_funcoes_test_intacto or nenhum_skip_ou_xfail"'
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: recalcular ou reescrever todas as impressões
    reason: apagaria a proteção sobre as outras 47
    instead: trocar só o token nomeado
  - action: afrouxar a comparação da guarda
    reason: 'Regra 3: nunca ajustar o verificador para passar'
    instead: registrar a mudança autorizada, e só ela
  - action: tirar test_gold.py de MODULOS
    reason: a guarda deixaria de proteger a Gold
    instead: manter MODULOS
  do_not_touch:
  - _raw
  - contracts
  - cvg/docs/adrs
  - src
  - infra
  - tests/test_gold.py
  - tests/test_gold_assuntos.py
  rollback: Reverter tests/test_testes_leves.py.
  observability: mudanças em teste selado registradas na guarda
source_seam_sha256: 2f14c70090d54bb2484e9079b8417f8e5f4970cc35a5cdfee5d3035a8683605b
---
# Guarda atualizada

## Observable proof

Um token no diff.

## Runnable leaves

- `T-20260925-guarda-registra-nome-oficial` — A guarda dos testes selados registra a mudança autorizada na Gold: Em tests/test_testes_leves.py muda EXATAMENTE o token 'commit_carrega_a_forma a48ab419462c1eba 1' para 'commit_carrega_a_forma 942ea6bcdf6c9ad3 1', mais um comentário que nomeia a exceção; os testes da guarda passam.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
