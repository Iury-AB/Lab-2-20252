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

# --- CONSTANTE DE TOLERÂNCIA FLOAT ---
TOLERANCIA = 1e-4 # Tolerância do factível (mantida)
TOLERANCIA_CUSTO = 1e-4 # Tolerância de Custo para o VND (mantida para alta precisão)
# Flag para controlar a verbosidade dos logs
LOG_CONSTRUTIVO_GERAL = False
LOG_CONSTRUTIVO_DETALHADO = False
LOG_VND_ATIVO = False
LOG_DIAGNOSTICO_DEADLOCK = False

# --- PARÂMETRO ILS/R&R ---
FATOR_RUINA = 0.25 # AUMENTADO PARA 25% - MAXIMIZA A DIVERSIFICAÇÃO
# CORREÇÃO CRÍTICA DE VELOCIDADE: Amostragem agressiva na Reconstrução
AMOSTRA_J_RNR = 3

# --- CLASSE CONTADOR (Para contagem mutável) ---
class Contador:
    def __init__(self):
        self.count = 0
        self.limite = 0

    def set_limite(self, limite):
        self.limite = limite

    def incrementar(self, incremento=1):
        """
        Incrementa e verifica o limite.
        NOTA IMPORTANTE: Esta função só é chamada estritamente por
        calcular_funcao_objetivo para respeitar o critério de avaliação.
        """
        self.count += incremento
        return self.count > self.limite

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
        N = list(range(1, dados.n + 1)) 
        N_atendidas_total = set()

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
                    
                    tempo_saida_anterior = chegadas_kv[i-1] + dados.s[no_anterior]
                    tempo_viagem = dados.T[no_anterior, no_atual]
                    
                    chegada_minima_esperada = tempo_saida_anterior + tempo_viagem
                    
                    if chegadas_kv[i] < chegada_minima_esperada - 1e-4:
                        if verbose:
                            print(f"Inconsistência de tempo: (k={k}, v={v}), {no_anterior}->{no_atual}")
                        return False

                # 3. Checagem de Tmax (Duração da viagem)
                duracao = self.chegada[k][v][-1] - self.chegada[k][v][0]
                if duracao > dados.Tmax + 1e-4:
                    if verbose:
                        print(f"TMAX Violado: Veículo {k} viagem {v} excedeu Tmax: {duracao} > {dados.Tmax}")
                    return False

                # 4. Checagem de Janelas de Tempo (e, l)
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
                    N.remove(req)
        
        # 6. Checagem Final: Todas as requisições N foram atendidas?
        if len(N) != 0:
            if verbose:
                print("Requisições não atendidas:", N)
            return False
        
        return True

# --- FUNÇÕES AUXILIARES DO ACO E R&R ---

def pode_inserir_requisicao(rota_atual, chegadas_atuais, req_nova, tempo_atual, dados):
    deslocamento = dados.T[rota_atual[-1]][req_nova]
    i = rota_atual[-1] 
    
    if i == 0:
        min_arrival = chegadas_atuais[-1] + dados.s[0] + deslocamento
    else:
        min_arrival = tempo_atual + deslocamento
        
    inicio_janela, fim_janela = dados.e[req_nova-1], dados.l[req_nova-1]
    T_inicio_servico_projetado = max(min_arrival, inicio_janela)
    
    if T_inicio_servico_projetado > fim_janela + TOLERANCIA: return False
        
    T_chegada_final_projetada = T_inicio_servico_projetado + dados.s[req_nova] + dados.T[req_nova][0]
    duracao_projetada = T_chegada_final_projetada - chegadas_atuais[0]
    
    if duracao_projetada > dados.Tmax + TOLERANCIA: return False
    
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

def calcular_funcao_objetivo(solucao_dict, dados, contador: Contador):
    """
    CALCULADOR DA FUNÇÃO OBJETIVO E CONTADOR DE AVALIAÇÃO OFICIAL (FX TOTAL)
    """
    custo = 0.0
    for k_str, viagens in solucao_dict.get("onibus", {}).items():
        for v_str, dados_viagem in viagens.items():
            rota = dados_viagem["rota"]
            for i in range(len(rota) - 1):
                custo += dados.c[rota[i]][rota[i+1]]
    
    contador.incrementar() 
    return custo

def atualizar_feromonio(feromonio_map, melhor_solucao_dict, melhor_custo, rho, Q, dados, fator_elite):
    """
    ATENÇÃO: Função de depósito de feromônio. 
    O nome foi corrigido de 'actualizar_feromonio' para 'atualizar_feromonio'.
    """
    # Evaporação
    feromonio_map *= (1.0 - rho)
    
    # Depósito
    if melhor_solucao_dict and melhor_custo < float('inf'):
        # Delta Tau baseado na melhor solução de toda a execução (Best-So-Far)
        delta_tau = (fator_elite * Q) / max(1e-6, melhor_custo)
        
        for k_str, viagens in melhor_solucao_dict.get("onibus", {}).items():
            for v_str, dados_viagem in viagens.items():
                rota = dados_viagem["rota"]
                for i in range(len(rota) - 1):
                    # O depósito usa o custo da melhor solução global
                    feromonio_map[rota[i]][rota[i+1]] += delta_tau
    return feromonio_map

def dict_para_solucao(dict_solucao: Dict[str, Any], dados: Dados, contador: Contador) -> Solucao:
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
    
    sol.fx = calcular_funcao_objetivo(dict_solucao, dados, contador)
    return sol

def solucao_to_hash(solucao_obj: Solucao) -> str:
    """
    Cria um hash único para a estrutura da rota (ignora os tempos de chegada).
    Utilizado para contar soluções únicas (Diversificação).
    """
    rotas_tuplas = []
    
    # Coleta todas as rotas (k, v)
    for k in sorted(solucao_obj.rota.keys()):
        for v in sorted(solucao_obj.rota[k].keys()):
            rota = solucao_obj.rota[k][v]
            # Adiciona (ônibus, viagem, rota_como_tupla)
            rotas_tuplas.append((k, v, tuple(rota)))
            
    # Cria uma tupla de tuplas e a converte em string para ser usada como hash
    # NOTA: Garante que a ordem (k, v) é consistente para que o hash seja único
    return str(tuple(rotas_tuplas))


# --- FUNÇÃO PRINCIPAL DO CONSTRUTIVO (ACO MELHORADO) ---
def construir_solucao_global_aco(dados, feromonio_map, alpha, beta, FATOR_PESO_L: float, FATOR_PESO_E: float, clientes_iniciais: Optional[set] = None) -> Tuple[Optional[Dict], Optional[int]]:
    
    n, m, r_max = dados.n, dados.K, dados.r
    j_nao_atendidas = clientes_iniciais if clientes_iniciais is not None else set(range(1, n + 1))
    
    rotas_em_construcao = {} 
    bus_status = {k: {"tempo": 0.0, "viagem": 1} for k in range(1, m + 1)}
    solucao = {"onibus": {str(k): {} for k in range(1, m + 1)}}
    
    iteracao_construtiva = 0 
    
    # Sub-função para gerar candidatos 
    def gerar_candidatos(j_pool, FATOR_L, FATOR_E, rotas_em_construcao_snapshot):
        cands = []
        for j_escolhido in j_pool:
            
            # Cálculo de Urgência
            urgencia_l = 1.0 / max(1e-6, dados.l[j_escolhido-1])
            urgencia_e = 1.0 / max(1e-6, dados.e[j_escolhido-1] + 1) 
            fator_urgencia_composto = 1.0 + FATOR_L * urgencia_l + FATOR_E * urgencia_e
            
            # 1.A. Extensão em Rotas Abertas
            for (k, v), rota_data in rotas_em_construcao_snapshot.items():
                 rota, chegada = rota_data["rota"], rota_data["chegada"]
                 tempo_fim_servico_ultimo = rota_data["tempo_fim_servico"]
                 i = rota[-1]
                 
                 if pode_inserir_requisicao(rota, chegada, j_escolhido, tempo_fim_servico_ultimo, dados):
                     
                     chegada_estimada = tempo_fim_servico_ultimo + dados.T[i][j_escolhido]
                     inicio_servico = max(chegada_estimada, dados.e[j_escolhido-1])
                     melhor_tempo_fim_servico = inicio_servico + dados.s[j_escolhido]
                     
                     custo_incremental = dados.c[i][j_escolhido]
                     custo_retorno_previsto = dados.c[j_escolhido][0]
                     custo_adicional_efetivo = custo_incremental + 0.8 * custo_retorno_previsto 
                     
                     heuristica_extensao = 1.0 / (custo_adicional_efetivo + 1e-6)
                     heuristica_extensao *= fator_urgencia_composto

                     atratividade = calcular_atratividade(feromonio_map[i][j_escolhido], heuristica_extensao, alpha, beta)
                     
                     cands.append({
                         "j": j_escolhido, "k": k, "v": v, "tipo": "existente",
                         "atratividade": atratividade, 
                         "custo_adicional": custo_incremental, 
                         "T_saida_garagem": chegada[0],
                         "melhor_tempo_fim_servico": melhor_tempo_fim_servico,
                         "heuristica_eta": heuristica_extensao
                     })
                     
            # 1.B. Nova Viagem
            for k in range(1, m + 1):
                v = bus_status[k]["viagem"]
                if (k, v) in rotas_em_construcao_snapshot or v > r_max: continue
                
                tempo_retorno_ultimo = bus_status[k]["tempo"]
                T_chegada_inicio_viagem = tempo_retorno_ultimo 
                
                if pode_inserir_requisicao([0], [T_chegada_inicio_viagem], j_escolhido, T_chegada_inicio_viagem, dados):
                    
                    T_partida_garagem = T_chegada_inicio_viagem + dados.s[0]
                    chegada_estimada = T_partida_garagem + dados.T[0][j_escolhido]
                    inicio_servico = max(chegada_estimada, dados.e[j_escolhido-1])
                    melhor_tempo_fim_servico = inicio_servico + dados.s[j_escolhido]
                    
                    custo_adicional = dados.c[0][j_escolhido]
                    custo_retorno_inicial = dados.c[j_escolhido][0]
                    custo_total_previsto = custo_adicional + custo_retorno_inicial
                    
                    heuristica_nova_viagem = 1.0 / (custo_total_previsto + 1e-6)
                    heuristica_nova_viagem *= fator_urgencia_composto

                    atratividade = calcular_atratividade(feromonio_map[0][j_escolhido], heuristica_nova_viagem, alpha, beta)
                    
                    cands.append({
                        "j": j_escolhido, "k": k, "v": v, "tipo": "novo",
                        "atratividade": atratividade, "custo_adicional": custo_adicional,
                        "T_saida_garagem": T_chegada_inicio_viagem,
                        "melhor_tempo_fim_servico": melhor_tempo_fim_servico,
                        "heuristica_eta": heuristica_nova_viagem
                    })
        return cands

    # Loop Principal: Continua até que todos os clientes sejam atendidos.
    while j_nao_atendidas:
        iteracao_construtiva += 1
        
        if LOG_CONSTRUTIVO_GERAL:
            if iteracao_construtiva % 50 == 0 or len(j_nao_atendidas) <= 5:
                print(f"--- Log Const. {iteracao_construtiva}: Clientes faltantes: {len(j_nao_atendidas)}/{n} ---")
        
        # Heurística de priorização: Se houver candidatos, prioriza os mais restritivos (menor L)
        candidatos_globais = gerar_candidatos(j_nao_atendidas, FATOR_PESO_L, FATOR_PESO_E, rotas_em_construcao)

        if candidatos_globais and len(j_nao_atendidas) > 0:
            js_unicos = list(set(c['j'] for c in candidatos_globais if 'j' in c))
            if len(js_unicos) > 0:
                js_ordenados = sorted(js_unicos, key=lambda x: dados.l[x-1])
                j1 = js_ordenados[0]
                # Apenas candidatos para o cliente mais restritivo
                candidatos_finais = [c for c in candidatos_globais if c['j'] == j1]
            else:
                 candidatos_finais = candidatos_globais 
        else:
             candidatos_finais = candidatos_globais
        
        # ----------------------------------------------------------------------
        # FASE DEADLOCK/FECHAMENTO
        # ----------------------------------------------------------------------
        
        if not candidatos_finais:
            # Tenta fechar rotas abertas
            rotas_abertas = list(rotas_em_construcao.items())
            if rotas_abertas:
                candidatos_retorno = []
                for (k, v), rota_data in rotas_em_construcao.items():
                    i = rota_data["rota"][-1]
                    if i != 0: 
                        T_chegada_garagem = rota_data["tempo_fim_servico"] + dados.T[i][0]
                        # A rota de retorno deve ser factível (Tmax)
                        if (T_chegada_garagem - rota_data["chegada"][0]) <= dados.Tmax + TOLERANCIA:
                            custo_adicional = dados.c[i][0]
                            candidatos_retorno.append({"k": k, "v": v, "custo_adicional": custo_adicional, "T_chegada_garagem": T_chegada_garagem})
                
                if candidatos_retorno:
                    if LOG_CONSTRUTIVO_GERAL: print(f"--- Log Const. {iteracao_construtiva}: Deadlock: Candidatos Globais = 0. Tentando Fechar Rotas. ---")
                        
                    slot_escolhido_retorno = min(candidatos_retorno, key=lambda x: x['custo_adicional']) 
                    k, v = slot_escolhido_retorno['k'], slot_escolhido_retorno['v']
                    rota_data = rotas_em_construcao[(k, v)]
                    T_chegada_garagem = slot_escolhido_retorno['T_chegada_garagem']
                    
                    bus_status[k]["tempo"] = T_chegada_garagem 
                    bus_status[k]["viagem"] += 1 
                    rota_data["rota"].append(0)
                    rota_data["chegada"].append(T_chegada_garagem)
                    solucao["onibus"][str(k)][f"viagem_{v}"] = rota_data
                    del rotas_em_construcao[(k, v)] 
                    continue 
                
            # Tenta ROTA DE RESGATE (última chance)
            if j_nao_atendidas:
                j_restritivo = min(j_nao_atendidas, key=lambda j: dados.l[j - 1])
                melhor_resgate = None
                melhor_custo_resgate = float('inf')
                
                for k in range(1, m + 1):
                    v = bus_status[k]["viagem"]
                    if v > r_max: continue
                    tempo_retorno_ultimo = bus_status[k]["tempo"]
                    T_chegada_inicio_viagem = tempo_retorno_ultimo 
                    
                    is_possible = pode_inserir_requisicao([0], [T_chegada_inicio_viagem], j_restritivo, T_chegada_inicio_viagem, dados)

                    if is_possible:
                        # Se for possível, calcula o custo e tempo final
                        T_partida_garagem = T_chegada_inicio_viagem + dados.s[0]
                        chegada_estimada = T_partida_garagem + dados.T[0][j_restritivo]
                        inicio_servico = max(chegada_estimada, dados.e[j_restritivo-1])
                        melhor_tempo_fim_servico = inicio_servico + dados.s[j_restritivo]
                        T_chegada_final = melhor_tempo_fim_servico + dados.T[j_restritivo][0]
                        custo_resgate = dados.c[0][j_restritivo] + dados.c[j_restritivo][0]
                        
                        if custo_resgate < melhor_custo_resgate:
                            melhor_custo_resgate = custo_resgate
                            melhor_resgate = {
                                "k": k, "v": v, 
                                "rota": [0, j_restritivo, 0], 
                                "chegada": [T_chegada_inicio_viagem, inicio_servico, T_chegada_final]
                            }

                if melhor_resgate:
                    k, v = melhor_resgate['k'], melhor_resgate['v']
                    T_chegada_final = melhor_resgate['chegada'][-1]
                    bus_status[k]["tempo"] = T_chegada_final
                    bus_status[k]["viagem"] += 1
                    solucao["onibus"][str(k)][f"viagem_{v}"] = {"rota": melhor_resgate['rota'], "chegada": melhor_resgate['chegada']}
                    j_nao_atendidas.remove(j_restritivo)
                    continue
                        
                # Deadlock real (falha na rota de resgate)
                cliente_restritivo_faltante = j_restritivo
                print(f"--- Log CRÍTICO {iteracao_construtiva}: DEADLOCK REAL - Rota de resgate impossível para R{cliente_restritivo_faltante}. ---")
                return None, cliente_restritivo_faltante 
                
            cliente_restritivo_faltante = None
            if j_nao_atendidas: cliente_restritivo_faltante = min(j_nao_atendidas, key=lambda j: dados.l[j - 1])
            print(f"--- Log CRÍTICO {iteracao_construtiva}: DEADLOCK REAL - Falha em Resgate e Fechamento. Cliente R{cliente_restritivo_faltante} impossível. ---")
            return None, cliente_restritivo_faltante 
        
        # ----------------------------------------------------------------------
        # C. FASE 3: APLICAÇÃO DO MELHOR CANDIDATO ENCONTRADO (Normal)
        # ----------------------------------------------------------------------

        if not j_nao_atendidas: continue 

        # Escolha por Roleta
        slot_escolhido = escolher_slot_por_probabilidade(candidatos_finais, dados)

        j_escolhido = slot_escolhido['j']
        k, v = slot_escolhido['k'], slot_escolhido['v']
        T_chegada_real_j = slot_escolhido['melhor_tempo_fim_servico'] - dados.s[j_escolhido]
        
        if LOG_CONSTRUTIVO_DETALHADO:
            tipo = slot_escolhido['tipo']
            eta_valor = slot_escolhido['heuristica_eta']
            print(f"--- Log Const. {iteracao_construtiva}: Cliente {j_escolhido} atendido por k={k}, v={v} ({tipo}). Heurística (Eta) = {eta_valor:.4f} ---")


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

    # FASE DE FINALIZAÇÃO 
    rotas_abertas = list(rotas_em_construcao.items())
    for (k, v), rota_data in rotas_abertas:
         T_chegada_garagem = rota_data["tempo_fim_servico"] + dados.T[rota_data["rota"][-1]][0]
         rota_data["rota"].append(0)
         rota_data["chegada"].append(T_chegada_garagem)
         solucao["onibus"][str(k)][f"viagem_{v}"] = rota_data

    return solucao, None 


# =============================================================================
# 4. BUSCA LOCAL (VND: OPERADORES)
# =============================================================================

def recalcular_chegadas_e_validar_rota(rota: List[int], t_partida: float, dados: Any) -> Optional[List[float]]:
    """
    Recalcula a factibilidade temporal para uma rota após uma modificação.
    """
    chegadas = [t_partida]
    if len(rota) <= 1: return None 
    
    if len(rota) == 2 and rota == [0, 0]:
         chegadas.append(chegadas[0])
         return chegadas 
         
    u_init, v_init = rota[0], rota[1]
    
    if v_init != 0:
        tempo_saida_u_init = t_partida + dados.s[u_init] 
        chegada_em_v_init = tempo_saida_u_init + dados.T[u_init][v_init]
        inicio_servico_v_init = max(chegada_em_v_init, dados.e[v_init-1])
        if inicio_servico_v_init > dados.l[v_init-1] + TOLERANCIA: return None 
        chegadas.append(inicio_servico_v_init)
    elif len(rota) == 2 and v_init == 0:
         chegadas.append(t_partida)
         return chegadas
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

# --- OPERADOR 1: RELOCATE (1-0 Shift/Inter) - AMOSTRAGEM REINTRODUZIDA ---

def busca_local_relocate(solucao: Any, dados: Any, contador: Contador) -> Tuple[Any, bool]:
    chaves_k = list(solucao.rota.keys())
    TOLERANCIA_CUSTO = 1e-4
    # Limite de amostragem AGRESSIVO RESTAURADO: 3 slots. VND SUPERFICIAL E RÁPIDO.
    AMOSTRA_J = 3 

    for k_orig in chaves_k:
        chaves_v = list(solucao.rota.get(k_orig, {}).keys())
        for v_orig in chaves_v:
            if v_orig not in solucao.rota.get(k_orig, {}): continue 
            rota_orig = solucao.rota[k_orig][v_orig]
            
            # Tenta mover cada cliente (i)
            for i in range(1, len(rota_orig) - 1):
                cliente_a_mover = rota_orig[i]
                rota_orig_recortada = rota_orig[:i] + rota_orig[i+1:]
                t_partida_orig = solucao.chegada[k_orig][v_orig][0]
                
                # CÁLCULO DE REMOÇÃO: Precisa ser validado
                novas_chegadas_orig = None
                if len(rota_orig_recortada) > 2:
                    novas_chegadas_orig = recalcular_chegadas_e_validar_rota(rota_orig_recortada, t_partida_orig, dados)
                    
                    if novas_chegadas_orig is None: continue 
                    
                custo_antigo_orig = calcular_custo_rota(rota_orig, dados)
                custo_novo_orig = calcular_custo_rota(rota_orig_recortada, dados)
                
                # Tenta INSERIR em todos os destinos possíveis
                for k_dest in range(1, dados.K + 1):
                    
                    # 2A. Inserir em VIAGENS EXISTENTES (Relocate Inter e Shift Intra)
                    chaves_v_dest = list(solucao.rota.get(k_dest, {}).keys())
                    for v_dest in chaves_v_dest:
                        rota_dest_base = solucao.rota[k_dest][v_dest]
                        t_partida_dest = solucao.chegada[k_dest][v_dest][0]
                        custo_antigo_dest = calcular_custo_rota(rota_dest_base, dados)
                        
                        # Lógica especial para "Shift" (mesma rota)
                        if k_dest == k_orig and v_dest == v_orig:
                            rota_dest_base = rota_orig_recortada
                            t_partida_dest = t_partida_orig
                            custo_antigo_dest = custo_novo_orig 
                            
                        # --- INÍCIO DA AMOSTRAGEM DE POSIÇÕES (j) ---
                        max_posicoes = len(rota_dest_base)
                        indices_j = list(range(1, max_posicoes)) # Posições entre o primeiro 0 e o último 0
                        
                        # Se a rota é grande, amostra AMOSTRA_J posições (ou todas se for pequena)
                        if max_posicoes > AMOSTRA_J + 1:
                            indices_j = random.sample(indices_j, AMOSTRA_J) 
                            
                        for j in indices_j: # Itera apenas nas posições amostradas
                            # --- FIM DA AMOSTRAGEM DE POSIÇÕES (j) ---
                            
                            # Se for a mesma rota (Shift), pule a posição original
                            if k_dest == k_orig and v_dest == v_orig and j == i: continue
                            
                            rota_dest_nova = rota_dest_base[:j] + [cliente_a_mover] + rota_dest_base[j:]
                            novas_chegadas_dest = recalcular_chegadas_e_validar_rota(rota_dest_nova, t_partida_dest, dados)
                            
                            if novas_chegadas_dest is None: continue 
                            
                            custo_novo_dest = calcular_custo_rota(rota_dest_nova, dados)
                            
                            if k_dest == k_orig and v_dest == v_orig:
                                delta_custo = custo_novo_dest - custo_antigo_orig
                            else:
                                delta_custo = (custo_novo_orig + custo_novo_dest) - (custo_antigo_orig + custo_antigo_dest)
                                
                            if delta_custo < -TOLERANCIA_CUSTO: 
                                
                                # APLICAÇÃO DO MOVIMENTO (First Improvement)
                                if len(rota_orig_recortada) > 2:
                                    solucao.rota[k_orig][v_orig] = rota_orig_recortada
                                    solucao.chegada[k_orig][v_orig] = novas_chegadas_orig
                                else:
                                    if k_orig in solucao.rota and v_orig in solucao.rota[k_orig]:
                                        del solucao.rota[k_orig][v_orig]
                                        del solucao.chegada[k_orig][v_orig]
                                        
                                if k_dest not in solucao.rota: solucao.rota[k_dest] = {}; solucao.chegada[k_dest] = {}
                                solucao.rota[k_dest][v_dest] = rota_dest_nova
                                solucao.chegada[k_dest][v_dest] = novas_chegadas_dest
                                
                                # ATUALIZA O FX INCREMENTALMENTE
                                solucao.fx += delta_custo
                                
                                # Limpeza e Retorno Imediato (First Improvement)
                                for k_clean in list(solucao.rota.keys()):
                                    for v_clean in list(solucao.rota[k_clean].keys()):
                                        if len(solucao.rota[k_clean][v_clean]) <= 2:
                                            del solucao.rota[k_clean][v_clean]
                                            del solucao.chegada[k_clean][v_clean]
                                    if not solucao.rota.get(k_clean): 
                                        if k_clean in solucao.rota: del solucao.rota[k_clean]
                                        if k_clean in solucao.chegada: del solucao.chegada[k_clean]
                                        
                                return solucao, True # Melhoria encontrada, retorna!
                                
                    # 2B. Tentar inserir em uma NOVA VIAGEM (Relocate New Trip)
                    if len(solucao.rota.get(k_dest, {})) < dados.r:
                        tempo_disponivel = 0.0
                        if solucao.rota.get(k_dest): 
                            ultima_v = max(solucao.rota[k_dest].keys())
                            tempo_disponivel = solucao.chegada[k_dest][ultima_v][-1] 
                        
                        T_saida_min_disponivel = tempo_disponivel + dados.s[0]
                        T_partida_ideal_janela = dados.e[cliente_a_mover-1] - dados.s[0] - dados.T[0][cliente_a_mover] 
                        t_partida_nova_viagem = max(T_partida_ideal_janela, T_saida_min_disponivel)
                        
                        rota_dest_nova = [0, cliente_a_mover, 0]
                        novas_chegadas_dest = recalcular_chegadas_e_validar_rota(rota_dest_nova, t_partida_nova_viagem, dados)

                        if novas_chegadas_dest is None: continue 
                            
                        custo_novo_dest = calcular_custo_rota(rota_dest_nova, dados)
                        delta_custo = (custo_novo_orig + custo_novo_dest) - custo_antigo_orig
                        
                        if delta_custo < -TOLERANCIA_CUSTO:
                            
                            # APLICAÇÃO DO MOVIMENTO (First Improvement)
                            if len(rota_orig_recortada) <= 2:
                                if k_orig in solucao.rota and v_orig in solucao.rota[k_orig]:
                                    del solucao.rota[k_orig][v_orig]
                                    del solucao.chegada[k_orig][v_orig]
                            else:
                                solucao.rota[k_orig][v_orig] = rota_orig_recortada
                                solucao.chegada[k_orig][v_orig] = novas_chegadas_orig
                            
                            nova_v_dest = len(solucao.rota.get(k_dest, {})) + 1
                            if k_dest not in solucao.rota:
                                solucao.rota[k_dest] = {}
                                solucao.chegada[k_dest] = {}
                            solucao.rota[k_dest][nova_v_dest] = rota_dest_nova
                            solucao.chegada[k_dest][nova_v_dest] = novas_chegadas_dest
                            
                            # ATUALIZA O FX INCREMENTALMENTE
                            solucao.fx += delta_custo
                            
                            # Limpeza e Retorno Imediato (First Improvement)
                            for k_clean in list(solucao.rota.keys()):
                                for v_clean in list(solucao.rota[k_clean].keys()):
                                    if len(solucao.rota[k_clean][v_clean]) <= 2:
                                        del solucao.rota[k_clean][v_clean]
                                        del solucao.chegada[k_clean][v_clean]
                                    if not solucao.rota.get(k_clean): 
                                        if k_clean in solucao.rota: del solucao.rota[k_clean]
                                        if k_clean in solucao.chegada: del solucao.chegada[k_clean]
                                        
                            return solucao, True # Melhoria encontrada, retorna!


    # Limpeza final de dicionários vazios (para segurança)
    for k in list(solucao.rota.keys()):
        for v in list(solucao.rota[k].keys()):
            if len(solucao.rota[k][v]) <= 2:
                del solucao.rota[k][v]
                del solucao.chegada[k][v]
        if not solucao.rota.get(k): 
            if k in solucao.rota: del solucao.rota[k]
            if k in solucao.chegada: del solucao.chegada[k]
                
    return solucao, False

# --- OPERADOR 2: 2-OPT (Intra-Rota) ---

def busca_local_2opt(solucao: Any, dados: Any, contador: Contador) -> Tuple[Any, bool]:
    """
    Tenta o 2-Opt (Inversão de arestas) intra-rota.
    """
    chaves_k = list(solucao.rota.keys())
    TOLERANCIA_CUSTO = 1e-4

    for k in chaves_k:
        chaves_v = list(solucao.rota.get(k, {}).keys())
        for v in chaves_v:
            if v not in solucao.rota.get(k, {}): continue 
            rota = solucao.rota[k][v]
            t_partida = solucao.chegada[k][v][0]
            
            custo_orig = calcular_custo_rota(rota, dados)
            
            if len(rota) < 4: continue 

            for i in range(1, len(rota) - 2): 
                for j in range(i + 1, len(rota) - 1): 
                    
                    segmento_invertido = rota[i:j+1][::-1]
                    nova_rota = rota[:i] + segmento_invertido + rota[j+1:]

                    novas_chegadas = recalcular_chegadas_e_validar_rota(nova_rota, t_partida, dados)
                    
                    if novas_chegadas is None: continue
                        
                    custo_novo = calcular_custo_rota(nova_rota, dados)
                    delta_custo = custo_novo - custo_orig
                    
                    if delta_custo < -TOLERANCIA_CUSTO:
                        # Aplica o movimento (First Improvement)
                        solucao.rota[k][v] = nova_rota
                        solucao.chegada[k][v] = novas_chegadas
                        # ATUALIZA O FX INCREMENTALMENTE
                        solucao.fx += delta_custo
                        
                        return solucao, True # Melhoria encontrada, retorna!

    return solucao, False

# =============================================================================
# 5. RUÍNA E RECONSTRUÇÃO (PERTURBAÇÃO ILS)
# =============================================================================

def calcular_custo_marginal(rota: List[int], chegadas: List[float], dados: Dados) -> List[float]:
    """
    Calcula a contribuição marginal de custo de cada cliente na rota (Worst Ruin).
    """
    marginais = []
    if len(rota) <= 2: return marginais # Rota [0, 0]

    for i in range(1, len(rota) - 1):
        cliente = rota[i]
        no_anterior = rota[i-1]
        no_proximo = rota[i+1]

        # Custo da remoção = Custo das duas arestas removidas - Custo da nova aresta
        custo_remocao = (dados.c[no_anterior][cliente] + dados.c[cliente][no_proximo]) - dados.c[no_anterior][no_proximo]
        
        marginais.append((cliente, i, custo_remocao)) 
        
    return marginais

def ruina_reconstrucao(melhor_solucao_obj: Solucao, dados: Dados, fator_ruina: float, contador: Contador) -> Optional[Dict]:
    """
    Executa a perturbação de Ruína e Reconstrução (Worst Ruin + Greedy Reinsert).
    """
    temp_solucao = copy.deepcopy(melhor_solucao_obj)
    
    # 1. RUÍNA: Seleção dos Piores Clientes (Worst Ruin)
    lista_custos_marginais = []
    
    for k in temp_solucao.rota.keys():
        for v in temp_solucao.rota[k].keys():
            rota_data = temp_solucao.rota[k][v]
            chegadas_data = temp_solucao.chegada[k][v]
            if len(rota_data) > 2:
                marginais = calcular_custo_marginal(rota_data, chegadas_data, dados)
                for cliente, pos, custo in marginais:
                    lista_custos_marginais.append({"cliente": cliente, "k": k, "v": v, "pos": pos, "custo": custo})
            
    if not lista_custos_marginais: return None

    # Ordena pelo custo de remoção (decrescente) e seleciona os piores
    lista_custos_marginais.sort(key=lambda x: x['custo'], reverse=True)
    
    n_clientes_remover = round(fator_ruina * dados.n)
    clientes_a_remover_raw = lista_custos_marginais[:min(n_clientes_remover, len(lista_custos_marginais))]
    clientes_orfãos = set(c['cliente'] for c in clientes_a_remover_raw)

    # 2. FASE DE REMOÇÃO E CONSOLIDAÇÃO (Fechamento/ajuste das rotas)
    for k in list(temp_solucao.rota.keys()):
        for v in list(temp_solucao.rota[k].keys()):
            rota_original = temp_solucao.rota[k][v]
            
            nova_rota_raw = [n for n in rota_original if n not in clientes_orfãos]
            
            if len(nova_rota_raw) > 2:
                t_partida = temp_solucao.chegada[k][v][0]
                novas_chegadas_kv = recalcular_chegadas_e_validar_rota(nova_rota_raw, t_partida, dados)
                
                if novas_chegadas_kv is not None:
                    temp_solucao.rota[k][v] = nova_rota_raw
                    temp_solucao.chegada[k][v] = novas_chegadas_kv
                else:
                    clientes_orfãos.update([n for n in rota_original if n not in nova_rota_raw and n != 0])
                    del temp_solucao.rota[k][v]
                    del temp_solucao.chegada[k][v]
            elif len(nova_rota_raw) <= 2:
                del temp_solucao.rota[k][v]
                del temp_solucao.chegada[k][v]

    # Recalcula FX da solução parcial (NÃO AVALIA, apenas calcula o FX para ser usado como base)
    temp_solucao.fx = 0.0
    for k in temp_solucao.rota.keys():
        for v in temp_solucao.rota[k].keys():
            temp_solucao.fx += calcular_custo_rota(temp_solucao.rota[k][v], dados)

    # 3. RECONSTRUÇÃO: Inserção Gulosa (Greedy Reinsert - Best Cost)
    clientes_a_inserir = list(clientes_orfãos)
    random.shuffle(clientes_a_inserir) 
    
    for cliente in clientes_a_inserir:
        melhor_delta = float('inf')
        melhor_slot = None
        
        # Procura o melhor slot em ROTAS EXISTENTES
        for k in range(1, dados.K + 1):
            for v in temp_solucao.rota.get(k, {}).keys():
                rota_base = temp_solucao.rota[k][v]
                t_partida = temp_solucao.chegada[k][v][0]
                custo_base = calcular_custo_rota(rota_base, dados)
                
                # RECONSTRUÇÃO AGORA COM AMOSTRAGEM RÁPIDA (AMOSTRA_J_RNR = 3)
                max_posicoes = len(rota_base)
                indices_j = list(range(1, max_posicoes))
                
                # APLICAÇÃO DA AMOSTRAGEM AQUI para acelerar: 
                # Se a rota é grande, amostra AMOSTRA_J_RNR posições (ou todas se for pequena)
                if max_posicoes > AMOSTRA_J_RNR + 1:
                    indices_j = random.sample(indices_j, AMOSTRA_J_RNR)
                
                for j in indices_j: # Itera nas posições amostradas
                    rota_candidata = rota_base[:j] + [cliente] + rota_base[j:]
                    chegadas_candidatas = recalcular_chegadas_e_validar_rota(rota_candidata, t_partida, dados)
                    
                    if chegadas_candidatas is not None:
                        custo_novo = calcular_custo_rota(rota_candidata, dados)
                        delta = custo_novo - custo_base
                        
                        if delta < melhor_delta:
                            melhor_delta = delta
                            melhor_slot = (k, v, rota_candidata, chegadas_candidatas)
            
                        
        # Procura o melhor slot em NOVA VIAGEM
        for k in range(1, dados.K + 1):
            if len(temp_solucao.rota.get(k, {})) < dados.r:
                nova_v = len(temp_solucao.rota.get(k, {})) + 1
                
                tempo_retorno_ultimo = 0.0
                if temp_solucao.rota.get(k): 
                    ultima_v = max(temp_solucao.rota[k].keys())
                    tempo_retorno_ultimo = temp_solucao.chegada[k][ultima_v][-1] 
                
                T_saida_min_disponivel = tempo_retorno_ultimo + dados.s[0]
                T_partida_ideal_janela = dados.e[cliente-1] - dados.s[0] - dados.T[0][cliente] 
                t_partida_nova_viagem = max(T_partida_ideal_janela, T_saida_min_disponivel)
                
                rota_candidata = [0, cliente, 0]
                chegadas_candidatas = recalcular_chegadas_e_validar_rota(rota_candidata, t_partida_nova_viagem, dados)
                
                if chegadas_candidatas is not None:
                    custo_novo = calcular_custo_rota(rota_candidata, dados)
                    delta = custo_novo # Delta é o custo total da nova rota
                    
                    if delta < melhor_delta:
                        melhor_delta = delta
                        melhor_slot = (k, nova_v, rota_candidata, chegadas_candidatas)
        
        # Aplica o melhor slot encontrado
        if melhor_slot:
            k, v, nova_rota, novas_chegadas = melhor_slot
            
            if v in temp_solucao.rota.get(k, {}):
                custo_antigo_base = calcular_custo_rota(temp_solucao.rota[k][v], dados)
                temp_solucao.fx -= custo_antigo_base
                
            temp_solucao.fx += melhor_delta 
            temp_solucao.rota.setdefault(k, {})[v] = nova_rota
            temp_solucao.chegada.setdefault(k, {})[v] = novas_chegadas
    
    # A solução deve ser avaliada globalmente na função 'resolva' para contar 1 avaliação.
    solucao_dict = {
        "fx": temp_solucao.fx, 
        "onibus": {
            str(k): {
                f"viagem_{v}": {"rota": r, "chegada": c}
                for v, (r, c) in zip(temp_solucao.rota[k].keys(), zip(temp_solucao.rota[k].values(), temp_solucao.chegada[k].values()))
            }
            for k in temp_solucao.rota.keys() if temp_solucao.rota[k] 
        }
    }
    return solucao_dict

# =============================================================================
# 6. FUNÇÃO OFICIAL DE ENTREGA (`resolva`) - Aplicando ACO + VND (Multi-Colônia)
# =============================================================================

def inicializar_colonia(dados, perfil):
    """Gera parâmetros e feromônio para uma colônia com um perfil específico."""
    
    # Fatores heurísticos de construção (L e E)
    FATOR_L_SEGURO = 6.0 # Parâmetro de segurança que evita deadlocks (uso no Ouro)
    FATOR_E_SEGURO = 1.0 
    
    FATOR_L_EXPL = 2.0 # Parâmetro mais arriscado para forçar deadlock (uso no Explorador e Guloso)
    FATOR_E_EXPL = 0.5 

    params = {}
    if perfil == 1: # Explorador (ACO Clássico - Arriscado)
        params = {'alpha': round(random.uniform(2.5, 4.0), 2), 
                  'beta': round(random.uniform(1.0, 2.0), 2), 
                  'rho': round(random.uniform(0.02, 0.05), 3),
                  'Q': 2000.0, 'fator_elite': 6.0, 'nome': 'Explorador',
                  'FATOR_L': FATOR_L_EXPL, 'FATOR_E': FATOR_E_EXPL}
    elif perfil == 2: # Guloso (Heurístico Forte - Arriscado)
        params = {'alpha': round(random.uniform(1.0, 2.0), 2), 
                  'beta': round(random.uniform(4.0, 6.0), 2), 
                  'rho': round(random.uniform(0.05, 0.1), 3),
                  'Q': 1000.0, 'fator_elite': 4.0, 'nome': 'Guloso',
                  'FATOR_L': FATOR_L_EXPL, 'FATOR_E': FATOR_E_EXPL}
    elif perfil == 3: # Colônia de Ouro (Parâmetros que encontraram 129k - Seguro)
        params = {'alpha': 2.44, 
                  'beta': 3.66,  
                  'rho': 0.111,  
                  'Q': 1000.0, 'fator_elite': 6.0, 'nome': 'Ouro_129k',
                  'FATOR_L': FATOR_L_SEGURO, 'FATOR_E': FATOR_E_SEGURO}
    else: 
        # Fallback (Seguro)
        params = {'alpha': round(random.uniform(1.8, 3.0), 2), 
                  'beta': round(random.uniform(2.5, 4.5), 2), 
                  'rho': round(random.uniform(0.1, 0.15), 3), 
                  'Q': 1500.0, 'fator_elite': 5.0, 'nome': 'Estável_Fallback',
                  'FATOR_L': FATOR_L_SEGURO, 'FATOR_E': FATOR_E_SEGURO}

    # feromonio é inicializado apenas se necessário (não usado aqui, mapa é passado)
    feromonio = np.full((dados.n + 1, dados.n + 1), 1e-4)
    return params, feromonio

def resolva(dados: Dados, numero_avaliacoes: int) -> Solucao:
    
    # Inicializa os Mapas de Feromônio (persistem entre iterações)
    colonia1_mapa = np.full((dados.n + 1, dados.n + 1), 1e-4)
    colonia2_mapa = np.full((dados.n + 1, dados.n + 1), 1e-4)
    colonia3_mapa = np.full((dados.n + 1, dados.n + 1), 1e-4)
    
    colonias = [
        {'id': 1, 'nome': 'Explorador', 'mapa': colonia1_mapa},
        {'id': 2, 'nome': 'Guloso', 'mapa': colonia2_mapa},
        {'id': 3, 'nome': 'Ouro_129k', 'mapa': colonia3_mapa}
    ]

    melhor_solucao = Solucao()
    melhor_solucao_dict = None 
    melhor_custo = float('inf')
    
    contador = Contador()
    contador.set_limite(numero_avaliacoes)
    
    # Rastreamento de Soluções Únicas
    solucoes_unicas_hash = set()
    
    print(f"\n--- INICIANDO PROTOCOLO MULTI-COLÔNIA (3x MAS) + VND + ILS ---")
    print(f"Colônia 3 (Ouro) fixada em: a=2.44, b=3.66, r=0.111, Q=1000, FE=6.0")
    print(f"Colônias 1 e 2 (Exploratórias) configuradas para forçar DEADLOCK.")
    print(f"Fator Ruína: {FATOR_RUINA*100:.0f}% (Agressivo) | R&R Reconstrução: {AMOSTRA_J_RNR} slots (Rápida)")
    print(f"Limite de Avaliações (FX): {numero_avaliacoes}. Iniciando...")
    
    # ILS/ACO Loop
    iteracao_global = 0
    while contador.count < numero_avaliacoes:
        iteracao_global += 1
        
        # Roda o ciclo em todas as 3 colônias em sequência
        for idx, colonia_data in enumerate(colonias):
            
            if contador.count >= numero_avaliacoes: break
            
            # --- OTIMIZAÇÃO DE VARIABILIDADE (Se Colônia Exploratória/Guloso) ---
            perfil_id = colonia_data['id']
            # Re-inicializa os parâmetros a cada ciclo (exceto o mapa de feromônio)
            params, _ = inicializar_colonia(dados, perfil_id) 
            feromonio = colonia_data['mapa'] # Obtém o mapa de feromônio atual

            alpha, beta, rho = params['alpha'], params['beta'], params['rho']
            Q, fator_elite = params['Q'], params['fator_elite']
            nome_colonia = params['nome']
            
            # Fatores de construção específicos da colônia
            FATOR_L_COLONIA = params['FATOR_L']
            FATOR_E_COLONIA = params['FATOR_E']
            
            dict_solucao_candidata = None
            tag_origem = "ACO"
            
            # 1. FASE DE GERAÇÃO/PERTURBAÇÃO (ACO ou R&R)
            
            # ACO (Exploração)
            if iteracao_global == 1 or melhor_solucao_dict is None or random.random() < 0.2: 
                dict_solucao_candidata, _ = construir_solucao_global_aco(
                    dados, feromonio, alpha, beta, 
                    FATOR_L_COLONIA, FATOR_E_COLONIA, # Usa Fatores Arriscados/Seguros
                    clientes_iniciais=None
                )
            # R&R (Diversificação)
            else:
                tag_origem = "R&R"
                if melhor_solucao.factivel(dados): 
                     dict_solucao_candidata = ruina_reconstrucao(melhor_solucao, dados, FATOR_RUINA, contador)
                else:
                     # Se a melhor global for inviável (não deve acontecer), refaz ACO seguro.
                     params_seguros = inicializar_colonia(dados, 3)[0] # Parâmetros do Ouro (Seguros)
                     dict_solucao_candidata, _ = construir_solucao_global_aco(
                        dados, feromonio, alpha, beta, 
                        params_seguros['FATOR_L'], params_seguros['FATOR_E'],
                        clientes_iniciais=None
                    )
            
            if dict_solucao_candidata is None:
                # Deadlock Real: Conta como falha, mas força a próxima iteração a aprender.
                if melhor_solucao_dict:
                    # CORRIGIDO: usa atualizar_feromonio
                    colonia_data['mapa'] = atualizar_feromonio(feromonio, melhor_solucao_dict, melhor_custo, rho, Q, dados, fator_elite)
                continue 
            
            # 2. INTENSIFICAÇÃO (VND: Relocate + 2-Opt)
            # (1ª Avaliação contada em dict_para_solucao)
            solucao_obj = dict_para_solucao(dict_solucao_candidata, dados, contador)
            
            if contador.count > numero_avaliacoes: break
                
            if solucao_obj and solucao_obj.factivel(dados, verbose=False): 
                
                custo_construido = solucao_obj.fx # Custo antes do VND
                solucao_polida = copy.deepcopy(solucao_obj)
                
                # VND: Aplica os operadores (Custo de avaliações é ZERO aqui)
                while True:
                    melhorou_iter = False
                    temp_solucao = copy.deepcopy(solucao_polida)

                    # K=1: RELOCATE (Busca com 3 Slots)
                    solucao_polida, melhorou_relocate = busca_local_relocate(solucao_polida, dados, contador)
                    if melhorou_relocate:
                        melhorou_iter = True
                        if not solucao_polida.factivel(dados, verbose=False): solucao_polida = temp_solucao; break
                        continue 
                    
                    # K=2: 2-OPT 
                    solucao_polida, melhorou_2opt = busca_local_2opt(solucao_polida, dados, contador)
                    if melhorou_2opt:
                        melhorou_iter = True
                        if not solucao_polida.factivel(dados, verbose=False): solucao_polida = temp_solucao; break
                        continue 

                    if not melhorou_iter:
                        break
                
                # 3. ATUALIZAÇÃO, RASTREAMENTO E REFORÇO
                
                if solucao_polida.factivel(dados, verbose=False):
                    custo_polido = solucao_polida.fx # Reutiliza o FX incremental
                    
                    # RASTREAMENTO DE SOLUÇÕES ÚNICAS
                    polida_hash = solucao_to_hash(solucao_polida)
                    solucoes_unicas_hash.add(polida_hash)

                    if custo_polido < melhor_custo:
                        melhor_custo = custo_polido
                        melhor_solucao = solucao_polida
                        
                        melhor_solucao_dict = {
                            "fx": melhor_solucao.fx, 
                            "onibus": {
                                str(k): {
                                    f"viagem_{v}": {"rota": r, "chegada": c}
                                    for v, (r, c) in zip(melhor_solucao.rota[k].keys(), zip(melhor_solucao.rota[k].values(), melhor_solucao.chegada[k].values()))
                                }
                                for k in melhor_solucao.rota.keys() if melhor_solucao.rota[k] 
                            }
                        }
                        
                        # NOVO LOG DETALHADO
                        gain_vnd = custo_construido - custo_polido
                        print(f"Nova melhor solução GLOBAL [{nome_colonia}] em Avaliação {contador.count}: Custo = {melhor_custo:.2f}")
                        print(f"   -> Custo Construído (ACO/R&R): {custo_construido:.2f} | Ganho VND: {gain_vnd:.2f}")
                    
                    # Prepara o dicionário da solução polida (reutiliza o FX)
                    solucao_reforco_dict = {
                        "fx": solucao_polida.fx, 
                        "onibus": {
                            str(k): {
                                f"viagem_{v}": {"rota": r, "chegada": c}
                                for v, (r, c) in zip(solucao_polida.rota[k].keys(), zip(solucao_polida.rota[k].values(), solucao_polida.chegada[k].values()))
                            }
                            for k in solucao_polida.rota.keys() if solucao_polida.rota[k] 
                        }
                    }
                    
                    # Reforça o feromônio da COLÔNIA LOCAL com a sua solução polida
                    # CORRIGIDO: usa atualizar_feromonio
                    colonia_data['mapa'] = atualizar_feromonio(feromonio, solucao_reforco_dict, solucao_polida.fx, rho, Q, dados, fator_elite)
                
                # Se a polida for inviável, utiliza a melhor global para reforçar o feromônio local.
                elif melhor_solucao_dict:
                     # CORRIGIDO: usa atualizar_feromonio
                     colonia_data['mapa'] = atualizar_feromonio(feromonio, melhor_solucao_dict, melhor_custo, rho, Q, dados, fator_elite)

            # Se a solução construída for inviável, utiliza a melhor global para reforçar o feromônio local.
            elif melhor_solucao_dict:
                 # CORRIGIDO: usa atualizar_feromonio
                 colonia_data['mapa'] = atualizar_feromonio(feromonio, melhor_solucao_dict, melhor_custo, rho, Q, dados, fator_elite)
        
    print(f"\nFinalizado o ACO + VND + ILS. Total de avaliações contadas (FX): {contador.count}")
    print(f"Melhor Custo Encontrado: {melhor_custo:.2f}")
    print(f"Soluções Únicas Encontradas: {len(solucoes_unicas_hash)}")

    melhor_solucao.debug_info = melhor_solucao_dict # Retorna a solução completa em dict
    return melhor_solucao

# =============================================================================
# 7. BLOCO DE TESTES (Validação das 30 execuções) - Mantido
# =============================================================================
if __name__ == "__main__":
    try:
        # A função salvar_solucao_json deve ser fornecida pelo ambiente
        def salvar_solucao_json(sol, filename):
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

        ARQUIVO_JSON = "pequena.json" 
        dados = carrega_dados_json(os.path.join("dados", ARQUIVO_JSON))
        
        N_evals = 48240 
        
        print(f"--- Teste de 30 Execuções ({ARQUIVO_JSON}) ---")
        print(f"Limite de Avaliações: {N_evals}")

        historico_custos = []
        historico_params = []
        melhor_global_custo = float('inf')
        melhor_global_solucao = None
        melhor_global_params = {}
        
        for i in range(1, 31):
            t_inicio = time.time()
            sol = resolva(dados, N_evals) 
            duracao = time.time() - t_inicio
            
            # Os parâmetros agora estão dentro da estrutura retornada
            params_usados = getattr(sol, 'debug_info', {}).get('params', {}) 
            
            if sol and sol.fx > 0 and sol.fx < float('inf'):
                is_valid = sol.factivel(dados, False) 
                valid_tag = "VALID" if is_valid else "INVALID"
                
                print(f"Exec {i:02d}: Custo = {sol.fx:.2f} | Tempo = {duracao:.2f}s | Status: {valid_tag}")
                
                if is_valid:
                    historico_custos.append(sol.fx)
                    historico_params.append(params_usados)
                    
                    if sol.fx <= melhor_global_custo:
                        if 'melhor_anterior' not in locals() or sol.fx < locals()['melhor_anterior']:
                             print("  -> 🏆 NOVA MELHOR SOLUÇÃO GLOBAL!")
                        locals()['melhor_anterior'] = sol.fx

                        melhor_global_custo = sol.fx
                        melhor_global_solucao = sol
                        melhor_global_params = params_usados
                        salvar_solucao_json(sol, "melhor_solucao_aco.json")
            else:
                print(f"Exec {i:02d}: Nenhuma solução encontrada.")
            
        if historico_custos:
            print("-" * 40)
            print(f"Melhor Custo Global: {min(historico_custos):.2f}")
            print(f"Média dos Custos: {sum(historico_custos)/len(historico_custos):.2f}")
            print(f"Desvio Padrão: {np.std(historico_custos):.2f}")
            # Não imprime a config, pois é multi-colônia
        else:
            print("Falha: Nenhuma solução válida encontrada em 30 tentativas.")

        plt.figure(figsize=(10, 6))
        valid_costs = [c for c in historico_custos if c < float('inf')]
        valid_indices = list(range(1, len(valid_costs) + 1))
        
        if valid_costs:
            plt.plot(valid_indices, valid_costs, marker='o', linestyle='-', color='b')
            best_idx_local = np.argmin(valid_costs)
            
            plt.annotate(f'Melhor Custo Global: {melhor_global_custo:.2f}', 
                            xy=(best_idx_local+1, melhor_global_custo), 
                            xytext=(best_idx_local+1.5, melhor_global_custo + 1000),
                            arrowprops=dict(facecolor='red', shrink=0.05),
                            bbox=dict(boxstyle="round,pad=0.3", fc="yellow", alpha=0.9))
            
        plt.title(f'Multi-Colônia ACO + VND + ILS - {ARQUIVO_JSON}')
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