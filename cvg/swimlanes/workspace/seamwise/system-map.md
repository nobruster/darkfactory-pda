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
- LEG-DESFECHO-SEMPRE-COM-PACOTE
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
- id: OBJ-C41
  status: FIXED
  summary: A execução dependia de contrato e fonte sem entrega identificada — a fonte real não está neste
    workspace.
  owner: Bruno Nunes
  rationale: A tarefa do contrato passou a entregar contracts/competencia.yaml e um fixture reduzido.
    Os testes provam contra eles; a contagem esperada vem do contrato, não do número fixo de 41,7 milhões.
- id: OBJ-C42
  status: FIXED
  summary: O pacote não prometia os dados que explicam uma reprovação por tempo — 650s e 550s teriam o
    mesmo registro.
  owner: Bruno Nunes
  rationale: O pacote passou a registrar a duração observada e o limite aplicado. Uma recusa por tempo
    é distinguível de uma por controle sem reexecutar.
- id: OBJ-C43
  status: FIXED
  summary: 'Testar as seis classes não provava cobertura: um defeito observado sem classificação seria
    ignorado.'
  owner: Bruno Nunes
  rationale: eval_3 passou a exigir cenário em que um defeito chega sem classificação e o juízo bloqueia
    — exclusividade da enumeração não prova correspondência com os defeitos.
- id: OBJ-C44
  status: FIXED
  summary: BUILD-ORDER — o juízo prometia prova ponta a ponta, mas a orquestração que entrega o fluxo
    vem depois dele no grafo.
  owner: Bruno Nunes
  rationale: A prova ponta a ponta migrou para a orquestração, que possui o fluxo. O juízo prova sobre
    agregado derivado, sem depender de artefato futuro. Mesma classe da C11 — corrigir a posse deslocou
    a dependência.
- id: OBJ-C45
  status: FIXED
  summary: O caminho de float recusado não devolvia agregado, deixando o juízo sem o que comparar.
  owner: Bruno Nunes
  rationale: B-1 da agregação passou a exigir o agregado mesmo na recusa, com o campo recusado contado
    em linhas_invalidas. Recusar não é devolver nada.
- id: OBJ-C30
  status: FIXED
  summary: A classificação podia sobrepor a recusa obrigatória dos cinco controles — um total divergente
    marcado CONFIRMED autorizaria.
  owner: Bruno Nunes
  rationale: 'B-2 do juízo declara a PRECEDÊNCIA: divergência em qualquer controle recusa, mesmo classificada.
    A classificação explica, nunca autoriza.'
- id: OBJ-C31
  status: FIXED
  summary: Modo explícito não garantia soma exata — a precisão do contexto decide antes.
  owner: Bruno Nunes
  rationale: 'ADR 0006 (novo). Verificado: em prec=6, 10000.00 + 0.01 vira 10000.0, e quantizar depois
    devolve 10000.00, não 10000.01. A perda é anterior ao arredondamento. Um teste força prec=6 e exige
    que a soma acuse.'
- id: OBJ-C32
  status: FIXED
  summary: O pacote exigia campos que não existem nos términos antecipados — o gravador rejeitaria o próprio
    caso que deve registrar.
  owner: Bruno Nunes
  rationale: B-1 da evidência passou a exigir que campos não percorridos sejam AUSENTES e marcados como
    tal, nunca preenchidos com zero ou valor artificial que comprometeria a reconstrução.
- id: OBJ-C33
  status: FIXED
  summary: ERRO não tinha cenário de falha real — testar a enumeração não prova que exceções chegam ao
    finalizador.
  owner: Bruno Nunes
  rationale: B-2 da orquestração passou a exigir uma exceção REAL dentro da leitura, que deve virar ERRO
    com pacote. Falha do próprio gravador é o único caso sem pacote, e sai com código distinto.
- id: OBJ-C34
  status: FIXED
  summary: Registro monetário malformado não tinha participação definida nos cinco controles.
  owner: Bruno Nunes
  rationale: 'B-2 da leitura declara: entra em linhas_invalidas e NÃO entra em sum/min/max.'
- id: OBJ-C35
  status: FIXED
  summary: Os nomes dos extremos divergiam entre contrato e agregado.
  owner: Bruno Nunes
  rationale: B-1 do contrato passou a exigir os cinco controles sob os MESMOS nomes que o agregado usa.
- id: OBJ-C14
  status: FIXED
  summary: O encerramento sem âncora foi delegado a um "orquestrador" que nenhuma das cinco tarefas assumia.
  owner: Bruno Nunes
  rationale: 'Criada a sexta costura, SEAM-ORQUESTRACAO, com tarefa própria. Ela possui o fluxo: decide
    o desfecho, o código de saída, e garante o pacote em todo caminho.'
- id: OBJ-C15
  status: FIXED
  summary: O juízo exigia cinco controles que o produtor não prometia entregar — não havia schema de saída.
  owner: Bruno Nunes
  rationale: B-1 da agregação passou a exigir os cinco controles NOMEADOS no agregado devolvido.
- id: OBJ-C16
  status: FIXED
  summary: Os três vereditos enumerados excluíam a recusa com âncora — justamente quando o juiz acusa.
  owner: Bruno Nunes
  rationale: 'São quatro terminais (ADR 0005): ACEITO, ACEITO_SEM_ANCORA, RECUSADO e ERRO. A recusa com
    âncora grava como RECUSADO.'
- id: OBJ-C17
  status: FIXED
  summary: 'O teste de R-6 media só a leitura: 530s de leitura mais 120s do resto passaria e violaria
    o requisito.'
  owner: Bruno Nunes
  rationale: A medição saiu da leitura (que agora só reporta sua duração) e foi para a orquestração, que
    mede do início ao veredito contra os 600s.
- id: OBJ-C18
  status: FIXED
  summary: Exclusividade das classificações não provava bloqueio de MODERN_DEFECT nem CONTRACT_AMBIGUITY.
  owner: Bruno Nunes
  rationale: 'B-2 do juízo passou a exigir a política de cada uma das seis: três bloqueiam, três registram
    sem bloquear.'
- id: OBJ-C19
  status: FIXED
  summary: O veredito público sem âncora divergia de R-1 — NAO_MEDIDO e ACEITO_SEM_ANCORA sem relação
    declarada.
  owner: Bruno Nunes
  rationale: 'ADR 0005 resolve: ACEITO_SEM_ANCORA é o veredito, NAO_MEDIDO é a causa. Camadas, não alternativas.'
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
