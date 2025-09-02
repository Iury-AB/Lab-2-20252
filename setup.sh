#!/bin/bash
# Script de configuração e execução do projeto

echo "============================================================"
echo "CONFIGURAÇÃO DO PROJETO - EMBARQUE REMOTO AEROPORTO"
echo "============================================================"

# Verificar se Python3 está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 não encontrado. Instale o Python3 primeiro."
    exit 1
fi

echo "✓ Python3 encontrado"

# Criar ambiente virtual (opcional)
echo "Criando ambiente virtual..."
python3 -m venv venv
source venv/bin/activate
echo "✓ Ambiente virtual ativado"

# Instalar dependências
echo "Instalando dependências..."
pip install --upgrade pip
pip install -r requirements.txt

# Verificar instalação
echo "Verificando instalação..."
python3 testar_instalacao.py

echo ""
echo "============================================================"
echo "EXECUÇÃO DOS EXEMPLOS"
echo "============================================================"

echo "1. Demonstração conceitual (sem Gurobi):"
echo "   python3 demonstracao.py"
echo ""

echo "2. Exemplo simples com Gurobi:"
echo "   python3 exemplo_simples.py"
echo ""

echo "3. Implementação completa:"
echo "   python3 aeroporto_gurobi.py"
echo ""

echo "============================================================"
echo "LICENÇA GUROBI"
echo "============================================================"
echo "Para usar o Gurobi, você precisa de uma licença:"
echo "• Acadêmica (gratuita): https://www.gurobi.com/academia/"
echo "• Comercial: https://www.gurobi.com/products/gurobi-optimizer/"
echo "• Teste (30 dias): Incluída na instalação"
echo ""

echo "Configuração concluída!"
echo "Execute 'source venv/bin/activate' para ativar o ambiente virtual"
