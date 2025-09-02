# Conjunto de Dados - Problema de Embarque Remoto de Aeroporto

## Visão Geral

Este conjunto de dados representa instâncias realísticas do problema de otimização do serviço de embarque remoto de um aeroporto. O problema é modelado como um **Problema de Roteamento de Veículos com Coleta e Entrega Acopladas (Dial-a-Ride Problem - DARP)** com múltiplas viagens, janelas de tempo e limitações de distância.

## Descrição do Problema

### Contexto
- **Cenário**: Aeroporto com operações de embarque e desembarque remotos
- **Veículos**: Ônibus idênticos com capacidade de 50 passageiros
- **Operação**: Transporte de passageiros entre portões de embarque e aeronaves
- **Restrições**: Janelas de tempo dos voos, capacidade dos ônibus, autonomia limitada

### Características Principais
1. **Requisições Acopladas**: Cada requisição consiste em coleta + entrega obrigatórias
2. **Múltiplas Viagens**: Ônibus podem fazer várias viagens retornando à garagem para reabastecimento
3. **Janelas de Tempo**: Cada requisição tem horário específico baseado nos voos
4. **Limite de Distância**: Autonomia máxima por viagem antes do reabastecimento

## Instâncias Geradas

### 1. Instância Pequena (Teste)
- **Voos**: 5
- **Requisições**: 19
- **Ônibus**: 3
- **Passageiros**: 839
- **Duração**: 3h 52min
- **Uso**: Testes rápidos e desenvolvimento

### 2. Instância Média (Realística)
- **Voos**: 15
- **Requisições**: 63
- **Ônibus**: 6
- **Passageiros**: 2.813
- **Duração**: 8h 8min
- **Uso**: Cenário típico de operação diária

### 3. Instância Grande (Pico de Operação)
- **Voos**: 30
- **Requisições**: 135
- **Ônibus**: 10
- **Passageiros**: 6.005
- **Duração**: 12h 11min
- **Uso**: Dias de alta demanda

### 4. Instância Rush (Alta Intensidade)
- **Voos**: 20
- **Requisições**: 85
- **Ônibus**: 8
- **Passageiros**: 3.738
- **Duração**: 6h 7min
- **Uso**: Picos concentrados de operação

## Estrutura dos Dados

### Formato dos Arquivos
- **Tipo**: JSON
- **Codificação**: UTF-8
- **Nomenclatura**: `instancia_aeroporto_[tamanho].json`

### Campos Principais

#### Metadados
```json
{
  "metadados": {
    "descricao": "Instância realística de embarque remoto de aeroporto",
    "data_geracao": "2025-09-02T...",
    "n_voos": 15,
    "capacidade_onibus": 50,
    "duracao_operacao_horas": 8,
    "seed": 42
  }
}
```

#### Parâmetros do Problema
- `numeroRequisicoes` (n): Número total de requisições
- `numeroOnibus` (K): Número de ônibus disponíveis
- `distanciaMaxima` (Dmax): Distância máxima por viagem (metros)

#### Matrizes de Distância
- `distanciaRequisicoes` (D): Matriz (n+1) × (n+1) de distâncias entre requisições
- `distanciaPontos` (d): Matriz de distâncias entre todos os pontos físicos
- `custo` (c): Matriz de custos (igual à distância)

#### Tempos
- `tempoServico` (s): Tempo de serviço para cada requisição (minutos)
- `tempoRequisicoes` (T): Matriz de tempos de viagem entre requisições
- `tempoPontos` (t): Matriz de tempos entre pontos físicos

#### Janelas de Tempo
- `inicioJanela` (e): Início da janela de tempo para cada requisição
- `fimJanela` (l): Fim da janela de tempo para cada requisição

#### Detalhes dos Voos
```json
{
  "detalhes_voos": [
    {
      "id": 1,
      "tipo": "embarque|desembarque",
      "n_passageiros": 180,
      "n_requisicoes": 4,
      "horario_base": 45
    }
  ]
}
```

#### Coordenadas Geográficas
```json
{
  "coordenadas_pontos": {
    "garagem": [0, 0],
    "pontos_coleta": [[x1, y1], ...],
    "pontos_entrega": [[x2, y2], ...],
    "portoes": [[x3, y3], ...],
    "posicoes_aeronaves": [[x4, y4], ...]
  }
}
```

## Características Realísticas

### Layout do Aeroporto
- **Garagem**: Posição central (0, 0)
- **Portões**: Lado oeste (-800m a -200m)
- **Aeronaves**: Lado leste (500m a 1500m)
- **Distâncias**: Baseadas em aeroportos reais

### Voos
- **Passageiros**: 80-300 por voo (distribuição realística)
- **Tipos**: Embarque e desembarque balanceados
- **Horários**: Distribuídos ao longo do período de operação

### Operação
- **Velocidade**: 30 km/h (500 m/min)
- **Tempo de Serviço**: 3-8 minutos por requisição
- **Reabastecimento**: 10 minutos na garagem
- **Capacidade**: 50 passageiros por ônibus

### Janelas de Tempo
- **Coordenação**: Baseadas nos horários dos voos
- **Flexibilidade**: 15 minutos por requisição
- **Sequenciamento**: Requisições do mesmo voo são sequenciais

## Métricas de Análise

### Eficiência Operacional
- **Requisições por Ônibus**: 6,3 - 13,5
- **Passageiros por Ônibus**: 280 - 600
- **Utilização Temporal**: 48% - 152%

### Complexidade
- **Densidade**: Requisições por hora de operação
- **Dispersão**: Variação nas distâncias
- **Coordenação**: Sincronização de janelas de tempo

## Uso dos Dados

### Algoritmos Testáveis
1. **Exatos**: Branch-and-bound, programação linear inteira
2. **Metaheurísticas**: Algoritmos genéticos, simulated annealing
3. **Heurísticas**: Inserção, roteamento em duas fases

### Métricas de Avaliação
- **Função Objetivo**: Minimizar distância total percorrida
- **Viabilidade**: Respeitar janelas de tempo e capacidades
- **Eficiência**: Utilização dos recursos disponíveis

### Casos de Uso
- **Pesquisa**: Desenvolvimento de novos algoritmos
- **Benchmarking**: Comparação de métodos
- **Validação**: Teste de implementações
- **Ensino**: Exemplos didáticos de otimização

## Arquivos Complementares

### Scripts de Geração
- `gerar_instancia_realistica.py`: Gerador principal
- `analisar_instancias.py`: Análise e visualização

### Visualizações
- `layout_aeroporto_media.png`: Layout físico do aeroporto
- `janelas_tempo_media.png`: Distribuição temporal
- `relatorio_comparativo_instancias.png`: Análise comparativa

### Documentação
- `README_instancias.md`: Este arquivo
- `formulacao.tex`: Modelo matemático detalhado

## Validação

### Consistência dos Dados
- ✅ Matrizes de distância simétricas
- ✅ Janelas de tempo não sobrepostas para mesmo voo
- ✅ Capacidades respeitadas
- ✅ Coordenadas geográficas válidas

### Realismo
- ✅ Distâncias compatíveis com aeroportos reais
- ✅ Tempos de operação realísticos
- ✅ Distribuição de voos balanceada
- ✅ Parâmetros operacionais validados

## Exemplo de Uso

```python
import json
import numpy as np

# Carregar instância
with open('instancia_aeroporto_media.json', 'r') as f:
    dados = json.load(f)

# Extrair parâmetros
n = dados['numeroRequisicoes']
K = dados['numeroOnibus']
D = np.array(dados['distanciaRequisicoes'])
e = np.array(dados['inicioJanela'])
l = np.array(dados['fimJanela'])

# Usar nos algoritmos de otimização
# ... implementação do algoritmo ...
```

## Referências

- Cordeau, J.-F., & Laporte, G. (2007). The dial-a-ride problem: models and algorithms.
- Cattaruzza, D., Absi, N., & Feillet, D. (2016). The multi-trip vehicle routing problem with time windows.
- Parragh, S. N., Doerner, K. F., & Hartl, R. F. (2008). A survey on pickup and delivery problems.

---

**Gerado em**: 2 de setembro de 2025  
**Versão**: 1.0  
**Autor**: André Costa Batista  
**Contato**: [seu-email@exemplo.com]
