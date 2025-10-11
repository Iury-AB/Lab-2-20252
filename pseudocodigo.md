// Função Multi-ACS(K, MaxIter, m) 

Entrada: conjunto de requisições N, frota de ônibus homogênea K, número máximo de iterações MaxIter, número de formigas m 

Saída: melhor solução encontrada (BestSol) 

InicializarFeromônio(); 
BestSol ← ConstróiSoluçãoInicial; 
 
repeat (iter = 1 até MaxIter) 
 
    for formiga f ∈ {1,…,m} 
        // 1ª fase: Atribuição de requisições a ônibus (bus-ant) 
        Q ← {todas as requisições N};  //requisições não atendidas 
        for ônibus k ∈ K 
            Qk ← ∅; 
 
        while Q ≠ ∅ do 
            i ← SelecionaRequisição(Q, FeromônioBus, AtratividadeBus); 
            k ← SelecionaÔnibusDisponível(i, FeromônioBus, AtratividadeBus); 
            Atribuir(i → k); 
            AtualizarFeromônioLocal(i, k); 
        end while 
 
        // 2ª fase: Construção da rota para cada ônibus (route-ant) 
        for ônibus k ∈ K 
            v ← 1
            Rota(k,v) ← [garagem]; 
            while Qk ≠ ∅ do
                i ← ÚltimaRequisição(Rota(k,v)); 
                j ← SelecionaPróximaRequisição(Qk,i, FeromônioRoute, AtratividadeRoute);
                If Bjv > Tmax - Ti0
                    Inserir(garagem após i, v)
                    v ← v + 1
                    i ← ÚltimaRequisição(Rota(k,v)); 
                Inserir(j após i, v); //Adiciona
            end while 

            FecharRota(Rota(k,v), garagem); 
        end for                    
 
        Sol(f) ← (Qk for k ∈ K); 
        Sol(f) ← BuscaLocal(Sol(f)); 
    end for 
 
    // 3ª fase: Atualização global 
    f* ← argmin{ Custo(Sol(f)) }; // Escolhe a melhor solução dentre as formigas 
    If Custo(Sol(f*)) < Custo(BestSol) então 
        BestSol ← Sol(f*); 
    end If 
    AtualizarFeromônioGlobal(Sol(f*)); 
 
end repeat 
