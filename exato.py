import gurobipy as gp
from gurobipy import GRB
import json
import numpy as np
from time import time
import pandas as pd

with open("./dados/pequena.json", "r") as f:
    dados = json.load(f)

n = dados["numeroRequisicoes"]
K = dados["numeroOnibus"]
D = np.array(dados["distanciaRequisicoes"])
Dmax = dados["distanciaMaxima"]
c = np.array(dados["custo"])
s = np.array(dados["tempoServico"])
T = np.array(dados["tempoRequisicoes"])
e = np.array(dados["inicioJanela"])
l = np.array(dados["fimJanela"])
V_max = 5

N = list(range(1, n+1))
N0 = list(range(n+1))
V = list(range(1, V_max+1))
K = list(range(1, K+1))
x = {}
y = {}
B = {}
M = 1e10
LIMITE_TEMPO = 5*60.

modelo = gp.Model("Otimização do Serviço de Ônibus para Embarque Remoto")

for k in K:
    for v in V:
        for i in N0:
            for j in N0:
                if i != j:
                    x[i, j, v, k] = modelo.addVar(vtype=GRB.BINARY,
                                            name=f"x_{i}_{j}_{v}_{k}")

            B[i, v, k] = modelo.addVar(vtype=GRB.CONTINUOUS,
                                        lb=0.0,
                                        name=f"B_{i}_{v}_{k}")
            
        y[v, k] = modelo.addVar(vtype=GRB.BINARY,
                                name=f"y_{v}_{k}")

modelo.update()

funcao_objetivo = modelo.setObjective(
    gp.quicksum(c[i, j] * x[i, j, v, k] 
                for i in N0 
                for j in N0
                for v in V
                for k in K
                if i != j),
    GRB.MINIMIZE
)

for j in N:
    modelo.addConstr(
        gp.quicksum(x[i, j, v, k]
                    for i in N0
                    for k in K
                    for v in V
                    if i != j) == 1,
        name=f"atendimento_{j}"
)

for k in K:
    for j in N:

        entrada = gp.quicksum(x[i, j, v, k]
                               for i in N0
                               if i != j)

        saida = gp.quicksum(x[j, i, v, k]
                            for i in N0
                            if i != j)

        modelo.addConstr(
            entrada - saida == 0,
            name=f"conservacao_{j}_{k}"
        )

for k in K:
    for v in V:
        modelo.addConstr(
            gp.quicksum(x[0, j, v, k]
                        for j in N) == y[v, k],
            name=f"inicio_viagem_{v}_{k}"
        )
        modelo.addConstr(
            gp.quicksum(x[i, 0, v, k]
                        for i in N) == y[v, k],
            name=f"termino_viagem_{v}_{k}"
        )

for k in K:
    for v in V:
        if v > 1:
            modelo.addConstr(
                y[v, k] <= y[v-1, k],
                name=f"sequencia_viagem_{v}_{k}"
            )

for k in K:
    for v in V:
        modelo.addConstr(
            gp.quicksum(D[i,j] * x[i, j, v, k]
                        for i in N0
                        for j in N0
                        if i != j) <= Dmax,
            name=f"distancia_maxima_{v}_{k}"
        )


for k in K:
    for v in V:
        for i in N:
            modelo.addConstr(
                B[i, v, k] >= e[i-1] * gp.quicksum(x[j, i, v, k]
                for j in N0 if i != j),
                name=f"janela_inferior_{i}_{v}_{k}"
            )
            modelo.addConstr(
                B[i, v, k] <= l[i-1] * gp.quicksum(x[j, i, v, k]
                for j in N0 if i != j),
                name=f"janela_superior_{i}_{v}_{k}"
            )

for k in K:
    for v in V:
        for i in N0:
            for j in N0:
                
                if i == j:
                    continue
                
                elif i == 0 and v == 1:
                    modelo.addConstr(
                        s[0] + T[0, j] - M * (1 - x[0, j, 1, k]) <= B[j, 1, k],
                        name=f"fluxo_tempo_intra_0_{j}_{v}_{k}"
                    )

                else:
                    modelo.addConstr(
                        B[i, v, k] + s[i] + T[i, j] - M * (1 - x[i, j, v, k]) 
                        <= B[j, v, k],
                    name=f"fluxo_tempo_intra_{i}_{j}_{v}_{k}"
                )
            
            if v > 1 and i != 0:
                modelo.addConstr(
                    B[0, v-1, k] + s[0] + T[0, i] - M * (1 - x[0, i, v, k]) <= B[i, v, k],
                    name=f"fluxo_tempo_inter_{i}_{v}_{k}"
                )

modelo.update()

modelo.setParam(GRB.Param.TimeLimit, LIMITE_TEMPO)

tic = time()
modelo.optimize()
tempo_total = time() - tic

if modelo.Status == GRB.OPTIMAL:
    print(f"Solução ótima encontrada em {tempo_total:.2f} segundos.")
    modelo.write("modelo_otimo.lp")
elif modelo.Status == GRB.TIME_LIMIT:
    print(f"Tempo limite atingido em {tempo_total:.2f} segundos.")
    modelo.write("modelo_time_limit.lp")
else:
    print(f"Solução não encontrada. Status: {modelo.Status}")
    exit()

print(f"Valor da função objetivo: {modelo.ObjVal:.2f}")

resultado = {}
todas_requisicoes = []
for k in K:
    resultado[k] = {}
    for v in V:
        requisicoes = []
        for i in N0:
            for j in N:
                if i != j and x[i, j, v, k].X > 0.5:
                    requisicoes.append(j)
                    todas_requisicoes.append(j)
        resultado[k][v] = requisicoes
    print(f"Ônibus {k}: {resultado[k]}")
print(f"Todas as requisições: {sorted(todas_requisicoes)}")