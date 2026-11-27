# Guia de montagem

O que já existe: os dados, um modelo pronto (tabelas, relacionamentos, 46 medidas), o tema e quatro páginas vazias.
O que você monta: os 46 visuais, seguindo [report-spec.md](report-spec.md) (em inglês). A Fase A leva cerca de meia
hora; a Fase B leva algumas horas. Also in English: [build-guide.md](build-guide.md).

## O que você precisa

* Um computador com Windows e o **Power BI Desktop** comum (Microsoft Store ou o instalador de powerbi.microsoft.com).
  A edição "otimizada para o Servidor de Relatórios" não abre projetos.
* Esta pasta, **inteira**, em um lugar que **o OneDrive não sincroniza**. `C:\labtrack-bi` é o mais fácil: o modelo
  procura os dados em `C:\labtrack-bi\data` por padrão. Não abra o `labtrack.pbip` de dentro do zip: o Power BI precisa
  das pastas que ficam ao lado dele. Clique com o botão direito no zip e escolha Extrair Tudo ou, se você tem o Git,
  rode `git clone https://github.com/juanbezerra1/labtrack-bi C:\labtrack-bi`.
* Python 3.10 ou mais novo, **só para as conferências** (`check-model`, `check-report`). O relatório em si não usa
  Python. Em um terminal, nesta pasta, uma vez: `py -m pip install -e .`. Daí em diante todo comando deste guia é
  `py -m labtrack_bi <comando>`; se a pasta Scripts do Python estiver no seu PATH, `labtrack-bi <comando>` faz o mesmo.
* Os nomes de menu abaixo estão em inglês. Se o seu Power BI está em português, os botões são os mesmos e as palavras
  mudam (a tabela no fim do guia traz os nomes mais prováveis, de memória: confira no seu Desktop). Para seguir o guia
  palavra por palavra, troque o idioma em File > Options and settings > Options > Regional Settings > Application
  language e reinicie o programa (em português, algo como Arquivo > Opções e configurações > Opções > Configurações
  regionais > Idioma do aplicativo).

Desde setembro de 2026 o formato de projeto (`.pbip`) está em disponibilidade geral no Power BI Desktop e o PBIR é o
formato padrão do relatório, então não há nada para ligar. O Desktop continua salvando `.pbix` por padrão, mas um
projeto que você abriu como `labtrack.pbip` é salvo de volta como projeto. Em uma versão mais antiga, ligue antes as
opções: File > Options and settings > Options > Preview features: "Power BI Project (.pbip) save option", "Store
semantic model using TMDL format" e "Store reports using enhanced metadata format (PBIR)"; reinicie o Desktop.

## Fase A: abra o projeto e confira os números

1. **Abra `labtrack.pbip`** (duplo clique, ou File > Open report > Browse this device). O Desktop mostra as quatro
   páginas vazias e as tabelas do modelo; as tabelas ficam sem linhas até você atualizar.
2. **Aponte o modelo para os dados**, se a pasta não for `C:\labtrack-bi`: Home > Transform data > Edit parameters,
   escreva o caminho completo da pasta `data` em `DataFolder` (por exemplo `D:\trabalho\labtrack-bi\data`), OK, e
   Close & Apply se o Desktop pedir.
3. **Atualize**: Home > Refresh. Oito consultas carregam, com estas linhas:

   | Tabela | Linhas | Tabela | Linhas |
   |---|---:|---|---:|
   | Calendar | 2.192 | Session | 909 |
   | Study | 3 | Recording | 1.634 |
   | Participant | 200 | Trial | 45.806 |
   | Researcher | 12 | Device | 24 |

   A Table view (segundo ícone da barra da esquerda) mostra, embaixo, o número de linhas da tabela selecionada.
4. **Olhe o modelo**: Model view (terceiro ícone). Deve ficar igual a [img/model.svg](img/model.svg): sete
   relacionamentos, todos de muitos para um, com a seta para o lado "um", e uma tabela `Measures` sem relacionamentos,
   com 46 medidas em seis pastas.
5. **Confira os números**: DAX query view (quarto ícone). Abra `model/check.dax` em qualquer editor de texto, copie
   **uma** consulta (todas as linhas de `EVALUATE` até a linha em branco antes do próximo comentário), cole na DAX query
   view e clique em Run. Compare o resultado com a tabela de mesmo número em [expected-numbers.md](expected-numbers.md).
   Faça as 13. As que mais importam são a 1 (todas as medidas), a 4 (acumulados por mês) e a 13 (os três efeitos).
   Diferença na última casa pode ser arredondamento; número diferente é defeito, no modelo ou no meu entendimento do
   Power BI, e eu quero saber qual consulta foi e o que ela devolveu.
6. **Salve** (Ctrl+S). A partir daqui os arquivos do projeto são do Power BI Desktop: ele os reescreve do jeito dele.
   Não rode `py -m labtrack_bi build --reset-project` a menos que queira jogar seu trabalho fora (ele guarda uma cópia
   `.backup` das pastas antigas, mas você perderia os visuais das novas).
7. Em um terminal, nesta pasta: `py -m labtrack_bi check-model`. Ele lê o modelo que o Desktop salvou e diz se ainda
   significa o que [model.md](model.md) diz. A última linha deve ser `ok: the model says what the spec says`.

### Se o projeto não abrir

O Desktop é o único leitor que eu não consegui testar aqui, então isso pode acontecer. Anote a versão (Help > About) e a
mensagem exata e me mande; eu conserto o gerador.

**A primeira coisa a tentar.** Três arquivos pequenos não têm uma linha que os esquemas publicados pela Microsoft dão
como obrigatória (os projetos de exemplo que o próprio Desktop salva também não a têm; veja
[verification.md](verification.md#three-small-files), em inglês). Se a mensagem falar de esquema (schema), de versão ou
de uma propriedade que ele não conhece, acrescente a linha como primeira propriedade do arquivo (a vírgula no fim faz
parte dela), salve e abra o projeto de novo:

| Arquivo | A linha a acrescentar |
|---|---|
| `labtrack.pbip` | `"$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",` |
| `labtrack.Report/definition.pbir` | `"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",` |
| `labtrack.SemanticModel/definition.pbism` | `"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",` |

Se isso não resolver, dá para montar o mesmo modelo à mão (nove consultas para colar, sete relacionamentos, 46
medidas), o que é lento, mas funciona:

1. Abra um relatório novo em branco. Home > Transform data > New source > Blank query > Advanced editor. Cole
   `model/powerquery/DataFolder.pq` (a última linha; corrija o caminho) e dê à consulta o nome `DataFolder`.
2. Faça o mesmo com cada um dos outros oito arquivos de `model/powerquery/`, dando à consulta o nome do arquivo
   (`Calendar`, `Study`, ...). Close & Apply.
3. Marque `Calendar` como tabela de datas (Table tools > Mark as date table, coluna `Date`) e crie os sete
   relacionamentos de [model.md](model.md#relationships) na Model view (arraste do lado "muitos" para o lado "um"; deixe
   o resto como o Power BI sugerir: muitos para um, direção única).
4. Crie a tabela `Measures` e cole cada bloco de `model/measures.dax`, como explicam as primeiras linhas do arquivo.
5. Siga para o passo 5 acima. A partir daí o relatório é o mesmo.

## Fase B: monte o relatório

### O ciclo

Para cada página, na ordem de [report-spec.md](report-spec.md): monte os visuais da lista, um por um; salve; rode
`py -m labtrack_bi check-report`; corrija o que ele listar; olhe a página ao lado do desenho dela em `docs/img/`. A
conferência só lê o arquivo que o Desktop salvou. Para cada visual ela compara o tipo, o título, a posição (aceita 8 pixels de
diferença) e os campos de cada poço. É a prova de que você fez o que a especificação diz, e nada além: se a página está
bonita, quem julga são seus olhos.

```console
PS C:\labtrack-bi> py -m labtrack_bi check-report
```

Ela imprime primeiro os erros (visual que falta, campo no poço errado), depois os avisos (posição a mais de 8 pixels,
título diferente do da especificação, visual que a especificação não lista) e termina com o número de visuais da
especificação que encontrou com o tipo e os campos certos. Ela só termina com erro enquanto houver erros; avisos não
a fazem falhar. Uma página que você ainda não começou aparece como faltando: é esperado.

### Ordem de trabalho em uma página

1. A caixa de texto com o título, depois os slicers, depois os cartões: são os visuais fáceis e eles fixam a posição de
   todo o resto.
2. Os gráficos. 3. A tabela.
4. Defina o título, a posição e o texto alternativo de cada visual **na hora**. Voltar a todos no fim é muito mais lento.

As cores vêm do tema `LabTrack`, que já está aplicado ao relatório (View > Themes). Não pinte nada à mão: a paleta do
tema foi conferida para leitores que não enxergam todas as cores ([design.md](design.md#colours)).

### Como fazer cada coisa

**Adicionar um visual com seus campos.** Clique em um lugar vazio da página, clique no ícone do tipo no painel
Visualizations (deixe o ponteiro parado em cima para ler o nome) e arraste os campos do painel Data para os poços que a
coluna Fields cita (X-axis, Y-axis, Legend, Values, Tooltips). `Table[Column]` é uma coluna daquela tabela; `[Nome]` é uma
medida, e toda medida está na tabela `Measures`. Em cartão, slicer e tabela, o poço se chama Fields, Field e Columns na
especificação; no painel pode se chamar Data ou Values.

**Título, posição, tamanho, texto alternativo.** Selecione o visual, depois Format visual (o rolo de tinta) > aba General:

* *Title*: ligue e digite o texto da coluna Title. A conferência acha o seu visual primeiro por esse texto. Em uma caixa
  de texto, a coluna Title é o texto que fica dentro da caixa.
* *Properties*: Position (horizontal, vertical) e Size (largura, altura) recebem os quatro números da coluna Position.
* *Alt text*: uma frase sobre o que o visual mostra.

**Copiar um visual.** Ctrl+C, Ctrl+V cola a cópia na mesma posição; troque o campo e o título. Os seis cartões da página
1 são um cartão feito uma vez e colado cinco vezes.

**Slicer.** Ícone Slicer, a coluna em Field. Format visual > Visual > Slicer settings > Options > Style: Dropdown ou
Tile, como a coluna Notes diz. Se os botões do Tile não couberem em uma linha, ponha a orientação na horizontal.

**Rótulos de dados, legenda, eixos.** Format visual > Visual > Data labels, Legend, X axis, Y axis. A coluna Notes diz
quando os rótulos ficam ligados. Gráfico com duas ou mais séries sempre mantém a legenda.

**Ordenar.** O `...` no canto de cima à direita do gráfico > Sort axis > a medida, e depois `...` > Sort descending.

**Filtrar um visual.** Com o visual selecionado, o painel Filters mostra "Filters on this visual". Arraste a coluna para
lá. *Basic filtering* tem uma lista de caixas (desmarque `(Blank)` para tirar os vazios); *Advanced filtering* tem "is
less than or equal to 4" e parecidos; *Top N* pede o número, a medida em "By value" e depois Apply filter. As notas da
especificação dizem qual coluna e quais valores.

**Tabela.** Format visual > Visual > Totals liga a linha de totais. Barras de dados: Format visual > Visual > Cell
elements, escolha a coluna em "Apply settings to" e ligue Data bars.

**Caixa de texto.** Home > Text box (ou Insert > Text box). Digite o texto e formate como a coluna Notes diz.

### As quatro páginas

* **Página 1, Overview** (13 visuais). Seis cartões com os números principais, dois gráficos de sessões, um acumulado e
  uma tabela dos três estudos. Os gráficos por mês são filtrados para os anos de 2024 a 2026: o calendário vai de 2023
  a 2028 e as sessões vão de março de 2024 a dezembro de 2026.
* **Página 2, Recruitment** (13). O gráfico de visitas é filtrado para as visitas de 1 a 4, porque todo estudo planeja
  quatro visitas e os números maiores são visitas extras.
* **Página 3, Data quality** (12). O gráfico de resultado do controle de qualidade tem quatro séries (passed, flagged,
  rejected, pending), então a legenda fica ligada. Os dois gráficos de barras da direita têm um filtro cada (motivos em
  branco fora, os 8 principais aparelhos).
* **Página 4, Findings** (8). Três efeitos plantados nos dados. A caixa de texto do alto diz que os dados são sintéticos:
  mantenha, porque a página mostra como se faz um relatório, e os números dela não são evidência de nada.

### Quando a página estiver pronta

1. Salve (Ctrl+S) e rode `py -m labtrack_bi check-report`. Procure ficar sem erro e sem aviso.
2. **Capturas de tela.** Para cada página, mostre-a no tamanho real (View > Page view > Actual size, se a sua tela for
   grande o bastante), tire uma foto só da tela do relatório (Windows: Win+Shift+S) e salve como PNG com estes nomes, em
   `docs/img/`:

   ```text
   docs/img/screenshot-overview.png
   docs/img/screenshot-recruitment.png
   docs/img/screenshot-data-quality.png
   docs/img/screenshot-findings.png
   ```

   Depois `py -m labtrack_bi add-screenshots` coloca as que existem em `README.md` e `README.pt-BR.md`, entre os
   dois comentários `screenshots`. Dá para rodar de novo quando você acrescentar as outras.
3. Feche o Desktop e olhe as mudanças antes de enviar ao Git: as pastas do projeto só têm arquivos de texto, e
   `.pbi/localSettings.json` e `.pbi/cache.abf` (o cache dos dados, grande) estão no `.gitignore`.

## Quando algo não bate

| O que você vê | Causa provável | O que fazer |
|---|---|---|
| O Desktop diz que o arquivo não é compatível ou não consegue abri-lo | Edição do Servidor de Relatórios, ou versão antiga com as opções de projeto desligadas | Instale o Desktop comum, ou ligue as três opções de preview acima |
| O Desktop diz `ReportDefinition: Required artifact is missing in '...\labtrack.Report\definition.pbir'` | As pastas `labtrack.Report` e `labtrack.SemanticModel` não estão ao lado do `labtrack.pbip`. A causa mais comum é abrir o arquivo de dentro do zip, onde o Windows extrai só aquele arquivo | Feche o Desktop. Extraia o zip inteiro (botão direito > Extrair Tudo) ou faça `git clone` do repositório, e abra o `labtrack.pbip` dessa pasta |
| As tabelas estão vazias | Os dados ainda não foram carregados | Home > Refresh |
| A atualização diz que não acha um arquivo ou uma pasta | `DataFolder` aponta para o lugar errado | Home > Transform data > Edit parameters; a pasta precisa conter `dim_date.csv` |
| A atualização diz que o acesso ao caminho foi negado | A pasta está no OneDrive, ou em um lugar que o Windows protege | Mova o repositório para `C:\labtrack-bi` |
| Um número de `check.dax` difere de `expected-numbers.md` | Defeito no modelo, ou a pasta de dados não é a deste repositório | Compare `data/SHA256SUMS` com os arquivos; se baterem, me mande a consulta e o resultado |
| Aparece a barra "Apply external changes" | Um arquivo do projeto mudou com o Desktop aberto (por exemplo por `py -m labtrack_bi build`) | Escolha Apply, ou feche sem salvar; não rode `build` com o Desktop aberto |
| `check-report` diz que falta um visual que você montou | Outro tipo de visual, outro campo em um poço, ou um título diferente do da especificação | Leia a mensagem: ela diz o que esperava e o visual mais próximo que achou |
| `check-report` diz "extra visual" | Um visual que a especificação não lista (por exemplo um que o Desktop criou quando você soltou um campo na página vazia) | Apague, ou ignore o aviso se você o pôs de propósito |

Nomes de menu em português (de memória; confira no seu Desktop): Home = Página Inicial, Insert = Inserir, View = Exibir,
Transform data = Transformar dados, Refresh = Atualizar, Edit parameters = Editar parâmetros, Close & Apply = Fechar e
Aplicar, Visualizations = Visualizações, Data = Dados, Filters = Filtros, Format visual = Formatar visual,
General = Geral, Title = Título, Alt text = Texto alternativo, Text box = Caixa de texto, Slicer = Segmentação de Dados,
Legend = Legenda, Data labels = Rótulos de dados.

## Depois que o Desktop salvou o projeto

`py -m labtrack_bi build` escreve os arquivos que derivam de `src/labtrack_bi/spec.py` (os arquivos de Power Query e de
DAX, os documentos, os desenhos) e escreve o projeto (`labtrack.pbip` e as duas pastas dele) só na primeira vez. Do
primeiro salvamento no Desktop em diante o projeto é do Desktop; `py -m labtrack_bi check` deixa de compará-lo byte a
byte e avisa, e
`check-model` e `check-report` comparam o que ele significa. Se você mudar `spec.py`, mude o projeto à mão no Desktop
também, ou use `build --reset-project` para recomeçar o projeto a partir da especificação (as pastas antigas ficam como
`.backup`).
