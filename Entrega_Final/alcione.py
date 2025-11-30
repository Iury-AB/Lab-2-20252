import MACS
from dados import Dados, carrega_dados_json
from solucao import Solucao


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
  solucao_otima = macs.otimizar(n_formigas=20, max_avaliacoes=numero_avaliacoes, 
                                alpha1=0.2,beta1=0.2,
                                alpha2=2,beta2=0.5,rho=0.6)
  return solucao_otima
