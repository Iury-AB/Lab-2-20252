import time

inicio = time.time()
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from exemplo_prof.dados import Dados, carrega_dados_json
from exemplo_prof.solucao import Solucao
import implementacao.grafo as grafo
import Restricoes as res
import numpy as np
import random
import math
from implementacao.busca_em_largura import bfs_existe_rota, dfs_hamiltoniano

class Requisicao:
    def __init__(self, e, l):
        self.e = e # início da janela de tempo
        self.l = l # fim da janela de tempo

    def __str__(self):
      # String representacao de uma requisicao
      return f"[{self.e}, {self.l}]"
    
    def __lt__(self,other):
       # Comparacao entre requisicoes, a "menor" é a que abre a janela mais cedo
       return self.e < other.e
    
    def __eq__(self, value):
      return self.e == value.e and self.l == value.l
    
def le_requisicoes(instancia: Dados):
    requisicoes = {}
    for requisicao in range(1,instancia.n+1):
        r = Requisicao(instancia.e[requisicao-1], instancia.l[requisicao-1])
        requisicoes[requisicao] = r
    return requisicoes

def f_objetivo(solucao: Solucao, instancia: Dados):
    custo = 0
    for k, viagens in solucao.rota.items():
        for v, lista_requisicoes in viagens.items():
            for i, requisicao in enumerate(lista_requisicoes):
                if (i+1) >= len(lista_requisicoes):
                  continue
                custo += instancia.c[requisicao][lista_requisicoes[i+1]]
    
    solucao.fx = custo
    return custo

def Constroi_solucao_inicial(instancia: Dados):
  requisicoes = le_requisicoes(instancia)
  requisicoes_ordenadas = [i+1 for i, _ in sorted(enumerate(requisicoes), key=lambda x: x[1])]
  solucao = Solucao()
  solucao.rota = {k: {v: [] for v in range(1,instancia.r+1)} for k in range(1,instancia.K+1)}
  solucao.chegada = {k: {v: [] for v in range(1,instancia.r+1)} for k in range(1,instancia.K+1)}
  solucao.arcos = {k: {v: [] for v in range(1,instancia.r+1)} for k in range(1,instancia.K+1)}

  for requisicao in requisicoes_ordenadas:
    atribuida = False
    for viagem in range(1,instancia.r+1):
      if atribuida:
         break
      for onibus in range(1,instancia.K+1): 
        ultima_req = requisicao
        ultimo_tempo = requisicoes[requisicao].e
        tempo_chegada = ultimo_tempo - instancia.T[0][requisicao] - instancia.s[0]

        if solucao.rota[onibus][viagem]:
          ultima_req = solucao.rota[onibus][viagem][-1]
          ultimo_tempo = solucao.chegada[onibus][viagem][-1]
          tempo_chegada = ultimo_tempo + instancia.s[ultima_req] + instancia.T[ultima_req][requisicao]
          tempo_servico = max(tempo_chegada, requisicoes[requisicao].e) + instancia.s[requisicao]  + instancia.T[requisicao][0] - solucao.chegada[onibus][viagem][0]
          if not (tempo_chegada <= requisicoes[requisicao].l and 
                  tempo_servico <= instancia.Tmax):
             continue

        if not solucao.rota[onibus][viagem]:
          if solucao.rota[onibus].get(viagem-1,[]):
            solucao.rota[onibus][viagem-1].append(0)
            solucao.chegada[onibus][viagem-1].append(solucao.chegada[onibus][viagem-1][-1] + 
                                                     instancia.T[solucao.rota[onibus][viagem-1][-1]][0] + instancia.s[solucao.rota[onibus][viagem-1][-1]])
            solucao.arcos[onibus][viagem-1].append((solucao.rota[onibus][viagem-1][-1], 0))

            solucao.chegada[onibus][viagem].append(tempo_chegada)
          else:
            solucao.chegada[onibus][viagem].append(max(tempo_chegada, 0))
            
          solucao.rota[onibus][viagem].append(0)
        
        ultima_req = solucao.rota[onibus][viagem][-1]
        ultimo_tempo = solucao.chegada[onibus][viagem][-1]
        tempo_chegada = ultimo_tempo + instancia.s[ultima_req] + instancia.T[ultima_req][requisicao]

        solucao.rota[onibus][viagem].append(requisicao)
        solucao.chegada[onibus][viagem].append(max(requisicoes[requisicao].e, tempo_chegada))
        solucao.arcos[onibus][viagem].append((ultima_req, requisicao))
        atribuida = True
        break

  for viagem in range(1, instancia.r+1):
     for onibus in range(1, instancia.K+1):
        if not solucao.rota[onibus][viagem]:
           continue
        if solucao.rota[onibus][viagem][-1] != 0:
           ultima_req = solucao.rota[onibus][viagem][-1]
           solucao.rota[onibus][viagem].append(0)
           solucao.chegada[onibus][viagem].append(solucao.chegada[onibus][viagem][-1] + instancia.T[ultima_req][0] + instancia.s[ultima_req])
           solucao.arcos[onibus][viagem].append((ultima_req, 0))
  f_objetivo(solucao, instancia)
  return solucao

class MACS:
  def __init__(self, instancia: Dados):
    self.instancia = instancia
    self.requisicoes = dict(sorted(le_requisicoes(instancia).items(), key=lambda item: item[1]))

    self.grafo = grafo.Graph()
    for i, req_i in self.requisicoes.items():
      for j, req_j in self.requisicoes.items():
        if req_j.l - req_i.e >= instancia.s[i] + instancia.T[i][j] and req_i != req_j:
            self.grafo.add_edge(i, j, self.instancia.T[i][j])

    for req in self.requisicoes.keys():
       self.grafo.add_edge(0, req, self.instancia.c[0][req])

    self.feromonios_onibus = {i: {k: 1 for k in range(1,instancia.K+1)} for i in range(1,instancia.n+1)}
    self.feromonios_rota = {i: {j: 1 for j in range(0,instancia.n+1)} for i in range(0,instancia.n+1)}
    self.feromonios_garagem = {i: 1 for i in range(1,instancia.n+1)}

  def __seleciona_requisicao(self, requisicoes):
    i = random.choice(list(requisicoes.keys()))
    return i
  
  def __seleciona_onibus(self, distribuicoes: dict, requisicao: 
                         int, alpha: float, beta: float):
    servico_maximo = self.instancia.Tmax

    servico_onibus = {k: 0 for k in range(1, self.instancia.K+1)}
    servico_restante_onibus = {k: 0 for k in range(1, self.instancia.K+1)}
    for onibus, req_lista in distribuicoes.items():
      for i, req in enumerate(req_lista):
        if (i+1) >= len(req_lista):
           continue
        servico_onibus[onibus] += self.instancia.T[req][req_lista[i+1]] + self.instancia.s[req]
      servico_restante_onibus[onibus] = servico_maximo - servico_onibus[onibus]

    atratividade1 = {k: 0 for k in range(1,self.instancia.K +1)}
    atratividade2 = {k: 0 for k in range(1,self.instancia.K +1)}
    atratividade = {k: 0 for k in range(1,self.instancia.K +1)}
    for k in range(1, self.instancia.K+1):
      requisicoes_distribuicao = {req: self.requisicoes[req] for req in distribuicoes[k]}

      atratividade1[k] = servico_restante_onibus[k] / (sum(servico_restante_onibus.values()))
      
      atratividade2[k] = math.exp(
         -(abs(max(requisicoes_distribuicao.values()).e - self.requisicoes[requisicao].e))/self.instancia.Tmax) if distribuicoes[k] else math.exp(-(self.requisicoes[requisicao].e)/self.instancia.Tmax)

      atratividade[k] = atratividade1[k] * atratividade2[k]

    vontade = {k: (atratividade[k]**beta) * (self.feromonios_onibus[requisicao][k]**alpha)
                    for k in range(1, self.instancia.K+1)}
    
    probabilidades = {k: vontade[k] / sum(vontade.values())
                          for k in vontade}

    onibus_possiveis = list(probabilidades.keys())
    pesos = list(probabilidades.values())
    onibus_escolhido = random.choices(onibus_possiveis, weights=pesos, k=1)[0]
    
    # for onibus in range(len(onibus_possiveis)):
    #   onibus_escolhido = random.choices(onibus_possiveis, weights=pesos, k=1)[0]

    #   if distribuicoes[onibus_escolhido]:
    #     vizinhos = {i: len(self.grafo.get_neighbors(i)) for i in distribuicoes[onibus_escolhido]}
    #     max_vizinhos = max(vizinhos.values())
    #     maiores_vizinhos = [i for i, v in vizinhos.items() if v == max_vizinhos]

    #     rota_encontrada = False
    #     for i in maiores_vizinhos:
    #       vertices_subgrafo = distribuicoes[onibus_escolhido].copy()
    #       vertices_subgrafo.append(requisicao)
    #       sub_grafo = self.grafo.subgraph(vertices_subgrafo)

    #       if (
    #           dfs_hamiltoniano(i, requisicao, sub_grafo, set()) or 
    #           dfs_hamiltoniano(requisicao, i, sub_grafo, set())
    #       ):
    #         rota_encontrada = True
    #         break

    #     if rota_encontrada:
    #       break
    #     onibus_possiveis.remove(onibus_escolhido)
    #     pesos.remove(probabilidades[onibus_escolhido])
    #   else:
    #     break

    return onibus_escolhido
  
  def __seleciona_proxima_requisicao(self, distribuicao: dict, i: int,
                                     alpha: float, beta: float):
     
    # vizinhos = self.grafo.get_neighbors(i)
    # vizinhos_factiveis = [vizinho for vizinho in vizinhos if vizinho in distribuicao]
    atratividade1 = {j: 0 for j in distribuicao}
    atratividade2 = {j: 0 for j in distribuicao}
    atratividade = {j: 0 for j in distribuicao}

    menor_distancia = min(
      self.instancia.c[i][j]
      for i in range(len(self.instancia.c))
      for j in range(len(self.instancia.c[i]))
      if i != j
    )

    for j in distribuicao:
      atratividade1[j] = menor_distancia / self.instancia.c[i][j]
      atratividade2[j] = math.exp(-(abs(self.requisicoes[i].e - self.requisicoes[j].e))/self.instancia.Tmax) if i != 0 else math.exp(-(self.requisicoes[j].e)/self.instancia.Tmax)
      atratividade[j] = atratividade1[j] * atratividade2[j]

    vontade = {j: (atratividade[j] ** beta) * (self.feromonios_rota[i][j] ** alpha) 
               for j in distribuicao}
    
    probabilidades = {j: vontade[j] / sum(vontade.values()) 
                      for j in distribuicao}
    
    Requisicao_j = random.choices(
       distribuicao,
       probabilidades.values(), k=1)[0]

    # req_restantes = [n for n in distribuicao if n != Requisicao_j]
    # sub_grafo = self.grafo.subgraph(distribuicao)
    # saidas = {n: sub_grafo.out_degree(n) for n in req_restantes}
    # ultimo = max(saidas, key=saidas.get) if saidas else Requisicao_j
    # while  (not dfs_hamiltoniano(Requisicao_j, ultimo, sub_grafo,set())
    #         and len(distribuicao) > 1):
    #   vizinhos_factiveis.remove(Requisicao_j)
    #   probabilidades.pop(Requisicao_j)
    #   Requisicao_j = random.choices(
    #      vizinhos_factiveis,
    #      probabilidades.values(), k=1)[0]
    #   req_restantes = [n for n in distribuicao if n != Requisicao_j]
    #   saidas = {n: sub_grafo.out_degree(n) for n in req_restantes}
    #   ultimo = max(saidas, key=saidas.get)

    return Requisicao_j
  
  def __fechar_rota(self, solucao: Solucao, onibus: int,
                     alfa: float, beta: float):
    
      return solucao

  def otimizar(self, n_formigas, alpha1: float, beta1: float,
                alpha2: float, beta2: float):
    m = n_formigas
    K = self.instancia.K

    melhor_solucao = Constroi_solucao_inicial(self.instancia)

    for f in range(m):

      sol = Solucao()
      for k in range(1, self.instancia.K+1):
        sol.chegada[k] = {}
        sol.rota[k] = {}
        for v in range(1, self.instancia.r+1):
            sol.chegada[k][v] = []
            sol.rota[k][v] = []

      Q = self.requisicoes.copy()
      Qk = {k: [] for k in range(1, K+1)}

      while Q:
        i = self.__seleciona_requisicao(Q)
        k = self.__seleciona_onibus(Qk, i, alpha1, beta1)
        Qk[k].append(i)
        Q.pop(i)
        continue

      for k in range(1, self.instancia.K+1):

        if Qk[k]: sol.rota[k][1].append(0)

        while Qk[k]:
          i = sol.rota[k][1][-1]
          j = self.__seleciona_proxima_requisicao(Qk[k], i, alpha2, beta2)

          #######

          chegada_i = (max(
            self.requisicoes[j].e - self.instancia.s[i] - self.instancia.T[i][j], 0) 
            if i == 0 else sol.chegada[k][1][-1])

          sol.rota[k][1].append(j)
          if i == 0: sol.chegada[k][1].append(chegada_i)
          sol.chegada[k][1].append(max(
             chegada_i + self.instancia.s[i] + self.instancia.T[i][j],
             self.instancia.e[j-1]))
          Qk[k].remove(j)
        if sol.rota[k][1]: self.__fechar_rota(sol, k, 0, 1)
      sol.fx = f_objetivo(sol, self.instancia)

      melhor_solucao = sol if sol.fx < melhor_solucao.fx else melhor_solucao


    return melhor_solucao

instancia = carrega_dados_json("dados/pequena.json")

macs = MACS(instancia)
solucao = macs.otimizar(100, alpha1=0,beta1=1,alpha2=0,beta2=1)
fim = time.time()
print(f"Tempo de execução: {fim - inicio:.4f} segundos")
print(solucao.fx)
print(solucao)
print(res.eh_factivel(solucao, instancia))
pequena_otima = Solucao()
pequena_otima.carregar("dados/otimo_pequena.json")
f_objetivo(pequena_otima, instancia)
print("#####\n", pequena_otima, pequena_otima.fx)