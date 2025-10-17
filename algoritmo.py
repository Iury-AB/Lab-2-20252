from exemplo_prof import dados
from exemplo_prof import solucao
import numpy as np

class Edge:
    def __init__(self, u, v, w):
        self.u = u  # starting vertex
        self.v = v  # ending vertex
        self.w = w  # weight of the edge
    
    def __lt__(self, other):
        # This makes the edges comparable by weight for sorting
        return self.w < other.w
    
    def __str__(self):
        # String representation of an edge
        return f"{self.u} -> {self.v} ({self.w})"
    
    def __repr__(self):
        return self.__str__()

class Graph:
    def __init__(self):
        # Initialize a graph with no predefined number of vertices
        self.graph = {}  # key: vertex, value: list of edges
    
    def add_edge(self, u, v, w):
        # Add an edge from u to v with weight w
        if u not in self.graph:
            self.graph[u] = []
        if v not in self.graph:
            self.graph[v] = []
        
        self.graph[u].append(Edge(u, v, w))
    
    def add_undirected_edge(self, u, v, w):
        # Add an undirected edge between u and v with weight w
        self.add_edge(u, v, w)
        self.add_edge(v, u, w)
    
    def __str__(self):
        # String representation of the entire graph
        result = []
        for u in self.graph:
            for edge in self.graph[u]:
                result.append(str(edge))
        return "\n".join(result)
    
    def get_edges(self):
        # Returns all edges in the graph
        edges = []
        for u in self.graph:
            for edge in self.graph[u]:
                edges.append(edge)
        return edges

    def out_degree(self, u):
        # Return the out-degree of vertex u
        if u in self.graph:
            return len(self.graph[u])
        else:
            raise ValueError(f"Vertex {u} not found in the graph.")
    
    def in_degree(self, v):
        # Return the in-degree of vertex v
        in_deg = 0
        for u in self.graph:
            for edge in self.graph[u]:
                if edge.v == v:
                    in_deg += 1
        return in_deg
    
    def get_neighbors(self, u):
        # Returns the neighbors of vertex u
        if u in self.graph:
            return [edge.v for edge in self.graph[u]]
        else:
            raise ValueError(f"Vertex {u} not found in the graph.")
        
    def get_vertex(self):
      vertices = []
      arestas = self.get_edges()
      for aresta in arestas:
        if aresta.u in vertices:
            vertices.append(aresta.u)
        if aresta.v in vertices:
            vertices.append(aresta.v)
      return vertices

class Requisicao:
    def __init__(self, e, l):
        self.e = e # início da janela de tempo
        self.l = l # fim das janela de tempo

    def __str__(self):
      # String representation of an edge
      return f"[{self.e}, {self.l}]"

def InicializarFeromonio (grafo: Graph):
  vertices = grafo.get_vertex()
  n = len(vertices)
  matriz_feromonios = np.zeros((n,n))
  return matriz_feromonios

instancia_pequena = dados.carrega_dados_json("dados/pequena.json")

requisicoes = []
for requisicao in range(instancia_pequena.n):
  r = Requisicao(instancia_pequena.e[requisicao], instancia_pequena.l[requisicao])
  requisicoes.append(r)

grafo_requisicoes = Graph()

for i in range(instancia_pequena.n):
    for j in range(instancia_pequena.n):
        if i == j:
            continue
        grafo_requisicoes.add_edge(requisicoes[i], requisicoes[j], instancia_pequena.c[i][j])
        
print(grafo_requisicoes)
