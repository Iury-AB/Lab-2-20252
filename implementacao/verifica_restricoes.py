import json

with open("grande.json", "r", encoding="utf-8") as f:
    dados = json.load(f)
tempo_max_viagem = dados["tempoMaximoViagem"]
n = dados["numeroRequisicoes"]
r_max = dados["numeroMaximoViagens"]

with open("melhorsolucao_modular.json", "r", encoding="utf-8") as f:
    solucao = json.load(f)

# 1. Atendimento único das requisições
atendidas = set()
duplicadas = set()
for k in solucao["onibus"]:
    for v in solucao["onibus"][k]:
        rota = solucao["onibus"][k][v]["rota"]
        for req in rota:
            if req != 0:
                if req in atendidas:
                    duplicadas.add(req)
                atendidas.add(req)
faltantes = set(range(1, n+1)) - atendidas

# 2. Início/fim na garagem
violacoes_garagem = []
for k in solucao["onibus"]:
    for v in solucao["onibus"][k]:
        rota = solucao["onibus"][k][v]["rota"]
        if rota[0] != 0 or rota[-1] != 0:
            violacoes_garagem.append((k, v))

# 3. Tempo máximo por viagem
violacoes_tempo = []
for k in solucao["onibus"]:
    for v in solucao["onibus"][k]:
        chegada = solucao["onibus"][k][v]["chegada"]
        if len(chegada) >= 2:
            duracao = chegada[-1] - chegada[0]
            if duracao > tempo_max_viagem:
                violacoes_tempo.append((k, v, duracao))

# 4. Número máximo de viagens por ônibus
violacoes_viagens = []
for k in solucao["onibus"]:
    if len(solucao["onibus"][k]) > r_max:
        violacoes_viagens.append((k, len(solucao["onibus"][k])))

print("--- RELATÓRIO DE RESTRIÇÕES ---")
print(f"Requisições duplicadas: {sorted(duplicadas)}")
print(f"Requisições faltantes: {sorted(faltantes)}")
print(f"Rotas que não começam/terminam na garagem: {violacoes_garagem}")
print(f"Viagens que excedem o tempo máximo: {violacoes_tempo}")
print(f"Ônibus que excederam o número máximo de viagens: {violacoes_viagens}")
