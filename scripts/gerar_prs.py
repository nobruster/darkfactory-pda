"""Gera a descrição de cada PR a partir dos dados reais do repositório.

Não inventa número: lê os receipts, conta os testes que cada branch
acrescenta, e extrai do pda-recipe.yaml as objeções do Pass 4 que viraram
código naquela tarefa.

Cada arquivo traz o link do GitHub que abre o formulário de PR já apontando
base e head — não é preciso `gh` instalado.

Token: PRS=GERADOS|ERRO
"""
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = "nobruster/darkfactory-pda"
SAIDA = Path("cvg/prs")
RECEITA = Path("cvg/swimlanes/pda-recipe.yaml")

# ordem de dependência: cada uma parte da anterior
CADEIA = [
    ("contrato-ancora", "contrato", "SEAM-CONTRATO"),
    ("leitura-posicional", "leitura", "SEAM-LEITURA"),
    ("agregacao-exata", "agregacao", "SEAM-AGREGACAO"),
    ("envelope-fronteira", "envelope", "SEAM-FRONTEIRA"),
    ("juizo-classifica", "juizo", "SEAM-JUIZO"),
    ("evidencia-packet", "evidencia", "SEAM-EVIDENCIA"),
    ("orquestra-desfecho", "orquestracao", "SEAM-ORQUESTRACAO"),
]


def _git(*args: str) -> str:
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    return r.stdout.strip()


def _stat(branch: str, base: str, modulo: str) -> tuple[int, int, int]:
    """Linhas totais, de código, e arquivos que a branch acrescenta.

    Separa código de evidência: a orquestração acrescenta 2746 linhas, das
    quais 1432 são dois pacotes de evidência da execução real. Mostrar só o
    total faria o revisor achar que o módulo tem 3x o tamanho dos outros.
    """
    saida = _git("diff", "--shortstat", f"{base}..{branch}")
    linhas = re.search(r"(\d+) insertion", saida)
    arquivos = re.search(r"(\d+) file", saida)

    codigo = 0
    for alvo in (f"src/pda/{modulo}.py", f"tests/test_{modulo}.py"):
        n = _git("diff", "--numstat", f"{base}..{branch}", "--", alvo)
        m = re.match(r"(\d+)", n)
        if m:
            codigo += int(m.group(1))

    return (int(linhas.group(1)) if linhas else 0,
            codigo,
            int(arquivos.group(1)) if arquivos else 0)


def _testes(branch: str, modulo: str) -> int:
    saida = _git("show", f"{branch}:tests/test_{modulo}.py")
    return len(re.findall(r"^def test_", saida, re.M))


def _receipt(tarefa: str) -> dict:
    p = Path(f"cvg/receipts/T-20260921-{tarefa}.json")
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _sem_acento(s: str) -> str:
    import unicodedata
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower())
        if unicodedata.category(c) != "Mn"
    )


def _objecoes(seam: str) -> list[tuple[str, str]]:
    """As objeções do Pass 4 cujo texto cita esta costura.

    O texto das objeções escreve a costura de várias formas — "AGREGAÇÃO"
    em maiúscula e com acento, "agregação" no meio da frase, "B-2 da
    agregação". Comparar sem acento e sem caixa é o que faz o filtro
    achar: a primeira versão devolvia zero para quatro costuras que
    claramente tinham objeções.
    """
    if not RECEITA.exists():
        return []
    texto = RECEITA.read_text(encoding="utf-8")
    bloco = texto[texto.index("\nobjections:"):] if "\nobjections:" in texto else ""
    achadas = []
    lane = _sem_acento(seam.replace("SEAM-", ""))
    for m in re.finditer(
        r"- id: (OBJ-\S+).*?summary: >-\n(.*?)\n    owner:.*?rationale: >-\n(.*?)(?=\n  - id:|\ncontentions:|\Z)",
        bloco, re.S
    ):
        oid, resumo, razao = m.group(1), " ".join(m.group(2).split()), m.group(3)
        if lane in _sem_acento(resumo + " " + razao):
            achadas.append((oid.replace("OBJ-", ""), resumo))
    return achadas


def main() -> int:
    if not Path(".git").exists():
        print("  rode da raiz do repositório", file=sys.stderr)
        print("PRS=ERRO")
        return 1

    SAIDA.mkdir(parents=True, exist_ok=True)
    base = "main"
    gerados = 0

    for i, (tarefa, modulo, seam) in enumerate(CADEIA, 1):
        branch = f"task/{tarefa}"
        if not _git("rev-parse", "--verify", branch):
            print(f"  {tarefa:<22} branch ausente — pulada")
            continue

        linhas, codigo, arquivos = _stat(branch, base, modulo)
        n_testes = _testes(branch, modulo)
        rec = _receipt(tarefa)
        objs = _objecoes(seam)

        link = (f"https://github.com/{REPO}/compare/"
                f"{base}...{branch}?expand=1")

        corpo = [
            f"# T-20260921-{tarefa}",
            "",
            f"Costura `{seam}` · módulo `src/pda/{modulo}.py`",
            "",
            "| | |",
            "|---|---|",
            f"| base | `{base}` |",
            f"| head | `{branch}` |",
            f"| código | {codigo} linhas (`{modulo}.py` + testes) |",
            f"| diff total | {linhas} linhas em {arquivos} arquivo(s) |",
            f"| testes | {n_testes} em `tests/test_{modulo}.py` |",
            f"| selo | Tier 1 — HMAC v3 |",
            f"| veredito | `{rec.get('result', '?')}` · "
            f"path_policy `{rec.get('evaluation', {}).get('path_policy', '?')}` |",
            "",
        ]

        if objs:
            corpo += [
                "## As objeções do Pass 4 que viraram código aqui",
                "",
                "| # | O que faltava |",
                "|---|---|",
            ]
            for oid, resumo in objs[:6]:
                corpo.append(f"| `{oid}` | {resumo[:130]} |")
            corpo.append("")

        corpo += [
            "## Como conferir",
            "",
            "```bash",
            f"git checkout {branch}",
            f"pytest tests/test_{modulo}.py -q",
            "```",
            "",
            "## Abrir o PR",
            "",
            f"{link}",
            "",
            "---",
            "",
            "⚠️ Escrito por um agente sob contrato selado no Pass 5, com escopo",
            "de escrita declarado. O agente **não pode** editar a Task-Spec nem",
            "os testes que o avaliam.",
        ]

        destino = SAIDA / f"{i:02d}-{tarefa}.md"
        destino.write_text("\n".join(corpo) + "\n", encoding="utf-8")
        print(f"  {tarefa:<22} {codigo:>5} cod · {n_testes:>3} testes · "
              f"{len(objs)} objeção(ões)")
        gerados += 1
        base = branch  # o próximo compara contra este

    print()
    print(f"  {gerados} descrição(ões) em {SAIDA}/")
    print("  cada arquivo traz o link que abre o formulário do PR")
    print("PRS=GERADOS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
