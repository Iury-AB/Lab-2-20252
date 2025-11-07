from itertools import combinations
from collections import deque
import heapq
import time
from implementacao import grafo
from exemplo_prof import dados

class State:
    def __init__(self, requisicao, custo, path=None):
        self.costs = custo
        self.requisicao = requisicao
        self.path = path or []

    def finished(self):
        return all(pos==1 for pos in self.positions.values())
    
    def get_time(self):
        return self.time
    
    def get_torch(self):
        return self.torch_side

    def get_positions(self):
        return (tuple(self.positions.items()), self.torch_side)
    
    def next_states_list(self):
        next_states = []
        side_with_torch = []
        for person, position in self.positions.items():
            if position == self.torch_side:
                side_with_torch.append(person)
        
        for n in [1,2]:
            for crossers in combinations(side_with_torch, n):
                new_positions = self.positions.copy()
                for name in crossers:
                    new_positions[name] = 1 - new_positions[name]
                new_torch_side = 1 - self.torch_side
                new_time = self.time + max(self.costs[name] for name in crossers)

                new_state = State(self.costs, new_positions, new_torch_side, new_time, self.path + [self])
                next_states.append(new_state)

        return next_states
    
    def info(self):
        return f"Positions: {self.positions}, Torch side: {self.torch_side}, Current time: {self.time}"
    


def bfs_existe_rota(inicio: int, destino: int, grafo: grafo.Graph, 
                    instancia: dados.Dados):
    
    if (not grafo.graph or 
        destino not in grafo.graph.keys() or
        inicio not in grafo.graph.keys()):
        return False
    
    visited = set()
    queue = deque([(inicio, [inicio])])
    custo = 0
    while queue:
        current, caminho = queue.pop()
        if destino in caminho and len(caminho) == len(grafo.graph.keys()):
            return True

        visited.add((current, tuple(caminho)))

        for vizinho in grafo.get_neighbors(current):
            if vizinho not in visited:
                queue.append((vizinho, tuple(caminho) + (vizinho,)))
                visited.add((vizinho, tuple(caminho) + (vizinho,)))
    return False

def dfs_hamiltoniano(atual: int, destino: int, 
                     grafo: grafo.Graph, visitados: set):
    if atual not in visitados:
        visitados.add(atual)

    if (not grafo.graph or 
        destino not in grafo.graph.keys() or
        atual not in grafo.graph.keys()):
        return False
    
    if len(visitados) == len(grafo.graph.keys()):
        return destino in visitados

    for vizinho in grafo.get_neighbors(atual):
        if vizinho not in visitados:
            visitados.add(vizinho)
            if dfs_hamiltoniano(vizinho, destino, grafo, visitados):
                return True
            visitados.remove(vizinho)
    return False
