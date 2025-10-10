"""
Módulo de Utilitários para Análise de Instâncias do Problema de Embarque Remoto

Este módulo contém funções auxiliares para carregar, analisar e visualizar
instâncias do problema de otimização de rotas de ônibus em aeroportos com
embarque remoto.

Funcionalidades principais:
- Carregamento de instâncias a partir de arquivos JSON
- Análise estatística detalhada de instâncias
- Visualização do layout físico do aeroporto
- Gráficos de janelas de tempo das requisições
- Relatórios comparativos entre múltiplas instâncias
- Análise de eficiência operacional

Visualizações disponíveis:
- Layout 2D do aeroporto com posições dos pontos
- Gráficos de barras das janelas de tempo
- Relatórios comparativos multidimensionais
- Análise de utilização de recursos

Dependências:
- json: Carregamento de dados de instâncias
- numpy: Operações matemáticas e análise estatística
- matplotlib: Geração de gráficos e visualizações
- pandas: Manipulação de dados tabulares
- datetime: Manipulação de dados temporais

Autor: André Batista
Data: Setembro 2025
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List, Any, Tuple

def carregar_instancia(nome_arquivo: str) -> Dict[str, Any]:
    """
    Carrega uma instância do problema a partir de um arquivo JSON.
    
    Esta função lê um arquivo JSON contendo todos os dados de uma instância
    do problema de embarque remoto e retorna um dicionário com os dados
    organizados para análise e processamento.
    
    Args:
        nome_arquivo (str): Caminho para o arquivo JSON da instância.
                           Deve conter campos como numeroRequisicoes, 
                           numeroOnibus, coordenadas_pontos, etc.
    
    Returns:
        Dict[str, Any]: Dicionário contendo todos os dados da instância:
            - numeroRequisicoes: Número de requisições de transporte
            - numeroOnibus: Número de ônibus disponíveis
            - coordenadas_pontos: Posições físicas dos pontos
            - detalhes_voos: Informações detalhadas dos voos
            - inicioJanela/fimJanela: Janelas de tempo
            - distanciaRequisicoes: Matriz de distâncias
            - E outros campos específicos da instância
    
    Raises:
        FileNotFoundError: Se o arquivo especificado não existir
        json.JSONDecodeError: Se o arquivo não contiver JSON válido
        UnicodeDecodeError: Se houver problemas de codificação
    
    Example:
        >>> dados = carregar_instancia('dados/pequena.json')
        >>> print(f"Instância com {dados['numeroRequisicoes']} requisições")
        >>> print(f"Número de voos: {len(dados['detalhes_voos'])}")
    
    Note:
        - O arquivo deve estar em formato JSON válido
        - Recomenda-se usar codificação UTF-8
        - Campos obrigatórios devem estar presentes para análise completa
    """
    with open(nome_arquivo, 'r', encoding='utf-8') as f:
        return json.load(f)

def analisar_instancia(dados: Dict[str, Any], nome_instancia: str) -> Dict[str, Any]:
    """
    Realiza análise estatística completa de uma instância do problema.
    
    Esta função examina todos os aspectos de uma instância, calculando
    métricas importantes para compreender a complexidade e características
    do problema, incluindo análise temporal, espacial e operacional.
    
    Análises realizadas:
    1. **Dimensões básicas**: Requisições, ônibus, capacidades
    2. **Análise de voos**: Tipos, passageiros, distribuição
    3. **Análise temporal**: Janelas de tempo, duração operacional
    4. **Análise espacial**: Distâncias entre pontos
    5. **Análise operacional**: Tempos de serviço, eficiência
    
    Args:
        dados: Dicionário contendo todos os dados da instância
               (resultado de carregar_instancia())
        nome_instancia: Nome identificador da instância para relatórios
    
    Returns:
        Dict[str, Any]: Dicionário com métricas calculadas:
            - nome: Nome da instância
            - requisicoes: Número de requisições
            - onibus: Número de ônibus
            - max_viagens: Máximo de viagens por ônibus
            - capacidade_total: Capacidade total de viagens
            - utilizacao: Taxa de utilização (0-1)
            - voos: Número total de voos
            - passageiros_total: Passageiros totais
            - duracao_operacao: Duração em minutos
            - distancia_media: Distância média entre requisições
            - tempo_servico_medio: Tempo médio de serviço
    
    Side Effects:
        - Imprime relatório detalhado na saída padrão
        - Calcula e exibe métricas em tempo real
    
    Example:
        >>> dados = carregar_instancia('dados/media.json')
        >>> analise = analisar_instancia(dados, 'media')
        >>> print(f"Utilização: {analise['utilizacao']:.1%}")
        
    Note:
        - Assume formato específico do JSON da instância
        - Calcula métricas derivadas para análise de eficiência
        - Fornece insights sobre dimensionamento e complexidade
    """
    print(f"\n=== ANÁLISE DA INSTÂNCIA: {nome_instancia.upper()} ===")
    
    # ===== INFORMAÇÕES BÁSICAS E DIMENSIONAMENTO =====
    n = dados['numeroRequisicoes']                          # Total de requisições
    K = dados['numeroOnibus']                               # Frota de ônibus
    Tmax = dados.get('tempoMaximoViagem', dados.get('distanciaMaxima', 0))  # Tempo máximo por viagem
    V_max = dados.get('numeroMaximoViagens', 5)             # Viagens por ônibus
    
    print(f"Número de requisições: {n}")
    print(f"Número de ônibus: {K}")
    print(f"Máximo de viagens por ônibus: {V_max}")
    print(f"Capacidade total de viagens: {K * V_max}")
    print(f"Utilização estimada: {n / (K * V_max) * 100:.1f}%")
    print(f"Tempo máximo por viagem: {Tmax:.1f} min")
    
    # ===== ANÁLISE DETALHADA DOS VOOS (MODELO DESEMBARQUE-EMBARQUE) =====
    voos = dados['detalhes_voos']
    print(f"\nNúmero de voos: {len(voos)}")
    
    # Verificar se é o novo modelo (com desembarque e embarque separados)
    if 'n_passageiros_desembarque' in voos[0]:
        # Novo modelo: cada voo tem desembarque e embarque
        passageiros_desembarque = sum(v['n_passageiros_desembarque'] for v in voos)
        passageiros_embarque = sum(v['n_passageiros_embarque'] for v in voos)
        requisicoes_desembarque = sum(v['n_requisicoes_desembarque'] for v in voos)
        requisicoes_embarque = sum(v['n_requisicoes_embarque'] for v in voos)
        
        print(f"Passageiros em desembarque: {passageiros_desembarque}")
        print(f"Passageiros em embarque: {passageiros_embarque}")
        print(f"Total de passageiros: {passageiros_desembarque + passageiros_embarque}")
        print(f"Requisições de desembarque: {requisicoes_desembarque}")
        print(f"Requisições de embarque: {requisicoes_embarque}")
        print(f"Média de passageiros por voo (desembarque): {passageiros_desembarque / len(voos):.1f}")
        print(f"Média de passageiros por voo (embarque): {passageiros_embarque / len(voos):.1f}")
        
        # Estatísticas de turnaround
        turnaround_medio = np.mean([v['tempo_turnaround'] for v in voos])
        print(f"Tempo médio de turnaround: {turnaround_medio:.1f} min")
        
        passageiros_total = passageiros_desembarque + passageiros_embarque
    else:
        # Modelo antigo: embarque OU desembarque
        passageiros_total = sum(v['n_passageiros'] for v in voos)
        passageiros_medio = passageiros_total / len(voos)
        
        embarques = [v for v in voos if v['tipo'] == 'embarque']
        desembarques = [v for v in voos if v['tipo'] == 'desembarque']
        
        print(f"Passageiros total: {passageiros_total}")
        print(f"Passageiros por voo (média): {passageiros_medio:.1f}")
        print(f"Embarques: {len(embarques)}, Desembarques: {len(desembarques)}")
    
    # ===== ANÁLISE TEMPORAL E JANELAS DE TEMPO =====
    e = np.array(dados['inicioJanela'])                     # Início das janelas
    l = np.array(dados['fimJanela'])                        # Fim das janelas
    
    print(f"Janela de tempo mais cedo: {e.min():.1f} min")
    print(f"Janela de tempo mais tarde: {l.max():.1f} min")
    print(f"Duração total da operação: {l.max() - e.min():.1f} min")
    
    # ===== ANÁLISE ESPACIAL E DISTÂNCIAS =====
    D = np.array(dados['distanciaRequisicoes'])
    distancias_nao_zero = D[D > 0]                          # Excluir distâncias zero
    
    print(f"Distância média entre requisições: {distancias_nao_zero.mean():.2f}m")
    print(f"Distância máxima entre requisições: {distancias_nao_zero.max():.2f}m")
    print(f"Distância mínima entre requisições: {distancias_nao_zero.min():.2f}m")
    
    # ===== ANÁLISE OPERACIONAL E TEMPOS DE SERVIÇO =====
    s = np.array(dados['tempoServico'])
    print(f"Tempo de serviço médio: {s[1:].mean():.2f} min")  # Excluir garagem
    print(f"Tempo de reabastecimento (garagem): {s[0]:.2f} min")
    
    # ===== COMPILAÇÃO DE MÉTRICAS PARA RETORNO =====
    return {
        'nome': nome_instancia,                             # Identificador da instância
        'requisicoes': n,                                   # Dimensão do problema
        'onibus': K,                                        # Recursos disponíveis
        'max_viagens': V_max,                               # Capacidade por recurso
        'capacidade_total': K * V_max,                      # Capacidade total sistema
        'utilizacao': n / (K * V_max),                      # Taxa de utilização (0-1)
        'voos': len(voos),                                  # Operações aéreas
        'passageiros_total': passageiros_total,             # Demanda total
        'duracao_operacao': l.max() - e.min(),             # Janela operacional
        'distancia_media': distancias_nao_zero.mean(),     # Características espaciais
        'tempo_servico_medio': s[1:].mean()                 # Características temporais
    }

def visualizar_layout_aeroporto(dados: Dict[str, Any], nome_instancia: str, 
                                salvar: bool = False) -> None:
    """
    Gera visualização 2D do layout físico do aeroporto.
    
    Esta função cria um gráfico que mostra a disposição espacial de todos
    os pontos relevantes no aeroporto, incluindo garagem, portões de embarque,
    posições de aeronaves e as conexões entre pontos de coleta e entrega
    das requisições.
    
    Elementos visualizados:
    - **Garagem**: Quadrado preto (ponto de partida/retorno dos ônibus)
    - **Portões**: Círculos azuis (locais de embarque de passageiros)
    - **Aeronaves**: Triângulos vermelhos (posições das aeronaves)
    - **Conexões**: Linhas verdes (ligação coleta-entrega por requisição)
    
    Características do gráfico:
    - Escala proporcional em metros
    - Aspecto igual para preservar distâncias
    - Grid para facilitar leitura de coordenadas
    - Legenda explicativa dos símbolos
    
    Args:
        dados: Dicionário da instância contendo 'coordenadas_pontos'
               com subcampos: garagem, portoes, posicoes_aeronaves,
               pontos_coleta, pontos_entrega
        nome_instancia: Nome para título do gráfico
        salvar: Se True, salva gráfico como PNG de alta resolução
    
    Returns:
        None: Exibe gráfico na tela e opcionalmente salva arquivo
    
    Side Effects:
        - Cria figura matplotlib de 12x8 polegadas
        - Exibe gráfico interativo na tela
        - Se salvar=True, gera arquivo 'layout_aeroporto_{nome}.png'
    
    Example:
        >>> dados = carregar_instancia('dados/media.json')
        >>> visualizar_layout_aeroporto(dados, 'media', salvar=True)
        # Exibe gráfico e salva arquivo 'layout_aeroporto_media.png'
    
    Note:
        - Requer dados de coordenadas válidos na instância
        - Preserva proporções reais das distâncias
        - Útil para compreender geometria do problema
    """
    """Visualiza o layout do aeroporto com as posições dos pontos."""
    # Configuração da figura e eixo principal
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    
    # Extração das coordenadas dos pontos
    coords = dados['coordenadas_pontos']
    
    # ===== PLOTAGEM DA GARAGEM (PONTO CENTRAL) =====
    garagem = coords['garagem']
    ax.plot(garagem[0], garagem[1], 'ks', markersize=15, label='Garagem')
    
    # ===== PLOTAGEM DOS PORTÕES DE EMBARQUE =====
    portoes = coords['portoes']
    portoes_x = [p[0] for p in portoes]                     # Coordenadas X
    portoes_y = [p[1] for p in portoes]                     # Coordenadas Y
    ax.plot(portoes_x, portoes_y, 'bo', markersize=8, label='Portões de Embarque')
    
    # ===== PLOTAGEM DAS POSIÇÕES DE AERONAVES =====
    aeronaves = coords['posicoes_aeronaves']
    aeronaves_x = [p[0] for p in aeronaves]                 # Coordenadas X
    aeronaves_y = [p[1] for p in aeronaves]                 # Coordenadas Y
    ax.plot(aeronaves_x, aeronaves_y, 'r^', markersize=8, label='Posições de Aeronaves')
    
    # ===== CONEXÕES ENTRE PONTOS DE COLETA E ENTREGA =====
    coletas = coords['pontos_coleta']
    entregas = coords['pontos_entrega']
    
    # Desenhar linhas conectando cada par coleta-entrega
    for i, (coleta, entrega) in enumerate(zip(coletas, entregas)):
        # Linha verde semitransparente conectando os pontos da requisição
        ax.plot([coleta[0], entrega[0]], [coleta[1], entrega[1]], 
                'g-', alpha=0.3, linewidth=1)
    
    # ===== CONFIGURAÇÃO DOS EIXOS E APARÊNCIA =====
    ax.set_xlabel('Posição X (metros)')
    ax.set_ylabel('Posição Y (metros)')
    ax.set_title(f'Layout do Aeroporto - Instância {nome_instancia.capitalize()}')
    ax.legend()                                             # Exibir legenda
    ax.grid(True, alpha=0.3)                               # Grid semitransparente
    ax.axis('equal')                                        # Proporção 1:1
    
    # ===== FINALIZAÇÃO E SALVAMENTO =====
    plt.tight_layout()
    if salvar:
        plt.savefig(f'layout_aeroporto_{nome_instancia}.png', dpi=300, bbox_inches='tight')
    plt.show()

def visualizar_janelas_tempo(dados: Dict[str, Any], nome_instancia: str, 
                             salvar: bool = False) -> None:
    """
    Gera visualização das janelas de tempo das requisições.
    
    Esta função cria um gráfico de barras horizontais mostrando as janelas
    de tempo de todas as requisições, permitindo visualizar a distribuição
    temporal das operações e identificar períodos de pico e sobreposições.
    
    Características da visualização:
    - **Barras horizontais**: Cada requisição é uma barra
    - **Posicionamento**: Início da barra = início da janela
    - **Comprimento**: Duração da janela de tempo
    - **Dupla escala**: Minutos (principal) e horas (secundária)
    - **Grid**: Facilita leitura temporal
    
    Informações visuais:
    - Eixo Y: Número da requisição (1, 2, 3, ...)
    - Eixo X inferior: Tempo em minutos desde início
    - Eixo X superior: Tempo convertido em horas
    - Largura da barra: Flexibilidade temporal da requisição
    
    Args:
        dados: Dicionário da instância contendo 'inicioJanela' e 'fimJanela'
               (arrays com início e fim de cada janela de tempo)
        nome_instancia: Nome para título do gráfico
        salvar: Se True, salva gráfico como PNG de alta resolução
    
    Returns:
        None: Exibe gráfico na tela e opcionalmente salva arquivo
    
    Side Effects:
        - Cria figura matplotlib de 12x6 polegadas
        - Gera gráfico com dupla escala temporal
        - Se salvar=True, gera arquivo 'janelas_tempo_{nome}.png'
    
    Applications:
        - Identificar períodos de rush e baixa demanda
        - Verificar conflitos temporais potenciais
        - Analisar distribuição da carga de trabalho
        - Validar factibilidade temporal das instâncias
    
    Example:
        >>> dados = carregar_instancia('dados/rush.json')
        >>> visualizar_janelas_tempo(dados, 'rush', salvar=True)
        # Mostra picos de demanda e salva gráfico
    
    Note:
        - Janelas sobrepostas indicam possível competição por recursos
        - Janelas muito estreitas podem indicar alta rigidez temporal
        - Distribuição uniforme facilita otimização
    """
    """Visualiza as janelas de tempo das requisições."""
    # Extração dos dados temporais
    e = np.array(dados['inicioJanela'])                     # Início das janelas
    l = np.array(dados['fimJanela'])                        # Fim das janelas
    
    # Configuração da figura principal
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    
    # ===== PREPARAÇÃO DOS DADOS PARA PLOTAGEM =====
    requisicoes = range(1, len(e) + 1)                     # Números das requisições
    duracao = l - e                                         # Duração de cada janela
    
    # ===== CRIAÇÃO DO GRÁFICO DE BARRAS HORIZONTAIS =====
    bars = ax.barh(requisicoes, duracao, left=e, alpha=0.7, 
                   color='skyblue', edgecolor='darkblue')
    
    # ===== CONFIGURAÇÃO DOS EIXOS PRINCIPAIS =====
    ax.set_xlabel('Tempo (minutos)')
    ax.set_ylabel('Requisição')
    ax.set_title(f'Janelas de Tempo das Requisições - Instância {nome_instancia.capitalize()}')
    ax.grid(True, alpha=0.3, axis='x')                     # Grid apenas no eixo X
    
    # ===== ADIÇÃO DE ESCALA SECUNDÁRIA EM HORAS =====
    ax2 = ax.twiny()                                        # Eixo X secundário (superior)
    ax2.set_xlim(ax.get_xlim())                            # Mesmos limites do eixo principal
    tick_locations = ax.get_xticks()                        # Posições dos ticks do eixo principal
    ax2.set_xticks(tick_locations)                          # Aplicar mesmas posições
    ax2.set_xticklabels([f'{t/60:.1f}h' for t in tick_locations])  # Converter para horas
    ax2.set_xlabel('Tempo (horas)')
    
    # ===== FINALIZAÇÃO E SALVAMENTO =====
    plt.tight_layout()
    if salvar:
        plt.savefig(f'janelas_tempo_{nome_instancia}.png', dpi=300, bbox_inches='tight')
    plt.show()

def gerar_relatorio_comparativo(todas_analises: List[Dict[str, Any]], 
                                salvar: bool = False) -> None:
    """
    Gera relatório comparativo completo de múltiplas instâncias.
    
    Esta função cria uma análise comparativa abrangente entre diferentes
    instâncias do problema, incluindo tabelas resumo, métricas de eficiência
    e visualizações gráficas multidimensionais para facilitar a compreensão
    das diferenças entre as instâncias.
    
    Componentes do relatório:
    1. **Tabela quantitativa**: Resumo numérico de todas as métricas
    2. **Análise de eficiência**: Métricas derivadas por instância
    3. **Gráficos comparativos**: 4 visualizações simultâneas
    
    Gráficos gerados:
    - **Requisições vs Ônibus**: Dimensão do problema e recursos
    - **Passageiros totais**: Demanda absoluta por instância  
    - **Duração operacional**: Janela temporal de operação
    - **Eficiência**: Requisições por ônibus (produtividade)
    
    Métricas de eficiência calculadas:
    - Requisições por ônibus: Carga de trabalho por veículo
    - Passageiros por ônibus: Demanda por veículo
    - Utilização temporal: Percentual do dia de trabalho usado
    
    Args:
        todas_analises: Lista de dicionários retornados por analisar_instancia()
                       Cada elemento deve conter todas as métricas calculadas
        salvar: Se True, salva gráfico comparativo como PNG de alta resolução
    
    Returns:
        None: Imprime relatório e exibe gráficos na tela
    
    Side Effects:
        - Imprime tabela comparativa formatada na saída padrão
        - Calcula e exibe métricas de eficiência derivadas
        - Cria figura 2x2 com 4 subgráficos comparativos
        - Se salvar=True, gera 'relatorio_comparativo_instancias.png'
    
    Applications:
        - Comparar complexidade entre instâncias
        - Identificar instâncias mais/menos desafiadoras
        - Avaliar dimensionamento adequado de recursos
        - Benchmarking de diferentes cenários operacionais
    
    Example:
        >>> analises = []
        >>> for nome in ['pequena', 'media', 'grande']:
        >>>     dados = carregar_instancia(f'dados/{nome}.json')
        >>>     analise = analisar_instancia(dados, nome)
        >>>     analises.append(analise)
        >>> gerar_relatorio_comparativo(analises, salvar=True)
    
    Note:
        - Assume formato consistente dos dados de análise
        - Calcula automaticamente métricas de benchmarking
        - Gráficos com escalas automáticas para melhor comparação
        - Dia de trabalho assumido como 8 horas para cálculo de utilização
    """
    """Gera um relatório comparativo de todas as instâncias."""
    # Conversão para DataFrame para facilitar manipulação
    df = pd.DataFrame(todas_analises)
    
    # ===== RELATÓRIO TEXTUAL RESUMIDO =====
    print("\n" + "="*80)
    print("RELATÓRIO COMPARATIVO DAS INSTÂNCIAS")
    print("="*80)
    
    print("\nResumo Quantitativo:")
    print(df.to_string(index=False, float_format='%.2f'))
    
    # ===== CÁLCULO DE MÉTRICAS DE EFICIÊNCIA =====
    print("\nAnálise de Eficiência:")
    df['requisicoes_por_onibus'] = df['requisicoes'] / df['onibus']
    df['passageiros_por_onibus'] = df['passageiros_total'] / df['onibus']
    df['utilizacao_tempo'] = df['duracao_operacao'] / (8 * 60)  # 8h = dia trabalho
    
    # Relatório individualizado por instância
    for _, row in df.iterrows():
        print(f"\n{row['nome'].upper()}:")
        print(f"  - Requisições por ônibus: {row['requisicoes_por_onibus']:.1f}")
        print(f"  - Passageiros por ônibus: {row['passageiros_por_onibus']:.0f}")
        print(f"  - Utilização do tempo de operação: {row['utilizacao_tempo']:.1%}")
    
    # ===== CRIAÇÃO DOS GRÁFICOS COMPARATIVOS =====
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    
    # GRÁFICO 1: Requisições vs Ônibus (dimensionamento)
    ax1.bar(df['nome'], df['requisicoes'], color='lightblue', alpha=0.7)
    ax1_twin = ax1.twinx()                                  # Eixo Y secundário
    ax1_twin.plot(df['nome'], df['onibus'], 'ro-', markersize=8, linewidth=2)
    ax1.set_ylabel('Número de Requisições', color='blue')
    ax1_twin.set_ylabel('Número de Ônibus', color='red')
    ax1.set_title('Requisições vs Ônibus por Instância')
    ax1.tick_params(axis='x', rotation=45)
    
    # GRÁFICO 2: Demanda total de passageiros
    ax2.bar(df['nome'], df['passageiros_total'], color='lightgreen', alpha=0.7)
    ax2.set_ylabel('Passageiros Totais')
    ax2.set_title('Total de Passageiros por Instância')
    ax2.tick_params(axis='x', rotation=45)
    
    # GRÁFICO 3: Janela temporal de operação
    ax3.bar(df['nome'], df['duracao_operacao']/60, color='lightyellow', alpha=0.7)
    ax3.set_ylabel('Duração (horas)')
    ax3.set_title('Duração da Operação por Instância')
    ax3.tick_params(axis='x', rotation=45)
    
    # GRÁFICO 4: Eficiência operacional (produtividade)
    ax4.bar(df['nome'], df['requisicoes_por_onibus'], color='lightcoral', alpha=0.7)
    ax4.set_ylabel('Requisições por Ônibus')
    ax4.set_title('Eficiência: Requisições por Ônibus')
    ax4.tick_params(axis='x', rotation=45)
    
    # ===== FINALIZAÇÃO E SALVAMENTO =====
    plt.tight_layout()
    if salvar:
        plt.savefig('relatorio_comparativo_instancias.png', dpi=300,
                    bbox_inches='tight')
    plt.show()