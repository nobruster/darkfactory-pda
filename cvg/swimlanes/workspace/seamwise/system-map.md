---
schema_version: 1
kind: system-map
claim: proposed
components:
- Contrato e âncora
- Leitura posicional
- Agregação monetária
- Juízo do agregado
- Pacote de evidência
- Orquestração da execução
external_dependencies:
- Arquivo CSV da competência, imutável em _raw/
- Âncora medida na origem por fora do pipeline
- Spark e MinIO, a montar — o carregamento ao lago é escopo próprio
unknowns: []
proposed_steel_thread:
- LEG-CONTRATO-RECUSA-SEM-ANCORA
- LEG-LEITURA-POSICIONAL
- LEG-AGREGADO-EXATO
- LEG-ENVELOPE-VINCULADO
- LEG-JUIZO-ACUSA
- LEG-EVIDENCIA-RECONSTROI
- LEG-DESFECHO-COM-PACOTE
objections:
- id: OBJ-C1
  status: FIXED
  summary: O fluxo dito inteiro não cobria a arquitetura do ADR 0005 — dava para concluir a cadeia com
    módulos Python e fixtures, sem nunca conectar o produtor que será julgado.
  owner: Bruno Nunes
  rationale: Criada a sétima costura, SEAM-FRONTEIRA. Ela escreve o contrato entre produtor e juiz agora,
    para que o Spark implemente contra algo declarado em vez de contra o que o juiz por acaso aceita.
    A independência do ADR 0005 deixa de ser só declaração.
- id: OBJ-C2
  status: FIXED
  summary: Declarar um modo de arredondamento não demonstrava HALF_EVEN — uma implementação com HALF_UP
    passaria nos testes descritos.
  owner: Bruno Nunes
  rationale: B-2 da agregação passou a exigir o resultado de HALF_EVEN comparado contra o que HALF_UP
    produziria, recusando-o.
- id: OBJ-C3
  status: FIXED
  summary: Leitura posicional não provava rejeição de mudança de layout; trocar duas colunas não monetárias
    preservaria os cinco controles.
  owner: Bruno Nunes
  rationale: B-1 da leitura passou a exigir bloqueio ANTES de ler qualquer registro quando o cabeçalho
    está fora da ordem declarada, como o ADR 0002 promete.
- id: OBJ-C4
  status: FIXED
  summary: A procedência não vinculava a âncora ao arquivo efetivamente lido — uma republicação com os
    mesmos controles passaria.
  owner: Bruno Nunes
  rationale: O envelope da SEAM-FRONTEIRA carrega o sha256 do arquivo lido, e a validação recusa sha256
    ausente ou divergente do ancorado.
- id: OBJ-C5
  status: FIXED
  summary: A interface não definia como linhas inválidas chegam aos cinco controles; um produtor que contasse
    só as válidas devolveria zero.
  owner: Bruno Nunes
  rationale: O envelope exige coerência entre linhas_invalidas e a contagem de defeitos observados, e
    recusa envelope incoerente.
- id: OBJ-C6
  status: FIXED
  summary: O truncamento do ADR 0004 podia nunca chegar à classificação — dinheiro válido e descrições
    truncadas passariam com defeitos vazios.
  owner: Bruno Nunes
  rationale: B-2 da leitura passou a exigir que descrição de exatamente 20 caracteres emita defeito de
    truncamento, mesmo sem ser linha inválida.
- id: OBJ-C7
  status: FIXED
  summary: A promessa de pacote em todo caminho assumia que a própria gravação não falha.
  owner: Bruno Nunes
  rationale: 'B-2 da orquestração declara o desfecho quando o gravador falha: ERRO com código próprio,
    nunca ACEITO sem pacote — autorização sem evidência é o que a fábrica existe para impedir.'
contentions: []
---
# System Map

## Components

- Contrato e âncora
- Leitura posicional
- Agregação monetária
- Juízo do agregado
- Pacote de evidência
- Orquestração da execução

## External dependencies

- Arquivo CSV da competência, imutável em _raw/
- Âncora medida na origem por fora do pipeline
- Spark e MinIO, a montar — o carregamento ao lago é escopo próprio

## Unknowns

- (none)

This is a **proposed** map. The delivery-plan transformation must
close or gate every material unknown; it may not reinterpret this text as
runtime proof.
