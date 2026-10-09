# Projeto Final — MO810

Este repositório usa os dados abertos da CAPES sobre **discentes da pós-graduação
*stricto sensu* no Brasil, de 2004 a 2024**, com foco no programa de Ciência da
Computação da Unicamp (IC).

Os dados brutos (~2,7 GB) **não** estão versionados. Este documento explica como
obtê-los e como gerar o recorte usado no projeto.

## O que já está no repositório

A pasta `ic_capes-anon/` traz o recorte do IC já **desidentificado** (sem nome,
documento do discente e título do trabalho). Se for usar só esse recorte, não é
preciso baixar nada.

| Arquivo                 | Conteúdo                                                                 |
|-------------------------|--------------------------------------------------------------------------|
| `ic_capes.csv`          | Discentes do programa de Ciência da Computação da Unicamp, 2004–2024, com a coluna `ARQUIVO_ORIGEM` |
| `esquema.csv`           | Colunas de cada arquivo da CAPES (o esquema muda entre os períodos)      |
| `programas_unicamp.csv` | Programas da Unicamp com "COMPUTA" no nome, por ano, e se entraram no filtro |
| `resumo.csv`            | Contagem de linhas por arquivo × grau × situação do discente             |

## Fonte dos dados

[Portal de Dados Abertos da CAPES](https://dadosabertos.capes.gov.br), licença
Creative Commons Attribution (CC-BY). São quatro conjuntos:

| Conjunto (slug no portal)                                                      | Anos      | Tamanho (CSVs) |
|--------------------------------------------------------------------------------|-----------|---------------:|
| `discentes-dos-programas-de-pos-graduacao-stricto-sensu-no-brasil-2004-a-2012` | 2004–2012 | ~700 MB |
| `discentes-da-pos-graduacao-stricto-sensu-do-brasil-2013-a-2016`               | 2013–2016 | ~530 MB |
| `discentes-da-pos-graduacao-stricto-sensu-do-brasil-2017-a-2019`               | 2017–2020 | ~640 MB |
| `2021-a-2024-discentes-da-pos-graduacao-stricto-sensu-do-brasil`               | 2021–2024 | ~700 MB |

Apesar do nome, o conjunto `...-2017-a-2019` também contém o ano de 2020.
Cada conjunto tem um CSV por ano, um XLSX com os mesmos dados e um PDF de
metadados (dicionário de variáveis).

## Requisitos

- Python 3.8 ou superior
- `requests` (obrigatório) e `tqdm` (opcional, para barra de progresso)

```bash
pip install requests tqdm
```

## Passo 1 — Baixar os dados brutos

```bash
python baixar_discentes_capes.py
```

Isso baixa os CSVs de todos os anos e os PDFs de metadados dos quatro conjuntos
para `dados/capes_discentes/`. Reserve ~3 GB de espaço em disco.

- Se o download for interrompido, basta rodar de novo: os arquivos parciais
  (`*.part`) são retomados e os já baixados são pulados.
- `--forcar` rebaixa tudo, mesmo o que já existe.
- O arquivo `dados/capes_discentes/manifesto.csv` registra, para cada arquivo,
  a URL de origem, o tamanho, o SHA-256 e a data do download.

Outras opções úteis:

```bash
# Só listar o que há em cada conjunto (sem baixar); --colunas mostra as colunas
python baixar_discentes_capes.py --listar --colunas

# Baixar só alguns anos
python baixar_discentes_capes.py --recursos "2019|2020"

# Gerar também extratos só com as linhas da Unicamp (todos os programas),
# em dados/capes_discentes/filtrado/
python baixar_discentes_capes.py --filtro SG_ENTIDADE_ENSINO=UNICAMP

# Incluir os XLSX (repetem os dados dos CSVs)
python baixar_discentes_capes.py --formatos todos
```

> **Não use `--modo datastore` para análise.** Em outubro de 2026, várias
> tabelas da API DataStore da CAPES estavam incompletas (ex.: só 3.000 linhas
> em cada ano de 2013 a 2016). O modo padrão baixa os arquivos completos e
> aplica os filtros localmente.

### Alternativa: arquivo compactado

Se você recebeu o arquivo `capes_discentes.tar.xz` (~200 MB, mesmo conteúdo de
`dados/capes_discentes/`), descompacte-o na raiz do repositório em vez de
baixar do portal:

```bash
tar -xJf capes_discentes.tar.xz
```

## Passo 2 — Gerar o recorte do IC

Com os dados brutos em `dados/capes_discentes/`:

```bash
# Versão desidentificada (a que está versionada)
python extrair_ic_capes.py dados/capes_discentes -o ic_capes-anon --desidentificar

# Versão completa, com nomes e documentos (saída padrão: ic_capes/)
python extrair_ic_capes.py dados/capes_discentes
```

O filtro seleciona as linhas com sigla da IES `UNICAMP` e nome de programa igual
a `CIENCIA DA COMPUTACAO` ou `COMPUTACAO` (sem diferenciar acentos e
maiúsculas). Para mudar os programas, use
`--programas "NOME 1;NOME 2"`; o arquivo `programas_unicamp.csv` ajuda a
conferir os nomes disponíveis.

## Estrutura após o download

```
dados/capes_discentes/                       # não versionado
├── manifesto.csv
├── discentes-dos-programas-de-...-2004-a-2012/
│   ├── br-capes-colsucup-discentes-<ano>-2021-03-01.csv
│   ├── metadados_discentes_2004a2012.pdf
│   └── _metadados_ckan.json
├── discentes-da-pos-graduacao-...-2013-a-2016/
├── discentes-da-pos-graduacao-...-2017-a-2019/
├── 2021-a-2024-discentes-da-pos-graduacao-.../
└── filtrado/                                # só com --filtro
ic_capes/                                    # não versionado (dados pessoais)
ic_capes-anon/                               # versionado
```

## Observações sobre os dados

- **Dados pessoais.** Os CSVs da CAPES trazem nome e número de documento dos
  discentes. Por isso `dados/capes_discentes/`, `ic_capes/` e
  `capes_discentes.tar.xz` estão no `.gitignore`. Versione apenas saídas geradas
  com `--desidentificar`.
- **Formato.** Os CSVs originais usam `;` como separador e codificação
  Windows-1252 (cp1252). Os arquivos gerados pelos scripts usam `,` e UTF-8.
- **Esquema variável.** Os arquivos de 2004–2012 têm 31 colunas; os de 2013 em
  diante, 37, com nomes diferentes para algumas variáveis (ex.:
  `NM_NIVEL_PROGRAMA` → `NM_GRAU_PROGRAMA`). O recorte combinado contém a
  união das colunas, com campos vazios onde a coluna não existe no período.
  Consulte `esquema.csv` e os PDFs de metadados.
- **Datas.** Em 2004–2012, matrícula e situação vêm como ano e mês separados
  (`AN_MATRICULA_DISCENTE`, `ME_MATRICULA_DISCENTE` etc.). De 2013 em diante,
  vêm como data completa (`DT_MATRICULA_DISCENTE`, `DT_SITUACAO_DISCENTE`) no
  formato `20SEP2019:00:00:00`.
