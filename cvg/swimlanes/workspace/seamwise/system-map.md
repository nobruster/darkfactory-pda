---
schema_version: 1
kind: system-map
claim: proposed
components:
- Contrato e âncora
- Leitura da competência
- Agregação monetária
- Juízo do agregado
- Pacote de evidência
external_dependencies:
- Arquivo da competência publicado pela origem, imutável
- Âncora medida na origem por fora do pipeline
unknowns: []
proposed_steel_thread:
- LEG-CONTRATO-RECUSA-SEM-ANCORA
- LEG-LEITURA-NAO-ALTERA-FONTE
- LEG-AGREGADO-EXATO
- LEG-JUIZO-ACUSA-CENTAVO
- LEG-EVIDENCIA-RECONSTROI
objections:
- id: OBJ-C1
  status: FIXED
  summary: O pacote entregue continha índices, mas não os planos dos legs — o adversário revisava cabeçalhos
    sem o conteúdo a implementar.
  owner: Bruno Nunes
  rationale: A ponte passou a projetar os LEG-*.md ao lado de cada _lane.md. O dispatcher, que varre <dir>/*/*.md,
    passou de 5 para 10 arquivos.
- id: OBJ-C2
  status: FIXED
  summary: A evidência prometia gravar ACEITO_SEM_ANCORA, mas o contrato encerrava com NAO_MEDIDO antes
    de qualquer leitura, sem transferir esse resultado.
  owner: Bruno Nunes
  rationale: O contrato passou a produzir 'veredito NAO_MEDIDO' como saída declarada, e a evidência a
    consumi-lo. B-4 exige que ele alcance a evidência antes do exit.
- id: OBJ-C3
  status: FIXED
  summary: Presença de cinco números era tratada como prova de âncora medida, sem exigir aprovador nem
    data.
  owner: Bruno Nunes
  rationale: B-1 passou a exigir os cinco números NOMEADOS mais a procedência, e B-3 recusa (NAO_MEDIDO)
    uma âncora numericamente completa sem aprovador ou data de medição.
- id: OBJ-C4
  status: FIXED
  summary: O defeito preservado na leitura desaparecia ao virar agregado — o juízo não recebia o que precisava
    para classificá-lo.
  owner: Bruno Nunes
  rationale: '''defeitos observados'' virou saída da leitura, atravessa a agregação e é consumido pelo
    juízo. B-3 exige identidade do registro, valor original e posição.'
- id: OBJ-C5
  status: FIXED
  summary: A prova de arredondamento verificava apenas total diferente; R-3 exige veredito diferente.
  owner: Bruno Nunes
  rationale: 'B-3 do juízo passou a exigir que meio-para-cima leve a VEREDITO diferente. Total diferente
    não basta: o juízo poderia re-arredondar e anular a divergência.'
- id: OBJ-C6
  status: FIXED
  summary: A prova de um centavo partia de um agregado já alterado, não de uma linha corrompida como R-5
    exige.
  owner: Bruno Nunes
  rationale: B-1 passou a corromper UMA LINHA do arquivo e rodar o pipeline ponta a ponta. O teste anterior
    passaria mesmo se a leitura descartasse a linha.
- id: OBJ-C8
  status: FIXED
  summary: A execução sem âncora tinha dois vereditos incompatíveis — o contrato mandava NAO_MEDIDO, a
    evidência esperava ACEITO_SEM_ANCORA.
  owner: Bruno Nunes
  rationale: A evidência passou a gravar QUALQUER veredito terminal dos três, registrando qual foi, com
    os campos que existirem. NAO_MEDIDO grava sem agregado e nunca aparece como ACEITO.
- id: OBJ-C9
  status: FIXED
  summary: O juízo não provava comparação dos cinco controles do ADR 0002 — redistribuir valores mantendo
    soma e contagem alterava extremos sem recusa.
  owner: Bruno Nunes
  rationale: B-1 passou a exigir comparação individual dos cinco, com um caso que mantém soma e contagem
    e ainda assim deve recusar.
- id: OBJ-C10
  status: FIXED
  summary: O leitor consumia posições que o contrato não prometia fornecer; contagem certa e hash inalterado
    não provam que a coluna certa foi lida.
  owner: Bruno Nunes
  rationale: O layout de leitura (posições, formato monetário, chave) virou parte do contrato, e sua ausência
    resulta em NAO_MEDIDO. B-1 da leitura exige leitura posicional mesmo com cabeçalho repetido.
- id: OBJ-C11
  status: FIXED
  summary: 'Ciclo de construção: a primeira folha precisava provar gravação de evidência, mas o gravador
    é a última tarefa.'
  owner: Bruno Nunes
  rationale: 'Defeito introduzido pela correção de C2. Separadas as responsabilidades: o contrato RETORNA
    o veredito como valor, sem gravar nem encerrar; quem persiste é a evidência. O eval de tempo da leitura
    passou a medir só a leitura, não até o veredito.'
- id: OBJ-C12
  status: FIXED
  summary: 'A granularidade do arredondamento não estava reconciliada: 2,345 + 2,345 dá 4,68 por campo
    e 4,69 só no total, ambos HALF_EVEN.'
  owner: Bruno Nunes
  rationale: Registrado no ADR 0004 — arredonda uma vez, sobre o total final, e a mesma granularidade
    vale para a medição da âncora. Contra-exemplo verificado; com três valores o desvio dobra.
- id: OBJ-C13
  status: FIXED
  summary: Comparar meio-para-par com meio-para-cima não detectava herança do default — um contexto já
    configurado passaria, violando R-3.
  owner: Bruno Nunes
  rationale: B-2 da agregação passou a exigir modo EXPLÍCITO, com um teste que troca o default do contexto
    e falha se a implementação o herdar.
- id: OBJ-C7
  status: FIXED
  summary: R-6 (10 minutos) não tinha prova nem responsável — tudo passaria com a competência levando
    horas.
  owner: Bruno Nunes
  rationale: B-4 da leitura mede do início ao veredito e reprova acima de 600s. O tempo entrou na observabilidade
    da lane.
contentions: []
---
# System Map

## Components

- Contrato e âncora
- Leitura da competência
- Agregação monetária
- Juízo do agregado
- Pacote de evidência

## External dependencies

- Arquivo da competência publicado pela origem, imutável
- Âncora medida na origem por fora do pipeline

## Unknowns

- (none)

This is a **proposed** map. The delivery-plan transformation must
close or gate every material unknown; it may not reinterpret this text as
runtime proof.
