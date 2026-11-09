"""Leva o gênero anotado (csvs/genero2.csv) para participacoes.csv e lista quem falta anotar.

Só docentes/avaliadores (linhas MARC 700). NÃO infere gênero pelo nome: a
anotação é manual e feita pelo grupo.

Identificação de pessoas (pessoa_id):
  - participações com o mesmo ORCID ou o mesmo Lattes são a mesma pessoa
    (união transitiva: ORCID A + Lattes L em uma defesa, só Lattes L em outra);
  - participações sem ORCID e sem Lattes são agrupadas pelo nome normalizado
    (sem acento, minúsculas, sem pontuação) e NÃO são ligadas às pessoas acima.

Gênero (colunas genero, genero_fonte):
  - "orcid":  o ORCID da própria participação está no genero2.csv;
  - "lattes": a pessoa está ligada (por Lattes) a um ORCID do genero2.csv;
  - se uma pessoa tem ORCIDs com gêneros diferentes no genero2, fica sem gênero
    e é reportada como conflito;
  - ligação só pelo nome nunca atribui gênero: vira dica em a_anotar_genero.csv;
  - dica_base_antiga: ORCID que a base antiga (final_defesas_2006a2024.csv)
    tinha na mesma posição da banca, quando o registro atual não tem ORCID
    (o repositório removeu o ORCID de alguns registros). Também só dica.

Saídas:
  - acrescenta pessoa_id, genero, genero_fonte em <pasta>/participacoes.csv
    para cada pasta em --tabelas (pode rodar de novo sem duplicar colunas);
  - a_anotar_genero.csv: uma linha por pessoa sem gênero, com a coluna genero
    vazia para preencher.

Uso:
  python marc/genero.py --tabelas marc/tabelas marc/tabelas_pub
"""
import argparse
import re
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd

RE_ORCID = re.compile(r"(\d{4}-\d{4}-\d{4}-\d{3}[\dX])")
RE_ID = re.compile(r"/detalhe/(\d+)", re.I)
NOVAS = ["pessoa_id", "genero", "genero_fonte"]


def norm_orcid(v):
    m = RE_ORCID.search(str(v)) if pd.notna(v) else None
    return m.group(1) if m else ""


def norm_nome(nome):
    s = unicodedata.normalize("NFKD", str(nome))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def nome_direto(nome):
    """'Pedrini, Hélio' -> 'Hélio Pedrini' (para comparar com os nomes do genero2)."""
    sobrenome, _, prenome = str(nome).partition(",")
    return f"{prenome.strip()} {sobrenome.strip()}".strip()


def orcids_base_antiga(caminho, p):
    """{índice da participação sem ORCID: ORCID da base antiga na mesma posição}.

    Mesmo alinhamento do crawler2/validar.py: orientador = último 700 Orientador;
    avaliadorK = K-ésimo 700 Avaliador (só se o nº de avaliadores bate)."""
    old = pd.read_csv(caminho, low_memory=False)
    old["codigo"] = old["url"].map(lambda u: int(m.group(1)) if (m := RE_ID.search(str(u))) else None)
    av_cols = sorted([c for c in old.columns if re.fullmatch(r"avaliador\d+", c)], key=lambda c: int(c[9:]))
    grupos = p.groupby("codigo")
    res = {}
    for _, r in old.iterrows():
        if r["codigo"] not in grupos.groups:
            continue
        g = grupos.get_group(r["codigo"])
        ori = g[g["papel"] == "Orientador"].sort_values("ordem")
        avs = g[g["papel"] == "Avaliador"].sort_values("ordem")
        pares = [(r["orientador"], ori.index[-1])] if len(ori) else []
        vals = [r[c] for c in av_cols if pd.notna(r[c]) and str(r[c]).strip()]
        if len(vals) == len(avs):
            pares += list(zip(vals, avs.index))
        for v, idx in pares:
            o = norm_orcid(v)
            if o and not p.at[idx, "orcid_n"]:
                res[idx] = o
    return res


class UniaoBusca:
    def __init__(self, n):
        self.pai = list(range(n))

    def raiz(self, i):
        while self.pai[i] != i:
            self.pai[i] = self.pai[self.pai[i]]
            i = self.pai[i]
        return i

    def unir(self, a, b):
        self.pai[self.raiz(a)] = self.raiz(b)


def identificar(p):
    """Devolve a Series pessoa_id para cada participação."""
    uf = UniaoBusca(len(p))
    for col in ("orcid_n", "lattes"):
        primeiro = {}
        for i, v in enumerate(p[col]):
            if v:
                if v in primeiro:
                    uf.unir(i, primeiro[v])
                else:
                    primeiro[v] = i
    grupos = {}
    for i in range(len(p)):
        grupos.setdefault(uf.raiz(i), []).append(i)
    pid = [""] * len(p)
    for membros in grupos.values():
        orcids = sorted({p["orcid_n"].iat[i] for i in membros} - {""})
        lattes = sorted({p["lattes"].iat[i] for i in membros} - {""})
        if orcids:
            chave = f"orcid:{orcids[0]}"
        elif lattes:
            chave = f"lattes:{lattes[0]}"
        else:
            chave = None  # sem ORCID e sem Lattes: chave pelo nome, individualmente
        for i in membros:
            pid[i] = chave or f"nome:{p['nome_norm'].iat[i]}"
    return pd.Series(pid, index=p.index)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tabelas", nargs="+", default=["marc/tabelas", "marc/tabelas_pub"],
                    help="pastas com participacoes.csv e defesas.csv; a primeira é a base")
    ap.add_argument("--genero", default="csvs/genero2.csv")
    ap.add_argument("--anotar", default="marc/a_anotar_genero.csv")
    ap.add_argument("--base-antiga", default="final_defesas_2006a2024.csv",
                    help="base antiga, para a dica de ORCID perdido (vazio para não usar)")
    args = ap.parse_args()

    base = Path(args.tabelas[0])
    p = pd.read_csv(base / "participacoes.csv", dtype={"orcid": str, "lattes": str})
    p = p.drop(columns=[c for c in NOVAS if c in p])
    anos = pd.read_csv(base / "defesas.csv").set_index("codigo")["ano_planilha"]
    p["ano"] = p["codigo"].map(anos)
    p["orcid_n"] = p["orcid"].map(norm_orcid)
    p["lattes"] = p["lattes"].fillna("").astype(str).str.replace(r"\.0$", "", regex=True)
    p["nome_norm"] = p["nome"].map(norm_nome)
    p["pessoa_id"] = identificar(p)

    g2 = pd.read_csv(args.genero)
    g2["orcid_n"] = g2["orcid"].map(norm_orcid)
    g2 = g2[g2["genero"].notna() & (g2["orcid_n"] != "")]
    genero_de = dict(zip(g2["orcid_n"], g2["genero"]))

    # gênero por pessoa (só pessoas com ORCID/Lattes; nome nunca atribui gênero)
    conflitos, genero_pessoa = {}, {}
    for pid, g in p.groupby("pessoa_id"):
        if pid.startswith("nome:"):
            continue
        gs = {genero_de[o] for o in set(g["orcid_n"]) if o in genero_de}
        if len(gs) == 1:
            genero_pessoa[pid] = gs.pop()
        elif len(gs) > 1:
            conflitos[pid] = sorted(gs)

    def atribui(r):
        if r["orcid_n"] in genero_de and r["pessoa_id"] not in conflitos:
            return genero_de[r["orcid_n"]], "orcid"
        if r["pessoa_id"] in genero_pessoa:
            return genero_pessoa[r["pessoa_id"]], "lattes"
        return "", ""

    p[["genero", "genero_fonte"]] = p.apply(atribui, axis=1, result_type="expand")

    # dicas: mesmo nome normalizado de alguém que já tem gênero (nos 700 ou no genero2)
    com_genero = p[p["genero"] != ""]
    dica_por_nome = {}
    for nn, o, nome in zip(com_genero["nome_norm"], com_genero["pessoa_id"], com_genero["nome"]):
        dica_por_nome.setdefault(nn, set()).add(f"{o.split(':', 1)[1]} ({nome})")
    for o, nome in zip(g2["orcid_n"], g2["nome"]):
        dica_por_nome.setdefault(norm_nome(nome), set()).add(f"{o} ({nome})")

    antigos = orcids_base_antiga(args.base_antiga, p) if args.base_antiga else {}
    nome_g2 = dict(zip(g2["orcid_n"], g2["nome"]))

    linhas = []
    for pid, g in p[p["genero"] == ""].groupby("pessoa_id"):
        orcids = sorted(set(g["orcid_n"]) - {""})
        if pid in conflitos:
            motivo = "conflito: ORCIDs com gêneros diferentes no genero2 (" + ", ".join(conflitos[pid]) + ")"
        elif orcids:
            motivo = "ORCID fora do genero2"
        else:
            motivo = "sem ORCID"
        nomes = Counter(g["nome"])
        dicas = set()
        for nome in nomes:
            dicas |= dica_por_nome.get(norm_nome(nome), set())
            dicas |= dica_por_nome.get(norm_nome(nome_direto(nome)), set())
        linhas.append({
            "pessoa_id": pid,
            "nome": nomes.most_common(1)[0][0],
            "variantes_nome": " | ".join(sorted(set(nomes) - {nomes.most_common(1)[0][0]})),
            "orcids": " | ".join(orcids),
            "lattes": " | ".join(sorted(set(g["lattes"]) - {""})),
            "n_participacoes": len(g),
            "papeis": "; ".join(f"{k}:{v}" for k, v in Counter(g["papel"]).most_common()),
            "anos": f"{int(g['ano'].min())}–{int(g['ano'].max())}" if g["ano"].notna().any() else "",
            "motivo": motivo,
            "dica_mesmo_nome": " | ".join(sorted(dicas)),
            "dica_base_antiga": " | ".join(sorted(
                f"{o} ({nome_g2[o]})" if o in nome_g2 else f"{o} (fora do genero2)"
                for o in {antigos[i] for i in g.index if i in antigos})),
            "genero": "",
        })
    anotar = pd.DataFrame(linhas).sort_values(["n_participacoes", "nome"], ascending=[False, True])
    anotar.to_csv(args.anotar, index=False)

    for pasta in args.tabelas:
        arq = Path(pasta) / "participacoes.csv"
        q = pd.read_csv(arq, dtype={"orcid": str, "lattes": str, "ano_nasc": "Int64"})
        q = q.drop(columns=[c for c in NOVAS if c in q])
        q = q.merge(p[["codigo", "ordem"] + NOVAS], on=["codigo", "ordem"], how="left", validate="1:1")
        q.to_csv(arq, index=False)

    print(f"{len(p)} participações; com gênero: {(p['genero'] != '').sum()} "
          f"({p['genero_fonte'].replace('', 'sem').value_counts().to_dict()})")
    print(f"pessoas: {p['pessoa_id'].nunique()}; a anotar: {len(anotar)} "
          f"({anotar['motivo'].str.split(':').str[0].value_counts().to_dict()}); "
          f"com dica de mesmo nome: {(anotar['dica_mesmo_nome'] != '').sum()}; "
          f"com dica da base antiga: {(anotar['dica_base_antiga'] != '').sum()}")
    print(f"participações cobertas pela lista a anotar: {anotar['n_participacoes'].sum()}")
    if conflitos:
        print(f"conflitos de gênero: {conflitos}")
    print(f"-> {args.anotar}; colunas {NOVAS} em " + ", ".join(args.tabelas))


if __name__ == "__main__":
    main()
