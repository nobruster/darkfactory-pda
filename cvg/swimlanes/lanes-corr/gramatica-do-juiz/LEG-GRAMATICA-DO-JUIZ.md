> Projetado de `LEG-GRAMATICA-DO-JUIZ.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `2c6bccb671ec74e856879e3933f6d96caac052c3164f671091bb15d6aad40855`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-GRAMATICA-DO-JUIZ
seam_id: SEAM-GRAMATICA-DO-JUIZ
swimlane_id: LANE-GRAMATICA-DO-JUIZ
observable_state: Gramática do juiz em Spark
proof: Veredito igual ao de pda.leitura em toda a tabela de casos.
requires: []
produces:
- gramatica do juiz em spark
tasks:
- id: T-20260924-gramatica-do-juiz
  title: A gramática do juiz, uma só, para os módulos Spark
  goal: Ter num módulo só a gramática monetária e o padrão de espécie que o juiz Python selado usa, expressos
    em Spark, para os três módulos do produtor pararem de divergir dele. Para rodar testes, o ÚNICO comando
    liberado ao agente é `docker compose -f infra/docker-compose.yml exec -T spark python3 -m pytest <arquivo>
    -k <cenarios>`.
  done_condition: src/produtor/gramatica.py dá, para cada caso da tabela, o MESMO veredito que pda.leitura;
    os testes de tests/test_gramatica.py passam.
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
  - src/produtor/gramatica.py
  - tests/test_gramatica.py
  behavior:
  - id: B-1
    given: os textos '1.518,00', '        1.518,00', '\t1,00', '\xa01,00' (NBSP, existe em latin-1), '1518,00',
      '1,5', '1,50', '1,500', '-5,00', '-0,00', '0,00', '1.62,00', 'abc', '', 'NaN', '1e3,00' numa coluna
      Spark, e a escala 2 do contrato
    when: gramatica.valor_decimal(coluna, precisao, escala) é aplicada, numa sessão com ANSI ligado
    then: 'cada linha dá o MESMO veredito que pda.leitura._converter_monetario(texto, escala), comparado
      com == de Decimal (o Spark não guarda o sinal do zero, e ''-0,00'' tem de dar igual por ==): tira
      das pontas os MESMOS caracteres que str.strip() tira no domínio latin-1 do contrato — espaço, \t,
      \n, \r, \x0b, \x0c, \x1c a \x1f, \x85 e \xa0 —, aplica a regex ^-?\d{1,3}(\.\d{3})*,\d+$, conta
      as casas decimais NO TEXTO antes do cast (o cast arredondaria ''1,500'' em vez de recusar) e recusa
      mais de ''escala'' casas, e recusa valor menor que zero: ''1,5'' vale 1.50, ''-5,00'' e ''1,500''
      são NULL, ''-0,00'' é aceito; o resultado é DecimalType(precisao, escala), nunca float. A ORDEM
      é a do juiz — gramática, casas, sinal — e só DEPOIS a precisão: valor inválido por qualquer das
      três é NULL e nunca chega ao cast, então ''-1.000,00'' com precisão 5 é NULL (inválido, como o juiz
      devolve None); só um valor VÁLIDO que não cabe em DecimalType(precisao, escala) — ''1.000,00'' com
      precisão 5 — faz a ação FALHAR com o erro do Spark (ANSI), nunca vira NULL. A regex fica exposta
      como constante do módulo.'
  - id: B-2
    given: códigos de espécie como '01', ' 01 ', '1', '001', 'ab', '' e nulo
    when: gramatica.especie_valida(coluna) é aplicada
    then: dá o mesmo veredito que pda.leitura._especie_valida (^\d{2}$ depois de tirar das pontas os mesmos
      caracteres de B-1), com nulo tratado como inválido; escala negativa recusa com ValueError antes
      de montar a expressão. A sessão do teste é uma fixture de escopo de módulo, com spark.sql.ansi.enabled=true,
      nunca parada pelo módulo. Nenhum cenário usa skip, xfail ou importorskip.
  evals:
  - id: eval_1
    description: O mesmo veredito do juiz
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in mesmo_veredito_do_juiz
      texto_com_espacos_nas_pontas nbsp_e_tab_como_o_juiz uma_casa_decimal_vale; do python3 -m pytest
      --collect-only -q tests/test_gramatica.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
      exit 1; }; done; python3 -m pytest -q tests/test_gramatica.py -k "mesmo_veredito_do_juiz or texto_com_espacos_nas_pontas
      or nbsp_e_tab_como_o_juiz or uma_casa_decimal_vale"'
    verifies:
    - B-1
  - id: eval_2
    description: O que o juiz recusa
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in negativo_invalido menos_zero_aceito_como_o_juiz
      casas_demais_invalido fora_da_precisao_falha negativo_fora_da_precisao_e_invalido escala_negativa_recusa;
      do python3 -m pytest --collect-only -q tests/test_gramatica.py -k "$c" 2>/dev/null | grep -q "::"
      || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_gramatica.py
      -k "negativo_invalido or menos_zero_aceito_como_o_juiz or casas_demais_invalido or fora_da_precisao_falha
      or negativo_fora_da_precisao_e_invalido or escala_negativa_recusa"'
    verifies:
    - B-1
    - B-2
  - id: eval_3
    description: Espécie e tipos
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in especie_mesmo_veredito_do_juiz
      resultado_decimal_nunca_float regex_exposta; do python3 -m pytest --collect-only -q tests/test_gramatica.py
      -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3
      -m pytest -q tests/test_gramatica.py -k "especie_mesmo_veredito_do_juiz or resultado_decimal_nunca_float
      or regex_exposta"'
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: copiar a regex para uma quarta constante solta
    reason: é a duplicação que criou a divergência
    instead: um módulo, importado pelos três
  - action: reimplementar o juiz no teste
    reason: o teste compararia a gramática com ela mesma
    instead: importar pda.leitura e comparar veredito a veredito
  - action: alterar pda.leitura
    reason: o juiz é selado e é o oráculo desta tarefa
    instead: o módulo Spark se ajusta ao juiz
  do_not_touch:
  - _raw
  - contracts
  - cvg/docs/adrs
  - src/pda
  - src/medalhao
  - src/ontologia
  - infra
  - src/produtor/spark_produtor.py
  - src/produtor/gravar_lago.py
  - src/produtor/vincular_procedencia.py
  - tests/test_produtor.py
  - tests/test_vincular_procedencia.py
  rollback: Remover os dois arquivos criados.
  observability: divergência de veredito entre Spark e juiz
source_seam_sha256: 26dddb9e15cf26297a58b4421c19d8d8bd71063812694e399b7c1a4e07afda7c
---
# Gramática do juiz em Spark

## Observable proof

Veredito igual ao de pda.leitura em toda a tabela de casos.

## Runnable leaves

- `T-20260924-gramatica-do-juiz` — A gramática do juiz, uma só, para os módulos Spark: src/produtor/gramatica.py dá, para cada caso da tabela, o MESMO veredito que pda.leitura; os testes de tests/test_gramatica.py passam.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
