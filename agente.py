import os
import pandas as pd
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent

# Carregar variáveis do ambiente (.env)
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("❌ GOOGLE_API_KEY não encontrada no .env")

# Inicializar LLM (Gemini)
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0,
    google_api_key=GOOGLE_API_KEY
)

# Carregar planilha final processada
df = pd.read_excel("dados/VR MENSAL 05.2025.xlsx")
print(f"[DEBUG] Planilha carregada com {len(df)} registros e {len(df.columns)} colunas.")

# Criar agente especializado em DataFrame
agent = create_pandas_dataframe_agent(
    llm,
    df,
    verbose=True,
    allow_dangerous_code=True
)

# Prompt inicial fixo para evitar alucinações
instructions = """
Você é um analista de RH que responde perguntas sobre a base de VR.

📊 Colunas disponíveis no DataFrame:
['MATRICULA', 'NOME/CARGO', 'SINDICATO', 'DIAS ÚTEIS', 'VALOR UNITÁRIO',
 'VR TOTAL', 'EMPRESA (80%)', 'COLABORADOR (20%)']

📌 Regras de resposta:
1. Sempre use apenas os dados do DataFrame carregado (VR MENSAL 05.2025.xlsx).
2. Nunca crie DataFrames fictícios ou invente valores.
3. Trabalhe diretamente com as colunas listadas acima.
4. Se a pergunta envolver cálculos (soma, média, contagem etc.), mostre:
   - 🔢 O resultado numérico exato.
   - 📖 Uma breve explicação de como o cálculo foi feito.
5. Se a pergunta for sobre um colaborador específico, mostre seus dados e explique.
6. Responda em português claro e objetivo.
"""

print("\n🤖 Agente pronto! Faça suas perguntas. Digite 'sair' para encerrar.\n")

# Loop interativo
while True:
    pergunta = input("❓ Pergunta: ")
    if pergunta.lower() in ["sair", "exit", "quit"]:
        print("👋 Encerrando agente...")
        break

    try:
        resposta = agent.invoke(instructions + "\n\nPergunta: " + pergunta)
        print("\n💡 Resposta:", resposta["output"])
    except Exception as e:
        print("⚠️ Erro ao processar pergunta:", e)
