import json
import random

with open("media.json", "r") as f:
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

def construir_solucao_critica(feromonio, alpha, beta):
    global avaliacoes
    avaliacoes += 1
    # Ordena requisições por (largura da janela, fim da janela)
    reqs_ordenadas = sorted(
        range(1, n+1),
        key=lambda j: (fim_janela[j-1] - inicio_janela[j-1], fim_janela[j-1])
    )
    # Inicializa slots: [ônibus][viagem] = lista de requisições
    slots = [[[] for _ in range(r_max)] for _ in range(m)]
    tempos = [[tempo_servico[0]] * r_max for _ in range(m)]  # tempo atual em cada slot
    rotas = [[ [0] ] * r_max for _ in range(m)]  # começa na garagem
    arcos = [[ [] for _ in range(r_max)] for _ in range(m)]
    chegadas = [[ [] for _ in range(r_max)] for _ in range(m)]
    atendidas = set()
    for req in reqs_ordenadas:
        melhor_slot = None
        melhor_inicio = float("inf")
        # Tenta encaixar no primeiro slot disponível
        for k in range(m):
            for v in range(r_max):
                if len(slots[k][v]) >= 1 and len(slots[k][v]) >= capacidade_onibus:
                    continue
                ultimo = rotas[k][v][-1] if len(rotas[k][v]) > 0 else 0
                deslocamento = tempo_requisicoes[ultimo][req]
                chegada_estimada = tempos[k][v] + deslocamento
                inicio_servico = max(chegada_estimada, inicio_janela[req-1])
                if inicio_servico > fim_janela[req-1]:
                    continue
                if inicio_servico < melhor_inicio:
                    melhor_inicio = inicio_servico
                    melhor_slot = (k, v, ultimo, deslocamento)
        if melhor_slot:
            k, v, ultimo, deslocamento = melhor_slot
            slots[k][v].append(req)
            rotas[k][v].append(req)
            arcos[k][v].append([ultimo, req])
            chegadas[k][v].append(melhor_inicio)
            tempos[k][v] = melhor_inicio + tempo_servico[req]
            atendidas.add(req)
    # Monta a solução final
    solucao = {"onibus": {}}
    for k in range(m):
        solucao["onibus"][str(k)] = {}
        for v in range(r_max):
            if len(rotas[k][v]) > 1:
                # Fecha a viagem na garagem
                rotas[k][v].append(0)
                arcos[k][v].append([rotas[k][v][-2], 0])
                chegadas[k][v].append(tempos[k][v] + tempo_requisicoes[rotas[k][v][-2]][0])
                solucao["onibus"][str(k)][f"viagem_{v}"] = {
                    "rota": rotas[k][v],
                    "arcos": arcos[k][v],
                    "chegada": chegadas[k][v]
                }
    if len(atendidas) == n:
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
            fx, solucao = construir_solucao_critica(feromonios[c], alpha, beta)
            solucoes_colonia.append((fx, solucao))
            if fx is not None and fx < melhor_fx_global:
                melhor_fx_global = fx
                melhor_solucao_global = {
                    "fx": fx,
                    "onibus": solucao["onibus"]
                }
        atualizar_feromonio(feromonios[c], rho, solucoes_colonia)
    reforcar_melhor_global(feromonios, melhor_solucao_global)
    if avaliacoes % log_interval == 0:
        print(f"[LOG] Avaliações: {avaliacoes} | Melhor fx: {melhor_fx_global}")
        historico_fx.append((avaliacoes, melhor_fx_global))

if melhor_solucao_global:
    with open("melhorsolucao.json", "w") as f:
        json.dump(melhor_solucao_global, f, indent=2)
    print(f"Melhor solução encontrada com fx = {melhor_fx_global} após {avaliacoes} avaliações.")
else:
    print("Nenhuma solução viável foi encontrada após o número máximo de avaliações.")

with open("historico_fx.json", "w") as f:
    json.dump(historico_fx, f, indent=2)