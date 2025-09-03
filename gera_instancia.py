#!/usr/bin/env python3
"""
Gerador de Instâncias Realísticas para Otimização do Serviço de Embarque Remoto de Aeroporto

Este script gera conjuntos de dados representativos para o problema de roteamento de ônibus
em aeroportos, considerando características realísticas como:
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

def gerar_instancia_aeroporto(n_voos=10, capacidade_onibus=50, n_onibus=5, 
                            duracao_operacao_horas=8, seed=42, n_portoes=10,
                            n_posicoes_aeronaves=15):
    """
    Gera uma instância realística do problema de embarque remoto de aeroporto.
    
    Parâmetros:
    - n_voos: número de voos (embarques + desembarques)
    - capacidade_onibus: capacidade de passageiros por ônibus
    - n_onibus: número de ônibus disponíveis
    - duracao_operacao_horas: duração total da operação em horas
    - seed: semente para reprodutibilidade
    - n_portoes: número de portões de embarque
    - n_posicoes_aeronaves: número de posições de aeronaves
    """
    
    random.seed(seed)
    np.random.seed(seed)
    
    print(f"Gerando instância com {n_voos} voos, {n_onibus} ônibus...")
    
    # 1. Gerar voos com número de passageiros variado
    voos = []
    total_requisicoes = 0
    
    for i in range(n_voos):
        # Número de passageiros varia entre 80 e 300 (típico para voos domésticos/internacionais)
        n_passageiros = random.randint(80, 300)
        
        # Calcular número de requisições necessárias (viagens de ônibus)
        n_requisicoes_voo = math.ceil(n_passageiros / capacidade_onibus)
        
        # Tipo de operação (embarque ou desembarque)
        tipo = random.choice(['embarque', 'desembarque'])
        
        # Horário do voo (distribuído ao longo do dia)
        horario_base = i * (duracao_operacao_horas * 60) // n_voos  # em minutos
        
        voo = {
            'id': i + 1,
            'tipo': tipo,
            'n_passageiros': n_passageiros,
            'n_requisicoes': n_requisicoes_voo,
            'horario_base': horario_base
        }
        
        voos.append(voo)
        total_requisicoes += n_requisicoes_voo
    
    n = total_requisicoes
    print(f"Total de requisições geradas: {n}")
    
    # 2. Gerar layout do aeroporto (coordenadas dos pontos)
    # Garagem (ponto 0) no centro
    garagem = (0, 0)
    
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
        
        for req_voo in range(voo['n_requisicoes']):
            req_id += 1
            
            if voo['tipo'] == 'embarque':
                # Coleta no portão, entrega na aeronave
                pontos_coleta.append(portao)
                pontos_entrega.append(posicao_aeronave)
            else:
                # Coleta na aeronave, entrega no portão
                pontos_coleta.append(posicao_aeronave)
                pontos_entrega.append(portao)
            
            # Janela de tempo para esta requisição
            # Requisições do mesmo voo têm janelas sequenciais
            inicio_janela = voo['horario_base'] + req_voo * 5  # 5 min entre requisições do mesmo voo
            fim_janela = inicio_janela + 15  # 15 min de flexibilidade
            
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
                d[i, j] = distancia_euclidiana(todos_pontos[i], todos_pontos[j])
    
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
    s[0] = 10.0  # 10 min para reabastecimento na garagem
    for i in range(1, n + 1):
        # Tempo de embarque/desembarque varia entre 3-8 minutos
        s[i] = random.uniform(3.0, 8.0)
    
    # 8. Calcular tempos de viagem (assumindo velocidade de 30 km/h = 500 m/min)
    velocidade = 500  # metros por minuto
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
    
    # 10. Distância máxima por viagem (baseada na autonomia do ônibus)
    # Considerando que um ônibus pode operar por 2-3 horas sem reabastecimento
    Dmax = 2 * np.max(D) + 0.5 * np.sum(D) / n  # Aproximadamente 2-3 requisições por viagem
    
    # 11. Estruturar dados para saída
    dados = {
        "metadados": {
            "descricao": "Instância realística de embarque remoto de aeroporto",
            "data_geracao": datetime.now().isoformat(),
            "n_voos": n_voos,
            "capacidade_onibus": capacidade_onibus,
            "duracao_operacao_horas": duracao_operacao_horas,
            "seed": seed
        },
        "numeroRequisicoes": n,
        "numeroOnibus": n_onibus,
        "distanciaRequisicoes": D.tolist(),
        "distanciaPontos": d.tolist(),
        "distanciaMaxima": float(Dmax),
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
        }
    }
    
    return dados

def gerar_instancias_variadas():
    """Gera várias instâncias com diferentes tamanhos e características."""
    
    instancias = [
        # Instância pequena (teste)
        {"nome": "pequena", "n_voos": 5, "n_onibus": 3, "duracao": 4},
        
        # Instância média (realística)
        {"nome": "media", "n_voos": 15, "n_onibus": 6, "duracao": 8},
        
        # Instância grande (pico de operação)
        {"nome": "grande", "n_voos": 30, "n_onibus": 10, "duracao": 12},
        
        # Instância rush (alta demanda)
        {"nome": "rush", "n_voos": 20, "n_onibus": 8, "duracao": 6}
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
        print(f"Requisições: {dados['numeroRequisicoes']}")
        print(f"Ônibus: {dados['numeroOnibus']}")
        print(f"Distância máxima por viagem: {dados['distanciaMaxima']:.2f}m")

if __name__ == "__main__":
    print("Gerador de Instâncias Realísticas - Embarque Remoto de Aeroporto")
    print("=" * 70)
    
    gerar_instancias_variadas()
    
    print("\n" + "=" * 70)
    print("Instâncias geradas com sucesso!")
    print("\nCaracterísticas das instâncias:")
    print("- Layout realístico de aeroporto com portões e posições de aeronaves")
    print("- Voos com número variado de passageiros (80-300)")
    print("- Janelas de tempo coordenadas com horários de voos")
    print("- Tempos de serviço realísticos (3-8 min)")
    print("- Distâncias baseadas em coordenadas geográficas")
    print("- Capacidade de ônibus: 50 passageiros")
    print("- Velocidade de operação: 30 km/h")
