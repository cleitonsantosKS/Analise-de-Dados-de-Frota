# 🚛 Análise de Dados de Frota - Automação FMS

Este repositório contém scripts em Python desenvolvidos para auditar e analisar os dados de telemetria e despacho (FMS) de frotas de mineração/transporte. O foco principal é a **identificação de anomalias de automação** (falsos positivos, tempos excedidos, perda de GPS) e a geração de relatórios investigativos para as equipas de Automação, Manutenção e Operação.

## 📂 Ficheiros do Projeto

* `relatorio_master.py`: Analisa o ficheiro CSV e gera um relatório TXT detalhado com ranking de operadores, deteção de erros críticos (com link do GPS) e auditoria de tempos excedidos.
* `gerar_graficos_master.py`: Processa os mesmos dados para criar um Dashboard visual com 5 gráficos em formato `.png` (Circular, Barras, Métricas de Qualidade).
* `movimentacao_detalhada.csv`: Ficheiro de base de dados extraído do sistema (deve ser inserido na mesma pasta antes da execução).

---

## 🚀 Guia de Instalação e Execução (Windows / PowerShell)

Siga o passo a passo abaixo para configurar o ambiente do zero em qualquer computador com Windows usando o **PowerShell**.

### Passo 1: Instalar o Python pelo PowerShell
Abra o **PowerShell como Administrador** (prima a tecla Windows, escreva "PowerShell", clique com o botão direito do rato e selecione "Executar como Administrador").
Cole o comando abaixo e prima Enter:

```powershell
winget install -e --id Python.Python.3.11
winget install -e --id Git.Git
```

### Passo 2: Criar a pasta de Trabalho em "Documentos"
Abra o PowerShell (já não precisa de ser como administrador) e crie a pasta de análise executando:
Cole o comando abaixo e prima Enter:

```powershell
New-Item -Path "$env:USERPROFILE\Documents\Analise_de_Dados_Frota" -ItemType Directory
```
Navegue até à pasta recém-criada:
```powershell
cd "$env:USERPROFILE\Documents\Analise_de_Dados_Frota"
```
```
git clone https://github.com/cleitonsantosKS/Analise-de-Dados-de-Frota.git

```

### Passo 3: Instalar as Dependências (Bibliotecas)
Ainda no PowerShell e dentro da sua nova pasta, instale as bibliotecas necessárias executando:

PowerShell

```powershell
pip install pandas matplotlib seaborn
```
### Passo 4: Organizar os Ficheiros
Agora, vá ao seu Explorador do Windows (pastas), aceda à pasta Documentos > Analise_de_Dados_Frota e coloque três ficheiros lá dentro:

O seu ficheiro de dados: movimentacao_detalhada.csv

O script de relatório: relatorio_master.py

O script de gráficos: gerar_graficos_master.py

### Passo 5: Executar as Análises
Com os ficheiros na pasta e o PowerShell aberto na mesma, basta executar os comandos abaixo sempre que quiser gerar a análise do dia.

Para gerar o Relatório Master (TXT):

```powershell
python relatorio_master.py
```
Para gerar o Dashboard de Gráficos (PNGs):

```powershell
python gerar_graficos_master.py
```

### Resultados Esperados

Após a execução, a pasta será automaticamente preenchida com os relatórios gerados com a data e hora da extração, prontos para serem enviados por e-mail ou anexados a apresentações de fim de turno.

Exemplo de ficheiros gerados:

RELATORIO_MASTER_27-05-2026_18-30.txt

01_grafico_pizza_ciclos.png

02_grafico_adesao_etapas.png

03_grafico_metricas_qualidade.png

04_grafico_barras_caminhoes.png

05_grafico_barras_destinos.png
