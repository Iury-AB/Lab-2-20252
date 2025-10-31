import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from exemplo_prof.dados import Dados, carrega_dados_json
from exemplo_prof.solucao import Solucao
import implementacao.grafo as grafo
import Restricoes as res
import numpy as np
import random

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
  return solucao

class MACS:
  def __init__(self, instancia: Dados):
    self.instancia = instancia
    self.requisicoes = le_requisicoes(instancia)

    self.grafo = grafo.Graph()
    for i, req_i in self.requisicoes.items():
      for j, req_j in self.requisicoes.items():
        if req_j.e >= req_i.e and req_i != req_j:
          self.grafo.add_edge(i, j, self.instancia.c[i][j])

    self.feromonios_onibus = {i: {k: 1 for k in range(1,instancia.K+1)} for i in range(1,instancia.n+1)}
    self.feromonios_rota = {i: {j: 1 for j in range(1,instancia.n+1)} for i in range(1,instancia.n+1)}

  def __seleciona_requisicao(self, requisicoes):
    i = random.choice(list(self.requisicoes.keys()))
    return i
  
  def __seleciona_onibus(self, distribuicoes: dict, requisicao):
    servico_maximo = self.instancia.Tmax * self.instancia.r

    servico_onibus = {k: 0 for k in range(1, self.instancia.K+1)}
    servico_restante_onibus = {k: 0 for k in range(1, self.instancia.K+1)}
    for onibus, req_lista in distribuicoes.items():
      for i, req in enumerate(req_lista):
        if (i+1) >= len(req_lista):
           continue
        servico_onibus[onibus] += self.instancia.c[req][req_lista[i+1]] + self.instancia.s[req]
      servico_restante_onibus[onibus] = servico_maximo - servico_onibus[onibus]

    atratividade1 = {i: {k: 0 for k in range(1,self.instancia.K +1)} for i in range(1,self.instancia.n+1)}
    atratividade2 = {i: {k: 0 for k in range(1,self.instancia.K +1)} for i in range(1,self.instancia.n+1)}
    atratividade = {i: {k: 0 for k in range(1,self.instancia.K +1)} for i in range(1,self.instancia.n+1)}
    for k in range(1, self.instancia.K+1):
       for i in range(1, self.instancia.n+1):
          atratividade1[i][k] = servico_restante_onibus[k] / (sum(servico_restante_onibus.values()))
          atratividade2[i][k] = self.instancia.Tmax / abs(distribuicoes[k][-1].e - self.requisicoes[i].e) if distribuicoes[k] else self.requisicoes[i].e
          atratividade[i][k] = atratividade1[i][k] * atratividade2[i][k]

    vontade = {i: {k: atratividade[i][k] * self.feromonios_onibus[i][k]
                    for k in range(1, self.instancia.K+1)}
                      for i in range(1, self.instancia.n+1)}
    
    probabilidades = {i: {k: vontade[i][k] / sum(vontade[i].values())
                          for k in vontade[i]}
                            for i in vontade}

    onibus_possiveis = list(probabilidades[requisicao].keys())
    pesos = list(probabilidades[requisicao].values())
    onibus_escolhido = random.choices(onibus_possiveis, weights=pesos, k=1)[0]

    return onibus_escolhido

  def otimizar(self, n_formigas):
    m = n_formigas
    K = self.instancia.K

    melhor_solucao = Constroi_solucao_inicial(self.instancia)

    for f in range(m):
      Q = self.requisicoes
      Qk = {k: [] for k in range(1, K+1)}

      while Q:
        i = self.__seleciona_requisicao(Q)
        k = self.__seleciona_onibus(Qk, i)
        #Qk[k] = i
        continue
      continue
    return melhor_solucao

instancia = carrega_dados_json("dados/pequena.json")

macs = MACS(instancia)
macs.otimizar(1)
