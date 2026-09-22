"""Confere W-1: os bytes de origem imutáveis e verificáveis.

O adversário (R13-C5) apontou que hash antes/depois não prova proteção —
um arquivo em 0666 passa no teste quando ninguém escreve durante ele. E
estava certo: o CSV estava 0644, enquanto W-1 exige chmod 444.

Confere as duas metades da promessa: modo do arquivo E sha256 contra o
CHECKSUMS.txt declarado.

Token: W1=OK|VIOLADO|ERRO
"""
import hashlib
import stat
import sys
from pathlib import Path

RAW = Path("_raw")
CHECKSUMS = RAW / "CHECKSUMS.txt"
MODO_EXIGIDO = 0o444


def main() -> int:
    if not RAW.is_dir():
        print(f"erro: {RAW} não encontrado", file=sys.stderr)
        print("W1=ERRO")
        return 1

    violados = 0
    arquivos = sorted(p for p in RAW.iterdir() if p.is_file())

    print("  modo dos bytes de origem:")
    for p in arquivos:
        modo = stat.S_IMODE(p.stat().st_mode)
        ok = modo == MODO_EXIGIDO
        if not ok:
            violados += 1
        print(f"    {'ok     ' if ok else 'VIOLADO'} {oct(modo)}  {p.name}")

    print()
    declarados: dict[str, str] = {}
    if CHECKSUMS.exists():
        for linha in CHECKSUMS.read_text(encoding="utf-8").splitlines():
            partes = linha.split()
            if len(partes) == 2:
                declarados[Path(partes[1]).name] = partes[0]

    if not declarados:
        print("  nenhum sha256 declarado em CHECKSUMS.txt")
    else:
        print("  sha256 contra o declarado:")
        for nome, esperado in declarados.items():
            alvo = RAW / nome
            if not alvo.exists():
                print(f"    AUSENTE {nome}")
                violados += 1
                continue
            h = hashlib.sha256()
            with alvo.open("rb") as f:
                for bloco in iter(lambda: f.read(1 << 20), b""):
                    h.update(bloco)
            real = h.hexdigest()
            ok = real == esperado
            if not ok:
                violados += 1
            print(f"    {'ok     ' if ok else 'DIVERGE'} {nome}")
            if not ok:
                print(f"            declarado {esperado}")
                print(f"            real      {real}")

    print()
    if violados:
        print(f"  {violados} violação(ões) de W-1")
        print("  W-1 exige chmod 444 E sha256 verificável — hash antes/depois")
        print("  não prova proteção; um arquivo 0666 passa nesse teste")
        print("W1=VIOLADO")
        return 1

    print(f"  {len(arquivos)} arquivo(s) em 444, checksums conferidos")
    print("W1=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
