# main.py

import sys
import os
import json
import matplotlib.pyplot as plt
import numpy as np
from typing import Any, Dict
import math

from matplotlib.patches import FancyArrowPatch

# Adiciona o diretório atual ao sys.path para importações locais
sys.path.append(os.path.dirname(__file__))

# Importações dos módulos do projeto
try:
    from dados import carrega_dados_json, Dados
    from alcione import resolva
    import utils 
    from solucao import Solucao
except ImportError as e:
    print(f"Erro de importação. Verifique se os arquivos estão presentes: {e}")
    sys.exit(1)

# --- Configuração ---
NOME_INSTANCIA = "pequena"
ARQUIVO_INSTANCIA = f"dados/{NOME_INSTANCIA}.json"
ARQUIVO_SOLUCAO = f"solucao_{NOME_INSTANCIA}.json"
NUMERO_AVALIACOES_MAX = 500

def executar_e_visualizar():
    print(f"*** Executando projeto para a instância: {NOME_INSTANCIA} ***")
    
    # 1. Carregar os dados da instância (classe Dados)
    try:
        dados: Dados = carrega_dados_json(ARQUIVO_INSTANCIA)
        print("Dados da instância carregados com sucesso (classe Dados).")
    except Exception as e:
        print(f"\nERRO ao carregar dados da instância: {e}")
        return

    # 2. Executar o algoritmo MACS
    print(f"\nIniciando otimização com MACS (max avaliações: {NUMERO_AVALIACOES_MAX})...")
    try:
        solucao_otima: Solucao = resolva(dados, NUMERO_AVALIACOES_MAX)
        print("\n--- Otimização Concluída ---")
        print(f"Custo Final (fx): {solucao_otima.fx:.2f}")
        print("Rotas Encontradas:")
        print(solucao_otima)
    except Exception as e:
        print(f"\nERRO durante a execução do MACS: {e}")
        return

    # 3. Salvar a Solução em Disco
    print(f"\nSalvando solução em disco: {ARQUIVO_SOLUCAO}")
    solucao_otima.salvar(ARQUIVO_SOLUCAO)
    
    # 4. Carregar Dados Brutos da Instância (para coordenadas)
    try:
        dados_json_brutos: Dict[str, Any] = utils.carregar_instancia(ARQUIVO_INSTANCIA)
        print("Dados brutos da instância carregados para plotagem.")
    except Exception as e:
        print(f"AVISO: Não foi possível carregar dados JSON brutos para plotagem: {e}")
        return
    
    # 5. Carregar a Solução do Disco (simulação de recuperação)
    solucao_recuperada = Solucao()
    solucao_recuperada.carregar(ARQUIVO_SOLUCAO)
    print("Solução recuperada do disco (simulação).")
    
    # 6. Plotar as Rotas (Lógica de visualização reimplementada no main.py)
    print("\nVisualizando o gráfico 2D do aeroporto com as rotas dos ônibus...")
    visualizar_rotas_solucao_integrada(solucao_recuperada, dados_json_brutos, NOME_INSTANCIA)

def visualizar_rotas_solucao_integrada(solucao: Solucao, dados_json: Dict[str, Any], nome_instancia: str, salvar: bool = False) -> None:
    """
    Gera visualização em facetas (subplots): Um gráfico separado para cada ônibus.
    """
    
    # Extração de dados
    coords = dados_json['coordenadas_pontos']
    N_req = dados_json['numeroRequisicoes']
    
    # --- 1. Mapeamento de Pontos (Geral) ---
    ponto_rota_coord = {0: tuple(coords['garagem'])}
    req_coleta_coord: Dict[int, Tuple[float, float]] = {}
    req_entrega_coord: Dict[int, Tuple[float, float]] = {}

    for i in range(N_req):
        req_id = i + 1
        req_coleta_coord[req_id] = tuple(coords['pontos_coleta'][i])
        req_entrega_coord[req_id] = tuple(coords['pontos_entrega'][i])

    # --- 2. Configuração da Grade de Subplots ---
    bus_ids = sorted(solucao.rota.keys())
    num_onibus = len(bus_ids)
    
    # Define colunas (ex: 2 ou 3 por linha) e calcula linhas necessárias
    ncols = 3 if num_onibus > 4 else 2
    nrows = math.ceil(num_onibus / ncols)
    
    # Ajusta o tamanho da figura baseado no número de plots
    fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 5 * nrows), constrained_layout=True)
    
    # Garante que axes seja sempre uma lista plana, mesmo se for 1x1
    if num_onibus == 1:
        axes_flat = [axes]
    else:
        axes_flat = axes.flatten()

    # --- Função Auxiliar para Plotar o Contexto Estático em cada Subplot ---
    def plotar_contexto_estatico(ax):
        # Garagem
        ax.plot(coords['garagem'][0], coords['garagem'][1], 'ks', markersize=8, label='Garagem', zorder=1)
        
        # Portões
        portoes_x = [p[0] for p in coords['portoes']]
        portoes_y = [p[1] for p in coords['portoes']]
        ax.plot(portoes_x, portoes_y, 'co', markersize=5, alpha=0.15, zorder=0)
        
        # Aeronaves
        aeronaves_x = [p[0] for p in coords['posicoes_aeronaves']]
        aeronaves_y = [p[1] for p in coords['posicoes_aeronaves']]
        ax.plot(aeronaves_x, aeronaves_y, 'r*', markersize=6, alpha=0.2, zorder=0)
        
        # Pontos de Coleta (Círculos Azuis - todos, para contexto)
        col_coords_x = [req_coleta_coord[i][0] for i in req_coleta_coord.keys()]
        col_coords_y = [req_coleta_coord[i][1] for i in req_coleta_coord.keys()]
        ax.plot(col_coords_x, col_coords_y, 'bo', markersize=4, alpha=0.1, zorder=0)

        # Entrega (Diamante - todos, para contexto)
        ent_coords_x = [req_entrega_coord[i][0] for i in req_entrega_coord.keys()]
        ent_coords_y = [req_entrega_coord[i][1] for i in req_entrega_coord.keys()]
        ax.plot(ent_coords_x, ent_coords_y, 'mD', markersize=4, alpha=0.1, zorder=0)

    # Cores para distinguir visualmente (opcional, já que estão separados)
    cmap_cores = plt.get_cmap('tab10', num_onibus + 1)

    # --- 3. Iteração por Faceta (Ônibus) ---
    for idx, ax in enumerate(axes_flat):
        if idx < num_onibus:
            k = bus_ids[idx]  # ID do ônibus atual
            cor_onibus = cmap_cores(idx)
            
            # Plota o fundo (aeroporto)
            plotar_contexto_estatico(ax)
            
            viagens = solucao.rota[k]
            tem_rota = False

            # --- Lógica de Rota Específica do Ônibus K ---
            for v, rota in viagens.items():
                if not rota or len(rota) <= 1:
                    continue
                
                tem_rota = True
                
                # Garante a rota completa
                rota_original = rota.copy()
                if rota_original[-1] != 0:
                    rota_original.append(0)
                
                # --- Reconstrução da Rota ---
                ponto_atual = 0 
                for req_destino_id in rota_original[1:]:
                    coord_origem = (0,0)
                    coord_destino = (0,0)
                    
                    # Lógica simplificada de reconstrução para plotagem
                    # Se não é 0, o destino é um Ponto de Coleta
                    if req_destino_id != 0:
                        # Arco Viagem: Ponto Atual (Origem ou D anterior) -> P (Coleta Atual)
                        coord_origem = ponto_rota_coord[0] if ponto_atual == 0 else req_entrega_coord[ponto_atual]
                        coord_destino = req_coleta_coord[req_destino_id]
                        
                        # Plota arco até a COLETA
                        seta = FancyArrowPatch(
                            coord_origem, coord_destino,
                            connectionstyle=f'arc3,rad=0.2',
                            color=cor_onibus, linewidth=2, arrowstyle='-|>', mutation_scale=10, alpha=0.8, zorder=3
                        )
                        ax.add_patch(seta)
                        
                        # Plota arco da COLETA para ENTREGA (P -> D)
                        seta_interna = FancyArrowPatch(
                            req_coleta_coord[req_destino_id], req_entrega_coord[req_destino_id],
                            connectionstyle=f'arc3,rad=0.1',
                            color=cor_onibus, linewidth=1.5, linestyle='--', arrowstyle='-|>', mutation_scale=8, alpha=0.8, zorder=3
                        )
                        ax.add_patch(seta_interna)
                        
                        # Destaca os pontos visitados especificamente por este ônibus
                        ax.plot(req_coleta_coord[req_destino_id][0], req_coleta_coord[req_destino_id][1], 'bo', markersize=6, alpha=1.0, zorder=4)
                        ax.plot(req_entrega_coord[req_destino_id][0], req_entrega_coord[req_destino_id][1], 'mD', markersize=6, alpha=1.0, zorder=4)
                        
                        ponto_atual = req_destino_id

                    elif req_destino_id == 0 and ponto_atual != 0:
                        # Retorno à Garagem: D anterior -> 0
                        coord_origem = req_entrega_coord[ponto_atual]
                        coord_destino = ponto_rota_coord[0]
                        
                        seta = FancyArrowPatch(
                            coord_origem, coord_destino,
                            connectionstyle=f'arc3,rad=0.2',
                            color='gray', linewidth=1, linestyle=':', arrowstyle='-|>', mutation_scale=10, alpha=0.5, zorder=2
                        )
                        ax.add_patch(seta)
                        ponto_atual = 0

            # Configurações do Subplot
            ax.set_title(f'Ônibus {k}', fontsize=10, fontweight='bold', color='black')
            ax.set_xticks([])
            ax.set_yticks([])
            ax.grid(True, alpha=0.2)
            
            if not tem_rota:
                ax.text(0.5, 0.5, "Sem Rota", ha='center', va='center', transform=ax.transAxes, color='red')

        else:
            # Oculta subplots vazios (se houver mais espaço na grade que ônibus)
            ax.axis('off')

    # Título Global
    fig.suptitle(f'Rotas por Veículo - Instância {nome_instancia.capitalize()}', fontsize=14)
    
    # Legenda Global (Cria elementos falsos para a legenda)
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='s', color='w', markerfacecolor='k', label='Garagem'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='b', label='Coleta (P)'),
        Line2D([0], [0], marker='D', color='w', markerfacecolor='m', label='Entrega (D)'),
        Line2D([0], [0], color='gray', lw=2, label='Rota'),
        Line2D([0], [0], color='gray', lw=1.5, linestyle='--', label='Serviço (P->D)')
    ]
    fig.legend(handles=legend_elements, loc='lower center', ncol=5, bbox_to_anchor=(0.5, 0.01))

    # Plotar as Rotas Encontradas no Canto Inferior Esquerdo
    route_text = str(solucao) 
    
    ax.text(0.02, 0.02,                   
            "Rotas Encontradas:\n" + route_text,
            transform=ax.transAxes,       
            fontsize=9,
            verticalalignment='bottom',   
            horizontalalignment='left',   
            bbox=dict(boxstyle="round,pad=0.5", facecolor='lightgray', alpha=0.9, edgecolor='black'),
            zorder=20
           )

    if salvar:
        plt.savefig(f'rotas_facetas_{nome_instancia}.png', dpi=300, bbox_inches='tight')
    plt.show()

if __name__ == "__main__":
    executar_e_visualizar()