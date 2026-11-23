# Gerador de Rodízio Balanceado

Aplicação web desenvolvida em Python e Streamlit para automatizar o planejamento amostral e a alocação balanceada de produtos em pesquisas de mercado e testes sensoriais.

## Contexto e Problema

A montagem de matrizes de rodízio de produtos costumava depender de ferramentas legadas em ambiente DOS (como o KofN executado via DOSBox) e de conferências manuais em planilhas, tornando o processo lento e suscetível a erros operacionais.

Este projeto foi criado para substituir esse fluxo manual por uma interface web acessível via navegador, permitindo gerar matrizes de distribuição por cotas e auditar o equilíbrio das amostras antes da ida a campo.

## Como Funciona

A aplicação recebe uma base de participantes (`.xlsx` ou `.csv`) ou gera uma sequência de IDs e realiza a distribuição em etapas:

1. **Segmentação por cotas:** agrupa os participantes pelas variáveis selecionadas (ex.: perfil, faixa etária, praça) para garantir equilíbrio dentro de cada estrato.
2. **Alocação híbrida (Fixos + Rotativos):** combina produtos obrigatórios (controle) com produtos rotativos sorteados a partir de um conjunto cíclico balanceado (`itertools.cycle`), evitando que um item seja sub ou super-representado no grupo.
3. **Controle de repetição e ordem:** aplica troca de adjacência para evitar duplicidade imediata na mesma amostra e embaralha a ordem de apresentação (`Posicao_1` a `Posicao_N`) por participante para reduzir viés de posição.
4. **Auditoria visual e exportação:** exibe tabela de frequência total, matriz cruzada (Produto x Posição) com gradiente de calor e exporta o arquivo `.xlsx` com abas separadas para a base final e o resumo de auditoria.

## Tecnologias Utilizadas

- **Python**
- **Streamlit** (interface web e visualização interativa)
- **pandas** (manipulação de bases, agrupamento por cotas e tabelas cruzadas)
- **XlsxWriter** (exportação da base gerada e da aba de auditoria para Excel)
- **Matplotlib** (estilização do mapa de calor na auditoria)

## Como Executar Localmente

```bash
# Clone o repositório
git clone [https://github.com/eduardabandeira/rodizio_advance.git](https://github.com/eduardabandeira/rodizio_advance.git)
cd rodizio_advance

# Instale as dependências
pip install -r requirements.txt

# Execute a aplicação
streamlit run app.py
