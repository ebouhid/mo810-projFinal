#!/usr/bin/env python3
"""
Extrai, dos CSVs de discentes da CAPES (2004-2024) já baixados, só as linhas
da Unicamp nos programas de Computação do IC. O resultado é pequeno o bastante
para anexar na conversa.

Uso:
    python extrair_ic_capes.py dados/capes_discentes
    python extrair_ic_capes.py dados/capes_discentes --desidentificar
    python extrair_ic_capes.py dados/capes_discentes --programas "CIENCIA DA COMPUTACAO;COMPUTACAO"

Saída (padrão: ./ic_capes):
    ic_capes.csv            linhas filtradas de todos os anos (UTF-8), com ARQUIVO_ORIGEM
    esquema.csv             colunas de cada arquivo, para ver o que muda entre períodos
    programas_unicamp.csv   programas da Unicamp com "COMPUTA" no nome, por arquivo,
                            com contagem e se entraram no filtro
    resumo.csv              linhas por arquivo x grau x situação do discente

O filtro compara nomes sem acento e sem diferenciar maiúsculas:
sigla da IES == UNICAMP e nome do programa igual a um dos --programas.
--desidentificar remove nome e documento do discente e título do trabalho
(mantém ID_PESSOA e orientador).
"""
from __future__ import annotations

import argparse
import csv
import sys
import unicodedata
from collections import Counter
from pathlib import Path

csv.field_size_limit(2**31 - 1)
CODIFICACOES = ("utf-8-sig", "cp1252", "latin-1")
REMOVER_AO_DESIDENTIFICAR = ("NM_DISCENTE", "NR_DOCUMENTO_DISCENTE",
                             "TP_DOCUMENTO_DISCENTE", "NM_TESE_DISSERTACAO")


def normalizar(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.upper().split())


def achar_coluna(cab: list[str], exatas: tuple, contem: tuple = ()) -> int | None:
    norm = [normalizar(c) for c in cab]
    for nome in exatas:
        if nome in norm:
            return norm.index(nome)
    for i, c in enumerate(norm):
        if all(p in c for p in contem) and contem:
            return i
    return None


def detectar_codificacao(caminho: Path) -> str:
    amostra = caminho.open("rb").read(1 << 20)
    try:
        amostra.decode("utf-8")
        return "utf-8-sig"
    except UnicodeDecodeError as e:
        if e.start >= len(amostra) - 3:
            return "utf-8-sig"
    try:
        amostra.decode("cp1252")
        return "cp1252"
    except UnicodeDecodeError:
        return "latin-1"


def ler_arquivo(caminho: Path, programas: set[str], esquema, progs, linhas_ic):
    inicio = CODIFICACOES.index(detectar_codificacao(caminho))
    for codif in CODIFICACOES[inicio:]:
        # cada tentativa acumula à parte: se a decodificação falhar no meio do
        # arquivo, o que foi lido até ali é descartado em vez de duplicado
        esq, cont, linhas = [], Counter(), []
        try:
            resultado = _ler(caminho, codif, programas, esq, cont, linhas)
        except UnicodeDecodeError:
            continue
        esquema.extend(esq)
        progs.update(cont)
        linhas_ic.extend(linhas)
        return resultado
    raise RuntimeError("não consegui decodificar o arquivo")


def _ler(caminho, codif, programas, esquema, progs, linhas_ic):
    mantidas_antes = len(linhas_ic)
    with caminho.open(newline="", encoding=codif) as f:
        primeira = f.readline()
        sep = ";" if primeira.count(";") >= primeira.count(",") else ","
        cab = [c.strip() for c in next(csv.reader([primeira], delimiter=sep))]
        esquema.append({"arquivo": caminho.name, "codificacao": codif,
                        "n_colunas": len(cab), "colunas": "|".join(cab)})
        i_ies = achar_coluna(cab, ("SG_ENTIDADE_ENSINO", "SG_IES"), ("SG_", "ENTIDADE"))
        i_prog = achar_coluna(cab, ("NM_PROGRAMA_IES", "NM_PROGRAMA"), ("NM_PROGRAMA",))
        if i_ies is None or i_prog is None:
            print(f"  ! {caminho.name}: não achei coluna de IES ou de programa; "
                  f"veja esquema.csv", file=sys.stderr)
            return 0, 0
        lidas = 0
        for linha in csv.reader(f, delimiter=sep):
            lidas += 1
            if len(linha) <= max(i_ies, i_prog):
                continue
            if "UNICAMP" not in linha[i_ies].upper() or normalizar(linha[i_ies]) != "UNICAMP":
                continue
            prog = normalizar(linha[i_prog])
            if "COMPUTA" in prog:
                progs[(caminho.name, prog, prog in programas)] += 1
            if prog in programas:
                reg = dict(zip(cab, linha))
                reg["ARQUIVO_ORIGEM"] = caminho.name
                linhas_ic.append(reg)
    return lidas, len(linhas_ic) - mantidas_antes


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("pasta", type=Path, help="pasta com os CSVs baixados da CAPES")
    p.add_argument("-o", "--saida", type=Path, default=Path("ic_capes"))
    p.add_argument("--programas", default="CIENCIA DA COMPUTACAO;COMPUTACAO",
                   help="nomes exatos de programa, separados por ';' (padrão: %(default)s)")
    p.add_argument("--desidentificar", action="store_true",
                   help="remove nome/documento do discente e título do trabalho")
    args = p.parse_args(argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:
        pass

    programas = {normalizar(x) for x in args.programas.split(";") if x.strip()}
    arquivos = sorted(c for c in args.pasta.rglob("*.csv")
                      if "filtrado" not in c.parts and c.name != "manifesto.csv")
    if not arquivos:
        print(f"nenhum CSV encontrado em {args.pasta}", file=sys.stderr)
        return 1

    esquema, progs, linhas_ic = [], Counter(), []
    for arq in arquivos:
        print(f"- {arq.name}")
        try:
            lidas, mantidas = ler_arquivo(arq, programas, esquema, progs, linhas_ic)
        except Exception as e:
            print(f"  ! erro: {e}", file=sys.stderr)
            continue
        print(f"  {mantidas:,} de {lidas:,} linhas mantidas")
        if lidas and not mantidas:
            print("  aviso: nada passou no filtro; veja programas_unicamp.csv")

    args.saida.mkdir(parents=True, exist_ok=True)
    colunas = []
    for reg in linhas_ic:
        for c in reg:
            if c not in colunas:
                colunas.append(c)
    if args.desidentificar:
        colunas = [c for c in colunas if normalizar(c) not in REMOVER_AO_DESIDENTIFICAR]
    colunas = ["ARQUIVO_ORIGEM"] + [c for c in colunas if c != "ARQUIVO_ORIGEM"]

    with (args.saida / "ic_capes.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colunas, extrasaction="ignore", restval="")
        w.writeheader()
        w.writerows(linhas_ic)

    with (args.saida / "esquema.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["arquivo", "codificacao", "n_colunas", "colunas"])
        w.writeheader()
        w.writerows(esquema)

    with (args.saida / "programas_unicamp.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["arquivo", "programa", "no_filtro", "linhas"])
        for (arq, prog, dentro), n in sorted(progs.items()):
            w.writerow([arq, prog, "sim" if dentro else "não", n])

    def valor(reg, *partes):
        for c, v in reg.items():
            n = normalizar(c)
            if all(x in n for x in partes) and not n.startswith(("DT_", "QT_", "CD_")):
                return v
        return "?"

    resumo = Counter((r["ARQUIVO_ORIGEM"], valor(r, "GRAU", "DISCENTE"),
                      valor(r, "SITUACAO", "DISCENTE")) for r in linhas_ic)
    with (args.saida / "resumo.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["arquivo", "grau", "situacao", "linhas"])
        for (arq, grau, sit), n in sorted(resumo.items()):
            w.writerow([arq, grau, sit, n])

    print(f"\n{len(linhas_ic):,} linhas no total -> {args.saida}/ic_capes.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
