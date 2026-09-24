> Projetado de `LEG-ONTOLOGIA.md` pelo Seamwise.
> **Não edite aqui** — edite a recipe e rode `seamwise plan`.
> origem sha256: `e3f026e4a429111280a2203a71e48bb6d0a45fec70b211ff2b089c8bb9a20c59`

---

---
schema_version: 1
kind: capability-leg
claim: derived
id: LEG-ONTOLOGIA
seam_id: SEAM-ONTOLOGIA
swimlane_id: LANE-ONTOLOGIA
observable_state: Ontologia carregada e conferida
proof: Carregador confere 65 nomes, 13 termos e o sha256 contra _raw/.
requires: []
produces:
- ontologia carregada
tasks:
- id: T-20260924-ontologia-versionada
  title: Ontologia versionada dos benefícios emitidos, reconferida contra os bytes do INSS
  goal: Ter num arquivo versionado os conceitos da fonte — colunas, termos do glossário, espécies com
    o nome oficial e o grupo de cada uma — e um carregador que só aceita a ontologia se ela confere com
    os bytes de _raw/. Para rodar testes, o ÚNICO comando liberado ao agente é `docker compose -f infra/docker-compose.yml
    exec -T spark python3 -m pytest <arquivo> -k <cenarios>`.
  done_condition: src/ontologia/beneficios-emitidos.yaml existe; carregar_ontologia devolve a ontologia
    com 14 colunas, 13 termos e 65 espécies quando ela confere com os dois .xlsx de /dados/_raw e com
    o contrato, e recusa em qualquer divergência ou ausência; os testes de tests/test_ontologia.py passam.
  effort: M
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
  - src/ontologia/beneficios-emitidos.yaml
  - src/medalhao/ontologia.py
  - tests/test_ontologia.py
  behavior:
  - id: B-1
    given: os bytes oficiais em /dados/_raw (dicionario-especies-beneficio.xlsx e glossario-beneficios-emitidos.xlsx,
      com sha256 em /dados/_raw/CHECKSUMS.txt) e o contrato contracts/competencia-202601.yaml com grupos_especie
    when: carregar_ontologia lê src/ontologia/beneficios-emitidos.yaml
    then: 'devolve a ontologia com: as duas fontes e o sha256 de cada, que confere com o arquivo e com
      a linha do CHECKSUMS.txt — cujas linhas têm o formato ''<sha256>  _raw/<arquivo>'', casadas pelo
      NOME do arquivo, porque no contêiner o diretório é /dados/_raw; as 14 colunas do CSV, cada uma por
      POSIÇÃO de 0 a 13 com o cabeçalho e o termo do glossário que representa — o cabeçalho declarado
      de cada posição é IGUAL ao da primeira linha (latin-1, separador '';'') de todo D.SDA.PDA.003.EMI.*.csv
      em /dados/_raw; as posições 12 e 13 são as duas ''Espécie'', com papel codigo e descricao_truncada
      (ADR 0002), e nenhuma ligação é feita pelo nome; os 13 termos com a descrição IGUAL à do glossário;
      as 65 espécies, código de 2 dígitos em texto, com o nome oficial IGUAL, caractere a caractere e
      sem normalização, ao texto extraído do dicionário (medido: nenhum dos 65 tem espaço nas pontas nem
      está fora de NFC), e o grupo de cada uma lido de contrato.grupos_especie.grupos, por referência.
      O atributo sha256 da ontologia é o sha256 do JSON canônico (chaves ordenadas, sem espaços) do conteúdo
      RESOLVIDO — fontes, colunas, termos, espécies com o grupo vindo do contrato —, para que uma mudança
      de grupo no contrato mude a versão. Os .xlsx são lidos só com a biblioteca padrão (zipfile e xml),
      sem openpyxl, porque o contêiner não tem rede.'
  - id: B-2
    given: uma ontologia, uma fonte ou um contrato que não conferem, ou que não foram lidos
    when: carregar_ontologia confere
    then: 'recusa, nunca devolve ontologia parcial: sha256 divergente do arquivo ou do CHECKSUMS.txt,
      código a mais ou a menos que o dicionário, nome diferente do dicionário, código sem grupo ou em
      dois grupos, termo que o glossário não tem ou com descrição diferente, cabeçalho diferente do CSV
      na mesma posição, posição de coluna faltando ou repetida, carregar_contrato devolvendo a string
      NAO_MEDIDO ou grupos_especie ausente — cada caso com o motivo nomeado; zero espécies lidas, zero
      termos lidos, nenhum CSV em /dados/_raw ou arquivo ausente devolvem NAO_MEDIDO, não OK (Regra 9).
      Os cenários de recusa usam cópias em tmp_path, nunca alteram /dados/_raw. Nenhum cenário usa skip,
      xfail ou importorskip, nem retorna antes de afirmar: fonte ausente no ambiente de teste FALHA o
      teste.'
  evals:
  - id: eval_1
    description: A ontologia real confere com o INSS e com o contrato
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in ontologia_real_confere
      sessenta_e_cinco_especies catorze_colunas_por_posicao sha256_cobre_os_grupos; do python3 -m pytest
      --collect-only -q tests/test_ontologia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
      exit 1; }; done; python3 -m pytest -q tests/test_ontologia.py -k "ontologia_real_confere or sessenta_e_cinco_especies
      or catorze_colunas_por_posicao or sha256_cobre_os_grupos"'
    verifies:
    - B-1
  - id: eval_2
    description: Divergência recusa com motivo
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in sha256_divergente_recusa
      checksums_divergente_recusa nome_diferente_recusa codigo_sem_grupo_recusa codigo_em_dois_grupos_recusa
      termo_fora_do_glossario_recusa descricao_de_termo_diferente_recusa cabecalho_trocado_recusa posicao_repetida_recusa;
      do python3 -m pytest --collect-only -q tests/test_ontologia.py -k "$c" 2>/dev/null | grep -q "::"
      || { echo "EVAL=CENARIO_AUSENTE_$c"; exit 1; }; done; python3 -m pytest -q tests/test_ontologia.py
      -k "sha256_divergente_recusa or checksums_divergente_recusa or nome_diferente_recusa or codigo_sem_grupo_recusa
      or codigo_em_dois_grupos_recusa or termo_fora_do_glossario_recusa or descricao_de_termo_diferente_recusa
      or cabecalho_trocado_recusa or posicao_repetida_recusa"'
    verifies:
    - B-2
  - id: eval_3
    description: Ausência não é medição
    bash: docker compose -f infra/docker-compose.yml exec -T spark sh -c 'for c in dicionario_vazio_nao_medido
      fonte_ausente_nao_medido contrato_nao_medido_recusa le_xlsx_sem_dependencia; do python3 -m pytest
      --collect-only -q tests/test_ontologia.py -k "$c" 2>/dev/null | grep -q "::" || { echo "EVAL=CENARIO_AUSENTE_$c";
      exit 1; }; done; python3 -m pytest -q tests/test_ontologia.py -k "dicionario_vazio_nao_medido or
      fonte_ausente_nao_medido or contrato_nao_medido_recusa or le_xlsx_sem_dependencia"'
    verifies:
    - B-1
    - B-2
  anti_patterns:
  - action: ligar coluna a termo pelo nome do cabeçalho
    reason: os nomes divergem e as duas Espécie têm cabeçalho idêntico (ADR 0002)
    instead: ligar pela posição de 0 a 13
  - action: copiar os grupos de espécie para dentro da ontologia
    reason: duas fontes do mesmo fato divergem em silêncio
    instead: referenciar grupos_especie do contrato e conferir a cobertura
  - action: corrigir ou abreviar o nome oficial para caber em 20 caracteres
    reason: o nome oficial é o que a ontologia acrescenta; o truncado já está na Silver
    instead: guardar o nome exatamente como o dicionário publica
  do_not_touch:
  - _raw
  - cvg/docs/adrs
  - contracts
  - src/pda
  - infra
  rollback: Remover os três arquivos criados; nada mais depende deles até a próxima tarefa.
  observability: ontologia recusada por divergência com os bytes do INSS
source_seam_sha256: 794d7da3d10d423b43beb73e9e11601fc073792e7d470e0a1307506437dafb9e
---
# Ontologia carregada e conferida

## Observable proof

Carregador confere 65 nomes, 13 termos e o sha256 contra _raw/.

## Runnable leaves

- `T-20260924-ontologia-versionada` — Ontologia versionada dos benefícios emitidos, reconferida contra os bytes do INSS: src/ontologia/beneficios-emitidos.yaml existe; carregar_ontologia devolve a ontologia com 14 colunas, 13 termos e 65 espécies quando ela confere com os dois .xlsx de /dados/_raw e com o contrato, e recusa em qualquer divergência ou ausência; os testes de tests/test_ontologia.py passam.

The leg names a capability state, not an activity. Each leaf owns one coherent,
independently provable done-condition.
