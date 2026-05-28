import pandas as pd
import numpy as np
from datetime import datetime
import re
import warnings

# Ignora avisos do Pandas no terminal para manter a saída limpa
warnings.filterwarnings('ignore')

def clean_numeric(val):
    """Limpa strings numéricas do padrão brasileiro para float."""
    if pd.isna(val): return 0.0
    if isinstance(val, (int, float)): return float(val)
    val = str(val).replace('.', '').replace(',', '.')
    val = re.sub(r'[^\d\.\-]', '', val)
    try:
        return float(val) if val else 0.0
    except:
        return 0.0

def carregar_dados(file_path):
    """Lê o arquivo CSV e limpa colunas de texto e numéricas."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            skip = 1 if 'Período' in first_line else 0
            
        df = pd.read_csv(file_path, sep=';', skiprows=skip, encoding='utf-8', low_memory=False)

        # Limpeza de Textos
        cols_texto = ['Início Carga', 'Fim Carga', 'Início Basculamento', 'Fim Basculamento', 
                      'Operador', 'Caminhão', 'Origem', 'Destino', 'Material', 'Equipamento de Carga']
        for col in cols_texto:
            if col in df.columns: 
                df[col] = df[col].astype(str).str.strip()

        # Limpeza de Numéricos
        cols_num = ['Distância Cheio (m)', 'Tempo Basculamento (min)', 'Tempo de Ciclo (min)', 
                    'Latitude (Basculamento)', 'Longitude (Basculamento)', 'Tempo Carregamento (min)', 'Massa (tons)']
        for col in cols_num:
            if col in df.columns: 
                df[col] = df[col].apply(clean_numeric)

        df.fillna({'Origem': 'Desconhecido', 'Destino': 'Desconhecido', 'Material': 'Desconhecido'}, inplace=True)
        return df
    except Exception as e:
        print(f"Erro ao carregar o arquivo CSV: {e}")
        return None

def gerar_relatorio_master():
    df = carregar_dados('movimentacao_detalhada.csv')
    if df is None or df.empty: 
        print("❌ Arquivo não encontrado ou vazio.")
        return

    print("⏳ Processando inteligência de frota...")

    # =========================================================
    # 1. LÓGICA DE DETECÇÃO DE ANOMALIAS E PADRÕES
    # =========================================================
    df['Erro_Coord_00'] = (df.get('Latitude (Basculamento)', 0) == 0.0) & (df.get('Longitude (Basculamento)', 0) == 0.0)
    df['Erro_Dist_0'] = df.get('Distância Cheio (m)', 0) == 0.0
    df['Erro_Origem_Destino'] = df['Origem'] == df['Destino']
    df['Erro_Tempo_Basc_Alto'] = df.get('Tempo Basculamento (min)', 0) > 15.0
    df['Erro_Ciclo_Curto'] = df.get('Tempo de Ciclo (min)', 0) < 2.0
    df['Erro_Ciclo_Longo'] = df.get('Tempo de Ciclo (min)', 0) > 120.0

    df['Erro_Trans_Manual_Auto'] = False
    if 'Início Basculamento' in df.columns and 'Fim Basculamento' in df.columns:
        df['Erro_Trans_Manual_Auto'] = (df['Início Basculamento'].str.contains('Manual', na=False, case=False)) & \
                                       (df['Fim Basculamento'].str.contains('Automático', na=False, case=False))

    df['Tem_Erro'] = df[['Erro_Coord_00', 'Erro_Dist_0', 'Erro_Origem_Destino', 
                         'Erro_Tempo_Basc_Alto', 'Erro_Ciclo_Curto', 'Erro_Ciclo_Longo', 
                         'Erro_Trans_Manual_Auto']].any(axis=1)

    # =========================================================
    # 2. LÓGICA DE CLASSIFICAÇÃO DE CICLOS (Auto/Manual/Misto)
    # =========================================================
    cols_etapas = ['Início Carga', 'Fim Carga', 'Início Basculamento', 'Fim Basculamento']
    for col in cols_etapas:
        if col not in df.columns: df[col] = 'Desconhecido'

    df['Ciclo_100_Auto'] = (df['Início Carga'].str.contains('Automático', na=False, case=False)) & \
                           (df['Fim Carga'].str.contains('Automático', na=False, case=False)) & \
                           (df['Início Basculamento'].str.contains('Automático', na=False, case=False)) & \
                           (df['Fim Basculamento'].str.contains('Automático', na=False, case=False))

    df['Ciclo_100_Manual'] = (df['Início Carga'].str.contains('Manual', na=False, case=False)) & \
                             (df['Fim Carga'].str.contains('Manual', na=False, case=False)) & \
                             (df['Início Basculamento'].str.contains('Manual', na=False, case=False)) & \
                             (df['Fim Basculamento'].str.contains('Manual', na=False, case=False))

    df['Ciclo_Misto'] = ~df['Ciclo_100_Auto'] & ~df['Ciclo_100_Manual']

    # =========================================================
    # 3. CÁLCULOS E ESTATÍSTICAS GERAIS
    # =========================================================
    total_ciclos = len(df)
    ciclos_ok = len(df[~df['Tem_Erro']])
    ciclos_erro = len(df[df['Tem_Erro']])
    qtd_cava_sul = len(df[df['Destino'].str.contains('CAVA SUL', case=False, na=False)])

    perc_falhas = (ciclos_erro / total_ciclos * 100) if total_ciclos > 0 else 0
    perc_coord_00 = (df['Erro_Coord_00'].sum() / total_ciclos * 100) if total_ciclos > 0 else 0
    perc_trans_man_aut = (df['Erro_Trans_Manual_Auto'].sum() / total_ciclos * 100) if total_ciclos > 0 else 0

    df['Falso_Positivo'] = df['Erro_Dist_0'] & (df.get('Tempo de Ciclo (min)', 0) > 5)
    perc_falsos_pos = (df['Falso_Positivo'].sum() / total_ciclos * 100) if total_ciclos > 0 else 0

    # Definição de Hipóteses para os casos críticos
    def classificar_severidade(row):
        score = sum([row['Erro_Coord_00'], row['Erro_Dist_0'], row['Erro_Origem_Destino'], row['Erro_Tempo_Basc_Alto']])
        if score >= 3 or row['Erro_Tempo_Basc_Alto']: return 'CRÍTICA'
        if score == 2: return 'ALTA'
        if score == 1: return 'MÉDIA'
        return 'BAIXA'

    def definir_hipotese(row):
        h = []
        if row['Erro_Coord_00']: h.append("Perda de pacote GPS ou Área de Sombra")
        if row['Erro_Tempo_Basc_Alto']: h.append("Esquecimento de apontamento / Falha de fechamento")
        if row['Erro_Origem_Destino']: h.append("Geofence incorreta (Basculou na Carga)")
        if row['Erro_Dist_0']: h.append("Drift GPS / Odômetro inativo")
        if row['Erro_Trans_Manual_Auto']: h.append("Intervenção manual indevida")
        return " | ".join(h) if h else "Anomalia FMS"

    df_criticos = df[df['Tem_Erro']].copy()
    df_criticos['Severidade'] = df_criticos.apply(classificar_severidade, axis=1)
    df_criticos['Hipotese'] = df_criticos.apply(definir_hipotese, axis=1)
    eventos_prioritarios = df_criticos[df_criticos['Severidade'].isin(['ALTA', 'CRÍTICA'])].sort_values(by='Severidade')

    # =========================================================
    # 4. GERAÇÃO DO TEXTO DO RELATÓRIO
    # =========================================================
    linhas = []
    linhas.append("=" * 80)
    linhas.append("  RELATÓRIO MASTER DE DESEMPENHO, ADESÃO E AUDITORIA DE FROTAS")
    linhas.append("=" * 80)

    linhas.append("\n[ 1. RESUMO GERAL ]")
    linhas.append(f"Quantidade total de ciclos analisados  : {total_ciclos}")
    linhas.append(f"Quantidade de ciclos OK                : {ciclos_ok}")
    linhas.append(f"Quantidade de ciclos com ERRO/Anomalia : {ciclos_erro}")
    linhas.append(f"Quantidade de 'Basculou na Cava Sul'   : {qtd_cava_sul}")
    linhas.append("-" * 40)
    linhas.append(f"Ciclos 100% Automáticos (4 etapas)     : {df['Ciclo_100_Auto'].sum()}")
    linhas.append(f"Ciclos 100% Manuais (4 etapas)         : {df['Ciclo_100_Manual'].sum()}")
    linhas.append(f"Ciclos Mistos (Intervenção Parcial)    : {df['Ciclo_Misto'].sum()}")

    linhas.append("\n[ 2. MÉTRICAS DE QUALIDADE DA AUTOMAÇÃO ]")
    linhas.append(f"Taxa de Confiabilidade do Sistema      : {100 - perc_falhas:.2f}%")
    linhas.append(f"Taxa de Inconsistência Operacional     : {perc_falhas:.2f}%")
    linhas.append(f"Taxa de Falsos Positivos Estimada      : {perc_falsos_pos:.2f}%")
    linhas.append(f"Taxa de Perda GPS (Coordenada Zerada)  : {perc_coord_00:.2f}%")
    linhas.append(f"Taxa de Transição Manual -> Auto       : {perc_trans_man_aut:.2f}%")

    linhas.append("\n[ 3. PERCENTUAL DE AUTOMAÇÃO POR ETAPA DO CICLO ]")
    for col in cols_etapas:
        contagem = df[col].value_counts()
        total_etapa = contagem.sum()
        linhas.append(f"--- {col.upper()} ---")
        for status, qtd in contagem.items():
            perc = (qtd / total_etapa) * 100 if total_etapa > 0 else 0
            linhas.append(f"  > {status}: {qtd} apontamentos ({perc:.1f}%)")

    linhas.append("\n[ 4. RANKING DE ADESÃO DOS OPERADORES (Fim Basculamento) ]")
    linhas.append("> TOP 5: MAIS ACERTIVOS NO AUTOMÁTICO:")
    ranking_auto = df[df['Fim Basculamento'] == 'Automático'].groupby(['Operador', 'Caminhão']).size().sort_values(ascending=False).head(5)
    for (op, cam), qtd in ranking_auto.items():
        linhas.append(f"  [+] Operador: {op} | TAG: {cam} -> {qtd} ciclos")

    linhas.append("\n> TOP 5: MAIOR USO DO MODO MANUAL (Possível necessidade de reciclagem):")
    ranking_manual = df[df['Fim Basculamento'] == 'Manual'].groupby(['Operador', 'Caminhão']).size().sort_values(ascending=False).head(5)
    for (op, cam), qtd in ranking_manual.items():
        linhas.append(f"  [-] Operador: {op} | TAG: {cam} -> {qtd} ciclos")

    linhas.append("\n[ 5. ANÁLISE DE PADRÕES DETECTADOS ]")
    linhas.append(f"Distância Cheio = 0                    : {df['Erro_Dist_0'].sum()}")
    linhas.append(f"Origem igual ao Destino                : {df['Erro_Origem_Destino'].sum()}")
    linhas.append(f"Coordenadas 0,0                        : {df['Erro_Coord_00'].sum()}")
    linhas.append(f"Tempos incompatíveis (>15min basc)     : {df['Erro_Tempo_Basc_Alto'].sum()}")
    linhas.append(f"Troca Manual → Auto (fechamento)       : {df['Erro_Trans_Manual_Auto'].sum()}")

    linhas.append("\n[ 6. EVENTOS CRÍTICOS DETALHADOS E AUDITORIA ]")
    linhas.append("🚨 ATAQUE MANUTENÇÃO / AUTOMAÇÃO / OPERAÇÃO 🚨\n")

    erro_carga_tempo = df[(df['Fim Carga'] == 'Manual') & (df.get('Tempo Carregamento (min)', 0) > 15.0)]
    linhas.append("-> 6.1 Tempo de Carga Estourado (> 15 min) em MODO MANUAL (Esquecimento de tela):")
    if not erro_carga_tempo.empty:
        for _, r in erro_carga_tempo.head(5).iterrows():
            linhas.append(f"   ⏱️ {r['Caminhão']} (Esc: {r.get('Equipamento de Carga','N/A')}) | Op: {r['Operador']} | Início: {r.get('Hora Início','')}")
    else: linhas.append("   Nenhuma ocorrência.")

    erro_esq_basc = df[df.get('Tempo Basculamento (min)', 0) > 15.0]
    linhas.append("\n-> 6.2 Esquecimento de Tela na Descarga (Status Manual com Tempo Basculamento > 10 min):")
    if not erro_esq_basc.empty:
        for _, r in erro_esq_basc.head(5).iterrows():
            linhas.append(f"   ⏱️ {r['Caminhão']} | Op: {r['Operador']} | Início: {r.get('Hora Início','')} | Duração: {r.get('Tempo Basculamento (min)',0):.2f} min")
    else: linhas.append("   Nenhuma ocorrência.")

    linhas.append("\n-> 6.3 Ocorrências com Múltiplas Anomalias (ALTA/CRÍTICA):")
    if not eventos_prioritarios.empty:
        for _, row in eventos_prioritarios.head(15).iterrows():
            # Busca inteligente e dinâmica pelo link de rotas (independente do nome da coluna)
            link_mapa = next((str(v) for v in row.values if isinstance(v, str) and v.startswith('http')), 'Link indisponível no CSV')
            
            linhas.append(f"   [{row['Severidade']}] TAG: {row['Caminhão']} | Op: {row['Operador']} | Início: {row.get('Data Início','')} {row.get('Hora Início','')}")
            linhas.append(f"      - Hipótese: {row['Hipotese']}")
            linhas.append(f"      - Trajeto: {row['Origem']} -> {row['Destino']}")
            linhas.append(f"      - Dados: Basc({row.get('Tempo Basculamento (min)',0):.2f} min) | Dist({row.get('Distância Cheio (m)',0):.2f} m) | Coord({row.get('Latitude (Basculamento)',0)}, {row.get('Longitude (Basculamento)',0)})")
            linhas.append(f"      - Rota GPS: {link_mapa}")
            linhas.append("   " + "-"*40)
    else:
        linhas.append("   Nenhuma anomalia crítica severa identificada.")

    linhas.append("\n" + "=" * 80)
    linhas.append("Fim do Relatório Investigativo - Gerado Automaticamente")

    # =========================================================
    # 5. SALVAMENTO DO ARQUIVO
    # =========================================================
    agora = datetime.now().strftime("%d-%m-%Y_%H-%M")
    nome_arquivo = f'RELATORIO_MASTER_{agora}.txt'
    with open(nome_arquivo, 'w', encoding='utf-8') as f:
        f.write("\n".join(linhas))

    print(f"✅ Relatório Master gerado com sucesso: '{nome_arquivo}'")

if __name__ == '__main__':
    gerar_relatorio_master()
