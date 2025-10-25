import re
import json

# Função para ler media.json (parâmetros da instância)

def ler_parametros_media(path):
    with open(path, "r", encoding="utf-8") as f:
        dados = json.load(f)
    # Retorna todos os parâmetros relevantes
    return {
        "n_requisicoes": dados["numeroRequisicoes"],
        "numero_onibus": dados["numeroOnibus"],
        "numero_maximo_viagens": dados["numeroMaximoViagens"],
        "capacidade_onibus": dados.get("capacidade_onibus", 9999),
        "custo": dados["custo"],
        "tempo_servico": dados["tempoServico"],
        "tempo_requisicoes": dados["tempoRequisicoes"],
        "inicio_janela": dados["inicioJanela"],
        "fim_janela": dados["fimJanela"]
    }


# Função para ler melhorSolucao.json (solução encontrada)
def ler_rotas_solucao(path):
    with open(path, 'r', encoding='utf-8') as f:
        texto = f.read()
    padrao_rota = r"rota ([\d ]+)"
    rotas = re.findall(padrao_rota, texto)
    rotas_onibus = []
    for rota in rotas:
        pontos = [int(x) for x in rota.strip().split()]
        rotas_onibus.append(pontos)
    return rotas_onibus

def verificar_restricoes(media_path, solucao_path):
    params = ler_parametros_media(media_path)
    rotas = ler_rotas_solucao(solucao_path)
    n_requisicoes = params['n_requisicoes']
    capacidade = params['capacidade_onibus']
    inicio_janela = params['inicio_janela']
    fim_janela = params['fim_janela']

    # 1. Atendimento único das requisições
    atendidas = set()
    duplicadas = set()
    for rota in rotas:
        for req in rota:
            if req != 0:
                if req in atendidas:
                    duplicadas.add(req)
                atendidas.add(req)
    faltantes = set(range(1, n_requisicoes+1)) - atendidas

    # 2. Capacidade dos ônibus (exemplo: checa se rota tem mais que capacidade)
    violacoes_capacidade = []
    for idx, rota in enumerate(rotas):
        if len([x for x in rota if x != 0]) > capacidade:
            violacoes_capacidade.append(idx)

    # 3. Início/fim na garagem
    violacoes_garagem = []
    for idx, rota in enumerate(rotas):
        if rota[0] != 0 or rota[-1] != 0:
            violacoes_garagem.append(idx)

    # 4. Janelas de tempo (exemplo: só checa se existe janela para cada requisição)
    violacoes_janela = []
    for req in atendidas:
        if req > len(inicio_janela) or req > len(fim_janela):
            violacoes_janela.append(req)

    # Relatório
    print('--- RELATÓRIO DE RESTRIÇÕES ---')
    print(f'Requisições duplicadas: {sorted(duplicadas)}')
    print(f'Requisições faltantes: {sorted(faltantes)}')
    print(f'Rotas que excedem capacidade: {violacoes_capacidade}')
    print(f'Rotas que não começam/terminam na garagem: {violacoes_garagem}')
    print(f'Requisições sem janela de tempo definida: {violacoes_janela}')
    print('Total de rotas:', len(rotas))

if __name__ == '__main__':
    # Ajuste os nomes dos arquivos conforme necessário
    verificar_restricoes('media.json', 'melhorSolucao.json')
