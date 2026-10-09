#!/usr/bin/env python3
"""
Baixa os dados de "Discentes da Pós-Graduação stricto sensu do Brasil" do
Portal de Dados Abertos da CAPES (CKAN), de 2004 a 2024.

Requisitos:
    pip install requests tqdm        # tqdm é opcional (barra de progresso)

Exemplos:
    python baixar_discentes_capes.py --listar             # o que há em cada conjunto
    python baixar_discentes_capes.py --listar --colunas   # + colunas de cada tabela

    # Baixar os CSVs de todos os anos + PDFs de metadados (padrão)
    python baixar_discentes_capes.py

    # Baixar e gerar extratos só com as linhas da Unicamp (um por ano + um combinado)
    python baixar_discentes_capes.py --filtro SG_ENTIDADE_ENSINO=UNICAMP

    # Só alguns anos; ou tudo, incluindo os XLSX (mesmos dados dos CSVs)
    python baixar_discentes_capes.py --recursos "2019|2020"
    python baixar_discentes_capes.py --formatos todos

    python baixar_discentes_capes.py --buscar "discentes stricto sensu"

Sobre a API DataStore: em outubro/2026 várias tabelas do DataStore da CAPES
estavam incompletas (ex.: 3.000 linhas em cada ano de 2013 a 2016, 1.000 em 2019).
Por isso o --filtro é aplicado localmente, sobre o CSV completo baixado.
"--modo datastore" continua disponível, mas não serve para análise sem conferência.

Saída (padrão: ./dados/capes_discentes):
    <slug-do-conjunto>/<arquivo>              arquivos originais
    <slug-do-conjunto>/_metadados_ckan.json   resposta do package_show
    filtrado/<arquivo>__<filtro>.csv          extratos por ano (UTF-8), com --filtro
    filtrado/_combinado__<filtro>.csv         todos os anos juntos (união das colunas)
    manifesto.csv                             origem, tamanho, sha256, linhas e data

Downloads interrompidos ficam como "<arquivo>.part" e são retomados na
próxima execução. Arquivos já baixados são pulados (use --forcar para refazer).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from tqdm import tqdm
except ImportError:  # barra de progresso é opcional
    tqdm = None

BASE_URL = "https://dadosabertos.capes.gov.br"

DATASETS_PADRAO = [
    "discentes-dos-programas-de-pos-graduacao-stricto-sensu-no-brasil-2004-a-2012",
    "discentes-da-pos-graduacao-stricto-sensu-do-brasil-2013-a-2016",
    "discentes-da-pos-graduacao-stricto-sensu-do-brasil-2017-a-2019",  # inclui 2020
    "2021-a-2024-discentes-da-pos-graduacao-stricto-sensu-do-brasil",
]

FORMATOS_PADRAO = {"csv", "pdf"}
FORMATOS_TABULARES = {"csv", "tsv", "xlsx", "xls"}
CODIFICACOES = ("utf-8-sig", "utf-8", "cp1252", "latin-1")  # latin-1 nunca falha
BLOCO = 1 << 20  # 1 MiB
CAMPOS_MANIFESTO = [
    "dataset", "recurso_id", "recurso_nome", "formato", "modo", "url",
    "arquivo_local", "bytes", "linhas", "linhas_origem", "sha256", "filtros",
    "recurso_modificado_em", "baixado_em", "status",
]

csv.field_size_limit(2**31 - 1)  # títulos de tese podem ser longos


# --------------------------------------------------------------------------- #
# Cliente CKAN
# --------------------------------------------------------------------------- #
class Ckan:
    def __init__(self, base_url: str, timeout_leitura: int = 300):
        self.base = base_url.rstrip("/")
        self.timeout = (30, timeout_leitura)
        self.s = requests.Session()
        retry = Retry(
            total=5, connect=5, read=5, backoff_factor=2,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
        )
        adaptador = HTTPAdapter(max_retries=retry)
        self.s.mount("https://", adaptador)
        self.s.mount("http://", adaptador)
        self.s.headers["User-Agent"] = "baixar-discentes-capes/1.1 (python-requests)"

    def acao(self, nome: str, **params):
        """Chama /api/3/action/<nome> e devolve o campo 'result'."""
        url = f"{self.base}/api/3/action/{nome}"
        r = self.s.get(url, params=params, timeout=self.timeout)
        try:
            dados = r.json()
        except ValueError:
            r.raise_for_status()
            raise RuntimeError(f"resposta não-JSON de {r.url}")
        if not dados.get("success"):
            raise RuntimeError(f"{nome} falhou ({r.status_code}): {dados.get('error')}")
        return dados["result"]


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
def slug_de(x: str) -> str:
    """Aceita o slug ou a URL completa do conjunto."""
    x = x.strip().rstrip("/")
    m = re.search(r"/dataset/([^/?#]+)", x)
    return m.group(1) if m else x


def formato_de(rec: dict) -> str:
    fmt = (rec.get("format") or "").strip().lower().lstrip(".")
    if not fmt:
        fmt = Path(urlparse(rec.get("url") or "").path).suffix.lower().lstrip(".")
    return fmt


def inteiro(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def tamanho_legivel(n) -> str:
    n = inteiro(n)
    if n is None:
        return "?"
    for unidade in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unidade}" if unidade == "B" else f"{n:.1f} {unidade}"
        n /= 1024
    return f"{n:.1f} TB"


def seguro(texto: str, max_len: int = 120) -> str:
    texto = re.sub(r"[^\w.\-]+", "_", texto, flags=re.UNICODE).strip("._")
    return texto[:max_len] or "recurso"


def nome_arquivo(rec: dict, fmt: str) -> str:
    nome = unquote(Path(urlparse(rec.get("url") or "").path).name)
    if not nome or "." not in nome:
        nome = seguro(rec.get("name") or rec["id"])
        if fmt and not nome.lower().endswith("." + fmt):
            nome += "." + fmt
    return seguro(nome, 200)


def sufixo_filtros(filtros: dict) -> str:
    partes = []
    for col, val in filtros.items():
        val = "+".join(val) if isinstance(val, list) else val
        partes.append(f"{col}-{val}")
    return "__" + seguro("_".join(partes), 80)


def sha256_de(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(BLOCO), b""):
            h.update(bloco)
    return h.hexdigest()


def agora_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parece_incompleto(total, estimado=False) -> bool:
    """Contagens redondas (3000, 14000...) indicam carga parcial no DataStore."""
    t = inteiro(total)
    return bool(estimado) or (t is not None and t > 0 and t % 1000 == 0)


class Progresso:
    """Barra do tqdm se disponível; senão, imprime a cada 5 s."""

    def __init__(self, total, desc, unidade="B"):
        self.desc, self.unidade, self.total = desc, unidade, total
        self.n, self.ultimo = 0, time.monotonic()
        self.barra = None
        if tqdm is not None:
            self.barra = tqdm(
                total=total, desc=desc, unit=unidade, unit_scale=True,
                unit_divisor=1024 if unidade == "B" else 1000, leave=False,
            )

    def update(self, k):
        if self.barra is not None:
            self.barra.update(k)
            return
        self.n += k
        t = time.monotonic()
        if t - self.ultimo > 5:
            feito = tamanho_legivel(self.n) if self.unidade == "B" else f"{self.n:,} {self.unidade}"
            alvo = ""
            if self.total:
                alvo = " de " + (tamanho_legivel(self.total) if self.unidade == "B"
                                 else f"{self.total:,}")
            print(f"    {self.desc}: {feito}{alvo}", file=sys.stderr)
            self.ultimo = t

    def close(self):
        if self.barra is not None:
            self.barra.close()


# --------------------------------------------------------------------------- #
# Download
# --------------------------------------------------------------------------- #
def baixar_arquivo(cli: Ckan, url: str, destino: Path, _tentou_de_novo=False) -> int:
    """Baixa url -> destino via <destino>.part, retomando se possível."""
    parcial = destino.with_name(destino.name + ".part")
    ja = parcial.stat().st_size if parcial.exists() else 0
    headers = {"Range": f"bytes={ja}-"} if ja else {}

    with cli.s.get(url, headers=headers, stream=True, timeout=cli.timeout) as r:
        if r.status_code == 416:  # .part inválido ou já completo: recomeça
            parcial.unlink(missing_ok=True)
            if _tentou_de_novo:
                raise RuntimeError("servidor recusou o intervalo (416) duas vezes")
            return baixar_arquivo(cli, url, destino, _tentou_de_novo=True)
        r.raise_for_status()
        if r.status_code == 206:
            modo = "ab"
            print(f"    retomando a partir de {tamanho_legivel(ja)}", file=sys.stderr)
        else:
            modo, ja = "wb", 0
        restante = inteiro(r.headers.get("Content-Length"))
        total = ja + restante if restante is not None else None
        prog = Progresso(total, destino.name)
        prog.update(ja)
        try:
            with open(parcial, modo) as f:
                for bloco in r.iter_content(BLOCO):
                    f.write(bloco)
                    prog.update(len(bloco))
        finally:
            prog.close()

    obtido = parcial.stat().st_size
    if total is not None and obtido != total:
        raise IOError(f"download incompleto ({obtido} de {total} bytes); rode de novo para retomar")
    parcial.replace(destino)
    return obtido


def baixar_datastore(cli: Ckan, recurso_id: str, destino: Path,
                     filtros: dict, limite: int) -> int:
    """Pagina datastore_search e grava um CSV UTF-8. Devolve o nº de linhas."""
    parcial = destino.with_name(destino.name + ".part")
    offset, total, escritor, prog = 0, None, None, None
    try:
        with open(parcial, "w", newline="", encoding="utf-8") as f:
            while True:
                params = {"resource_id": recurso_id, "limit": limite,
                          "offset": offset, "sort": "_id"}
                if filtros:
                    params["filters"] = json.dumps(filtros, ensure_ascii=False)
                res = cli.acao("datastore_search", **params)
                if escritor is None:
                    campos = [c["id"] for c in res["fields"] if c["id"] != "_id"]
                    escritor = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
                    escritor.writeheader()
                    total = inteiro(res.get("total"))
                    prog = Progresso(total, destino.name, unidade="linhas")
                registros = res.get("records") or []
                if not registros:
                    break
                escritor.writerows(registros)
                offset += len(registros)
                prog.update(len(registros))
                # O servidor pode limitar 'limit' (rows_max); por isso o critério é o total.
                if total is not None and offset >= total:
                    break
    except BaseException:
        parcial.unlink(missing_ok=True)  # paginação não é retomável: recomeça na próxima vez
        raise
    finally:
        if prog is not None:
            prog.close()
    if total is not None and offset != total:
        raise IOError(f"DataStore devolveu {offset} de {total} linhas")
    parcial.replace(destino)
    return offset


# --------------------------------------------------------------------------- #
# Filtro local sobre o CSV completo
# --------------------------------------------------------------------------- #
def detectar_codificacao(caminho: Path) -> str:
    with open(caminho, "rb") as f:
        amostra = f.read(1 << 20)
    if amostra.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    try:
        amostra.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError as e:
        if e.start >= len(amostra) - 3:  # caractere cortado no fim da amostra
            return "utf-8"
    try:
        amostra.decode("cp1252")
        return "cp1252"
    except UnicodeDecodeError:
        return "latin-1"


def _filtrar_csv(origem: Path, parcial: Path, filtros: dict, codif: str):
    lidas = mantidas = 0
    prog = Progresso(None, f"filtrando {origem.name}", unidade="linhas")
    try:
        with open(origem, newline="", encoding=codif) as fi, \
                open(parcial, "w", newline="", encoding="utf-8") as fo:
            primeira = fi.readline()
            sep = ";" if primeira.count(";") >= primeira.count(",") else ","
            cab = [c.strip() for c in next(csv.reader([primeira], delimiter=sep))]
            faltando = [c for c in filtros if c not in cab]
            if faltando:
                raise ValueError(f"coluna(s) ausente(s) neste arquivo: {', '.join(faltando)}")
            alvo = {
                cab.index(col): {str(v).strip().casefold()
                                 for v in (vals if isinstance(vals, list) else [vals])}
                for col, vals in filtros.items()
            }
            w = csv.writer(fo)
            w.writerow(cab)
            for linha in csv.reader(fi, delimiter=sep):
                lidas += 1
                if all(i < len(linha) and linha[i].strip().casefold() in vals
                       for i, vals in alvo.items()):
                    w.writerow(linha)
                    mantidas += 1
                if lidas % 50000 == 0:
                    prog.update(50000)
    finally:
        prog.close()
    return lidas, mantidas


def filtrar_csv(origem: Path, destino: Path, filtros: dict):
    """Grava em destino (UTF-8, vírgula) só as linhas que atendem aos filtros."""
    parcial = destino.with_name(destino.name + ".part")
    inicio = CODIFICACOES.index(detectar_codificacao(origem))
    try:
        for codif in CODIFICACOES[inicio:]:
            try:
                lidas, mantidas = _filtrar_csv(origem, parcial, filtros, codif)
                break
            except UnicodeDecodeError:  # a amostra enganou: tenta a próxima codificação
                continue
    except BaseException:
        parcial.unlink(missing_ok=True)
        raise
    parcial.replace(destino)
    return lidas, mantidas, codif


def extrair(origem: Path, linha_origem: dict, args, filtros: dict, manifesto: dict) -> dict:
    pasta = args.saida / "filtrado"
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / (origem.stem + sufixo_filtros(filtros) + ".csv")
    chave = destino.as_posix()
    linha = {k: linha_origem.get(k, "") for k in
             ("dataset", "recurso_id", "recurso_nome", "url", "recurso_modificado_em")}
    linha.update(formato="csv", modo="filtro-local", arquivo_local=chave,
                 filtros=json.dumps(filtros, ensure_ascii=False))
    anterior = manifesto.get(chave, {})

    atualizado = destino.exists() and destino.stat().st_mtime >= origem.stat().st_mtime
    if atualizado and anterior.get("linhas") and not args.forcar:
        print(f"    extrato já existe ({int(anterior['linhas']):,} linhas)")
        linha.update(anterior)
        linha["status"] = "existente"
        return linha
    try:
        lidas, mantidas, codif = filtrar_csv(origem, destino, filtros)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"    ERRO no filtro: {e}", file=sys.stderr)
        linha["status"] = f"falhou: {e}"
        return linha
    print(f"    extrato: {mantidas:,} de {lidas:,} linhas (lido como {codif}) -> {destino}")
    if mantidas == 0:
        print("    aviso: nenhuma linha atendeu ao filtro; confira o valor usado")
    linha.update(bytes=destino.stat().st_size, linhas=mantidas, linhas_origem=lidas,
                 sha256=sha256_de(destino), baixado_em=agora_iso(), status="extraído")
    return linha


def combinar_extratos(pasta: Path, filtros: dict):
    """Junta os extratos de todos os anos num só CSV (união das colunas)."""
    sufixo = sufixo_filtros(filtros)
    saida = pasta / f"_combinado{sufixo}.csv"
    arquivos = sorted(p for p in pasta.glob(f"*{sufixo}.csv") if p != saida)
    if not arquivos:
        return None
    colunas = []
    for p in arquivos:
        with open(p, newline="", encoding="utf-8") as f:
            for c in next(csv.reader(f), []):
                if c not in colunas:
                    colunas.append(c)
    total = 0
    parcial = saida.with_name(saida.name + ".part")
    with open(parcial, "w", newline="", encoding="utf-8") as fo:
        w = csv.DictWriter(fo, fieldnames=["ARQUIVO_ORIGEM"] + colunas, restval="")
        w.writeheader()
        for p in arquivos:
            with open(p, newline="", encoding="utf-8") as fi:
                for reg in csv.DictReader(fi):
                    reg["ARQUIVO_ORIGEM"] = p.name
                    w.writerow(reg)
                    total += 1
    parcial.replace(saida)
    print(f"\nCombinado: {total:,} linhas de {len(arquivos)} arquivo(s), "
          f"{len(colunas)} colunas -> {saida}")
    return saida


# --------------------------------------------------------------------------- #
# Manifesto
# --------------------------------------------------------------------------- #
def ler_manifesto(caminho: Path) -> dict:
    if not caminho.exists():
        return {}
    with open(caminho, newline="", encoding="utf-8") as f:
        return {linha["arquivo_local"]: linha for linha in csv.DictReader(f)}


def gravar_manifesto(caminho: Path, linhas: dict):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_name(caminho.name + ".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS_MANIFESTO, extrasaction="ignore")
        w.writeheader()
        for chave in sorted(linhas):
            w.writerow(linhas[chave])
    tmp.replace(caminho)


# --------------------------------------------------------------------------- #
# Processamento de um recurso
# --------------------------------------------------------------------------- #
def processar_recurso(cli, slug, rec, pasta: Path, args, filtros, manifesto, usados) -> list:
    fmt = formato_de(rec)
    via_ds = (args.modo == "datastore" and fmt in FORMATOS_TABULARES
              and rec.get("datastore_active") is not False)

    nome = nome_arquivo(rec, fmt)
    if via_ds:
        nome = Path(nome).stem + (sufixo_filtros(filtros) if filtros else "__datastore") + ".csv"
    if nome in usados:  # nomes repetidos dentro do mesmo conjunto
        nome = f"{Path(nome).stem}__{rec['id'][:8]}{Path(nome).suffix}"
    usados.add(nome)
    destino = pasta / nome
    chave = destino.as_posix()

    linha = {
        "dataset": slug, "recurso_id": rec["id"], "recurso_nome": rec.get("name") or "",
        "formato": fmt, "url": rec.get("url") or "", "arquivo_local": chave,
        "modo": "datastore" if via_ds else "arquivo",
        "filtros": json.dumps(filtros, ensure_ascii=False) if (filtros and via_ds) else "",
        "recurso_modificado_em": rec.get("last_modified") or rec.get("metadata_modified") or "",
    }
    anterior = manifesto.get(chave, {})
    print(f"  - {rec.get('name') or rec['id']} [{fmt or '?'}]")

    if destino.exists() and not args.forcar:
        tam = destino.stat().st_size
        esperado = inteiro(rec.get("size"))
        if not via_ds and esperado and esperado != tam:
            print(f"    aviso: tamanho local ({tam}) difere do informado pelo portal "
                  f"({esperado}); use --forcar para rebaixar")
        sha = anterior.get("sha256") if inteiro(anterior.get("bytes")) == tam else None
        linha.update(anterior)
        linha.update(bytes=tam, sha256=sha or sha256_de(destino), status="existente")
        print(f"    já existe ({tamanho_legivel(tam)}), pulando download")
    else:
        if args.forcar:
            destino.with_name(destino.name + ".part").unlink(missing_ok=True)
        try:
            if via_ds:
                n = baixar_datastore(cli, rec["id"], destino, filtros, args.limite_pagina)
                linha["linhas"] = n
                print(f"    {n:,} linhas -> {destino}")
                if parece_incompleto(n) and not filtros:
                    print("    aviso: contagem redonda; esta tabela do DataStore "
                          "provavelmente está incompleta")
            else:
                baixar_arquivo(cli, linha["url"], destino)
                print(f"    {tamanho_legivel(destino.stat().st_size)} -> {destino}")
            linha.update(bytes=destino.stat().st_size, sha256=sha256_de(destino),
                         baixado_em=agora_iso(), status="baixado")
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"    ERRO: {e}", file=sys.stderr)
            linha["status"] = f"falhou: {e}"
            return [linha]

    resultado = [linha]
    if filtros and not via_ds and fmt == "csv":
        resultado.append(extrair(destino, linha, args, filtros, manifesto))
    return resultado


# --------------------------------------------------------------------------- #
# Comandos
# --------------------------------------------------------------------------- #
def filtrar_recursos(recursos, args):
    sel = []
    for rec in recursos:
        fmt = formato_de(rec)
        if args.formatos is not None and fmt not in args.formatos:
            continue
        if args.recursos:
            alvo = f"{rec.get('name') or ''} {nome_arquivo(rec, fmt)}"
            if not re.search(args.recursos, alvo, flags=re.IGNORECASE):
                continue
        sel.append(rec)
    return sel


def listar(cli, recursos, mostrar_colunas):
    for rec in recursos:
        fmt = formato_de(rec)
        ds = {True: "sim", False: "não"}.get(rec.get("datastore_active"), "?")
        print(f"  - {rec.get('name') or rec['id']}")
        print(f"      formato: {fmt or '?'} | tamanho: {tamanho_legivel(rec.get('size'))}"
              f" | DataStore: {ds} | id: {rec['id']}")
        print(f"      url: {rec.get('url')}")
        if mostrar_colunas and rec.get("datastore_active") is not False \
                and fmt in FORMATOS_TABULARES:
            try:
                res = cli.acao("datastore_search", resource_id=rec["id"], limit=0)
                cols = [f"{c['id']} ({c.get('type', '?')})"
                        for c in res["fields"] if c["id"] != "_id"]
                total = inteiro(res.get("total"))
                aviso = ("  <- provavelmente incompleto"
                         if parece_incompleto(total, res.get("total_was_estimated")) else "")
                print(f"      linhas no DataStore: {total if total is not None else '?'}{aviso}")
                print(f"      colunas ({len(cols)}):")
                for c in cols:
                    print(f"        {c}")
            except Exception as e:
                print(f"      colunas indisponíveis: {e}")


def buscar(cli, termo):
    res = cli.acao("package_search", q=termo, rows=100)
    print(f"{res.get('count', 0)} conjunto(s) para '{termo}':")
    for p in res.get("results", []):
        print(f"  {p['name']}\n      {p.get('title')} ({p.get('num_resources', '?')} recursos)")


def ler_formatos(s: str):
    s = s.strip().lower()
    if s in ("todos", "all", "*"):
        return None
    return {x.strip().lstrip(".") for x in s.split(",") if x.strip()}


def analisar_args(argv=None):
    p = argparse.ArgumentParser(
        description="Baixa os dados de discentes da pós-graduação do portal de dados abertos da CAPES.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("datasets", nargs="*", default=DATASETS_PADRAO,
                   help="slugs ou URLs dos conjuntos (padrão: os 4 de discentes 2004–2024)")
    p.add_argument("-o", "--saida", type=Path, default=Path("dados/capes_discentes"),
                   help="pasta de saída (padrão: %(default)s)")
    p.add_argument("--formatos", type=ler_formatos, default=set(FORMATOS_PADRAO),
                   help="formatos separados por vírgula, ou 'todos' (padrão: csv,pdf; "
                        "os XLSX repetem os dados dos CSVs)")
    p.add_argument("--recursos", metavar="REGEX",
                   help="só recursos cujo nome/arquivo casa com a expressão (ex.: '2019|2020')")
    p.add_argument("--filtro", action="append", metavar="COLUNA=VALOR",
                   help="gera extratos dos CSVs só com as linhas que atendem (repetível; "
                        "vários valores com |, ex.: SG_ENTIDADE_ENSINO=UNICAMP|USP). "
                        "Comparação sem diferenciar maiúsculas")
    p.add_argument("--modo", choices=("arquivo", "datastore"), default="arquivo",
                   help="arquivo: baixa os arquivos originais (padrão); datastore: tabelas "
                        "via API, que estão incompletas para vários anos")
    p.add_argument("--limite-pagina", type=int, default=32000,
                   help="linhas por requisição no modo datastore (padrão: %(default)s)")
    p.add_argument("--listar", action="store_true", help="só lista os recursos, sem baixar")
    p.add_argument("--colunas", action="store_true", help="com --listar, mostra as colunas")
    p.add_argument("--buscar", metavar="TERMO", help="procura conjuntos no portal e sai")
    p.add_argument("--forcar", action="store_true",
                   help="rebaixa e refaz extratos mesmo se já existirem")
    p.add_argument("--base-url", default=BASE_URL, help=argparse.SUPPRESS)
    args = p.parse_args(argv)

    filtros = {}
    for item in args.filtro or []:
        if "=" not in item:
            p.error(f"--filtro deve ser COLUNA=VALOR (recebido: {item!r})")
        col, val = item.split("=", 1)
        vals = val.split("|")
        filtros[col.strip()] = vals if len(vals) > 1 else vals[0]
    if filtros and args.formatos is not None and "csv" not in args.formatos \
            and args.modo == "arquivo":
        p.error("--filtro atua sobre os CSVs; inclua csv em --formatos")
    if args.colunas:
        args.listar = True
    return args, filtros


def main(argv=None) -> int:
    try:  # mantém mensagens e progresso na ordem certa quando a saída vai para arquivo
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:
        pass
    args, filtros = analisar_args(argv)
    cli = Ckan(args.base_url)

    if args.buscar:
        buscar(cli, args.buscar)
        return 0
    if args.modo == "datastore" and not args.listar:
        print("Atenção: várias tabelas do DataStore da CAPES estão incompletas; "
              "confira as contagens antes de usar.", file=sys.stderr)

    caminho_manifesto = args.saida / "manifesto.csv"
    manifesto = ler_manifesto(caminho_manifesto) if not args.listar else {}
    contagem = {}

    try:
        for entrada in args.datasets:
            slug = slug_de(entrada)
            try:
                pacote = cli.acao("package_show", id=slug)
            except Exception as e:
                print(f"\n[{slug}] ERRO ao ler metadados: {e}", file=sys.stderr)
                contagem["falhou"] = contagem.get("falhou", 0) + 1
                continue

            todos = pacote.get("resources", [])
            recursos = filtrar_recursos(todos, args)
            print(f"\n[{slug}] {pacote.get('title', '')}")
            print(f"  {len(recursos)} de {len(todos)} recurso(s) selecionado(s)")

            if args.listar:
                listar(cli, recursos, args.colunas)
                continue

            pasta = args.saida / slug
            pasta.mkdir(parents=True, exist_ok=True)
            with open(pasta / "_metadados_ckan.json", "w", encoding="utf-8") as f:
                json.dump(pacote, f, ensure_ascii=False, indent=2)

            usados = set()
            for rec in recursos:
                for linha in processar_recurso(cli, slug, rec, pasta, args,
                                               filtros, manifesto, usados):
                    manifesto[linha["arquivo_local"]] = linha
                    status = linha.get("status", "").split(":")[0]
                    contagem[status] = contagem.get(status, 0) + 1
                gravar_manifesto(caminho_manifesto, manifesto)
    except KeyboardInterrupt:
        print("\nInterrompido. Rode de novo para retomar.", file=sys.stderr)
        return 130

    if args.listar:
        return 0
    if filtros and args.modo == "arquivo":
        combinar_extratos(args.saida / "filtrado", filtros)
    resumo = ", ".join(f"{v} {k}" for k, v in sorted(contagem.items())) or "nada a fazer"
    print(f"\nResumo: {resumo}. Manifesto: {caminho_manifesto}")
    return 1 if contagem.get("falhou") else 0


if __name__ == "__main__":
    sys.exit(main())
