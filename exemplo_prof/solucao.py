"""
Módulo de Representação de Soluções para o Problema de Embarque Remoto

Este módulo contém a classe Solucao, responsável por armazenar e organizar
os resultados obtidos pela resolução do problema de otimização de rotas
de ônibus em aeroportos com embarque remoto.

A classe encapsula:
- Rotas detalhadas de cada ônibus por viagem
- Arcos utilizados nas rotas ótimas
- Tempos de chegada em cada requisição
- Valor da função objetivo (custo total)
- Métodos para extração de dados do modelo Gurobi
- Representação formatada dos resultados

Funcionalidades principais:
- Carregamento automático de soluções do Gurobi
- Construção de rotas a partir de variáveis de decisão
- Cálculo de tempos de chegada
- Visualização organizada dos resultados

Autor: André Batista
Data: Setembro 2025
"""

import gurobipy as gp
from dados import Dados
from typing import Dict, List, Optional, Any
import json

class Solucao:
    """
    Classe para armazenar e organizar soluções do problema de embarque remoto.
    
    Esta classe encapsula todos os resultados obtidos pela resolução do modelo
    de otimização, incluindo rotas detalhadas, tempos de chegada e valor da
    função objetivo. Fornece métodos para extrair automaticamente os dados
    do modelo Gurobi e apresentá-los de forma organizada.
    
    A solução contém informações hierárquicas organizadas por:
    - Ônibus (k): Cada veículo da frota
    - Viagem (v): Cada viagem que um ônibus pode realizar
    - Requisições: Pontos visitados em cada viagem
    
    Atributos:
        rota (Dict[int, Dict[int, List[int]]]): 
            Rotas por ônibus e viagem. rota[k][v] = [0, req1, req2, ..., 0]
            
        arcos (Dict[int, Dict[int, List[tuple]]]): 
            Arcos utilizados por ônibus e viagem. arcos[k][v] = [(i,j), ...]
            
        chegada (Dict[int, Dict[int, List[float]]]): 
            Tempos de chegada por ônibus e viagem. chegada[k][v] = [t0, t1, ...]
            
        fx (Optional[float]): 
            Valor da função objetivo (custo total da solução)
    
    Example:
        >>> solucao = Solucao()
        >>> solucao.carrega_modelo_gurobi(modelo, dados)
        >>> print(f"Custo total: {solucao.fx}")
        >>> print(solucao)  # Exibe rotas formatadas
    
    Note:
        - Índice 0 sempre representa a garagem
        - Rotas vazias indicam viagens não realizadas
        - Tempos são em unidades conforme definido na instância
    """

    def __init__(self) -> None:
        """
        Inicializa uma instância vazia da classe Solucao.
        
        Cria as estruturas de dados vazias que serão preenchidas
        posteriormente através do método carrega_modelo_gurobi().
        
        Inicialização:
            - rota: Dicionário vazio para armazenar rotas
            - arcos: Dicionário vazio para armazenar arcos utilizados  
            - chegada: Dicionário vazio para tempos de chegada
            - fx: None (será definido após carregamento do modelo)
        """
        self.rota: Dict[int, Dict[int, List[int]]] = {}
        self.arcos: Dict[int, Dict[int, List[tuple]]] = {}
        self.chegada: Dict[int, Dict[int, List[float]]] = {}
        self.fx: Optional[float] = None

    def carrega_modelo_gurobi(self, modelo: gp.Model, dados: Dados) -> None:
        """
        Carrega a solução a partir de um modelo Gurobi resolvido.
        
        Este método extrai automaticamente todos os dados relevantes de um
        modelo Gurobi após a otimização, organizando-os nas estruturas
        internas da classe para fácil acesso e manipulação.
        
        Processo de extração:
        1. Verifica se existe solução válida
        2. Valida dados de entrada
        3. Define conjuntos de índices
        4. Para cada ônibus e viagem:
           - Extrai variáveis x[i,j,v,k] ativas (arcos utilizados)
           - Constrói rota sequencial a partir dos arcos
           - Extrai tempos de chegada B[i,v,k]
        5. Armazena valor da função objetivo
        
        Detalhes técnicos:
        - Variáveis x > 0.5 são consideradas ativas (binárias)
        - Rotas são construídas seguindo a sequência de arcos
        - Tempos incluem chegada na garagem (tempo 0)
        - Rotas vazias indicam viagens não utilizadas
        
        Args:
            modelo: Modelo Gurobi resolvido com solução ótima/factível
            dados: Instância original contendo dimensões do problema
            
        Returns:
            None: Modifica os atributos internos da instância
            
        Raises:
            Implicitamente pode gerar erros se:
            - Modelo não foi resolvido
            - Variáveis não existem no modelo
            - Dados inconsistentes
            
        Side Effects:
            - Preenche self.rota com rotas de todos os ônibus
            - Preenche self.arcos com arcos utilizados
            - Preenche self.chegada com tempos de chegada
            - Define self.fx com valor da função objetivo
            
        Example:
            >>> modelo.optimize()  # Resolve o modelo
            >>> if modelo.Status == GRB.OPTIMAL:
            >>>     solucao = Solucao()
            >>>     solucao.carrega_modelo_gurobi(modelo, dados)
            >>>     print(f"Solução com custo {solucao.fx}")
        """

        # Verificação de existência de solução
        if modelo.SolCount == 0:
            print("Solução não encontrada.")
            return

        # Validação dos dados de entrada
        if dados.K is None or dados.r is None or dados.n is None:
            print("Dados inválidos.")
            return

        # Definição dos conjuntos de índices
        K = range(1, dados.K + 1)  # Ônibus: {1, 2, ..., K}
        V = range(1, dados.r + 1)  # Viagens: {1, 2, ..., r}
        N = range(1, dados.n + 1)  # Requisições: {1, 2, ..., n}
        N0 = range(0, dados.n + 1)  # Requisições + garagem: {0, 1, ..., n}

        # Iteração sobre todos os ônibus da frota
        for k in K:

            # Inicialização das estruturas para o ônibus k
            self.rota[k] = {}
            self.arcos[k] = {}
            self.chegada[k] = {}

            # Iteração sobre todas as viagens possíveis do ônibus k
            for v in V:

                # Inicialização das estruturas para a viagem v do ônibus k
                self.rota[k][v] = []
                self.arcos[k][v] = []
                self.chegada[k][v] = []

                # Extração dos arcos ativos (variáveis x[i,j,v,k] = 1)
                arcos = []
                for i in N0:
                    for j in N0:

                        if i == j:
                            continue  # Não permitir arcos de um nó para ele mesmo
                        
                        # Obter valor da variável de decisão x[i,j,v,k]
                        var_x = modelo.getVarByName(f"x_{i}_{j}_{v}_{k}")
                        if var_x is not None:
                            x = var_x.X
                            
                            # Considerar arco ativo se x > 0.5 (tolerância numérica)
                            if x > 0.5:
                                arcos.append((i, j))

                # Verificação se existem arcos ativos para esta viagem
                if not arcos:
                    continue  # Viagem não utilizada - pular para próxima viagem

                # Construção sequencial da rota a partir dos arcos ativos
                # Algoritmo: seguir encadeamento de arcos partindo da garagem (0)
                rota = [0]  # Inicia sempre na garagem
                n_requisicoes = len(arcos) - 1  # Número de requisições na rota
                
                # Construir sequência seguindo os arcos conectados
                for i in range(n_requisicoes):
                    for j in range(len(arcos)):
                        # Procurar arco que sai do último nó da rota
                        if arcos[j][0] == rota[-1]:
                            rota.append(arcos[j][1])  # Adicionar destino do arco
                            break
                
                rota.append(0)  # Termina sempre na garagem
                self.rota[k][v] = rota  # Armazenar rota construída

                # Extração dos tempos de chegada em cada ponto da rota
                instantes = [0.]  # Tempo inicial na garagem = 0
                for requisicao in rota[1:]:  # Para cada ponto da rota (exceto primeiro 0)
                    # Obter tempo de chegada da variável B[requisicao,v,k]
                    var_B = modelo.getVarByName(f"B_{requisicao}_{v}_{k}")
                    if var_B is not None:
                        B = var_B.X
                        instantes.append(B)

                self.chegada[k][v] = instantes  # Armazenar tempos de chegada

        # Armazenar valor da função objetivo (custo total da solução)
        self.fx = modelo.ObjVal

    def salvar(self, nome_arquivo: str) -> None:
        """
        Salva a solução em formato JSON para facilitar a análise e integração.
        
        Este método serializa todos os dados da solução (rotas, arcos, 
        tempos de chegada e função objetivo) em formato JSON estruturado,
        permitindo fácil carregamento e processamento posterior.
        
        Estrutura do JSON:
        {
            "fx": valor_funcao_objetivo,
            "onibus": {
            "k": {
                "viagem_v": {
                "rota": [0, req1, req2, ..., 0],
                "arcos": [[i, j], [j, k], ...],
                "chegada": [t0, t1, t2, ...]
                }
            }
            }
        }
        
        Args:
            nome_arquivo (str): Caminho do arquivo JSON onde a solução será salva
            
        Returns:
            None: Escreve diretamente no arquivo especificado
            
        Raises:
            IOError: Se ocorrer um erro ao abrir ou escrever no arquivo
            
        Example:
            >>> solucao.salvar("resultado.json")
            # A solução é salva em formato JSON estruturado
        """
        
        # Estruturar dados para serialização JSON
        dados_json = {
            "fx": self.fx,
            "onibus": {}
        }
        
        # Organizar dados por ônibus
        for k in self.rota.keys():
            dados_json["onibus"][str(k)] = {}
            
            for v in self.rota[k].keys():
                if self.rota[k][v]:  # Apenas viagens não vazias
                    dados_json["onibus"][str(k)][f"viagem_{v}"] = {
                    "rota": self.rota[k][v],
                    "arcos": list(self.arcos[k][v]) if k in self.arcos and v in self.arcos[k] else [],
                    "chegada": self.chegada[k][v] if k in self.chegada and v in self.chegada[k] else []
                    }
        
        try:
            with open(nome_arquivo, 'w', encoding='utf-8') as f:
                json.dump(dados_json, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Erro ao salvar a solução em JSON: {e}")

    def __str__(self) -> str:
        """
        Retorna representação formatada da solução para visualização.
        
        Constrói uma string legível mostrando as rotas de cada ônibus,
        consolidando todas as viagens de um ônibus em uma rota completa.
        Ônibus não utilizados são explicitamente indicados.
        
        Formato de saída:
        - "Ônibus k: [0, req1, req2, 0, req3, req4, 0]" (múltiplas viagens)
        - "Ônibus k: Não utilizado" (ônibus sem viagens)
        
        Processo de construção:
        1. Identifica ônibus e viagens disponíveis
        2. Para cada ônibus:
           - Concatena todas as viagens não vazias
           - Remove garagens intermediárias (exceto primeira e última)
           - Formata resultado final
        
        Returns:
            str: Representação textual formatada da solução completa
            
        Example:
            >>> print(solucao)
            Ônibus 1: [0, 1, 2, 0, 3, 4, 0]
            Ônibus 2: [0, 5, 6, 0]
            Ônibus 3: Não utilizado
            
        Note:
            - Índice 0 representa a garagem
            - Rotas concatenadas mostram sequência completa de operação
            - Múltiplas viagens são visualmente distintas pelos retornos à garagem
        """
        # Obter conjuntos de ônibus e viagens disponíveis
        K = self.rota.keys()
        V = self.rota[next(iter(K))].keys() if K else []
        
        resultado = ""
        
        # Processar cada ônibus individualmente
        for k in K:
            rota_completa = []
            
            # Concatenar todas as viagens do ônibus k
            for v in V:
                if self.rota[k][v]:  # Se a viagem v não está vazia
                    if not rota_completa:  # Primeira viagem
                        rota_completa = self.rota[k][v]
                    else:  # Viagens subsequentes - remove o 0 inicial
                        rota_completa.extend(self.rota[k][v][1:])
            
            # Formatar resultado para o ônibus k
            if rota_completa:
                resultado += f"Ônibus {k}: {rota_completa}\n"
            else:
                resultado += f"Ônibus {k}: Não utilizado\n"

        return resultado.strip()  # Remove quebra de linha final