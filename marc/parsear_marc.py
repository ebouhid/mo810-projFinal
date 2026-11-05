"""Converte os JSONs baixados por coletar_marc.py em duas tabelas.

  defesas.csv        uma linha por defesa (registro do repositório)
  participacoes.csv  uma linha por (defesa, pessoa, papel), com papéis do campo
                     MARC 700 (Orientador, Coorientador, Avaliador...)

O endpoint devolve uma string HTML com uma tag MARC por linha (<br/>), subcampos
marcados como "|a", "|d" etc. e acentos como entidades HTML.

Uso:
  python parsear_marc.py marc_raw --saida tabelas
  python parsear_marc.py marc_raw --saida tabelas_pub --desidentificar

--desidentificar remove nome, ano de nascimento, ORCID e Lattes do AUTOR (estudante)
e o título/resumo; docentes e avaliadores ficam (são a rede analisada).
"""
import argparse
import html
import json
import re
from pathlib import Path

import pandas as pd

RE_LINHA = re.compile(r"^(\d{3})\s?(.*)$")
RE_ORCID = re.compile(r"(\d{4}-\d{4}-\d{4}-\d{3}[\dX])")
RE_LATTES = re.compile(r"lattes\.cnpq\.br/(\d+)")


def linhas_marc(texto):
    """Lista de (tag, indicadores, [(subcampo, valor), ...]) ou (tag, conteudo) p/ controle."""
    texto = re.sub(r"</?strong>", "", texto)
    saida = []
    for bruta in texto.split("<br/>"):
        linha = html.unescape(bruta).strip()
        m = RE_LINHA.match(linha)
        if not m:
            continue
        tag, resto = m.groups()
        if "|" not in resto:  # campos de controle (000-008)
            saida.append((tag, "", [("", resto.strip())]))
            continue
        ind, _, corpo = resto.partition("|")
        subs = [(p[0], p[1:].strip()) for p in ("|" + corpo).split("|")[1:] if p]
        saida.append((tag, ind.strip(), subs))
    return saida


def primeiro(subs, cod):
    return next((v for c, v in subs if c == cod), "")


def ids_externos(subs):
    links = " ".join(v for c, v in subs if c == "0")
    orcid = RE_ORCID.search(links)
    lattes = RE_LATTES.search(links)
    return (orcid.group(1) if orcid else ""), (lattes.group(1) if lattes else "")


def ano_nasc(subs):
    m = re.match(r"(\d{4})", primeiro(subs, "d"))
    return int(m.group(1)) if m else None


def parsear(codigo, texto):
    marc = linhas_marc(texto)
    d = {"codigo": codigo}
    parts = []
    banca_942, notas_500 = [], []
    for tag, _, subs in marc:
        if tag == "100":
            orcid, lattes = ids_externos(subs)
            d.update(autor_nome=primeiro(subs, "a"), autor_ano_nasc=ano_nasc(subs),
                     autor_orcid=orcid, autor_lattes=lattes)
        elif tag == "245":
            d["titulo"] = primeiro(subs, "a")
        elif tag == "260":
            d["ano_publicacao"] = primeiro(subs, "c").strip(". ")
        elif tag == "500":
            notas_500.append(primeiro(subs, "a"))
        elif tag == "502":
            d["nota_tese"] = primeiro(subs, "a")
        elif tag == "536":
            d["agencia_fomento"] = primeiro(subs, "a").replace("Agência de fomento:", "").strip()
        elif tag == "700":
            orcid, lattes = ids_externos(subs)
            parts.append({"codigo": codigo, "ordem": len(parts) + 1,
                          "papel": primeiro(subs, "e") or "?", "nome": primeiro(subs, "a"),
                          "ano_nasc": ano_nasc(subs), "orcid": orcid, "lattes": lattes})
        elif tag == "710":
            d["programa"] = " ".join(v for c, v in subs if c == "b").strip()
        elif tag == "852":
            d["unidade"] = primeiro(subs, "a")
        elif tag == "856":
            d.setdefault("handle", primeiro(subs, "u"))
        elif tag == "940":
            d["area_concentracao"] = primeiro(subs, "a").split(":", 1)[-1].strip()
        elif tag == "941":
            d["titulacao"] = primeiro(subs, "a").split(":", 1)[-1].strip()
        elif tag == "942":
            banca_942.append(primeiro(subs, "a").split(":", 1)[-1].strip())
        elif tag == "943":
            d.setdefault("data_defesa", primeiro(subs, "a").split(":", 1)[-1].strip())
        elif tag == "990":
            d["tipo_obra"] = primeiro(subs, "a")
    d["notas_500"] = " | ".join(notas_500)
    d["banca_942"] = " | ".join(banca_942)
    d["n_700"] = len(parts)
    d["n_banca_942"] = len(banca_942)
    nota = d.get("nota_tese", "").lower()
    d["nivel"] = "DOUTORADO" if "doutorado" in nota else "MESTRADO PROFISSIONAL" if "profissional" in nota \
        else "MESTRADO" if "mestrado" in nota else ""
    return d, parts


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pasta", help="pasta com <codigo>.json (saída do coletar_marc.py)")
    ap.add_argument("--saida", default="tabelas")
    ap.add_argument("--desidentificar", action="store_true")
    args = ap.parse_args()

    defesas, parts = [], []
    for arq in sorted(Path(args.pasta).glob("*.json")):
        dados = json.loads(arq.read_text())
        texto = dados if isinstance(dados, str) else json.dumps(dados, ensure_ascii=False)
        d, p = parsear(int(arq.stem), texto)
        defesas.append(d)
        parts.extend(p)

    df_d, df_p = pd.DataFrame(defesas), pd.DataFrame(parts)
    if "data_defesa" in df_d:
        df_d["data_defesa"] = pd.to_datetime(df_d["data_defesa"], format="%d-%m-%Y", errors="coerce")
    if args.desidentificar:
        df_d = df_d.drop(columns=[c for c in ["autor_nome", "autor_ano_nasc", "autor_orcid",
                                              "autor_lattes", "titulo"] if c in df_d])
    out = Path(args.saida)
    out.mkdir(parents=True, exist_ok=True)
    df_d.to_csv(out / "defesas.csv", index=False)
    df_p.to_csv(out / "participacoes.csv", index=False)
    print(f"{len(df_d)} defesas, {len(df_p)} participações -> {out}/")
    if len(df_p):
        print(df_p["papel"].value_counts().to_string())
        sem = (df_d["n_700"] != df_d["n_banca_942"]).sum()
        print(f"defesas com nº de 700 diferente do nº na banca (942): {sem}")


if __name__ == "__main__":
    main()
