import random

def permuta(k1, k2, solucao):
    # k1 e k2 devem ser o id do onibus
    # sempre é primeira viagem nesse ponto, ainda não adicionado as garagens
    k1_req_id = random.randrange(solucao.rota[k1][1])
    k2_req_id = random.randrange(solucao.rota[k2][1])
    # Troca as requisições entre os dois ônibus
    solucao.rota[k1][0][k1_req_id], solucao.rota[k2][0][k2_req_id] = solucao.rota[k2][0][k2_req_id], solucao.rota[k1][0][k1_req_id]
    return solucao




