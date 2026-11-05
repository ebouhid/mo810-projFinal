"""Gera links{ano}.csv (um por aba de ano) a partir da planilha de defesas do IC.

Mesma lógica do get_links.py da raiz: percorre as células de cada aba, guarda o
último cabeçalho de tipo visto (MESTRADO, DOUTORADO, MESTRADO PROFISSIONAL) e
coleta os hyperlinks que apontam para o repositório da Unicamp. Diferenças:
  - planilha, intervalo de anos e pasta de saída são parâmetros;
  - o cabeçalho é comparado sem diferenciar maiúsculas/minúsculas (a aba 2025
    usa "Mestrado"/"Doutorado");
  - extrai o código do registro (/acervo/detalhe/<id>, sem diferenciar caixa);
    links sem id (ex.: handle antigo jspui) podem ser resolvidos à mão em
    <saida>/ids_manuais.csv (colunas url,codigo,fonte);
  - compara com os links{ano}.csv antigos (--comparar) e gera
    antigos_substituidos.csv com os ids que só existem na base antiga.

Não copia nome do aluno nem título: só tipo, url, código, ano e célula.

Uso:
  python marc/gerar_links.py --planilha "marc/Histórico de Defesas de Mestrado e Doutorado - 2026.xlsx" \
      --inicio 2006 --fim 2025 --saida marc/links --comparar csvs
"""
import argparse
import datetime
import re
from collections import defaultdict
from pathlib import Path

import openpyxl
import pandas as pd

TIPOS = {"DOUTORADO", "MESTRADO", "MESTRADO PROFISSIONAL"}
RE_ID = re.compile(r"/detalhe/(\d+)", re.I)


def codigo_da_url(url, manuais):
    if url in manuais:
        return manuais[url]
    m = RE_ID.search(str(url))
    return int(m.group(1)) if m else None


def links_da_aba(sheet, ano, manuais):
    """Devolve (linhas de link, nº da linha das defesas sem link)."""
    linhas, sem_link = [], []
    tipo = None
    for row in sheet.iter_rows():
        tem_data = tem_link = False
        for cell in row:
            v = cell.value
            if isinstance(v, str) and v.strip().upper() in TIPOS:
                tipo = v.strip().upper()
            if isinstance(v, datetime.datetime):
                tem_data = True
            alvo = cell.hyperlink.target if cell.hyperlink else None
            if alvo and "repositorio" in alvo:
                tem_link = True
                linhas.append({"tipo": tipo, "url": alvo, "codigo": codigo_da_url(alvo, manuais),
                               "ano": ano, "celula": cell.coordinate})
        if tem_data and not tem_link:
            sem_link.append(row[0].row)
    return linhas, sem_link


def comparar(novos, pasta_antiga):
    """Imprime diferenças por ano e devolve os links que só existem na base antiga."""
    so_antigos = []
    print("\nano  antigo  novo  saíram(antigo->)  entraram(->novo)")
    for ano, df in sorted(novos.items()):
        arq = Path(pasta_antiga) / f"links{ano}.csv"
        if not arq.exists():
            print(f"{ano}  {'-':>6}  {len(df):>4}  (sem arquivo antigo)")
            continue
        antigo = pd.read_csv(arq)
        chave = lambda u: codigo_da_url(u, {}) or u  # noqa: E731
        ant = {chave(u): u for u in antigo["url"]}
        nov = {(int(c) if pd.notna(c) else u) for c, u in zip(df["codigo"], df["url"])}
        sairam = [k for k in ant if k not in nov]
        entraram = [k for k in nov if k not in ant]
        dup = sorted({k for k in map(chave, antigo["url"]) if list(map(chave, antigo["url"])).count(k) > 1})
        print(f"{ano}  {len(antigo):>6}  {len(df):>4}  {sairam or ''}  {entraram or ''}"
              + (f"  (duplicado no antigo: {dup})" if dup else ""))
        so_antigos += [{"url": ant[k], "codigo": k, "ano": ano} for k in sairam if isinstance(k, int)]
    return pd.DataFrame(so_antigos, columns=["url", "codigo", "ano"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--planilha", required=True)
    ap.add_argument("--inicio", type=int, default=2006)
    ap.add_argument("--fim", type=int, required=True, help="último ano (inclusive)")
    ap.add_argument("--saida", default="marc/links")
    ap.add_argument("--comparar", help="pasta com os links{ano}.csv antigos (ex.: csvs)")
    args = ap.parse_args()

    out = Path(args.saida)
    out.mkdir(parents=True, exist_ok=True)
    manuais = {}
    if (out / "ids_manuais.csv").exists():
        m = pd.read_csv(out / "ids_manuais.csv")
        manuais = dict(zip(m["url"], m["codigo"].astype(int)))

    wb = openpyxl.load_workbook(args.planilha)
    novos, onde = {}, defaultdict(list)
    print("ano  links  MESTRADO  DOUTORADO  M.PROF  sem_tipo  sem_id  defesas_sem_link(linha)")
    for ano in range(args.inicio, args.fim + 1):
        linhas, sem_link = links_da_aba(wb[str(ano)], ano, manuais)
        df = pd.DataFrame(linhas, columns=["tipo", "url", "codigo", "ano", "celula"])
        df["codigo"] = df["codigo"].astype("Int64")
        df.to_csv(out / f"links{ano}.csv", index=False)
        novos[ano] = df
        for c, cel in zip(df["codigo"].dropna(), df["celula"][df["codigo"].notna()]):
            onde[int(c)].append(f"{ano}:{cel}")
        t = df["tipo"].value_counts()
        print(f"{ano}  {len(df):>5}  {t.get('MESTRADO', 0):>8}  {t.get('DOUTORADO', 0):>9}  "
              f"{t.get('MESTRADO PROFISSIONAL', 0):>6}  {df['tipo'].isna().sum():>8}  "
              f"{df['codigo'].isna().sum():>6}  {sem_link or ''}")
        for u in df.loc[df["codigo"].isna(), "url"]:
            print(f"      link sem id: {u}")

    total = sum(len(d) for d in novos.values())
    print(f"\ntotal de links: {total}; ids únicos: {len(onde)}")
    for c, lugares in onde.items():
        if len(lugares) > 1:
            print(f"id duplicado: {c} em {lugares}")

    if args.comparar:
        so_antigos = comparar(novos, args.comparar)
        so_antigos.to_csv(out / "antigos_substituidos.csv", index=False)
        print(f"\n{len(so_antigos)} ids só na base antiga -> {out / 'antigos_substituidos.csv'}")


if __name__ == "__main__":
    main()
