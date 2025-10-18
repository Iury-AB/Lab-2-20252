from exemplo_prof import dados
from exemplo_prof import solucao
import numpy as np
import grafo

class Requisicao:
    def __init__(self, e, l):
        self.e = e # início da janela de tempo
        self.l = l # fim das janela de tempo

    def __str__(self):
      # String representation of an edge
      return f"[{self.e}, {self.l}]"

def InicializarFeromonio (grafo: grafo.Graph):
  vertices = grafo.get_vertex()
  n = len(vertices)
  matriz_feromonios = np.zeros((n,n))
  return matriz_feromonios

instancia_pequena = dados.carrega_dados_json("dados/pequena.json")

requisicoes = []
for requisicao in range(instancia_pequena.n):
  r = Requisicao(instancia_pequena.e[requisicao], instancia_pequena.l[requisicao])
  requisicoes.append(r)

grafo_requisicoes = grafo.Graph()

for i in range(instancia_pequena.n):
    for j in range(instancia_pequena.n):
        if i == j:
            continue
        grafo_requisicoes.add_edge(requisicoes[i], requisicoes[j], instancia_pequena.c[i][j])

maxIter = 1000
formigas = 3

feromonios = InicializarFeromonio(grafo_requisicoes)

for iter in range(maxIter):
    for formiga in range(formigas):
        Q = requisicoes
        Q_onibus = [[] for _ in range(instancia_pequena.K)]
        
    #while Q:
    #    r = seleciona_requisicao(Q, feromonios)
