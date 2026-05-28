import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import re
import warnings

# Ignora avisos visuais no terminal
warnings.filterwarnings('ignore')

def clean_numeric(val):
    if pd.isna(val): return 0.0
    if isinstance(val, (int, float)): return float(val)
    val = str(val).replace('.', '').replace(',', '.')
    val = re.sub(r'[^\d\.\-]', '', val)
    try:
        return float(val) if val else 0.0
    except:
        return 0.0

def carregar_dados():
    file_path = 'movimentacao_detalhada.csv'
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            primeira_linha = f.readline()
            pular = 1 if 'Período' in primeira_linha else 0
            
        df = pd.read_csv(file_path, sep=';', skiprows=pular, encoding='utf-8', low_memory=False)
        return df
    except Exception as e:
        print(f"Erro ao ler o arquivo CSV: {e}")
        return None

def gerar_graficos_master():
    df = carregar_dados()
    if df is None or df.empty:
        return

    print("📊 Iniciando geração do Dashboard de Gráficos (5 Imagens)...")
    sns.set_theme(style="whitegrid")

    # Tratamento prévio de colunas necessárias
    colunas_texto = ['Início Carga', 'Fim Carga', 'Início Basculamento', 'Fim Basculamento']
    for col in colunas_texto:
        if col not in df.columns: df[col] = 'Desconhecido'
        else: df[col] = df[col].astype(str).str.strip()

    # =========================================================================
    # GRÁFICO 1: PIZZA - TIPO DE CICLO GERAL
    # =========================================================================
    df['Ciclo_Auto'] = (df['Início Carga'].str.contains('Automático', case=False)) & \
                       (df['Fim Carga'].str.contains('Automático', case=False)) & \
                       (df['Início Basculamento'].str.contains('Automático', case=False)) & \
                       (df['Fim Basculamento'].str.contains('Automático', case=False))

    df['Ciclo_Manual'] = (df['Início Carga'].str.contains('Manual', case=False)) & \
                         (df['Fim Carga'].str.contains('Manual', case=False)) & \
                         (df['Início Basculamento'].str.contains('Manual', case=False)) & \
                         (df['Fim Basculamento'].str.contains('Manual', case=False))

    def classificar_ciclo(row):
        if row['Ciclo_Auto']: return '100% Automático'
        if row['Ciclo_Manual']: return '100% Manual'
        return 'Ciclo Misto / Parcial'

    df['Tipo de Ciclo'] = df.apply(classificar_ciclo, axis=1)

    plt.figure(figsize=(8, 6))
    contagem = df['Tipo de Ciclo'].value_counts()
    cores_pizza = ['#FF9800', '#F44336', '#4CAF50'] # Laranja (Misto), Vermelho (Manual), Verde (Auto)
    
    plt.pie(contagem, labels=contagem.index, autopct='%1.1f%%', startangle=140, colors=cores_pizza,
            wedgeprops={'edgecolor': 'white', 'linewidth': 1.5})
    plt.title('1. Distribuição: Ciclos Automáticos vs Manuais vs Mistos', fontsize=14, fontweight='bold')
    plt.savefig('01_grafico_pizza_ciclos.png', bbox_inches='tight', dpi=300)
    plt.close()
    print(" ✅ Salvo: 01_grafico_pizza_ciclos.png")

    # =========================================================================
    # GRÁFICO 2: BARRAS - PERCENTUAL DE AUTOMAÇÃO POR ETAPA
    # =========================================================================
    etapas = ['Início Carga', 'Fim Carga', 'Início Basculamento', 'Fim Basculamento']
    dados_etapas = []

    for etapa in etapas:
        contagem = df[etapa].value_counts()
        total = contagem.sum()
        auto = contagem.get('Automático', 0)
        manual = contagem.get('Manual', 0)
        dados_etapas.append({'Etapa': etapa, 'Automático': (auto/total)*100, 'Manual': (manual/total)*100})

    df_etapas = pd.DataFrame(dados_etapas).set_index('Etapa')

    ax = df_etapas.plot(kind='bar', figsize=(10, 6), color=['#4CAF50', '#F44336'], width=0.7)
    plt.title('2. Percentual de Adesão por Etapa do Ciclo', fontsize=14, fontweight='bold')
    plt.ylabel('Percentual (%)')
    plt.xlabel('Etapa Operacional')
    plt.xticks(rotation=0)
    plt.ylim(0, 110) # Espaço para o texto no topo
    
    # Adicionar os valores acima das barras
    for container in ax.containers:
        ax.bar_label(container, fmt='%.1f%%', padding=3, fontweight='bold', fontsize=10)

    plt.legend(title='Status', loc='upper right')
    plt.savefig('02_grafico_adesao_etapas.png', bbox_inches='tight', dpi=300)
    plt.close()
    print(" ✅ Salvo: 02_grafico_adesao_etapas.png")

    # =========================================================================
    # GRÁFICO 3: BARRAS HORIZONTAIS - MÉTRICAS DE QUALIDADE (ERROS)
    # =========================================================================
    # Preparando as anomalias
    df['Dist_0'] = df.get('Distância Cheio (m)', '0').apply(clean_numeric) == 0.0
    df['Coord_00'] = (df.get('Latitude (Basculamento)', '0').apply(clean_numeric) == 0.0) & \
                     (df.get('Longitude (Basculamento)', '0').apply(clean_numeric) == 0.0)
    df['Trans_Man_Aut'] = (df['Início Basculamento'].str.contains('Manual', case=False)) & \
                          (df['Fim Basculamento'].str.contains('Automático', case=False))
    
    total_ciclos = len(df)
    taxa_perda_gps = (df['Coord_00'].sum() / total_ciclos) * 100
    taxa_transicao = (df['Trans_Man_Aut'].sum() / total_ciclos) * 100
    taxa_falso_pos = (df['Dist_0'].sum() / total_ciclos) * 100 # Simplificação para falso positivo

    metricas = {
        'Taxa de Perda GPS (Coord 0,0)': taxa_perda_gps,
        'Taxa Falsos Positivos (Dist 0)': taxa_falso_pos,
        'Taxa Transição Indevida (Man->Aut)': taxa_transicao
    }

    df_metricas = pd.Series(metricas).sort_values(ascending=True)

    plt.figure(figsize=(10, 5))
    ax = df_metricas.plot(kind='barh', color='#E91E63')
    plt.title('3. Principais Anomalias e Métricas de Qualidade', fontsize=14, fontweight='bold')
    plt.xlabel('Percentual de Ocorrência (%)')
    plt.xlim(0, max(df_metricas) + 10)

    for i, v in enumerate(df_metricas):
        ax.text(v + 0.5, i, f"{v:.2f}%", va='center', fontweight='bold', fontsize=11)

    plt.savefig('03_grafico_metricas_qualidade.png', bbox_inches='tight', dpi=300)
    plt.close()
    print(" ✅ Salvo: 03_grafico_metricas_qualidade.png")

    # =========================================================================
    # GRÁFICO 4: BARRAS - CICLOS POR CAMINHÃO
    # =========================================================================
    plt.figure(figsize=(12, 6))
    df_cam = df['Caminhão'].fillna('Desconhecido')
    ordem_caminhoes = df_cam.value_counts().head(15).index # Top 15 para não poluir
    
    sns.countplot(data=df, x='Caminhão', order=ordem_caminhoes, palette='viridis', hue='Caminhão', legend=False)
    plt.title('4. Volume de Ciclos Operacionais por Caminhão (Top 15)', fontsize=14, fontweight='bold')
    plt.xlabel('Equipamento (Caminhão)')
    plt.ylabel('Quantidade de Ciclos')
    plt.xticks(rotation=45, ha='right')
    
    plt.savefig('04_grafico_barras_caminhoes.png', bbox_inches='tight', dpi=300)
    plt.close()
    print(" ✅ Salvo: 04_grafico_barras_caminhoes.png")

    # =========================================================================
    # GRÁFICO 5: BARRAS - TOP DESTINOS (BASCULAMENTO)
    # =========================================================================
    plt.figure(figsize=(10, 6))
    df['Destino'] = df['Destino'].fillna('Desconhecido')
    top_destinos = df['Destino'].value_counts().head(10).index
    
    sns.countplot(data=df, y='Destino', order=top_destinos, palette='magma', hue='Destino', legend=False)
    plt.title('5. Top 10 Destinos Mais Frequentes (Áreas de Basculamento)', fontsize=14, fontweight='bold')
    plt.xlabel('Quantidade de Basculamentos')
    plt.ylabel('Local de Destino')
    
    plt.savefig('05_grafico_barras_destinos.png', bbox_inches='tight', dpi=300)
    plt.close()
    print(" ✅ Salvo: 05_grafico_barras_destinos.png")
    
    print("\n🚀 Todos os 5 gráficos foram gerados e salvos com sucesso na pasta atual!")

if __name__ == '__main__':
    gerar_graficos_master()
