# Problema de Otimização do Serviço de Embarque Remoto de Aeroporto

Este projeto implementa a solução do Problema de Coleta e Entrega com Janelas de Tempo (PDPTW) para otimização do serviço de embarque remoto em aeroportos, utilizando o solver Gurobi.

## Descrição do Problema

O problema consiste em otimizar as rotas de ônibus que transportam passageiros entre portões de embarque e aviões em um aeroporto. Cada voo é dividido em requisições baseadas na capacidade dos ônibus, e cada requisição possui:

- Ponto de coleta (portão de embarque)
- Ponto de entrega (avião)
- Janela de tempo específica
- Restrições de autonomia dos ônibus

## Arquivos do Projeto

- `aeroporto_gurobi.py`: Implementação completa do modelo matemático
- `exemplo_simples.py`: Exemplo simplificado para demonstração
- `requirements.txt`: Dependências necessárias
- `formulacao.tex`: Documentação matemática do modelo
- `apresentacao.tex`: Apresentação em Beamer

## Instalação

### 1. Instalar o Gurobi

Primeiro, você precisa instalar o Gurobi Optimizer:

```bash
# Baixar do site oficial: https://www.gurobi.com/downloads/
# Ou usar conda:
conda install -c gurobi gurobi

# Ou pip (requer licença):
pip install gurobipy
```

### 2. Licença do Gurobi

- **Licença Acadêmica**: Gratuita para uso acadêmico
- **Licença Comercial**: Necessária para uso comercial
- **Licença de Teste**: 30 dias gratuitos

Para obter uma licença acadêmica:
1. Registre-se em https://www.gurobi.com/academia/
2. Baixe e instale a licença seguindo as instruções

### 3. Instalar Dependências Python

```bash
pip install -r requirements.txt
```

## Uso

### Exemplo Simples

Execute o exemplo básico com 3 requisições e 2 ônibus:

```bash
python exemplo_simples.py
```

### Implementação Completa

Execute o modelo completo:

```bash
python aeroporto_gurobi.py
```

## Parâmetros do Modelo

### Entrada
- `n_requisicoes`: Número de requisições
- `n_onibus`: Número de ônibus disponíveis
- `D_max`: Distância máxima de autonomia
- `d[u,v]`: Matriz de distâncias entre pontos
- `e[u], l[u]`: Janelas de tempo das requisições

### Saída
- Rotas otimizadas para cada ônibus
- Custo total (distância percorrida)
- Tempos de início das requisições
- Estatísticas de utilização

## Modelo Matemático

### Variáveis de Decisão
- `x[u,v,k]`: Binária - ônibus k vai de u para v
- `B[u,k]`: Tempo de início do serviço na coleta u
- `q[u,k]`: Distância acumulada pelo ônibus k
- `p[u,k]`: Variável auxiliar para eliminação de sub-rotas

### Função Objetivo
Minimizar: Σ c[u,v] * x[u,v,k] (distância total percorrida)

### Principais Restrições
1. Cada requisição atendida exatamente uma vez
2. Conservação de fluxo
3. Rastreamento da distância acumulada
4. Restrições de autonomia
5. Janelas de tempo
6. Eliminação de sub-rotas (MTZ)

## Exemplo de Execução

```python
from aeroporto_gurobi import AeroportoEmbarcador

# Criar problema com 6 requisições e 3 ônibus
problema = AeroportoEmbarcador(n_requisicoes=6, n_onibus=3)

# Gerar dados de exemplo
problema.gerar_dados_exemplo()

# Criar e resolver modelo
problema.criar_modelo()
problema.resolver(tempo_limite=300)

# Salvar resultados
problema.salvar_resultados("resultados.csv")
```

## Configurações do Solver

- **Tempo limite**: 300 segundos (padrão)
- **Gap de otimalidade**: 1%
- **Método**: Branch-and-bound com cortes automáticos

## Resultados

O programa gera:

1. **Saída no console**: Rotas, custos, estatísticas
2. **Arquivo CSV**: Resultados detalhados para análise
3. **Métricas de performance**: Tempo de solução, gap de otimalidade

### Exemplo de Saída

```
RESULTADOS DA OTIMIZAÇÃO
=======================================
Valor da função objetivo: 145.67
Gap de otimalidade: 0.50%

ROTAS DOS ÔNIBUS:
Ônibus 1: 0 -> 1 -> 3 -> 0
  Distância total: 67.34
  Tempos de início: R1:5.0, R3:18.5

Ônibus 2: 0 -> 2 -> 4 -> 0
  Distância total: 78.33
  Tempos de início: R2:10.0, R4:25.0

ESTATÍSTICAS GERAIS:
Distância total percorrida: 145.67
Ônibus utilizados: 2/3
Taxa de utilização: 66.7%
```

## Limitações e Extensões

### Limitações Atuais
- Não considera diferentes tipos de ônibus
- Janelas de tempo fixas
- Capacidade uniforme dos ônibus

### Extensões Possíveis
- Ônibus com capacidades diferentes
- Múltiplos depósitos
- Restrições de manutenção
- Otimização multi-objetivo
- Incertezas nos tempos de viagem

## Troubleshooting

### Problema: "gurobipy not found"
**Solução**: Instale o Gurobi e configure a licença

### Problema: "Model is infeasible"
**Soluções**:
- Verificar se D_max é suficiente
- Relaxar janelas de tempo
- Aumentar número de ônibus

### Problema: Tempo de execução muito alto
**Soluções**:
- Reduzir número de requisições
- Ajustar parâmetros do solver
- Usar heurísticas iniciais

## Referências

1. Formulação matemática completa em `formulacao.tex`
2. Apresentação do problema em `apresentacao.tex`
3. Documentação do Gurobi: https://www.gurobi.com/documentation/

## Autor

André Costa Batista
ELE634 - Laboratório de Sistemas II
Universidade Federal de Minas Gerais
