#!/usr/bin/env python3
"""
Gerador de Instâncias Realísticas para Otimização do Serviço de Embarque 
Remoto de Aeroporto

Este script gera conjuntos de dados representativos para o problema de
roteamento de ônibus em aeroportos, considerando características 
realísticas como:
- Distâncias baseadas em layout real de aeroporto
- Janelas de tempo coordenadas com horários de voos
- Múltiplas requisições por voo baseadas na capacidade dos ônibus
- Tempos de serviço realísticos
"""

import numpy as np
import json
import random
from datetime import datetime, timedelta
import math

def gerar_instancia_aeroporto(n_voos=10, capacidade_onibus=55, n_onibus=5, 
                              duracao_operacao_horas=8, seed=42, n_portoes=5,
                              n_posicoes_aeronaves=15, preparo_onibus=10):
    """
    Gera uma instância realística do problema de embarque remoto de 
    aeroporto.
    
    Parâmetros:
    - n_voos: número de voos (embarques + desembarques)
    - capacidade_onibus: capacidade de passageiros por ônibus
    - n_onibus: número de ônibus disponíveis
    - duracao_operacao_horas: duração total da operação em horas
    - seed: semente para reprodutibilidade
    - n_portoes: número de portões de embarque
    - n_posicoes_aeronaves: número de posições de aeronaves
    - preparo_onibus: tempo (min) para o ônibus se preparar e iniciar 
      uma viagem
    """
    
    random.seed(seed)
    np.random.seed(seed)
    
    print(f"Gerando instância com {n_voos} voos, {n_onibus} ônibus...")
    
    # 1. Gerar voos com duas fases: desembarque seguido de embarque
    voos = []
    total_requisicoes = 0
    
    for i in range(n_voos):
        # Horário de aterrisagem (distribuído ao longo do dia)
        horario_aterrisagem = (
            + i * (duracao_operacao_horas * 60) // n_voos
        ) # em minutos

        # Garantir que o horário de aterrisagem permita o preparo do 
        # ônibus
        if horario_aterrisagem < preparo_onibus * 1.2:
            horario_aterrisagem = preparo_onibus * 1.2
        
        # Passageiros que desembarcam (chegando)
        n_passageiros_desembarque = random.randint(80, 300)
        n_requisicoes_desembarque = math.ceil(n_passageiros_desembarque 
                                              / capacidade_onibus)
        
        # Passageiros que embarcam (partindo) - pode ser diferente
        n_passageiros_embarque = random.randint(80, 300)
        n_requisicoes_embarque = math.ceil(n_passageiros_embarque 
                                           / capacidade_onibus)
        
        # Tempo total para desembarque completo (desde aterrisagem até último 
        # passageiro sair)
        tempo_total_desembarque = 25 # minutos fixo para desembarque
        
        # Tempo de turnaround: preparação da aeronave entre desembarque e 
        # embarque
        # Inclui: limpeza, abastecimento, checagens (min 15, max 30 min)
        tempo_turnaround = min(max(15, 15 + (n_passageiros_desembarque 
                                             + n_passageiros_embarque) / 20), 
                               30)
        
        # Tempo para embarque completo (desde início até último passageiro 
        # entrar)
        # Geralmente mais rápido que desembarque
        tempo_total_embarque = 50 # minutos fixo para embarque
        
        # Horário que o desembarque deve iniciar (logo após aterrisagem)
        horario_inicio_desembarque = horario_aterrisagem
        
        # Horário que o embarque deve iniciar (após desembarque + turnaround)
        horario_inicio_embarque = (horario_inicio_desembarque 
                                   + tempo_total_desembarque 
                                   + tempo_turnaround)
        
        voo = {
            'id': i + 1,
            'horario_aterrisagem': horario_aterrisagem,
            'n_passageiros_desembarque': n_passageiros_desembarque,
            'n_requisicoes_desembarque': n_requisicoes_desembarque,
            'n_passageiros_embarque': n_passageiros_embarque,
            'n_requisicoes_embarque': n_requisicoes_embarque,
            'tempo_total_desembarque': tempo_total_desembarque,
            'tempo_turnaround': tempo_turnaround,
            'tempo_total_embarque': tempo_total_embarque,
            'horario_inicio_desembarque': horario_inicio_desembarque,
            'horario_inicio_embarque': horario_inicio_embarque
        }
        
        voos.append(voo)
        total_requisicoes += n_requisicoes_desembarque + n_requisicoes_embarque
    
    n = total_requisicoes
    
    # Calcular número máximo de viagens por ônibus baseado nos parâmetros
    # Considera: requisições totais, ônibus disponíveis, duração da operação e 
    # eficiência
    requisicoes_por_onibus = math.ceil(n / n_onibus)
    
    # Tempo médio por viagem (incluindo ida, serviço e volta): ~45-60 min
    tempo_medio_viagem = 50  # minutos (CORRIGIDO: valor realístico)
    viagens_possiveis_por_tempo = int(duracao_operacao_horas * 60 
                                      / tempo_medio_viagem)
    
    # Usar o maior entre a necessidade e a possibilidade temporal
    max_viagens_por_onibus = max(
        requisicoes_por_onibus,  # Necessidade baseada em requisições
        min(viagens_possiveis_por_tempo, 10)  # Limite prático de 10 viagens
    )
    
    print(f"Total de requisições geradas: {n}")
    print(f"Máximo de viagens por ônibus: {max_viagens_por_onibus}")
    
    # 2. Gerar layout do aeroporto (coordenadas dos pontos)
    # Garagem (ponto 0) no centro da operação
    garagem = (0, 1000)
    
    # Portões de embarque (lado oeste)
    portoes = []
    for i in range(n_portoes):
        x = random.uniform(-800, -200)  # metros
        y = random.uniform(-500, 500)
        portoes.append((x, y))
    
    # Posições de aeronaves (lado leste, mais distantes)
    posicoes_aeronaves = []
    for i in range(n_posicoes_aeronaves):
        x = random.uniform(500, 1500)  # metros
        y = random.uniform(-800, 800)
        posicoes_aeronaves.append((x, y))
    
    # 3. Mapear requisições para pontos específicos
    pontos_coleta = [garagem]  # índice 0 é a garagem
    pontos_entrega = []
    
    janelas_tempo = []
    req_id = 0
    
    for voo in voos:
        # Selecionar portão e posição de aeronave para este voo
        portao = random.choice(portoes)
        posicao_aeronave = random.choice(posicoes_aeronaves)
        
        # FASE 1: DESEMBARQUE (aeronave → portão)
        # Requisições de desembarque ocorrem logo após aterrisagem
        tempo_por_requisicao_desembarque = (voo['tempo_total_desembarque'] 
                                            / voo['n_requisicoes_desembarque'])
        
        for req_desembarque in range(voo['n_requisicoes_desembarque']):
            req_id += 1
            
            # Coleta na aeronave, entrega no portão
            pontos_coleta.append(posicao_aeronave)
            pontos_entrega.append(portao)
            
            # Janela de tempo para esta requisição de desembarque
            # Cada requisição tem uma janela dentro do tempo total de 
            # desembarque
            inicio_janela = (voo['horario_inicio_desembarque'] 
                             + req_desembarque 
                             * tempo_por_requisicao_desembarque)
            fim_janela = inicio_janela + tempo_por_requisicao_desembarque
            
            janelas_tempo.append((inicio_janela, fim_janela))
        
        # FASE 2: EMBARQUE (portão → aeronave)
        # Requisições de embarque ocorrem após desembarque completo 
        # + turnaround
        tempo_por_requisicao_embarque = (voo['tempo_total_embarque'] 
                                         / voo['n_requisicoes_embarque'])

        for req_embarque in range(voo['n_requisicoes_embarque']):
            req_id += 1
            
            # Coleta no portão, entrega na aeronave
            pontos_coleta.append(portao)
            pontos_entrega.append(posicao_aeronave)
            
            # Janela de tempo para esta requisição de embarque
            # Cada requisição tem uma janela dentro do tempo total de embarque
            inicio_janela = (voo['horario_inicio_embarque'] 
                             + req_embarque * tempo_por_requisicao_embarque)
            fim_janela = inicio_janela + tempo_por_requisicao_embarque
            
            janelas_tempo.append((inicio_janela, fim_janela))
    
    # 4. Calcular matriz de distâncias entre todos os pontos
    todos_pontos = pontos_coleta + pontos_entrega
    n_pontos = len(todos_pontos)
    
    def distancia_euclidiana(p1, p2):
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    
    # Matriz de distâncias entre pontos individuais
    d = np.zeros((n_pontos, n_pontos))
    for i in range(n_pontos):
        for j in range(n_pontos):
            if i != j:
                d[i, j] = distancia_euclidiana(todos_pontos[i], 
                                               todos_pontos[j])
    
    # 5. Calcular matriz de distâncias entre requisições (D)
    D = np.zeros((n + 1, n + 1))
    for i in range(n + 1):
        for j in range(n + 1):
            if i == j:
                continue
            elif i == 0:  # da garagem para requisição j
                D[0, j] = d[0, j]
            elif j == 0:  # da requisição i para garagem
                D[i, 0] = d[i + n, 0]
            else:  # entre requisições i e j
                # Distância = coleta_i -> entrega_i -> coleta_j
                D[i, j] = d[i, i + n] + d[i + n, j]
    
    # 6. Matriz de custos (igual à distância)
    c = D.copy()
    
    # 7. Tempos de serviço
    s = np.zeros(n + 1)
    s[0] = preparo_onibus # Tempo de preparo para uma viagem (minutos)
    for i in range(1, n + 1):
        # Tempo de embarque/desembarque varia entre 3-8 minutos
        s[i] = random.uniform(3.0, 8.0)
    
    # 8. Calcular tempos de viagem (assumindo velocidade de 30 km/h = 500 m/min)
    velocidade = 500 # metros por minuto
    t = d / velocidade
    
    # Matriz de tempos entre requisições
    T = np.zeros((n + 1, n + 1))
    for i in range(n + 1):
        for j in range(n + 1):
            if i == j:
                T[i, j] = 0
            elif i == 0:
                T[0, j] = t[0, j]
            elif j == 0:
                T[i, 0] = t[i + n, 0]
            else:
                T[i, j] = t[i, i + n] + t[i + n, j]
    
    # 9. Janelas de tempo das requisições
    e = np.array([jt[0] for jt in janelas_tempo])
    l = np.array([jt[1] for jt in janelas_tempo])
    
    # 10. TEMPO MÁXIMO por viagem (em vez de distância máxima)
    # Baseado na análise dos tempos de viagem e características operacionais
    
    # Calcular estatísticas dos tempos para definir limite realístico
    tempo_medio_requisicao = np.mean([T[0, j] + s[j] + T[j, 0] for j in 
                                      range(1, n + 1)])
    tempo_max_requisicao = np.max([T[0, j] + s[j] + T[j, 0] for j in 
                                   range(1, n + 1)])
    
    # Tempo máximo por viagem: permite 3-4 requisições com folga
    # Fórmula: tempo_preparacao_garagem + 3.5 * tempo_medio_requisicao
    Tmax = s[0] + 3.5 * tempo_medio_requisicao
    
    # Garantir viabilidade: pelo menos uma requisição deve ser possível
    Tmax = max(Tmax, tempo_max_requisicao + 10)  # +10 min de margem
    
    # Limitar para ser realístico: mínimo 60 min, máximo 120 min
    # FIXME: o máximo é para ser 6 horas e o mínimo pode ser umas 2 horas.
    Tmax = max(60.0, min(Tmax, 120.0))
    
    print(f"Tempo médio por requisição: {tempo_medio_requisicao:.1f} min")
    print(f"Tempo máximo por requisição: {tempo_max_requisicao:.1f} min")
    print(f"Tempo máximo por viagem definido: {Tmax:.1f} min")
    print(
        f"Requisições estimadas por viagem: {((Tmax - s[0])
        / tempo_medio_requisicao):.1f}"
    )

    # 11. Estruturar dados para saída
    dados = {
        "metadados": {
            "descricao": ("Instância de embarque remoto de aeroporto com "
                          + "modelo de desembarque-embarque"),
            "data_geracao": datetime.now().isoformat(),
            "n_voos": n_voos,
            "capacidade_onibus": capacidade_onibus,
            "duracao_operacao_horas": duracao_operacao_horas,
            "seed": seed,
        },
        "numeroRequisicoes": n,
        "numeroOnibus": n_onibus,
        "numeroMaximoViagens": max_viagens_por_onibus,
        "distanciaRequisicoes": D.tolist(),
        "distanciaPontos": d.tolist(),
        "tempoMaximoViagem": float(Tmax),  # MUDANÇA: era distanciaMaxima
        "custo": c.tolist(),
        "tempoServico": s.tolist(),
        "tempoRequisicoes": T.tolist(),
        "tempoPontos": t.tolist(),
        "inicioJanela": e.tolist(),
        "fimJanela": l.tolist(),
        "detalhes_voos": voos,
        "coordenadas_pontos": {
            "garagem": garagem,
            "pontos_coleta": pontos_coleta[1:],  # excluir garagem
            "pontos_entrega": pontos_entrega,
            "portoes": portoes,
            "posicoes_aeronaves": posicoes_aeronaves
        },
        "estatisticas_tempo": {  # NOVO: estatísticas para análise
            "tempo_medio_requisicao": float(tempo_medio_requisicao),
            "tempo_max_requisicao": float(tempo_max_requisicao),
            "tempo_preparacao_garagem": float(s[0]),
            "velocidade_operacao": velocidade,
            "requisicoes_estimadas_por_viagem": round(Tmax 
                                                      / tempo_medio_requisicao,
                                                      1)
        }
    }
    
    return dados

def gerar_instancias_variadas():
    """Gera várias instâncias com diferentes tamanhos e características."""
    
    instancias = [
        # Instância pequena (teste)
        {"nome": "pequena", "n_voos": 2, "n_onibus": 3, "duracao": 4},
        
        # Instância média (realística)
        {"nome": "media", "n_voos": 10, "n_onibus": 6, "duracao": 8},
        
        # Instância grande (pico de operação)
        {"nome": "grande", "n_voos": 15, "n_onibus": 11, "duracao": 12},
        
        # Instância rush (alta demanda)
        {"nome": "rush", "n_voos": 15, "n_onibus": 11, "duracao": 6}
    ]
    
    for config in instancias:
        print(f"\n=== Gerando instância {config['nome']} ===")
        
        dados = gerar_instancia_aeroporto(
            n_voos=config["n_voos"],
            n_onibus=config["n_onibus"],
            duracao_operacao_horas=config["duracao"],
            seed=42
        )
        
        nome_arquivo = f"./dados/{config['nome']}.json"
        
        with open(nome_arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
        
        print(f"Instância salva em: {nome_arquivo}")
        print(f"Voos: {config['n_voos']}")
        print(f"Requisições totais: {dados['numeroRequisicoes']}")
        
        # Calcular estatísticas de desembarque/embarque
        n_req_desembarque = sum(v['n_requisicoes_desembarque'] 
                                for v in dados['detalhes_voos'])
        n_req_embarque = sum(v['n_requisicoes_embarque'] 
                             for v in dados['detalhes_voos'])
        
        print(f"  - Requisições de desembarque: {n_req_desembarque}")
        print(f"  - Requisições de embarque: {n_req_embarque}")
        print(f"Ônibus: {dados['numeroOnibus']}")
        print(f"Máximo viagens por ônibus: {dados['numeroMaximoViagens']}")
        print(f"Capacidade total: {(dados['numeroOnibus']
              * dados['numeroMaximoViagens'])} viagens")
        print(f"Tempo máximo por viagem: {dados['tempoMaximoViagem']:.1f} min")
        print("Requisições estimadas por viagem: "
              + f"{(dados['estatisticas_tempo']
              ['requisicoes_estimadas_por_viagem'])}")

if __name__ == "__main__":
    print("Gerador de Instâncias Realísticas - Embarque Remoto de Aeroporto")
    print("=" * 70)
    
    gerar_instancias_variadas()
    
    print("\n" + "=" * 70)
    print("Instâncias geradas com sucesso!")
