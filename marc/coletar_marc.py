"""Baixa o MARC das defesas do repositório da Unicamp (Sophia) direto do endpoint JSON.

Substitui o Selenium do crawler2.py: em vez de abrir cada página e clicar na aba
MARC, faz POST em /marc/obterRegistroMARCTags com {"codigoRegistro": <id>}.
O endpoint exige os cookies da validação anti-robô (SBW.REQUEST.VALIDATION) e o
token antiforgery do ASP.NET (cookie + cabeçalho requestverificationtoken).

Duas formas de obter essas credenciais:
  1. --curl arquivo.txt  -> cole num arquivo o "Copy as cURL" do DevTools.
  2. (padrão) Playwright abre um registro, clica em MARC e captura a requisição.
     Requer: pip install playwright requests pandas && playwright install chromium

Uso:
  python marc/coletar_marc.py marc/links/links*.csv --saida marc/marc_raw --curl marc/curl.txt --pausa 1.5

Com --curl, se um pedido falha, o script pede de novo um id de controle que já
funcionou: se o controle também falhar, o token expirou e o script para; se não,
a falha é do registro (status no _log.csv, corpo em --saida/_falhas/<id>.txt) e
a coleta segue. Respostas 200 que não são a string MARC esperada (com <br/>)
contam como "formato-inesperado" e não são salvas como <id>.json.

Saída: um JSON bruto por registro em --saida/<id>.json (retomável: pula os já
baixados) e --saida/_log.csv com o status de cada pedido.
NÃO versionem curl.txt: ele carrega cookies da sua sessão.
"""
import argparse
import csv
import json
import re
import shlex
import sys
import time
from pathlib import Path

import pandas as pd
import requests

BASE = "https://repositorio.unicamp.br"
ENDPOINT = f"{BASE}/marc/obterRegistroMARCTags"
HEADERS_UTEIS = {"requestverificationtoken", "user-agent", "accept", "accept-language"}


def ids_dos_csvs(caminhos):
    """(id, csv de origem) únicos. Usa a coluna 'codigo' se existir; senão extrai da url."""
    ids = []
    for c in caminhos:
        df = pd.read_csv(c)
        codigos = df["codigo"] if "codigo" in df else [None] * len(df)
        for url, cod in zip(df["url"], codigos):
            if pd.notna(cod):
                ids.append((int(cod), Path(c).name))
                continue
            m = re.search(r"/detalhe/(\d+)", str(url), re.I)
            if m:
                ids.append((int(m.group(1)), Path(c).name))
            else:
                print(f"[aviso] {Path(c).name}: link sem id, não será coletado: {url}", file=sys.stderr)
    vistos, unicos = set(), []
    for i, origem in ids:
        if i not in vistos:
            vistos.add(i)
            unicos.append((i, origem))
    return unicos


def credenciais_do_curl(arquivo):
    """Lê cabeçalhos (-H) e cookies (-b) de um 'Copy as cURL'."""
    tokens = shlex.split(Path(arquivo).read_text().replace("\\\n", " "))
    headers, cookies = {}, {}
    for flag, valor in zip(tokens, tokens[1:]):
        if flag in ("-H", "--header"):
            nome, _, v = valor.partition(":")
            if nome.strip().lower() in HEADERS_UTEIS:
                headers[nome.strip().lower()] = v.strip()
        elif flag in ("-b", "--cookie"):
            for par in valor.split(";"):
                k, _, v = par.strip().partition("=")
                if k:
                    cookies[k] = v
    return headers, cookies


def credenciais_do_playwright(id_exemplo, mostrar=False):
    """Abre um registro num navegador real, clica em MARC e captura a requisição."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        nav = p.chromium.launch(headless=not mostrar)
        ctx = nav.new_context()
        page = ctx.new_page()
        page.goto(f"{BASE}/acervo/detalhe/{id_exemplo}", wait_until="networkidle", timeout=90_000)
        with page.expect_request(lambda r: "obterRegistroMARCTags" in r.url, timeout=60_000) as req_info:
            page.get_by_role("button", name=re.compile("MARC", re.I)).first.click()
        req = req_info.value
        headers = {k: v for k, v in req.headers.items() if k.lower() in HEADERS_UTEIS}
        cookies = {c["name"]: c["value"] for c in ctx.cookies(BASE)}
        nav.close()
    return headers, cookies


def nova_sessao(headers, cookies):
    s = requests.Session()
    s.headers.update(headers)
    s.headers.update({"content-type": "application/json;charset=UTF-8", "origin": BASE})
    for k, v in cookies.items():
        s.cookies.set(k, v, domain="repositorio.unicamp.br")
    return s


def pedir(sessao, codigo):
    r = sessao.post(
        ENDPOINT,
        json={"codigoRegistro": codigo},
        headers={"referer": f"{BASE}/acervo/detalhe/{codigo}"},
        timeout=60,
    )
    if r.status_code != 200:
        return None, r.status_code, r.text
    try:
        dados = r.json()
    except ValueError:  # veio HTML (ex.: tela de validação) em vez de JSON
        return None, "nao-json", r.text
    if not isinstance(dados, str) or "<br/>" not in dados:
        return None, "formato-inesperado", r.text
    return dados, 200, None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csvs", nargs="+", help="CSVs com coluna 'url' (ex.: csvs/links2025.csv)")
    ap.add_argument("--saida", default="marc_raw")
    ap.add_argument("--curl", help="arquivo com o 'Copy as cURL' do DevTools")
    ap.add_argument("--pausa", type=float, default=1.0, help="segundos entre pedidos")
    ap.add_argument("--mostrar", action="store_true", help="abre o navegador visível (Playwright)")
    ap.add_argument("--controle", type=int, default=1266276,
                    help="id que sabidamente funciona, usado para distinguir falha do registro "
                         "de token expirado (padrão: 1266276)")
    args = ap.parse_args()

    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    pendentes = [(i, o) for i, o in ids_dos_csvs(args.csvs) if not (saida / f"{i}.json").exists()]
    print(f"{len(pendentes)} registros a baixar", file=sys.stderr)
    if not pendentes:
        return

    def credenciais():
        if args.curl:
            return credenciais_do_curl(args.curl)
        return credenciais_do_playwright(pendentes[0][0], args.mostrar)

    sessao = nova_sessao(*credenciais())
    log_path = saida / "_log.csv"
    novo_log = not log_path.exists()
    with open(log_path, "a", newline="") as flog:
        log = csv.writer(flog)
        if novo_log:
            log.writerow(["codigo", "csv_origem", "status"])
        ultimo_ok = args.controle
        for n, (codigo, origem) in enumerate(pendentes, 1):
            dados, status, corpo = pedir(sessao, codigo)
            if dados is None and not args.curl:
                # credenciais expiradas: recaptura uma vez e tenta de novo
                sessao = nova_sessao(*credenciais_do_playwright(codigo, args.mostrar))
                dados, status, corpo = pedir(sessao, codigo)
            if dados is None and args.curl:
                # A falha é do registro ou do token? Pede de novo um id que já funcionou.
                controle_ok = False
                if ultimo_ok is not None:
                    time.sleep(args.pausa)
                    controle_ok = pedir(sessao, ultimo_ok)[0] is not None
                if not controle_ok:
                    print(f"[{codigo}] falhou ({status}) e o id de controle {ultimo_ok} também; "
                          "o token do cURL provavelmente expirou. Copie um novo e rode de novo "
                          "(os já baixados são pulados).", file=sys.stderr)
                    break
                falhas = saida / "_falhas"
                falhas.mkdir(exist_ok=True)
                (falhas / f"{codigo}.txt").write_text(f"status: {status}\n\n{corpo or ''}")
                print(f"[{codigo}] falhou ({status}); controle {ultimo_ok} ok -> falha do registro, "
                      f"corpo em {falhas / f'{codigo}.txt'}", file=sys.stderr)
            if dados is not None:
                (saida / f"{codigo}.json").write_text(json.dumps(dados, ensure_ascii=False, indent=1))
                ultimo_ok = codigo
            log.writerow([codigo, origem, status])
            flog.flush()
            if n % 25 == 0:
                print(f"{n}/{len(pendentes)}", file=sys.stderr)
            time.sleep(args.pausa)


if __name__ == "__main__":
    main()
