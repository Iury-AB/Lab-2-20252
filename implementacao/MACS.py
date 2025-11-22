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
  solucao.rota = {k: {} for k in range(1,instancia.K+1)}
  solucao.chegada = {k: {} for k in range(1,instancia.K+1)}

  for requisicao in requisicoes_ordenadas:
    atribuida = False
    for viagem in range(1,instancia.r+1):
      if atribuida:
         break
      for onibus in range(1,instancia.K+1): 
        ultima_req = requisicao
        ultimo_tempo = requisicoes[requisicao].e
        tempo_chegada = ultimo_tempo - instancia.T[0][requisicao] - instancia.s[0]

        if viagem in solucao.rota[onibus]:
          ultima_req = solucao.rota[onibus][viagem][-1]
          ultimo_tempo = solucao.chegada[onibus][viagem][-1]
          tempo_chegada = ultimo_tempo + instancia.s[ultima_req] + instancia.T[ultima_req][requisicao]
          tempo_servico = max(tempo_chegada, requisicoes[requisicao].e) + instancia.s[requisicao]  + instancia.T[requisicao][0] - solucao.chegada[onibus][viagem][0]
          if not (tempo_chegada <= requisicoes[requisicao].l and 
                  tempo_servico <= instancia.Tmax):
             continue

        if viagem not in solucao.rota[onibus]:
          if solucao.rota[onibus].get(viagem-1,[]):
            solucao.rota[onibus][viagem-1].append(0)
            solucao.chegada[onibus][viagem-1].append(solucao.chegada[onibus][viagem-1][-1] + 
                                                     instancia.T[solucao.rota[onibus][viagem-1][-1]][0] + instancia.s[solucao.rota[onibus][viagem-1][-1]])

            solucao.chegada[onibus][viagem] = []
            solucao.chegada[onibus][viagem].append(tempo_chegada)
          else:
            solucao.chegada[onibus][viagem] = []
            solucao.chegada[onibus][viagem].append(max(tempo_chegada, 0))
            
          solucao.rota[onibus][viagem] = []
          solucao.rota[onibus][viagem].append(0)
        
        ultima_req = solucao.rota[onibus][viagem][-1]
        ultimo_tempo = solucao.chegada[onibus][viagem][-1]
        tempo_chegada = ultimo_tempo + instancia.s[ultima_req] + instancia.T[ultima_req][requisicao]

        solucao.rota[onibus][viagem].append(requisicao)
        solucao.chegada[onibus][viagem].append(max(requisicoes[requisicao].e, tempo_chegada))
        atribuida = True
        break

  for viagem in range(1, instancia.r+1):
     for onibus in range(1, instancia.K+1):
        if viagem not in solucao.rota[onibus]:
           continue
        if solucao.rota[onibus][viagem][-1] != 0:
           ultima_req = solucao.rota[onibus][viagem][-1]
           solucao.rota[onibus][viagem].append(0)
           solucao.chegada[onibus][viagem].append(solucao.chegada[onibus][viagem][-1] + instancia.T[ultima_req][0] + instancia.s[ultima_req])
  f_objetivo(solucao, instancia)
  return solucao

class MACS:
  def __init__(self, instancia: Dados, solucao_inicial: Solucao):
    self.instancia = instancia
    self.requisicoes = dict(sorted(le_requisicoes(instancia).items(), key=lambda item: item[1]))

    self.avaliacoes = 0
    self.solucoes_exploradas = 0
    self.solucoes_factiveis = 0
    self.melhorias = 0

    self.sol_inicial = solucao_inicial

    self.grafo = grafo.Graph()
    for i, req_i in self.requisicoes.items():
      for j, req_j in self.requisicoes.items():
        if req_i != req_j:
          if req_j.l - req_i.e >= instancia.s[i] + instancia.T[i][j]:
            self.grafo.add_edge(i, j, self.instancia.T[i][j])
          else:
            self.grafo.add_edge(i, j, 100000)

    for req in self.requisicoes.keys():
       self.grafo.add_edge(0, req, self.instancia.c[0][req])

    self.menor_distancia = min(
      self.instancia.c[i][j]
      for i in range(len(self.instancia.c))
      for j in range(len(self.instancia.c[i]))
      if i != j
    )

    self.feromonios_onibus = {i: {k: 100/solucao_inicial.fx 
                                  for k in range(1,instancia.K+1)}
                                  for i in range(1,instancia.n+1)}
    
    self.feromonios_rota = {i: {j: 100/solucao_inicial.fx
                                for j in range(0,instancia.n+1)}
                                for i in range(0,instancia.n+1)}
    
  def __str__(self):
    return (f"Soluções exploradas: {self.solucoes_exploradas}\nSoluções factíveis encontradas: {self.solucoes_factiveis}\nMelhorias no ótimo encontrado: {self.melhorias}")
  
  def __seleciona_requisicao(self, requisicoes):
    i = random.choice(requisicoes)
    return i
  
  def __seleciona_onibus(self, distribuicoes: dict, requisicao: int, 
                         servico_restante_onibus: dict, total_servico: float,
                         alpha: float, beta: float):

    atratividade_onibus = {}
    vontade_onibus = {}
    for k in range(1, self.instancia.K+1):
      atratividade_onibus[k] = servico_restante_onibus[k] / total_servico
      vontade_onibus[k] = ((atratividade_onibus[k]**beta) *
                                            (self.feromonios_onibus[requisicao][k]**alpha))

    onibus_possiveis = list(distribuicoes.keys())
    pesos = list(vontade_onibus.values())
    onibus_escolhido = random.choices(onibus_possiveis, weights=pesos, k=1)[0]

    return onibus_escolhido
  
  def __seleciona_proxima_requisicao(self, distribuicao: list, i: int,
                                     alpha: float, beta: float):
    
    atratividade_rota = {}
    vontade_rota = {}
    for j in distribuicao:
      atratividade_rota[j] = self.menor_distancia / self.instancia.c[i][j]
      vontade_rota[j] = ((atratividade_rota[j] ** beta) *
                              (self.feromonios_rota[i][j] ** alpha))

    pesos = list(vontade_rota.values())
    Requisicao_j = random.choices(distribuicao, weights=pesos, k=1)[0]

    return Requisicao_j
  
  def __fechar_rota(self, solucao: Solucao, onibus: int):
    viagem = 1
    mover = False
    rota = solucao.rota[onibus][viagem].copy()
    indice = 0
    for i, r in enumerate(rota):
      if r == 0 and i != 0 and i+1 < len(rota):
        mover = True
        solucao.rota[onibus][1].pop(indice)
        viagem += 1
        continue
      if mover and r != 0:
        if viagem not in solucao.rota[onibus]:
          solucao.rota[onibus][viagem] = [0]
        solucao.rota[onibus][1].remove(r)
        solucao.rota[onibus][viagem].append(r)
        continue
      indice += 1
    
    for v in range(1,self.instancia.r+1):
      if v in solucao.rota[onibus] and solucao.rota[onibus][v][-1] != 0:
        solucao.rota[onibus][v].append(0)
    return solucao
  
  def __atualiza_feromonios(self, rho: float, solucao: Solucao):
    incremento_feromonio = 100 / solucao.fx
    for k, viagens in solucao.rota.items():
      for v, lista_requisicoes in viagens.items():
        for req in lista_requisicoes:
            if req == 0:
              continue
            self.feromonios_onibus[req][k] = (rho * self.feromonios_onibus[req][k] +
                                              incremento_feromonio)

    for k, viagens in solucao.rota.items():
      for v, lista_requisicoes in viagens.items():
        for i, req in enumerate(lista_requisicoes):
          if i == 0:
            continue
          self.feromonios_rota[solucao.rota[k][v][i-1]][req] = (
            rho * self.feromonios_rota[solucao.rota[k][v][i-1]][req] + 
            incremento_feromonio)
    return None

  def __calcula_chegadas(self, solucao: Solucao, k: int):
    ultima_chegada = 0.0
    for v, lista_requisicoes in solucao.rota[k].items():
      chegadas = []
      for i, req in enumerate(lista_requisicoes):
        if i == 0:
          primeira_req = solucao.rota[k][v][1]
          chegada_real = (self.instancia.e[primeira_req - 1] - self.instancia.s[0] -
                          self.instancia.T[0][primeira_req])
          chegada = max(chegada_real, ultima_chegada)
        else:
          req_anterior = solucao.rota[k][v][i-1]
          chegada_real = (chegadas[i-1] + self.instancia.s[req_anterior] + 
                          self.instancia.T[req_anterior][req])
          if req != 0:
            chegada = max(chegada_real, self.instancia.e[req - 1])
          else:
            chegada = chegada_real
        chegadas.append(chegada)
      ultima_chegada = chegadas[-1]
      solucao.chegada[k][v] = chegadas
    return True

  def __penaliza_feromonios_rota(self, solucao: Solucao, penalidade: float):
    for k, viagens in solucao.rota.items():
      for v, lista_requisicoes in viagens.items():
        for i, req in enumerate(lista_requisicoes):
          if i == 0:
            continue
          self.feromonios_rota[solucao.rota[k][v][i-1]][req] = (
            penalidade * self.feromonios_rota[solucao.rota[k][v][i-1]][req])
    return None
  
  def __penaliza_feromonios_onibus(self, solucao: Solucao, penalidade: float):
    for k, viagens in solucao.rota.items():
      for v, lista_requisicoes in viagens.items():
        for req in lista_requisicoes:
            if req == 0:
              continue
            self.feromonios_onibus[req][k] = (penalidade * self.feromonios_onibus[req][k])
    return None

  def otimizar(self, n_formigas, max_iter, alpha1: float, beta1: float,
                alpha2: float, beta2: float, rho: float):
    m = n_formigas
    K = self.instancia.K

    melhor_solucao = self.sol_inicial
    print(melhor_solucao.fx)
    self.feromonios_onibus
    self.avaliacoes += 1

    while self.avaliacoes < max_iter:
      solucoes = []
      for f in range(m):

        sol = Solucao()
        for k in range(1, self.instancia.K+1):
          sol.chegada[k] = {}
          sol.rota[k] = {}

        Q = list(self.requisicoes.keys())
        Qk = {k: [] for k in range(1, K+1)}

        servico_restante_onibus = {k: self.instancia.Tmax for k in range(1, self.instancia.K+1)}
        total_servico = self.instancia.Tmax * self.instancia.K
        while Q:
          i = self.__seleciona_requisicao(Q)
          k = self.__seleciona_onibus(Qk, i, servico_restante_onibus, total_servico, alpha1, beta1)
          servico_restante_onibus[k] -= self.instancia.s[i]
          total_servico -= self.instancia.s[i]
          Qk[k].append(i)
          Q.remove(i)
          continue

        for k in range(1, self.instancia.K+1):

          if Qk[k]: sol.rota[k][1] = [0]

          while Qk[k]:
            i = sol.rota[k][1][-1]
            n_viagens = sol.rota[k][1].count(0)
            if (0 not in Qk[k] and i != 0 and n_viagens < self.instancia.r): Qk[k].append(0)
            j = self.__seleciona_proxima_requisicao(Qk[k], i, alpha2, beta2)
            sol.rota[k][1].append(j)
            Qk[k].remove(j)
          if 1 in sol.rota[k]: self.__fechar_rota(sol, k)
          self.__calcula_chegadas(sol, k)
        
        solucoes.append(sol)
      for solucao in solucoes:
        self.solucoes_exploradas +=1
        if solucao.factivel(self.instancia): 
          self.solucoes_factiveis+=1
          f_objetivo(solucao, self.instancia)
          self.avaliacoes += 1
          if solucao.fx < melhor_solucao.fx:
            self.melhorias+=1
            melhor_solucao = solucao
            print(f"fx: {melhor_solucao.fx}, solucoes factiveis exploradas: {self.solucoes_factiveis}")
          if self.avaliacoes > max_iter:
            return melhor_solucao
        else:
            self.__penaliza_feromonios_rota(solucao, 0.7)
            self.__penaliza_feromonios_onibus(solucao, 0.7)
          
      self.__atualiza_feromonios(rho, melhor_solucao)

    return melhor_solucao

instancia = carrega_dados_json("dados/media.json")
solucao = Solucao()
solucao.carregar("dados/otimo_media.json")
print(solucao)
print(solucao.fx)

# solucao_inicial = Constroi_solucao_inicial(instancia)
# print(solucao_inicial)
# macs = MACS(instancia, solucao_inicial)
# solucao = macs.otimizar(n_formigas=10, max_iter=2100, alpha1=0.5,beta1=0.9,
#                         alpha2=0.5,beta2=0.9,rho=0.6)
# fim = time.time()
# print(macs)
# print(f"Tempo de execução: {fim - inicio:.4f} segundos")
# print(solucao.fx)
# print(solucao)
# print(solucao.factivel(instancia, verbose=True))
