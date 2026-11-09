"""Converte os JSONs baixados por coletar_marc.py em duas tabelas.

  defesas.csv        uma linha por defesa (registro do repositório)
  participacoes.csv  uma linha por (defesa, pessoa, papel), com papéis do campo
                     MARC 700 (Orientador, Coorientador, Avaliador...)

O endpoint devolve uma string HTML com uma tag MARC por linha (<br/>), subcampos
marcados como "|a", "|d" etc. e acentos como entidades HTML.

Uso:
  python marc/parsear_marc.py marc/marc_raw --links marc/links --saida marc/tabelas
  python marc/parsear_marc.py marc/marc_raw --links marc/links --saida marc/tabelas_pub --desidentificar

--links acrescenta, cruzando pelo código do registro, a aba de origem
(ano_planilha) e o tipo da planilha (MESTRADO, DOUTORADO, MESTRADO PROFISSIONAL)
da primeira ocorrência; outras ocorrências do mesmo id vão para
outras_ocorrencias_planilha ("ano:tipo").

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
RE_DATA = re.compile(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})")


def linhas_marc(texto):
    """Lista de (tag, indicadores, [(subcampo, valor), ...]) ou (tag, conteudo) p/ controle."""
    texto = re.sub(r"</?strong>", "", texto)
    saida = []
    for bruta in texto.split("<br/>"):
        # alguns campos (ex.: 536 |d, 520) trazem quebra de linha no meio do valor
        linha = re.sub(r"\s*\n\s*", " ", html.unescape(bruta)).strip()
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


def nome(subs):
    """|a sem a vírgula/ponto final que aparece em parte dos registros ("Miyazawa, Flávio Keidi,",
    "Kijak, Ewa."). O ponto de uma inicial ("Silva, J.") é mantido."""
    n = re.sub(r"\s+\.$", "", primeiro(subs, "a").rstrip(", "))
    return re.sub(r"(\w{2,})\.$", r"\1", n)


def papel(subs):
    """|e sem o ponto final ("Orientador." -> "Orientador"); "?" quando não há |e."""
    return primeiro(subs, "e").rstrip(". ") or "?"


def data_943(textos):
    """(dd-mm-aaaa da primeira data legível, texto original da primeira 943)."""
    for t in textos:
        m = RE_DATA.search(t)
        if m:
            d, mes, a = m.groups()
            return f"{int(d):02d}-{int(mes):02d}-{a}", textos[0]
    return "", (textos[0] if textos else "")


def ano_nasc(subs):
    m = re.match(r"(\d{4})", primeiro(subs, "d"))
    return int(m.group(1)) if m else None


def parsear(codigo, texto):
    marc = linhas_marc(texto)
    d = {"codigo": codigo}
    parts = []
    banca_942, notas_500, agencias, datas, dados_pesq, outros_856 = [], [], [], [], [], []
    for tag, _, subs in marc:
        if tag == "100":
            orcid, lattes = ids_externos(subs)
            d.update(autor_nome=nome(subs), autor_ano_nasc=ano_nasc(subs),
                     autor_orcid=orcid, autor_lattes=lattes)
        elif tag == "245":
            d["titulo"] = primeiro(subs, "a")
        elif tag == "260":
            d["ano_publicacao"] = primeiro(subs, "c").strip(". ")
        elif tag == "500":
            notas_500.append(primeiro(subs, "a"))
        elif tag == "502":
            d["nota_tese"] = primeiro(subs, "a")
        elif tag == "536":  # pode se repetir (ex.: CAPES e CNPQ); o nº do processo (|d) é descartado
            ag = primeiro(subs, "a").replace("Agência de fomento:", "").strip()
            if ag:
                agencias.append(ag)
        elif tag == "700":
            orcid, lattes = ids_externos(subs)
            parts.append({"codigo": codigo, "ordem": len(parts) + 1,
                          "papel": papel(subs), "nome": nome(subs),
                          "ano_nasc": ano_nasc(subs), "orcid": orcid, "lattes": lattes})
        elif tag == "710":
            d["programa"] = " ".join(v for c, v in subs if c == "b").strip()
        elif tag == "852":
            d["unidade"] = primeiro(subs, "a")
        elif tag == "856":  # |y "Texto completo" (handle), "DOI" (da tese), "Dados de pesquisa" (DOIs)
            u, y = primeiro(subs, "u"), primeiro(subs, "y").rstrip(". ").lower()
            if not u:
                continue
            if "hdl.handle.net" in u:
                d.setdefault("handle", u)
            elif y == "doi" or "10.47749/" in u:
                d.setdefault("doi", u)
            elif y.startswith("dados de pesquisa"):
                if u not in dados_pesq:
                    dados_pesq.append(u)
            elif u not in outros_856:
                outros_856.append(u)
        elif tag == "940":
            d["area_concentracao"] = primeiro(subs, "a").split(":", 1)[-1].strip()
        elif tag == "941":
            d["titulacao"] = primeiro(subs, "a").split(":", 1)[-1].strip()
        elif tag == "942":
            banca_942.append(primeiro(subs, "a").split(":", 1)[-1].strip())
        elif tag == "943":  # "Data da Defesa: dd-mm-aaaa", com variações (sem ":", "/", ponto final)
            datas.append(re.sub(r"^Data da [Dd]efesa:?", "", primeiro(subs, "a")).strip())
        elif tag == "990":
            d["tipo_obra"] = primeiro(subs, "a")
    d["agencia_fomento"] = " | ".join(agencias)
    d["dados_pesquisa"] = " | ".join(dados_pesq)
    if outros_856:
        d["outros_856"] = " | ".join(outros_856)
    d["data_defesa"], d["data_defesa_txt"] = data_943(datas)
    d["notas_500"] = " | ".join(notas_500)
    d["banca_942"] = " | ".join(banca_942)
    d["n_700"] = len(parts)
    d["n_banca_942"] = len(banca_942)
    nota = d.get("nota_tese", "").lower()
    d["nivel"] = "DOUTORADO" if "doutorado" in nota else "MESTRADO PROFISSIONAL" if "profissional" in nota \
        else "MESTRADO" if "mestrado" in nota else ""
    return d, parts


def info_planilha(pasta_links):
    """codigo -> (ano_planilha, tipo, outras ocorrências) a partir dos links{ano}.csv."""
    df = pd.concat([pd.read_csv(a) for a in sorted(Path(pasta_links).glob("links*.csv"))])
    df = df.dropna(subset=["codigo"]).sort_values(["ano", "celula"])
    info = {}
    for cod, g in df.groupby("codigo", sort=False):
        ocorr = [f"{a}:{t if pd.notna(t) else ''}" for a, t in zip(g["ano"], g["tipo"])]
        info[int(cod)] = {"ano_planilha": int(g["ano"].iloc[0]), "tipo": g["tipo"].iloc[0],
                          "outras_ocorrencias_planilha": " | ".join(ocorr[1:])}
    return pd.DataFrame.from_dict(info, orient="index").rename_axis("codigo").reset_index()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pasta", help="pasta com <codigo>.json (saída do coletar_marc.py)")
    ap.add_argument("--saida", default="tabelas")
    ap.add_argument("--desidentificar", action="store_true")
    ap.add_argument("--links", help="pasta com links{ano}.csv (saída do gerar_links.py)")
    args = ap.parse_args()

    defesas, parts = [], []
    for arq in sorted(Path(args.pasta).glob("*.json")):
        dados = json.loads(arq.read_text())
        texto = dados if isinstance(dados, str) else json.dumps(dados, ensure_ascii=False)
        d, p = parsear(int(arq.stem), texto)
        defesas.append(d)
        parts.extend(p)

    df_d, df_p = pd.DataFrame(defesas), pd.DataFrame(parts)
    for df, col in ((df_d, "autor_ano_nasc"), (df_p, "ano_nasc")):
        if col in df:
            df[col] = df[col].astype("Int64")
    if "data_defesa" in df_d:
        df_d["data_defesa"] = pd.to_datetime(df_d["data_defesa"], format="%d-%m-%Y", errors="coerce")
    if args.links:  # a base é o que a planilha liga: registros baixados sem link (ou anulados) saem
        info = info_planilha(args.links)
        fora = sorted(set(df_d["codigo"]) - set(info["codigo"]))
        if fora:
            print(f"[aviso] {len(fora)} registros em {args.pasta} sem link na planilha "
                  f"(ou anulados em ids_manuais.csv), ignorados: {fora}")
        df_d = info.merge(df_d, on="codigo", how="right")  # "right" mantém a ordem dos arquivos
        df_d = df_d[df_d["codigo"].isin(info["codigo"])].reset_index(drop=True)
        df_p = df_p[df_p["codigo"].isin(df_d["codigo"])].reset_index(drop=True)
        df_d["ano_planilha"] = df_d["ano_planilha"].astype("Int64")
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
