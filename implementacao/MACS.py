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
    requisicoes = []
    for requisicao in range(instancia.n):
        r = Requisicao(instancia.e[requisicao], instancia.l[requisicao])
        requisicoes.append(r)
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
  solucao.rota = {k: {v: [] for v in range(instancia.r)} for k in range(instancia.K)}
  solucao.chegada = {k: {v: [] for v in range(instancia.r)} for k in range(instancia.K)}
  solucao.arcos = {k: {v: [] for v in range(instancia.r)} for k in range(instancia.K)}

  for requisicao in requisicoes_ordenadas:
    atribuida = False
    for viagem in range(instancia.r):
      for onibus in range(instancia.K): 
        if not solucao.rota[onibus][viagem]:
          solucao.rota[onibus][viagem].append(0)
          solucao.chegada[onibus][viagem].append(0)

        ultima_req = solucao.rota[onibus][viagem][-1]
        ultimo_tempo = solucao.chegada[onibus][viagem][-1]

        tempo_chegada = ultimo_tempo + instancia.s[requisicao] + instancia.T[ultima_req][requisicao]
        if tempo_chegada <= requisicoes[requisicao-1].l and tempo_chegada + instancia.s[requisicao] <= instancia.Tmax - instancia.T[ultima_req][0]:
          # inicializa viagem se não existir
          if viagem not in solucao.rota[onibus]:
            solucao.rota[onibus][viagem] = [0]
            solucao.chegada[onibus][viagem] = [0]

          solucao.rota[onibus][viagem].append(requisicao)
          solucao.chegada[onibus][viagem].append(max(requisicoes[requisicao-1].e, tempo_chegada))
          solucao.arcos[onibus][viagem].append((ultima_req, requisicao))
          atribuida = True
          break
        else:
          continue
      if atribuida:
          break
      
  for viagem in range(instancia.r):
     for onibus in range(instancia.K):
        if solucao.rota[onibus][viagem]:
          ultima_req = solucao.rota[onibus][viagem][-1]
          solucao.rota[onibus][viagem].append(0)
          solucao.arcos[onibus][viagem].append((ultima_req, 0))
          solucao.chegada[onibus][viagem].append(solucao.chegada[onibus][viagem][-1] + instancia.c[ultima_req][0] + instancia.s[0])

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