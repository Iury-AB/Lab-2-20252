import numpy as np
import math
import random
import copy
from typing import Dict, Any, Tuple, List, Optional
from exemplo_prof.dados import Dados
from exemplo_prof.solucao import Solucao

# --- CONSTANTE DO GRUPO ---
NOME_GRUPO = "alcione" 

# --- CONSTANTES DE CONTROLE ---
TOLERANCIA = 1e-4 
TOLERANCIA_CUSTO = 1e-4 

# --- PARÂMETROS GERAIS ---
EXP_SCALING_FACTOR = 10000.0 
K_RCL = 10 
T_INICIAL_BASE = 1500.0         # Base (usado para pequena, agora parâmetro)
T_COOLING_RATE = 0.999 
T_MIN = 1.0          
FATOR_RUINA_BASE = 0.20 
Q = 1000.0 
FATOR_ELITE = 6.0 
PENALIDADE_WINDOW_VIOLATION_FACTOR = 5000.0

# --- PARÂMETROS BASE ---
PARAMS_BASE = {
    'alpha': 2.44, 'beta': 3.66, 'rho': 0.111, 'greedy_factor': 0.80, 'p_random_choice': 0.01,
    'fator_ruina': FATOR_RUINA_BASE,
    'temperatura_inicial': T_INICIAL_BASE # NOVO: Adicionado T_INICIAL ao base
}

# --- MAPA DE OTIMIZAÇÃO (Incluindo a Temperatura Inicial) ---
OPTIMIZED_PARAMS_MAP = {
    'pequena': {'alpha': 2.44, 'beta': 3.66, 'rho': 0.111, 'greedy_factor': 0.50, 'p_random_choice': 0.05, 'fator_ruina': 0.30, 'temperatura_inicial': 1500.0},
    'media':   {'alpha': 1.43, 'beta': 5.00, 'rho': 0.37, 'greedy_factor': 0.80, 'p_random_choice': 0.01, 'fator_ruina': 0.35, 'temperatura_inicial': 15000.0},  # AUMENTADO
    'grande':  {'alpha': 1.43, 'beta': 3.41, 'rho': 0.10, 'greedy_factor': 0.80, 'p_random_choice': 0.01, 'fator_ruina': 0.45, 'temperatura_inicial': 20000.0}, # AUMENTADO
    'rush':    {'alpha': 1.43, 'beta': 5.00, 'rho': 0.37, 'greedy_factor': 0.80, 'p_random_choice': 0.01, 'fator_ruina': 0.45, 'temperatura_inicial': 20000.0}  # AUMENTADO
}

# --- NOVO: FUNÇÃO DE ACEITAÇÃO SIMULATED ANNEALING ---
def sa_acceptance(current_fx: float, neighbor_fx: float, current_T: float) -> bool:
    """
    Decide se aceita uma solução vizinha (ACO/R&R) baseada no Simulated Annealing.
    O SA só é aplicado se o vizinho for PIOR (neighbor_fx > current_fx).
    """
    if neighbor_fx < current_fx - TOLERANCIA_CUSTO:
        # Sempre aceita melhorias
        return True
    
    if neighbor_fx > current_fx + TOLERANCIA_CUSTO:
        # Move pior: calcula a probabilidade de aceitação
        delta_fx = neighbor_fx - current_fx
        try:
            prob_acceptance = math.exp(-delta_fx / max(1e-6, current_T))
        except OverflowError:
            prob_acceptance = 0.0
            
        if random.random() < prob_acceptance:
            # Aceita o movimento pior
            return True
        
    # Rejeita o movimento (pior ou marginalmente igual)
    return False

# --- FUNÇÕES AUXILIARES (FACTIBILIDADE E CUSTO) ---
# [Funções auxiliares inalteradas: recalcular_chegadas_e_validar_rota, calcular_custo_rota, etc.]

def recalcular_chegadas_e_validar_rota(rota: List[int], t_partida: float, dados: Any) -> Optional[List[float]]:
    """Recalcula a factibilidade temporal para uma rota."""
    chegadas = [t_partida]
    if len(rota) <= 1: return None 
    
    if len(rota) == 2 and rota == [0, 0]:
         chegadas.append(t_partida)
         return chegadas 
         
    u_init, v_init = rota[0], rota[1]
    
    if v_init != 0:
        tempo_saida_u_init = t_partida + dados.s[u_init] 
        chegada_em_v_init = tempo_saida_u_init + dados.T[u_init][v_init]
        inicio_servico_v_init = max(chegada_em_v_init, dados.e[v_init-1])
        if inicio_servico_v_init > dados.l[v_init-1] + TOLERANCIA: return None 
        chegadas.append(inicio_servico_v_init)
    elif len(rota) >= 2 and v_init == 0:
         chegadas.append(t_partida)
    else: return None

    for i in range(2, len(rota)):
        u, v = rota[i-1], rota[i]
        tempo_saida_u = chegadas[i-1] + dados.s[u]
        chegada_em_v = tempo_saida_u + dados.T[u][v]
        
        if v != 0:
            inicio_servico = max(chegada_em_v, dados.e[v-1])
            if inicio_servico > dados.l[v-1] + TOLERANCIA: return None 
            chegadas.append(inicio_servico)
        else:
            chegadas.append(chegada_em_v) 
            
    if (chegadas[-1] - chegadas[0]) > dados.Tmax + TOLERANCIA: return None
    return chegadas

def calcular_custo_rota(rota: List[int], dados: Any) -> float:
    custo = 0.0
    for i in range(len(rota) - 1):
        custo += dados.c[rota[i]][rota[i+1]]
    return custo

def calcular_custo_total_solucao(solucao_dict: Dict, dados: Any) -> float:
    custo = 0.0
    for k_str, viagens in solucao_dict.get("onibus", {}).items():
        for v_str, dados_viagem in viagens.items():
            rota = dados_viagem["rota"]
            for i in range(len(rota) - 1):
                custo += dados.c[rota[i]][rota[i+1]]
    return custo

def calcular_funcao_objetivo(solucao_dict: Dict, dados: Any, contador: Any) -> float:
    """Calcula FO e incrementa contador."""
    if contador.count < contador.limite: 
        contador.incrementar()
    return calcular_custo_total_solucao(solucao_dict, dados)

def dict_para_solucao(dict_solucao: Dict[str, Any], dados: Dados, contador: Any) -> Solucao:
    """Converte dict para objeto Solucao, com proteção contra NoneType."""
    sol = Solucao()
    sol.rota = {k: {} for k in range(1, dados.K + 1)}
    sol.chegada = {k: {} for k in range(1, dados.K + 1)}
    
    if dict_solucao is None: 
        sol.fx = float('inf')
        if contador.count < contador.limite: contador.incrementar()
        return sol
    
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
    
    # --- CORREÇÃO BLINDADA CONTRA NONE ---
    # Verifica se 'fx' existe, se não é None e se é maior que zero
    raw_fx = dict_solucao.get('fx')
    if raw_fx is not None and raw_fx > 0:
         sol.fx = raw_fx
         if contador.count < contador.limite: contador.incrementar()
    elif sol.fx == 0.0 or sol.fx == float('inf') or sol.fx is None:
         # Se não tem FX válido, calcula do zero
         sol.fx = calcular_funcao_objetivo(dict_solucao, dados, contador)
    else:
        if contador.count < contador.limite: contador.incrementar()
        
    # Garante que sol.fx nunca seja None
    if sol.fx is None: sol.fx = float('inf')

    return sol

# --- ACO UTILS ---

def calcular_atratividade(tau, eta, alpha, beta):
    return math.exp(alpha * math.log(max(1e-6, tau)) + beta * math.log(max(1e-6, eta)))

def escolher_slot_por_probabilidade(candidatos_slot, dados, p_random_choice=0.0):
    if len(candidatos_slot) > K_RCL:
        candidatos_slot.sort(key=lambda x: x['atratividade'], reverse=True)
        candidatos_slot = candidatos_slot[:K_RCL]

    if random.random() < p_random_choice:
        return random.choice(candidatos_slot)

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

def atualizar_feromonio(feromonio_map: np.ndarray, melhor_solucao_dict: Dict, melhor_custo: float, rho: float, Q: float, dados: Any) -> np.ndarray:
    feromonio_map *= (1.0 - rho)
    if melhor_solucao_dict and melhor_custo < float('inf'):
        delta_tau = (FATOR_ELITE * Q) * math.exp(-melhor_custo / EXP_SCALING_FACTOR)
        for k_str, viagens in melhor_solucao_dict.get("onibus", {}).items():
            for v_str, dados_viagem in viagens.items():
                rota = dados_viagem["rota"]
                for i in range(len(rota) - 1):
                    feromonio_map[rota[i]][rota[i+1]] += delta_tau
    return feromonio_map

# --- REPARO INTELIGENTE COM RETRY ---

def _calcular_melhores_insercoes(solucao: Dict, cliente: int, dados: Dados) -> List[Tuple[float, Dict]]:
    """Encontra todas as posições de inserção viáveis para um cliente."""
    opcoes_viaveis = []

    for k_str, viagens in solucao["onibus"].items():
        k = int(k_str)
        for v_str, dados_viagem in viagens.items():
            v = int(v_str.split('_')[1])
            rota_atual = dados_viagem["rota"]
            chegada_atual_inicio = dados_viagem["chegada"][0]
            custo_atual = calcular_custo_rota(rota_atual, dados)
            
            for pos in range(1, len(rota_atual)):
                nova_rota = rota_atual[:pos] + [cliente] + rota_atual[pos:]
                novas_chegadas = recalcular_chegadas_e_validar_rota(nova_rota, chegada_atual_inicio, dados)
                
                if novas_chegadas is not None:
                    novo_custo = calcular_custo_rota(nova_rota, dados)
                    delta_custo = novo_custo - custo_atual
                    opcoes_viaveis.append((delta_custo, {
                        "tipo": "existente", "k": k, "v": v, 
                        "rota": nova_rota, "chegada": novas_chegadas
                    }))

        if len(viagens) < dados.r:
            ultima_v_num = 0
            tempo_disp = 0.0
            if viagens:
                ultima_v_key = max(viagens.keys(), key=lambda x: int(x.split('_')[1]))
                ultima_v_num = int(ultima_v_key.split('_')[1])
                tempo_disp = viagens[ultima_v_key]["chegada"][-1]
            
            nova_v = ultima_v_num + 1
            T_saida_min = tempo_disp + dados.s[0]
            T_necessario_para_janela = dados.e[cliente-1] - dados.T[0][cliente] - dados.s[0]
            t_partida = max(T_necessario_para_janela, T_saida_min)
            rota_nova = [0, cliente, 0]
            chegadas_nova = recalcular_chegadas_e_validar_rota(rota_nova, t_partida, dados)
            
            if chegadas_nova is not None:
                custo_viagem = calcular_custo_rota(rota_nova, dados)
                opcoes_viaveis.append((custo_viagem, {
                    "tipo": "nova", "k": k, "v": nova_v, 
                    "rota": rota_nova, "chegada": chegadas_nova
                }))

    opcoes_viaveis.sort(key=lambda x: x[0])
    return opcoes_viaveis[:2]

def _executar_rodada_regret(solucao: Dict, pendentes: List[int], dados: Dados) -> Tuple[Dict, List[int]]:
    """Executa uma rodada completa de inserção Regret-2."""
    while pendentes:
        melhores_opcoes_por_cliente = []
        clientes_sem_opcao = []
        
        for cliente in pendentes:
            opcoes = _calcular_melhores_insercoes(solucao, cliente, dados)
            if not opcoes:
                clientes_sem_opcao.append(cliente)
                continue
            
            melhor_custo = opcoes[0][0]
            segundo_custo = opcoes[1][0] if len(opcoes) > 1 else float('inf')
            regret = segundo_custo - melhor_custo
            
            melhores_opcoes_por_cliente.append({
                "cliente": cliente, "regret": regret, "custo": melhor_custo, "dados_insercao": opcoes[0][1]
            })
            
        if clientes_sem_opcao:
            return solucao, pendentes 

        if not melhores_opcoes_por_cliente: break

        escolhido = max(melhores_opcoes_por_cliente, key=lambda x: (x["regret"], x["custo"]))
        
        meta = escolhido["dados_insercao"]
        k_str, v_key = str(meta["k"]), f"viagem_{meta['v']}"
        
        if meta["tipo"] == "existente":
            solucao["onibus"][k_str][v_key]["rota"] = meta["rota"]
            solucao["onibus"][k_str][v_key]["chegada"] = meta["chegada"]
        else:
            solucao["onibus"][k_str][v_key] = {"rota": meta["rota"], "chegada": meta["chegada"]}
            
        pendentes.remove(escolhido["cliente"])
        
    return solucao, [] 

def _executar_rodada_gulosa_random(solucao: Dict, pendentes: List[int], dados: Dados) -> Tuple[Dict, List[int]]:
    """Executa inserção gulosa com ordem aleatória (Fallback)."""
    random.shuffle(pendentes)
    nao_inseridos = []
    
    for cliente in pendentes:
        opcoes = _calcular_melhores_insercoes(solucao, cliente, dados)
        if opcoes:
            meta = opcoes[0][1]
            k_str, v_key = str(meta["k"]), f"viagem_{meta['v']}"
            
            if meta["tipo"] == "existente":
                solucao["onibus"][k_str][v_key]["rota"] = meta["rota"]
                solucao["onibus"][k_str][v_key]["chegada"] = meta["chegada"]
            else:
                solucao["onibus"][k_str][v_key] = {"rota": meta["rota"], "chegada": meta["chegada"]}
        else:
            nao_inseridos.append(cliente)
            
    return solucao, nao_inseridos

def reparar_solucao_incompleta(solucao_base: Dict, j_nao_atendidas: set, dados: Dados) -> Tuple[Dict, set]:
    """
    Tenta reparar a solução com múltiplas estratégias e retries.
    """
    if not j_nao_atendidas: return solucao_base, set()
    
    pendentes_originais = list(j_nao_atendidas)
    
    sol_temp = copy.deepcopy(solucao_base)
    sol_regret, sobras_regret = _executar_rodada_regret(sol_temp, pendentes_originais.copy(), dados)
    
    if not sobras_regret:
        return sol_regret, set()
        
    melhor_resultado = (sol_regret, set(sobras_regret))
    
    MAX_RETRIES = 5
    for _ in range(MAX_RETRIES):
        sol_retry = copy.deepcopy(solucao_base) 
        sol_random, sobras_random = _executar_rodada_gulosa_random(sol_retry, pendentes_originais.copy(), dados)
        
        if not sobras_random:
            return sol_random, set() 
            
        if len(sobras_random) < len(melhor_resultado[1]):
            melhor_resultado = (sol_random, set(sobras_random))
            
    return melhor_resultado

# --- FASE CONSTRUTIVA ACO ---

def construir_solucao_global_aco(dados: Dados, feromonio_map: np.ndarray, alpha: float, beta: float, FATOR_PESO_L: float, FATOR_PESO_E: float, greedy_factor_retorno: float = 0.8, p_random_choice: float = 0.0) -> Tuple[Optional[Dict], Optional[set]]:
    """Função principal do construtivo ACO (Nível Único)."""
    n, m, r_max = dados.n, dados.K, dados.r
    j_nao_atendidas = set(range(1, n + 1))
    
    rotas_em_construcao = {} 
    bus_status = {k: {"tempo": 0.0, "viagem": 1} for k in range(1, m + 1)}
    solucao = {"onibus": {str(k): {} for k in range(1, m + 1)}}
    
    while j_nao_atendidas:
        candidatos_globais = []
        
        # 1. GERAÇÃO DE CANDIDATOS
        for j_escolhido in list(j_nao_atendidas):
            # 1.A. Extensão
            for (k, v), rota_data in rotas_em_construcao.items():
                 rota, chegada = rota_data["rota"], rota_data["chegada"]
                 i = rota[-1]
                 if not recalcular_chegadas_e_validar_rota(rota + [j_escolhido, 0], chegada[0], dados): continue 
                 
                 chegada_estimada = rota_data["tempo_fim_servico"] + dados.T[i][j_escolhido]
                 inicio_servico = max(chegada_estimada, dados.e[j_escolhido-1])
                 melhor_tempo_fim_servico = inicio_servico + dados.s[j_escolhido]
                 folga_temporal = dados.l[j_escolhido-1] - inicio_servico
                 
                 custo_adc = dados.c[i][j_escolhido] + greedy_factor_retorno * dados.c[j_escolhido][0]
                 heuristica = (1.0 / (custo_adc + 1e-6)) * ((1.0 / (folga_temporal + 1.0)))
                 atratividade = calcular_atratividade(feromonio_map[i][j_escolhido], heuristica, alpha, beta)
                 candidatos_globais.append({"j": j_escolhido, "k": k, "v": v, "tipo": "existente", "atratividade": atratividade, "custo_adicional": dados.c[i][j_escolhido], "T_saida_garagem": chegada[0], "melhor_tempo_fim_servico": melhor_tempo_fim_servico})
                     
            # 1.B. Nova Viagem
            for k in range(1, m + 1):
                v = bus_status[k]["viagem"]
                if (k, v) in rotas_em_construcao or v > r_max: continue
                T_inicio = bus_status[k]["tempo"]
                if not recalcular_chegadas_e_validar_rota([0, j_escolhido, 0], T_inicio, dados): continue
                
                T_partida = T_inicio + dados.s[0]
                chegada_est = T_partida + dados.T[0][j_escolhido]
                inicio_servico = max(chegada_est, dados.e[j_escolhido-1])
                melhor_tempo_fim = inicio_servico + dados.s[j_escolhido]
                folga_temporal = dados.l[j_escolhido-1] - inicio_servico
                
                custo_adc = dados.c[0][j_escolhido] + greedy_factor_retorno * dados.c[j_escolhido][0]
                heuristica = (1.0 / (custo_adc + 1e-6)) * ((1.0 / (folga_temporal + 1.0)))
                atratividade = calcular_atratividade(feromonio_map[0][j_escolhido], heuristica, alpha, beta)
                candidatos_globais.append({"j": j_escolhido, "k": k, "v": v, "tipo": "novo", "atratividade": atratividade, "custo_adicional": dados.c[0][j_escolhido], "T_saida_garagem": T_inicio, "melhor_tempo_fim_servico": melhor_tempo_fim})
        
        # 2. SELEÇÃO
        if not candidatos_globais:
             movimentos_retorno = []
             for (k, v), rota_data in rotas_em_construcao.items():
                 i = rota_data["rota"][-1]
                 if i != 0: 
                     T_cheg = rota_data["tempo_fim_servico"] + dados.T[i][0]
                     if (T_cheg - rota_data["chegada"][0]) <= dados.Tmax + TOLERANCIA:
                         movimentos_retorno.append({"k": k, "v": v, "T_chegada_garagem": T_cheg})
             if movimentos_retorno:
                 escolha = movimentos_retorno[0]
                 k, v = escolha['k'], escolha['v']
                 rota_data = rotas_em_construcao[(k, v)]
                 bus_status[k]["tempo"] = escolha['T_chegada_garagem'] 
                 bus_status[k]["viagem"] += 1 
                 rota_data["rota"].append(0)
                 rota_data["chegada"].append(escolha['T_chegada_garagem'])
                 solucao["onibus"][str(k)][f"viagem_{v}"] = rota_data
                 del rotas_em_construcao[(k, v)] 
                 continue 
             break 
        
        escolhido = escolher_slot_por_probabilidade(candidatos_globais, dados, p_random_choice)
        j, k, v = escolhido['j'], escolhido['k'], escolhido['v']
        T_cheg_real = escolhido['melhor_tempo_fim_servico'] - dados.s[j]
        
        if escolhido['tipo'] == "novo":
            rotas_em_construcao[(k, v)] = {"rota": [0, j], "chegada": [escolhido['T_saida_garagem'], T_cheg_real], "tempo_fim_servico": escolhido['melhor_tempo_fim_servico']}
        else:
            r_d = rotas_em_construcao[(k, v)]
            r_d["rota"].append(j)
            r_d["chegada"].append(T_cheg_real)
            r_d["tempo_fim_servico"] = escolhido['melhor_tempo_fim_servico']
        j_nao_atendidas.remove(j)

    for (k, v), rota_data in rotas_em_construcao.items():
         T_cheg = rota_data["tempo_fim_servico"] + dados.T[rota_data["rota"][-1]][0]
         rota_data["rota"].append(0)
         rota_data["chegada"].append(T_cheg)
         solucao["onibus"][str(k)][f"viagem_{v}"] = rota_data

    if j_nao_atendidas:
        solucao, j_nao_atendidas = reparar_solucao_incompleta(solucao, j_nao_atendidas, dados)

    return solucao, j_nao_atendidas