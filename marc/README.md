# Coleta MARC das defesas do IC/Unicamp (2006–2025)

Base para o projeto de MO810 (Feminismo de Dados). Esta coleta substitui o caminho antigo
(`get_links.py` → `crawler2.py` com Selenium → scripts de ORCID → `junta_planilhas.ipynb`), que
guardava só os ORCIDs das linhas MARC 700. Aqui o registro MARC **completo** de cada defesa vem
de um endpoint JSON do repositório da Unicamp (Sophia Biblioteca Web). Com isso temos:

- nome, papel (Orientador, Coorientador, Avaliador), ORCID e Lattes de **todas** as pessoas da
  banca, inclusive quem não tem ORCID;
- data da defesa (943), nível (502), agência de fomento (536), programa (710), unidade (852),
  handle (856), área (940) e titulação (941), entre outros.

Os CSVs antigos (`csvs/*`, `final_defesas_2006a2024.csv`) **não** são alterados. Eles servem de
referência para a validação.

## Fluxo

Todos os comandos rodam a partir da raiz do repositório.

```bash
# 1. links: uma lista por aba de ano da planilha do IC
python marc/gerar_links.py \
    --planilha "marc/Histórico de Defesas de Mestrado e Doutorado - 2026.xlsx" \
    --inicio 2006 --fim 2025 --saida marc/links --comparar csvs

# 2. coleta: um JSON bruto por registro (retomável: pula os já baixados)
python marc/coletar_marc.py marc/links/links*.csv --saida marc/marc_raw --curl marc/curl.txt --pausa 1.5
#    ids que só existiam na base antiga (só para a validação)
python marc/coletar_marc.py marc/links/antigos_substituidos.csv --saida marc/marc_raw/antigos \
    --curl marc/curl.txt --pausa 1.5

# 3. parsing: tabela completa (local) e desidentificada (versionada)
python marc/parsear_marc.py marc/marc_raw --links marc/links --saida marc/tabelas
python marc/parsear_marc.py marc/marc_raw --links marc/links --saida marc/tabelas_pub --desidentificar

# 4. gênero: acrescenta pessoa_id, genero e genero_fonte e lista quem falta anotar
python marc/genero.py --tabelas marc/tabelas marc/tabelas_pub

# 5. validação contra a base antiga -> marc/relatorio_validacao.md
python marc/validar.py
```

Requer `pandas`, `openpyxl` e `requests`. O Playwright só é necessário se o `coletar_marc.py`
rodar **sem** `--curl`, que não é o modo usado aqui.

**Seja gentil com o servidor.** É um serviço público da universidade: não use `--pausa` abaixo
de 1.0. A coleta completa (~1.100 registros) leva cerca de 30 minutos com `--pausa 1.5`.

## Como obter o `curl.txt`

O endpoint `POST https://repositorio.unicamp.br/marc/obterRegistroMARCTags` (corpo
`{"codigoRegistro": <id>}`) exige o cookie de validação anti-robô `SBW.REQUEST.VALIDATION`, o cookie
`__RequestVerificationToken` e o cabeçalho `requestverificationtoken` (antiforgery do ASP.NET). Para
obtê-los:

1. No navegador, abra um registro qualquer, por exemplo
   `https://repositorio.unicamp.br/acervo/detalhe/1266276`. Se aparecer a validação anti-robô,
   resolva-a.
2. Abra o DevTools (F12) na aba **Network** (Rede).
3. Na página, clique no botão **MARC**.
4. Na lista de requisições, clique com o botão direito em `obterRegistroMARCTags` e escolha
   **Copy → Copy as cURL (bash)**.
5. Cole o conteúdo em `marc/curl.txt`.

O `coletar_marc.py` lê do cURL os cabeçalhos (`-H`) e os cookies (`-b`).

**Quando o token expira**, o script detecta sozinho. Se um pedido falha, ele pede de novo um id
que já funcionou (`--controle`, padrão 1266276):

- se o controle também falhar, o token expirou e o script para. Copie um cURL novo e rode o
  mesmo comando de novo; os registros já baixados são pulados;
- se o controle funcionar, a falha é daquele registro. O status vai para `marc_raw/_log.csv`, o
  corpo da resposta vai para `marc_raw/_falhas/<id>.txt` e a coleta segue.

Respostas que não seguem o formato esperado (string HTML com uma tag MARC por linha, separadas
por `<br/>`) são registradas como `formato-inesperado` e não são salvas.

## Arquivos

| arquivo | conteúdo | dados pessoais de estudantes? | versionado? |
|---|---|---|---|
| `curl.txt` | cookies e tokens da sua sessão | (credenciais) | **não** |
| `Histórico de Defesas ... - 2026.xlsx` | planilha do IC com aba 2025 | sim (nome do aluno, título) | **não** |
| `marc_raw/<id>.json`, `marc_raw/antigos/` | MARC bruto | sim (campo 100, título, resumo) | **não** |
| `marc_raw/_log.csv`, `marc_raw/_falhas/` | status de cada pedido | não | não (fica junto do bruto) |
| `tabelas/defesas.csv` | uma linha por defesa, completa | sim: `autor_nome`, `autor_ano_nasc`, `autor_orcid`, `autor_lattes`, `titulo` | **não** |
| `tabelas/participacoes.csv` | uma linha por (defesa, pessoa, papel) | não (só docentes/avaliadores) | não (cópia local) |
| `tabelas_pub/defesas.csv` | igual, sem as colunas do autor e o título | não | sim |
| `tabelas_pub/participacoes.csv` | igual à de `tabelas/` | não | sim |
| `links/links{ano}.csv` | tipo, url, código, ano e célula da planilha | não | sim |
| `links/antigos_substituidos.csv` | ids que só existem na base antiga | não | sim |
| `a_anotar_genero.csv` | pessoas sem gênero anotado | não (docentes/avaliadores) | sim |
| `relatorio_validacao.md` | resultado do `validar.py` | não (gerado só de `tabelas_pub/`) | sim |

`resposta.json`, na raiz, é um exemplo de resposta do endpoint com os dados do autor, e também
está no `.gitignore`.

Atenção: `codigo`, `handle` e `doi` levam ao registro público no repositório, onde estão o nome do
aluno e o título. Já era assim com as URLs da base antiga. Leve isso em conta antes de
publicar análises que cruzem com outras fontes.

## Tabelas

**`defesas.csv`**: `codigo` (id do registro), `ano_planilha` (aba de origem), `tipo` (cabeçalho da
planilha: MESTRADO, DOUTORADO ou MESTRADO PROFISSIONAL), `outras_ocorrencias_planilha` (id
repetido em outra aba), `nivel` (a partir da nota 502), `nota_tese` (502), `data_defesa` (943, `aaaa-mm-dd`),
`data_defesa_txt` (texto original da 943), `agencia_fomento` (536, várias separadas por ` | `),
`programa` (710), `unidade` (852), `handle` (856 "Texto completo"), `doi` (856 "DOI", o DOI da
tese), `dados_pesquisa` (856 "Dados de pesquisa", DOIs de conjuntos de dados ou artigos, separados
por ` | `), `area_concentracao` (940), `titulacao` (941),
`tipo_obra` (990), `notas_500` (notas "Orientador(es): ..."), `banca_942` (lista da banca),
`n_700` e `n_banca_942`. Os números de processo do 536 (`|d`) são descartados.

**`participacoes.csv`**: `codigo`, `ordem` (posição no MARC), `papel` (700 `|e`, sem o ponto final;
`?` quando falta), `nome` (700 `|a`, no formato "Sobrenome, Nome", sem vírgula ou ponto final),
`ano_nasc` (700 `|d`), `orcid` (`0000-0000-0000-000X`), `lattes` (só os dígitos; leia como texto,
porque há zeros à esquerda), `pessoa_id`, `genero` e `genero_fonte`.

## Gênero

O `genero.py` leva o gênero do `csvs/genero2.csv` (anotação manual feita no MO412) para
`participacoes.csv`. Ele **não infere gênero pelo nome**.

- `pessoa_id`: participações com o mesmo ORCID ou o mesmo Lattes são a mesma pessoa
  (`orcid:...` ou `lattes:...`). Quem não tem ORCID nem Lattes recebe `nome:<nome normalizado>`.
- `genero_fonte = orcid`: o ORCID da participação está no `genero2.csv`.
- `genero_fonte = lattes`: a pessoa está ligada, pelo Lattes, a um ORCID do `genero2.csv`.
  Nesta base isso nunca acontece, porque quem tem Lattes em algum registro tem sempre o mesmo
  ORCID. A regra fica para coletas futuras.
- A ligação só pelo nome nunca atribui gênero.

O `a_anotar_genero.csv` tem uma linha por pessoa ainda sem gênero, ordenada pelo número de
participações. Colunas:

- `motivo`: "sem ORCID" ou "ORCID fora do genero2";
- `dica_mesmo_nome`: alguém já anotado com o mesmo nome normalizado;
- `dica_base_antiga`: o ORCID que a base antiga tinha na mesma posição da banca, quando o
  registro atual não tem mais ORCID;
- `genero`: vem vazia, para o grupo preencher.

As dicas servem para o grupo conferir, não são atribuições. O `pessoa_id` permite levar a
anotação de volta para `participacoes.csv`.

## Particularidades dos dados (detalhes em `relatorio_validacao.md`)

- O campo 942 (“Banca:”) lista o primeiro orientador e os avaliadores, **mas não o
  coorientador nem o segundo orientador** (dupla orientação ou cotutela). Por isso
  `n_700 ≠ n_banca_942` em quase todas as defesas com coorientação.
- Há papéis fora do padrão: 6 linhas 700 sem `|e` (`papel = ?`), 1 `Presidente` e 1
  `Organizador`. O papel não é inferido. Três defesas não têm nenhum 700 `Orientador`.
- O repositório **removeu o ORCID** de algumas participações depois da coleta antiga (por
  exemplo, Fabio Verdi e David Menotti). Nesses casos, a base antiga é a única ligação por
  identificador (veja `dica_base_antiga`).
- Dois links da planilha apontavam para obras que **não são do IC**:
  - aba 2016, D60 → 979994, um TCC de Geociências de um homônimo do aluno;
  - aba 2019, D8 → 1060991, uma tese da Faculdade de Educação; a busca casou nomes de campos
    diferentes.

  Os registros certos foram achados por busca manual: **979626** e **1089706**. Os dois
  conferem com aluno, orientador, data e nível da planilha e estão mapeados em
  `marc/links/ids_manuais.csv`. A base antiga do MO412 incluía as bancas erradas.
- Outros 14 registros têm 502 ou 852 com grafia variante, ou o 852 de outra unidade (por
  exemplo, o IMECC em 2024–25), mas são do IC.
- 3 defesas estão sem data (943 ausente, vazio ou com erro de digitação).
- A aba 2010 da planilha não tem o cabeçalho MESTRADO, então as defesas de mestrado de 2010
  ficam sem `tipo`. Use `nivel`, que vem da nota 502.
- O id 434549 aparece em duas abas (2008 MESTRADO e 2013 DOUTORADO). Em `defesas.csv` fica a
  primeira ocorrência, e a outra vai para `outras_ocorrencias_planilha`.
- 2010, célula D48: o link é um handle do DSpace antigo (`jspui/handle/REPOSIP/275621`), que hoje
  responde 404. Além disso, ele apontava para uma tese da FEEC de 2001, e a planilha traz ao lado
  a anotação "nao achei". O registro certo (917890) foi achado por busca manual e mapeado em
  `marc/links/ids_manuais.csv` (colunas `url,codigo,fonte`), que o `gerar_links.py` aplica. Com
  `codigo` preenchido, o link passa a apontar para esse registro. Com `codigo` vazio, o link é
  anulado e a linha fica fora da base. Em qualquer caso, o `parsear_marc.py` só considera os
  registros ligados à planilha: um JSON baixado e não ligado (como 979994) é ignorado.
  Ele está catalogado com data de defesa 20-12-**2013**, mas a planilha diz 20-12-2010, com a
  numeração geral da secretaria dentro de 2010. Para corrigir links de outros casos assim,
  acrescente linhas a esse arquivo e rode de novo o `gerar_links.py` e a coleta.
- A planilha nova corrigiu quatro links da antiga (2021, 2022, 2023 e 2024). Os registros
  errados (1242940 do IFGW e 1089524 da FOP, entre outros) foram baixados à parte em
  `marc_raw/antigos/` só para a validação.
