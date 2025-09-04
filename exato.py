"""
Módulo de Resolução Exata para o Problema de Embarque Remoto

Este módulo implementa um algoritmo de otimização exata baseado em Programação 
Linear Inteira Mista (MILP) usando o solver Gurobi para resolver o Problema 
de Transporte de Passageiros em Aeroportos com Embarque Remoto.

O problema consiste em otimizar rotas de ônibus que transportam passageiros 
entre portões de embarque e aeronaves estacionadas remotamente, minimizando 
o custo total de operação enquanto respeitando:
- Janelas de tempo das requisições
- Capacidade limitada de viagens por ônibus
- Restrições de distância máxima (autonomia)
- Conservação de fluxo

Formulação Matemática:
- Variáveis de decisão binárias x[i,j,v,k] para arcos entre requisições
- Variáveis binárias y[v,k] para ativação de viagens
- Variáveis contínuas B[i,v,k] para tempos de chegada
- Função objetivo minimiza custo total de transporte

Autor: André Batista
Data: Setembro 2025
"""

import gurobipy as gp
from gurobipy import GRB
from time import time
from dados import Dados
from solucao import Solucao
from typing import Optional

class Exato:
    """
    Classe para resolução exata do Problema de Embarque Remoto usando MILP.
    
    Esta classe implementa um modelo de Programação Linear Inteira Mista (MILP)
    para resolver o problema de otimização de rotas de ônibus em aeroportos,
    utilizando o solver comercial Gurobi Optimizer.
    
    O modelo matemático implementado é baseado em uma formulação de roteamento
    de veículos com janelas de tempo (VRPTW) adaptada para o contexto específico
    do transporte de passageiros entre portões e aeronaves remotas.
    
    Características do modelo:
    - Minimização do custo total de transporte
    - Respeito a janelas de tempo das requisições
    - Limitação de viagens por veículo (ônibus)
    - Restrições de distância máxima por viagem
    - Conservação de fluxo entre requisições
    
    Atributos:
        limite_tempo (Optional[float]): Tempo limite em segundos para otimização
    
    Example:
        >>> from dados import carrega_dados_json
        >>> dados = carrega_dados_json('dados/pequena.json')
        >>> solver = Exato(limite_tempo=300)  # 5 minutos
        >>> solucao = solver.resolve(dados)
        >>> print(f"Custo ótimo: {solucao.custo_total}")
    """

    def __init__(self, limite_tempo: Optional[float] = None) -> None:
        """
        Inicializa o solver de otimização exata.
        
        Args:
            limite_tempo: Tempo limite em segundos para a otimização.
                         Se None, não há limite de tempo.
        """
        self.limite_tempo = limite_tempo

    def resolve(self, dados: Dados) -> Solucao:
        """
        Resolve o problema de embarque remoto usando otimização exata (MILP).
        
        Este método constrói e resolve um modelo de Programação Linear Inteira
        Mista que minimiza o custo total de transporte respeitando todas as
        restrições operacionais do problema.
        
        Processo de resolução:
        1. Validação dos dados de entrada
        2. Definição dos conjuntos e parâmetros
        3. Criação das variáveis de decisão
        4. Formulação da função objetivo
        5. Adição das restrições do modelo
        6. Otimização usando Gurobi
        7. Extração e retorno da solução
        
        Args:
            dados: Instância do problema contendo todos os parâmetros necessários
                  (requisições, ônibus, distâncias, custos, janelas de tempo, etc.)
        
        Returns:
            Solucao: Objeto contendo a solução ótima ou melhor solução encontrada,
                    incluindo rotas dos ônibus, custos, tempos e status da otimização
        
        Raises:
            ValueError: Se os dados fornecidos são inválidos ou incompletos
            RuntimeError: Se o solver não consegue encontrar uma solução viável
        
        Note:
            - Se um limite de tempo foi definido e é atingido, retorna a melhor
              solução encontrada até o momento
            - O status da solução pode ser verificado no objeto Solucao retornado
        """

        self._valida_dados(dados)

        M = 1e10
        LIMITE_TEMPO = self.limite_tempo

        modelo = gp.Model("Otimização do Serviço de Ônibus para Embarque Remoto")

        N, N0, V, K = self._retorna_conjuntos(dados)

        x, y, B = self._define_variaveis(modelo, N, N0, V, K)

        funcao_objetivo = self._define_funcao_objetivo(modelo, dados, x, N0, V,
                                                       K)

        self._restricao_atendimento(modelo, N, N0, x, V, K)

        self._restricao_conservacao(modelo, N, N0, x, V, K)

        self._restricao_garagem(modelo, N, N0, V, K, x, y)

        self._restricao_sequencia(modelo, K, V, y)

        self._restricao_distancia(modelo, K, V, dados, x, N0)

        self._restricao_janela(modelo, dados, K, V, N0, N, x, B)

        self._restricao_fluxo(modelo, dados, M, K, V, N0, x, B)

        modelo.update()

        if LIMITE_TEMPO is not None:
            modelo.setParam(GRB.Param.TimeLimit, LIMITE_TEMPO)

        tic = time()
        modelo.optimize()
        tempo_total = time() - tic

        if modelo.Status == GRB.OPTIMAL:
            print(f"Solução ótima encontrada em {tempo_total:.2f} segundos.")
        elif modelo.Status == GRB.TIME_LIMIT:
            print(f"Tempo limite atingido em {tempo_total:.2f} segundos.")
        else:
            print(f"Solução não encontrada. Status: {modelo.Status}")
            exit()

        solucao = Solucao()
        solucao.carrega_modelo_gurobi(modelo, dados)
        return solucao
    
    def _valida_dados(self, dados: Dados) -> None:
        """
        Valida se os dados fornecidos contêm todos os campos obrigatórios.
        
        Verifica a presença e integridade de todos os atributos necessários
        para a construção do modelo de otimização, garantindo que nenhum
        campo essencial esteja ausente ou seja None.
        
        Args:
            dados: Objeto Dados a ser validado
            
        Raises:
            ValueError: Se qualquer campo obrigatório estiver ausente ou for None
            
        Campos validados:
            - n: Número de requisições
            - r: Número máximo de viagens por ônibus  
            - K: Número de ônibus disponíveis
            - D: Matriz de distâncias entre requisições
            - c: Matriz de custos entre requisições
            - s: Vetor de tempos de serviço
            - T: Matriz de tempos de viagem
            - e: Vetor de início das janelas de tempo
            - l: Vetor de fim das janelas de tempo
            - Dmax: Distância máxima permitida por viagem
        """

        if dados is None:
            raise ValueError("Dados fornecidos são None.")        
        if not hasattr(dados, 'n') or dados.n is None:
            raise ValueError(f"Dados não possuem o campo obrigatório 'n' ou o campo é None")
        if not hasattr(dados, 'r') or dados.r is None:
            raise ValueError(f"Dados não possuem o campo obrigatório 'r' ou o campo é None")
        if not hasattr(dados, 'K') or dados.K is None:
            raise ValueError(f"Dados não possuem o campo obrigatório 'K' ou o campo é None")
        if not hasattr(dados, 'D') or dados.D is None:
            raise ValueError(f"Dados não possuem o campo obrigatório 'D' ou o campo é None")
        if not hasattr(dados, 'c') or dados.c is None:
            raise ValueError(f"Dados não possuem o campo obrigatório 'c' ou o campo é None")
        if not hasattr(dados, 's') or dados.s is None:
            raise ValueError(f"Dados não possuem o campo obrigatório 's' ou o campo é None")
        if not hasattr(dados, 'T') or dados.T is None:
            raise ValueError(f"Dados não possuem o campo obrigatório 'T' ou o campo é None")
        if not hasattr(dados, 'e') or dados.e is None:
            raise ValueError(f"Dados não possuem o campo obrigatório 'e' ou o campo é None")
        if not hasattr(dados, 'l') or dados.l is None:
            raise ValueError(f"Dados não possuem o campo obrigatório 'l' ou o campo é None")
        if not hasattr(dados, 'Dmax') or dados.Dmax is None:
            raise ValueError(f"Dados não possuem o campo obrigatório 'Dmax' ou o campo é None")

    def _retorna_conjuntos(self, dados: Dados) -> tuple[list[int], list[int], list[int], list[int]]:
        """
        Define os conjuntos de índices utilizados no modelo matemático.
        
        Cria as listas de índices que serão utilizadas para construir as
        variáveis de decisão e restrições do modelo MILP.
        
        Args:
            dados: Instância contendo as dimensões do problema
            
        Returns:
            tuple contendo:
                - N: Lista de requisições [1, 2, ..., n]
                - N0: Lista incluindo garagem [0, 1, 2, ..., n] 
                - V: Lista de viagens [1, 2, ..., r]
                - K: Lista de ônibus [1, 2, ..., K]
                
        Note:
            - O índice 0 sempre representa a garagem
            - N0 = {0} ∪ N (garagem + todas as requisições)
            - Todos os conjuntos são baseados em 1, exceto N0 que inclui 0
        """
        N = list(range(1, dados.n+1))    # Requisições: {1, 2, ..., n}
        N0 = list(range(dados.n+1))      # Garagem + Requisições: {0, 1, ..., n}
        V = list(range(1, dados.r+1))    # Viagens: {1, 2, ..., r}
        K = list(range(1, dados.K+1))    # Ônibus: {1, 2, ..., K}
        return N, N0, V, K

    def _define_variaveis(self, modelo: gp.Model, N: list[int], N0: list[int], 
                          V: list[int], K: list[int]) -> tuple[dict, dict, dict]:
        """
        Define as variáveis de decisão do modelo MILP.
        
        Cria três tipos de variáveis de decisão necessárias para o modelo:
        
        1. x[i,j,v,k]: Variáveis binárias indicando se o ônibus k na viagem v
           vai diretamente da requisição i para a requisição j
           
        2. y[v,k]: Variáveis binárias indicando se o ônibus k realiza a viagem v
        
        3. B[i,v,k]: Variáveis contínuas representando o tempo de chegada do
           ônibus k na requisição i durante a viagem v
        
        Args:
            modelo: Modelo Gurobi onde as variáveis serão adicionadas
            N: Lista de requisições [1, ..., n]
            N0: Lista incluindo garagem [0, 1, ..., n]
            V: Lista de viagens [1, ..., r]
            K: Lista de ônibus [1, ..., K]
            
        Returns:
            tuple contendo:
                - x: Dicionário de variáveis binárias de roteamento
                - y: Dicionário de variáveis binárias de ativação de viagem
                - B: Dicionário de variáveis contínuas de tempo
                
        Note:
            - x[i,j,v,k] = 1 se ônibus k vai de i para j na viagem v, 0 caso contrário
            - y[v,k] = 1 se ônibus k faz a viagem v, 0 caso contrário  
            - B[i,v,k] ≥ 0 representa o tempo de chegada (contínuo)
        """

        x = {}
        y = {}
        B = {}

        for k in K:
            for v in V:
                for i in N0:
                    for j in N0:
                        if i != j:
                            x[i, j, v, k] = modelo.addVar(vtype=GRB.BINARY,
                                                    name=f"x_{i}_{j}_{v}_{k}")

                    B[i, v, k] = modelo.addVar(vtype=GRB.CONTINUOUS,
                                                lb=0.0,
                                                name=f"B_{i}_{v}_{k}")
                    
                y[v, k] = modelo.addVar(vtype=GRB.BINARY,
                                        name=f"y_{v}_{k}")
        
        modelo.update()
        
        return x, y, B
    
    def _define_funcao_objetivo(self, modelo: gp.Model, dados: Dados, x: dict,
                                N0: list[int], V: list[int], K: list[int]):
        """
        Define a função objetivo do modelo de minimização de custos.
        
        Estabelece o objetivo de minimizar o custo total de transporte,
        calculado como a soma dos custos de todos os arcos utilizados
        pelas rotas dos ônibus.
        
        Função objetivo:
        MIN Σ Σ Σ Σ c[i,j] * x[i,j,v,k]
            i∈N0 j∈N0 v∈V k∈K
            
        Onde:
        - c[i,j] é o custo de viajar da requisição i para j
        - x[i,j,v,k] = 1 se ônibus k vai de i para j na viagem v
        
        Args:
            modelo: Modelo Gurobi onde definir a função objetivo
            dados: Instância contendo a matriz de custos
            x: Dicionário de variáveis binárias de roteamento
            N0: Lista incluindo garagem [0, 1, ..., n]
            V: Lista de viagens [1, ..., r]
            K: Lista de ônibus [1, ..., K]
            
        Returns:
            Função objetivo configurada no modelo
            
        Note:
            - Considera apenas arcos válidos (i ≠ j)
            - Custo total = soma de custos de todos os segmentos percorridos
        """
        funcao_objetivo = modelo.setObjective(
            gp.quicksum(dados.c[i, j] * x[i, j, v, k] 
                        for i in N0 
                        for j in N0
                        for v in V
                        for k in K
                        if i != j),
            GRB.MINIMIZE
        )
        return funcao_objetivo

    def _restricao_atendimento(self, modelo: gp.Model, N: list[int], N0: list[int],
                               x: dict, V: list[int], K: list[int]) -> None:
        """
        Adiciona restrições que garantem o atendimento de todas as requisições.
        
        Cada requisição deve ser atendida exatamente uma vez por algum ônibus
        em alguma viagem. Esta é uma restrição fundamental que assegura que
        nenhuma requisição seja deixada sem atendimento.
        
        Restrição matemática:
        Σ Σ Σ x[i,j,v,k] = 1    ∀j ∈ N
        i∈N0 v∈V k∈K
        (i≠j)
        
        Interpretação:
        - Para cada requisição j, a soma de todas as chegadas a j deve ser 1
        - Isso garante que cada requisição seja visitada exatamente uma vez
        - A restrição considera todas as possíveis origens i, viagens v e ônibus k
        
        Args:
            modelo: Modelo Gurobi onde adicionar as restrições
            N: Lista de requisições [1, ..., n]
            N0: Lista incluindo garagem [0, 1, ..., n]
            x: Dicionário de variáveis binárias de roteamento
            V: Lista de viagens [1, ..., r]
            K: Lista de ônibus [1, ..., K]
        """
        for j in N:
            modelo.addConstr(
                gp.quicksum(x[i, j, v, k]
                            for i in N0
                            for k in K
                            for v in V
                            if i != j) == 1,
                name=f"atendimento_{j}"
        )

    def _restricao_conservacao(self, modelo: gp.Model, N: list[int], N0: list[int],
                                x: dict, V: list[int], K: list[int]) -> None:
        """
        Adiciona restrições de conservação de fluxo nas requisições.
        
        Garante que se um ônibus chega a uma requisição, ele também deve
        sair dela. Isso assegura continuidade nas rotas e evita que ônibus
        "desapareçam" ou "apareçam" no meio de uma viagem.
        
        Restrição matemática:
        Σ x[i,j,v,k] - Σ x[j,i,v,k] = 0    ∀j ∈ N, ∀v ∈ V, ∀k ∈ K
        i∈N0        i∈N0
        (i≠j)       (i≠j)
        
        Interpretação:
        - Para cada requisição j, viagem v e ônibus k:
          entrada = saída
        - Se um ônibus entra em uma requisição, deve sair dela
        - Princípio fundamental de conservação de fluxo em redes
        
        Args:
            modelo: Modelo Gurobi onde adicionar as restrições
            N: Lista de requisições [1, ..., n]
            N0: Lista incluindo garagem [0, 1, ..., n]
            x: Dicionário de variáveis binárias de roteamento
            V: Lista de viagens [1, ..., r]
            K: Lista de ônibus [1, ..., K]
        """
        for k in K:
            for v in V:
                for j in N:

                    entrada = gp.quicksum(x[i, j, v, k]
                                        for i in N0
                                        if i != j)

                    saida = gp.quicksum(x[j, i, v, k]
                                        for i in N0
                                        if i != j)

                    modelo.addConstr(
                        entrada - saida == 0,
                        name=f"conservacao_{j}_{v}_{k}"
                    )

    def _restricao_garagem(self, modelo: gp.Model, N: list[int], N0: list[int], 
                           V: list[int], K: list[int], x: dict, y: dict) -> None:
        """
        Adiciona restrições que controlam o início e fim de viagens na garagem.
        
        Estabelece que toda viagem deve começar e terminar na garagem (índice 0),
        e vincula as variáveis de roteamento x com as variáveis de ativação y.
        
        Restrições matemáticas:
        1. Início de viagem:
           Σ x[0,j,v,k] = y[v,k]    ∀v ∈ V, ∀k ∈ K
           j∈N
           
        2. Término de viagem:
           Σ x[i,0,v,k] = y[v,k]    ∀v ∈ V, ∀k ∈ K
           i∈N
        
        Interpretação:
        - Se y[v,k] = 1, então o ônibus k faz a viagem v
        - Se viagem é feita, deve sair da garagem exatamente uma vez
        - Se viagem é feita, deve voltar à garagem exatamente uma vez
        - Se y[v,k] = 0, não há movimento de/para garagem nesta viagem
        
        Args:
            modelo: Modelo Gurobi onde adicionar as restrições
            N: Lista de requisições [1, ..., n]
            N0: Lista incluindo garagem [0, 1, ..., n]
            V: Lista de viagens [1, ..., r]
            K: Lista de ônibus [1, ..., K]
            x: Dicionário de variáveis binárias de roteamento
            y: Dicionário de variáveis binárias de ativação de viagem
        """
        for k in K:
            for v in V:
                # Restrição de início: saída da garagem
                modelo.addConstr(
                    gp.quicksum(x[0, j, v, k]
                                for j in N) == y[v, k],
                    name=f"inicio_viagem_{v}_{k}"
                )
                # Restrição de término: retorno à garagem
                modelo.addConstr(
                    gp.quicksum(x[i, 0, v, k]
                                for i in N) == y[v, k],
                    name=f"termino_viagem_{v}_{k}"
                )
        
    def _restricao_sequencia(self, modelo: gp.Model, K: list[int], V: list[int],
                             y: dict) -> None:
        """
        Adiciona restrições de sequenciamento de viagens por ônibus.
        
        Garante que as viagens de cada ônibus sejam realizadas em ordem
        sequencial, evitando lacunas na numeração das viagens. Se um ônibus
        não faz a viagem v, então também não pode fazer viagens v+1, v+2, etc.
        
        Restrição matemática:
        y[v,k] ≤ y[v-1,k]    ∀v ∈ V\\{1}, ∀k ∈ K
        
        Interpretação:
        - Se y[v,k] = 1, então y[v-1,k] deve ser 1
        - Ônibus só pode fazer viagem v se já fez viagem v-1
        - Força uso sequencial: 1ª viagem → 2ª viagem → 3ª viagem → ...
        - Evita situações como: não fazer viagem 1, mas fazer viagem 2
        
        Exemplo:
        - Válido: y[1,k]=1, y[2,k]=1, y[3,k]=0
        - Inválido: y[1,k]=1, y[2,k]=0, y[3,k]=1
        
        Args:
            modelo: Modelo Gurobi onde adicionar as restrições
            K: Lista de ônibus [1, ..., K]
            V: Lista de viagens [1, ..., r]
            y: Dicionário de variáveis binárias de ativação de viagem
        """
        for k in K:
            for v in V:
                if v > 1:  # Aplica apenas para viagens 2, 3, ..., r
                    modelo.addConstr(
                        y[v, k] <= y[v-1, k],
                        name=f"sequencia_viagem_{v}_{k}"
                    )

    def _restricao_distancia(self, modelo: gp.Model, K: list[int], V: list[int],
                             dados: Dados, x: dict, N0: list[int]) -> None:
        """
        Adiciona restrições de distância máxima por viagem.
        
        Garante que cada viagem respeite a limitação de distância máxima,
        simulando restrições de autonomia dos ônibus ou políticas operacionais
        que limitam a distância total que pode ser percorrida em uma única viagem.
        
        Restrição matemática:
        Σ Σ D[i,j] * x[i,j,v,k] ≤ Dmax    ∀v ∈ V, ∀k ∈ K
        i∈N0 j∈N0
        (i≠j)
        
        Interpretação:
        - Para cada viagem v de cada ônibus k
        - Soma das distâncias de todos os arcos utilizados
        - Deve ser menor ou igual à distância máxima permitida (Dmax)
        - Previne viagens excessivamente longas
        
        Contexto prático:
        - Autonomia limitada dos ônibus
        - Tempo máximo de operação por viagem
        - Políticas de manutenção preventiva
        - Eficiência operacional
        
        Args:
            modelo: Modelo Gurobi onde adicionar as restrições
            K: Lista de ônibus [1, ..., K]
            V: Lista de viagens [1, ..., r]
            dados: Instância contendo matriz de distâncias D e limite Dmax
            x: Dicionário de variáveis binárias de roteamento
            N0: Lista incluindo garagem [0, 1, ..., n]
        """
        for k in K:
            for v in V:
                modelo.addConstr(
                    gp.quicksum(dados.D[i,j] * x[i, j, v, k]
                                for i in N0
                                for j in N0
                                if i != j) <= dados.Dmax,
                    name=f"distancia_maxima_{v}_{k}"
                )

    def _restricao_janela(self, modelo: gp.Model, dados: Dados, K: list[int],
                          V: list[int], N0: list[int], N: list[int], x: dict, 
                          B: dict) -> None:
        """
        Adiciona restrições de janelas de tempo para as requisições.
        
        Garante que cada requisição seja atendida dentro de sua janela de tempo
        específica, respeitando os horários de início mais cedo e fim mais tarde
        definidos para cada requisição.
        
        Restrições matemáticas:
        1. Limite inferior (início mais cedo):
           B[i,v,k] ≥ e[i-1] * Σ x[j,i,v,k]    ∀i ∈ N, ∀v ∈ V, ∀k ∈ K
                            j∈N0
                            (j≠i)
        
        2. Limite superior (fim mais tarde):
           B[i,v,k] ≤ l[i-1] * Σ x[j,i,v,k]    ∀i ∈ N, ∀v ∈ V, ∀k ∈ K
                            j∈N0
                            (j≠i)
        
        Interpretação:
        - B[i,v,k] é o tempo de chegada na requisição i
        - e[i-1] é o início da janela de tempo da requisição i (ajuste de índice)
        - l[i-1] é o fim da janela de tempo da requisição i (ajuste de índice)
        - Se a requisição i é visitada, então e[i-1] ≤ B[i,v,k] ≤ l[i-1]
        - Se não é visitada, as restrições são relaxadas (multiplicador = 0)
        
        Args:
            modelo: Modelo Gurobi onde adicionar as restrições
            dados: Instância contendo vetores e e l de janelas de tempo
            K: Lista de ônibus [1, ..., K]
            V: Lista de viagens [1, ..., r]
            N0: Lista incluindo garagem [0, 1, ..., n]
            N: Lista de requisições [1, ..., n]
            x: Dicionário de variáveis binárias de roteamento
            B: Dicionário de variáveis contínuas de tempo de chegada
        """
        for k in K:
            for v in V:
                for i in N:
                    # Limite inferior: não pode chegar antes do início da janela
                    modelo.addConstr(
                        B[i, v, k] >= dados.e[i-1] * gp.quicksum(x[j, i, v, k]
                        for j in N0 if i != j),
                        name=f"janela_inferior_{i}_{v}_{k}"
                    )
                    # Limite superior: não pode chegar após o fim da janela
                    modelo.addConstr(
                        B[i, v, k] <= dados.l[i-1] * gp.quicksum(x[j, i, v, k]
                        for j in N0 if i != j),
                        name=f"janela_superior_{i}_{v}_{k}"
                    )

    def _restricao_fluxo(self, modelo: gp.Model, dados: Dados, M: float,
                         K: list[int], V: list[int], N0: list[int], x: dict, 
                         B: dict) -> None:
        """
        Adiciona restrições de fluxo temporal entre requisições.
        
        Esta é a restrição mais complexa do modelo, responsável por:
        1. Sincronizar tempos de chegada entre requisições consecutivas
        2. Conectar viagens sequenciais do mesmo ônibus
        3. Garantir factibilidade temporal das rotas
        
        Existem três casos principais:
        
        CASO 1 - Primeira viagem saindo da garagem:
        s[0] + T[0,j] - M*(1-x[0,j,1,k]) ≤ B[j,1,k]    ∀j ∈ N0\\{0}, ∀k ∈ K
        
        CASO 2 - Movimento dentro da mesma viagem:
        B[i,v,k] + s[i] + T[i,j] - M*(1-x[i,j,v,k]) ≤ B[j,v,k]    
        ∀i,j ∈ N0, ∀v ∈ V, ∀k ∈ K (i≠j, exceto caso 1)
        
        CASO 3 - Transição entre viagens consecutivas:
        B[0,v-1,k] + s[0] + T[0,i] - M*(1-x[0,i,v,k]) ≤ B[i,v,k]    
        ∀i ∈ N, ∀v ∈ V\\{1}, ∀k ∈ K
        
        Componentes das restrições:
        - B[i,v,k]: Tempo de chegada na requisição i durante viagem v do ônibus k
        - s[i]: Tempo de serviço na requisição i (reabastecimento se i=0)
        - T[i,j]: Tempo de viagem da requisição i para j
        - M: Constante grande para relaxar restrições quando x[i,j,v,k] = 0
        
        Interpretação:
        - Se x[i,j,v,k] = 1: tempo_chegada_j ≥ tempo_chegada_i + serviço_i + viagem_i_j
        - Se x[i,j,v,k] = 0: restrição é relaxada (lado direito fica muito negativo)
        
        Args:
            modelo: Modelo Gurobi onde adicionar as restrições
            dados: Instância contendo matrizes s e T de tempos
            M: Constante grande para relaxamento de restrições
            K: Lista de ônibus [1, ..., K]
            V: Lista de viagens [1, ..., r]
            N0: Lista incluindo garagem [0, 1, ..., n]
            x: Dicionário de variáveis binárias de roteamento
            B: Dicionário de variáveis contínuas de tempo de chegada
        """

        for k in K:
            for v in V:
                for i in N0:
                    for j in N0:
                        
                        if i == j:
                            continue  # Não permitir arcos de um nó para ele mesmo
                        
                        # CASO 1: Primeira viagem saindo da garagem
                        elif i == 0 and v == 1:
                            modelo.addConstr(
                                dados.s[0] + dados.T[0, j] - M * (1 - x[0, j, 1, k]) 
                                <= B[j, 1, k],
                                name=f"fluxo_tempo_intra_0_{j}_{v}_{k}"
                            )

                        # CASO 2: Movimento dentro da mesma viagem (exceto caso 1)
                        else:
                            modelo.addConstr(
                                B[i, v, k] + dados.s[i] + dados.T[i, j]
                                - M * (1 - x[i, j, v, k]) <= B[j, v, k],
                            name=f"fluxo_tempo_intra_{i}_{j}_{v}_{k}"
                        )
                    
                    # CASO 3: Transição entre viagens consecutivas (v-1 → v)
                    if v > 1 and i != 0:
                        modelo.addConstr(
                            B[0, v-1, k] + dados.s[0] + dados.T[0, i] 
                            - M * (1 - x[0, i, v, k]) <= B[i, v, k],
                            name=f"fluxo_tempo_inter_{i}_{v}_{k}"
                        )

if __name__ == "__main__":
    """
    Exemplo de uso do solver de otimização exata.
    
    Este bloco demonstra como usar a classe Exato para resolver uma
    instância do problema de embarque remoto:
    
    1. Carrega dados de uma instância JSON
    2. Configura o solver com limite de tempo
    3. Resolve o problema
    4. Exibe a solução encontrada
    
    Parâmetros configuráveis:
    - Arquivo de instância: './dados/pequena.json'
    - Limite de tempo: 60 segundos
    
    Para usar com outras instâncias, modifique o caminho do arquivo.
    Para problemas maiores, aumente o limite de tempo.
    """
    from dados import carrega_dados_json
    
    # Carrega instância do problema
    dados = carrega_dados_json('./dados/media.json')
    
    # Configura solver com limite de tempo de 60 segundos
    metodo = Exato(limite_tempo=3600)
    
    # Resolve o problema
    solucao = metodo.resolve(dados)
    
    # Exibe resultados
    print(solucao)

    # Salva solução
    solucao.salvar('resultado.json')