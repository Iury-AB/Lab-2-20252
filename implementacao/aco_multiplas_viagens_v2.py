import json
import random

# =========================
# LEITURA DOS DADOS
# =========================
with open("grande.json", "r", encoding="utf-8") as f:
    dados = json.load(f)

# Parâmetros principais
n = dados["numeroRequisicoes"]
m = dados["numeroOnibus"]
r_max = dados["numeroMaximoViagens"]
tempo_max_viagem = dados["tempoMaximoViagem"]
custo = dados["custo"]
tempo_servico = dados["tempoServico"]
tempo_requisicoes = dados["tempoRequisicoes"]
inicio_janela = dados["inicioJanela"]
fim_janela = dados["fimJanela"]

# =========================
# FUNÇÃO: Verifica se requisição pode ser alocada na viagem atual
# =========================
def pode_alocar_requisicao(rota, chegada, req, tempo_atual):
    """
    Verifica se é possível alocar a requisição 'req' na rota atual do ônibus, respeitando:
    - Janela de tempo da requisição
    - Tempo máximo da viagem
    - Sequência temporal
    """
    deslocamento = tempo_requisicoes[rota[-1]][req]
    chegada_estimada = tempo_atual + deslocamento
    inicio_servico = max(chegada_estimada, inicio_janela[req-1])
    fim_servico = inicio_servico + tempo_servico[req]
    tempo_incremento = inicio_servico - tempo_atual + tempo_servico[req]
    # Restrição: janela de tempo da requisição
    if inicio_servico > fim_janela[req-1]:
        return False
    # Restrição: tempo máximo da viagem
    if chegada and (inicio_servico - chegada[0] + tempo_servico[req]) > tempo_max_viagem:
        return False
    return True

# =========================
# FUNÇÃO: Constrói uma viagem para um ônibus
# =========================
def construir_viagem_onibus(requisicoes_restantes, feromonio, alpha, beta):
    """
    Tenta encaixar o máximo de requisições viáveis em uma viagem, respeitando restrições.
    """
    rota = [0]
    arcos = []
    chegada = []
    tempo_atual = tempo_servico[0]
    while requisicoes_restantes:
        i = rota[-1]
        candidatos = list(requisicoes_restantes)
        # Escolha probabilística baseada em feromônio e heurística
        candidatos_viaveis = [j for j in candidatos if pode_alocar_requisicao(rota, chegada, j, tempo_atual)]
        if not candidatos_viaveis:
            break
        # Probabilidade baseada em feromônio e heurística
        probabilidades = []
        total = 0
        for j in candidatos_viaveis:
            deslocamento = tempo_requisicoes[i][j]
            tau = feromonio[i][j]
            eta = 1 / (deslocamento + 1e-6)
            valor = (tau ** alpha) * (eta ** beta)
            probabilidades.append((j, valor))
            total += valor
        probabilidades = [(j, v / total) for j, v in probabilidades]
        r = random.random()
        acumulado = 0
        for j, p in probabilidades:
            acumulado += p
            if r <= acumulado:
                escolhido = j
                break
        else:
            escolhido = probabilidades[-1][0]
        # Atualiza rota e tempos
        deslocamento = tempo_requisicoes[rota[-1]][escolhido]
        chegada_estimada = tempo_atual + deslocamento
        inicio_servico = max(chegada_estimada, inicio_janela[escolhido-1])
        tempo_atual = inicio_servico + tempo_servico[escolhido]
        rota.append(escolhido)
        arcos.append([rota[-2], escolhido])
        chegada.append(inicio_servico)
        requisicoes_restantes.remove(escolhido)
    # Finaliza viagem retornando à garagem
    if len(rota) > 1:
        rota.append(0)
        arcos.append([rota[-2], 0])
        chegada.append(tempo_atual + tempo_requisicoes[rota[-2]][0])
        return {
            "rota": rota,
            "arcos": arcos,
            "chegada": chegada
        }
    return None

# =========================
# FUNÇÃO: Constrói solução global (todos ônibus e viagens)
# =========================
def construir_solucao_global(feromonio, alpha, beta):
    """
    Aloca requisições aos ônibus e viagens, respeitando todas as restrições.
    """
    solucao = {"onibus": {}}
    requisicoes_restantes = set(range(1, n+1))
    for k in range(m):
        viagens = {}
        num_viagens = 0
        while requisicoes_restantes and num_viagens < r_max:
            viagem = construir_viagem_onibus(requisicoes_restantes, feromonio, alpha, beta)
            if viagem:
                viagens[f"viagem_{num_viagens}"] = viagem
                num_viagens += 1
            else:
                break
        if viagens:
            solucao["onibus"][str(k)] = viagens
    return solucao

# =========================
# FUNÇÃO: Valida solução encontrada
# =========================
def validar_solucao(solucao):
    """
    Valida:
    - Atendimento único das requisições
    - Início/fim na garagem
    - Tempo máximo por viagem
    - Número máximo de viagens por ônibus
    """
    atendidas = set()
    for k in solucao["onibus"]:
        if len(solucao["onibus"][k]) > r_max:
            print(f"Ônibus {k} excedeu o número máximo de viagens ({len(solucao['onibus'][k])} > {r_max})")
            return False
        for v in solucao["onibus"][k]:
            viagem = solucao["onibus"][k][v]
            rota = viagem["rota"]
            chegada = viagem["chegada"]
            # Atendimento único
            for req in rota:
                if req != 0:
                    if req in atendidas:
                        print(f"Requisição {req} duplicada!")
                        return False
                    atendidas.add(req)
            # Início/fim na garagem
            if rota[0] != 0 or rota[-1] != 0:
                print(f"Rota de ônibus {k}, viagem {v} não começa/termina na garagem!")
                return False
            # Tempo máximo por viagem
            if len(chegada) >= 2 and chegada[-1] - chegada[0] > tempo_max_viagem:
                print(f"Ônibus {k}, viagem {v} excedeu tempo máximo!")
                return False
    if len(atendidas) != n:
        print(f"Requisições faltantes: {set(range(1, n+1)) - atendidas}")
        return False
    return True

# =========================
# EXECUÇÃO DO MACO
# =========================
NUM_COLONIAS = 4
NUM_FORMIGAS = 72
MAX_AVALIACOES = 7000

colonia_parametros = [
    {"alpha": 3.0, "beta": 2.0, "rho": 0.1},
    {"alpha": 0.5, "beta": 2.0, "rho": 0.7},
    {"alpha": 1.0, "beta": 5.0, "rho": 0.5},
    {"alpha": 0.1, "beta": 1.0, "rho": 0.9},
]

feromonios = [
    [[1.0 for _ in range(n+1)] for _ in range(n+1)]
    for _ in range(NUM_COLONIAS)
]

melhor_solucao_global = None
melhor_fx_global = float("inf")

for _ in range(MAX_AVALIACOES):
    for c in range(NUM_COLONIAS):
        alpha = colonia_parametros[c]["alpha"]
        beta = colonia_parametros[c]["beta"]
        solucao = construir_solucao_global(feromonios[c], alpha, beta)
        if validar_solucao(solucao):
            fx = 0
            for k in solucao["onibus"]:
                for v in solucao["onibus"][k]:
                    arcos = solucao["onibus"][k][v]["arcos"]
                    for i, j in arcos:
                        fx += custo[i][j]
            if fx < melhor_fx_global:
                melhor_fx_global = fx
                melhor_solucao_global = {
                    "fx": fx,
                    "onibus": solucao["onibus"]
                }

if melhor_solucao_global:
    with open("melhorsolucao_modular.json", "w") as f:
        json.dump(melhor_solucao_global, f, indent=2)
    print(f"Melhor solução encontrada com fx = {melhor_fx_global}")
else:
    print("Nenhuma solução viável foi encontrada.")