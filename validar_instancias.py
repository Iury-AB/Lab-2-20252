#!/usr/bin/env python3
"""
Teste de Validação das Instâncias Geradas

Este script testa se as instâncias geradas são compatíveis com o solver
existente e verifica a qualidade dos dados.
"""

import json
import numpy as np
import sys

def validar_instancia(nome_arquivo):
    """Valida uma instância gerada."""
    print(f"\n=== VALIDANDO {nome_arquivo} ===")
    
    try:
        # Carregar dados
        with open(nome_arquivo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        # Extrair parâmetros principais
        n = dados["numeroRequisicoes"]
        K = dados["numeroOnibus"]
        D = np.array(dados["distanciaRequisicoes"])
        Dmax = dados["distanciaMaxima"]
        c = np.array(dados["custo"])
        s = np.array(dados["tempoServico"])
        T = np.array(dados["tempoRequisicoes"])
        e = np.array(dados["inicioJanela"])
        l = np.array(dados["fimJanela"])
        
        print(f"✅ Arquivo carregado com sucesso")
        print(f"   Requisições: {n}, Ônibus: {K}")
        
        # Validações básicas
        erros = []
        
        # 1. Dimensões das matrizes
        if D.shape != (n+1, n+1):
            erros.append(f"Matriz D tem dimensão {D.shape}, esperado ({n+1}, {n+1})")
        
        if c.shape != (n+1, n+1):
            erros.append(f"Matriz c tem dimensão {c.shape}, esperado ({n+1}, {n+1})")
            
        if T.shape != (n+1, n+1):
            erros.append(f"Matriz T tem dimensão {T.shape}, esperado ({n+1}, {n+1})")
        
        if len(s) != n+1:
            erros.append(f"Vetor s tem {len(s)} elementos, esperado {n+1}")
            
        if len(e) != n:
            erros.append(f"Vetor e tem {len(e)} elementos, esperado {n}")
            
        if len(l) != n:
            erros.append(f"Vetor l tem {len(l)} elementos, esperado {n}")
        
        # 2. Valores não negativos
        if np.any(D < 0):
            erros.append("Matriz D contém valores negativos")
            
        if np.any(c < 0):
            erros.append("Matriz c contém valores negativos")
            
        if np.any(T < 0):
            erros.append("Matriz T contém valores negativos")
            
        if np.any(s < 0):
            erros.append("Vetor s contém valores negativos")
        
        # 3. Diagonal zero
        if not np.allclose(np.diag(D), 0):
            erros.append("Diagonal da matriz D não é zero")
            
        if not np.allclose(np.diag(T), 0):
            erros.append("Diagonal da matriz T não é zero")
        
        # 4. Janelas de tempo válidas
        if np.any(e > l):
            erros.append("Algumas janelas de tempo são inválidas (início > fim)")
            
        if np.any(e < 0):
            erros.append("Janelas de tempo contêm valores negativos")
        
        # 5. Consistência entre matrizes
        if not np.allclose(D, c):
            erros.append("Matrizes D e c não são consistentes")
        
        # 6. Distância máxima razoável
        max_dist = np.max(D[D > 0])
        if Dmax < max_dist:
            erros.append(f"Distância máxima ({Dmax:.2f}) menor que distância entre requisições ({max_dist:.2f})")
        
        # Reportar resultados
        if erros:
            print("❌ FALHAS ENCONTRADAS:")
            for erro in erros:
                print(f"   - {erro}")
            return False
        else:
            print("✅ Todas as validações passaram")
            
            # Estatísticas adicionais
            print(f"   Distância média: {np.mean(D[D > 0]):.2f}m")
            print(f"   Distância máxima: {np.max(D[D > 0]):.2f}m")
            print(f"   Tempo de serviço médio: {np.mean(s[1:]):.2f} min")
            print(f"   Janela de tempo média: {np.mean(l - e):.2f} min")
            
            return True
            
    except Exception as e:
        print(f"❌ ERRO ao carregar arquivo: {e}")
        return False

def testar_compatibilidade_solver():
    """Testa se as instâncias são compatíveis com o solver existente."""
    print("\n=== TESTE DE COMPATIBILIDADE COM SOLVER ===")
    
    try:
        # Tentar usar a instância pequena com o formato do solver existente
        with open('instancia_aeroporto_pequena.json', 'r') as f:
            dados = json.load(f)
        
        # Simular carregamento como no exato.py
        n = dados["numeroRequisicoes"]
        K = dados["numeroOnibus"]
        D = np.array(dados["distanciaRequisicoes"])
        Dmax = dados["distanciaMaxima"]
        c = np.array(dados["custo"])
        s = np.array(dados["tempoServico"])
        T = np.array(dados["tempoRequisicoes"])
        e = np.array(dados["inicioJanela"])
        l = np.array(dados["fimJanela"])
        V = 5  # Número de viagens como no solver original
        
        # Criar conjuntos como no solver
        N = list(range(1, n+1))
        N0 = list(range(n+1))
        V_list = list(range(1, V+1))
        K_list = list(range(1, K+1))
        
        print("✅ Formato compatível com solver existente")
        print(f"   Conjuntos criados: N={len(N)}, N0={len(N0)}, V={len(V_list)}, K={len(K_list)}")
        
        # Verificar se há dados suficientes para uma solução viável
        total_demanda = n
        capacidade_total = K * V  # ônibus × viagens
        
        print(f"   Demanda total: {total_demanda} requisições")
        print(f"   Capacidade total: {capacidade_total} (ônibus×viagens)")
        
        if capacidade_total >= total_demanda:
            print("✅ Capacidade suficiente para atender todas as requisições")
        else:
            print("⚠️  Capacidade pode ser insuficiente")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO na compatibilidade: {e}")
        return False

def gerar_relatorio_final():
    """Gera relatório final de validação."""
    print("\n" + "="*60)
    print("RELATÓRIO FINAL DE VALIDAÇÃO")
    print("="*60)
    
    instancias = ['pequena', 'media', 'grande', 'rush']
    resultados = {}
    
    for nome in instancias:
        arquivo = f'instancia_aeroporto_{nome}.json'
        resultados[nome] = validar_instancia(arquivo)
    
    # Teste de compatibilidade
    compatibilidade = testar_compatibilidade_solver()
    
    # Resumo
    print(f"\n=== RESUMO ===")
    sucesso = sum(resultados.values())
    total = len(resultados)
    
    print(f"Instâncias validadas: {sucesso}/{total}")
    print(f"Compatibilidade com solver: {'✅' if compatibilidade else '❌'}")
    
    if sucesso == total and compatibilidade:
        print("🎉 TODAS AS VALIDAÇÕES PASSARAM!")
        print("   As instâncias estão prontas para uso.")
        return True
    else:
        print("⚠️  Algumas validações falharam.")
        print("   Verifique os erros acima.")
        return False

if __name__ == "__main__":
    print("VALIDADOR DE INSTÂNCIAS - EMBARQUE REMOTO DE AEROPORTO")
    print("="*60)
    
    sucesso = gerar_relatorio_final()
    
    if sucesso:
        print("\n✅ Dataset pronto para uso em pesquisa e desenvolvimento!")
        sys.exit(0)
    else:
        print("\n❌ Dataset requer correções.")
        sys.exit(1)
