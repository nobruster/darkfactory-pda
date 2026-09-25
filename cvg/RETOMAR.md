# Onde parei — 25/09/2026

Isto é para retomar sem reconstruir contexto. O histórico completo está no
`git log`; as decisões, nos ADRs (`cvg/docs/adrs/`, 0000–0016) e no
[`ESTADO.md`](ESTADO.md).

## A regra do dono que governa tudo agora

**Todo arquivo de fonte passa por landing → Bronze → Silver → Gold**, cada
camada lendo só da anterior (ADR 0015). O **Postgres** é a exceção deliberada:
carrega pelos **próprios arquivos**, com um parser independente, e é
**validado contra a Gold** antes do commit (ADR 0016).

## O que está em produção

| Onde | O quê | Versão | Linhas | Estado |
|---|---|---|---:|---|
| Landing | `s3a://landing/pda/beneficios-emitidos` + `_PROCEDENCIA.json` | — | 41.572.553 | 2026-01, soma 78.521.752.562,12 |
| Landing | `s3a://landing/pda/referencia/<arquivo>/sha256=<…>/` | — | 2 arquivos | os `.xlsx` do INSS como vieram, com prova |
| Bronze | `bronze/pda/beneficios-emitidos` | v4 | 41.572.553 | `INTEGRO` |
| Bronze | `bronze/pda/referencia/{dicionario_especies,glossario}` | v1 | 69 / 24 | linhas como vieram, lidas do landing |
| Silver | `silver/pda/beneficios-emitidos` | v5 | 41.572.553 | `INTEGRO` |
| Silver | `silver/pda/glossario` | v1 | 13 | descartes contados (1 cabeçalho, 10 vazias) |
| Silver | `silver/pda/especie` | v2 | 65 | nomes da Bronze do dicionário; **idêntica à v1** |
| Gold | `gold/pda/beneficios-emitidos` | v3 | 65 códigos | `INTEGRO` |
| Gold | `gold/pda/assuntos/{fat_especie,kpis_nacionais}` | v7 | 65 / 1 | `INTEGRO` |
| Gold | `gold/pda/referencia/{dim_especie,dim_termo}` | v1 | 65 / 13 | lidas da Silver |
| Postgres | `pda-postgres`, schema `ontologia` | carga 1 | 2/13/14/5/65 | carregado pelo caminho **antigo** (YAML) — recarregar pelo validado |

## A cadeia — onde termina

Ponta: **`task/postgres-validado-pela-gold`** (receita B). Loop `LOCAL_SETTLED`
na 1ª, lago intocado, AST dos testes OK, `PROCEDENCIA=OK`, 0 schemas de
teste no Postgres. **A suíte inteira ficou rodando ao parar** — conferir o
resultado no fim de `/tmp`… ou rodar de novo (abaixo). Última medida
completa: 534 passed (receita A).

## Decisões do dono registradas hoje

- Todo arquivo pelas quatro camadas (ADR 0015); Postgres pelos próprios
  arquivos, validado contra a Gold (ADR 0016).
- **RMV (30, 40) fica em `Outros`**, como no contrato de 2026-09-23 — o
  dicionário do INSS listá-lo entre os Amparos não muda `grupos_especie`.
  Questão encerrada.
- Competências de 2025: **2025-09 primeiro** (mesmo layout de 2026-01).
  2025-07/08 não têm código de espécie (só a descrição truncada) — ADR próprio
  depois.

## Próximos passos, em ordem

1. **Conferir a suíte da receita B** e publicar o Postgres pelo caminho novo
   (`projetar_validado`, schema `ontologia`) — validado contra a Gold.
2. **Nome oficial nas tabelas da Gold** (pedido do dono): a Gold principal e a
   `fat_especie` ganham `nome_oficial`, lido da Silver `especie`. **Decidir
   antes:** `tests/test_gold.py:369` confere as colunas da Gold principal
   contra uma tupla LITERAL — evoluir a tabela exige exceção nomeada nesse
   teste; a alternativa é publicar tabelas novas ao lado. Totais por código
   têm de continuar batendo com a âncora.
3. **Contrato de 2025-09**: rascunho medido em `~/rascunhos/competencia-202509.yaml`
   (âncora 41.376.846 / 73.485.964.937,46, sha256 e mapa de colapsos
   conferidos) — aprovações do dono `PENDENTE`.
4. **Receita C, limpeza**: retirar `publicar_especie` e `projetar_ontologia`
   antigas por lista nomeada; YAML só com conceitos; registrar o caminho da
   Gold no certificado do Postgres; guarda de `--rejeitos` dentro do destino.
5. **Publicar**: `git push` das branches `task/*` até a ponta — é do dono.

## Como retomar

```bash
# de dentro do WSL Ubuntu-24.04
cd ~/darkfactory-pda
git checkout task/postgres-validado-pela-gold
docker compose -f infra/docker-compose.yml up -d
python3 scripts/verificar_procedencia.py | tail -1     # PROCEDENCIA=OK
docker compose -f infra/docker-compose.yml exec -T spark sh -c \
  'cd /app && python3 -m pytest -q -rsx -p no:cacheprovider tests/ 2>&1 | tail -3'
```

## Armadilhas desta fábrica

- Nunca montar comando por `wsl.exe -- bash -lc '… $var …'`: o shell do
  Windows expande a variável vazia. Script em arquivo, sempre.
- **Árvore limpa não prova que o loop terminou.** Nada escreve no repositório
  com `cvg loop` vivo.
- **Plano contraditório contra teste selado** — quatro vezes nesta fábrica. Antes
  de despachar: `~/checar_cenarios_listados.py <receita>` (todo cenário de eval
  existe ou está na lista da tarefa) e um agente caçando contradições.
- Medir antes de escrever a premissa (o layout mudou em 2025-09; `ler_xlsx`
  descarta linhas vazias; a `dim_especie` não tem sha256).
- Escrever script com o editor exige ler o arquivo antes — senão roda a cópia
  velha. As guardas de árvore pegaram isso sem estrago.
