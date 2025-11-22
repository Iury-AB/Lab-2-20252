from exemplo_prof.dados import Dados
from exemplo_prof.solucao import Solucao

def atendimento_requisicoes(solucao: Solucao, dados: Dados):
  # cada requisição deve ser atendida exatamente uma vez
  # comentario a mais
  for k, viagens in solucao.rota.items():
    for v, rota in viagens.items():
        if not rota or len(rota) <=1:
            continue  # Pula viagens vazias ou sem paradas intermediárias
        req_atendidas = []
        for req in rota[1:-1]:  # Ignora a garagem no início e no fim
          req_atendidas.append(req)
        if len(req_atendidas) > dados.n:
            return False
  return True

def conservacao_de_fluxo(solucao: Solucao, dados: Dados):
  # Não precisa
  return True or False

def inicio_e_fim_de_cada_viagem(solucao: Solucao, dados: Dados):
  # solucao.rota[k][v][0] == 0 and solucao.rota[k][v][-1] == 0
  for k, viagens in solucao.rota.items():
    for v, rota in viagens.items():
        if not rota or len(rota) <=1:
            continue  # Pula viagens vazias ou sem paradas intermediárias
        inicio = solucao.rota[k][v][0]
        fim = solucao.rota[k][v][-1]
        if inicio != 0 or fim != 0:
            return False
  return True

def sequencia_de_viagens(solucao: Solucao, dados: Dados):
  # os identificadores das viagens devem ser sequenciais para cada ônibus
  # nao precisa
  return True or False

def atende_janela(requisicoes: list, chegadas: list, dados: Dados):
  for index, req in enumerate(requisicoes[1:-1]): 
      inicio = dados.e[req-1]
      fim = dados.l[req-1]
      tempo_chegada = chegadas[index+1]
      if tempo_chegada < inicio or tempo_chegada > fim:
        return False
  return True

def janela_de_tempo_da_coleta(solucao: Solucao, dados: Dados):
  # o tempo de chegada de uma requisição deve estar dentro da janela de tempo desta
  for k, viagens in solucao.rota.items():
    for v, rota in viagens.items():
      if not rota or len(rota) <=1:
          continue  # Pula viagens vazias ou sem paradas intermediárias
      if not atende_janela(rota, solucao.chegada[k][v], dados):
         return False
  return True

def sequencia_temporal_das_rotas_intra(solucao: Solucao, dados: Dados):
  # solucao.chegada[k][v][i] < solucao.chegada[k][v][i+1]
  for k, viagens in solucao.rota.items():
      for v, rota in viagens.items():
          if not rota or len(rota) <=1:
              continue  # Pula viagens vazias ou sem paradas intermediárias
          for i in range(len(rota)-2): # Até o penúltimo índice
            tempo_chegada_v1 = solucao.chegada[k][v][i]
            tempo_chegada_v2 = solucao.chegada[k][v][i+1]
            if tempo_chegada_v1 >= tempo_chegada_v2:
                return False
  return True

def Sequencia_temporal_das_rotas_inter(solucao: Solucao, dados: Dados):
  # solucao.chegada[k][v][0] <= solucao.chegada[k][v-1][-1]
  for k, viagens in solucao.rota.items():
      for v, rota in viagens.items():
          if not rota or len(rota) <=1:
              continue  # Pula viagens vazias ou sem paradas intermediárias
          if solucao.chegada[k].get(v+1) is None:
              continue  # Pula se não houver viagem posterior
          tempo_fim_v1 = solucao.chegada[k][v][-1]
          tempo_inicio_v2 = solucao.chegada[k][v+1][0] if solucao.chegada[k][v+1] else []
          if tempo_inicio_v2:
            if tempo_fim_v1 > tempo_inicio_v2:
                return False
  return True

def atende_tempo_maximo(chegadas: list, dados:Dados):
  tempo_fim_v = chegadas[-1]
  tempo_inicio_v = chegadas[0]
  duracao_v = tempo_fim_v - tempo_inicio_v
  if duracao_v > dados.Tmax:
      return False
  return True

def limite_de_tempo_por_viagem(solucao: Solucao, dados: Dados) -> bool:
  # solucao.chegada[k][v][-1] - solucao.chegada[k][v][0] <= dados.Tmax
  for k, viagens in solucao.rota.items():
      for v, rota in viagens.items():
          if not rota or len(rota) <=1:
            continue  # Pula viagens vazias ou sem paradas intermediárias
          if not atende_tempo_maximo(rota, dados):
            return False
  return True

def eh_factivel(solucao: Solucao, dados: Dados) -> bool:
   factivel = True
   if not(atendimento_requisicoes(solucao, dados)):
      print("Restrição 'atendimento_requisicoes' não atendida.")
      factivel = False
   if not(inicio_e_fim_de_cada_viagem(solucao, dados)):
      print("Restricao 'inicio_e_fim_de_cada_viagem' não atendida.")
      factivel = False
   if not(janela_de_tempo_da_coleta(solucao, dados)):
      print("Restricao 'janela_de_tempo_da_coleta' não atendida.")
      factivel = False
   if not(sequencia_temporal_das_rotas_intra(solucao, dados)):
      print("Restricao 'sequencia_temporal_das_rotas_intra' não atendida.")
      factivel = False
   if not(Sequencia_temporal_das_rotas_inter(solucao, dados)):
      print("Restricao 'Sequencia_temporal_das_rotas_inter' não atendida.")
      factivel = False
   if not(limite_de_tempo_por_viagem(solucao, dados)):
      print("Restricao 'limite_de_tempo_por_viagem' não atendida.")
      factivel = False
   return factivel
