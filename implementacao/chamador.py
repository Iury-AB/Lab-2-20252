import json
import numpy as np
import os
import time
import random
import matplotlib.pyplot as plt
import copy 
from typing import Dict, Any, Tuple, Optional

# --- CORREÇÃO DE IMPORTAÇÃO PARA PACOTE (Para ambientes de teste) ---
# Adiciona o diretório do script atual ao path do Python para que os módulos sejam encontrados
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# ------------------------------

# Agora os módulos alcione e aco devem ser encontrados como parte do pacote
import alcione
import aco 
from exemplo_prof.dados import carrega_dados_json
from exemplo_prof.solucao import Solucao

# --- Variáveis do Protocolo ---
ARQUIVO_JSON = "media.json" 
NOME_GRUPO = aco.NOME_GRUPO
MAX_EXECUCOES = 30
MAX_STAGNATION_ITERS = 5 # Não é mais usado diretamente pelo alcione, mas mantido para contexto
# O N_evals será calculado a partir dos dados

# --- FUNÇÕES DE PERSISTÊNCIA DE ESTADO ---

def salvar_solucao_json(sol: Solucao, filename: str):
    """Salva a solução final formatada (fx, onibus) em um arquivo JSON."""
    if sol.fx < float('inf') and sol.fx > 0:
        output = {
            "fx": sol.fx,
            "onibus": {
                str(k): {
                    f"viagem_{v}": {"rota": r, "chegada": c}
                    for v, (r, c) in zip(sol.rota[k].keys(), zip(sol.rota[k].values(), sol.chegada[k].values()))
                }
                for k in sol.rota.keys() if sol.rota[k]
            }
        }
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)

def salvar_estado_global(feromonio_map: np.ndarray, melhor_solucao_dict: Optional[Dict], instance_name: str, nome_grupo: str):
    """Salva o mapa de feromônio e a melhor solução persistente."""
    feromonio_filename = f"feromonio_persist_{instance_name}_{nome_grupo}.npy"
    solucao_filename = f"melhor_solucao_persist_{instance_name}_{nome_grupo}.json"
    
    try:
        np.save(feromonio_filename, feromonio_map)
    except Exception as e:
        print(f"Erro ao salvar o mapa de feromônio: {e}", flush=True)

    if melhor_solucao_dict is not None:
        dict_to_save = copy.deepcopy(melhor_solucao_dict)
        try:
            with open(solucao_filename, 'w') as f:
                json.dump(dict_to_save, f, indent=2)
        except Exception as e:
            print(f"Erro ao salvar a melhor solução persistente: {e}", flush=True)
            
def salvar_contador_estagnacao(contador_valor: int, instance_name: str, nome_grupo: str):
    """Salva o contador de estagnação."""
    filename = f"stagnation_count_persist_{instance_name}_{nome_grupo}.txt"
    try:
        with open(filename, 'w') as f:
            f.write(str(contador_valor))
    except Exception as e:
        print(f"Erro ao salvar contador de estagnação: {e}", flush=True)

def carregar_contador_estagnacao(instance_name: str, nome_grupo: str) -> int:
    """Carrega o contador de estagnação, retornando 0 se não encontrar."""
    filename = f"stagnation_count_persist_{instance_name}_{nome_grupo}.txt"
    try:
        with open(filename, 'r') as f:
            return int(f.read().strip())
    except FileNotFoundError:
        return 0
    except ValueError:
        return 0
    except Exception as e:
        print(f"Aviso: Falha ao carregar contador de estagnação. Resetando para 0. Erro: {e}", flush=True)
        return 0
    
def carregar_estado_global(instance_name: str, nome_grupo: str) -> Tuple[Optional[np.ndarray], Optional[Dict]]:
    """Carrega o mapa de feromônio e a melhor solução persistente."""
    feromonio_filename = f"feromonio_persist_{instance_name}_{nome_grupo}.npy"
    solucao_filename = f"melhor_solucao_persist_{instance_name}_{nome_grupo}.json"
    
    feromonio_map = None
    solucao_dict = None
    
    try:
        feromonio_map = np.load(feromonio_filename)
        print(f"-> Estado: Mapa de Feromônio carregado de {feromonio_filename}", flush=True)
    except FileNotFoundError: pass
    except Exception as e:
        print(f"Aviso: Falha ao carregar o feromônio. Iniciando do zero. Erro: {e}", flush=True)
        
    try:
        with open(solucao_filename, 'r') as f:
            solucao_dict = json.load(f)
            print(f"-> Estado: Melhor Solução persistente carregada de {solucao_filename}", flush=True)
    except FileNotFoundError: pass
    except json.JSONDecodeError:
        print("Aviso: Falha ao decodificar o JSON da melhor solução persistente. Continuando sem ela.", flush=True)
        pass
        
    return feromonio_map, solucao_dict


# --- BLOCO PRINCIPAL DE TESTES (30 EXECUÇÕES) ---
if __name__ == "__main__":
    try:
        # Define a semente para reprodutibilidade
        random.seed(42) 
        np.random.seed(42)
        
        instance_name = ARQUIVO_JSON.split('.')[0]
        
        # 1. Carrega os dados
        data_path = os.path.join("dados", ARQUIVO_JSON)
        dados = carrega_dados_json(data_path)
        
        # 2. Calcula N_evals
        N_evals = 10 * dados.n * dados.K * dados.r 
        
        print(f"--- Teste de {MAX_EXECUCOES} Execuções ({ARQUIVO_JSON}) ---", flush=True)
        print(f"Limite de Avaliações (Nmar = 10*n*K*r): {N_evals}", flush=True)
        print(f"-> PERSISTÊNCIA ATIVA para {instance_name}_{NOME_GRUPO} <-\n", flush=True)

        historico_custos = []
        melhor_global_custo_persistente = float('inf')
        melhor_global_solucao_dict_persistente = None
        feromonio_map_persistente = None
        melhor_global_custo_cumulativo = float('inf')
        historico_cumulativo = []
        
        TOLERANCIA_CUSTO = 1e-4
        
        # 3. Carrega o estado global antes de tudo
        feromonio_map_persistente, melhor_global_solucao_dict_persistente = carregar_estado_global(instance_name, NOME_GRUPO)
        stagnation_counter = carregar_contador_estagnacao(instance_name, NOME_GRUPO)
        
        # Inicializa parâmetros base para exibição e reset
        base_params = aco.PARAMS_BASE.copy()
        base_params.update(aco.OPTIMIZED_PARAMS_MAP.get(instance_name, {}))
        
        if melhor_global_solucao_dict_persistente:
             # CORREÇÃO BLINDADA: Verifica se 'fx' existe e não é None
             if 'fx' in melhor_global_solucao_dict_persistente and melhor_global_solucao_dict_persistente['fx'] is not None:
                 melhor_global_custo_persistente = float(melhor_global_solucao_dict_persistente['fx'])
             else:
                 melhor_global_custo_persistente = float('inf')

             print(f"-> Estado: Custo Global Inicial (Carregado): {melhor_global_custo_persistente:.2f}", flush=True)
             
             # Exibição do contador (corrigida para usar a constante)
             print(f"-> Contador de Estagnação (Carregado): {stagnation_counter}/{MAX_STAGNATION_ITERS}", flush=True) 
             
             # NOVO: Carrega T_INICIAL para exibição
             T_inicial_loaded = melhor_global_solucao_dict_persistente.get('temperatura_inicial', base_params.get('temperatura_inicial', aco.T_INICIAL_BASE))
             print(f"-> Temperatura SA (Inicial da Instância): {T_inicial_loaded:.2f}", flush=True)
             print(f"-> Temperatura SA (Atual Carregada): {melhor_global_solucao_dict_persistente.get('temperatura', T_inicial_loaded):.2f}", flush=True)

             # Parâmetros ACO (apenas os essenciais, sem ILS/SA)
             print(f"-> Parâmetros ACO (Carregado): Alpha={melhor_global_solucao_dict_persistente.get('alpha', base_params['alpha']):.2f}, Beta={melhor_global_solucao_dict_persistente.get('beta', base_params['beta']):.2f}, Rho={melhor_global_solucao_dict_persistente.get('rho', base_params['rho']):.2f}\n", flush=True)
        else:
             T_inicial_default = base_params.get('temperatura_inicial', aco.T_INICIAL_BASE)
             print(f"-> Estado: Custo Global Inicial (Base Otimizada): {melhor_global_custo_persistente:.2f}", flush=True)
             print(f"-> Contador de Estagnação (Inicial): 0/{MAX_STAGNATION_ITERS}", flush=True)
             print(f"-> Temperatura SA (Inicial da Instância): {T_inicial_default:.2f}", flush=True)
             
        
        # Garante que o dicionário de uso inicial reflita os defaults otimizados se não houver persistência completa
        if melhor_global_solucao_dict_persistente is None:
             melhor_global_solucao_dict_persistente = {'fx': melhor_global_custo_persistente}
             melhor_global_solucao_dict_persistente.update(base_params)


        # 4. Loop de Execuções
        for i in range(1, MAX_EXECUCOES + 1):
            t_inicio = time.time()
            
            feromonio_uso = feromonio_map_persistente
            solucao_dict_uso = melhor_global_solucao_dict_persistente
            
            # --- Lógica de Reset de Estado (Simplificada) ---
            should_reset = False
            if i == 1 and melhor_global_custo_persistente < float('inf'):
                 print("-> AJUSTE: Ignorando estado persistente para a Execução 01 (Início do Teste de 30).", flush=True)
                 should_reset = True
            
            # A lógica de reset por estagnação foi removida: o ACO Puro sempre reinicia com a persistência.
            # Caso o usuário force o reset, ele deve deletar os arquivos.

            if should_reset:
                 feromonio_uso = None 
                 stagnation_counter = 0 
                 
                 # Recria o dicionário de uso com os defaults otimizados da INSTÂNCIA
                 reset_params = aco.PARAMS_BASE.copy()
                 reset_params.update(aco.OPTIMIZED_PARAMS_MAP.get(instance_name, {}))
                 solucao_dict_uso = reset_params
                 solucao_dict_uso['fx'] = float('inf') # Começa do zero
                 solucao_dict_uso['temperatura'] = reset_params.get('temperatura_inicial', aco.T_INICIAL_BASE) # Reseta a temperatura

            # Chama resolva (função do alcione.py).
            sol, feromonio_map_final, melhor_solucao_dict_final = alcione.resolva(
                dados, 
                N_evals, 
                initial_feromonio=feromonio_uso, 
                initial_solucao_dict=solucao_dict_uso,
                stagnation_counter=stagnation_counter
            )
            
            duracao = time.time() - t_inicio
            
            # 5. Pós-Processamento e Persistência
            # O contador de estagnação e temperatura são mantidos dentro do solucao_dict_final
            current_stagnation = melhor_solucao_dict_final.get('stagnation_counter', 0)
            
            if sol and sol.fx > 0 and sol.fx < float('inf'):
                is_valid = sol.factivel(dados, False) 
                valid_tag = "VALID" if is_valid else "INVALID"
                
                debug_info = getattr(sol, 'debug_info', {})
                total_avaliacoes = debug_info.get('total_avaliacoes', 'N/A')
                total_movimentos_vnd = debug_info.get('total_movimentos_vnd', 'N/A')
                log_calibracao = debug_info.get('log_calibracao', [])
                
                # Exibindo Movimentos VND para calibração
                print(f"Exec {i:02d}: Custo = {sol.fx:.2f} | FX Contado = {total_avaliacoes} | VND Movs. = {total_movimentos_vnd} | Tempo = {duracao:.2f}s | Status: {valid_tag}", flush=True)

                # Se houver log de calibração, exibe (somente para a primeira execução do teste)
                if i == 1 and log_calibracao:
                    print("\n--- DETALHES DA CALIBRAÇÃO (Execução 01) ---", flush=True)
                    for entry in log_calibracao:
                        print(f"  [Iter {entry['iter']:<4} | Nmar: {entry['avaliacoes_aco_total']:<5}] FX {entry['fx_final']:.2f} (Origem: {entry['origem_construcao']}) - Melhoria VND: {entry['melhoria_vnd']:.2f} ({entry['movimentos_vnd_passo']} Movs.)", flush=True)
                    print("--------------------------------------------------\n", flush=True)
                
                if is_valid:
                    historico_custos.append(sol.fx)
                    
                    final_fx = melhor_solucao_dict_final['fx'] if 'fx' in melhor_solucao_dict_final else float('inf')
                    final_is_new_global = final_fx < melhor_global_custo_persistente - TOLERANCIA_CUSTO
                    
                    # 5A. Atualização da Persistência
                    if final_is_new_global: 
                        print("  -> 🏆 NOVA MELHOR SOLUÇÃO GLOBAL PERSISTENTE! SALVANDO ESTADO...", flush=True)
                        melhor_global_custo_persistente = sol.fx
                        
                        # Salva a nova melhor solução no arquivo
                        output_filename_json = f"melhor_solucao_aco_{instance_name}_{NOME_GRUPO}.json"
                        salvar_solucao_json(sol, output_filename_json)
                        
                    # O estado é sempre atualizado com a saída de 'resolva'
                    melhor_global_solucao_dict_persistente = melhor_solucao_dict_final
                    feromonio_map_persistente = feromonio_map_final
                    
                    # Salva o estado persistente para a próxima execução (i+1)
                    salvar_estado_global(feromonio_map_persistente, melhor_global_solucao_dict_persistente, instance_name, NOME_GRUPO)
                    salvar_contador_estagnacao(current_stagnation, instance_name, NOME_GRUPO)
                    stagnation_counter = current_stagnation
                    
                    # Atualiza o custo cumulativo para o gráfico
                    if sol.fx < melhor_global_custo_cumulativo:
                         melhor_global_custo_cumulativo = sol.fx
                    historico_cumulativo.append(melhor_global_custo_cumulativo)


            else:
                print(f"Exec {i:02d}: Nenhuma solução válida encontrada ou infactível. Tempo = {duracao:.2f}s", flush=True)
                # O contador de estagnação é 0, mas atualizamos o feromônio com a melhor solução global conhecida
                feromonio_map_persistente = feromonio_map_final
                melhor_global_solucao_dict_persistente = melhor_solucao_dict_final
                
                # Atualiza o estado persistente mesmo em falha
                salvar_estado_global(feromonio_map_persistente, melhor_global_solucao_dict_persistente, instance_name, NOME_GRUPO)
                salvar_contador_estagnacao(current_stagnation, instance_name, NOME_GRUPO)
                stagnation_counter = current_stagnation


        # 6. Sumário e Gráfico
        if historico_custos:
            print("-" * 40, flush=True)
            print(f"Melhor Custo Global ({MAX_EXECUCOES} Execuções): {min(historico_custos):.2f}", flush=True)
            print(f"Média dos Custos ({MAX_EXECUCOES} Execuções): {sum(historico_custos)/len(historico_custos):.2f}", flush=True)
            print(f"Desvio Padrão ({MAX_EXECUCOES} Execuções): {np.std(historico_custos):.2f}", flush=True)
        else:
            print("Falha: Nenhuma solução válida encontrada.", flush=True)

        # Geração de Gráfico da Curva de Aprendizado (Exponencial)
        plt.figure(figsize=(10, 6))
        
        if historico_cumulativo:
            valid_indices = list(range(1, len(historico_cumulativo) + 1))
            plt.plot(valid_indices, historico_cumulativo, marker='o', linestyle='-', color='b')
            
            plt.title(f'Curva de Aprendizado - Melhor Custo Global Cumulativo - {ARQUIVO_JSON}')
            plt.xlabel('Execução do Algoritmo')
            plt.ylabel('Melhor Custo Global (FX)')
            plt.grid(True)
            
            output_filename_png = f'aco_curva_aprendizado_{instance_name}_{NOME_GRUPO}.png'
            plt.savefig(output_filename_png)
            print(f"\nGráfico da Curva de Aprendizado salvo em: {output_filename_png}", flush=True)
        
    except FileNotFoundError:
        print(f"Erro: Arquivo '{ARQUIVO_JSON}' não encontrado. Verifique o caminho 'dados/{ARQUIVO_JSON}'.", flush=True)
    except ImportError as e:
        print(f"Erro de Importação: Não foi possível importar o módulo necessário. Detalhe: {e}", flush=True)
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}", flush=True)