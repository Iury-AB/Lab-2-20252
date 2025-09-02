#!/usr/bin/env python3
"""
Analisador e Visualizador de Instâncias do Problema de Embarque Remoto

Este script analisa e visualiza os dados das instâncias geradas para o problema
de otimização do serviço de embarque remoto de aeroporto.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pandas as pd

def carregar_instancia(nome_arquivo):
    """Carrega uma instância do arquivo JSON."""
    with open(nome_arquivo, 'r', encoding='utf-8') as f:
        return json.load(f)

def analisar_instancia(dados, nome_instancia):
    """Análise detalhada de uma instância."""
    print(f"\n=== ANÁLISE DA INSTÂNCIA: {nome_instancia.upper()} ===")
    
    # Informações básicas
    n = dados['numeroRequisicoes']
    K = dados['numeroOnibus']
    Dmax = dados['distanciaMaxima']
    
    print(f"Número de requisições: {n}")
    print(f"Número de ônibus: {K}")
    print(f"Distância máxima por viagem: {Dmax:.2f}m")
    
    # Análise dos voos
    voos = dados['detalhes_voos']
    print(f"Número de voos: {len(voos)}")
    
    passageiros_total = sum(v['n_passageiros'] for v in voos)
    passageiros_medio = passageiros_total / len(voos)
    
    embarques = [v for v in voos if v['tipo'] == 'embarque']
    desembarques = [v for v in voos if v['tipo'] == 'desembarque']
    
    print(f"Passageiros total: {passageiros_total}")
    print(f"Passageiros por voo (média): {passageiros_medio:.1f}")
    print(f"Embarques: {len(embarques)}, Desembarques: {len(desembarques)}")
    
    # Análise temporal
    e = np.array(dados['inicioJanela'])
    l = np.array(dados['fimJanela'])
    
    print(f"Janela de tempo mais cedo: {e.min():.1f} min")
    print(f"Janela de tempo mais tarde: {l.max():.1f} min")
    print(f"Duração total da operação: {l.max() - e.min():.1f} min")
    
    # Análise de distâncias
    D = np.array(dados['distanciaRequisicoes'])
    distancias_nao_zero = D[D > 0]
    
    print(f"Distância média entre requisições: {distancias_nao_zero.mean():.2f}m")
    print(f"Distância máxima entre requisições: {distancias_nao_zero.max():.2f}m")
    print(f"Distância mínima entre requisições: {distancias_nao_zero.min():.2f}m")
    
    # Análise de tempos de serviço
    s = np.array(dados['tempoServico'])
    print(f"Tempo de serviço médio: {s[1:].mean():.2f} min")  # excluir garagem
    print(f"Tempo de reabastecimento (garagem): {s[0]:.2f} min")
    
    return {
        'nome': nome_instancia,
        'requisicoes': n,
        'onibus': K,
        'voos': len(voos),
        'passageiros_total': passageiros_total,
        'duracao_operacao': l.max() - e.min(),
        'distancia_media': distancias_nao_zero.mean(),
        'tempo_servico_medio': s[1:].mean()
    }

def visualizar_layout_aeroporto(dados, nome_instancia):
    """Visualiza o layout do aeroporto com as posições dos pontos."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    
    coords = dados['coordenadas_pontos']
    
    # Garagem
    garagem = coords['garagem']
    ax.plot(garagem[0], garagem[1], 'ks', markersize=15, label='Garagem')
    
    # Portões
    portoes = coords['portoes']
    portoes_x = [p[0] for p in portoes]
    portoes_y = [p[1] for p in portoes]
    ax.plot(portoes_x, portoes_y, 'bo', markersize=8, label='Portões de Embarque')
    
    # Posições de aeronaves
    aeronaves = coords['posicoes_aeronaves']
    aeronaves_x = [p[0] for p in aeronaves]
    aeronaves_y = [p[1] for p in aeronaves]
    ax.plot(aeronaves_x, aeronaves_y, 'r^', markersize=8, label='Posições de Aeronaves')
    
    # Pontos de coleta e entrega das requisições
    coletas = coords['pontos_coleta']
    entregas = coords['pontos_entrega']
    
    for i, (coleta, entrega) in enumerate(zip(coletas, entregas)):
        # Linha conectando coleta e entrega da mesma requisição
        ax.plot([coleta[0], entrega[0]], [coleta[1], entrega[1]], 
                'g-', alpha=0.3, linewidth=1)
    
    ax.set_xlabel('Posição X (metros)')
    ax.set_ylabel('Posição Y (metros)')
    ax.set_title(f'Layout do Aeroporto - Instância {nome_instancia.capitalize()}')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.axis('equal')
    
    plt.tight_layout()
    plt.savefig(f'layout_aeroporto_{nome_instancia}.png', dpi=300, bbox_inches='tight')
    plt.show()

def visualizar_janelas_tempo(dados, nome_instancia):
    """Visualiza as janelas de tempo das requisições."""
    e = np.array(dados['inicioJanela'])
    l = np.array(dados['fimJanela'])
    
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    
    # Criar gráfico de barras horizontais para as janelas de tempo
    requisicoes = range(1, len(e) + 1)
    duracao = l - e
    
    bars = ax.barh(requisicoes, duracao, left=e, alpha=0.7, 
                   color='skyblue', edgecolor='darkblue')
    
    ax.set_xlabel('Tempo (minutos)')
    ax.set_ylabel('Requisição')
    ax.set_title(f'Janelas de Tempo das Requisições - Instância {nome_instancia.capitalize()}')
    ax.grid(True, alpha=0.3, axis='x')
    
    # Converter tempo em horas para melhor legibilidade
    ax2 = ax.twiny()
    ax2.set_xlim(ax.get_xlim())
    tick_locations = ax.get_xticks()
    ax2.set_xticks(tick_locations)
    ax2.set_xticklabels([f'{t/60:.1f}h' for t in tick_locations])
    ax2.set_xlabel('Tempo (horas)')
    
    plt.tight_layout()
    plt.savefig(f'janelas_tempo_{nome_instancia}.png', dpi=300, bbox_inches='tight')
    plt.show()

def gerar_relatorio_comparativo(todas_analises):
    """Gera um relatório comparativo de todas as instâncias."""
    df = pd.DataFrame(todas_analises)
    
    print("\n" + "="*80)
    print("RELATÓRIO COMPARATIVO DAS INSTÂNCIAS")
    print("="*80)
    
    print("\nResumo Quantitativo:")
    print(df.to_string(index=False, float_format='%.2f'))
    
    # Análise de eficiência
    print("\nAnálise de Eficiência:")
    df['requisicoes_por_onibus'] = df['requisicoes'] / df['onibus']
    df['passageiros_por_onibus'] = df['passageiros_total'] / df['onibus']
    df['utilizacao_tempo'] = df['duracao_operacao'] / (8 * 60)  # assumindo 8h como dia de trabalho
    
    for _, row in df.iterrows():
        print(f"\n{row['nome'].upper()}:")
        print(f"  - Requisições por ônibus: {row['requisicoes_por_onibus']:.1f}")
        print(f"  - Passageiros por ônibus: {row['passageiros_por_onibus']:.0f}")
        print(f"  - Utilização do tempo de operação: {row['utilizacao_tempo']:.1%}")
    
    # Gráfico comparativo
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    
    # Gráfico 1: Requisições vs Ônibus
    ax1.bar(df['nome'], df['requisicoes'], color='lightblue', alpha=0.7)
    ax1_twin = ax1.twinx()
    ax1_twin.plot(df['nome'], df['onibus'], 'ro-', markersize=8, linewidth=2)
    ax1.set_ylabel('Número de Requisições', color='blue')
    ax1_twin.set_ylabel('Número de Ônibus', color='red')
    ax1.set_title('Requisições vs Ônibus por Instância')
    ax1.tick_params(axis='x', rotation=45)
    
    # Gráfico 2: Passageiros totais
    ax2.bar(df['nome'], df['passageiros_total'], color='lightgreen', alpha=0.7)
    ax2.set_ylabel('Passageiros Totais')
    ax2.set_title('Total de Passageiros por Instância')
    ax2.tick_params(axis='x', rotation=45)
    
    # Gráfico 3: Duração da operação
    ax3.bar(df['nome'], df['duracao_operacao']/60, color='lightyellow', alpha=0.7)
    ax3.set_ylabel('Duração (horas)')
    ax3.set_title('Duração da Operação por Instância')
    ax3.tick_params(axis='x', rotation=45)
    
    # Gráfico 4: Eficiência (requisições por ônibus)
    ax4.bar(df['nome'], df['requisicoes_por_onibus'], color='lightcoral', alpha=0.7)
    ax4.set_ylabel('Requisições por Ônibus')
    ax4.set_title('Eficiência: Requisições por Ônibus')
    ax4.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig('relatorio_comparativo_instancias.png', dpi=300, bbox_inches='tight')
    plt.show()

def main():
    """Função principal do analisador."""
    instancias = ['pequena', 'media', 'grande', 'rush']
    todas_analises = []
    
    print("ANALISADOR DE INSTÂNCIAS - EMBARQUE REMOTO DE AEROPORTO")
    print("="*60)
    
    for nome in instancias:
        arquivo = f'instancia_aeroporto_{nome}.json'
        try:
            dados = carregar_instancia(arquivo)
            analise = analisar_instancia(dados, nome)
            todas_analises.append(analise)
            
            # Gerar visualizações para instância média (representativa)
            if nome == 'media':
                print(f"\nGerando visualizações para instância {nome}...")
                visualizar_layout_aeroporto(dados, nome)
                visualizar_janelas_tempo(dados, nome)
                
        except FileNotFoundError:
            print(f"Arquivo {arquivo} não encontrado!")
    
    if todas_analises:
        gerar_relatorio_comparativo(todas_analises)
    
    print("\nAnálise concluída! Arquivos de visualização salvos.")

if __name__ == "__main__":
    main()
