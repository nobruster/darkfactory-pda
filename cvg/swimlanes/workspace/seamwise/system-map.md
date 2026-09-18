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
