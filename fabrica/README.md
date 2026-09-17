# Fábrica — Etapa 1: o juiz

**Status:** juiz funcionando, 12 testes passando.
**Próximo:** ligar no seu pipeline real.

Isto é a **Etapa 1** do roadmap: o oráculo e o golden-match. Sem o juiz,
automação é só um agente rodando solto.

---

## Rodar agora

```bash
cd fabrica

# 1. Provar que o juiz falha quando deve
python -m pytest tests/ -v

# 2. Ver o veredito num resultado correto
python judge/run_judge.py \
  --oracle contracts/oracles/exemplo-lote-001.json \
  --actual /caminho/do/resultado.json
```

Saída: `evidence/<batch_id>/golden-match.json`, e exit **0** (verde) ou **1** (empacado).

---

## O que tem aqui

```
fabrica/
├── contracts/
│   ├── oracles/          🔒 A VERDADE. Nunca edite para um portão passar.
│   └── schemas/
├── judge/
│   ├── golden_match.py   o comparador — 6 classificações, zero tolerância
│   └── run_judge.py      Fase 0 (intake) + Fase 6 (veredito)
├── tests/
│   └── test_judge_fails_red.py   ⭐ prova que o juiz ACUSA
└── evidence/             pacotes por execução
```

---

## O teste mais importante

`tests/test_judge_fails_red.py` não testa se o juiz aprova. Testa se ele **acusa**.

> Um portão que nunca falhou não é um portão — é decoração que dá falsa confiança.

O que ele corrompe de propósito, e exige que seja pego:

| Teste | O que prova |
|---|---|
| `test_um_centavo_a_menos_e_pego` | O caso que justifica a fábrica |
| `test_arredondamento_errado_e_pego` | HALF_EVEN vs HALF_UP — o erro estruturalmente verde |
| `test_linha_faltando_e_pega` | Registro ausente |
| `test_linha_extra_e_pega` | Duplicata de reprocessamento |
| `test_float_em_campo_monetario_e_recusado` | float perde centavo em silêncio |
| `test_comparar_registros_sem_chave_e_recusado` | Comparar por posição é prova falsa |

E os dois que ensinam a fábrica a saber **quem** errou:

| Teste | O que prova |
|---|---|
| `test_sistema_atual_errado_e_classificado_como_legacy_defect` | Você certo, produção errada → `CONFIRMED_LEGACY_DEFECT` |
| `test_copiar_o_erro_do_sistema_atual_...` | Copiou o bug do legado → `MODERN_DEFECT`, **bloqueia** |

O segundo é o motivo de se ler o **contrato**, nunca o código antigo.

---

## As seis classificações

Toda diferença recebe exatamente uma:

| Código | Significa | Bloqueia? |
|---|---|---|
| `CONFIRMED_SOURCE_DEFECT` | A fonte mentiu | Não — explicado |
| `CONFIRMED_LEGACY_DEFECT` | **O sistema em que você confiava** está errado | Não — explicado |
| `APPROVED_BEHAVIOR_CHANGE` | Mudou de propósito, aprovado | Não — explicado |
| `MODERN_DEFECT` | Seu código está errado | **Sim** |
| `CONTRACT_AMBIGUITY` | O contrato não decide | **Sim** |
| `UNRESOLVED` | Não classificado | **Sim** |

Não existe parâmetro de tolerância em lugar nenhum. É deliberado:
tolerância configurável é como um centavo inexplicado vira um centavo aceito.

---

## Ligar no seu pipeline

### 1. Monte o oráculo

Copie `contracts/oracles/exemplo-lote-001.json` e preencha com um lote real
cujo resultado você **conferiu na mão**.

Campos obrigatórios:
- `approved_by` — quem do negócio confirmou. Sem isso o juiz recusa.
- `aggregate` — os números finais
- `money_fields` — quais campos são dinheiro (viram Decimal exato)
- `key_fields` — a chave de negócio, se for comparar linha a linha

> Pegue um lote **do passado**, cujo número final já foi validado e fechado.
> É o oráculo mais barato que existe — já foi conferido, só falta congelar.

### 2. Faça o pipeline emitir JSON

```json
{
  "aggregate": {"valor_liquido": "1237926.25", "linhas_validas": "998"},
  "records": [{"id_venda": "V001", "valor_liquido": "1500.00"}]
}
```

**Dinheiro como string ou Decimal, nunca float.** O juiz recusa float —
`0.1 + 0.2 != 0.3` em binário, e é assim que um centavo some.

### 3. Rode o juiz no fim do pipeline

```bash
python judge/run_judge.py --oracle contracts/oracles/lote-001.json \
                         --actual saida/resultado.json
echo $?   # 0 = verde, 1 = empacado
```

### 4. Comparando com o sistema atual

Se existe um sistema rodando hoje que você quer substituir:

```bash
python judge/run_judge.py --oracle ... --actual novo.json --reference atual.json
```

Aí o juiz responde as **duas** perguntas separadamente, e consegue dizer
`CONFIRMED_LEGACY_DEFECT` quando **você** está certo e a produção está errada.

---

## As regras

1. **Nunca edite o oráculo para ficar verde.** Editar o juiz é a manobra mais
   perigosa que existe. Se o número mudou legitimamente, alguém do negócio
   re-aprova e o `approved_at` muda junto.
2. **Dinheiro é Decimal.** Nunca float.
3. **Prove vermelho antes de confiar no verde.** Rode os testes.
4. **Sem oráculo, não se constrói.** A Fase 0 recusa em segundos.
5. **Zero tolerância.** Classifique a diferença ou conserte o pipeline.

---

## Próximas etapas

| Etapa | O que entra | Status |
|---|---|---|
| 1 | **O juiz** — oráculo + golden-match | ✅ **Feito** |
| 2 | Fases 0, 3 e 6 no seu pipeline real | ← você está aqui |
| 3 | Determinismo (mesmo hash) + ambiente limpo | |
| 4 | O loop (fila, tick, stall, cron) | |
| 5 | Evidência + PR + revisão matinal | |
| 6 | Apagar as luzes | |

Detalhe de cada etapa em `ESTUDO/[C] Como Construir uma Fabrica Autonoma.md`.
