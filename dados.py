"""
Módulo de Estruturas de Dados para o Problema de Embarque Remoto

Este módulo contém as classes e funções responsáveis por carregar, estruturar e 
manipular os dados das instâncias do problema de otimização do serviço de 
embarque remoto em aeroportos.

O problema consiste em otimizar rotas de ônibus que transportam passageiros 
entre portões de embarque e aeronaves em posições remotas, respeitando 
janelas de tempo e restrições operacionais.

Autor: André Batista
Data: Setembro 2025
"""

import json
import numpy as np
from typing import Optional

class Dados:
    """
    Classe para armazenar e organizar todos os dados de uma instância do 
    problema de embarque remoto.
    
    Esta classe encapsula todos os parâmetros necessários para a modelagem
    matemática do problema, incluindo:
    - Dimensões do problema (número de requisições, ônibus, viagens)
    - Matrizes de distância, custo e tempo
    - Janelas de tempo das requisições
    - Restrições operacionais
    
    Atributos:
        n (int): Número de requisições de transporte
        K (int): Número de ônibus disponíveis
        r (int): Número máximo de viagens por ônibus
        D (np.ndarray): Matriz de distâncias entre requisições (n+1 x n+1)
        c (np.ndarray): Matriz de custos entre requisições (n+1 x n+1)
        T (np.ndarray): Matriz de tempos de viagem entre requisições (n+1 x n+1)
        s (np.ndarray): Vetor de tempos de serviço por requisição (n+1)
        e (np.ndarray): Vetor de início das janelas de tempo (n)
        l (np.ndarray): Vetor de fim das janelas de tempo (n)
        Tmax (float): Tempo máximo permitido por viagem
    
    Nota:
        - O índice 0 sempre representa a garagem
        - Os índices 1 a n representam as requisições de transporte
        - Todas as matrizes têm dimensão (n+1) para incluir a garagem
    """
    
    def __init__(self, 
                 numeroRequisicoes: Optional[int] = None,
                 numeroOnibus: Optional[int] = None, 
                 distanciaRequisicoes: Optional[np.ndarray] = None, 
                 custo: Optional[np.ndarray] = None, 
                 tempoServico: Optional[np.ndarray] = None, 
                 tempoRequisicoes: Optional[np.ndarray] = None, 
                 inicioJanela: Optional[np.ndarray] = None, 
                 fimJanela: Optional[np.ndarray] = None, 
                 numeroMaximoViagens: Optional[int] = None, 
                 tempoMaximo: Optional[float] = None) -> None:
        """
        Inicializa uma instância da classe Dados.
        
        Args:
            numeroRequisicoes: Número total de requisições de transporte
            numeroOnibus: Número de ônibus disponíveis na frota
            distanciaRequisicoes: Matriz (n+1)x(n+1) com distâncias entre pontos
            custo: Matriz (n+1)x(n+1) com custos de deslocamento
            tempoServico: Vetor (n+1) com tempos de serviço em cada ponto
            tempoRequisicoes: Matriz (n+1)x(n+1) com tempos de viagem
            inicioJanela: Vetor (n) com início das janelas de tempo
            fimJanela: Vetor (n) com fim das janelas de tempo
            numeroMaximoViagens: Máximo de viagens que um ônibus pode fazer
            tempoMaximo: Tempo máximo por viagem
        """
        # Dimensões do problema
        self.n = numeroRequisicoes          # Número de requisições
        self.K = numeroOnibus               # Número de ônibus
        self.r = numeroMaximoViagens        # Máximo de viagens por ônibus
        
        # Matrizes de distância, custo e tempo entre requisições
        self.D = distanciaRequisicoes       # Matriz de distâncias (n+1 x n+1)
        self.c = custo                      # Matriz de custos (n+1 x n+1)
        self.T = tempoRequisicoes          # Matriz de tempos de viagem (n+1 x n+1)
        
        # Tempos de serviço em cada ponto
        self.s = tempoServico              # Vetor de tempos de serviço (n+1)
        
        # Janelas de tempo das requisições
        self.e = inicioJanela              # Início das janelas de tempo (n)
        self.l = fimJanela                 # Fim das janelas de tempo (n)
        
        # Restrições operacionais
        self.Tmax = tempoMaximo            # Tempo máximo por viagem
    
    def __str__(self) -> str:
        """
        Representação em string da instância para visualização.
        
        Returns:
            str: Resumo formatado dos principais parâmetros da instância.
        """
        capacidade_total = self.K * self.r if self.K is not None and self.r is not None else None
        utilizacao = (self.n / capacidade_total * 100) if capacidade_total and self.n else None
        utilizacao_str = f"{utilizacao:.1f}%" if utilizacao else "N/A"
        
        return f"""
=== INSTÂNCIA DO PROBLEMA DE EMBARQUE REMOTO ===
Requisições: {self.n}
Ônibus: {self.K}
Máximo de viagens por ônibus: {self.r}
Tempo máximo por viagem: {self.Tmax:.1f} min
==============================================="""
    
    def __repr__(self) -> str:
        """Representação técnica da instância."""
        return f"Dados(n={self.n}, K={self.K}, r={self.r}, Tmax={self.Tmax})"
    

def carrega_dados_json(arquivo: str) -> Dados:
    """
    Carrega uma instância do problema a partir de um arquivo JSON.
    
    Esta função lê um arquivo JSON contendo todos os dados necessários para
    uma instância do problema de embarque remoto e os organiza em uma 
    estrutura de dados apropriada para uso nos algoritmos de otimização.
    
    Args:
        arquivo (str): Caminho para o arquivo JSON contendo os dados da instância.
                      O arquivo deve conter os seguintes campos obrigatórios:
                      - numeroRequisicoes: int
                      - numeroOnibus: int
                      - numeroMaximoViagens: int
                      - distanciaRequisicoes: lista 2D (n+1 x n+1)
                      - custo: lista 2D (n+1 x n+1)
                      - tempoServico: lista 1D (n+1)
                      - tempoRequisicoes: lista 2D (n+1 x n+1)
                      - inicioJanela: lista 1D (n)
                      - fimJanela: lista 1D (n)
                      - distanciaMaxima: float
    
    Returns:
        Dados: Objeto contendo todos os dados da instância organizados e 
               convertidos para arrays NumPy quando apropriado.
    
    Raises:
        FileNotFoundError: Se o arquivo especificado não for encontrado.
        KeyError: Se algum campo obrigatório estiver ausente no JSON.
        json.JSONDecodeError: Se o arquivo não contiver JSON válido.
    
    Example:
        >>> dados = carrega_dados_json("./dados/pequena.json")
        >>> print(f"Instância com {dados.n} requisições e {dados.K} ônibus")
        >>> print(f"Máximo de {dados.r} viagens por ônibus")
    
    Nota:
        - As matrizes são automaticamente convertidas para np.ndarray
        - O índice 0 sempre representa a garagem nos arrays
        - As janelas de tempo são indexadas de 0 a n-1 (sem incluir garagem)
    """
    # Carrega o arquivo JSON
    with open(arquivo, "r", encoding="utf-8") as f:
        dados_dict = json.load(f)
    
    # Cria e retorna objeto Dados com conversão automática para NumPy arrays
    return Dados(
        numeroRequisicoes=dados_dict["numeroRequisicoes"],
        numeroOnibus=dados_dict["numeroOnibus"],
        distanciaRequisicoes=np.array(dados_dict["distanciaRequisicoes"]),
        custo=np.array(dados_dict["custo"]),
        tempoServico=np.array(dados_dict["tempoServico"]),
        tempoRequisicoes=np.array(dados_dict["tempoRequisicoes"]),
        inicioJanela=np.array(dados_dict["inicioJanela"]),
        fimJanela=np.array(dados_dict["fimJanela"]),
        numeroMaximoViagens=dados_dict["numeroMaximoViagens"],
        tempoMaximo=dados_dict.get("tempoMaximoViagem", dados_dict.get("distanciaMaxima", None))
    )
