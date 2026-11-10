# Relatório de validação: coleta MARC vs. base antiga

Gerado por `marc/validar.py` a partir de `marc/tabelas_pub/` (desidentificada) e `base_mo412/final_defesas_2006a2024.csv`. Base nova: 1099 defesas, 4375 participações (linhas 700).

## 1. Coleta

- Links na planilha (2006–2025): **1100**; ids únicos: **1099**.
- Registros baixados com status 200 e parseados: **1099**.
- Falhas: **0**; ids nunca pedidos: **0**.
- Links sem id de registro ou anulados em `links/ids_manuais.csv` (não entram na base): **0**.


## 2. Links: planilha nova vs. base_mo412/csvs/links{ano}.csv antigos

| ano | antigo | novo | saíram | entraram |
|---|---|---|---|---|
| 2006 | 71 | 71 |  |  |
| 2007 | 41 | 41 |  |  |
| 2008 | 36 | 36 |  |  |
| 2009 | 47 | 47 |  |  |
| 2010 | 59 | 59 |  |  |
| 2011 | 52 | 52 |  |  |
| 2012 | 55 | 55 |  |  |
| 2013 | 58 | 58 |  |  |
| 2014 | 44 | 44 |  |  |
| 2015 | 61 | 61 |  |  |
| 2016 | 61 | 61 |  |  |
| 2017 | 57 | 57 |  |  |
| 2018 | 54 | 54 |  |  |
| 2019 | 50 | 50 |  |  |
| 2020 | 69 | 69 |  |  |
| 2021 | 58 | 58 | 1242940 | 1162360 |
| 2022 | 55 | 55 | https://www.repositorio.unicamp.br/Resultado/Listar?guid=1706887206525 | 1254557 |
| 2023 | 48 | 48 | 480769 | 1376657 |
| 2024 | 55 | 55 | 1089524 | 1384867, 1456567 |
| 2025 | - | 69 |  |  |


## 3. ORCIDs: base antiga vs. nova (mesmo id)

- Defesas da base antiga (`final_defesas_2006a2024.csv`): 1028; com o mesmo id na nova: **1024**; ausentes na nova: 4.
  Ausentes (ids trocados na planilha nova ou corrigidos/anulados em `ids_manuais.csv`): 979994 (2016), 1060991 (2019), 480769 (2023), 1089524 (2024)
- Divergências de orientador: **3**; de conjunto de avaliadores: **15**.
- Orientador antes "sem orcid" e agora com ORCID: 0 (não conta como divergência).
- Critério: ORCIDs normalizados (`0000-0000-0000-000X`). Avaliadores divergem se um ORCID antigo não aparece entre os `Avaliador` novos, ou se há mais ORCIDs novos do que "sem orcid" antigos.
- Nos casos "ausente", a pessoa continua no registro, na mesma posição, mas **sem ORCID**: o registro do repositório foi editado depois da coleta antiga. Nesses casos, o ORCID da base antiga é a única ligação por identificador para essas participações.

| codigo | ano | campo | antigo | novo | obs |
|---|---|---|---|---|---|
| 403868 | 2007 | avaliadores | 0000-0001-5015-2131, 0000-0003-1574-0362 | 0000-0001-5015-2131 | 0000-0003-1574-0362 ausente; na mesma posição a nova tem Jr, Roberto Marcondes Cesar (sem ORCID) |
| 782510 | 2010 | orientador | 0000-0002-9539-6874 | (sem ORCID) | ORCID antigo está na nova com papel '?' (Rigo, Sandro) |
| 895751 | 2012 | avaliadores | 0000-0002-5455-8910, 0000-0003-2046-602X | 0000-0003-2046-602X | 0000-0002-5455-8910 ausente; na mesma posição a nova tem Verdi, Fabio Luciano (sem ORCID) |
| 869220 | 2012 | avaliadores | 0000-0001-8318-1780, 0000-0002-1756-4852, 0000-0002-1941-6036, 0000-0003-2430-2030 | 0000-0001-8318-1780, 0000-0002-1756-4852, 0000-0002-1941-6036 | 0000-0003-2430-2030 ausente; na mesma posição a nova tem Menotti, David (sem ORCID) |
| 932501 | 2014 | avaliadores | 0000-0001-8522-2056, 0000-0003-2430-2030 | 0000-0001-8522-2056 | 0000-0003-2430-2030 ausente; na mesma posição a nova tem Menotti, David (sem ORCID) |
| 959703 | 2015 | avaliadores | 0000-0002-1953-9132, 0000-0002-6023-5982 | 0000-0002-6023-5982 | 0000-0002-1953-9132 ausente; na mesma posição a nova tem Guidoni, Daniel Ludovico (sem ORCID) |
| 959789 | 2015 | avaliadores | 0000-0001-8956-8660, 0000-0002-5455-8910, 0000-0002-6023-5982, 0000-0003-3109-4305 | 0000-0001-8956-8660, 0000-0002-6023-5982, 0000-0003-3109-4305 | 0000-0002-5455-8910 ausente; na mesma posição a nova tem Verdi, Fabio Luciano (sem ORCID) |
| 961780 | 2015 | avaliadores | 0000-0001-5015-2131, 0000-0002-0189-8540, 0000-0002-9707-799X, 0000-0003-2059-9463 | 0000-0001-5015-2131, 0000-0002-9707-799X, 0000-0003-2059-9463 | 0000-0002-0189-8540 ausente; na mesma posição a nova tem Silva, Alexandre Gonçalves da (sem ORCID) |
| 973537 | 2016 | avaliadores | 0000-0002-1180-2637, 0000-0002-5455-8910 | 0000-0002-1180-2637 | 0000-0002-5455-8910 ausente; na mesma posição a nova tem Verdi, Fabio Luciano (sem ORCID) |
| 983291 | 2016 | avaliadores | 0000-0001-6030-2682, 0000-0002-3948-305X, 0000-0002-8972-080X, 0000-0003-3910-8804 | 0000-0001-6030-2682, 0000-0002-3948-305X, 0000-0002-8972-080X | 0000-0003-3910-8804 ausente; na mesma posição a nova tem Rangel, Maria do Socorro Nogueira (sem ORCID) |
| 1010167 | 2018 | avaliadores | 0000-0001-6305-9059, 0000-0002-1953-9132, 0000-0003-1495-5935, 0000-0003-2483-6382 | 0000-0001-6305-9059, 0000-0003-1495-5935, 0000-0003-2483-6382 | 0000-0002-1953-9132 ausente; na mesma posição a nova tem Guidoni, Daniel Ludovico (sem ORCID) |
| 1010003 | 2018 | avaliadores | 0000-0001-5378-4732, 0000-0002-5455-8910, 0000-0003-2046-602X, 0000-0003-3109-4305 | 0000-0001-5378-4732, 0000-0003-2046-602X, 0000-0003-3109-4305 | 0000-0002-5455-8910 ausente; na mesma posição a nova tem Verdi, Fabio Luciano (sem ORCID) |
| 1246260 | 2022 | avaliadores | 0000-0001-8597-4987, 0000-0002-2961-4044, 0000-0003-2440-0247, 0000-0003-3765-8300 | 0000-0001-8597-4987, 0000-0002-2961-4044, 0000-0003-3765-8300 | 0000-0003-2440-0247 ausente; na mesma posição a nova tem Chávez, Guillermo Cámara (sem ORCID) |
| 1254355 | 2022 | avaliadores | 0000-0002-1095-6714, 0000-0002-5455-8910, 0000-0002-6023-5982, 0000-0002-8603-699X | 0000-0002-1095-6714, 0000-0002-6023-5982, 0000-0002-8603-699X | 0000-0002-5455-8910 ausente; na mesma posição a nova tem Verdi, Fabio Luciano (sem ORCID) |
| 1376019 | 2023 | orientador | 0000-0003-2046-602X | (sem ORCID) | ORCID antigo está na nova com papel 'Avaliador' (Fonseca, Nelson Luis Saldanha da) |
| 1397017 | 2024 | avaliadores | 0000-0002-3754-9115, 0000-0003-2430-2030 | 0000-0002-3754-9115 | 0000-0003-2430-2030 ausente; na mesma posição a nova tem Menotti, David (sem ORCID) |
| 1409397 | 2024 | orientador | 0000-0003-0499-2564 | (sem ORCID) | ORCID antigo está na nova com papel 'Organizador' (Raimundo, Marcos Medeiros) |
| 1397455 | 2024 | avaliadores | 0000-0002-5455-8910, 0000-0002-8603-699X, 0000-0002-9539-6874, 0000-0003-0524-3274 | 0000-0002-8603-699X, 0000-0002-9539-6874, 0000-0003-0524-3274 | 0000-0002-5455-8910 ausente; na mesma posição a nova tem Verdi, Fabio Luciano (sem ORCID) |


## 4. Participações "sem orcid" da base antiga que agora têm nome

| faixa | "sem orcid" antigos | agora com nome | % com nome | dos quais com ORCID | com Lattes | não alinháveis | ausentes na nova |
|---|---|---|---|---|---|---|---|
| 2006–12 | 366 | 366 | 100.0 | 19 | 164 | 0 | 0 |
| 2013–18 | 190 | 190 | 100.0 | 16 | 53 | 0 | 0 |
| 2019–24 | 102 | 99 | 97.1 | 22 | 45 | 0 | 3 |
| **total** | 658 | 655 | 99.5 | 57 | 262 | 0 | 3 |


Conferência do alinhamento por posição (participações que já tinham ORCID na base antiga): 3037 com o mesmo ORCID na posição correspondente, 15 diferentes.
"Não alinhável": o nº de avaliadores difere entre as bases, então não dá para saber qual pessoa nova corresponde ao "sem orcid". "Agora com ORCID": o registro foi atualizado no repositório depois da coleta antiga.


## 5. Defesas com nº de linhas 700 diferente do nº de nomes no 942

- Total: **373** de 1099 defesas.
  - coorientador(es) não entram no 942: 358
  - 2º orientador (e coorientadores) não entram no 942: 7
  - coorientador/2º orientador + 700 sem papel (|e) não entram no 942: 6
  - 700 com papel incomum (Presidente/Organizador) não entra no 942: 2

Nos registros conferidos, o campo 942 ("Banca:") lista o (primeiro) orientador e os avaliadores, mas **nunca o coorientador nem o segundo orientador** (dupla orientação/cotutela). Diferenças explicadas por isso não indicam erro.

### Não explicadas

_(nenhum)_

### Explicadas por coorientador ou 2º orientador (só os ids)

1014614, 1014622, 1022097, 1031433, 1034706, 1035934, 1045562, 1050562, 1052146, 1060175, 1060709, 1061736, 1062749, 1062788, 1062910, 1064125, 1079656, 1079882, 1080338, 1080384, 1081295, 1081374, 1081804, 1082810, 1082977, 1089548, 1089611, 1089706, 1090831, 1091134, 1091235, 1091333, 1091949, 1095682, 1096114, 1097898, 1121198, 1126430, 1126478, 1126948, 1127094, 1127108, 1128679, 1128803, 1128918, 1129083, 1129107, 1129149, 1129256, 1129334, 1129341, 1148929, 1149064, 1149200, 1157234, 1157496, 1157501, 1157515, 1157604, 1157685, 1157713, 1157788, 1158115, 1161410, 1161434, 1161648, 1161700, 1161715, 1161854, 1162360, 1164221, 1164238, 1164514, 1164542, 1164703, 1165307, 1165392, 1165864, 1166113, 1166371, 1166600, 1167318, 1170196, 1170202, 1170400, 1231958, 1235753, 1236073, 1236423, 1237384, 1239069, 1241300, 1241314, 1241978, 1242638, 1242931, 1244851, 1247973, 1248397, 1249064, 1249078, 1254071, 1254351, 1254557, 1254700, 1258784, 1259169, 1259671, 1260085, 1260802, 1267507, 1274358, 1297927, 1313341, 1338842, 1341471, 1342249, 1342942, 1346037, 1346774, 1347215, 1347602, 1362019, 1362654, 1363183, 1371284, 1371294, 1371375, 1371384, 1371723, 1371766, 1371803, 1372592, 1374170, 1374643, 1374913, 1376657, 1378810, 1379182, 1380388, 1384107, 1384597, 1384752, 1384867, 1384992, 1389654, 1390745, 1394128, 1394578, 1394645, 1394730, 1394764, 1395407, 1397795, 1398630, 1406201, 1408046, 1409397, 1409513, 1410421, 1411984, 1412466, 1436248, 1455804, 1456019, 1456218, 1456431, 1456436, 1456655, 1456842, 1456870, 1456876, 1490236, 1498645, 1498825, 1498859, 1498995, 1499023, 1499027, 1499435, 1499436, 1499777, 1501090, 1501685, 1506246, 1506609, 1507851, 1507897, 1508764, 1508781, 1508794, 1509112, 1509177, 1509319, 1509363, 1519497, 1519548, 1521322, 1521398, 1522520, 1522768, 1526465, 1527774, 1529515, 1529628, 1531915, 1540639, 1541418, 1544947, 1547619, 364410, 372953, 372982, 373192, 377504, 378058, 378324, 385673, 385706, 385776, 397843, 398426, 398427, 399410, 399466, 399489, 399615, 403718, 403868, 408757, 409260, 410052, 410063, 420752, 429546, 430019, 434428, 444356, 444561, 444926, 445476, 446556, 467483, 477130, 479696, 771256, 771269, 772853, 774079, 776458, 777601, 779213, 779398, 782497, 782510, 782519, 787681, 795402, 798142, 798651, 803009, 818405, 836668, 837152, 838912, 845811, 854836, 862508, 867041, 898838, 900635, 900666, 901718, 902622, 903641, 904617, 906006, 909776, 910355, 911592, 911619, 912865, 913827, 914760, 914939, 918032, 918754, 918763, 918924, 920397, 926523, 926578, 926582, 926600, 927569, 928470, 928475, 931099, 931530, 931956, 931972, 932013, 932506, 932513, 934630, 935835, 935853, 937441, 944925, 945092, 945171, 945944, 947717, 949473, 950343, 950532, 951342, 951350, 951382, 953970, 959709, 959748, 959777, 959789, 961153, 962103, 965252, 970857, 971449, 971818, 971900, 972970, 973034, 973327, 974200, 974392, 974502, 974575, 974962, 975456, 976389, 977097, 978685, 978688, 978692, 978836, 978844, 979031, 979352, 979360, 979626, 979871, 979996, 980786, 983916, 983950, 984216, 984319, 984498, 985165, 986043, 986670, 987504, 988452, 988854, 989419, 989599, 989942, 990899, 991387, 991617, 991730, 994808


## 6. Registros cuja nota 502 ou unidade 852 não é do Instituto de Computação

- Na base nova: **14**. Por classificação:
  - 852 de outra unidade; 502 e 710 do IC (catalogação): 10
  - 502 com grafia variante/sem a unidade; 852 do IC (catalogação): 4

| codigo | ano_planilha | classificacao | nota_tese | unidade | programa | tipo_obra |
|---|---|---|---|---|---|---|
| 437602 | 2009 | 502 com grafia variante/sem a unidade; 852 do IC (catalogação) | Tese (doutorado) - Universidade Estadual de Campinas, Instituto da Computação | Instituto de Computação | Instituto de Computação. Programa de Pós-Graduação em Ciência da Computação. | TESE |
| 448924 | 2009 | 502 com grafia variante/sem a unidade; 852 do IC (catalogação) | Dissertação (mestrado) - Universidade Estadual de Campinas, Institutot de Computação | Instituto de Computação | Instituto de Computação. Programa de Pós-Graduação em Ciência da Computação. | DISSERTAÇÃO |
| 787665 | 2010 | 502 com grafia variante/sem a unidade; 852 do IC (catalogação) | Dissertação (mestrado) - Universidade Estadual de Campinas, Insituto de Computação | Instituto de Computação | Instituto de Computação. Programa de Pós-Graduação em Ciência da Computação. | DISSERTAÇÃO |
| 1161412 | 2020 | 502 com grafia variante/sem a unidade; 852 do IC (catalogação) | Dissertação (mestrado) - Programa de Pós-Graduação em Ciência da Computação | Instituto de Computação | Instituto de Computação. Programa de Pós-Graduação em Ciência da Computação. | DISSERTAÇÃO |
| 1254351 | 2022 | 852 de outra unidade; 502 e 710 do IC (catalogação) | Dissertação (mestrado) - Universidade Estadual de Campinas, Instituto de Computação | Instituto de Geociências | Instituto de Computação. Programa de Pós-Graduação em Ciência da Computação. | DISSERTAÇÃO |
| 1456447 | 2024 | 852 de outra unidade; 502 e 710 do IC (catalogação) | Tese (doutorado) - Universidade Estadual de Campinas (UNICAMP), Instituto de Computação. | Instituto de Matemática, Estatística e Computação Científica | Instituto de Computação. Programa de Pós-Graduação em Ciência da Computação. | TESE |
| 1456451 | 2024 | 852 de outra unidade; 502 e 710 do IC (catalogação) | Dissertação (mestrado) - Universidade Estadual de Campinas (UNICAMP), Instituto de Computação | Instituto de Matemática, Estatística e Computação Científica | Instituto de Computação. Programa de Pós-Graduação em Ciência da Computação. | DISSERTAÇÃO |
| 1456567 | 2024 | 852 de outra unidade; 502 e 710 do IC (catalogação) | Dissertação (mestrado) - Universidade Estadual de Campinas (UNICAMP), Instituto de Computação | Instituto de Matemática, Estatística e Computação Científica | Instituto de Computação. Programa de Pós-Graduação em Ciência da Computação. | DISSERTAÇÃO |
| 1456574 | 2024 | 852 de outra unidade; 502 e 710 do IC (catalogação) | Dissertação (mestrado) - Universidade Estadual de Campinas (UNICAMP), Instituto de Computação | Instituto de Matemática, Estatística e Computação Científica | Instituto de Computação. Programa de Pós-Graduação em Ciência da Computação. | DISSERTAÇÃO |
| 1456655 | 2024 | 852 de outra unidade; 502 e 710 do IC (catalogação) | Dissertação (mestrado) - Universidade Estadual de Campinas (UNICAMP), Instituto de Computação | Instituto de Matemática, Estatística e Computação Científica | Instituto de Computação. Programa de Pós-Graduação em Ciência da Computação. | DISSERTAÇÃO |
| 1456697 | 2024 | 852 de outra unidade; 502 e 710 do IC (catalogação) | Dissertação (mestrado) - Universidade Estadual de Campinas (UNICAMP), Instituto de Computação | Instituto de Matemática, Estatística e Computação Científica | Instituto de Computação. Programa de Pós-Graduação em Ciência da Computação. | DISSERTAÇÃO |
| 1456870 | 2024 | 852 de outra unidade; 502 e 710 do IC (catalogação) | Dissertação (mestrado) - Universidade Estadual de Campinas (UNICAMP), Instituto de Computação | Instituto de Matemática, Estatística e Computação Científica | Instituto de Computação. Programa de Pós-Graduação em Ciência da Computação. | DISSERTAÇÃO |
| 1506329 | 2025 | 852 de outra unidade; 502 e 710 do IC (catalogação) | Dissertação (mestrado) - Universidade Estadual de Campinas (UNICAMP), Instituto de Computação | Instituto de Matemática, Estatística e Computação Científica | Instituto de Computação. Programa de Pós-Graduação em Ciência da Computação. | DISSERTAÇÃO |
| 1509319 | 2025 | 852 de outra unidade; 502 e 710 do IC (catalogação) | Dissertação (mestrado) - Universidade Estadual de Campinas (UNICAMP), Instituto de Computação | Instituto de Matemática, Estatística e Computação Científica | Instituto de Matemática, Estatística e Ciência da Computação. Programa de Pós-Graduação em Ciência da Computação. | DISSERTAÇÃO |


Links da planilha **corrigidos à mão** em `links/ids_manuais.csv` (o registro do link original não é a defesa; `(anulado)` = registro certo ainda não achado, a linha fica fora da base):

| ano_planilha | celula | id_na_planilha | codigo_usado | 502_do_id_da_planilha | 852_do_id_da_planilha | fonte |
|---|---|---|---|---|---|---|
| 2010 | D48 | (handle antigo, sem id) | 917890 |  |  | busca manual no repositório (2026-11-09); o handle antigo aponta para uma tese da FEEC de 2001; o registro certo está catalogado com data de defesa 20-12-2013 |
| 2016 | D60 | 979994 | 979626 | Trabalho de Conclusão de Curso (graduação) - Universidade Estadual de Campinas, Instituto de Geociências | Instituto de Geociências | busca manual no repositório (2026-11-09): o link da planilha apontava para 979994, um TCC do Instituto de Geociências de um homônimo do aluno; 979626 confere com aluno, orientador, data e nível da planilha |
| 2019 | D8 | 1060991 | 1089706 | Tese (doutorado) - Universidade Estadual de Campinas, Faculdade de Educação | Faculdade de Educação | busca manual no repositório (2026-11-09): o link da planilha apontava para 1060991, uma tese da Faculdade de Educação (a busca casou nomes de campos diferentes); 1089706 confere com aluno, orientador, data e nível da planilha |


Ids que só existem na base antiga (a planilha nova trocou os links), coletados à parte em `marc_raw/antigos/` só para esta checagem:

| codigo | ano_antigo | nota_tese | unidade | tipo_obra | fora_do_IC |
|---|---|---|---|---|---|
| 1089524 | 2024 | Dissertação (mestrado profissional) - Universidade Estadual de Campinas, Faculdade de Odontologia de Piracicaba | Faculdade de Odontologia de Piracicaba (FOP) | DISSERTAÇÃO | True |
| 1242940 | 2021 |  | Instituto de Física Gleb Wataghin | ARTIGO | True |
| 480769 | 2023 | Tese (doutorado) - Universidade Estadual de Campinas, Faculdade de Ciencias Medicas | Faculdade de Ciências Médicas | TESE | True |


## 7. Ids duplicados e defesas de 2010 sem tipo

Ids duplicados na planilha nova:

| codigo | ano | celula | tipo |
|---|---|---|---|
| 434549 | 2008 | D21 | MESTRADO |
| 434549 | 2013 | D60 | DOUTORADO |


Ids duplicados nos `base_mo412/csvs/links*.csv` antigos:

| codigo | arquivo |
|---|---|
| 434549 | links2008.csv, links2013.csv |
| 1456454 | links2024.csv, links2024.csv |


Defesas de 2010 sem `tipo` na planilha: **46** (a aba 2010 não tem o cabeçalho MESTRADO). Na base antiga eram 45. O `nivel` tirado da nota 502 cobre o buraco: MESTRADO: 46.

Ids: 478387, 480801, 772832, 771277, 480734, 480729, 771272, 771295, 771289, 776438, 771302, 779146, 771269, 772338, 771256, 778145, 779116, 779140, 777443, 778260, 774177, 779402, 774079, 777416, 778122, 772853, 772316, 779213, 777438, 777420, 786051, 783735, 779382, 782517, 787681, 782510, 782519, 779165, 779398, 782411, 786096, 783707, 787665, 782265, 845762, 917890


## 8. Agência de fomento (campo 536)

- Defesas com alguma agência: **487** de 1099 (44.3%). O campo existe em quase todos os registros, mas muitas vezes vem vazio ("Agência de fomento:").

Valores (uma defesa pode ter mais de um):

| agencia | defesas |
|---|---|
| CAPES | 309 |
| CNPQ | 237 |
| FAPESP | 181 |
| Funcamp | 28 |
| FAEPEX | 6 |
| CPqD/Campinas | 1 |
| FUNCAP | 1 |
| FUNCAMP | 1 |
| CTI | 1 |
| FUNDECT | 1 |
| BEX | 1 |


Preenchimento por ano da planilha:

| ano_planilha | com agência | defesas | % |
|---|---|---|---|
| 2006 | 0 | 71 | 0 |
| 2007 | 1 | 41 | 2 |
| 2008 | 0 | 36 | 0 |
| 2009 | 0 | 47 | 0 |
| 2010 | 0 | 59 | 0 |
| 2011 | 0 | 52 | 0 |
| 2012 | 0 | 55 | 0 |
| 2013 | 0 | 57 | 0 |
| 2014 | 1 | 44 | 2 |
| 2015 | 42 | 61 | 69 |
| 2016 | 57 | 61 | 93 |
| 2017 | 44 | 57 | 77 |
| 2018 | 42 | 54 | 78 |
| 2019 | 44 | 50 | 88 |
| 2020 | 49 | 69 | 71 |
| 2021 | 45 | 58 | 78 |
| 2022 | 41 | 55 | 75 |
| 2023 | 37 | 48 | 77 |
| 2024 | 40 | 55 | 73 |
| 2025 | 44 | 69 | 64 |


## 9. Papéis e coorientadores

| papel | participações |
|---|---|
| Avaliador | 2886 |
| Orientador | 1103 |
| Coorientador | 378 |
| ? | 6 |
| Organizador | 1 |
| Presidente | 1 |


- Coorientadores: **378** participações em **365** defesas (354 com ORCID). A base antiga não tinha nenhum.
- Linhas 700 sem papel (`|e`): **6**. O papel não foi inferido.
- Linhas 700 com papel "Autor" (seriam o estudante): **0**.

Papéis fora de Avaliador/Orientador/Coorientador (mantidos como estão no MARC; `?` = sem `|e`):

| codigo | ano_planilha | ordem | papel | nome | orcid_n |
|---|---|---|---|---|---|
| 1170202 | 2021 | 6 | ? | Borin, Juliana Freitag | 0000-0002-8603-699X |
| 1236073 | 2021 | 6 | ? | Colombini, Esther Luna | 0000-0003-0467-3133 |
| 1347602 | 2023 | 3 | ? | Morabito, Reinaldo | 0000-0002-3948-305X |
| 1371384 | 2023 | 4 | ? | Usberti, Fábio Luiz | 0000-0002-8972-080X |
| 1409397 | 2024 | 1 | Organizador | Raimundo, Marcos Medeiros | 0000-0003-0499-2564 |
| 779398 | 2010 | 1 | ? | Azevedo, Rodolfo Jardim de | 0000-0002-8803-0401 |
| 782510 | 2010 | 1 | ? | Rigo, Sandro | 0000-0002-9539-6874 |
| 983916 | 2017 | 2 | Presidente | Ramírez Rivera, Adín | 0000-0002-4321-9075 |

- Defesas com mais de um 700 `Orientador` (dupla orientação/cotutela): **7**.
- Linhas 700 sem nome (`|a`): **1**: 782519 (Orientador).

- Defesas sem nenhum 700 `Orientador`: **3**: 1376019, 1409397, 782510


## 10. Outras checagens

Defesas coletadas por ano da planilha e nível (nota 502):

| ano_planilha | DOUTORADO | MESTRADO | MESTRADO PROFISSIONAL | total |
|---|---|---|---|---|
| 2006 | 12 | 32 | 27 | 71 |
| 2007 | 11 | 29 | 1 | 41 |
| 2008 | 11 | 25 | 0 | 36 |
| 2009 | 15 | 32 | 0 | 47 |
| 2010 | 13 | 46 | 0 | 59 |
| 2011 | 14 | 38 | 0 | 52 |
| 2012 | 21 | 34 | 0 | 55 |
| 2013 | 17 | 40 | 0 | 57 |
| 2014 | 13 | 31 | 0 | 44 |
| 2015 | 18 | 43 | 0 | 61 |
| 2016 | 24 | 37 | 0 | 61 |
| 2017 | 17 | 40 | 0 | 57 |
| 2018 | 17 | 37 | 0 | 54 |
| 2019 | 15 | 35 | 0 | 50 |
| 2020 | 15 | 54 | 0 | 69 |
| 2021 | 17 | 41 | 0 | 58 |
| 2022 | 19 | 36 | 0 | 55 |
| 2023 | 19 | 29 | 0 | 48 |
| 2024 | 21 | 34 | 0 | 55 |
| 2025 | 26 | 42 | 1 | 69 |
| total | 335 | 735 | 29 | 1099 |


`tipo` da planilha diferente do `nivel` da nota 502 (fora os sem tipo): **3**

| codigo | ano_planilha | tipo | nivel | nota_tese |
|---|---|---|---|---|
| 1540326 | 2025 | MESTRADO | MESTRADO PROFISSIONAL | Dissertação (mestrado profissional) - Universidade Estadual de Campinas (UNICAMP), Instituto de Computação |
| 404987 | 2006 | MESTRADO PROFISSIONAL | MESTRADO | Dissertação (mestrado) - Universidade Estadual de Campinas, Instituto de  Computação |
| 415555 | 2007 | MESTRADO | DOUTORADO | Tese (doutorado) - Universidade Estadual de Campinas, Instituto de Computação. |


- Data da defesa (943) ausente ou não interpretável: **3**

| codigo | ano_planilha | data_defesa_txt |
|---|---|---|
| 1506491 | 2025 | (943 ausente ou vazio) |
| 378303 | 2006 | 20-02 206 |
| 822086 | 2011 | (943 ausente ou vazio) |

- Ano da data 943 diferente da aba da planilha: **6**

| codigo | ano_planilha | data |
|---|---|---|
| 373710 | 2006 | 2004-02-23 |
| 397009 | 2006 | 2007-05-15 |
| 397843 | 2006 | 2007-12-15 |
| 425656 | 2008 | 2007-02-23 |
| 896594 | 2012 | 2004-04-20 |
| 917890 | 2010 | 2013-12-20 |

