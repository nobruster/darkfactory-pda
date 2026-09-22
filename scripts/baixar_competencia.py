"""Baixa uma competência da fonte pública e a mede — sem publicar nada.

Cada competência nova é um ponto a mais na série, e é disso que os gates de
série (ADR 0010) e de acumulado (ADR 0011) dependem: com seis pontos qualquer
limiar é palpite.

O que ele faz, nesta ordem:

  1. baixa o ZIP da fonte pública
  2. confere o sha256 e grava em _raw/CHECKSUMS.txt
  3. extrai o CSV e grava o sha256 dele também — a âncora é medida no CSV,
     e sem o par o CSV extraído poderia ser trocado sem detecção (R2-C3)
  4. aplica W-1: chmod 444 nos arquivos, 555 no diretório
  5. mede com os scripts que já existem, um por vez
  6. grava evidence/_totais-<AAAAMM>.json

Não toca no contrato, não julga nada, não publica. Medir é o passo anterior
a decidir — a âncora de uma competência nova nasce sem aprovação, e alguém
do negócio precisa confirmá-la antes que ela valha (Regra 2).

Uso:
    python3 scripts/baixar_competencia.py 2026-04
    python3 scripts/baixar_competencia.py 2026-04 --so-medir   (já baixada)

Token: COMPETENCIA=MEDIDA|EXISTE|ERRO
"""
import argparse
import hashlib
import re
import subprocess
import sys
import time
import zipfile
from pathlib import Path

BASE = "https://armazenamento-dadosabertos.s3.sa-east-1.amazonaws.com/"
RAW = Path("_raw")
EVIDENCIA = Path("evidence")

MEDIDORES = [
    ("medir_ancora.py", "ANCORA"),
    ("medir_gramatica.py", "GRAMATICA"),
    ("medir_codigos.py", "CODIGOS"),
    ("medir_colapso.py", "COLAPSO"),
    ("medir_sinal.py", "SINAL"),
    ("medir_layout.py", "LAYOUT"),
]


def _sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _destravar() -> None:
    """W-1 exige 444/555; para escrever em _raw é preciso destravar antes."""
    if RAW.is_dir():
        RAW.chmod(0o755)
        for p in RAW.iterdir():
            if p.is_file():
                p.chmod(0o644)


def _travar() -> None:
    """Reaplica W-1: a escrita em Unix é do DIRETÓRIO, não do arquivo."""
    for p in RAW.iterdir():
        if p.is_file():
            p.chmod(0o444)
    RAW.chmod(0o555)


def baixar(comp: str) -> tuple[Path, Path]:
    aaaamm = comp.replace("-", "")
    nome_zip = f"D.SDA.PDA.003.EMI.{aaaamm}.CSV.ZIP"
    nome_csv = f"D.SDA.PDA.003.EMI.{aaaamm}.csv"
    zip_path = RAW / nome_zip
    csv_path = RAW / nome_csv

    if csv_path.exists():
        print(f"  {nome_csv} já existe — pulando download")
        return zip_path, csv_path

    RAW.mkdir(exist_ok=True)
    _destravar()

    url = BASE + nome_zip
    print(f"  baixando {url}")
    t0 = time.time()
    rc = subprocess.call(["curl", "-fSL", "--progress-bar", "-o", str(zip_path), url])
    if rc != 0 or not zip_path.exists():
        print(f"  download falhou (rc={rc})", file=sys.stderr)
        raise SystemExit(1)
    print(f"  {zip_path.stat().st_size / 1e6:.0f} MB em {time.time() - t0:.0f}s")

    print("  extraindo...")
    with zipfile.ZipFile(zip_path) as zf:
        interno = zf.namelist()[0]
        with zf.open(interno) as origem, csv_path.open("wb") as destino:
            while bloco := origem.read(1 << 20):
                destino.write(bloco)
    print(f"  {csv_path.stat().st_size / 1e9:.1f} GB extraídos")

    return zip_path, csv_path


def registrar_hashes(zip_path: Path, csv_path: Path) -> None:
    """Os DOIS hashes. Só o do ZIP não basta: a âncora é medida no CSV."""
    arquivo = RAW / "CHECKSUMS.txt"
    linhas = []
    if arquivo.exists():
        linhas = [
            l for l in arquivo.read_text(encoding="utf-8").splitlines()
            if l.strip() and zip_path.name not in l and csv_path.name not in l
        ]

    for p in (zip_path, csv_path):
        if p.exists():
            print(f"  sha256 {p.name}...", flush=True)
            linhas.append(f"{_sha256(p)}  _raw/{p.name}")

    _destravar()
    arquivo.write_text("\n".join(sorted(linhas)) + "\n", encoding="utf-8")


def medir(comp: str, csv_path: Path) -> bool:
    aaaamm = comp.replace("-", "")
    todos_ok = True

    for script, token in MEDIDORES:
        caminho = Path("scripts") / script
        if not caminho.exists():
            print(f"  {token:<12} script ausente — pulado")
            continue

        # os medidores têm o CSV de 2026-01 fixo; passa o caminho quando aceitam
        cmd = [sys.executable, str(caminho)]
        if script == "medir_ancora.py":
            cmd += [str(csv_path), "--coluna-valor", "9",
                    "--out", str(EVIDENCIA / f"_totais-{aaaamm}.json")]

        print(f"  {token:<12} rodando...", flush=True)
        r = subprocess.run(cmd, capture_output=True, text=True)
        ultima = (r.stdout.strip().splitlines() or ["(sem saída)"])[-1]
        print(f"  {token:<12} {ultima}")
        if "=ERRO" in ultima or "=NAO_MEDIDO" in ultima:
            todos_ok = False

    return todos_ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("competencia", help="no formato AAAA-MM, ex.: 2026-04")
    ap.add_argument("--so-medir", action="store_true",
                    help="não baixa; mede o que já está em _raw/")
    args = ap.parse_args()

    if not re.match(r"^\d{4}-\d{2}$", args.competencia):
        print("  competência precisa ser AAAA-MM", file=sys.stderr)
        print("COMPETENCIA=ERRO")
        return 1

    aaaamm = args.competencia.replace("-", "")

    # Já medida? Em dois lugares: _totais-<AAAAMM>.json (o padrão deste
    # script) e _ancora.json, que é como a competência 2026-01 foi gravada
    # antes deste script existir. Remedir 41 milhões de linhas para chegar
    # ao mesmo número é desperdício, não verificação.
    ja_medidas = {EVIDENCIA / f"_totais-{aaaamm}.json"}
    ancora = EVIDENCIA / "_ancora.json"
    if ancora.exists():
        import json as _json
        try:
            d = _json.loads(ancora.read_text(encoding="utf-8"))
            if aaaamm in str(d.get("arquivo", "")):
                ja_medidas.add(ancora)
        except Exception:  # noqa: BLE001
            pass

    for p in ja_medidas:
        if p.exists():
            print(f"  {p} já existe — nada a fazer")
            print("COMPETENCIA=EXISTE")
            return 0

    print(f"=== competência {args.competencia} ===")

    if args.so_medir:
        csv_path = RAW / f"D.SDA.PDA.003.EMI.{aaaamm}.csv"
        zip_path = RAW / f"D.SDA.PDA.003.EMI.{aaaamm}.CSV.ZIP"
        if not csv_path.exists():
            print(f"  {csv_path} não existe — rode sem --so-medir")
            print("COMPETENCIA=ERRO")
            return 1
    else:
        zip_path, csv_path = baixar(args.competencia)
        registrar_hashes(zip_path, csv_path)

    _travar()
    print("  W-1 aplicado: arquivos 444, diretório 555")
    print()

    EVIDENCIA.mkdir(exist_ok=True)
    ok = medir(args.competencia, csv_path)

    print()
    if not ok:
        print("  algum medidor não fechou — a competência NÃO está medida")
        print("COMPETENCIA=ERRO")
        return 1

    print(f"  medida. Agora rode para ver a série ganhar um ponto:")
    print("    python3 scripts/medir_serie.py")
    print("    python3 scripts/medir_incremental.py")
    print()
    print("  ⚠ A âncora nova nasce SEM aprovação. Alguém do negócio confirma")
    print("    o número antes que ele valha como oráculo (Regra 2).")
    print("COMPETENCIA=MEDIDA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
