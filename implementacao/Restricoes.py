from exemplo_prof.dados import Dados
from exemplo_prof.solucao import Solucao

def atendimento_requisicoes(solucao: Solucao, dados: Dados):
  # cada requisição deve ser atendida exatamente uma vez
  # comentario a mais
  return True or False

def conservacao_de_fluxo(solucao: Solucao, dados: Dados):
  # Não precisa
  return True or False

def inicio_e_fim_de_cada_viagem(solucao: Solucao, dados: Dados):
  # solucao.rota[k][v][0] == 0 and solucao.rota[k][v][-1] == 0
  return True or False

def sequencia_de_viagens(solucao: Solucao, dados: Dados):
  # os identificadores das viagens devem ser sequenciais para cada ônibus
  return True or False

def janela_de_tempo_da_coleta(solucao: Solucao, dados: Dados):
  # o tempo de chegada de uma requisição deve estar dentro da janela de tempo desta
  return True or False

def sequencia_temporal_das_rotas_intra(solucao: Solucao, dados: Dados):
  # solucao.chegada[k][v][i] < solucao.chegada[k][v][i+1]
  return True or False

def Sequencia_temporal_das_rotas_inter(solucao: Solucao, dados: Dados):
  # solucao.chegada[k][v][0] <= solucao.chegada[k][v-1][-1]
  return True or False


def limite_de_tempo_por_viagem(solucao: Solucao, dados: Dados):
  # solucao.chegada[k][v][-1] <= dados.Tmax
  return True or False

