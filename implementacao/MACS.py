import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from exemplo_prof.dados import Dados, carrega_dados_json
from exemplo_prof.solucao import Solucao
import numpy as np
import implementacao.grafo as grafo
import Restricoes as res

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
    
def le_requisicoes(instancia: Dados):
    requisicoes = {}
    for requisicao in range(1,instancia.n+1):
        r = Requisicao(instancia.e[requisicao-1], instancia.l[requisicao-1])
        requisicoes[requisicao] = r
    return requisicoes

def f_objetivo(solucao: Solucao, instancia: Dados):
    custo = 0
    for k, viagens in solucao.arcos.items():
        for v, lista_arcos in viagens.items():
            for (i,j) in lista_arcos:
                custo += instancia.c[i][j]
    
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

def Inicializar_feromonio (grafo: grafo.Graph):
  vertices = grafo.get_vertex()
  n = len(vertices)
  matriz_feromonios = np.zeros((n,n))
  return matriz_feromonios

instancia_pequena = carrega_dados_json("dados/pequena.json")

solucao_inicial = Constroi_solucao_inicial(instancia_pequena)

print(solucao_inicial)
print(f_objetivo(solucao_inicial, instancia_pequena))
print(res.atendimento_requisicoes(solucao_inicial, instancia_pequena))
print(res.inicio_e_fim_de_cada_viagem(solucao_inicial, instancia_pequena))
print(res.janela_de_tempo_da_coleta(solucao_inicial, instancia_pequena))
print(res.sequencia_temporal_das_rotas_intra(solucao_inicial, instancia_pequena))
print(res.Sequencia_temporal_das_rotas_inter(solucao_inicial, instancia_pequena))
print(res.limite_de_tempo_por_viagem(solucao_inicial, instancia_pequena))