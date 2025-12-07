import MACS
from dados import Dados, carrega_dados_json
from solucao import Solucao
from matplotlib import pyplot as plt


def resolva(dados: Dados , numero_avaliacoes: int) -> Solucao:
  """
  Executa o algoritmo de otimizacao.

  Parametros:
  -----------
    dados : Dados
    Objeto com os dados da instancia

    numero_avaliacoes : int
    Numero maximo de avaliacoes permitidas

  Retorna:
  --------
    Solucao
    Objeto com rotas , tempos e funcao objetivo
  """
  solucao_incial = MACS.Constroi_solucao_inicial(dados)
  macs = MACS.MACS(dados, solucao_incial)
  solucao_otima = macs.otimizar(n_formigas=50, max_avaliacoes=numero_avaliacoes, 
                                alpha1=0.5,beta1=0,
                                alpha2=0.8,beta2=0.7,rho=0.6)
  return solucao_otima


instancia = carrega_dados_json("dados/pequena.json")
solucao, convergencia, avaliacoes = resolva(instancia, 2100)
print(solucao)
print(solucao.fx)

plt.plot(avaliacoes, convergencia)
plt.xlabel('Avaliações de fx')
plt.ylabel('Valor de f(x)')
plt.title('Gráfico de Convergência')
plt.grid(True)
plt.show()

