import matplotlib.pyplot as plt
from .maco_otimizado_v2 import resolva
from exemplo_prof.dados import carrega_dados_json
# Carrega os dados do arquivo JSON
dados = carrega_dados_json("dados/pequena.json")
n = dados.n
K = dados.K
r = dados.r

# Lista para armazenar os resultados de fx
resultados_fx = []

# Executa resolva 30 vezes
for i in range(30):
    solucao = resolva(dados, 10 * n * K * r)
    resultados_fx.append(solucao.fx)

# Gera o gráfico
plt.figure(figsize=(10, 6))
plt.plot(resultados_fx, marker='o', linestyle='-', color='blue')
plt.title('Distribuição dos valores de fx em 30 execuções')
plt.xlabel('Execução')
plt.ylabel('Valor de fx')
plt.grid(True)
plt.tight_layout()
plt.show()
