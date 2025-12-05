import MACS
from dados import Dados, carrega_dados_json
from solucao import Solucao
import matplotlib.pyplot as plt
import sys
import os
import alcione as al

# Carrega e resolve
instancia = carrega_dados_json("dados/pequena.json")
solucao = Solucao()
solucao.carregar("dados/otimo_pequena.json")

# --- INICIO DO TRECHO ADICIONADO ---

def plotar_cronograma(solucao, instancia):
    """
    Plota um gráfico de Gantt das rotas dos ônibus.
    Barra inicia na Chegada e termina em Chegada + Serviço + Deslocamento p/ próximo.
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Cores para diferenciar visualmente as barras (opcional, mas ajuda a ver separação)
    cmap = plt.get_cmap('tab20')
    
    # Lista de ônibus para o eixo Y
    lista_onibus = sorted(solucao.rota.keys())
    
    for k in lista_onibus:
        # Itera sobre todas as viagens (v) do ônibus (k)
        # Como o eixo Y é o ônibus, todas as viagens ficam na mesma linha
        for v in solucao.rota[k]:
            rota_lista = solucao.rota[k][v]
            chegada_lista = solucao.chegada[k][v]
            
            # Percorre cada requisição na rota
            for idx, req in enumerate(rota_lista):
                if idx + 1 == len(rota_lista) and v+1 in solucao.rota[k]:
                    continue
                # Geralmente pulamos o depósito (0) na plotagem de tarefas, 
                # a menos que você queira ver o tempo parado no depósito.
                # Assumindo que queremos ver apenas as requisições de serviço:
                
                inicio_barra = chegada_lista[idx]
                tempo_servico = instancia.s[req]
                
                # Determinar o próximo ponto para calcular o deslocamento (T)
                # Se houver um próximo item na lista, usamos ele.
                # Se for o último item da lista, assumimos retorno ao depósito (0).
                if idx + 1 < len(rota_lista):
                    proximo_req = rota_lista[idx+1]
                    tempo_deslocamento = instancia.T[req][proximo_req]
                else:
                    tempo_deslocamento = 0
                
                # Definição da largura conforme seu pedido:
                # "direita representa chegada+serviço+deslocamento para a proxima"
                # Largura = (Chegada + Servico + Deslocamento) - (Chegada)
                largura_barra = tempo_servico + tempo_deslocamento
                
                # Desenha a barra
                # Usamos req % 20 para variar as cores baseadas no ID da requisição
                cor = cmap(int(req) % 20)
                
                ax.barh(y=k, width=largura_barra, left=inicio_barra, 
                        color=cor, edgecolor='black', alpha=0.7, align='center')
                
                # Adiciona o ID da requisição no centro da barra para identificação
                ax.text(inicio_barra + largura_barra/2, k, str(req), 
                        va='center', ha='center', color='white', fontsize=8, fontweight='bold')

    # Formatação do Gráfico
    ax.set_xlabel('Tempo')
    ax.set_ylabel('Ônibus (ID)')
    ax.set_title('Cronograma de Atendimento por Ônibus')
    
    # Define os ticks do eixo Y para mostrar apenas os IDs dos ônibus existentes
    ax.set_yticks(lista_onibus)
    
    # Adiciona grid vertical para facilitar leitura do tempo
    ax.grid(True, axis='x', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    plt.show()


# Chama a função para gerar o gráfico
plotar_cronograma(solucao, instancia)
