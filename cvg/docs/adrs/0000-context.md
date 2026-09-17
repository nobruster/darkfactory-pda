---
adr: "0000"
status: accepted
date: 2026-09-17
ground: greenfield
converge_pass: 2
spec_ref: "R-1, R-3"
supersedes: ""
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0000 — Context: the ground we stand on

## Terrain

**Greenfield.** A fábrica descrita pela tech-spec ainda não existe: não há
pipeline, contrato nem juiz construídos para esta demanda. Os ADRs desta
pasta registram as restrições que a especificação impõe, não fatos observados
num sistema em operação.

O que existe é **referência**, não base: o repositório traz um juiz de exemplo
(`fabrica/`) e uma fábrica de produção separada (`darkfactory-inss`) de onde
a doutrina vem.

## Given surface

Verificado nesta máquina, não presumido:

- `fabrica/judge/golden_match.py` — comparador com 6 classificações e zero
  tolerância. **12 testes passam**, e eles provam que o juiz *acusa*, não que
  aprova.
- `fabrica/contracts/oracles/exemplo-lote-001.json` — a forma de um oráculo:
  `approved_by`, `aggregate`, `money_fields`, `key_fields`.
- `converge/bin/cvg` + `task-spec-3.8.1/bin/taskspec` — o motor de passes.
  `DOCTOR_HOST=OK`: esta máquina assina, faz bind, loop e settle.
- ⚠️ Nenhuma fonte de dados real está conectada. **Nenhuma âncora foi
  medida.**

## Build surface

O que os passes seguintes ainda precisam construir:

- Leitura da competência e produção do agregado
- Medição da âncora direto na origem, independente do pipeline
- Adaptação do juiz ao contrato desta demanda
- Pacote de evidência por execução

Decidido no Pass 3, não aqui: motor de processamento, linguagem, formato de
armazenamento.

## Spec

[`../tech-spec/tech-spec-exemplo-fabrica.md`](../tech-spec/tech-spec-exemplo-fabrica.md)

⚠️ **Sign-off ainda `pending`** — a spec não é canônica. O GAP-001 (qual
competência será a primeira âncora, e quem confirma) permanece aberto e
bloqueia R-1.

Estes ADRs registram o terreno enquanto essa decisão não vem. Eles **não
autorizam** a descida ao Pass 3: o veredito de `cvg intent` é que autoriza, e
ele está em `CHECK_TECH_SPEC=FAIL`.
