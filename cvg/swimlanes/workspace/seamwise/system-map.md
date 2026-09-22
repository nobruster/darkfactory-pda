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
- id: OBJ-R2-C1
  status: ACCEPTED
  summary: O fluxo não construiria o produtor Spark nem a infraestrutura que o ADR 0005 menciona — dava
    para fechar a cadeia com Python e envelope sintético, sem produtor real.
  owner: Bruno Nunes
  rationale: 'ACCEPTED aqui significa RECEBIDA E DECIDIDA SEM MUDANÇA — o schema do seamwise só admite
    FIXED, ACCEPTED e OPEN, e esta objeção foi REFUTADA, não corrigida. A objeção lê o ADR 0005 como se
    ele encomendasse o produtor; ele decide QUAL motor julga — Spark grava, Python puro confere — e existe
    justamente para que o juiz não herde os defeitos de quem ele julga. O carregamento em Spark e MinIO
    já está em out_of_scope desta receita, com o motivo escrito: o juízo precisa existir antes de haver
    o que julgar, e entra como plano próprio depois deste. A tensão com a tech-spec que a objeção aponta
    é a mesma exclusão, vista do outro lado — não há contradição a resolver. Construir o produtor aqui
    apagaria a separação de motores que o ADR 0005 estabelece. Segunda vez que esta objeção aparece; a
    primeira virou a sétima costura, e a reincidência mostra que o que faltava não era mais uma correção,
    e sim esta decisão explícita.'
- id: OBJ-R2-C2
  status: FIXED
  summary: A regra que EU escrevi na rodada 1 confundia contagem de defeitos com linhas inválidas, e recusaria
    a competência 2026-01, que está correta.
  owner: Bruno Nunes
  rationale: 'Verificado contra a âncora medida: linhas_invalidas=0 com milhões de truncamentos válidos.
    B-2 da fronteira passou a confrontar linhas_invalidas só com defeitos do tipo VALOR_ILEGIVEL — truncamento
    é defeito numa linha válida.'
- id: OBJ-R2-C3
  status: FIXED
  summary: O hash ancorado não dizia se cobria o ZIP publicado ou o CSV extraído sobre o qual a âncora
    foi medida.
  owner: Bruno Nunes
  rationale: 'Verificado no repositório: CHECKSUMS.txt traz só o sha256 do ZIP, e a âncora foi medida
    no CSV, que não tem hash nenhum — trocar o CSV extraído não seria detectado. B-1 do contrato passou
    a exigir os dois hashes, cada um declarando qual artefato cobre.'
- id: OBJ-R2-C4
  status: FIXED
  summary: O juízo provava ausência de classificação, não classificação única — duas classificações na
    mesma diferença passariam.
  owner: Bruno Nunes
  rationale: 'B-2 do juízo passou a exigir exatamente uma classificação por diferença: zero bloqueia e
    duas também, porque duas permitem escolher a mais branda na hora de ler.'
- id: OBJ-R2-C5
  status: FIXED
  summary: O pacote podia reproduzir o rótulo do veredito sem preservar a prova que o prende ao arquivo
    julgado.
  owner: Bruno Nunes
  rationale: B-1 da evidência passou a exigir veredito REDERIVADO dos controles, da âncora e dos dois
    hashes; pacote com rótulo trocado é recusado, e pacote sem os hashes é recusado antes disso.
- id: OBJ-R2-C6
  status: FIXED
  summary: A regra que EU escrevi na rodada 1 — descrição com exatamente 20 caracteres — deixava de fora
    o exemplo principal do ADR 0004.
  owner: Bruno Nunes
  rationale: 'Verificado: ''Pensão por Morte de '' tem bruto=20 e strip=19; medindo após strip, os códigos
    01, 03, 23 e 59 não emitiriam defeito. B-2 da leitura passou a medir o campo BRUTO ocupando os 20
    caracteres do layout.'
- id: OBJ-R2-C7
  status: FIXED
  summary: Os cinco controles não tinham semântica para registros ilegíveis — cada implementação decidiria
    se contá-los.
  owner: Bruno Nunes
  rationale: 'B-1 da agregação passou a exigir que cada controle declare se conta o ilegível: count_linhas
    conta todo registro lido, os quatro monetários somam só os legíveis. Contar o ilegível no monetário
    somaria zero e faria a âncora medida deixar de bater.'
- id: OBJ-R3-C1
  status: FIXED
  summary: O ADR 0005 põe a infra Spark no escopo do Pass 3, e o out_of_scope da receita a exclui. Terceira
    rodada da mesma objeção.
  owner: Bruno Nunes
  rationale: 'MINHA REFUTAÇÃO DA 2a RODADA ESTAVA ERRADA. Argumentei que o ADR 0005 só decidia qual motor
    julga; ele diz na linha 90 que montar a infra "faz parte do escopo, e entra como tarefa no plano do
    Pass 3". Eu tinha lido a seção Decision e não o resto do documento. O adversário tinha os fatos; eu
    tinha leitura parcial. A contradição era real e estava entre a doutrina e o plano. Resolvida com o
    ADR 0006, que SUPERSEDES a parte de escopo do 0005 e registra o fato verificável: a receita das sete
    costuras não menciona pyspark, e a âncora foi medida por Python sequencial em 64s — juízo e produtor
    são entregáveis separáveis. A separação de motores do 0005 permanece; é ela que torna a ordem livre.
    CHECK_ADR=OK.'
- id: OBJ-R3-C2
  status: FIXED
  summary: Minha correção de C5 recusava pacote sem hash incondicionalmente, o que impedia gravar justamente
    a execução ACEITO_SEM_ANCORA.
  owner: Bruno Nunes
  rationale: 'Duas correções minhas se contradiziam. B-1 da evidência passou a tratar ausência de hash
    como algo que DECIDE o veredito, não que o recusa: sem hash do CSV o desfecho é ACEITO_SEM_ANCORA
    com causa NAO_MEDIDO, e o pacote é válido. Só é recusado o pacote cujo rótulo não bate com o que os
    insumos rederivam.'
- id: OBJ-R3-C3
  status: FIXED
  summary: 'Os insumos que eu listei para rederivar o veredito não o determinam: mesmos controles e hashes
    admitem decisões distintas.'
  owner: Bruno Nunes
  rationale: Correto — um defeito fora dos controles com CONFIRMED apenas registra e com UNRESOLVED bloqueia,
    e as classificações não estavam entre os insumos. B-1 da evidência passou a incluí-las na regra de
    rederivação.
- id: OBJ-R3-C4
  status: FIXED
  summary: Minha correção de C7 dizia "os quatro monetários somam"; não existem quatro monetários, e min/max
    não somam.
  owner: Bruno Nunes
  rationale: 'Verificado contra a âncora: são DOIS de contagem (count_linhas, linhas_invalidas) e TRÊS
    monetários (sum, min, max), e só sum é soma. Pior, minha justificativa era aritmeticamente falsa:
    preencher o ilegível com 0.00 NÃO é detectado por nenhum dos três — a soma não muda, max não muda,
    e min já é 0.00 na fonte. Só linhas_invalidas acusa. B-1 da agregação passou a exigir que o teste
    prove EXCLUSÃO do ilegível, nunca comparando totais.'
- id: OBJ-R3-C5
  status: FIXED
  summary: Comparar o hash declarado não prova que ele veio dos bytes lidos — um produtor com cache errado
    pode copiar o hash ancorado.
  owner: Bruno Nunes
  rationale: B-1 da fronteira passou a declarar o sha256 como SAÍDA do leitor, computada sobre os mesmos
    bytes que alimentaram os controles, e a recusar o envelope cujo hash declarado discorda do que o leitor
    computou. Igualdade com o ancorado não bastava.
- id: OBJ-R3-C6
  status: FIXED
  summary: 'A prova integrada de R-7 passaria sem exercitar o juízo: remover uma linha muda o hash, e
    a fronteira recusa antes da comparação.'
  owner: Bruno Nunes
  rationale: 'B-1 da orquestração trocou o caso: agora é o arquivo ÍNTEGRO com o agregador divergindo
    de um controle, recusado pelo JUÍZO com hash válido. E o teste falha se um juízo permissivo for injetado
    — é isso que prova que a integração chama e respeita o juízo, como R-7 exige.'
- id: OBJ-R4-C1
  status: FIXED
  summary: Minha correção de R3-C5 exigia comparar o hash computado, mas nada no grafo levava esse valor
    até o validador.
  owner: Bruno Nunes
  rationale: Verificado no grafo de capacidades — a leitura produzia apenas registros lidos e defeitos
    observados; o hash computado não existia como capacidade, e dois campos do mesmo envelope podiam repetir
    o ancorado. Criada a capacidade "sha256 computado na leitura", produzida pela leitura e exigida pela
    fronteira. Para produtor externo, que o ADR 0006 permite, o envelope sem essa capacidade é recusado
    por falta de insumo, nunca aceito por ausência de contraditório.
- id: OBJ-R4-C2
  status: FIXED
  summary: Minha correção de R3-C2 não distinguia falta de âncora de falha na execução — as duas chegam
    sem hash e não são o mesmo desfecho.
  owner: Bruno Nunes
  rationale: B-1 da evidência passou a separar os dois hashes. Falta o ANCORADO, do contrato, e é ACEITO_SEM_ANCORA
    com causa NAO_MEDIDO. Falta o OBSERVADO, da leitura, e é execução interrompida — ERRO, com o evento
    de falha entre os insumos da rederivação, porque controles ausentes depois de uma exceção não determinam
    ERRO por si.
- id: OBJ-R4-C3
  status: FIXED
  summary: O gate de layout não cobria a troca entre as duas colunas de cabeçalho idêntico — justamente
    o caso que motivou a leitura posicional.
  owner: Bruno Nunes
  rationale: 'Verificado no arquivo real: os índices 12 e 13 trazem o MESMO cabeçalho ''Espécie'', um
    com o código de 2 dígitos e outro com a descrição truncada. Trocar os valores entre si deixa o cabeçalho
    byte a byte igual e preserva os cinco controles. Conferir cabeçalho não distingue as duas; B-1 da
    leitura passou a exigir o formato de cada posição, e o teste falha se for satisfeito com colunas de
    nomes diferentes.'
- id: OBJ-R4-C4
  status: FIXED
  summary: Demonstrar que dois agrupamentos diferem não prova qual deles o agregador entregue usa.
  owner: Bruno Nunes
  rationale: A prova anterior era satisfeita dentro do teste, e continuaria verdadeira com um agregador
    que agrupa por descrição. B-2 da agregação passou a exigir que a SAÍDA preserve os 51 códigos distintos
    do ADR 0004, com o teste falhando se a chave entregue for a descrição.
- id: OBJ-R4-C5
  status: FIXED
  summary: Minha correção de R3-C6 SUBSTITUIU o cenário obrigatório de R-7 em vez de somar a ele.
  owner: Bruno Nunes
  rationale: R-7 exige uma linha removida ou um centavo alterado no arquivo, e eu troquei esse caso por
    divergência do agregador sobre arquivo íntegro. As duas provas verificam falhas diferentes e nenhuma
    substitui a outra. B-1 da orquestração passou a exigir as DUAS execuções de recusa — a do centavo
    alterado nos bytes e a do arquivo íntegro com juízo permissivo injetado.
- id: OBJ-R5-C1
  status: FIXED
  summary: A recusa de float estava só no agregador local; o envelope aceita produtor externo, que não
    passa por ele.
  owner: Bruno Nunes
  rationale: Quatro das cinco objeções desta rodada têm a mesma raiz — o ADR 0006 admitiu produtor externo
    e a fronteira ainda era escrita supondo o agregador local. B-2 da fronteira passou a contratar os
    três monetários como string ou Decimal, com recusa ANTES de qualquer conversão, porque Decimal(str(v))
    apagaria a prova de que veio float.
- id: OBJ-R5-C2
  status: FIXED
  summary: Um envelope podia omitir os truncamentos que a leitura observou e passar, com o juiz aprovando
    lista vazia.
  owner: Bruno Nunes
  rationale: A única reconciliação exigida era linhas_invalidas contra VALOR_ILEGIVEL. B-2 da fronteira
    passou a exigir que os defeitos observados cheguem por contagem e por tipo, e recusa a omissão — o
    juiz não violaria classificação única porque o defeito sumia antes de chegar nele.
- id: OBJ-R5-C3
  status: FIXED
  summary: A fronteira compara TRÊS hashes e o pacote gravava dois; um RECUSADO legítimo rederivaria ACEITO.
  owner: Bruno Nunes
  rationale: Contraexemplo válido — ancorado=observado=A com envelope declarando B é recusado pela fronteira,
    e sem o declarado no pacote a razão da recusa se perde. B-1 da evidência passou a gravar os três.
- id: OBJ-R5-C4
  status: FIXED
  summary: Execução encerrada por NAO_MEDIDO antes da leitura não tem nenhum dos dois hashes, e a precedência
    não estava declarada.
  owner: Bruno Nunes
  rationale: 'B-1 da evidência passou a declarar a precedência em vez de deixá-la deduzir: falta o ancorado
    e é ACEITO_SEM_ANCORA, inclusive quando o observado também falta; ERRO exige evento de falha registrado.
    Implementações independentes deixam de poder discordar.'
- id: OBJ-R5-C5
  status: FIXED
  summary: O ADR 0003 põe precisão e arredondamento no contrato, mas o carregador não os carregava — ficavam
    escolha privada da implementação.
  owner: Bruno Nunes
  rationale: B-1 do contrato passou a carregar a política decimal junto com âncora, layout e hashes, e
    contrato sem ela é NAO_MEDIDO. A agregação passou a exigir contrato validado entre seus requisitos,
    para que a política atravesse o grafo em vez de ser fixada dentro do agregador.
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
