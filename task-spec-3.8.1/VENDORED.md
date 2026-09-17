# task-spec 3.8.1 — a versão que o Converge exige

Esta pasta **não é um submódulo**. É uma cópia dos arquivos, versionada direto
neste repositório.

## Por que existem duas versões do task-spec

| Pasta | Versão | Para quê |
|---|---|---|
| [`../task-spec/`](../task-spec/) | 3.9.0 | TaskMesh — o daemon Go com `--frontier --mode autonomous` |
| **`./` (esta)** | **3.8.1** | **O que o `cvg` aceita** |

O Converge 0.2 exige `3.8.x` **exato**, não mínimo
(`converge/bin/cvg:143-149` — `case "$version" in 3.8.*`). Com a 3.9.0 ele
recusa:

```console
$ CVG_TASKSPEC_BIN=.../task-spec/bin/taskspec cvg doctor host
error: incompatible Task-Spec engine '3.9.0' — Converge 0.2 requires 3.8.x
```

Com esta, funciona:

```console
$ CVG_TASKSPEC_BIN=.../task-spec-3.8.1/bin/taskspec cvg doctor host
== cvg doctor host · can this machine run the delegation path? ==
  ok  git · bash · bash 4+ · python3 · sha256
```

A 3.9.0 **não foi removida** porque traz o TaskMesh — a peça que percorreria o
backlog sozinho, ausente na 3.8.x.

## Como usar

```bash
export CVG_TASKSPEC_BIN="$PWD/task-spec-3.8.1/bin/taskspec"
cvg doctor host
```

Sem essa variável, o `cvg` procura `taskspec` no `PATH` — e se achar a 3.9.0,
recusa.

## Procedência

| | |
|---|---|
| Origem | [github.com/luanmorenommaciel/task-spec](https://github.com/luanmorenommaciel/task-spec) |
| Tag | `v3.8.1` |
| Commit | `351c3990` |
| Autor | Luan Moreno Medeiros Maciel |
| Licença | MIT — ver [`LICENSE`](LICENSE) |
| Vendorizado em | 17/09/2026 |

O histórico git foi removido; os 366 arquivos são os da tag `v3.8.1`.
**Nenhum arquivo de código foi alterado.**

## Ao atualizar o Converge

Se um dia o Converge passar a aceitar `3.9.x`, esta pasta deixa de ser
necessária — apague-a e aponte `CVG_TASKSPEC_BIN` para `../task-spec/`.
Verifique com `grep CVG_TASKSPEC_REQUIRED converge/bin/cvg`.
