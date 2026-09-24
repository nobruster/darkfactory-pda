"""Mede o dicionário de espécies do INSS contra a Silver publicada.

Evidência do ADR 0014. Só lê: /dados/_raw (os .xlsx) e a Silver no MinIO.

  1. códigos: dicionário × dado
  2. texto da fonte == 20 primeiros caracteres do nome oficial (sem espaços
     à direita), em três variantes da regra — o número tem de ser o mesmo
  3. colapsos da fonte desfeitos pelo nome oficial

Uso, de dentro do pda-spark:
  python3 scripts/medir_dicionario.py [competencia]

Token: MEDIDA=OK|NAO_MEDIDO. Zero códigos lidos de qualquer lado é
NAO_MEDIDO, não OK (Regra 9).
"""
import re
import sys
import unicodedata
import zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, "/app/src")

DICIONARIO = "/dados/_raw/dicionario-especies-beneficio.xlsx"
SILVER = "s3a://silver/pda/beneficios-emitidos"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def ler_dicionario(caminho):
    z = zipfile.ZipFile(caminho)
    textos = ["".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t"))
              for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS)]
    dic, descartadas = {}, 0
    for linha in list(ET.fromstring(z.read("xl/worksheets/sheet1.xml")).iter(f"{{{NS['m']}}}row"))[1:]:
        vals = []
        for c in linha.findall("m:c", NS):
            v = c.find("m:v", NS)
            t = "" if v is None else v.text
            vals.append(textos[int(t)] if c.get("t") == "s" and t else (t or ""))
        if len(vals) >= 2 and re.fullmatch(r"\d+(\.0)?", vals[0].strip()):
            dic[f"{int(float(vals[0])):02d}"] = vals[1]
        else:
            descartadas += 1
    return dic, descartadas


def main():
    competencia = sys.argv[1] if len(sys.argv) > 1 else "2026-01"
    try:
        dic, descartadas = ler_dicionario(DICIONARIO)
    except (OSError, KeyError, zipfile.BadZipFile) as e:
        print(f"MEDIDA=NAO_MEDIDO dicionario ilegivel: {e}"); return 1
    print(f"dicionario: {len(dic)} codigos, {descartadas} linha(s) descartada(s) (cabecalho ou vazia)")
    if not dic:
        print("MEDIDA=NAO_MEDIDO dicionario sem codigos"); return 1

    from pyspark.sql import functions as F
    from medalhao import bronze
    spark = bronze.criar_sessao("medir-dicionario")
    spark.sparkContext.setLogLevel("ERROR")
    pares = (spark.read.format("delta").load(SILVER).where(F.col("competencia") == competencia)
             .select("especie_codigo", "especie_descricao").distinct().collect())
    spark.stop()
    dado = {}
    for r in pares:
        dado.setdefault(r["especie_codigo"], set()).add(r["especie_descricao"])
    if not dado:
        print(f"MEDIDA=NAO_MEDIDO competencia {competencia} sem linhas na Silver"); return 1

    print(f"1. codigos: dicionario={len(dic)} dado={len(dado)} "
          f"so_no_dicionario={sorted(set(dic) - set(dado))} so_no_dado={sorted(set(dado) - set(dic))}")
    multi = sorted(c for c, d in dado.items() if len(d) > 1)
    print(f"   codigos com mais de uma descricao no dado: {multi}")

    nfc = lambda s: unicodedata.normalize("NFC", s)  # noqa: E731
    regras = {
        "rstrip, sem NFC (regra da tarefa)": lambda f, n: f.rstrip() == n[:20].rstrip(),
        "rstrip, com NFC": lambda f, n: nfc(f).rstrip() == nfc(n)[:20].rstrip(),
        "strip dos dois lados": lambda f, n: f.strip() == n.strip()[:20].strip(),
    }
    comuns = sorted(set(dic) & set(dado))
    contagens = []
    print("2. texto da fonte == prefixo de 20 do nome oficial:")
    for nome, regra in regras.items():
        n = sum(1 for c in comuns if regra(next(iter(dado[c])), dic[c]))
        contagens.append(n)
        print(f"   {nome:36s}: {n} de {len(comuns)}")
    print(f"   nomes com espaco nas pontas: {[c for c, n in dic.items() if n != n.strip()]}")
    print(f"   nomes fora de NFC: {[c for c, n in dic.items() if n != nfc(n)]}")

    por_texto = {}
    for c in comuns:
        por_texto.setdefault(next(iter(dado[c])), []).append(c)
    grupos = {t: cs for t, cs in por_texto.items() if len(cs) > 1}
    desfeitos = sum(1 for cs in grupos.values() if len({dic[c] for c in cs}) == len(cs))
    print(f"3. colapsos no dado: {len(grupos)}  desfeitos pelo nome oficial: {desfeitos} de {len(grupos)}")

    if len(set(contagens)) != 1:
        print("   !! as variantes da regra divergem — o criterio importa aqui")
    print("MEDIDA=OK")
    return 0


sys.exit(main())
