import numpy as np
import random
import math
import copy
from typing import Dict, Any, Tuple, Optional, List

# IMPORTAÇÃO ROBUSTA: Garante que 'aco' seja importado corretamente
try:
    import aco 
except ImportError:
    from . import aco

from exemplo_prof.dados import Dados
from exemplo_prof.solucao import Solucao

# --- Parâmetros FATOR DE RUÍNA para Multi-Start R&R ---
R_R_FACTORS = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]

class Contador:
    def __init__(self, limite: int):
        self.count = 0
        self.limite = limite
    def incrementar(self, incremento=1):
        """
        Incrementa o contador.
        Nesta versão, SOMENTE o ACO e R&R (Multi-Start) chamam isso. 
        O VND NÃO conta.
        """
        if self.count < self.limite:
            self.count += incremento
            return True
        return False
    def esgotado(self):
        return self.count >= self.limite
    def get_count(self): return self.count

# --- FUNÇÕES AUXILIARES ---

def recalcular_chegadas_e_validar_rota(rota: List[int], t_partida: float, dados: Any) -> Optional[List[float]]:
    """Recalcula a factibilidade temporal para uma rota."""
    chegadas = [t_partida]
    if len(rota) <= 1: return None 
    if len(rota) == 2 and rota == [0, 0]:
         chegadas.append(t_partida); return chegadas 
    
    u_init, v_init = rota[0], rota[1]
    
    if v_init != 0:
        tempo_saida_u_init = t_partida + dados.s[u_init] 
        chegada_em_v_init = tempo_saida_u_init + dados.T[u_init][v_init]
        inicio_servico_v_init = max(chegada_em_v_init, dados.e[v_init-1])
        # Verifica se o início do serviço excede o limite (l) do cliente
        if inicio_servico_v_init > dados.l[v_init-1] + aco.TOLERANCIA: return None 
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
            # Verifica se o início do serviço excede o limite (l) do cliente
            if inicio_servico > dados.l[v-1] + aco.TOLERANCIA: return None 
            chegadas.append(inicio_servico)
        else:
            # Chegada de volta ao depósito (v=0)
            chegadas.append(chegada_em_v) 
            
    # Verifica a restrição de duração máxima da viagem (Tmax)
    if (chegadas[-1] - chegadas[0]) > dados.Tmax + aco.TOLERANCIA: return None
    return chegadas

def calcular_custo_rota(rota: List[int], dados: Any) -> float:
    """Calcula o custo total de uma rota com base nos custos de transição (c)."""
    custo = 0.0
    for i in range(len(rota) - 1): custo += dados.c[rota[i]][rota[i+1]]
    return custo

# --- OPERADORES VND "GRÁTIS" (Sem verificação de contador) ---

def busca_local_relocate(solucao: Solucao, dados: Dados) -> Tuple[Solucao, bool, int]:
    """Tenta mover um cliente para uma nova posição (intra ou inter-viagem/ônibus)."""
    solucao_atual = copy.deepcopy(solucao)
    melhorou = False
    movimentos_testados = 0 
    TOLERANCIA_CUSTO = 1e-3
    melhor_delta = -TOLERANCIA_CUSTO
    melhor_movimento = None
    
    chaves_k = list(solucao_atual.rota.keys())
    
    # Itera sobre todas as rotas e clientes
    for k_orig in chaves_k:
        chaves_v = list(solucao_atual.rota.get(k_orig, {}).keys())
        for v_orig in chaves_v:
            if v_orig not in solucao_atual.rota.get(k_orig, {}): continue 
            rota_orig = solucao_atual.rota[k_orig][v_orig]
            
            # Não move o depósito (índices 0 ou len-1)
            for i in range(1, len(rota_orig) - 1):
                cliente_a_mover = rota_orig[i]
                
                # Rota de origem após remoção
                rota_orig_recortada = rota_orig[:i] + rota_orig[i+1:]
                t_partida_orig = solucao_atual.chegada[k_orig][v_orig][0]
                
                novas_chegadas_orig = None
                if len(rota_orig_recortada) > 2:
                    novas_chegadas_orig = recalcular_chegadas_e_validar_rota(rota_orig_recortada, t_partida_orig, dados)
                    if novas_chegadas_orig is None: continue 
                
                custo_antigo_orig = calcular_custo_rota(rota_orig, dados)
                custo_novo_orig = calcular_custo_rota(rota_orig_recortada, dados)
                
                # Tenta todas as posições de inserção
                for k_dest in range(1, dados.K + 1):
                    chaves_v_dest = list(solucao_atual.rota.get(k_dest, {}).keys())
                    for v_dest in chaves_v_dest:
                        rota_dest_base = solucao_atual.rota[k_dest][v_dest]
                        t_partida_dest = solucao_atual.chegada[k_dest][v_dest][0]
                        custo_antigo_dest = calcular_custo_rota(rota_dest_base, dados)
                        
                        # Caso especial: movimento INTRA-ROTA (a rota de destino é a rota de origem recortada)
                        if k_dest == k_orig and v_dest == v_orig:
                            rota_dest_base = rota_orig_recortada
                            t_partida_dest = t_partida_orig
                            custo_antigo_dest = custo_novo_orig 
                        
                        # Tenta inserir na nova rota (j = posição de inserção)
                        for j in range(1, len(rota_dest_base)):
                            if k_dest == k_orig and v_dest == v_orig and j == i: continue
                            
                            movimentos_testados += 1 
                            
                            rota_dest_nova = rota_dest_base[:j] + [cliente_a_mover] + rota_dest_base[j:]
                            novas_chegadas_dest = recalcular_chegadas_e_validar_rota(rota_dest_nova, t_partida_dest, dados)
                            
                            if novas_chegadas_dest is None: continue 
                            
                            custo_novo_dest = calcular_custo_rota(rota_dest_nova, dados)
                            
                            if k_dest == k_orig and v_dest == v_orig: 
                                delta_custo = custo_novo_dest - custo_antigo_orig
                            else: 
                                delta_custo = (custo_novo_orig + custo_novo_dest) - (custo_antigo_orig + custo_antigo_dest)
                            
                            if delta_custo < melhor_delta: 
                                melhor_delta = delta_custo
                                melhor_movimento = (k_orig, v_orig, i, rota_orig_recortada, novas_chegadas_orig, k_dest, v_dest, rota_dest_nova, novas_chegadas_dest)

    if melhor_movimento:
        melhorou = True
        k_orig, v_orig, i, rota_orig_recortada, novas_chegadas_orig, k_dest, v_dest, rota_dest_nova, novas_chegadas_dest = melhor_movimento
        
        # Aplica a remoção na origem
        if len(rota_orig_recortada) <= 2:
            if k_orig in solucao_atual.rota and v_orig in solucao_atual.rota[k_orig]:
                del solucao_atual.rota[k_orig][v_orig]
                del solucao_atual.chegada[k_orig][v_orig]
        else:
            solucao_atual.rota[k_orig][v_orig] = rota_orig_recortada
            solucao_atual.chegada[k_orig][v_orig] = novas_chegadas_orig
            
        # Aplica a inserção no destino
        solucao_atual.rota.setdefault(k_dest, {})[v_dest] = rota_dest_nova
        solucao_atual.chegada.setdefault(k_dest, {})[v_dest] = novas_chegadas_dest
        solucao_atual.fx += melhor_delta
        
        # Limpeza de rotas vazias
        for k in list(solucao_atual.rota.keys()):
            for v in list(solucao_atual.rota[k].keys()):
                if len(solucao_atual.rota[k][v]) <= 2: 
                    del solucao_atual.rota[k][v]
                    del solucao_atual.chegada[k][v]
            if not solucao_atual.rota.get(k): 
                if k in solucao_atual.rota: del solucao_atual.rota[k]
                if k in solucao_atual.chegada: del solucao_atual.chegada[k]
                
    return solucao_atual, melhorou, movimentos_testados

def busca_local_2opt(solucao: Solucao, dados: Dados) -> Tuple[Solucao, bool, int]:
    """Executa o 2-Opt para otimização intra-rota."""
    solucao_atual = copy.deepcopy(solucao)
    melhorou = False
    movimentos_testados = 0
    TOLERANCIA_CUSTO = 1e-3
    chaves_k = list(solucao_atual.rota.keys())
    melhor_delta_global = -TOLERANCIA_CUSTO
    melhor_movimento_global = None

    for k in chaves_k:
        chaves_v = list(solucao_atual.rota.get(k, {}).keys())
        for v in chaves_v:
            rota_original = solucao_atual.rota[k][v]
            n_rota = len(rota_original)
            
            # A rota deve ter pelo menos 4 nós para haver 2-Opt (0-A-B-0)
            if n_rota < 4: continue 
            
            custo_antigo = calcular_custo_rota(rota_original, dados)
            t_partida = solucao_atual.chegada[k][v][0]

            # Inverte o segmento entre i e j (exclui o 0 inicial e final)
            for i in range(1, n_rota - 2):
                for j in range(i + 1, n_rota - 1):
                    movimentos_testados += 1 
                    
                    # Cria a nova rota invertendo o segmento [i...j]
                    rota_nova = rota_original[:i] + rota_original[i:j+1][::-1] + rota_original[j+1:]
                    
                    # Verifica factibilidade
                    novas_chegadas = recalcular_chegadas_e_validar_rota(rota_nova, t_partida, dados)
                    if novas_chegadas is None: continue 
                    
                    custo_novo = calcular_custo_rota(rota_nova, dados)
                    delta_custo = custo_novo - custo_antigo
                    
                    if delta_custo < melhor_delta_global:
                        melhor_delta_global = delta_custo
                        melhor_movimento_global = (k, v, rota_nova, novas_chegadas)

    if melhor_movimento_global:
        k, v, rota_nova, novas_chegadas = melhor_movimento_global
        solucao_atual.rota[k][v] = rota_nova
        solucao_atual.chegada[k][v] = novas_chegadas
        solucao_atual.fx += melhor_delta_global 
        melhorou = True
        
    return solucao_atual, melhorou, movimentos_testados

def busca_local_swap_inter(solucao: Solucao, dados: Dados) -> Tuple[Solucao, bool, int]:
    """Tenta trocar dois clientes entre viagens (inter-viagem/ônibus)."""
    solucao_atual = copy.deepcopy(solucao)
    melhorou = False
    movimentos_testados = 0
    TOLERANCIA_CUSTO = 1e-3
    melhor_delta = -TOLERANCIA_CUSTO
    melhor_movimento = None
    
    chaves_k = list(solucao_atual.rota.keys())
    
    # Itera sobre todas as viagens (rota 1)
    for k1 in chaves_k:
        chaves_v1 = list(solucao_atual.rota.get(k1, {}).keys())
        for v1 in chaves_v1:
            rota1 = solucao_atual.rota[k1][v1]
            if len(rota1) <= 2: continue # Rota sem clientes
            custo1_antigo = calcular_custo_rota(rota1, dados)
            t_partida1 = solucao_atual.chegada[k1][v1][0]
            
            for i in range(1, len(rota1) - 1): # Cliente A
                cliente_a = rota1[i]
                
                # Itera sobre todas as outras viagens (rota 2)
                for k2 in chaves_k:
                    chaves_v2 = list(solucao_atual.rota.get(k2, {}).keys())
                    for v2 in chaves_v2:
                        if k1 == k2 and v1 == v2: continue # Não é inter
                        rota2 = solucao_atual.rota[k2][v2]
                        if len(rota2) <= 2: continue # Rota sem clientes
                        custo2_antigo = calcular_custo_rota(rota2, dados)
                        t_partida2 = solucao_atual.chegada[k2][v2][0]
                        
                        for j in range(1, len(rota2) - 1): # Cliente B
                            movimentos_testados += 1 
                            cliente_b = rota2[j]
                            
                            # Cria as novas rotas trocando os clientes
                            rota1_nova = rota1[:i] + [cliente_b] + rota1[i+1:]
                            rota2_nova = rota2[:j] + [cliente_a] + rota2[j+1:]
                            
                            # Verifica factibilidade temporal
                            chegadas1_nova = recalcular_chegadas_e_validar_rota(rota1_nova, t_partida1, dados)
                            if chegadas1_nova is None: continue
                            chegadas2_nova = recalcular_chegadas_e_validar_rota(rota2_nova, t_partida2, dados)
                            if chegadas2_nova is None: continue
                            
                            custo1_novo = calcular_custo_rota(rota1_nova, dados)
                            custo2_novo = calcular_custo_rota(rota2_nova, dados)
                            delta_custo = (custo1_novo + custo2_novo) - (custo1_antigo + custo2_antigo)
                            
                            if delta_custo < melhor_delta:
                                melhor_delta = delta_custo
                                melhor_movimento = (k1, v1, rota1_nova, chegadas1_nova, k2, v2, rota2_nova, chegadas2_nova)

    if melhor_movimento:
        melhorou = True
        k1, v1, rota1_nova, chegadas1_nova, k2, v2, rota2_nova, chegadas2_nova = melhor_movimento
        
        # Aplica as mudanças
        solucao_atual.rota[k1][v1] = rota1_nova
        solucao_atual.chegada[k1][v1] = chegadas1_nova
        solucao_atual.rota[k2][v2] = rota2_nova
        solucao_atual.chegada[k2][v2] = chegadas2_nova
        solucao_atual.fx += melhor_delta 
        
    return solucao_atual, melhorou, movimentos_testados

# --- R&R (Chama o contador) ---

def ruina_reconstrucao(melhor_solucao_dict: Dict, dados: Dados, fator_ruina_atual: float, contador: Any) -> Optional[Dict]:
    """
    Executa Ruína e Reconstrução com um fator de ruína específico.
    Consome 1 crédito no contador (na hora de recalcular o FX da rota perturbada).
    """
    temp_solucao = aco.dict_para_solucao(melhor_solucao_dict, dados, contador)
    lista_clientes_em_rota = []
    
    # 1. COLETA DOS CLIENTES ATENDIDOS
    for k in temp_solucao.rota.keys():
        for v in temp_solucao.rota[k].keys():
            rota = temp_solucao.rota[k][v]
            # Coleta todos os clientes (nós 1 a n)
            if len(rota) > 2:
                for i in range(1, len(rota) - 1):
                    lista_clientes_em_rota.append({"cliente": rota[i], "k": k, "v": v, "pos": i})
    
    if not lista_clientes_em_rota: return None
    
    # 2. SELEÇÃO DOS CLIENTES PARA RUÍNA
    n_clientes_remover = round(fator_ruina_atual * dados.n)
    clientes_a_remover_raw = random.sample(lista_clientes_em_rota, min(n_clientes_remover, len(lista_clientes_em_rota)))
    clientes_orfãos = set(c['cliente'] for c in clientes_a_remover_raw)
    
    # 3. EXECUÇÃO DA RUÍNA
    for k in list(temp_solucao.rota.keys()):
        for v in list(temp_solucao.rota[k].keys()):
            rota_original = temp_solucao.rota[k][v]
            nova_rota_raw = [n for n in rota_original if n not in clientes_orfãos]
            
            if len(nova_rota_raw) > 2:
                t_partida = temp_solucao.chegada[k][v][0]
                novas_chegadas_kv = recalcular_chegadas_e_validar_rota(nova_rota_raw, t_partida, dados)
                
                if novas_chegadas_kv is not None:
                    # Atualiza a rota se for factível
                    temp_solucao.rota[k][v] = nova_rota_raw
                    temp_solucao.chegada[k][v] = novas_chegadas_kv
                else:
                    # Se a rota se tornar infactível após a remoção, descarta a viagem
                    clientes_orfãos.update([n for n in rota_original if n != 0])
                    del temp_solucao.rota[k][v]
                    del temp_solucao.chegada[k][v]
            elif len(nova_rota_raw) <= 2:
                # Remove rotas vazias
                del temp_solucao.rota[k][v]
                del temp_solucao.chegada[k][v]
    
    # Prepara o dicionário para a fase de Reparo/Reconstrução (aco.reparar_solucao_incompleta)
    solucao_dict_temp = {"onibus": {str(k): {f"viagem_{v}": {"rota": r, "chegada": c} for v, (r, c) in zip(temp_solucao.rota[k].keys(), zip(temp_solucao.rota[k].values(), temp_solucao.chegada[k].values()))} for k in temp_solucao.rota.keys() if temp_solucao.rota[k]}}
    
    # 4. EXECUÇÃO DA RECONSTRUÇÃO (ACO.reparar_solucao_incompleta usa Regret-2 e Guloso)
    solucao_reconstruida_dict, nao_atendidos = aco.reparar_solucao_incompleta(solucao_dict_temp, clientes_orfãos, dados)
    
    if nao_atendidos: return None
    
    # 5. AVALIAÇÃO DA FUNÇÃO OBJETIVO
    # Avalia o FX da solução reconstruída (Esta é a 1ª contagem do R&R)
    solucao_reconstruida_dict['fx'] = aco.calcular_custo_total_solucao(solucao_reconstruida_dict, dados)
    if contador.count < contador.limite: contador.incrementar() 
    
    return solucao_reconstruida_dict

# --- RESOLVA (ACO -> SA -> MultiR&R -> VND) ---

def resolva(dados: Dados, numero_avaliacoes: int, initial_feromonio: Optional[np.ndarray] = None, initial_solucao_dict: Optional[Dict] = None, stagnation_counter: int = 0) -> Tuple[Solucao, Optional[np.ndarray], Dict]:
    
    contador = Contador(limite=numero_avaliacoes)
    
    def solucao_to_dict(sol: Solucao) -> Dict:
        """Converte o objeto Solucao para o formato Dict de persistência."""
        return {"fx": sol.fx, "onibus": {str(k): {f"viagem_{v}": {"rota": r, "chegada": c} for v, (r, c) in zip(sol.rota[k].keys(), zip(sol.rota[k].values(), sol.chegada[k].values()))} for k in sol.rota.keys() if sol.rota[k]}}

    # 1. CARREGAMENTO E OTIMIZAÇÃO DE PARÂMETROS
    metadados_dict = getattr(dados, 'metadados', {})
    metadados_str = metadados_dict.get('descricao', '').lower()
    # Tenta identificar a instância para carregar os parâmetros otimizados
    instance_name = next((k for k in aco.OPTIMIZED_PARAMS_MAP.keys() if k in metadados_str), 'default')

    params = aco.PARAMS_BASE.copy()
    params.update(aco.OPTIMIZED_PARAMS_MAP.get(instance_name, {}))
    
    # Carrega parâmetros de ACO/SA persistentes
    if initial_solucao_dict:
        for key in ['alpha', 'beta', 'rho', 'greedy_factor', 'p_random_choice', 'fator_ruina', 'temperatura', 'temperatura_inicial']:
            if key in initial_solucao_dict: params[key] = initial_solucao_dict[key] 

    alpha, beta, rho = params['alpha'], params['beta'], params['rho']
    greedy_factor, p_random_choice = params['greedy_factor'], params['p_random_choice']
    
    # NOVO: Obtém a temperatura inicial específica da instância
    temp_inicial_final = params.get('temperatura_inicial', aco.T_INICIAL_BASE) 
    
    # Inicializa Temperatura: usa a persistente se existir, caso contrário usa a da instância
    current_temperatura = initial_solucao_dict.get('temperatura', temp_inicial_final)
    
    FATOR_L_COLONIA = 20.00 if instance_name == 'pequena' else 1.28
    FATOR_E_COLONIA = 0.27
    
    initial_feromonio_base = 1e-4
    feromonio = initial_feromonio.copy() if initial_feromonio is not None else np.full((dados.n + 1, dados.n + 1), initial_feromonio_base)

    melhor_solucao_global = aco.dict_para_solucao(initial_solucao_dict, dados, contador)
    melhor_custo_global = melhor_solucao_global.fx
    melhor_solucao_dict = initial_solucao_dict
    
    solucao_ils_atual = melhor_solucao_global 
    if not solucao_ils_atual.factivel(dados, verbose=False):
         solucao_ils_atual.fx = float('inf')
         
    log_calibracao = []
    total_movimentos_vnd = 0
    total_iteracoes = 0
    
    print(f"\n--- MODO ILS-SA-MultiR&R-VND Ativo (Instância={instance_name.upper()}, T inicial={temp_inicial_final:.2f}, T atual={current_temperatura:.2f}, ρ={rho}) ---", flush=True)

    while contador.count < numero_avaliacoes:
        total_iteracoes += 1
        
        # 1. CONSTRUÇÃO ACO (Gera nova solução candidata)
        dict_solucao_candidata, clientes_nao_atendidos = aco.construir_solucao_global_aco(dados, feromonio.copy(), alpha, beta, FATOR_L_COLONIA, FATOR_E_COLONIA, greedy_factor_retorno=greedy_factor, p_random_choice=p_random_choice)
        origem_construcao = "ACO"
        
        if dict_solucao_candidata is None or (clientes_nao_atendidos is not None and clientes_nao_atendidos):
             stagnation_counter += 1
             continue
        
        solucao_candidata_aco = aco.dict_para_solucao(dict_solucao_candidata, dados, contador)
        fx_candidato_aco = solucao_candidata_aco.fx
        
        # 2. ACEITAÇÃO SIMULATED ANNEALING
        ponto_partida_rr_dict = solucao_to_dict(solucao_ils_atual)
        
        if solucao_ils_atual.fx >= float('inf') - aco.TOLERANCIA_CUSTO:
            aceita_sa = True
        else:
            aceita_sa = aco.sa_acceptance(solucao_ils_atual.fx, fx_candidato_aco, current_temperatura)

        if aceita_sa:
            solucao_ils_atual = solucao_candidata_aco
            ponto_partida_rr_dict = dict_solucao_candidata # Novo ponto de partida (ACO)
            print(f"  -> [Iter {total_iteracoes}, Nmar={contador.get_count()}] SA ACEITO (FX={fx_candidato_aco:.2f}, T={current_temperatura:.2f}).", flush=True)
        else:
            # Mantém solucao_ils_atual, mas usa o candidato ACO como o ponto de partida para o R&R
            ponto_partida_rr_dict = dict_solucao_candidata
            print(f"  -> [Iter {total_iteracoes}, Nmar={contador.get_count()}] SA REJEITADO (Candidato={fx_candidato_aco:.2f}, T={current_temperatura:.2f}). Perturbando o estado atual.", flush=True)


        # --- 3. MULTI-START R&R (PERTURBAÇÃO OTIMIZADA) ---
        melhor_fx_rr = solucao_ils_atual.fx
        melhor_dict_rr = solucao_to_dict(solucao_ils_atual) # Começa com o ponto de partida do SA
        
        # Teste de ruína nos fatores definidos
        for fator_ruina_teste in R_R_FACTORS:
             if contador.esgotado(): break
             
             # Perturba o melhor ponto de partida atual (ponto_partida_rr_dict)
             dict_perturbado = ruina_reconstrucao(ponto_partida_rr_dict, dados, fator_ruina_teste, contador)
             
             if dict_perturbado and dict_perturbado['fx'] < melhor_fx_rr - aco.TOLERANCIA_CUSTO:
                  melhor_fx_rr = dict_perturbado['fx']
                  melhor_dict_rr = dict_perturbado
                  # Se o R&R achar algo melhor, este é o novo ponto de partida para o VND
                  
        solucao_trabalho = aco.dict_para_solucao(melhor_dict_rr, dados, contador)
        fx_antes_vnd = solucao_trabalho.fx


        # 4. VND "INFINITO" (GRÁTIS)
        vnd_melhoria = True
        movimentos_vnd_passo = 0
        
        while vnd_melhoria:
            vnd_melhoria = False
            
            solucao_trabalho, m1, mov_r = busca_local_relocate(solucao_trabalho, dados)
            movimentos_vnd_passo += mov_r
            if m1: vnd_melhoria = True
            
            if not vnd_melhoria:
                solucao_trabalho, m2, mov_2 = busca_local_2opt(solucao_trabalho, dados)
                movimentos_vnd_passo += mov_2
                if m2: vnd_melhoria = True
            
            if not vnd_melhoria:
                solucao_trabalho, m3, mov_s = busca_local_swap_inter(solucao_trabalho, dados)
                movimentos_vnd_passo += mov_s
                if m3: vnd_melhoria = True
            
        total_movimentos_vnd += movimentos_vnd_passo
        
        # 5. ATUALIZAÇÃO E DECAIMENTO DE TEMPERATURA
        if solucao_trabalho.fx < melhor_custo_global - aco.TOLERANCIA_CUSTO:
            # 5A. NOVA MELHORIA GLOBAL
            melhor_custo_global = solucao_trabalho.fx
            melhor_solucao_global = solucao_trabalho
            solucao_ils_atual = solucao_trabalho # A melhor global é o novo ponto de partida

            # RE-HEATING ADAPTATIVO: Reinicia a temperatura para o valor específico da instância
            current_temperatura = temp_inicial_final 
            
            melhoria_vnd = fx_antes_vnd - melhor_custo_global
            log_entry = {
                'iter': total_iteracoes, 'fx_final': melhor_custo_global, 'fx_inicial_aco': fx_candidato_aco,
                'avaliacoes_aco_total': contador.get_count(), 'movimentos_vnd_total': total_movimentos_vnd,
                'origem_construcao': origem_construcao, 'melhoria_vnd': melhoria_vnd, 'movimentos_vnd_passo': movimentos_vnd_passo
            }
            log_calibracao.append(log_entry)
            print(f"  -> [Iter {total_iteracoes}] 🏆 NOVA MELHORIA GLOBAL: {melhor_custo_global:.2f} (ΔVND: {melhoria_vnd:.2f}) -> Reiniciando T={temp_inicial_final:.2f}", flush=True)
            stagnation_counter = 0
        else:
            # Decaimento de Temperatura (Cooling)
            current_temperatura = max(current_temperatura * aco.T_COOLING_RATE, aco.T_MIN)
            stagnation_counter += 1


        # 6. Atualização do Feromônio (Baseado na solução trabalhada pelo VND)
        melhor_solucao_dict_atual = solucao_to_dict(solucao_trabalho)
        feromonio = aco.atualizar_feromonio(feromonio, melhor_solucao_dict_atual, solucao_trabalho.fx, rho, aco.Q, dados)

    # 7. Prepara Dicionário de Persistência
    melhor_solucao_global.debug_info = {'total_avaliacoes': contador.get_count(), 'log_calibracao': log_calibracao, 'total_movimentos_vnd': total_movimentos_vnd}
    
    # Atualiza o dicionário de persistência com os parâmetros finais
    if melhor_solucao_dict is None: melhor_solucao_dict = {}
    melhor_solucao_dict.update({
        'fator_ruina': params.get('fator_ruina', aco.FATOR_RUINA_BASE),
        'temperatura': current_temperatura, # Salva a temperatura final
        'temperatura_inicial': temp_inicial_final, # Salva T_INICIAL da instância
        'alpha': params['alpha'],
        'beta': params['beta'],
        'greedy_factor': params['greedy_factor'],
        'p_random_choice': params['p_random_choice'],
        'rho': params['rho'],
        'stagnation_counter': stagnation_counter,
        'fx': melhor_custo_global
    })
    
    return melhor_solucao_global, feromonio, melhor_solucao_dict