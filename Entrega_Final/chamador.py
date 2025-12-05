# main.py

import sys
import os
import json
import matplotlib.pyplot as plt
import numpy as np
from typing import Any, Dict

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
    Gera visualização 2D completa das rotas, removendo rótulos e alterando o marcador 
    de Entrega (D) para Diamante, resolvendo a ambiguidade com Aeronaves.
    """
    
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    
    # Extração de dados
    coords = dados_json['coordenadas_pontos']
    N_req = dados_json['numeroRequisicoes']
    
    # --- 1. Mapeamento de Pontos ---
    ponto_rota_coord = {0: tuple(coords['garagem'])}
    req_coleta_coord: Dict[int, Tuple[float, float]] = {}
    req_entrega_coord: Dict[int, Tuple[float, float]] = {}

    for i in range(N_req):
        req_id = i + 1
        req_coleta_coord[req_id] = tuple(coords['pontos_coleta'][i])
        req_entrega_coord[req_id] = tuple(coords['pontos_entrega'][i])

    # --- 2. Plotagem do Layout Estático (Contexto) ---
    
    ax.plot(coords['garagem'][0], coords['garagem'][1], 'ks', markersize=12, label='Garagem', zorder=12)
    
    portoes_x = [p[0] for p in coords['portoes']]
    portoes_y = [p[1] for p in coords['portoes']]
    ax.plot(portoes_x, portoes_y, 'co', markersize=8, alpha=0.3, label='Portões (Geral)', zorder=1)
    
    # Aeronaves (Estrela - Mantido)
    aeronaves_x = [p[0] for p in coords['posicoes_aeronaves']]
    aeronaves_y = [p[1] for p in coords['posicoes_aeronaves']]
    ax.plot(aeronaves_x, aeronaves_y, 'r*', markersize=10, label='Aeronaves (Geral)', zorder=1)
    
    # Pontos de Coleta (Círculos Azuis)
    col_coords_x = [req_coleta_coord[i][0] for i in req_coleta_coord.keys()]
    col_coords_y = [req_coleta_coord[i][1] for i in req_coleta_coord.keys()]
    ax.plot(col_coords_x, col_coords_y, 'bo', markersize=8, alpha=0.6, label='Coleta (P)', zorder=12)

    # CORREÇÃO: Entrega (Diamante - Distinto de Aeronaves)
    ent_coords_x = [req_entrega_coord[i][0] for i in req_entrega_coord.keys()]
    ent_coords_y = [req_entrega_coord[i][1] for i in req_entrega_coord.keys()]
    ax.plot(ent_coords_x, ent_coords_y, 'mD', markersize=8, alpha=0.6, label='Entrega (D)', zorder=12)
    
    # --- 3. Plotagem das Rotas (Duplicação e Reconstrução do Caminho) ---
    
    num_onibus = len(solucao.rota.keys())
    cores = plt.get_cmap('hsv', num_onibus + 1)
    
    linhas_plottadas = {} 
        
    for k, viagens in solucao.rota.items():
        cor_onibus = cores(k)
        
        for v, rota in viagens.items():
            if not rota or len(rota) <= 1:
                continue
            
            # Garante a rota completa, incluindo o retorno à garagem
            rota_original = rota.copy()
            if rota_original[-1] != 0:
                rota_original.append(0)
            
            # --- Reconstrução da Rota com Eventos P e D ---
            rota_eventos = []
            ponto_atual = 0 
            
            for req_destino_id in rota_original[1:]:
                if req_destino_id != 0:
                    # 1. Arco de Coleta (P): Arco de Viagem X -> P_i
                    coord_p1 = ponto_rota_coord[ponto_atual] if ponto_atual == 0 else req_entrega_coord.get(ponto_atual, (0, 0))
                    coord_p2 = req_coleta_coord[req_destino_id]
                    
                    rota_eventos.append({'origem_id': ponto_atual, 'destino_id': req_destino_id, 'tipo': 'P', 'coord_p1': coord_p1, 'coord_p2': coord_p2})
                    
                    # 2. Arco de Entrega (D): Arco de Evento P_i -> D_i
                    rota_eventos.append({'origem_id': req_destino_id, 'destino_id': req_destino_id, 'tipo': 'D', 'coord_p1': req_coleta_coord[req_destino_id], 'coord_p2': req_entrega_coord[req_destino_id]})
                    
                    ponto_atual = req_destino_id
                
                elif req_destino_id == 0 and ponto_atual != 0:
                    # 3. Retorno à Garagem (0): Arco de D_anterior -> 0
                    rota_eventos.append({'origem_id': ponto_atual, 'destino_id': 0, 'tipo': 'G', 'coord_p1': req_entrega_coord.get(ponto_atual, (0, 0)), 'coord_p2': ponto_rota_coord[0]})
                    ponto_atual = 0

            # --- Plotar os Arcos Reconstruídos ---
            
            for i, evento in enumerate(rota_eventos):
                p1 = evento['coord_p1']
                p2 = evento['coord_p2']
                
                # 2. Definir Parâmetros Geométricos
                curvatura_rad = 0.2 + (k * 0.02)
                
                # FancyArrowPatch desenha o arco e a seta na ponta
                seta_arco = FancyArrowPatch(
                    p1, p2, 
                    connectionstyle=f'arc3,rad={curvatura_rad}',
                    color=cor_onibus, 
                    linewidth=3, 
                    arrowstyle='-|>', 
                    mutation_scale=15, 
                    alpha=0.6,
                    zorder=3
                )
                ax.add_patch(seta_arco)
            
                # --- Rótulos (Texto) Removidos ---
            
            # --- Adicionar Legenda Única para Rota do Ônibus ---
            if k not in linhas_plottadas:
                ax.plot([], [], color=cor_onibus, linewidth=3, alpha=0.6, label=f'Rota Ônibus {k}', zorder=3)
                linhas_plottadas[k] = True

    # 4. Configuração final do gráfico
    ax.set_xlabel('Posição X (metros)')
    ax.set_ylabel('Posição Y (metros)')
    ax.set_title(f'Rotas Otimizadas (Arqueadas) - Instância {nome_instancia.capitalize()}')
    
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

    ax.legend(loc='upper right', fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.axis('equal')
    
    plt.tight_layout()
    if salvar:
        plt.savefig(f'rotas_finais_{nome_instancia}.png', dpi=300, bbox_inches='tight')
    plt.show()

if __name__ == "__main__":
    executar_e_visualizar()