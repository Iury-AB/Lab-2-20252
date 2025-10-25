import json
import random

with open("media.json", "r") as f:
    dados = json.load(f)

n = dados["numeroRequisicoes"]
m = dados["numeroOnibus"]
r_max = dados["numeroMaximoViagens"]
capacidade_onibus = dados.get("capacidade_onibus", 9999)  # ajuste se necessário
custo = dados["custo"]
tempo_servico = dados["tempoServico"]
tempo_requisicoes = dados["tempoRequisicoes"]
inicio_janela = dados["inicioJanela"]
fim_janela = dados["fimJanela"]

NUM_TESTES = 1000

motivos_totais = {"capacidade": 0, "janela": 0, "tempo_viagem": 0, "outros": 0}
total_viaveis = 0
total_inviaveis = 0

def validar_solucao(solucao):
    atendidas = set()
    for k in solucao["onibus"]:
        for v in solucao["onibus"][k]:
            rota = solucao["onibus"][k][v]["rota"]
            for req in rota:
                if req != 0:
                    atendidas.add(req)
    return len(atendidas) == n

def restricoes_atendidas(solucao, dados):
    tempo_max = dados["tempoMaximoViagem"]
    tempo_servico = dados["tempoServico"]
    tempo_requisicoes = dados["tempoRequisicoes"]
    inicio_janela = dados["inicioJanela"]
    fim_janela = dados["fimJanela"]

    atendidas = set()
    for k in solucao["onibus"]:
        for v in solucao["onibus"][k]:
            rota = solucao["onibus"][k][v]["rota"]
            tempo = 0
            viagem = []
            for i in range(len(rota)):
                ponto = rota[i]
                if ponto == 0:
                    # Nova viagem
                    if viagem:
                        if tempo > tempo_max:
                            return False
                        viagem = []
                        tempo = 0
                    continue
                ultimo = rota[i-1] if i > 0 else 0
                deslocamento = tempo_requisicoes[ultimo][ponto]
                tempo += deslocamento
                # Espera pela janela
                if tempo < inicio_janela[ponto-1]:
                    tempo = inicio_janela[ponto-1]
                # Verifica janela
                if tempo > fim_janela[ponto-1]:
                    return False
                tempo += tempo_servico[ponto]
                viagem.append(ponto)
                if ponto in atendidas:
                    return False
                atendidas.add(ponto)
            # Checa última viagem
            if viagem and tempo > tempo_max:
                return False
    # Checa se todas as requisições foram atendidas
    n = dados["numeroRequisicoes"]
    if len(atendidas) != n:
        return False
    return True

def construir_solucao_prioritaria():
    motivos = {"capacidade": 0, "janela": 0, "tempo_viagem": 0, "outros": 0}
    solucao = {"onibus": {}}
    requisicoes_restantes = set(range(1, n+1))
    for k in range(m):
        solucao["onibus"][str(k)] = {}
        rota = [0]
        arcos = []
        chegada = []
        tempo_atual = tempo_servico[0]
        capacidade = 0
        while requisicoes_restantes:
            i = rota[-1]
            candidatos = list(requisicoes_restantes)
            # Prioriza requisições com menor fim de janela
            candidatos.sort(key=lambda j: fim_janela[j-1])
            escolhido = None
            for j in candidatos:
                deslocamento = tempo_requisicoes[i][j]
                chegada_estimada = tempo_atual + deslocamento
                inicio_servico = max(chegada_estimada, inicio_janela[j-1])
                fim_servico = inicio_servico + tempo_servico[j]
                if capacidade + 1 > capacidade_onibus:
                    motivos["capacidade"] += 1
                    continue
                if inicio_servico > fim_janela[j-1]:
                    motivos["janela"] += 1
                    continue
                escolhido = j
                break
            if escolhido is None:
                break
            deslocamento = tempo_requisicoes[rota[-1]][escolhido]
            chegada_estimada = tempo_atual + deslocamento
            inicio_servico = max(chegada_estimada, inicio_janela[escolhido-1])
            tempo_atual = inicio_servico + tempo_servico[escolhido]
            rota.append(escolhido)
            arcos.append([rota[-2], escolhido])
            chegada.append(inicio_servico)
            requisicoes_restantes.remove(escolhido)
            capacidade += 1
            if capacidade >= r_max:
                break
        if len(rota) > 1:
            solucao["onibus"][str(k)]["viagem_0"] = {
                "rota": rota,
                "arcos": arcos,
                "chegada": chegada
            }
    if restricoes_atendidas(solucao):
        return True, motivos
    else:
        return False, motivos

for _ in range(NUM_TESTES):
    viavel, motivos = construir_solucao_prioritaria()
    if viavel:
        total_viaveis += 1
    else:
        total_inviaveis += 1
        for k in motivos:
            motivos_totais[k] += motivos[k]

print(f"Soluções viáveis: {total_viaveis}")
print(f"Soluções inviáveis: {total_inviaveis}")
print("Motivos de inviabilidade (acumulado):")
for motivo, qtd in motivos_totais.items():
    print(f"  {motivo}: {qtd}")