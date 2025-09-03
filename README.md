# ELE634 - Problema de Embarque Remoto em Aeroportos

## 📋 Descrição do Projeto

Este repositório contém a implementação completa de algoritmos de otimização para resolver o **Problema de Embarque Remoto em Aeroportos**. O problema consiste em otimizar rotas de ônibus que transportam passageiros entre portões de embarque e aeronaves estacionadas em posições remotas, minimizando custos operacionais enquanto respeitam janelas de tempo e restrições operacionais.

## 🎯 Objetivo

Desenvolver e comparar diferentes abordagens algorítmicas para resolver um problema real de roteamento de veículos em aeroportos:

- **Método Exato**: Programação Linear Inteira Mista (MILP) usando Gurobi
- **Metaheurísticas**: GRASP e VNS (Variable Neighborhood Search)
- **Análise Comparativa**: Avaliação de desempenho entre as diferentes abordagens

## 🏗️ Estrutura do Repositório

```
📂 ele634_202502/
├── 📄 README.md                   # Este arquivo
├── 📄 requirements.txt            # Dependências Python
├── 📄 dados.py                    # Estruturas de dados do problema
├── 📄 exato.py                    # Algoritmo exato (MILP)
├── 📄 solucao.py                  # Classe para representar soluções
├── 📄 utils.py                    # Utilitários e visualizações
├── 📄 gera_instancia.py           # Gerador de instâncias realísticas
├── 📓 analise_instancia.ipynb     # Análise exploratória das instâncias
├── 📓 resolucao_exata.ipynb       # Demonstração do método exato
├── 📂 dados/                      # Instâncias do problema
│   ├── pequena.json               # Instância pequena (5 voos, 19 requisições)
│   ├── media.json                 # Instância média (10 voos)
│   ├── grande.json                # Instância grande (20 voos)
│   └── rush.json                  # Instância horário de pico
├── 📂 metaheuristicas/            # Algoritmos metaheurísticos
│   ├── grasp.ipynb                # Implementação GRASP
│   └── vns.ipynb                  # Implementação VNS
├── 📂 documentacao/               # Documentação técnica
│   ├── formulacao.tex             # Formulação matemática (LaTeX)
│   └── formulacao.pdf             # Formulação matemática (PDF)
├── 📂 apresentacao/               # Material de apresentação
│   ├── apresentacao.tex           # Slides (LaTeX)
│   └── apresentacao.pdf           # Slides (PDF)
└── 📂 env/                        # Ambiente virtual Python
```

## 🔧 Instalação e Configuração

### Pré-requisitos

- Python 3.8 ou superior
- Gurobi Optimizer (licença acadêmica disponível)
- Jupyter Notebook/Lab

### Instalação

1. **Clone o repositório:**
```bash
git clone https://github.com/andre-batista/ele634_202502.git
cd ele634_202502
```

2. **Crie e ative um ambiente virtual:**
```bash
python -m venv env
# Windows
env\Scripts\activate
# Linux/Mac
source env/bin/activate
```

3. **Instale as dependências:**
```bash
pip install -r requirements.txt
```

4. **Configure o Gurobi:**
   - Obtenha uma licença acadêmica em: https://www.gurobi.com/academia/
   - Instale e configure conforme as instruções oficiais

## 🚀 Como Usar

### 1. Análise de Instâncias
Explore as características das instâncias disponíveis:
```bash
jupyter notebook analise_instancia.ipynb
```

### 2. Resolução Exata
Execute o algoritmo MILP para obter soluções ótimas:
```bash
python exato.py
# ou
jupyter notebook resolucao_exata.ipynb
```

### 3. Metaheurísticas
Compare com soluções heurísticas:
```bash
jupyter notebook metaheuristicas/grasp.ipynb
jupyter notebook metaheuristicas/vns.ipynb
```

### 4. Gerar Novas Instâncias
Crie instâncias personalizadas:
```python
from gera_instancia import gerar_instancia_aeroporto

# Gerar instância com 15 voos e 4 ônibus
instancia = gerar_instancia_aeroporto(
    n_voos=15, 
    n_onibus=4, 
    duracao_operacao_horas=6
)
```

## 📊 Características do Problema

### Parâmetros Principais
- **Requisições (n)**: Viagens de ônibus necessárias para transportar passageiros
- **Ônibus (K)**: Frota disponível para atender as requisições
- **Viagens (r)**: Número máximo de viagens por ônibus
- **Janelas de Tempo**: Horários específicos para atender cada requisição
- **Distâncias**: Matriz de distâncias entre todos os pontos (garagem, portões, aeronaves)
- **Autonomia**: Distância máxima que um ônibus pode percorrer por viagem

### Restrições
- ✅ Toda requisição deve ser atendida exatamente uma vez
- ✅ Respeitar janelas de tempo das requisições
- ✅ Não exceder capacidade de viagens por ônibus
- ✅ Respeitar limite de autonomia por viagem
- ✅ Conservação de fluxo (ônibus devem retornar à garagem)

### Função Objetivo
Minimizar o custo total de transporte, considerando:
- Custos de deslocamento entre pontos
- Penalizações por violações de restrições
- Eficiência operacional da frota

## 📈 Resultados e Análises

### Instâncias Disponíveis

| Instância | Voos | Requisições | Ônibus | Duração | Complexidade |
|-----------|------|-------------|--------|---------|--------------|
| Pequena   | 5    | 19          | 3      | 4h      | Baixa        |
| Média     | 10   | ~40         | 5      | 6h      | Moderada     |
| Grande    | 20   | ~80         | 8      | 8h      | Alta         |
| Rush      | 15   | ~60         | 6      | 4h      | Muito Alta   |

### Métricas de Desempenho
- **Tempo de Execução**: Comparação entre métodos
- **Qualidade da Solução**: Gap de otimalidade
- **Eficiência Operacional**: Utilização da frota
- **Robustez**: Sensibilidade a parâmetros

## 🔬 Metodologia

### 1. Formulação Matemática
O problema é modelado como um **Vehicle Routing Problem with Time Windows (VRPTW)** com características específicas:

**Variáveis de Decisão:**
- `x[i,j,v,k]`: Binária, 1 se o ônibus k na viagem v vai da requisição i para j
- `y[v,k]`: Binária, 1 se o ônibus k realiza a viagem v
- `B[i,v,k]`: Tempo de chegada na requisição i pelo ônibus k na viagem v

**Função Objetivo:**
```
min Σ Σ Σ Σ c[i,j] * x[i,j,v,k]
    i j v k
```

### 2. Métodos de Resolução

#### Método Exato (MILP)
- **Solver**: Gurobi Optimizer
- **Vantagens**: Solução ótima garantida
- **Limitações**: Tempo exponencial para instâncias grandes

#### GRASP (Greedy Randomized Adaptive Search)
- **Fase Construtiva**: Construção gulosa randomizada
- **Busca Local**: Melhoramento iterativo
- **Vantagens**: Boa qualidade em tempo razoável

#### VNS (Variable Neighborhood Search)
- **Múltiplas Vizinhanças**: Diferentes operadores de movimento
- **Busca Sistemática**: Exploração estruturada do espaço
- **Vantagens**: Escape de ótimos locais

## 📚 Documentação Técnica

- **Formulação Matemática**: `documentacao/formulacao.pdf`
- **Apresentação**: `apresentacao/apresentacao.pdf`
- **Código Comentado**: Todos os módulos possuem documentação detalhada
- **Notebooks Explicativos**: Análises passo-a-passo com visualizações

## 👥 Contribuições

Este projeto foi desenvolvido como parte da disciplina ELE634 - Otimização. Contribuições são bem-vindas através de:

1. Fork do repositório
2. Criação de branch para nova funcionalidade
3. Commit das alterações
4. Pull request com descrição detalhada

## 📄 Licença

Este projeto é desenvolvido para fins acadêmicos. O uso do código é livre para pesquisa e educação.

## 📞 Contato

**Autor**: André Batista  
**Disciplina**: ELE634 - Otimização  
**Instituição**: [Sua Instituição]  
**Data**: Setembro 2025

---

## 🔍 Links Úteis

- [Gurobi Academic License](https://www.gurobi.com/academia/)
- [Jupyter Documentation](https://jupyter.org/documentation)
- [Numpy Documentation](https://numpy.org/doc/)
- [Matplotlib Gallery](https://matplotlib.org/stable/gallery/index.html)

---

**Nota**: Este README é um documento vivo e será atualizado conforme o projeto evolui. Para dúvidas específicas sobre implementação, consulte os notebooks explicativos ou a documentação inline do código.
