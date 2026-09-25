---
schema_version: 1
kind: decision
id: DEC-DEFEITOS-LATENTES-FIXADOS
status: accepted
owner: Bruno Nunes
rationale: 'A primeira revisão do produtor (code-reviewer e test-generator, 2026-09-24) achou defeitos
  LATENTES, nenhum exercido pelo landing de 2026-01 (0 inválidas, uma carga, fecha com a âncora): a gramática
  Spark diverge da do juiz Python (''1,5'' e negativos); código vazio some de total_por_codigo sem contador;
  o append não confere partição vazia; linha inválida grava NULL sem o texto bruto; as sessões não declaram
  ansi.enabled. A adoção FIXA o comportamento atual em teste e não corrige: corrigir muda o código que
  gravou o dado, e cada correção é tarefa própria, decidida pelo dono.'
---
# DEC-DEFEITOS-LATENTES-FIXADOS

Status: **accepted**

Owner: Bruno Nunes

## Rationale

A primeira revisão do produtor (code-reviewer e test-generator, 2026-09-24) achou defeitos LATENTES, nenhum exercido pelo landing de 2026-01 (0 inválidas, uma carga, fecha com a âncora): a gramática Spark diverge da do juiz Python ('1,5' e negativos); código vazio some de total_por_codigo sem contador; o append não confere partição vazia; linha inválida grava NULL sem o texto bruto; as sessões não declaram ansi.enabled. A adoção FIXA o comportamento atual em teste e não corrige: corrigir muda o código que gravou o dado, e cada correção é tarefa própria, decidida pelo dono.
