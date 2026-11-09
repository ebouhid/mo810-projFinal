"""Valida a base nova (MARC completo) contra a base antiga e gera relatorio_validacao.md.

Lê só as tabelas desidentificadas (tabelas_pub), para que o relatório não traga
dados de estudantes. Os registros "antigos substituídos" (ids que só existem na
base antiga) são lidos do JSON bruto e parseados em memória, mas o relatório só
mostra código, nota 502, unidade 852 e tipo de obra (990).

Uso:
  python marc/validar.py            # usa os caminhos padrão abaixo
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd

from parsear_marc import parsear

RE_ID = re.compile(r"/detalhe/(\d+)", re.I)
RE_ORCID = re.compile(r"(\d{4}-\d{4}-\d{4}-\d{3}[\dX])")
IC = "Instituto de Computação"
FAIXAS = [(2006, 2012, "2006–12"), (2013, 2018, "2013–18"), (2019, 2024, "2019–24")]
K_SEM = '"sem orcid" antigos'


# --------------------------------------------------------------------- utilidades
def norm_orcid(v):
    m = RE_ORCID.search(str(v)) if pd.notna(v) else None
    return m.group(1) if m else ""


def codigo_url(u):
    m = RE_ID.search(str(u))
    return int(m.group(1)) if m else None


def eh_ic(nota, unidade):
    """Nota 502 cita o IC e a unidade 852 é o IC (espaços colapsados: há '502' com espaço duplo)."""
    esp = lambda x: re.sub(r"\s+", " ", str(x) if pd.notna(x) else "").strip(" .")  # noqa: E731
    return IC in esp(nota) and esp(unidade) == IC


def faixa(ano):
    for a, b, nome in FAIXAS:
        if a <= ano <= b:
            return nome
    return "outra"


def nome_942(txt):
    """'Banca: Pedrini, Hélio, 1963- [Orientador]' -> 'Pedrini, Hélio'."""
    txt = re.sub(r"\[[^\]]*\]", "", str(txt))
    txt = re.sub(r",\s*\d{4}-(\d{4})?\s*$", "", txt.strip())
    return txt.strip(" ,.")


def md_tabela(df, max_linhas=None):
    if df is None or len(df) == 0:
        return "_(nenhum)_\n"
    corte = df if max_linhas is None else df.head(max_linhas)
    cols = [str(c) for c in corte.columns]
    linhas = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in corte.iterrows():
        cel = ["" if pd.isna(v) else str(v).replace("|", "\\|").replace("\n", " ") for v in r]
        linhas.append("| " + " | ".join(cel) + " |")
    extra = f"\n_(+{len(df) - len(corte)} linhas omitidas)_\n" if len(corte) < len(df) else ""
    return "\n".join(linhas) + "\n" + extra


def ler_log(pasta):
    arq = Path(pasta) / "_log.csv"
    if not arq.exists():
        return pd.DataFrame(columns=["codigo", "csv_origem", "status"])
    log = pd.read_csv(arq, dtype={"status": str})
    return log.drop_duplicates("codigo", keep="last")  # vale a última tentativa


# --------------------------------------------------------------------- seções
def secao_coleta(links, raw, defesas):
    out = ["## 1. Coleta\n"]
    log = ler_log(raw)
    esperados = set(links["codigo"].dropna().astype(int))
    ok = set(defesas["codigo"])
    out.append(f"- Links na planilha (2006–2025): **{len(links)}**; ids únicos: **{len(esperados)}**.")
    out.append(f"- Registros baixados com status 200 e parseados: **{len(ok & esperados)}**.")
    falhas = log[(log["status"] != "200") & log["codigo"].isin(esperados - ok)]
    nunca = esperados - ok - set(falhas["codigo"])
    out.append(f"- Falhas: **{len(falhas)}**; ids nunca pedidos: **{len(nunca)}**.")
    sem_id = links[links["codigo"].isna()]
    out.append(f"- Links sem id de registro (não coletáveis): **{len(sem_id)}**.\n")
    if len(falhas):
        f = falhas.copy()
        f["motivo"] = [(Path(raw) / "_falhas" / f"{c}.txt").read_text()[:200].replace("\n", " ")
                       if (Path(raw) / "_falhas" / f"{c}.txt").exists() else "" for c in f["codigo"]]
        out.append("Falhas:\n\n" + md_tabela(f[["codigo", "csv_origem", "status", "motivo"]]))
    if len(sem_id):
        out.append("Links sem id:\n\n" + md_tabela(sem_id[["ano", "celula", "url"]]))
    if nunca:
        lista = sorted(nunca)
        out.append(f"Ids nunca pedidos ({len(lista)}): {lista[:30]}{' ...' if len(lista) > 30 else ''}\n")
    return "\n".join(out) + "\n"


def secao_links(links, pasta_antiga):
    out = ["## 2. Links: planilha nova vs. csvs/links{ano}.csv antigos\n"]
    linhas = []
    for ano, g in links.groupby("ano"):
        arq = Path(pasta_antiga) / f"links{ano}.csv"
        if not arq.exists():
            linhas.append({"ano": ano, "antigo": "-", "novo": len(g), "saíram": "", "entraram": ""})
            continue
        ant = pd.read_csv(arq)["url"]
        k_ant = [codigo_url(u) or u for u in ant]
        k_nov = [int(c) if pd.notna(c) else u for c, u in zip(g["codigo"], g["url"])]
        linhas.append({"ano": ano, "antigo": len(ant), "novo": len(g),
                       "saíram": ", ".join(map(str, sorted(set(map(str, k_ant)) - set(map(str, k_nov))))),
                       "entraram": ", ".join(map(str, sorted(set(map(str, k_nov)) - set(map(str, k_ant)))))})
    out.append(md_tabela(pd.DataFrame(linhas)))
    return "\n".join(out) + "\n"


def base_antiga(caminho):
    old = pd.read_csv(caminho, low_memory=False)
    old["codigo"] = old["url"].map(codigo_url)
    av_cols = sorted([c for c in old.columns if re.fullmatch(r"avaliador\d+", c)],
                     key=lambda c: int(c[9:]))
    return old, av_cols


def secao_orcids(old, av_cols, defesas, parts):
    out = ["## 3. ORCIDs: base antiga vs. nova (mesmo id)\n"]
    comuns = old[old["codigo"].isin(defesas["codigo"])]
    fora = old[~old["codigo"].isin(defesas["codigo"])]
    out.append(f"- Defesas da base antiga (`final_defesas_2006a2024.csv`): {len(old)}; "
               f"com o mesmo id na nova: **{len(comuns)}**; ausentes na nova: {len(fora)}.")
    if len(fora):
        out.append("  Ausentes: " + ", ".join(f"{c} ({a})" for c, a in zip(fora["codigo"], fora["ano"])))
    pp = parts.groupby("codigo")
    div, recuperados_or = [], 0
    for _, r in comuns.iterrows():
        p = pp.get_group(r["codigo"]) if r["codigo"] in pp.groups else parts.iloc[0:0]
        papel_de = {o: pa for o, pa in zip(p["orcid_n"], p["papel"]) if o}
        nome_de = {o: n for o, n in zip(p["orcid_n"], p["nome"]) if o}
        novos_or = set(p.loc[p["papel"] == "Orientador", "orcid_n"]) - {""}
        o_old = norm_orcid(r["orientador"])
        if o_old and o_old not in novos_or:
            if o_old in papel_de:
                obs = f"ORCID antigo está na nova com papel {papel_de[o_old]!r} ({nome_de[o_old]})"
            else:
                ori = p[p["papel"] == "Orientador"]
                obs = ("ORCID antigo ausente; orientador na nova: "
                       + ("; ".join(f"{n} (sem ORCID)" for n in ori["nome"]) or "nenhum"))
            div.append({"codigo": r["codigo"], "ano": r["ano"], "campo": "orientador",
                        "antigo": o_old, "novo": ", ".join(sorted(novos_or)) or "(sem ORCID)", "obs": obs})
        elif not o_old and novos_or:
            recuperados_or += 1
        old_av = [norm_orcid(r[c]) for c in av_cols if pd.notna(r[c]) and str(r[c]).strip()]
        avs_novos = p[p["papel"] == "Avaliador"].sort_values("ordem")
        set_old = set(old_av) - {""}
        n_sem = sum(1 for o in old_av if not o)
        set_new = set(p.loc[p["papel"] == "Avaliador", "orcid_n"]) - {""}
        perdidos, extras = set_old - set_new, set_new - set_old
        if perdidos or len(extras) > n_sem:
            obs = []
            for o in sorted(perdidos):
                if o in papel_de:
                    obs.append(f"{o} está na nova com papel {papel_de[o]!r}")
                elif len(old_av) == len(avs_novos):  # mesma posição (ordem do crawler2)
                    novo = avs_novos.iloc[old_av.index(o)]
                    obs.append(f"{o} ausente; na mesma posição a nova tem {novo['nome']} "
                               f"({novo['orcid_n'] or 'sem ORCID'})")
                else:
                    obs.append(f"{o} ausente na nova")
            if len(extras) > n_sem:
                obs.append(f"{len(extras)} ORCIDs novos para {n_sem} 'sem orcid' antigos: "
                           + ", ".join(f"{o} ({nome_de.get(o, '')})" for o in sorted(extras)))
            div.append({"codigo": r["codigo"], "ano": r["ano"], "campo": "avaliadores",
                        "antigo": ", ".join(sorted(set_old)), "novo": ", ".join(sorted(set_new)),
                        "obs": "; ".join(obs)})
    div = pd.DataFrame(div)
    n_or = (div["campo"] == "orientador").sum() if len(div) else 0
    n_av = (div["campo"] == "avaliadores").sum() if len(div) else 0
    out.append(f"- Divergências de orientador: **{n_or}**; de conjunto de avaliadores: **{n_av}**.")
    out.append(f"- Orientador antes \"sem orcid\" e agora com ORCID: {recuperados_or} (não conta como divergência).")
    out.append("- Critério: ORCIDs normalizados (`0000-0000-0000-000X`). Avaliadores divergem se um ORCID antigo "
               "não aparece entre os `Avaliador` novos, ou se há mais ORCIDs novos do que \"sem orcid\" antigos.")
    out.append("- Nos casos \"ausente\", a pessoa continua no registro, na mesma posição, mas **sem ORCID**: o "
               "registro do repositório foi editado depois da coleta antiga. Nesses casos, o ORCID da base antiga "
               "é a única ligação por identificador para essas participações.\n")
    out.append(md_tabela(div))
    return "\n".join(out) + "\n"


def secao_sem_orcid(old, av_cols, defesas, parts):
    """Alinha por posição como o crawler2: orientador = último 700 Orientador;
    avaliadorK = K-ésimo 700 Avaliador. Só alinha se o nº de avaliadores bate."""
    out = ["## 4. Participações \"sem orcid\" da base antiga que agora têm nome\n"]
    pp = parts.groupby("codigo")
    linhas, conferencia = [], Counter()
    for _, r in old.iterrows():
        cod = r["codigo"]
        presente = cod in pp.groups
        p = pp.get_group(cod) if presente else parts.iloc[0:0]
        ori = p[p["papel"] == "Orientador"].sort_values("ordem")
        avs = p[p["papel"] == "Avaliador"].sort_values("ordem")
        slots = [("orientador", r["orientador"], ori.iloc[-1] if len(ori) else None)]
        vals_av = [r[c] for c in av_cols if pd.notna(r[c]) and str(r[c]).strip()]
        alinhavel = len(vals_av) == len(avs)
        for k, v in enumerate(vals_av):
            slots.append(("avaliador", v, avs.iloc[k] if alinhavel else None))
        for tipo_slot, v, novo in slots:
            if pd.isna(v):
                continue
            if str(v).strip() != "sem orcid":
                if novo is not None:  # confere o alinhamento com quem já tinha ORCID
                    conferencia["ok" if norm_orcid(v) == novo["orcid_n"] else "difere"] += 1
                continue
            situacao = ("ausente na nova" if not presente else
                        "não alinhável" if novo is None else
                        "com nome" if str(novo["nome"]).strip() else "sem nome")
            linhas.append({"faixa": faixa(int(r["ano"])), "situacao": situacao,
                           "orcid": bool(novo is not None and novo["orcid_n"]),
                           "lattes": bool(novo is not None and str(novo["lattes"]).strip() not in ("", "nan"))})
    df = pd.DataFrame(linhas)
    tab = []
    for _, _, nome in FAIXAS:
        g = df[df["faixa"] == nome]
        nomeados = g[g["situacao"] == "com nome"]
        tab.append({"faixa": nome, K_SEM: len(g), "agora com nome": len(nomeados),
                    "% com nome": f"{100 * len(nomeados) / len(g):.1f}" if len(g) else "-",
                    "dos quais com ORCID": int(nomeados["orcid"].sum()),
                    "com Lattes": int(nomeados["lattes"].sum()),
                    "não alinháveis": (g["situacao"] == "não alinhável").sum(),
                    "ausentes na nova": (g["situacao"] == "ausente na nova").sum()})
    tab = pd.DataFrame(tab)
    tot = {c: (tab[c].sum() if c not in ("faixa", "% com nome") else "") for c in tab.columns}
    tot["faixa"] = "**total**"
    tot["% com nome"] = f"{100 * tot['agora com nome'] / tot[K_SEM]:.1f}" if tot[K_SEM] else "-"
    tab = pd.concat([tab, pd.DataFrame([tot])])
    out.append(md_tabela(tab))
    out.append(f"\nConferência do alinhamento por posição (participações que já tinham ORCID na base antiga): "
               f"{conferencia['ok']} com o mesmo ORCID na posição correspondente, {conferencia['difere']} diferentes.")
    out.append("\"Não alinhável\": o nº de avaliadores difere entre as bases, então não dá para saber "
               "qual pessoa nova corresponde ao \"sem orcid\". \"Agora com ORCID\": o registro foi "
               "atualizado no repositório depois da coleta antiga.\n")
    return "\n".join(out) + "\n"


def secao_700_942(defesas, parts):
    out = ["## 5. Defesas com nº de linhas 700 diferente do nº de nomes no 942\n"]
    cont = parts.groupby("codigo")["papel"].value_counts().unstack(fill_value=0)
    d = defesas.set_index("codigo")[["ano_planilha", "n_700", "n_banca_942", "banca_942"]].join(cont)
    for c in ("Coorientador", "?"):
        if c not in d:
            d[c] = 0
    d = d[d["n_700"] != d["n_banca_942"]].copy()
    nomes700 = parts.groupby("codigo")["nome"].apply(lambda s: {str(x).strip() for x in s})
    d["no_942_fora_do_700"] = [
        "; ".join(n for n in (nome_942(x) for x in str(b).split(" | ") if str(b) != "nan")
                  if n and n not in nomes700.get(c, set()))
        for c, b in zip(d.index, d["banca_942"])]

    if "Orientador" not in d:
        d["Orientador"] = 0
    d["ori_extra"] = (d["Orientador"] - 1).clip(lower=0)
    comuns = [c for c in ("Avaliador", "Orientador", "Coorientador", "?") if c in d]
    d["incomum"] = d["n_700"] - d[comuns].sum(axis=1)

    def explica(r):
        fora = r["n_700"] - r["n_banca_942"]
        if fora == r["Coorientador"]:
            return "coorientador(es) não entram no 942"
        if fora == r["Coorientador"] + r["ori_extra"]:
            return "2º orientador (e coorientadores) não entram no 942"
        if fora == r["Coorientador"] + r["ori_extra"] + r["?"]:
            return "coorientador/2º orientador + 700 sem papel (|e) não entram no 942"
        if fora == r["Coorientador"] + r["ori_extra"] + r["?"] + r["incomum"]:
            return "700 com papel incomum (Presidente/Organizador) não entra no 942"
        return "não explicado"

    d["explicacao"] = d.apply(explica, axis=1)
    out.append(f"- Total: **{len(d)}** de {len(defesas)} defesas.")
    for k, v in d["explicacao"].value_counts().items():
        out.append(f"  - {k}: {v}")
    out.append("\nNos registros conferidos, o campo 942 (\"Banca:\") lista o (primeiro) orientador e os "
               "avaliadores, mas **nunca o coorientador nem o segundo orientador** (dupla orientação/cotutela). "
               "Diferenças explicadas por isso não indicam erro.\n")
    tab = d.reset_index()[["codigo", "ano_planilha", "n_700", "n_banca_942", "Coorientador", "?",
                           "no_942_fora_do_700", "explicacao"]].rename(columns={"?": "sem_papel"})
    nexp = tab[tab["explicacao"] == "não explicado"]
    out.append("### Não explicadas\n\n" + md_tabela(nexp))
    exp = tab[tab["explicacao"] != "não explicado"]
    out.append("### Explicadas por coorientador ou 2º orientador (só os ids)\n\n"
               + (", ".join(map(str, exp["codigo"])) if len(exp) else "_(nenhuma)_") + "\n")
    return "\n".join(out) + "\n"


def secao_fora_ic(defesas, antigos):
    out = ["## 6. Registros cuja nota 502 ou unidade 852 não é do Instituto de Computação\n"]
    cols = ["codigo", "ano_planilha", "nota_tese", "unidade", "programa", "tipo_obra"]
    d = defesas.copy()
    mask = ~pd.Series([eh_ic(n, u) for n, u in zip(d["nota_tese"], d["unidade"])], index=d.index)
    f = d.loc[mask, cols].copy()
    comp = lambda x: bool(re.search(r"Computa", str(x)))  # noqa: E731

    def classe(r):
        if not comp(r["nota_tese"]) and not comp(r["unidade"]) and not comp(r["programa"]):
            return "**não é do IC** (502, 852 e 710 de outra unidade)"
        if comp(r["nota_tese"]) and str(r["unidade"]).strip() != IC:
            return "852 de outra unidade; 502 e 710 do IC (catalogação)"
        return "502 com grafia variante/sem a unidade; 852 do IC (catalogação)"

    f.insert(2, "classificacao", f.apply(classe, axis=1))
    f = f.sort_values(["classificacao", "codigo"])
    out.append(f"- Na base nova: **{len(f)}**. Por classificação:")
    for k, v in f["classificacao"].value_counts().items():
        out.append(f"  - {k}: {v}")
    out.append("")
    out.append(md_tabela(f))
    if len(antigos):
        a = antigos.copy()
        a["fora_do_IC"] = [not eh_ic(n, u) for n, u in zip(a["nota_tese"], a["unidade"])]
        out.append("\nIds que só existem na base antiga (a planilha nova trocou os links), coletados à parte "
                   "em `marc_raw/antigos/` só para esta checagem:\n")
        out.append(md_tabela(a[["codigo", "ano_antigo", "nota_tese", "unidade", "tipo_obra", "fora_do_IC"]]))
    return "\n".join(out) + "\n"


def secao_duplicados(links, pasta_antiga, defesas, old):
    out = ["## 7. Ids duplicados e defesas de 2010 sem tipo\n"]
    lk = links.dropna(subset=["codigo"]).astype({"codigo": int})
    dup = lk[lk["codigo"].duplicated(keep=False)].sort_values(["codigo", "ano"])
    out.append("Ids duplicados na planilha nova:\n\n" + md_tabela(dup[["codigo", "ano", "celula", "tipo"]]))
    ant = []
    for arq in sorted(Path(pasta_antiga).glob("links*.csv")):
        for u in pd.read_csv(arq)["url"]:
            ant.append({"codigo": codigo_url(u), "arquivo": arq.name})
    ant = pd.DataFrame(ant).dropna().astype({"codigo": int})
    dup_ant = ant[ant["codigo"].duplicated(keep=False)].sort_values("codigo")
    dup_ant = dup_ant.groupby("codigo")["arquivo"].apply(lambda s: ", ".join(s)).reset_index()
    out.append("\nIds duplicados nos `csvs/links*.csv` antigos:\n\n" + md_tabela(dup_ant))
    s10 = links[(links["ano"] == 2010) & links["tipo"].isna()]
    niv = defesas.set_index("codigo")["nivel"]
    s10 = s10.assign(nivel_502=[niv.get(int(c), "(não coletado)") if pd.notna(c) else "(sem id)"
                                for c in s10["codigo"]])
    out.append(f"\nDefesas de 2010 sem `tipo` na planilha: **{len(s10)}** (a aba 2010 não tem o cabeçalho "
               f"MESTRADO). Na base antiga eram {old[(old['ano'] == 2010) & old['tipo'].isna()].shape[0]}. "
               f"O `nivel` tirado da nota 502 cobre o buraco: "
               + ", ".join(f"{k}: {v}" for k, v in s10["nivel_502"].value_counts().items()) + ".\n")
    out.append("Ids: " + ", ".join(str(int(c)) if pd.notna(c) else "(sem id)" for c in s10["codigo"]) + "\n")
    return "\n".join(out) + "\n"


def secao_536(defesas):
    out = ["## 8. Agência de fomento (campo 536)\n"]
    ag = defesas["agencia_fomento"].fillna("").str.strip()
    out.append(f"- Defesas com alguma agência: **{(ag != '').sum()}** de {len(defesas)} "
               f"({100 * (ag != '').mean():.1f}%). O campo existe em quase todos os registros, "
               "mas muitas vezes vem vazio (\"Agência de fomento:\").\n")
    vals = Counter(v.strip() for x in ag if x for v in x.split(" | "))
    out.append("Valores (uma defesa pode ter mais de um):\n\n"
               + md_tabela(pd.DataFrame(vals.most_common(), columns=["agencia", "defesas"])))
    por_ano = defesas.assign(tem=(ag != "")).groupby("ano_planilha")["tem"].agg(["sum", "count"])
    por_ano["%"] = (100 * por_ano["sum"] / por_ano["count"]).round(0).astype(int)
    out.append("\nPreenchimento por ano da planilha:\n\n"
               + md_tabela(por_ano.reset_index().rename(columns={"sum": "com agência", "count": "defesas"})))
    return "\n".join(out) + "\n"


def secao_papeis(defesas, parts):
    out = ["## 9. Papéis e coorientadores\n"]
    out.append(md_tabela(parts["papel"].value_counts().rename_axis("papel").reset_index(name="participações")))
    co = parts[parts["papel"] == "Coorientador"]
    out.append(f"\n- Coorientadores: **{len(co)}** participações em **{co['codigo'].nunique()}** defesas "
               f"({co['orcid_n'].ne('').sum()} com ORCID). A base antiga não tinha nenhum.")
    sem = parts[parts["papel"] == "?"]
    out.append(f"- Linhas 700 sem papel (`|e`): **{len(sem)}**. O papel não foi inferido.")
    autor = parts[parts["papel"].str.lower().str.startswith("autor")]
    out.append(f"- Linhas 700 com papel \"Autor\" (seriam o estudante): **{len(autor)}**.")
    incomuns = parts[~parts["papel"].isin(["Avaliador", "Orientador", "Coorientador"])]
    out.append("\nPapéis fora de Avaliador/Orientador/Coorientador (mantidos como estão no MARC; "
               "`?` = sem `|e`):\n")
    out.append(md_tabela(incomuns.merge(defesas[["codigo", "ano_planilha"]], on="codigo")
                         [["codigo", "ano_planilha", "ordem", "papel", "nome", "orcid_n"]]))
    n_ori = parts[parts["papel"] == "Orientador"].groupby("codigo").size()
    out.append(f"- Defesas com mais de um 700 `Orientador` (dupla orientação/cotutela): **{(n_ori > 1).sum()}**.")
    sem_nome = parts[parts["nome"].isna() | (parts["nome"].astype(str).str.strip() == "")]
    out.append(f"- Linhas 700 sem nome (`|a`): **{len(sem_nome)}**"
               + (": " + ", ".join(f"{c} ({pa})" for c, pa in zip(sem_nome["codigo"], sem_nome["papel"]))
                  if len(sem_nome) else "") + ".")
    sem_ori = defesas[~defesas["codigo"].isin(parts.loc[parts["papel"] == "Orientador", "codigo"])]
    out.append(f"\n- Defesas sem nenhum 700 `Orientador`: **{len(sem_ori)}**"
               + (": " + ", ".join(map(str, sem_ori["codigo"])) if len(sem_ori) else "") + "\n")
    return "\n".join(out) + "\n"


def secao_extras(defesas):
    out = ["## 10. Outras checagens\n"]
    tab = pd.crosstab(defesas["ano_planilha"], defesas["nivel"].replace("", "(vazio)").fillna("(vazio)"),
                      margins=True, margins_name="total")
    out.append("Defesas coletadas por ano da planilha e nível (nota 502):\n\n" + md_tabela(tab.reset_index()))
    t = defesas["tipo"].fillna("(sem tipo)")
    n = defesas["nivel"].fillna("").replace("", "(vazio)")
    dif = defesas[(t != n) & (t != "(sem tipo)")]
    out.append(f"\n`tipo` da planilha diferente do `nivel` da nota 502 (fora os sem tipo): **{len(dif)}**\n")
    out.append(md_tabela(dif[["codigo", "ano_planilha", "tipo", "nivel", "nota_tese"]]))
    dd = pd.to_datetime(defesas["data_defesa"], errors="coerce")
    out.append(f"\n- Data da defesa (943) ausente ou não interpretável: **{dd.isna().sum()}**\n")
    if dd.isna().sum():
        out.append(md_tabela(defesas.loc[dd.isna(), ["codigo", "ano_planilha", "data_defesa_txt"]]
                             .fillna({"data_defesa_txt": "(943 ausente ou vazio)"})))
    difano = defesas[dd.notna() & (dd.dt.year != defesas["ano_planilha"])]
    out.append(f"- Ano da data 943 diferente da aba da planilha: **{len(difano)}**\n")
    if len(difano):
        out.append(md_tabela(difano.assign(data=dd[difano.index].dt.date)[["codigo", "ano_planilha", "data"]]))
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pub", default="marc/tabelas_pub")
    ap.add_argument("--antiga", default="final_defesas_2006a2024.csv")
    ap.add_argument("--links", default="marc/links")
    ap.add_argument("--links-antigos", default="csvs")
    ap.add_argument("--raw", default="marc/marc_raw")
    ap.add_argument("--saida", default="marc/relatorio_validacao.md")
    args = ap.parse_args()

    defesas = pd.read_csv(Path(args.pub) / "defesas.csv")
    parts = pd.read_csv(Path(args.pub) / "participacoes.csv", dtype={"orcid": str, "lattes": str})
    parts["orcid_n"] = parts["orcid"].map(norm_orcid)
    parts["lattes"] = parts["lattes"].fillna("")
    links = pd.concat([pd.read_csv(a) for a in sorted(Path(args.links).glob("links*.csv"))])
    old, av_cols = base_antiga(args.antiga)

    antigos = []
    subst = Path(args.links) / "antigos_substituidos.csv"
    ano_ant = dict(zip(*pd.read_csv(subst)[["codigo", "ano"]].values.T)) if subst.exists() else {}
    for arq in sorted((Path(args.raw) / "antigos").glob("*.json")):
        d, _ = parsear(int(arq.stem), json.loads(arq.read_text()))
        antigos.append({k: d.get(k) for k in ("codigo", "nota_tese", "unidade", "tipo_obra")}
                       | {"ano_antigo": ano_ant.get(int(arq.stem))})
    antigos = pd.DataFrame(antigos)

    partes = [
        "# Relatório de validação: coleta MARC vs. base antiga\n",
        f"Gerado por `marc/validar.py` a partir de `{args.pub}/` (desidentificada) e `{args.antiga}`. "
        f"Base nova: {len(defesas)} defesas, {len(parts)} participações (linhas 700).\n",
        secao_coleta(links, args.raw, defesas),
        secao_links(links, args.links_antigos),
        secao_orcids(old, av_cols, defesas, parts),
        secao_sem_orcid(old, av_cols, defesas, parts),
        secao_700_942(defesas, parts),
        secao_fora_ic(defesas, antigos),
        secao_duplicados(links, args.links_antigos, defesas, old),
        secao_536(defesas),
        secao_papeis(defesas, parts),
        secao_extras(defesas),
    ]
    Path(args.saida).write_text("\n".join(partes))
    print(f"relatório -> {args.saida}")


if __name__ == "__main__":
    main()
