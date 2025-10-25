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
  for k, viagens in solucao.rota.items():
      for v, rota in viagens.items():
          if not rota or len(rota) <=1:
              continue  # Pula viagens vazias ou sem paradas intermediárias
          for i in range(len(rota)-2): # Até o penúltimo índice
            tempo_chegada_v1 = solucao.chegada[k][v][i]
            tempo_chegada_v2 = solucao.chegada[k][v+1][i+1]
            if tempo_chegada_v1 >= tempo_chegada_v2:
                return False
  return True

def Sequencia_temporal_das_rotas_inter(solucao: Solucao, dados: Dados):
  # solucao.chegada[k][v][0] <= solucao.chegada[k][v-1][-1]
  for k, viagens in solucao.rota.items():
      for v, rota in viagens.items():
          if not rota or len(rota) <=1:
              continue  # Pula viagens vazias ou sem paradas intermediárias
          tempo_fim_v1 = solucao.chegada[k][v][-1]
          tempo_inicio_v2 = solucao.chegada[k][v+1][0]
          if tempo_fim_v1 > tempo_inicio_v2:
              return False
  return True

def limite_de_tempo_por_viagem(solucao: Solucao, dados: Dados) -> bool:
  # solucao.chegada[k][v][-1] <= dados.Tmax
  for k, viagens in solucao.rota.items():
      for v, rota in viagens.items():
          if not rota or len(rota) <=1:
              continue  # Pula viagens vazias ou sem paradas intermediárias
          tempo_fim_v = solucao.chegada[k][v][-1]
          if tempo_fim_v > dados.Tmax:
              return False
  return True

