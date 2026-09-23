---
id: T-20260922-bronze-confere-ancora
title: "Ler a partição do lago e conferi-la contra a âncora"
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: (none)
depends_on: [T-20260923-contrato-expoe-particao]
supersedes: (none)
touches_paths: []
creates_paths: [src/medalhao/bronze.py, tests/test_bronze.py]
source_note: "seamwise/legs/LEG-BRONZE-REPRODUZ-ANCORA.md#T-20260922-bronze-confere-ancora"
created: "2026-09-22T00:00:00Z"
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
signed_off_at: 2026-09-23T16:28:16Z
accepted: true
accepted_by: converge-loop
accepted_at: 2026-09-23T17:18:01Z
signed_off_sig: hmac-sha256-v3:85d3c104:f083aa9f2e213f632862cec6951c19cdb57a87eb7e0260280d10af6db023d6d7
accepted_tier: 1
accepted_attempt_id: 6bd7903f-0bd5-4379-8608-1415852582dc
accepted_authorization_ref: hmac-sha256-v3:85d3c104:f083aa9f2e213f632862cec6951c19cdb57a87eb7e0260280d10af6db023d6d7
acceptance_record_digest: sha256:f3740ac9baa0a64b424daba531dfe0319c8f6c93c8ffeed824b6a7fb6c0de062
---

# Ler a partição do lago e conferi-la contra a âncora

> **Why:** Fazer a camada recusar nascer sobre dado que não bate.

## Goal

Fazer a camada recusar nascer sobre dado que não bate.

## Context

Intent DI-PDA-MEDALHAO; seam SEAM-BRONZE; swimlane LANE-BRONZE; capability leg LEG-BRONZE-REPRODUZ-ANCORA. Done condition: Os cinco controles da partição real batem com o contrato. Partição AUSENTE ou VAZIA devolve NAO_MEDIDO; partição MEDIDA que diverge em qualquer controle devolve DIVERGE — os dois são estados distintos e nenhum escreve camada, porque confundir ausência de medição com reprovação torna instável a interface que Silver consome. Os evals rodam DENTRO do contêiner pda-spark, que tem pytest e pyspark; montar esse ambiente é pré-requisito do HOST — infra/preparar-spark.sh — e NÃO é trabalho desta tarefa, porque o contrato de runtime nega rede ao agente e instalar qualquer coisa seria impossível por construção.

## Behavior

- **B-1** — GIVEN a partição JÁ GRAVADA na landing — o prefixo competencia=2026-01 sob s3a://landing/pda/beneficios-emitidos — a RAIZ que o contrato declara em particionamento.caminho, com a chave 'competencia'; lê SÓ a partição, nunca a raiz inteira, lido dali e nunca regerado a partir do CSV — e o contrato da competência, com a âncora de linhas e de soma medidas na fonte WHEN Bronze lê a partição THEN No caminho Spark, o Context do Python NÃO governa a aritmética — medido: com prec=3 e Emax=5 no Python, o Spark somou exato, e sum() promove decimal(14,2) a decimal(24,2) por conta própria. O que governa é o DecimalType do acumulador, declarado a partir da politica_decimal do contrato, e a sessão roda com spark.sql.ansi.enabled=true DECLARADO: em modo não-ANSI, o estouro do acumulador devolve NULL sem erro, que é o Infinity da Regra 5 com outro nome. O Context(prec, rounding, traps=[], Emax, Emin) vale para o que roda em Python fora do motor. Os cinco controles, o mapa por código e o fechamento rodam NO MOTOR, sobre as 41.572.553 linhas, sem coletar — só os agregados saem do motor, e as linhas entregues a Silver são uma relação materializada, não uma coleção em memória. a contagem e a soma são recalculadas SOBRE A PARTIÇÃO, nunca sobre a união das partições — um agregado sem GROUP BY na coluna de partição não mede partição nenhuma, e foi assim que a leitura da união deu 41.622.553 contra a âncora de 41.572.553 e uma contaminação inexistente foi reportada, quando a partição real batia exato e as 50.000 linhas estavam em competencia=fatia-teste, isolada. A soma é feita com a precisão DECLARADA no contrato, jamais herdada do contexto global, como o ADR 0009 exige — e o contexto é construído INTEIRO a partir da politica_decimal do contrato, Context(prec, rounding, traps=[], Emax, Emin), porque declarar só a precisão deixa traps e limites de expoente virem do DefaultContext, que é mutável: com Emax baixo a soma vira Infinity e traps=[] silencia o Overflow que denunciaria, porque qualquer biblioteca importada pode alterar o contexto e o acumulador passaria a perder centavos sem que uma linha deste código mude. Os CINCO controles da âncora são comparados INDIVIDUALMENTE, como a R-5 da tech-spec exige — count_linhas, sum_vl_liquido, min_vl_liquido, max_vl_liquido e linhas_invalidas. Contagem e soma sozinhas não bastam, e não bastam nem juntas: uma alteração COMPENSADA entre duas linhas preserva as duas e ainda assim empurra o máximo acima dos 183.725,76 ancorados, com todos os valores finitos, não negativos e na escala permitida. Silver preservaria a soma e Gold compararia soma e cardinalidade; nenhuma das três veria. Bronze PRODUZ o mapa total_por_codigo — soma exata não quantizada, por código — e ele é parte declarada de 'bronze conferido'. É a ORIGEM do mapa: quem lê o Parquet é quem sabe qual valor pertence a qual código, e uma camada posterior que o recalcule a partir dos mesmos bytes repetiria um erro de atribuição nos dois lados da comparação, aprovando-o. Cada controle que diverge é nomeado na saída, porque saber QUAL falhou é o que separa investigar de adivinhar — e cada diferença recebe EXATAMENTE UMA das seis classificações da R-6 (CONFIRMED_SOURCE_DEFECT, CONFIRMED_LEGACY_DEFECT, APPROVED_BEHAVIOR_CHANGE, MODERN_DEFECT, CONTRACT_AMBIGUITY, UNRESOLVED). DIVERGE é estado de MEDIÇÃO, não classificação: recusar a partição corretamente e entregar diagnóstico sem classificação deixaria a diferença sem dono. Diferença que a camada não saiba classificar recebe UNRESOLVED, que é uma das seis e BLOQUEIA — nunca fica em branco. O tipo monetário da ENTRADA é recusado se não for decimal — a R-4 manda recusar float, nunca convertê-lo, e converter apaga a evidência da entrada proibida: Decimal(str(1.25)) devolve 1.25, finito, não negativo e na escala 2, satisfazendo todas as verificações de domínio enquanto a origem era um DOUBLE. A recusa é do TIPO declarado no esquema do Parquet, antes de ler valor algum. Só então a comparação monetária é entre Decimal e Decimal, e a igualdade é exata — tolerância aqui seria a Regra 3 pelo avesso, afrouxar o oráculo para a camada passar. Todo valor lido é conferido contra o domínio monetário do contrato antes de entrar no acumulador — finito, NÃO NEGATIVO e dentro da escala declarada. A não-negatividade não é preferência, e sim a premissa de soma MONOTÔNICA sob a qual o ADR 0009 deriva a precisão 14 — um valor negativo quebra a premissa e a perda de centavo passa a acontecer DURANTE a soma, onde a comparação final não a enxerga. Bronze lê Parquet, que não passa nem pela gramática do CSV nem pela fronteira do envelope, e por isso é uma TERCEIRA porta de entrada para valores; fechá-la é obrigação desta camada. Valor fora do domínio é defeito classificado com identidade, valor original e posição, nunca somado em silêncio. A posição é a do LAGO — o objeto Parquet e o ordinal da linha dentro dele —, nomeada assim, porque o Parquet não carrega a linha do CSV e uma numeração inventada fingiria localizar a origem. Ela nunca preenche o campo posicao do envelope, que é a linha do CSV: com defeito de domínio Bronze não fica INTEGRO, e sem INTEGRO não há envelope. A procedência do arquivo que originou a partição é APRESENTADA a Bronze junto da leitura — hoje pelo pacote que a gravação emite, não por coluna do Parquet, porque MEDIDO em gravar_lago.py a partição tem três colunas mais a de partição e nenhuma é procedência; exigir que ela viesse do Parquet faria Bronze devolver NAO_MEDIDO na partição CORRETA, que é o defeito da Regra 9 pelo avesso. Quando apresentada, o hash_csv_sha256 é comparado com o ancorado e divergência é DIVERGE, porque reproduzir os dois controles não distingue o arquivo ancorado de outro com os mesmos totais, e a âncora vale para UM arquivo. Fazer a partição carregar a procedência é melhoria desejável e exige tarefa própria, por tocar em gravar_lago.py, que está sem Task-Spec (Regra 11) — enquanto não existir, a ausência do vínculo tem CONSEQUÊNCIA definida e propagada — 'bronze conferido' sai marcado PROCEDENCIA_NAO_VINCULADA, Silver e Gold propagam a marca sem removê-la, e Gold NÃO PUBLICA sob ela. Registrar só uma ressalva deixaria a cadeia publicar partição diferente da ancorada, porque o hash correto num pacote sem vínculo verificável com a partição lida satisfaz a comparação textual e não prova nada. A capacidade 'bronze conferido' tem FORMA declarada, não apenas nome: um objeto com estado (INTEGRO, DIVERGE, NAO_MEDIDO, ERRO_LEITURA), os cinco controles medidos, o mapa total_por_codigo em Decimal exato, as marcas de limitação como PROCEDENCIA_NAO_VINCULADA, o HASH da procedência que lhe foi apresentada — que Silver transporta e Gold usa como sha256_arquivo_lido do envelope, e que por isso não pode ser descartado na origem —, a competência lida, e AS LINHAS CONFERIDAS, com os nomes de coluna MEDIDOS no lago — especie_codigo, especie_descricao, vl_liquido e competencia — que Silver consome pelos mesmos nomes, porque conteúdo sem nome deixa Bronze entregar codigo/descricao/valor e Silver esperar outra coisa, com as duas satisfazendo a descrição. Sem elas a capacidade é insuficiente: o multiconjunto de (código, valor) e a normalização de descrição não saem de agregado, e mandar Silver reler do lago introduziria uma SEGUNDA leitura cuja identidade com a conferida não está contratada — o mesmo motivo pelo qual Bronze recusa confiar no Parquet por tê-lo escrito — porque 'produces' com nome e sem forma deixa Silver e Bronze passarem nos próprios testes com fixtures locais e não encaixarem um no outro. Partição que diverge é DIVERGE, e Bronze não escreve nada. GRAVAÇÃO EM DELTA NO MINIO, pelas decisões DEC-CAMADAS-GRAVAM-NO-MINIO e DEC-CAMADAS-EM-DELTA: só com estado INTEGRO, Bronze grava primeiro numa tabela Delta de PREPARO, privada, s3a://bronze/_preparo/pda/beneficios-emitidos/execucao=<id>, e só depois de reconferir ali publica na tabela s3a://bronze/pda/beneficios-emitidos, particionada por competencia, com overwrite e replaceWhere na competência — commit atômico, idempotente na reexecução, que não toca as outras competências. O DecimalType da coluna monetária é o declarado a partir do contrato, e a IMPOSIÇÃO DE SCHEMA do Delta fica ligada; EVOLUÇÃO de schema só ADITIVA e explícita, com mergeSchema — mudança de tipo, sobretudo monetário, é recusada, e overwriteSchema nunca é usado. A tabela declara CHECK >= 0 na coluna monetária QUE A PRÓPRIA CAMADA GRAVA — vl_liquido em Bronze e Silver, o total agregado em Gold —, o domínio da ADR 0009, e NOT NULL nas chaves. A reconferência acontece NO PREPARO, ANTES de publicar: RELÊ a versão commitada do preparo e compara o MULTICONJUNTO de TODAS as colunas que a camada grava — em Silver inclusive a descrição normalizada e a classificação, esta conferida também contra os defeitos dos metadados — com o que produziu, exceptAll nos dois sentidos, ambos vazios, e os controles, porque trocar 10 e 20 por 11 e 19 preserva os cinco controles; divergência no preparo é DIVERGE e nada é publicado. Publicada, a competência é relida e conferida de novo; divergência ali é DIVERGE e a camada REVERTE SÓ A COMPETÊNCIA — replaceWhere com o conteúdo dela na versão anterior, ou DELETE da competência quando ela não existia antes, inclusive na primeira gravação —, nunca RESTORE da tabela inteira, que desfaria outra competência; o escritor é único, pela DEC-CAMADAS-EM-DELTA. Os METADADOS da competência — estado, competência, hash da procedência, os cinco controles, marcas de limitação, defeitos classificados, total_por_codigo em Decimal serializado como texto, cobertura do referencial quando houver, id da execução e a versão lida da camada anterior — vão no userMetadata do commit que PUBLICA a competência, e esse commit é o DONO deles: o consumidor resolve a versão V da tabela UMA vez, lê os dados da competência com versionAsOf=V e os metadados do ÚLTIMO commit até V cujo userMetadata nomeia essa competência — nunca do commit V em si, que pode ser de outra. Nenhum VACUUM abaixo da retenção padrão: o histórico é evidência. O destino é parâmetro com esse padrão, e os testes gravam sob um prefixo de teste próprio, nunca no destino real
- **B-2** — GIVEN uma competência cuja partição não existe no lago ou existe com zero linhas, ou cujo contrato NÃO declara âncora WHEN Bronze lê a partição THEN o desfecho é NAO_MEDIDO nos três casos, por DOIS caminhos. Sem âncora o caminho é EXTERNO, e MEDIDO: o carregador real devolve o sentinela NAO_MEDIDO antes de existir Contrato, e conduzir fecha CONTRATO_NAO_MEDIDO antes de chamar executar_leitura — Bronze NUNCA é invocado, e por isso não recebe nem simula um Contrato sem âncora. A prova usa o carregador REAL sobre um contrato-fixture sem âncora e confere que o callback não foi chamado: um Contrato artificial passaria sem demonstrar entrada que o carregador produz. Não é DIVERGE — sem referencial não há contra o que divergir. Partição ausente e partição vazia são de Bronze, que devolve NAO_MEDIDO como valor, sem escrever camada nenhuma e sem encerrar o processo; partição ausente e partição vazia são casos distintos e ambos NAO_MEDIDO, porque ler o lago e não encontrar nada não é o mesmo que medir e encontrar zero — a Regra 9 existe porque o segundo caminho é o que veste NAO_MEDIDO de MEDIDO. As outras partições do lago são nomeadas E CONTADAS na saída, e a soma das contagens por partição é conferida contra o total lido — nomear sem contar afirma isolação sem medi-la, e a lista de nomes continuaria idêntica se as linhas de uma partição tivessem migrado para outra. ERRO_LEITURA é o estado de quem NÃO CONSEGUIU medir — objeto ilegível, esquema inesperado, credencial ausente, listagem que falhou — e é distinto de NAO_MEDIDO, que é ter medido e não achar dado: não conseguir listar uma partição não prova que ela está ausente, e não conseguir ler um objeto não prova que ele tem zero linhas. Colapsar os dois faria a fábrica registrar 'não medido' para um lago que nunca abriu. A PRECEDÊNCIA é declarada e não negociável: o estado da competência SOLICITADA decide primeiro. Ausente ou vazia devolve NAO_MEDIDO mesmo que o lago tenha outros problemas, porque não se reprova o que não se mediu. Sem âncora a precedência é ESTRUTURAL: Bronze nem roda, então o fechamento do lago não chega a ser medido — e nada nesta camada precisa decidir entre os dois. Só quando a competência existe, foi medida e TEM âncora é que o fechamento do lago entra no estado — e aí, se a soma das partições não fecha com o total, é DIVERGE, porque linha que não pertence a partição nenhuma é contaminação — e o total vem de um UNIVERSO INDEPENDENTE, a listagem dos objetos do lago, nunca da mesma leitura agrupada: somar contagens agrupadas pela própria relação lida é identidade, fecha sempre, inclusive somando o grupo nulo, e não veria arquivo que as DUAS leituras ignoraram. Se o Contrato carregado trouxer particionamento ou os limites de expoente como None — contrato que não os declara —, Bronze devolve NAO_MEDIDO: é o CONSUMIDOR que exige esses campos, e ausência declarada não é valor padrão. A CHAVE de partição é a declarada no contrato — 'competencia' — e os objetos auxiliares que ele lista, como _SUCCESS, são ignorados no fechamento. A competência CONTRATADA não é a lista exaustiva de partições válidas: tratá-la assim reprovaria competencia=fatia-teste, que existe no lago e é legítima, e seria mais um gate recusando o correto; objeto fora delas, ou linha cuja chave de partição é nula, conta como não pertencente e faz o controle reprovar, e foi para vê-la que este controle existe

## Success Criteria

```bash
# eval_1: Os cinco controles comparados individualmente, e a partição medida isoladamente
eval_1() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in cinco_controles alteracao_compensada isola_particao nao_soma_uniao precisao_declarada entrega_as_linhas_conferidas ansi_declarado_estouro_nao_vira_nulo entrega_o_hash_da_procedencia posicao_no_lago_nomeada grava_no_minio_e_reconfere replacewhere_nao_toca_outra_competencia reconfere_multiconjunto_das_linhas commit_carrega_a_forma resolve_versao_uma_vez schema_evolucao_so_aditiva check_nao_negativo reconfere_no_preparo_antes_de_publicar reverte_so_a_competencia metadados_do_commit_dono_da_competencia; do python3 -m pytest --collect-only -q tests/test_bronze.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_bronze.py -k "cinco_controles or alteracao_compensada or isola_particao or nao_soma_uniao or precisao_declarada or entrega_as_linhas_conferidas or ansi_declarado_estouro_nao_vira_nulo or entrega_o_hash_da_procedencia or posicao_no_lago_nomeada or grava_no_minio_e_reconfere or replacewhere_nao_toca_outra_competencia or reconfere_multiconjunto_das_linhas or commit_carrega_a_forma or resolve_versao_uma_vez or schema_evolucao_so_aditiva or check_nao_negativo or reconfere_no_preparo_antes_de_publicar or reverte_so_a_competencia or metadados_do_commit_dono_da_competencia"'
}

# eval_2: Ausente e vazia devolvem NAO_MEDIDO; medida e divergente devolve DIVERGE
eval_2() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in particao_ausente particao_vazia diverge_nao_e_nao_medido objeto_orfao_na_listagem erro_leitura_nao_e_nao_medido sem_ancora_para_antes_de_bronze; do python3 -m pytest --collect-only -q tests/test_bronze.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_bronze.py -k "particao_ausente or particao_vazia or diverge_nao_e_nao_medido or objeto_orfao_na_listagem or erro_leitura_nao_e_nao_medido or sem_ancora_para_antes_de_bronze"'
}

# eval_3: Float recusado na entrada, e toda diferença com uma das seis classificações
eval_3() {
  docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in centavo_a_mais maximo_acima_do_ancorado recusa_float_na_entrada classificacao_das_seis recusa_valor_negativo recusa_valor_fora_da_escala recusa_hash_divergente emite_marca_sem_vinculo; do python3 -m pytest --collect-only -q tests/test_bronze.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_bronze.py -k "centavo_a_mais or maximo_acima_do_ancorado or recusa_float_na_entrada or classificacao_das_seis or recusa_valor_negativo or recusa_valor_fora_da_escala or recusa_hash_divergente or emite_marca_sem_vinculo"'
}

```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: "Os cinco controles comparados individualmente, e a partição medida isoladamente"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: false
    expected_duration_sec: 10
  - id: eval_2
    description: "Ausente e vazia devolvem NAO_MEDIDO; medida e divergente devolve DIVERGE"
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: false
    expected_duration_sec: 10
  - id: eval_3
    description: "Float recusado na entrada, e toda diferença com uma das seis classificações"
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
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

Remover o leitor Bronze e seus testes.

## Observability Hooks

partições recusadas por controle divergente

## Anti-Patterns

- Do not conferir só contagem e soma, deixando min, max e linhas_invalidas de fora: a R-5 exige os cinco individualmente, e uma alteração compensada entre duas linhas preserva contagem e soma enquanto empurra o máximo acima do ancorado; instead comparar os cinco, nomeando na saída qual deles divergiu.
- Do not aceitar diferença de centavos como arredondamento: afrouxar a tolerância é editar o oráculo pelo avesso; instead exigir igualdade exata entre Decimal e Decimal.
- Do not pedir ao agente do loop que instale ou baixe qualquer coisa para montar o ambiente de eval: o contrato de runtime nega rede — net.egress False e policy.network deny — então a tarefa seria impossível por construção e queimaria o orçamento inteiro sem escrever um arquivo; instead preparar o ambiente fora do loop, em infra/preparar-spark.sh, e o eval apenas usá-lo.

## Do-Not-Touch

- `_raw`
- `cvg/docs/adrs`
- `contracts`

## Open Questions

(none — this task is fully specified)
