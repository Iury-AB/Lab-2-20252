import json
import numpy as np
import math
import random
import time
import copy
import os
from typing import Dict, Any, Tuple, List, Optional
# Assume que exemplo_prof.dados está acessível
from exemplo_prof.dados import Dados
from exemplo_prof.dados import carrega_dados_json
import matplotlib.pyplot as plt

# --- CLASSE SOLUCAO (Conforme especificado) ---
class Solucao:
    def __init__(self):
        self.rota = {}
        self.chegada = {}
        self.fx = 0.0

    def factivel(self, dados, verbose=False):
        """
        Verifica se a solução é factível. (Sua função completa)
        """
        K_range = range(1, dados.K + 1)
        V_range = range(1, dados.r + 1)
        N = list(range(1, dados.n + 1)) # Lista de reqs a serem checadas
        N_atendidas_total = set() # Para checar duplicadas (embora o N.remove() já faça isso)

        for k in K_range:
            if k not in self.rota: continue
            
            for v in V_range:
                if v not in self.rota[k] or not self.rota[k][v]:
                    continue

                rota_kv = self.rota[k][v]
                chegadas_kv = self.chegada[k][v]

                # 1. Checagem de consistência da rota (deve ter garagem no início e fim)
                if rota_kv[0] != 0 or rota_kv[-1] != 0:
                    if verbose: print(f"Rota (k={k}, v={v}) não começa/termina na garagem (0). Rota: {rota_kv}")
                    return False
                
                # 2. Checagem de consistência de tempo INTERNA
                for i in range(1, len(rota_kv)):
                    no_anterior = rota_kv[i-1]
                    no_atual = rota_kv[i]
                    
                    # (Ajuste: O 'chegadas' é o tempo de INÍCIO de serviço, não o tempo de SAÍDA do anterior)
                    # Tempo de saída do nó anterior
                    tempo_saida_anterior = chegadas_kv[i-1] + dados.s[no_anterior]
                    tempo_viagem = dados.T[no_anterior, no_atual]
                    
                    chegada_minima_esperada = tempo_saida_anterior + tempo_viagem
                    
                    # O tempo de chegada real não pode ser menor que o mínimo esperado
                    if chegadas_kv[i] < chegada_minima_esperada - 1e-4:
                         if verbose:
                             print(f"Inconsistência de tempo: (k={k}, v={v}), {no_anterior}->{no_atual}")
                             print(f"  Saída de {no_anterior} (chegada {chegadas_kv[i-1]} + serv {dados.s[no_anterior]}) = {tempo_saida_anterior}")
                             print(f"  Chegada esperada em {no_atual} >= {tempo_saida_anterior} + viagem {tempo_viagem} = {chegada_minima_esperada}")
                             print(f"  Chegada real foi: {chegadas_kv[i]}")
                         return False

                # 3. Checagem de Tmax (Duração da viagem)
                # Duração = (Tempo de chegada na garagem) - (Tempo de saída da garagem)
                duracao = self.chegada[k][v][-1] - self.chegada[k][v][0]
                if duracao > dados.Tmax + 1e-4:
                    if verbose:
                        print(f"TMAX Violado: Veículo {k} viagem {v} excedeu Tmax: {duracao} > {dados.Tmax}")
                    return False

                # 4. Checagem de Janelas de Tempo (e, l)
                # Itera apenas nas requisições (ignorando garagem [0] e [-1])
                requisicoes_rota = self.rota[k][v][1:-1]
                chegadas_rota = self.chegada[k][v][1:-1]

                for i in range(len(requisicoes_rota)):
                    req = requisicoes_rota[i]
                    chegada = chegadas_rota[i]
                    
                    if (chegada < dados.e[req-1] - 1e-4 or chegada > dados.l[req-1] + 1e-4):
                        if verbose:
                            print(f"Janela Violada: (k={k}, v={v}) Req {req} violou janela [{dados.e[req-1]}, {dados.l[req-1]}]. Chegada: {chegada}")
                        return False
                    
                    # 5. Checagem de Atendimento (Remoção da lista)
                    if req not in N:
                        if verbose: print(f"Erro: Req {req} atendida mais de uma vez.")
                        # (Nota: o N.remove() abaixo falhará, o que é bom)
                    N.remove(req)
        
        # 6. Checagem Final: Todas as requisições N foram atendidas?
        if len(N) != 0:
            if verbose:
                print("Requisições não atendidas:", N)
            return False
        
        # Se passou por tudo, é factível
        return True


# --- FUNÇÕES AUXILIARES DO ACO ---

def pode_inserir_requisicao(rota_atual, chegadas_atuais, req_nova, tempo_atual, dados):
    """
    Validação local de viabilidade (usada durante a construção)
    """
    deslocamento = dados.T[rota_atual[-1]][req_nova]
    i = rota_atual[-1]
    
    if i == 0:
        min_arrival = chegadas_atuais[-1] + dados.s[0] + deslocamento
    else:
        min_arrival = tempo_atual + deslocamento
        
    inicio_janela, fim_janela = dados.e[req_nova-1], dados.l[req_nova-1]
    T_inicio_servico_projetado = max(min_arrival, inicio_janela)
    
    if T_inicio_servico_projetado > fim_janela + 1e-4: return False
        
    T_chegada_final_projetada = T_inicio_servico_projetado + dados.s[req_nova] + dados.T[req_nova][0]
    duracao_projetada = T_chegada_final_projetada - chegadas_atuais[0]
    
    if duracao_projetada > dados.Tmax + 1e-4: return False
    return True

def calcular_atratividade(tau, eta, alpha, beta):
    return math.exp(alpha * math.log(max(1e-6, tau)) + beta * math.log(max(1e-6, eta)))

def escolher_slot_por_probabilidade(candidatos_slot, dados):
    total_atratividade = sum(c['atratividade'] for c in candidatos_slot)
    if total_atratividade == 0:
        return min(candidatos_slot, key=lambda x: x['custo_adicional'])
    
    r_val = random.random()
    acumulado = 0
    for c in candidatos_slot:
        prob = c['atratividade'] / total_atratividade
        acumulado += prob
        if r_val <= acumulado: return c
    return candidatos_slot[-1]

def calcular_funcao_objetivo(solucao_dict, dados):
    custo = 0.0
    for k_str, viagens in solucao_dict["onibus"].items():
        for v_str, dados_viagem in viagens.items():
            rota = dados_viagem["rota"]
            for i in range(len(rota) - 1):
                custo += dados.c[rota[i]][rota[i+1]]
    return custo

def atualizar_feromonio(feromonio_map, melhor_solucao_dict, melhor_custo, rho, Q, dados, fator_elite):
    feromonio_map *= (1.0 - rho)
    if melhor_solucao_dict and melhor_custo < float('inf'):
        delta_tau = (fator_elite * Q) / max(1e-6, melhor_custo)
        for k_str, viagens in melhor_solucao_dict["onibus"].items():
            for v_str, dados_viagem in viagens.items():
                rota = dados_viagem["rota"]
                for i in range(len(rota) - 1):
                    feromonio_map[rota[i]][rota[i+1]] += delta_tau
    return feromonio_map

def dict_para_solucao(dict_solucao: Dict[str, Any], dados: Dados) -> Solucao:
    sol = Solucao()
    sol.rota = {k: {} for k in range(1, dados.K + 1)}
    sol.chegada = {k: {} for k in range(1, dados.K + 1)}
    if dict_solucao is None: return sol
    
    for k_str, onibus_data in dict_solucao.get("onibus", {}).items():
        try: k = int(k_str)
        except ValueError: continue
        if k not in sol.rota: sol.rota[k] = {}
        if k not in sol.chegada: sol.chegada[k] = {}
        for v_str, viagem in onibus_data.items():
            try: v = int(v_str.split('_')[1])
            except (IndexError, ValueError): continue
            if 'rota' in viagem and 'chegada' in viagem:
                sol.rota[k][v] = viagem['rota']
                sol.chegada[k][v] = viagem['chegada']
    return sol

# --- FUNÇÃO PRINCIPAL DO CONSTRUTIVO ---
def construir_solucao_global_aco(dados, feromonio_map, alpha, beta):
    n, m, r_max = dados.n, dados.K, dados.r
    j_nao_atendidas = set(range(1, n + 1))
    rotas_em_construcao = {} 
    bus_status = {k: {"tempo": 0.0, "viagem": 1} for k in range(1, m + 1)}
    solucao = {"onibus": {str(k): {} for k in range(1, m + 1)}}
    
    while j_nao_atendidas:
        candidatos_globais = []
        for j_escolhido in j_nao_atendidas:
            # A) Extensão
            for (k, v), rota_data in rotas_em_construcao.items():
                 rota, chegada = rota_data["rota"], rota_data["chegada"]
                 tempo_saida_ultimo_no = rota_data["tempo_fim_servico"]
                 i = rota[-1]
                 if pode_inserir_requisicao(rota, chegada, j_escolhido, tempo_saida_ultimo_no, dados):
                     chegada_estimada = tempo_saida_ultimo_no + dados.T[i][j_escolhido]
                     inicio_servico = max(chegada_estimada, dados.e[j_escolhido-1])
                     melhor_tempo_fim_servico = inicio_servico + dados.s[j_escolhido]
                     custo_adicional = dados.c[i][j_escolhido]
                     atratividade = calcular_atratividade(feromonio_map[i][j_escolhido], 1.0/(custo_adicional+1e-6), alpha, beta)
                     candidatos_globais.append({
                         "j": j_escolhido, "k": k, "v": v, "tipo": "existente",
                         "atratividade": atratividade, "custo_adicional": custo_adicional,
                         "T_saida_garagem": chegada[0],
                         "melhor_tempo_fim_servico": melhor_tempo_fim_servico
                     })
            # B) Nova Viagem
            for k in range(1, m + 1):
                v = bus_status[k]["viagem"]
                if (k, v) in rotas_em_construcao or v > r_max: continue
                
                T_saida_min_disponivel = bus_status[k]["tempo"] + dados.s[0] if bus_status[k]["tempo"] > 0 else 0
                T_partida_ideal_janela = dados.e[j_escolhido-1] - dados.s[0] - dados.T[0][j_escolhido] 
                T_ref_viagem_final_k = max(T_partida_ideal_janela, T_saida_min_disponivel)
                
                if pode_inserir_requisicao([0], [T_ref_viagem_final_k], j_escolhido, T_ref_viagem_final_k, dados):
                    chegada_estimada = T_ref_viagem_final_k + dados.s[0] + dados.T[0][j_escolhido]
                    inicio_servico = max(chegada_estimada, dados.e[j_escolhido-1])
                    melhor_tempo_fim_servico = inicio_servico + dados.s[j_escolhido]
                    custo_adicional = dados.c[0][j_escolhido]
                    atratividade = calcular_atratividade(feromonio_map[0][j_escolhido], 1.0/(custo_adicional+1e-6), alpha, beta)
                    candidatos_globais.append({
                        "j": j_escolhido, "k": k, "v": v, "tipo": "novo",
                        "atratividade": atratividade, "custo_adicional": custo_adicional,
                        "T_saida_garagem": T_ref_viagem_final_k,
                        "melhor_tempo_fim_servico": melhor_tempo_fim_servico
                    })

        # Filtro de Urgência
        if candidatos_globais:
            js_unicos = list(set(c['j'] for c in candidatos_globais))
            if len(js_unicos) >= 2:
                js_ordenados = sorted(js_unicos, key=lambda x: dados.l[x-1])
                j1, j2 = js_ordenados[0], js_ordenados[1]
                eh_critico = False
                candidatos_j1 = [c for c in candidatos_globais if c['j'] == j1]
                for c1 in candidatos_j1:
                    if (c1['melhor_tempo_fim_servico'] + dados.T[j1][j2]) > dados.l[j2-1]:
                        eh_critico = True; break
                if eh_critico: candidatos_globais = candidatos_j1

        # Deadlock
        if not candidatos_globais:
            rotas_abertas = list(rotas_em_construcao.items())
            if rotas_abertas:
                candidatos_retorno = []
                for (k, v), rota_data in rotas_abertas:
                    i = rota_data["rota"][-1]
                    if i != 0: 
                        T_chegada_garagem = rota_data["tempo_fim_servico"] + dados.T[i][0]
                        if (T_chegada_garagem - rota_data["chegada"][0]) <= dados.Tmax + 1e-4:
                            custo_adicional = dados.c[i][0]
                            candidatos_retorno.append({
                                "k": k, "v": v, "atratividade": 1.0/(custo_adicional+1e-6),
                                "custo_adicional": custo_adicional, "T_chegada_garagem": T_chegada_garagem
                            })
                if candidatos_retorno:
                    slot_escolhido = escolher_slot_por_probabilidade(candidatos_retorno, dados)
                    k, v = slot_escolhido['k'], slot_escolhido['v']
                    rota_data = rotas_em_construcao[(k, v)]
                    T_chegada_garagem = slot_escolhido['T_chegada_garagem']
                    bus_status[k]["tempo"] = T_chegada_garagem 
                    bus_status[k]["viagem"] += 1 
                    rota_data["rota"].append(0)
                    rota_data["chegada"].append(T_chegada_garagem)
                    solucao["onibus"][str(k)][f"viagem_{v}"] = rota_data
                    del rotas_em_construcao[(k, v)] 
                    continue 
            return None # Deadlock real

        # Seleção e Aplicação
        slot_escolhido = escolher_slot_por_probabilidade(candidatos_globais, dados)
        j_escolhido = slot_escolhido['j']
        k, v = slot_escolhido['k'], slot_escolhido['v']
        T_chegada_real_j = slot_escolhido['melhor_tempo_fim_servico'] - dados.s[j_escolhido]
        
        if slot_escolhido['tipo'] == "novo":
            rotas_em_construcao[(k, v)] = {
                "rota": [0, j_escolhido],
                "chegada": [slot_escolhido['T_saida_garagem'], T_chegada_real_j],
                "tempo_fim_servico": slot_escolhido['melhor_tempo_fim_servico']
            }
        else:
            rota_data = rotas_em_construcao[(k, v)]
            rota_data["rota"].append(j_escolhido)
            rota_data["chegada"].append(T_chegada_real_j)
            rota_data["tempo_fim_servico"] = slot_escolhido['melhor_tempo_fim_servico']
        
        j_nao_atendidas.remove(j_escolhido)
        
    # Finalização
    for (k, v), rota_data in rotas_em_construcao.items():
         T_chegada_garagem = rota_data["tempo_fim_servico"] + dados.T[rota_data["rota"][-1]][0]
         rota_data["rota"].append(0)
         rota_data["chegada"].append(T_chegada_garagem)
         solucao["onibus"][str(k)][f"viagem_{v}"] = rota_data

    return solucao

def salvar_solucao_json(solucao, filename="melhor_solucao_aco.json"):
    """
    Salva o objeto Solucao em um arquivo JSON no formato padronizado.
    """
    if solucao is None or solucao.fx == 0.0 or solucao.fx == float('inf'):
        print(f"\n--- JSON NÃO SALVO (Solução inviável ou custo {solucao.fx}) ---")
        return
    dados_onibus = {}
    for k, viagens in solucao.rota.items():
        k_str = str(k)
        dados_onibus[k_str] = {}
        for v, rota_lista in viagens.items():
            if rota_lista:
                v_str = f"viagem_{v}"
                dados_onibus[k_str][v_str] = {
                    "rota": rota_lista,
                    "chegada": solucao.chegada[k][v]
                }
    output = {"fx": solucao.fx, "onibus": dados_onibus}
    try:
        with open(filename, 'w') as f: json.dump(output, f, indent=2) 
        print(f"\n--- JSON SALVO (Custo: {solucao.fx:.2f}) ---")
        print(f"Solução salva em: {filename}")
    except Exception as e: print(f"Erro ao salvar JSON: {e}")

# =============================================================================
# 4. BUSCA LOCAL: RELOCATE INTER-ROTAS (SUBSTITUI O 2-OPT)
# =============================================================================

def calcular_custo_rota(rota, dados):
    c = 0.0
    for i in range(len(rota) - 1):
        c += dados.c[rota[i]][rota[i+1]]
    return c

# =============================================================================
# 4. BUSCA LOCAL 2-OPT (A CHAVE PARA O ÓTIMO)
# =============================================================================

def recalcular_chegadas_viagem(rota: List[int], t_partida: float, dados: Dados) -> Optional[List[float]]:
    """
    Tenta recalcular os tempos de chegada para uma rota;
    Retorna a lista de chegadas se for factível, senão None.
    """
    chegadas = [t_partida]
    for i in range(1, len(rota)):
        u, w = rota[i-1], rota[i]
        
        tempo_saida_u = chegadas[i-1] + dados.s[u]
        chegada_w = tempo_saida_u + dados.T[u][w]
        
        if w != 0: # É uma requisição
            # Chega antes da janela? Espera.
            inicio_servico = max(chegada_w, dados.e[w-1])
            # Viola o fim da janela? Rota infactível.
            if inicio_servico > dados.l[w-1] + 1e-4:
                return None
            chegadas.append(inicio_servico)
        else: # É a garagem
            chegadas.append(chegada_w)
    
    # Verifica Tmax
    if (chegadas[-1] - chegadas[0]) > dados.Tmax + 1e-4:
        return None
        
    return chegadas

def busca_local_2opt(solucao: Solucao, dados: Dados) -> Solucao:
    """
    Aplica o 2-Opt em cada rota de cada ônibus, recalculando o delta
    do custo e validando a factibilidade temporal.
    Custo de avaliação: 0 (pois não chama a FO completa).
    """
    melhorou_global = True
    while melhorou_global: # Continua até não haver mais melhorias
        melhorou_global = False
        
        for k in solucao.rota:
            for v in solucao.rota[k]:
                rota = solucao.rota[k][v]
                # Só otimiza rotas com pelo menos 2 clientes (ex: [0, A, B, 0])
                if len(rota) < 5: 
                    continue
                
                melhorou_rota = True
                while melhorou_rota:
                    melhorou_rota = False
                    
                    # Itera sobre todos os pares de arestas (i, j) para trocar
                    # Começa em 1 (ignora 0) e vai até -3 (para ter j+1 válido)
                    for i in range(1, len(rota) - 3):
                        
                        # *** CORREÇÃO CRÍTICA AQUI ***
                        # O loop deve ir até len(rota) - 1 para incluir o último nó
                        for j in range(i + 2, len(rota) - 1):
                            
                            a, b = rota[i], rota[i+1]
                            c, d = rota[j], rota[j+1]
                            
                            # Calcula o delta do CUSTO
                            custo_antigo = dados.c[a][b] + dados.c[c][d]
                            custo_novo = dados.c[a][c] + dados.c[b][d]
                            delta_custo = custo_novo - custo_antigo
                            
                            # Se a troca piorar o custo, ignora
                            if delta_custo >= 0:
                                continue
                                
                            # Custo melhorou. A troca é TEMPORALMENTE factível?
                            nova_rota = rota[:i+1] + rota[j:i:-1] + rota[j+1:]
                            t_partida = solucao.chegada[k][v][0]
                            
                            novas_chegadas = recalcular_chegadas_viagem(nova_rota, t_partida, dados)
                            
                            if novas_chegadas is not None:
                                # Troca factível! Aplica.
                                solucao.rota[k][v] = nova_rota
                                solucao.chegada[k][v] = novas_chegadas
                                solucao.fx += delta_custo
                                
                                melhorou_rota = True
                                melhorou_global = True
                                break # Reinicia a busca na rota modificada
                        if melhorou_rota: break
                        
    return solucao

# =============================================================================
# 4. BUSCA LOCAL: RELOCATE (CORRIGIDO)
# =============================================================================

def recalcular_chegadas_rota(rota: List[int], t_partida: float, dados: Dados) -> Optional[List[float]]:
    """
    Função auxiliar crucial.
    Calcula os tempos de chegada para uma ROTA e T_PARTIDA específicos.
    Retorna a lista de chegadas se for factível, ou None se inviável.
    """
    chegadas = [t_partida]
    tempo_atual = t_partida
    
    for i in range(1, len(rota)):
        u, v = rota[i-1], rota[i]
        
        # Tempo de saída de u + tempo de viagem
        tempo_saida_u = chegadas[i-1] + dados.s[u]
        chegada_em_v = tempo_saida_u + dados.T[u][v]
        
        if v != 0: # É uma requisição
            # Espera se chegar cedo
            inicio_servico = max(chegada_em_v, dados.e[v-1])
            
            # Viola janela de tempo? Rota infactível.
            if inicio_servico > dados.l[v-1] + 1e-4:
                return None
            
            chegadas.append(inicio_servico)
        else: # É a garagem (v == 0)
            chegadas.append(chegada_em_v)
            
    # Violou Tmax? Rota infactível.
    if (chegadas[-1] - chegadas[0]) > dados.Tmax + 1e-4:
        return None
        
    return chegadas

def calcular_custo_rota(rota: List[int], dados: Dados) -> float:
    """Calcula o custo de uma única rota."""
    custo = 0.0
    for i in range(len(rota) - 1):
        custo += dados.c[rota[i]][rota[i+1]]
    return custo

def busca_local_relocate(solucao: Solucao, dados: Dados) -> Solucao:
    """
    Tenta mover cada cliente para todas as outras posições possíveis,
    incluindo a criação de NOVAS VIAGENS (a lógica que faltava).
    """
    melhorou = True
    while melhorou:
        melhorou = False
        
        # Copiamos as chaves para poder modificar o dicionário durante a iteração
        for k_orig in list(solucao.rota.keys()):
            for v_orig in list(solucao.rota[k_orig].keys()):
                
                rota_orig = solucao.rota[k_orig][v_orig]
                
                # Tenta mover cada cliente (ignora a garagem 0 no início e fim)
                for i in range(1, len(rota_orig) - 1):
                    cliente_a_mover = rota_orig[i]
                    
                    # --- 1. Calcular o "Delta da Remoção" ---
                    
                    # Rota original sem o cliente
                    rota_orig_recortada = rota_orig[:i] + rota_orig[i+1:]
                    t_partida_orig = solucao.chegada[k_orig][v_orig][0]
                    
                    # Verifica viabilidade da rota original após a remoção
                    novas_chegadas_orig = recalcular_chegadas_rota(rota_orig_recortada, t_partida_orig, dados)
                    if novas_chegadas_orig is None:
                        continue # Remoção torna a rota origem infactível

                    custo_antigo_orig = calcular_custo_rota(rota_orig, dados)
                    custo_novo_orig = calcular_custo_rota(rota_orig_recortada, dados)
                    
                    
                    # --- 2. Tentar Inserir (Destino) ---
                    # Itera sobre todos os veículos de destino
                    for k_dest in range(1, dados.K + 1):
                        
                        # --- 2A. Tentar inserir em VIAGENS EXISTENTES ---
                        for v_dest in solucao.rota.get(k_dest, {}):
                            
                            # Não tenta inserir em si mesmo (já tratado)
                            if k_dest == k_orig and v_dest == v_orig:
                                continue
                                
                            rota_dest_base = solucao.rota[k_dest][v_dest]
                            t_partida_dest = solucao.chegada[k_dest][v_dest][0]
                            custo_antigo_dest = calcular_custo_rota(rota_dest_base, dados)

                            # Tenta inserir em cada posição da rota destino
                            for j in range(1, len(rota_dest_base)):
                                rota_dest_nova = rota_dest_base[:j] + [cliente_a_mover] + rota_dest_base[j:]
                                
                                novas_chegadas_dest = recalcular_chegadas_rota(rota_dest_nova, t_partida_dest, dados)
                                if novas_chegadas_dest is None:
                                    continue # Inserção infactível
                                    
                                # Factível! Calcula o delta total
                                custo_novo_dest = calcular_custo_rota(rota_dest_nova, dados)
                                
                                # Delta = (Custo_Novo_Total) - (Custo_Antigo_Total)
                                delta_custo = (custo_novo_orig + custo_novo_dest) - (custo_antigo_orig + custo_antigo_dest)
                                
                                if delta_custo < -1e-4: # Melhorou!
                                    # print(f"RELOCATE: Movendo {cliente_a_mover} de ({k_orig},{v_orig}) para ({k_dest},{v_dest}). Delta: {delta_custo}")
                                    solucao.rota[k_orig][v_orig] = rota_orig_recortada
                                    solucao.chegada[k_orig][v_orig] = novas_chegadas_orig
                                    
                                    solucao.rota[k_dest][v_dest] = rota_dest_nova
                                    solucao.chegada[k_dest][v_dest] = novas_chegadas_dest
                                    
                                    solucao.fx += delta_custo
                                    melhorou = True
                                    break
                            if melhorou: break
                        if melhorou: break
                        
                        # --- 2B. Tentar inserir em uma NOVA VIAGEM ---
                        # (Esta era a lógica que faltava!)
                        if not melhorou and len(solucao.rota.get(k_dest, {})) < dados.r:
                            
                            # Calcula o tempo que k_dest fica disponível
                            tempo_disponivel = 0.0
                            if solucao.rota.get(k_dest): # Se k_dest já tem viagens
                                ultima_v = max(solucao.rota[k_dest].keys())
                                tempo_disponivel = solucao.chegada[k_dest][ultima_v][-1] # Chegada na garagem
                            
                            # Lógica de tempo de partida (copiada do construtor)
                            T_saida_min_disponivel = tempo_disponivel + dados.s[0] if tempo_disponivel > 0 else 0
                            T_partida_ideal_janela = dados.e[cliente_a_mover-1] - dados.s[0] - dados.T[0][cliente_a_mover] 
                            t_partida_nova_viagem = max(T_partida_ideal_janela, T_saida_min_disponivel)
                            
                            rota_dest_nova = [0, cliente_a_mover, 0]
                            
                            novas_chegadas_dest = recalcular_chegadas_rota(rota_dest_nova, t_partida_nova_viagem, dados)
                            if novas_chegadas_dest is None:
                                continue # Nova rota infactível
                                
                            # Factível! Calcula o delta
                            custo_novo_dest = calcular_custo_rota(rota_dest_nova, dados)
                            
                            # Delta = (Custo_Novo_Origem + Custo_Nova_Rota) - (Custo_Antigo_Origem)
                            delta_custo = (custo_novo_orig + custo_novo_dest) - custo_antigo_orig
                            
                            if delta_custo < -1e-4: # Melhorou!
                                # print(f"RELOCATE (NEW TRIP): Movendo {cliente_a_mover} de ({k_orig},{v_orig}) para ({k_dest}, NOVA). Delta: {delta_custo}")
                                solucao.rota[k_orig][v_orig] = rota_orig_recortada
                                solucao.chegada[k_orig][v_orig] = novas_chegadas_orig
                                
                                # Adiciona a nova viagem
                                nova_v_dest = len(solucao.rota.get(k_dest, {})) + 1
                                solucao.rota[k_dest][nova_v_dest] = rota_dest_nova
                                solucao.chegada[k_dest][nova_v_dest] = novas_chegadas_dest
                                
                                solucao.fx += delta_custo
                                melhorou = True
                                break
                    if melhorou: break
                if melhorou: break
            if melhorou: break
            
        # Limpa rotas vazias (Ex: [0, 0]) que podem ter sido criadas
        for k in list(solucao.rota.keys()):
            for v in list(solucao.rota[k].keys()):
                if len(solucao.rota[k][v]) <= 2:
                    del solucao.rota[k][v]
                    del solucao.chegada[k][v]
            # Se o ônibus ficou sem viagens, limpa
            if not solucao.rota[k]:
                del solucao.rota[k]
                del solucao.chegada[k]
                
    return solucao

# =============================================================================
# 5. MÉTODO RESOLVA (Interface Oficial com ACO + 2-Opt)
# =============================================================================

def resolva(dados: Dados, numero_avaliacoes: int) -> Solucao:
    
    # --- SINTONIA ADAPTATIVA (Focada em EXPLORAÇÃO) ---
    if dados.n <= 20:
        # --- MUDANÇA ESTRATÉGICA (ANARQUIA + GANÂNCIA) ---
        # O problema é a convergência instantânea. Vamos lutar contra ela.
        params = {
            # Alpha BAIXO: Não confie cegamente no feromônio (que nos leva ao 36k)
            'alpha': round(random.uniform(0.1, 1.0), 2), 
            
            # Beta ALTO: Seja ganancioso! A ganância (menor custo) 
            # naturalmente favorece rotas de cliente único (ex: 0-A-0),
            # que é a estrutura da solução ótima de 33k.
            'beta': round(random.uniform(4.0, 8.0), 2), 
            
            # Rho ALTO: Esqueça os caminhos ruins (36k) rapidamente.
            'rho': round(random.uniform(0.2, 0.5), 2), 
            
            'Q': random.choice([500.0, 1000.0]),
            
            # Fator Elite BAIXO: Não reforce o ótimo local tão agressivamente.
            'fator_elite': round(random.uniform(0.1, 1.5), 1)
        }
    else: # Instâncias Grandes (devemos balancear)
        params = {
            'alpha': round(random.uniform(1.0, 2.0), 2),
            'beta': round(random.uniform(2.0, 4.0), 2),
            'rho': round(random.uniform(0.05, 0.2), 3),
            'Q': random.choice([1000.0, 2000.0]),
            'fator_elite': round(random.uniform(1.0, 3.0), 1)
        }
    
    alpha, beta, rho = params['alpha'], params['beta'], params['rho']
    Q, fator_elite = params['Q'], params['fator_elite']

    feromonio = np.full((dados.n + 1, dados.n + 1), 1e-4)
    melhor_solucao = Solucao()
    melhor_solucao_dict = None 
    melhor_custo = float('inf')
    
    avaliacoes = 0
    
    print(f"\n--- INICIANDO PROTOCOLO DE EXECUÇÃO DO ACO COM RELOCATE INTER-ROTAS(SHIFT) - 2-OPT (resolve) ---")
    print(f"Hiperparâmetros: ALPHA={alpha}, BETA={beta}, RHO={rho}, Q={Q}, FATOR_ELITE={fator_elite}")
    print(f"Iniciando (N={dados.n}, K={dados.K}, Nmar={numero_avaliacoes}).")
    
    while avaliacoes < numero_avaliacoes:
        
        # 1. CONSTRUÇÃO (retorna dicionário)
        dict_solucao_candidata = construir_solucao_global_aco(dados, feromonio, alpha, beta)
        
        # A construção conta como uma avaliação
        
        
        if dict_solucao_candidata is None:
            continue

        # 2. CONVERSÃO E TESTE DE FACTIBILIDADE
        solucao_obj = dict_para_solucao(dict_solucao_candidata, dados)
            
        if solucao_obj is not None and solucao_obj.factivel(dados, verbose=True): 
            
            # Aqui NÃO contamos avaliação, pois o 'factivel' é só um validador
            custo_construido = calcular_funcao_objetivo(dict_solucao_candidata, dados)
            solucao_obj.fx = custo_construido
            avaliacoes += 1
            
            # --- ETAPA DE BUSCA LOCAL (CUSTO 0 avaliações) ---
            # O 2-Opt vai polir a solução (ex: 36.606 -> 33.486)
            solucao_polida = busca_local_2opt(busca_local_relocate(copy.deepcopy(solucao_obj), dados), dados)
            custo_polido = solucao_polida.fx
            # --------------------------------------------------
            
            if custo_polido < melhor_custo and solucao_polida.factivel(dados, True):
                melhor_custo = custo_polido
                melhor_solucao = solucao_polida
                
                # Para o feromônio, usamos o *dicionário* da solução original
                # que levou à polida.
                melhor_solucao_dict = dict_solucao_candidata 
                
                print(f"Nova melhor solução em avaliação {avaliacoes}: Custo = {melhor_custo:.2f}")

            # 4. ATUALIZAÇÃO DE FEROMÔNIO
            feromonio = atualizar_feromonio(feromonio, melhor_solucao_dict, melhor_custo, rho, Q, dados, fator_elite)

    print(f"\nFinalizado o ACO+2-Opt. Total de avaliações: {avaliacoes}")
    print(f"Melhor Custo Encontrado: {melhor_custo:.2f}")

    # Anexa os parâmetros usados para debug
    melhor_solucao.debug_info = params
    
    # Retorna APENAS o objeto Solucao, como exigido
    return melhor_solucao

# =============================================================================
# 6. BLOCO DE TESTES (Validação das 30 execuções)
# =============================================================================
if __name__ == "__main__":
    try:
        ARQUIVO_JSON = "pequena.json"
        # Garante que o 'dados' seja carregado do subdiretório
        dados = carrega_dados_json(os.path.join("dados", ARQUIVO_JSON))
        
        N_evals = 10 * dados.n * dados.K * dados.r
        
        print(f"--- Teste de 30 Execuções ({ARQUIVO_JSON}) ---")
        print(f"Limite de Avaliações: {N_evals}")

        historico_custos = []
        historico_params = []
        melhor_global_custo = float('inf')
        melhor_global_solucao = None
        melhor_global_params = {}
        
        for i in range(1, 31):
            t_inicio = time.time()
            
            # Chama resolva (retorna SÓ a solução)
            sol = resolva(dados, N_evals)
            
            duracao = time.time() - t_inicio
            
            # Pega os parâmetros "escondidos"
            params_usados = getattr(sol, 'debug_info', {})
            
            if sol and sol.fx > 0 and sol.fx < float('inf'):
                # Validação final (redundante, mas segura)
                is_valid = sol.factivel(dados)
                valid_tag = "VALID" if is_valid else "INVALID"
                print(f"Exec {i:02d}: Custo = {sol.fx:.2f} | Tempo = {duracao:.2f}s | Status: {valid_tag}")
                
                if is_valid:
                    historico_custos.append(sol.fx)
                    historico_params.append(params_usados)
                    
                    if sol.fx < melhor_global_custo:
                        melhor_global_custo = sol.fx
                        melhor_global_solucao = sol
                        melhor_global_params = params_usados
                        salvar_solucao_json(sol, "melhor_solucao_aco.json")
                        print("  -> 🏆 NOVA MELHOR SOLUÇÃO GLOBAL!")
            else:
                print(f"Exec {i:02d}: Nenhuma solução encontrada.")
            
        if historico_custos:
            print("-" * 40)
            print(f"Melhor Custo Global: {min(historico_custos):.2f}")
            print(f"Média dos Custos: {sum(historico_custos)/len(historico_custos):.2f}")
            print(f"Desvio Padrão: {np.std(historico_custos):.2f}")
            print(f"Melhor Configuração Final: {melhor_global_params}")
        else:
            print("Falha: Nenhuma solução válida encontrada em 30 tentativas.")

        # --- GERAÇÃO DO GRÁFICO ---
        plt.figure(figsize=(10, 6))
        valid_costs = [c for c in historico_custos if c < float('inf')]
        valid_indices = list(range(1, len(valid_costs) + 1))
        
        if valid_costs:
            plt.plot(valid_indices, valid_costs, marker='o', linestyle='-', color='b')
            best_idx_local = np.argmin(valid_costs)
            
            if historico_params:
                # Garante que o índice de parâmetros está correto
                params_do_melhor = historico_params[best_idx_local]
                text_str = '\n'.join([f'{k}={v}' for k, v in params_do_melhor.items()])
                
                # Lógica para ajustar a posição da anotação se o gráfico for "flat"
                y_pos_ajuste = (max(valid_costs)-min(valid_costs)) * 0.1
                if y_pos_ajuste == 0: y_pos_ajuste = max(valid_costs) * 0.1
                
                plt.annotate(f'Melhor: {melhor_global_custo:.2f}\n{text_str}', 
                            xy=(best_idx_local+1, melhor_global_custo), 
                            xytext=(best_idx_local+1.5, melhor_global_custo + y_pos_ajuste),
                            arrowprops=dict(facecolor='red', shrink=0.05),
                            bbox=dict(boxstyle="round,pad=0.3", fc="yellow", alpha=0.9))
            
        plt.title(f'Sintonia Automática ACO+2-Opt - {ARQUIVO_JSON}')
        plt.xlabel('Execução')
        plt.ylabel('Custo (FX)')
        plt.grid(True)
        plt.savefig('aco_resultados.png')
        print("\nGráfico salvo em: aco_resultados.png")
        
    except FileNotFoundError:
        print(f"Erro: Arquivo '{ARQUIVO_JSON}' não encontrado. Verifique o caminho 'dados/{ARQUIVO_JSON}'.")
    except ImportError:
        print("Erro: Não foi possível importar 'exemplo_prof.dados'.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")