import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'exemplo_prof'))

from exemplo_prof import dados
from exemplo_prof import solucao as sol
import numpy as np
import implementacao.grafo as grafo

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
    
def le_requisicoes(instancia: dados.Dados):
    requisicoes = []
    for requisicao in range(instancia.n):
        r = Requisicao(instancia.e[requisicao], instancia.l[requisicao])
        requisicoes.append(r)
    return requisicoes

def f_objetivo(solucao: sol.Solucao, instancia: dados.Dados):
    custo = 0
    for k, viagens in solucao.arcos.items():
        for v, lista_arcos in viagens.items():
            for (i,j) in lista_arcos:
                custo += instancia.c[i][j]
    
    solucao.fx = custo
    return custo

def Constroi_solucao_inicial(instancia: dados.Dados):
   requisicoes = le_requisicoes(instancia)
   req_ordenadas = requisicoes.sorted()
   solucao = sol.Solucao()

   onibus = 0
   viagem = 0

   for requisicao in req_ordenadas:
    atribuida = False
    for onibus in range(instancia.K):
        for viagem in range(instancia.r):
            ultima_req = solucao.rota[onibus].get(viagem, [0])[-1]
            ultimo_tempo = solucao.chegada[onibus].get(viagem, [0])[-1]

            tempo_chegada = ultimo_tempo + instancia.T[ultima_req][requisicao.id]
            if tempo_chegada <= requisicao.l:
                # inicializa viagem se não existir
                if viagem not in solucao.rota[onibus]:
                    solucao.rota[onibus][viagem] = [0]
                    solucao.chegada[onibus][viagem] = [0]

                solucao.rota[onibus][viagem].append(requisicao.id)
                solucao.chegada[onibus][viagem].append(max(requisicao.e, tempo_chegada))
                atribuida = True
                break
        if atribuida:
            break
    if not atribuida:
        print(f"Requisição {requisicao.id} não pôde ser atribuída.")

   return solucao

def Inicializar_feromonio (grafo: grafo.Graph):
  vertices = grafo.get_vertex()
  n = len(vertices)
  matriz_feromonios = np.zeros((n,n))
  return matriz_feromonios

instancia_pequena = dados.carrega_dados_json("dados/pequena.json")

requisicoes = le_requisicoes(instancia_pequena)

grafo_requisicoes = grafo.Graph()

for i in range(instancia_pequena.n):
    for j in range(instancia_pequena.n):
        if i == j:
            continue
        grafo_requisicoes.add_edge(requisicoes[i], requisicoes[j], instancia_pequena.c[i][j])

maxIter = 1000
formigas = 3

feromonios = Inicializar_feromonio(grafo_requisicoes)

for iter in range(maxIter):
    for formiga in range(formigas):
        Q = requisicoes
        Q_onibus = [[] for _ in range(instancia_pequena.K)]
    
