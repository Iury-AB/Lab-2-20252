import json
import random

with open("pequena.json", "r") as f:
    dados = json.load(f)

n = dados["numeroRequisicoes"]
m = dados["numeroOnibus"]
r_max = dados["numeroMaximoViagens"]
capacidade_onibus = dados.get("capacidade_onibus", 9999)
custo = dados["custo"]
tempo_servico = dados["tempoServico"]
tempo_requisicoes = dados["tempoRequisicoes"]
inicio_janela = dados["inicioJanela"]
fim_janela = dados["fimJanela"]

NUM_COLONIAS = 4
NUM_FORMIGAS = 72
MAX_AVALIACOES = 3000


colonia_parametros = [
    {"alpha": 3.0, "beta": 2.0, "rho": 0.1},  # Exploitation
    {"alpha": 0.5, "beta": 2.0, "rho": 0.7},  # Exploration (alta evaporação)
    {"alpha": 1.0, "beta": 5.0, "rho": 0.5},  # Greedy/Heurística
    {"alpha": 0.1, "beta": 1.0, "rho": 0.9},  # Quase aleatória
]


feromonios = [
    [[1.0 for _ in range(n+1)] for _ in range(n+1)]
    for _ in range(NUM_COLONIAS)
]

melhor_solucao_global = None
melhor_fx_global = float("inf")
avaliacoes = 0

def validar_solucao(solucao):
    atendidas = set()
    for k in solucao["onibus"]:
        for v in solucao["onibus"][k]:
            rota = solucao["onibus"][k][v]["rota"]
            for req in rota:
                if req != 0:
                    atendidas.add(req)
    return len(atendidas) == n

def calcular_fx(solucao):
    fx = 0
    for k in solucao["onibus"]:
        for v in solucao["onibus"][k]:
            arcos = solucao["onibus"][k][v]["arcos"]
            for i, j in arcos:
                fx += custo[i][j]
    return fx

def escolher_proximo(i, candidatos, tempo_atual, feromonio, alpha, beta):
    candidatos.sort(key=lambda j: fim_janela[j-1])
    probabilidades = []
    total = 0
    for j in candidatos:
        deslocamento = tempo_requisicoes[i][j]
        chegada_estimada = tempo_atual + deslocamento
        inicio_servico = max(chegada_estimada, inicio_janela[j-1])
        fim_servico = inicio_servico + tempo_servico[j]
        if inicio_servico > fim_janela[j-1]:
            continue
        tau = feromonio[i][j]
        eta = 1 / (deslocamento + 1e-6)
        valor = (tau ** alpha) * (eta ** beta)
        probabilidades.append((j, valor))
        total += valor
    if not probabilidades or total == 0:
        return None
    probabilidades = [(j, v / total) for j, v in probabilidades]
    r = random.random()
    acumulado = 0
    for j, p in probabilidades:
        acumulado += p
        if r <= acumulado:
            return j
    return probabilidades[-1][0]

def construir_solucao(feromonio, alpha, beta):
    global avaliacoes
    avaliacoes += 1
    solucao = {"onibus": {}}
    requisicoes_restantes = set(range(1, n+1))
    for k in range(m):
        solucao["onibus"][str(k)] = {}
        rota = [0]
        arcos = []
        chegada = []
        tempo_atual = tempo_servico[0]
        capacidade = 0
        while requisicoes_restantes:
            i = rota[-1]
            candidatos = list(requisicoes_restantes)
            escolhido = escolher_proximo(i, candidatos, tempo_atual, feromonio, alpha, beta)
            if escolhido is None:
                break
            deslocamento = tempo_requisicoes[rota[-1]][escolhido]
            chegada_estimada = tempo_atual + deslocamento
            inicio_servico = max(chegada_estimada, inicio_janela[escolhido-1])
            tempo_atual = inicio_servico + tempo_servico[escolhido]
            rota.append(escolhido)
            arcos.append([rota[-2], escolhido])
            chegada.append(inicio_servico)
            requisicoes_restantes.remove(escolhido)
            capacidade += 1
            if capacidade >= r_max:
                break
        if len(rota) > 1:
            solucao["onibus"][str(k)]["viagem_0"] = {
                "rota": rota,
                "arcos": arcos,
                "chegada": chegada
            }
    if validar_solucao(solucao):
        fx = calcular_fx(solucao)
        return fx, solucao
    return None, None

def atualizar_feromonio(feromonio, rho, solucoes_colonia):
    for i in range(n+1):
        for j in range(n+1):
            feromonio[i][j] *= (1 - rho)
    for fx, solucao in solucoes_colonia:
        if fx is not None:
            delta = 1.0 / (fx + 1e-6)
            for k in solucao["onibus"]:
                for v in solucao["onibus"][k]:
                    arcos = solucao["onibus"][k][v]["arcos"]
                    for i, j in arcos:
                        feromonio[i][j] += delta

def reforcar_melhor_global(feromonios, melhor_solucao_global):
    if melhor_solucao_global:
        fx = melhor_solucao_global["fx"]
        delta = 1.0 / (fx + 1e-6)
        for c in range(NUM_COLONIAS):
            for k in melhor_solucao_global["onibus"]:
                for v in melhor_solucao_global["onibus"][k]:
                    arcos = melhor_solucao_global["onibus"][k][v]["arcos"]
                    for i, j in arcos:
                        feromonios[c][i][j] += delta

# LOGS
log_interval = 100
historico_fx = []

for _ in range(MAX_AVALIACOES):
    for c in range(NUM_COLONIAS):
        alpha = colonia_parametros[c]["alpha"]
        beta = colonia_parametros[c]["beta"]
        rho = colonia_parametros[c]["rho"]
        solucoes_colonia = []
        for a in range(NUM_FORMIGAS):
            fx, solucao = construir_solucao(feromonios[c], alpha, beta)
            solucoes_colonia.append((fx, solucao))
            if fx is not None and fx < melhor_fx_global:
                melhor_fx_global = fx
                melhor_solucao_global = {
                    "fx": fx,
                    "onibus": solucao["onibus"]
                }
        atualizar_feromonio(feromonios[c], rho, solucoes_colonia)
    reforcar_melhor_global(feromonios, melhor_solucao_global)
    # LOG a cada intervalo
    if avaliacoes % log_interval == 0:
        print(f"[LOG] Avaliações: {avaliacoes} | Melhor fx: {melhor_fx_global}")
        historico_fx.append((avaliacoes, melhor_fx_global))

if melhor_solucao_global:
    with open("melhorsolucao.json", "w") as f:
        json.dump(melhor_solucao_global, f, indent=2)
    print(f"Melhor solução encontrada com fx = {melhor_fx_global} após {avaliacoes} avaliações.")
else:
    print("Nenhuma solução viável foi encontrada após o número máximo de avaliações.")

# Salva histórico de evolução para análise posterior
with open("historico_fx.json", "w") as f:
    json.dump(historico_fx, f, indent=2)