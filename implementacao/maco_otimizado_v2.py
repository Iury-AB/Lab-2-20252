import json
import os
import random
from exemplo_prof.solucao import Solucao
from .Restricoes import eh_factivel
import numpy as np
import math


def dict_para_solucao(dict_solucao, dados):
    sol = Solucao()
    sol.rota = {}
    sol.chegada = {}
    m = dados.K
    r_max = dados.r

    for k in range(m):  # começa do 0
        sol.rota[k] = {}
        sol.chegada[k] = {}
        if str(k) in dict_solucao["onibus"]:
            for v in range(r_max):  # também começa do 0
                viagem_key = f"viagem_{v}"
                if viagem_key in dict_solucao["onibus"][str(k)]:
                    viagem = dict_solucao["onibus"][str(k)][viagem_key]
                    sol.rota[k][v] = viagem["rota"]
                    sol.chegada[k][v] = viagem["chegada"]
                else:
                    sol.rota[k][v] = []
                    sol.chegada[k][v] = []
        else:
            for v in range(r_max):
                sol.rota[k][v] = []
                sol.chegada[k][v] = []
    return sol


def pode_alocar_requisicao(rota, chegada, req, tempo_atual, dados):
    tempo_max_viagem = dados.Tmax
    tempo_servico = dados.s
    tempo_requisicoes = dados.T
    inicio_janela = dados.e
    fim_janela = dados.l
    deslocamento = tempo_requisicoes[rota[-1]][req]
    chegada_estimada = tempo_atual + deslocamento
    inicio_servico = max(chegada_estimada, inicio_janela[req-1])
    fim_servico = inicio_servico + tempo_servico[req]
    if inicio_servico > fim_janela[req-1]:
        return False
    if chegada and  (inicio_servico - chegada[0] + tempo_servico[req])> tempo_max_viagem:
        return False
    return True


def construir_viagem_onibus(requisicoes_restantes, feromonio, alpha, beta, tempoViagem, ultimoEscolhido, dados, peso_urgencia=2.0, prob_deterministica=0.2):
    tempo_servico = dados.s
    tempo_requisicoes = dados.T
    inicio_janela = dados.e
    rota = [0]
    arcos = []
    chegada = []
    tempo_atual = tempoViagem + tempo_servico[0]
    while requisicoes_restantes:
        i = rota[-1]
        candidatos = list(requisicoes_restantes)
        candidatos_viaveis = [j for j in candidatos if pode_alocar_requisicao(rota, chegada, j, tempo_atual, dados)]
        if not candidatos_viaveis:
            break
        
        # Converte para um array NumPy para facilitar os cálculos
        custo_array = np.array(dados.c)

        # Calcula o valor mínimo e máximo da matriz
        min_val = np.min(custo_array)
        max_val = np.max(custo_array)

        # Aplica a normalização min-max
        if max_val - min_val == 0:
            custo_normalizado = np.zeros_like(custo_array)
        else:
            custo_normalizado = (custo_array - min_val) / (max_val - min_val)

        # Calcula probabilidades com urgência
        probabilidades = []
        total = 0
        for j in candidatos_viaveis:
            deslocamento = dados.T[i][j]
            tau = max(1e-3, feromonio[i][j])
            tempo_limite = dados.l[j - 1]
            urgencia = peso_urgencia / (tempo_limite - tempo_atual + 1e-6)
            eta = max(1e-3, 1 / (custo_normalizado[i][j] + 1e-6)* urgencia) 
            valor = math.exp(alpha * math.log(tau + 1e-6) + beta * math.log(eta + 1e-6))
            probabilidades.append((j, valor))
            total += valor

        probabilidades = [(j, v / total) for j, v in probabilidades] if total > 0 else [(j, 0) for j, v in probabilidades]
        
        # Fallback: requisição mais urgente baseada na menor janela fim
        menor_fim = min(dados.l[j-1] for j in requisicoes_restantes)
        urgente = min(candidatos_viaveis, key=lambda j: dados.l[j-1])

        if dados.l[urgente-1] == menor_fim:
            escolhido = urgente
        else:
             # Escolha estocástica ou determinística
            if random.random() < prob_deterministica:
                maior_prob = max(probabilidades, key=lambda x: x[1])[1]
                melhores = [j for j, p in probabilidades if p == maior_prob]
                escolhido = min(melhores)
            else:
                r = random.random()
                acumulado = 0
                for j, p in probabilidades:
                    acumulado += p
                    if r <= acumulado:
                        escolhido = j
                        break
                    else: 
                        escolhido = probabilidades[-1][0]

        #Atualiza tempo e rota
        deslocamento = tempo_requisicoes[rota[-1]][escolhido]
        chegada_estimada = tempo_atual + deslocamento
        inicio_servico = max(chegada_estimada, inicio_janela[escolhido-1])
        tempo_atual = inicio_servico + tempo_servico[escolhido]
        rota.append(escolhido)
        arcos.append([rota[-2], escolhido])
        chegada.append(inicio_servico)
        requisicoes_restantes.remove(escolhido)
        ultimoEscolhido = escolhido
    if len(rota) > 1:
        rota.append(0)
        arcos.append([rota[-2], 0])
        chegada.append(tempo_atual + tempo_requisicoes[rota[-2]][0])
        return {"rota": rota, "arcos": arcos, "chegada": chegada}
    return None 

def construir_solucao_global(feromonio, alpha, beta, rho, dados, Q=100.0):
    n = dados.n
    m = dados.K
    r_max = dados.r
    custo=dados.c
    solucao = {"onibus": {}}
    requisicoes_restantes = set(range(1, n+1))
    for k in range(m):
        viagens = {}
        num_viagens = 0
        ultimoEscolhido = 0
        tempoViagem = 0
        while requisicoes_restantes and num_viagens < r_max:
            viagem = construir_viagem_onibus(requisicoes_restantes, feromonio, alpha, beta, tempoViagem, ultimoEscolhido, dados)
            if viagem:
                    viagens[f"viagem_{num_viagens}"] = viagem
                    num_viagens += 1
                    ultimoEscolhido=max(viagem["rota"])
                    tempoViagem = viagem["chegada"][-1]
            else:
                break
        if viagens:
            solucao["onibus"][str(k)] = viagens
    return solucao

def calcular_fx(solucao, custo):
    fx = 0
    for k in solucao["onibus"]:
        for v in solucao["onibus"][k]:
            arcos = solucao["onibus"][k][v]["arcos"]
            for i, j in arcos:
                fx += custo[i][j]
    return fx

""" def atualizar_feromonio(feromonio, solucao, custo, rho, Q=100.0):
    n = len(feromonio)
    for i in range(n):
        for j in range(n):
            feromonio[i][j] *= (1 - rho)
    for k in solucao["onibus"]:
        for v in solucao["onibus"][k]:
            arcos = solucao["onibus"][k][v]["arcos"]
            for i, j in arcos:
                feromonio[i][j] += Q / custo[i][j] """

def atualizar_feromonio(feromonio, solucao, custo, rho, historico_arcos=None, Q=1.0, penalidade_repeticao=0.5):
    n = len(feromonio)
    
    # Evaporação padrão
    for i in range(n):
        for j in range(n):
            feromonio[i][j] *= (1 - rho)

    
    # Normalização min-max
    min_custo = min(min(row) for row in custo)
    max_custo = max(max(row) for row in custo)

    custo_normalizado = [
        [(c - min_custo) / (max_custo - min_custo + 1e-6) for c in linha]
        for linha in custo
    ]

    # Reforço com penalidade por repetição
    for k in solucao["onibus"]:
        for v in solucao["onibus"][k]:
            arcos = solucao["onibus"][k][v]["arcos"]
            for i, j in arcos:
                delta = Q / (custo_normalizado[i][j] + 1e-6)
                if historico_arcos is not None and (i, j) in historico_arcos:
                    delta *= penalidade_repeticao  # aplica penalidade
                feromonio[i][j] += delta
                feromonio[i][j] = min(feromonio[i][j], 10.0)
                if historico_arcos is not None:
                    historico_arcos.add((i, j))

def reforcar_melhor_global(feromonios, melhores_solucoes_colonia):
    if melhores_solucoes_colonia:
        fx_melhor, solucao_melhor = min(melhores_solucoes_colonia, key=lambda x: x[0])
        delta = 1.0 / (math.log(fx_melhor + 1) + 1e-6)
        for c in range(len(feromonios)):
            for k in solucao_melhor["onibus"]:
                for v in solucao_melhor["onibus"][k]:
                    arcos = solucao_melhor["onibus"][k][v]["arcos"]
                    for i, j in arcos:
                        feromonios[c][i][j] *= (1 + delta)
                        feromonios[c][i][j] = min(feromonios[c][i][j], 10.0)

def perturbar_parametros(param):
    return {
        "alpha": max(0.1, param["alpha"] + random.uniform(-0.3, 0.3)),
        "beta": max(0.1, param["beta"] + random.uniform(-0.3, 0.3)),
        "rho": min(0.9, max(0.1, param["rho"] + random.uniform(-0.05, 0.05)))
    }

def resolva(dados, numero_avaliacoes):
    CHECKPOINT_FILE = "checkpoint.json"
    OUTPUT_FILE = "melhorSolucaoAlcione.json"
    n = dados.n
    m = dados.K
    r_max = dados.r
    custo = dados.c
    NUM_COLONIAS = 4
    NUM_FORMIGAS = 100
    colonia_parametros = [
        {"alpha": 3.0, "beta": 2.0, "rho": 0.1},
        {"alpha": 0.5, "beta": 2.0, "rho": 0.7},
        {"alpha": 1.0, "beta": 5.0, "rho": 0.5},
        {"alpha": 0.1, "beta": 1.0, "rho": 0.9},
    ] 
    
    historico_arcos = set()

    colonia_parametros = [perturbar_parametros(p) for p in colonia_parametros]
    avaliacoes_objetivo = 0
    avaliacoes_acumuladas = 0
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            checkpoint = json.load(f)
        if checkpoint["numeroRequisicoes"] == n:
            #feromonios = checkpoint["feromonios"]
            feromonios = [[[random.uniform(0.5, 1.5) for _ in range(n+1)] for _ in range(n+1)] for _ in range(NUM_COLONIAS)]
            melhor_fx_global = float("inf")
            melhor_solucao_global = None
            #melhor_fx_global = checkpoint["melhor_fx_global"]
            #melhor_solucao_global = checkpoint["melhor_solucao_global"]
            #avaliacoes_acumuladas = checkpoint["avaliacoes_acumuladas"]
        else:
            feromonios = [[[random.uniform(0.5, 1.5) for _ in range(n+1)] for _ in range(n+1)] for _ in range(NUM_COLONIAS)]
            melhor_fx_global = float("inf")
            melhor_solucao_global = None
    else:
        feromonios = [[[random.uniform(0.5, 1.5) for _ in range(n+1)] for _ in range(n+1)] for _ in range(NUM_COLONIAS)]
        melhor_fx_global = float("inf")
        melhor_solucao_global = None
    
    sem_melhora_por_execucoes = [0 for _ in range(NUM_COLONIAS)]
    melhor_fx_colonia = [float("inf") for _ in range(NUM_COLONIAS)]
    try:
        while avaliacoes_objetivo < numero_avaliacoes:
            for c in range(NUM_COLONIAS):
                alpha = colonia_parametros[c]["alpha"]
                beta = colonia_parametros[c]["beta"]
                rho = colonia_parametros[c]["rho"]
                melhores_solucoes_colonia = []
                for f in range(NUM_FORMIGAS):
                    dict_solucao = construir_solucao_global(feromonios[c], alpha, beta, rho, dados)
                    solucao_obj = dict_para_solucao(dict_solucao, dados)
                    if eh_factivel(solucao_obj, dados):
                        fx = calcular_fx(dict_solucao, custo)
                        avaliacoes_objetivo += 1
                        melhores_solucoes_colonia.append((fx, dict_solucao))
                        if fx < melhor_fx_global:
                            melhor_fx_global = fx
                            melhor_solucao_global = dict_solucao
                            print(f"Avaliação {avaliacoes_objetivo}: nova melhor solução global com fx = {melhor_fx_global}")
                        if fx < melhor_fx_colonia[c]:
                            melhor_fx_colonia[c] = fx
                            sem_melhora_por_execucoes[c] = 0
                        else:
                            sem_melhora_por_execucoes[c] += 1
                if sem_melhora_por_execucoes[c] >= 5:
                    colonia_parametros[c]["rho"] = min(0.9, colonia_parametros[c]["rho"] + 0.1)
                    colonia_parametros[c]["alpha"] = max(0.1, colonia_parametros[c]["alpha"] - 0.1)
                    sem_melhora_por_execucoes[c] = 0
                if avaliacoes_objetivo == numero_avaliacoes:
                    break
                if melhores_solucoes_colonia:
                    fx_melhor, solucao_melhor = min(melhores_solucoes_colonia, key=lambda x: x[0])
                    atualizar_feromonio(feromonios[c], solucao_melhor, custo, rho, historico_arcos)
                reforcar_melhor_global(feromonios, melhores_solucoes_colonia)
                print(f"Colônia {c}: melhor fx = {melhor_fx_colonia[c]} após {avaliacoes_objetivo} avaliações")
        resultado = Solucao()
        resultado.fx = melhor_fx_global
        resultado.rota = {}
        resultado.chegada = {}
        for k in range(1, m+1):
            resultado.rota[k] = {}
            resultado.chegada[k] = {}
            for v in range(1, r_max+1):
                if str(k) in melhor_solucao_global["onibus"] and f"viagem_{v-1}" in melhor_solucao_global["onibus"][str(k)]:
                    viagem = melhor_solucao_global["onibus"][str(k)][f"viagem_{v-1}"]
                    resultado.rota[k][v] = viagem["rota"]
                    resultado.chegada[k][v] = viagem["chegada"]
                else:
                    resultado.rota[k][v] = []
                    resultado.chegada[k][v] = []
        if melhor_solucao_global:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(melhor_solucao_global, f, indent=2)
            with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "numeroRequisicoes": n,
                    "feromonios": feromonios,
                    "avaliacoes_objetivo": avaliacoes_objetivo,
                    "avaliacoes_acumuladas": avaliacoes_acumuladas + avaliacoes_objetivo,
                    "melhor_fx_global": melhor_fx_global,
                    "melhor_solucao_global": melhor_solucao_global
                }, f)
        else:
            print(f"Número de avaliações = {avaliacoes_objetivo}. Solução não encontrada!")
        return resultado
    except KeyboardInterrupt:
        if melhor_solucao_global:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(melhor_solucao_global, f, indent=2)
            with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "numeroRequisicoes": n,
                    "feromonios": feromonios,
                    "avaliacoes_objetivo": avaliacoes_objetivo,
                    "avaliacoes_acumuladas": avaliacoes_acumuladas + avaliacoes_objetivo,
                    "melhor_fx_global": melhor_fx_global,
                    "melhor_solucao_global": melhor_solucao_global
                }, f)
            print("Interrupção detectada! Checkpoint salvo com sucesso.")
    except Exception as e:
        if melhor_solucao_global:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(melhor_solucao_global, f, indent=2)
            with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "numeroRequisicoes": n,
                    "feromonios": feromonios,
                    "avaliacoes_objetivo": avaliacoes_objetivo,
                    "avaliacoes_acumuladas": avaliacoes_acumuladas + avaliacoes_objetivo,
                    "melhor_fx_global": melhor_fx_global,
                    "melhor_solucao_global": melhor_solucao_global
                }, f)
            print("Erro inesperado! Checkpoint de emergência salvo.")
        raise e