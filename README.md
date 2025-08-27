# Grupo-278-I2A2

📊 Projeto de Cálculo de VR Mensal com Agente LLM
📌 Visão Geral

Este projeto foi desenvolvido para automatizar o cálculo do Vale-Refeição (VR) mensal dos colaboradores, aplicando regras de elegibilidade, exclusões, cálculo de dias úteis e integração com bases de sindicatos.

Além do processamento de dados, o projeto conta com um Agente LLM (usando Google Gemini + LangChain) que permite consultas em linguagem natural diretamente sobre os resultados processados.

🛠️ Tecnologias Utilizadas

Python 3.10+

Pandas → Manipulação e análise de dados.

OpenPyXL → Leitura e escrita em arquivos Excel.

LangChain + LangChain-Experimental → Criação de agentes inteligentes.

Google Generative AI (Gemini 1.5) → LLM usado no agente.

dotenv → Gerenciamento de variáveis de ambiente.

📂 Estrutura do Projeto
📁 Grupo-278-I2A2
│── main.py                 # Script principal do fluxo
│── processamento.py         # Funções de carregamento, consolidação e cálculo
│── agente.py                # Agente LLM para consultas em linguagem natural
│── .env                     # Configurações sensíveis (API keys) - NÃO subir no GitHub
│── .gitignore               # Arquivos e pastas ignorados no versionamento
│── requirements.txt         # Dependências do projeto
│
📁 dados/
│   ├── Desafio 4 - Dados.zip         # Base original (diversas planilhas)
│   ├── VR_MENSAL_CALCULADO.xlsx      # Resultado consolidado com VR calculado
│
📁 temp/                   # Arquivos temporários (se necessário)


Fluxo do Projeto

Carregamento das bases a partir do .zip com planilhas de colaboradores.

Consolidação das informações em um único DataFrame.

Aplicação de regras de exclusão: desligados, afastados, estagiários, aprendizes e exterior.

Cálculo de dias úteis para cada colaborador (descontando férias e afastamentos).

Integração com a tabela de sindicatos → definição do valor unitário do VR.

Cálculo do VR mensal (empresa 80% / colaborador 20%).

Exportação final para VR_MENSAL_CALCULADO.xlsx.

Agente LLM: permite perguntas em linguagem natural sobre os resultados.

🤖 Agente LLM

O agente é construído com LangChain + Gemini, possibilitando consultas sobre a planilha final.

Exemplos de perguntas que podem ser feitas:

"Qual foi o valor total de VR para a empresa?"

"Quantos colaboradores receberam VR no sindicato SINDPD SP?"

"Explique em linguagem simples o cálculo do colaborador de matrícula 32104."

⚙️ Configuração do Ambiente

1. Clone o repositório
git clone https://github.com/SEU_USUARIO/Grupo-278-I2A2.git
cd Grupo-278-I2A2

2. Crie o ambiente virtual
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

3. Instale as dependências
pip install -r requirements.txt

4. Configure as variáveis de ambiente
Crie um arquivo .env com:
GOOGLE_API_KEY=SEU_API_KEY_AQUI

5. Execute o fluxo de processamento
python main.py

6. Rode o agente
python agente.py

📊 Exemplo de Saída (main.py)
Arquivos encontrados no ZIP: ['ATIVOS.xlsx', 'DESLIGADOS.xlsx', ...]
[DEBUG] Base consolidada criada!
[DEBUG] Exclusões aplicadas: 23 colaboradores removidos
[DEBUG] Dias úteis calculados!
[DEBUG] Valores de VR calculados!

--- BASE FINAL COM VR ---
   MATRICULA       TITULO DO CARGO        VR_EMPRESA   VR_COLABORADOR
0      34941      TECH RECRUITER II        660.0          165.0
1      24401 COORDENADOR ADMINISTRATIVO    588.0          147.0
...
Total colaboradores com VR: 1875

📊 Exemplo de Consulta (agente.py)
❓ Pergunta: Qual foi o valor total de VR para a empresa?
💡 Resposta: O valor total de VR pago pela empresa foi R$ 1.102.500,00.


