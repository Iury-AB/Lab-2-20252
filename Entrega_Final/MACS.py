import time

inicio = time.time()
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from dados import Dados, carrega_dados_json
from solucao import Solucao
import grafo
import Restricoes as res
import numpy as np
import random
import gurobipy as gp
from gurobipy import GRB
import copy

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
    self.iteracoes = 0
    self.solucoes_exploradas = 0
    self.solucoes_factiveis = 0
    self.melhorias = 0

    self.sol_inicial = solucao_inicial

    self.grafo = grafo.Graph()
    for i, req_i in self.requisicoes.items():
      for j, req_j in self.requisicoes.items():
        if req_i != req_j:
          if req_j.l >= req_i.e + instancia.s[i] + instancia.T[i][j]:
            self.grafo.add_edge(i, j, self.instancia.T[i][j])

    for req in self.requisicoes.keys():
      self.grafo.add_edge(0, req, self.instancia.c[0][req])
      self.grafo.add_edge(req, 0, self.instancia.c[0][req])

    self.menor_distancia = min(
      self.instancia.c[i][j]
      for i in range(len(self.instancia.c))
      for j in range(len(self.instancia.c[i]))
      if i != j
    )

    self.feromonios_onibus = {i: {k: 100/solucao_inicial.fx 
                                  for k in range(1,instancia.K+1)}
                                  for i in range(1,instancia.n+1)}
    
    self.feromonios_rota = {i: {j: (
        1000/solucao_inicial.fx 
        if i == 0 or j == 0
        else 1000/solucao_inicial.fx
        if self.requisicoes[j].l >= self.requisicoes[i].e + instancia.s[i] + instancia.T[i][j] and i != 0 and j != 0
        else 1e-100)
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
    incremento_feromonio = 1000 / solucao.fx
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

  def __calcula_chegadas_gurobi(self, solucao: Solucao, k: int):
    modelo = gp.Model()
    B = {}
    
    for v, lista_requisicoes in solucao.rota[k].items():
      Qk = lista_requisicoes
      for i in Qk[1:]:
        B[i, v] = modelo.addVar(vtype=GRB.CONTINUOUS,
                              lb = 0.0,
                              name=f"B_{i}_{v}_{k}")

      modelo.update()

      for indice_i, i in enumerate(Qk):
        if i != 0:
          modelo.addConstr(
            B[i, v] >= self.instancia.e[i - 1],
            name = f"janela abertura {i} {v}")
          
          modelo.addConstr(
            B[i, v] <= self.instancia.l[i - 1],
            name = f"janela fechamento {i} {v}")
          
        for indice_j, j in enumerate(Qk):
          if i == j:
            continue

          elif i == 0 and v == 1 and Qk[indice_j - 1] == i and indice_i+1 != len(Qk):
            modelo.addConstr(
              B[j, 1] >= self.instancia.s[0] + self.instancia.T[0, j],
              name=f"fluxo_tempo_intra_0_{j}_{v}_{k}"
            )

          elif i != 0 and Qk[indice_j - 1] == i:
            modelo.addConstr(
                      B[i, v] + self.instancia.s[i] + self.instancia.T[i, j] <= B[j, v],
                      name=f"fluxo_tempo_intra_{i}_{j}_{v}_{k}"
              )
            
        if v > 1 and i != 0 and Qk[indice_i - 1] == 0:
              modelo.addConstr(
                  B[0, v-1] + self.instancia.s[0] + self.instancia.T[0, i] <= B[i, v],
                  name=f"fluxo_tempo_inter_{i}_{v}_{k}"
              )

    modelo.update()
    sub_fobj = modelo.setObjective(B[0, 1], GRB.MINIMIZE)
    modelo.setParam(GRB.param.OutputFlag, 0)
    modelo.setParam(GRB.Param.MIPFocus, 1)
    modelo.optimize()

    if modelo.Status == 3:
      ultimo_tempo = 0
      for v, lista_requisicoes in solucao.rota[k].items():
        solucao.chegada[k][v] = []
        for requisicao in lista_requisicoes:
          if requisicao == 0:
            solucao.chegada[k][v].append(ultimo_tempo)
            continue
          solucao.chegada[k][v].append(self.instancia.l[requisicao-1])
          ultimo_tempo = (solucao.chegada[k][v][-1] + self.instancia.T[requisicao][0] +
                          self.instancia.s[requisicao-1])
    else:
      for v, lista_requisicoes in solucao.rota[k].items():
        instantes = []
        for requisicao in lista_requisicoes[1:]:  # Para cada ponto da rota (exceto primeiro 0)
            # Obter tempo de chegada da variável B[requisicao,v,k]
            var_B = modelo.getVarByName(f"B_{requisicao}_{v}_{k}")
            if var_B is not None:
                instantes.append(var_B.X)
                if requisicao == lista_requisicoes[1]:
                    tempo_saida_garagem = var_B.X - self.instancia.T[0][requisicao] - self.instancia.s[0]
                    instantes.insert(0, tempo_saida_garagem)
        solucao.chegada[k][v] = instantes
    
    return None
  
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

  def __realocar_requisicao(self, solucao: Solucao, requisicao: int,
                           onibus_origem: int, viagem_origem: int,
                           onibus_destino: int, viagem_destino: int):

    if requisicao not in solucao.rota[onibus_origem][viagem_origem] or requisicao == 0:
      return solucao, False
    
    indice_req = solucao.rota[onibus_origem][viagem_origem].index(requisicao)
    rota_origem = (solucao.rota[onibus_origem][viagem_origem][0:indice_req] +
                   solucao.rota[onibus_origem][viagem_origem][indice_req+1:])
    
    nova_rota_destino = []
    distancias = {}
    rota_destino = solucao.rota[onibus_destino][viagem_destino]
    for req_idx, req in enumerate(rota_destino):
      if req_idx == 0:
        continue
      
      vizinhos = self.grafo.get_neighbors(requisicao)
      vizinhos_anterior = self.grafo.get_neighbors(rota_destino[req_idx-1])
      if req in vizinhos and requisicao in vizinhos_anterior:
        distancias[req_idx] = self.instancia.c[requisicao][req]
        break

    if distancias:
      melhor_substituicao = min(distancias, key=distancias.get)
      nova_rota_destino = rota_destino[0:melhor_substituicao] + [requisicao] + rota_destino[melhor_substituicao:]
    
    realocou = False
    nova_solucao = copy.deepcopy(solucao)
    if nova_rota_destino:
      realocou = True
      nova_solucao.rota[onibus_destino][viagem_destino] = nova_rota_destino
      if len(rota_origem) > 2:
        nova_solucao.rota[onibus_origem][viagem_origem] = rota_origem
        self.__calcula_chegadas_gurobi(nova_solucao, onibus_origem)
      else:
        del nova_solucao.rota[onibus_origem][viagem_origem]
        del nova_solucao.chegada[onibus_origem][viagem_origem]
        for v in list(nova_solucao.rota[onibus_origem].keys()):
          if v > viagem_origem:
            nova_solucao.rota[onibus_origem][v-1] = nova_solucao.rota[onibus_origem].pop(v)
            nova_solucao.chegada[onibus_origem][v-1] = nova_solucao.chegada[onibus_origem].pop(v)
        
      self.__calcula_chegadas_gurobi(nova_solucao, onibus_destino)

    return nova_solucao, realocou

  def __first_improvement_realocacao(self, solucao: Solucao, max_avaliacoes):
    solucao_incumbente = None
    melhor_encontrado = copy.deepcopy(solucao)
    lista_origens = [(r, v, k) for k in solucao.rota 
                     for v in solucao.rota[k] 
                     for r in solucao.rota[k][v] if r != 0]
    random.shuffle(lista_origens)
    
    lista_destinos = [(v, k) for k in solucao.rota 
                     for v in solucao.rota[k]]
    random.shuffle(lista_destinos)
    
    for origem in lista_origens:
      for destino in lista_destinos:
        solucao_incumbente = self.__realocar_requisicao(
          solucao, origem[0], origem[2], origem[1], destino[1], destino[0])
        self.solucoes_exploradas += 1

        if solucao_incumbente[1]:
          if solucao_incumbente[0].factivel(self.instancia):
            f_objetivo(solucao_incumbente[0], self.instancia)
            self.avaliacoes += 1
            self.solucoes_factiveis += 1
            if solucao_incumbente[0].fx < melhor_encontrado.fx:
              self.melhorias += 1
              print(solucao_incumbente[0].fx)
              melhor_encontrado = solucao_incumbente[0]
              return melhor_encontrado

        if self.avaliacoes >= max_avaliacoes:
          return melhor_encontrado

    return melhor_encontrado

  def __best_improvement_realocacao(self, solucao: Solucao, max_avaliacoes):
    solucao_incumbente = None
    melhor_encontrado = copy.deepcopy(solucao)
    
    
    for k_origem, viagens_origem in solucao.rota.items():
      for k_destino, viagens_destino in solucao.rota.items():
        if k_origem == k_destino:
          continue

        for v_origem, lista_requisicoes in solucao.rota[k_origem].items():
          for r in lista_requisicoes:
            if r == 0:
               continue
            
            for v_destino in solucao.rota[k_destino].keys():

              solucao_incumbente = self.__realocar_requisicao(
                solucao, r, k_origem, v_origem, k_destino, v_destino)
              self.solucoes_exploradas += 1
              
              if solucao_incumbente[1]:
                if solucao_incumbente[0].factivel(self.instancia):
                  f_objetivo(solucao_incumbente[0], self.instancia)
                  self.avaliacoes += 1
                  self.solucoes_factiveis += 1
                  if solucao_incumbente[0].fx < melhor_encontrado.fx:
                    self.melhorias += 1
                    print(solucao_incumbente[0].fx)
                    melhor_encontrado = solucao_incumbente[0]

              if self.avaliacoes >= max_avaliacoes:
                return melhor_encontrado

    return melhor_encontrado

  def otimizar(self, n_formigas, max_avaliacoes, alpha1: float, beta1: float,
                alpha2: float, beta2: float, rho: float):
    m = n_formigas
    K = self.instancia.K

    melhor_solucao = self.sol_inicial
    print(melhor_solucao.fx)
    self.feromonios_onibus
    self.avaliacoes += 1

    while (self.avaliacoes < max_avaliacoes and 
           self.solucoes_exploradas < 30*max_avaliacoes):
      self.iteracoes += 1
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
          k = self.__seleciona_onibus(Qk, i, servico_restante_onibus, total_servico, 
                                      alpha1, beta1)
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
          if sol.rota[k]: self.__calcula_chegadas(sol, k)
        
        solucoes.append(sol)
      for sol_idx, solucao in enumerate(solucoes):
        self.solucoes_exploradas +=1

        if solucao.factivel(self.instancia): 
          self.solucoes_factiveis+=1
          f_objetivo(solucao, self.instancia)
          self.avaliacoes += 1
          print(f"Solucao encontrada: {solucao.fx}, com {self.avaliacoes} avaliações. e {self.solucoes_exploradas} soluções geradas.")
          self.__atualiza_feromonios(1, solucao) 

          if solucao.fx < melhor_solucao.fx:
            self.melhorias+=1
            melhor_solucao = solucao
            print(f"Ótimo fx atualizado para: {melhor_solucao.fx}, com {self.melhorias} atualizações")

          if self.avaliacoes > max_avaliacoes:
            return melhor_solucao
        else:
            self.__penaliza_feromonios_rota(solucao, 0.9)
            self.__penaliza_feromonios_onibus(solucao, 0.9)

      self.__atualiza_feromonios(rho, melhor_solucao)

      # Busca Local
      if self.avaliacoes < max_avaliacoes:

        solucao_busca = copy.deepcopy(melhor_solucao)
        melhor_fx = solucao_busca.fx
        while True:
          solucao_busca = self.__best_improvement_realocacao(
            solucao_busca, min(self.avaliacoes+100, max_avaliacoes))
          if not (solucao_busca.fx < melhor_fx):
            break
          else:
            melhor_fx = solucao_busca.fx
        melhor_solucao = solucao_busca

    return melhor_solucao
