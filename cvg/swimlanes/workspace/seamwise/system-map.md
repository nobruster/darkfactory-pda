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
- id: OBJ-R6-C1
  status: FIXED
  summary: Minha correção de R5-C2 criou uma recusa por omissão que a evidência não conseguia rederivar.
  owner: Bruno Nunes
  rationale: Contraexemplo válido — leitura observa truncamento, envelope declara lista vazia, controles
    e os três hashes coincidem; a recusa é legítima e só a divergência entre as listas a explica. B-1
    da evidência passou a gravar as DUAS listas separadamente, a observada e a declarada.
- id: OBJ-R6-C2
  status: FIXED
  summary: NAO_MEDIDO tem várias causas — sem aprovador, sem data, sem política decimal — e minha regra
    lia a falta do hash como se fosse a causa.
  owner: Bruno Nunes
  rationale: 'Contraexemplo válido — contrato com âncora e os dois hashes, mas sem aprovador, parando
    antes da leitura sem exceção: há hash ancorado, não há observado, não há evento de falha, e nenhuma
    regra determinava o desfecho. B-1 da evidência passou a decidir pela CAUSA registrada: NAO_MEDIDO
    por qualquer motivo dá ACEITO_SEM_ANCORA, e ERRO exige evento de falha.'
- id: OBJ-R6-C3
  status: FIXED
  summary: Produtor externo podia agrupar por descrição, colapsar espécies e declarar os mesmos cinco
    controles, hashes e defeitos.
  owner: Bruno Nunes
  rationale: Mesma raiz da rodada 5 — R-3 estava provado só no agregador local, enquanto o envelope é
    o contrato do produtor externo. B-2 da fronteira passou a exigir o agregado declarado POR CÓDIGO,
    com os 51 códigos do ADR 0004 como chaves.
- id: OBJ-R6-C4
  status: FIXED
  summary: Minha correção de R5-C5 cobria política decimal ausente, mas não política presente e contraditória.
  owner: Bruno Nunes
  rationale: Um contrato com HALF_UP satisfaria a condição de presença e sairia validado, deixando o agregador
    entre obedecer ao contrato e obedecer ao ADR. B-1 do contrato passou a RECUSAR no carregamento a política
    que contradiz o ADR 0003. A validação confere a política contra o ADR, nunca o contrário — afrouxar
    o ADR para o contrato passar é a manobra que a Regra 3 proíbe.
- id: OBJ-R6-C5
  status: FIXED
  summary: Minha correção de R4-C5 dividiu R-7 em duas provas; R-7 escreveu uma propriedade CONJUNTA.
  owner: Bruno Nunes
  rationale: R-7 exige alteração real no arquivo, recusada, "provada por teste que falha se o juízo aceitar".
    Separadas, um juízo permissivo deixa o teste da alteração real verde. Decidido com Bruno Nunes — o
    teste altera um centavo E reancora o sha256 do arquivo alterado, de modo que a fronteira passe e o
    JUÍZO seja quem recusa, contra a âncora monetária original. Uma prova só, conjunta, como R-7 escreveu.
- id: OBJ-R6-C6
  status: FIXED
  summary: O done_condition dizia "medido contra R-9", mas medir com relógio simulado não demonstra orçamento
    de competência completa.
  owner: Bruno Nunes
  rationale: R-9 é should, e a lacuna não autoriza inventar recusa por timeout. O done_condition passou
    a declarar que R-9 NÃO está coberto aqui, e o tempo é medido e registrado no pacote para que a cobertura
    seja decidida contra competência real. Declarar cobertura que o teste não entrega é verde pelo motivo
    errado.
- id: OBJ-R7-C1
  status: FIXED
  summary: Minha correção de R6-C3 tratou os 51 códigos do ADR 0004 como o universo; eles saíram de uma
    AMOSTRA de ~3 milhões de linhas.
  owner: Bruno Nunes
  rationale: 'MEDIDO NA COMPETÊNCIA INTEIRA, e o adversário estava certo — são 65 códigos, não 51. A regra
    que escrevi RECUSARIA o arquivo correto. A cauda mostra por que a amostra não os viu: o código ''60''
    aparece 1.395 vezes em 41.572.553 linhas. É a Regra 3 pelo avesso — um gate calibrado em amostra recusa
    a verdade. A cardinalidade passou a ser ANCORADA no contrato, medida na competência inteira, e scripts/medir_codigos.py
    registra a medição (CODIGOS=MEDIDO).'
- id: OBJ-R7-C2
  status: FIXED
  summary: Minha correção de R6-C4 criou um RECUSADO no carregamento do contrato sem caminho de rederivação
    nem exercício na orquestração.
  owner: Bruno Nunes
  rationale: Mesmo padrão das rodadas 5 e 6 — garantia nova cria estado novo cuja consequência eu não
    declaro. B-1 da evidência passou a antecipar o terceiro caminho, gravando a política recusada e a
    cláusula do ADR violada; B-2 da orquestração passou a exercitá-lo.
- id: OBJ-R7-C3
  status: FIXED
  summary: Exigir os códigos como chaves não prova agrupamento correto — dá para atribuir o total ao primeiro
    código e zerar os demais.
  owner: Bruno Nunes
  rationale: Todas as chaves presentes, cinco controles, hashes e defeitos idênticos, e as espécies fundidas
    mesmo assim. B-2 da fronteira passou a CONFERIR cada total por código contra a leitura — R-3 prova-se
    por valor, não por forma.
- id: OBJ-R7-C4
  status: FIXED
  summary: A recusa de float cobria os três controles globais e deixava o dinheiro por espécie sem contrato.
  owner: Bruno Nunes
  rationale: Um envelope com controles em string e totais por espécie como número JSON satisfaria a recusa
    escrita só para os três, e o produtor externo introduziria float sem passar pelo agregador local.
    B-2 da fronteira passou a contratar TODO campo monetário, porque R-4 e o ADR 0003 valem para todo
    dinheiro.
- id: OBJ-R7-C5
  status: FIXED
  summary: Conferir defeitos por contagem e tipo não detecta substituição — A duplicado e B omitido preserva
    ambas as contagens.
  owner: Bruno Nunes
  rationale: 'Contraexemplo válido e mais fino que a omissão que eu tinha coberto: cada entrada declarada
    recebe classificação única, B nunca é classificado, e juízo e rederivação concordam violando R-6.
    B-2 da fronteira passou a conferir POR IDENTIDADE, com valor original e posição, que é o que a leitura
    já produz.'
- id: OBJ-R8-C6
  status: FIXED
  summary: Minha correção de R7-C3 mandava conferir o total por código contra a leitura, mas a fronteira
    consumia um agregado só.
  owner: Bruno Nunes
  rationale: Mesmo erro da R4-C1, terceira vez — regra que compara um valor que ninguém se compromete
    a entregar. Com um mapa só, deslocar valores entre códigos seria aprovado por comparação consigo mesmo.
    Criada a capacidade "totais por código da leitura", produzida pela LEITURA e exigida pela fronteira;
    a referência não vem do agregador julgado, pelo mesmo motivo do ADR 0005.
- id: OBJ-R8-C7
  status: FIXED
  summary: A rederivação não contemplava a recusa por total divergente de uma espécie — transferir 1,00
    de A para B preserva tudo o mais.
  owner: Bruno Nunes
  rationale: 'B-1 da evidência passou a gravar os PARES de origens distintas que motivaram cada comparação:
    as duas listas de defeitos e os dois mapas de totais por código. Sem eles o pacote descreveria uma
    execução aceita, e o leitor dependeria do rótulo.'
- id: OBJ-R8-C8
  status: FIXED
  summary: A prova do agregador local exigia as chaves, não os valores — somar por descrição e zerar os
    demais códigos passaria.
  owner: Bruno Nunes
  rationale: E se esse agregador fornecesse a referência da fronteira, o defeito contaminaria a conferência
    também. B-2 da agregação passou a exigir cada VALOR por código conferido contra os totais da leitura.
- id: OBJ-R8-C9
  status: FIXED
  summary: Minha correção de R6-C4 conferia a política contra o ADR sem dizer como a SUFICIÊNCIA da precisão
    se estabelece.
  owner: Bruno Nunes
  rationale: MEDIDO — precisão 6 com HALF_EVEN e arredondamento final satisfaz presença, modo e granularidade,
    e devolve 7.85218E+10 no lugar de 78.521.752.562,12; prec=12 já perde o último centavo. O mínimo para
    esta âncora é 13 dígitos significativos. B-1 do contrato passou a RECUSAR precisão insuficiente no
    carregamento, em vez de deixá-la aparecer durante a agregação.
- id: OBJ-R8-C10
  status: FIXED
  summary: Minha correção de R3-C4 excluía o ilegível sem dizer o que são min e max quando NENHUM registro
    é legível.
  owner: Bruno Nunes
  rationale: Zero inventaria extremos inexistentes; exceção decidiria por conta própria que defeito de
    fonte interrompe o processamento, o que nem a tech-spec nem o juízo pediram. B-1 da agregação passou
    a marcar os extremos AUSENTES, com sum=0.00, reusando a representação de ausência que fronteira e
    evidência já tratam.
- id: OBJ-R9-C1
  status: FIXED
  summary: Minha correção de R8-C9 usou a precisão do TOTAL como prova de suficiência; a perda depende
    da escala dos intermediários.
  owner: Bruno Nunes
  rationale: Contraexemplo executado e confirmado — somar 78521752562,12 + 0,005 + 0,005 em prec=13 devolve
    78521752562,12; em prec=14, 78521752562,13. O centavo some ANTES da quantização, que é a falha da
    primeira camada do ADR 0003 atingindo a precisão que eu julgava suficiente. Suficiência para representar
    não é suficiência para somar.
- id: OBJ-R9-C2
  status: FIXED
  summary: Os dois mapas por código não tinham escala de comparação definida, nem estava dito de onde
    vem a soma global.
  owner: Bruno Nunes
  rationale: Um código de soma exata 2,345 podia chegar 2,345 de um lado e 2,34 do outro, com os dois
    planos cumpridos e a fronteira recusando. B-2 da fronteira passou a exigir soma EXATA nos dois mapas
    e comparação exata, e a soma global vem dos valores originais, nunca dos grupos arredondados — dois
    códigos de 2,345 dão 4,69 no total e 4,68 por grupo.
- id: OBJ-R9-C3
  status: FIXED
  summary: Conversibilidade para Decimal não define dinheiro legível — NaN, Infinity, 1_000 e 1e3 passam
    pelo construtor.
  owner: Bruno Nunes
  rationale: Verificado — os quatro são aceitos por Decimal(), e um NaN chegaria vivo aos extremos, onde
    min levanta InvalidOperation e transformaria defeito de UMA linha em ERRO da execução inteira. B-2
    da leitura passou a definir legível pela gramática monetária declarada, não pelo que o parser aceita.
- id: OBJ-R9-C4
  status: FIXED
  summary: A fronteira pode recusar só por tipo, e o pacote não preservava o tipo original dos campos
    monetários.
  owner: Bruno Nunes
  rationale: Serializar tudo como string faria 0.0 e '0.00' virarem insumos numericamente iguais, e a
    recusa legítima por número JSON deixaria de ser rederivável com controles e hashes coincidindo. B-1
    da evidência passou a preservar o tipo recebido, sem normalizar.
- id: OBJ-R9-C5
  status: FIXED
  summary: Meu plano corrigia em SILÊNCIO um número do ADR 0003 — declarei 13 dígitos onde o ADR diz 14,
    e o mesmo plano manda validar contra o ADR.
  owner: Bruno Nunes
  rationale: 'Violação de cerca que eu cometi, e a objeção estava certa em duas camadas. O ADR 0003 errou
    a conta — leu 7,9×10¹⁰ como 12 dígitos inteiros, são 11 — mas acertou o número, porque somar exige
    14 e não 13. Minha "correção" teria quebrado o que estava certo. Resolvido com o ADR 0007, que SUPERSEDES
    o 0003 e registra a precisão como valor DERIVADO: dígitos inteiros da âncora mais a escala dos intermediários,
    11 + 3 = 14. As três camadas do 0003 permanecem. CHECK_ADR=OK.'
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
