---
adr: "0012"
status: accepted
date: 2026-09-22
ground: brownfield
converge_pass: 2
spec_ref: "R-1"
supersedes: ""
superseded_by: ""
deciders: "Bruno Nunes"
---

# 0012 — the 2026-01 anchor has three independent measurements, not two

## Context

O ADR 0001 fixou a âncora de 2026-01 e registrou uma validação cruzada:

> Os três valores batem — contagem, total e hash do ZIP. **Duas medições
> independentes chegando ao mesmo número é o que distingue uma âncora de um
> palpite.**

Ao inventariar o disco procurando competências novas, apareceu um terceiro
arquivo que ninguém tinha citado: `evidence/_totais-controle.json`, no
`darkfactory-inss`. Ele traz os cinco controles de 2026-01, medidos em 50s.

O ADR 0001 não está errado — está **incompleto**. E o número de medições
independentes é exatamente o que sustenta a força da âncora, então vale
corrigir o registro.

## Decision

**São três medições independentes, não duas.**

| origem | count_linhas | sum_vl_liquido | segundos |
|---|---|---|---|
| `darkfactory-pda/evidence/_ancora.json` | 41.572.553 | 78.521.752.562,12 | 64 |
| `darkfactory-inss/evidence/_totais-controle.json` | 41.572.553 | 78.521.752.562,12 | 50 |
| `darkfactory-inss/contracts/layout.yaml` | 41.572.553 | 78.521.752.562,12 | — |

Os cinco controles batem nas três: contagem, soma, mínimo, máximo e linhas
inválidas. Códigos distintos, momentos distintos, o mesmo número.

Há uma quarta, acidental: um defeito em `scripts/baixar_competencia.py`
remediu 2026-01 durante um teste, gravando `_totais-202601.json` em 99s. Os
cinco controles bateram também. O defeito foi corrigido, e o arquivo ficou
porque medição que confirma é evidência, não lixo.

## Rejected reading

**Que `_totais-controle.json` fosse uma cópia do `layout.yaml`**, e não uma
medição.

É plausível: os dois vivem no mesmo repositório, trazem os mesmos números, e
um arquivo chamado "controle" bem poderia ser derivado do contrato.

O que a mata é o campo `segundos: 50`. Um arquivo copiado não registra quanto
tempo levou para varrer 11,6 GB. E o valor difere dos 64s da nossa medição,
o que descarta cópia de qualquer uma das duas — é varredura própria, em
máquina ou momento diferente.

## Evidence

```sh
python3 - <<'PY'
import json
for p in ("/home/nobru/darkfactory-pda/evidence/_ancora.json",
          "/home/nobru/darkfactory-inss/evidence/_totais-controle.json"):
    d = json.load(open(p, encoding="utf-8"))
    print(d["count_linhas"], d["sum_vl_liquido"], d.get("segundos"))
PY
```

observed output:

```
41572553 78521752562.12 64
41572553 78521752562.12 50
```

E a terceira, no contrato do outro repositório:

```sh
grep -A 3 '"2026-01"' /home/nobru/darkfactory-inss/contracts/layout.yaml
```

observed output:

```
  "2026-01":
    count_linhas: 41572553
    sum_vl_liquido: "78521752562.12"
```

## Consequences

- O ADR 0001 permanece **válido**: a âncora que ele fixou é a mesma. Este ADR
  acrescenta uma medição ao registro, não muda o número.
- A frase "duas medições independentes" do ADR 0001 está desatualizada. Quem
  citar a força da âncora deve citar **três**.
- Três medições não tornam a âncora imune: elas mediram o **mesmo arquivo**.
  Um defeito na fonte publicada apareceria nas três. O que elas descartam é
  erro de implementação, não erro de origem.
- Re-verify when: a fonte republicar 2026-01 — aí o sha256 do ZIP muda e as
  três medições passam a valer para um arquivo que não existe mais.
