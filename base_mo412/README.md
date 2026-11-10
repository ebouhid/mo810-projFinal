# Entradas legadas do MO412

Cópia, **sem alteração**, de arquivos do projeto anterior (MO412), usados como entrada pelos
scripts de `marc/`. A origem é `ebouhid/mo412-projetofinal`, commit `aa215b4`, um fork de
[gondimjoaom/mo412-projetofinal](https://github.com/gondimjoaom/mo412-projetofinal). Os caminhos
abaixo repetem os do repositório de origem.

| arquivo | conteúdo | usado por |
|---|---|---|
| `csvs/genero2.csv` | gênero anotado manualmente no MO412, por ORCID (`orcid`, `nome`, `genero`) | `marc/genero.py --genero` |
| `csvs/links{2006..2024}.csv` | links das defesas extraídos da planilha antiga (`tipo`, `url`) | `marc/gerar_links.py --comparar`, `marc/validar.py --links-antigos` |
| `final_defesas_2006a2024.csv` | base antiga de bancas: ORCID, nome, filiação e país de orientador e avaliadores, por URL da defesa | `marc/genero.py --base-antiga`, `marc/validar.py --antiga` |

Não há nome de aluno nem título nesses arquivos, mas a `url` leva ao registro público da defesa,
onde eles aparecem. Não edite estes arquivos: correções vão para `marc/`.
