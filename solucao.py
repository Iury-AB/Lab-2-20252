"""
Módulo de Representação de Soluções para o Problema de Embarque Remoto

Este módulo contém a classe Solucao, responsável por armazenar e 
organizar os resultados obtidos pela resolução do problema de otimização 
de rotas de ônibus em aeroportos com embarque remoto.

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
            - chegada: Dicionário vazio para tempos de chegada
            - fx: None (será definido após carregamento do modelo)
        """
        self.rota: Dict[int, Dict[int, List[int]]] = {}
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
            self.chegada[k] = {}

            # Iteração sobre todas as viagens possíveis do ônibus k
            for v in V:

                # Inicialização das estruturas para a viagem v do ônibus k
                self.rota[k][v] = []
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
                instantes = []
                for requisicao in rota[1:]:  # Para cada ponto da rota (exceto primeiro 0)
                    # Obter tempo de chegada da variável B[requisicao,v,k]
                    var_B = modelo.getVarByName(f"B_{requisicao}_{v}_{k}")
                    if var_B is not None:
                        B = var_B.X
                        instantes.append(B)
                        if requisicao == rota[1]:
                            tempo_saida_garagem = B - dados.T[0][requisicao] - dados.s[0]
                            instantes.insert(0, tempo_saida_garagem)

                self.chegada[k][v] = instantes  # Armazenar tempos de chegada

        # Armazenar valor da função objetivo (custo total da solução)
        self.fx = modelo.ObjVal

    def carrega_para_modelo_gurobi(self, modelo: gp.Model, dados: Dados) -> None:
        """
        Carrega a solução atual para as variáveis de um modelo Gurobi.
        
        Este método é o inverso de carrega_modelo_gurobi(), permitindo
        que uma solução armazenada seja recarregada em um modelo Gurobi
        para uso como ponto inicial (warm start) ou para validação.
        
        Processo de carregamento:
        1. Valida se a solução contém dados
        2. Obtém conjuntos de índices dos dados
        3. Para cada ônibus e viagem:
        - Identifica arcos da rota
        - Define x[i,j,v,k] = 1 para arcos utilizados
        - Define x[i,j,v,k] = 0 para arcos não utilizados
        - Define y[v,k] = 1 se viagem é utilizada
        - Define B[i,v,k] com tempos de chegada
        4. Atualiza o modelo com os valores
        
        Aplicações:
        - Warm start: acelerar resolução fornecendo solução inicial
        - Validação: verificar factibilidade de solução construída
        - Debugging: comparar soluções manualmente construídas
        - Resolução iterativa: usar solução anterior como ponto de partida
        
        Args:
            modelo: Modelo Gurobi onde carregar a solução
            dados: Instância original contendo dimensões do problema
            
        Returns:
            None: Modifica as variáveis do modelo diretamente
            
        Raises:
            ValueError: Se a solução está vazia ou dados são inconsistentes
            AttributeError: Se variáveis não existem no modelo
            
        Example:
            >>> # Resolver problema e salvar solução
            >>> solucao1 = solver.resolve(dados)
            >>> 
            >>> # Criar novo modelo e usar solução como warm start
            >>> modelo2 = criar_modelo(dados)
            >>> solucao1.carrega_para_modelo_gurobi(modelo2, dados)
            >>> modelo2.optimize()  # Mais rápido com warm start
            
        Note:
            - Variáveis não mencionadas na solução são definidas como 0
            - O modelo deve ter as mesmas variáveis que geraram a solução
            - Útil para comparar soluções heurísticas com o ótimo
            
        See Also:
            carrega_modelo_gurobi: Método inverso que extrai solução do modelo
        """
        
        # Validar se a solução contém dados válidos
        if not self.rota:
            raise ValueError("Solução vazia. Não há dados para carregar.")

        # Validar dados de entrada
        if dados.K is None or dados.r is None or dados.n is None:
            raise ValueError("Dados inválidos.")
        
        # Definição dos conjuntos de índices
        K = range(1, dados.K + 1)
        V = range(1, dados.r + 1)
        N = range(1, dados.n + 1)
        N0 = range(0, dados.n + 1)
        
        # Inicializar todas as variáveis com 0
        for k in K:
            for v in V:
                # Variável y[v,k] - viagem ativa ou não
                var_y = modelo.getVarByName(f"y_{v}_{k}")
                if var_y is not None:
                    # Viagem é ativa se existe rota não vazia
                    if k in self.rota and v in self.rota[k] and self.rota[k][v]:
                        var_y.Start = 1
                    else:
                        var_y.Start = 0
                
                # Variáveis x[i,j,v,k] - arcos
                for i in N0:
                    for j in N0:
                        if i == j:
                            continue
                        
                        var_x = modelo.getVarByName(f"x_{i}_{j}_{v}_{k}")
                        if var_x is not None:
                            var_x.Start = 0  # Inicializa como 0
                
                # Variáveis B[i,v,k] - tempos de chegada
                for i in N0:
                    var_B = modelo.getVarByName(f"B_{i}_{v}_{k}")
                    if var_B is not None:
                        var_B.Start = 0  # Inicializa como 0
        
        # Carregar valores da solução
        for k in self.rota.keys():
            for v in self.rota[k].keys():
                rota = self.rota[k][v]
                
                # Pular viagens vazias
                if not rota or len(rota) <= 1:
                    continue
                
                # Definir y[v,k] = 1 para viagem ativa
                var_y = modelo.getVarByName(f"y_{v}_{k}")
                if var_y is not None:
                    var_y.Start = 1
                
                # Definir x[i,j,v,k] = 1 para arcos da rota
                for idx in range(len(rota) - 1):
                    i = rota[idx]
                    j = rota[idx + 1]
                    
                    var_x = modelo.getVarByName(f"x_{i}_{j}_{v}_{k}")
                    if var_x is not None:
                        var_x.Start = 1
                
                # Definir B[i,v,k] com tempos de chegada
                if k in self.chegada and v in self.chegada[k]:
                    tempos = self.chegada[k][v]
                    
                    for idx, i in enumerate(rota):
                        if idx < len(tempos):
                            var_B = modelo.getVarByName(f"B_{i}_{v}_{k}")
                            if var_B is not None:
                                var_B.Start = tempos[idx]
        
        # Atualizar modelo com os valores iniciais
        modelo.update()

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
                    "chegada": self.chegada[k][v] if k in self.chegada and v in 
                    self.chegada[k] else []
                    }
        
        try:
            with open(nome_arquivo, 'w', encoding='utf-8') as f:
                json.dump(dados_json, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Erro ao salvar a solução em JSON: {e}")

    def carregar(self, nome_arquivo: str) -> None:
        """
        Carrega uma solução previamente salva de um arquivo JSON.
        
        Este método é o inverso de salvar(), permitindo recuperar uma
        solução armazenada em formato JSON e reconstruir todas as estruturas
        internas da classe (rotas, arcos, tempos de chegada e função objetivo).
        
        O método valida a estrutura do JSON e reconstrói os dicionários
        internos mantendo os tipos de dados corretos (int para índices,
        float para tempos).
        
        Args:
            nome_arquivo (str): Caminho do arquivo JSON contendo a solução
            
        Returns:
            None: Atualiza os atributos internos da instância
            
        Raises:
            FileNotFoundError: Se o arquivo especificado não existe
            json.JSONDecodeError: Se o arquivo não contém JSON válido
            KeyError: Se a estrutura do JSON está incorreta
            
        Example:
            >>> solucao = Solucao()
            >>> solucao.carregar("resultado.json")
            >>> print(f"Custo carregado: {solucao.fx}")
            >>> print(solucao)
            
        Note:
            - O arquivo deve ter sido gerado pelo método salvar()
            - Chaves numéricas são convertidas de strings para inteiros
            
        See Also:
            salvar: Método que serializa a solução em JSON
        """
        
        try:
            # Carregar dados do arquivo JSON
            with open(nome_arquivo, 'r', encoding='utf-8') as f:
                dados_json = json.load(f)
            
            # Limpar estruturas existentes
            self.rota = {}
            self.chegada = {}
            
            # Carregar função objetivo
            self.fx = dados_json.get("fx")
            
            # Reconstruir estruturas de dados
            onibus_data = dados_json.get("onibus", {})
            
            for k_str, viagens_data in onibus_data.items():
                k = int(k_str)  # Converter chave de string para int
                
                # Inicializar estruturas para o ônibus k
                self.rota[k] = {}
                self.chegada[k] = {}
                
                for viagem_str, viagem_data in viagens_data.items():
                    # Extrair número da viagem (formato: "viagem_v")
                    v = int(viagem_str.split('_')[1])
                    
                    # Carregar rota
                    self.rota[k][v] = viagem_data.get("rota", [])
                    
                    # Carregar tempos de chegada
                    self.chegada[k][v] = viagem_data.get("chegada", [])
            
            print(f"Solução carregada com sucesso de {nome_arquivo}")
            
        except FileNotFoundError:
            print(f"Erro: Arquivo '{nome_arquivo}' não encontrado.")
            raise
        except json.JSONDecodeError as e:
            print(f"Erro ao decodificar JSON: {e}")
            raise
        except (KeyError, ValueError) as e:
            print(f"Erro na estrutura do arquivo JSON: {e}")
            raise
        except Exception as e:
            print(f"Erro inesperado ao carregar solução: {e}")
            raise

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
                        rota_completa = self.rota[k][v].copy()
                    else:  # Viagens subsequentes - remove o 0 inicial
                        rota_completa.extend(self.rota[k][v][1:])
            
            # Formatar resultado para o ônibus k
            if rota_completa:
                resultado += f"Ônibus {k}: {rota_completa}\n"
            else:
                resultado += f"Ônibus {k}: Não utilizado\n"

        return resultado.strip()  # Remove quebra de linha final