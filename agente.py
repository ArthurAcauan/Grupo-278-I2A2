import os
import pandas as pd
from dotenv import load_dotenv
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_google_genai import ChatGoogleGenerativeAI

# 1. Carrega variáveis de ambiente
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("❌ GOOGLE_API_KEY não encontrada no .env")

# 2. Carrega a base final (exportada pelo processamento.py)
CAMINHO_PLANILHA = "dados/VR_MENSAL_CALCULADO.xlsx"
df_final = pd.read_excel(CAMINHO_PLANILHA)

print(f"[DEBUG] Planilha carregada com {len(df_final)} registros e {len(df_final.columns)} colunas.")

# 3. Inicializa o modelo Gemini
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",  # pode trocar por gemini-1.5-pro
    temperature=0,
    google_api_key=GOOGLE_API_KEY,
)

# 4. Cria agente em cima do dataframe
agent = create_pandas_dataframe_agent(
    llm,
    df_final,
    verbose=True,
    allow_dangerous_code=True  # necessário para pandas mais avançado
)

# 5. Função para interagir
def perguntar(pergunta: str):
    print(f"\n❓ Pergunta: {pergunta}")
    resposta = agent.run(pergunta)
    print(f"💡 Resposta: {resposta}\n")
    return resposta

# 6. Exemplos de perguntas
if __name__ == "__main__":
    perguntar("Qual foi o valor total de VR para a empresa?")
    perguntar("Quantos colaboradores receberam VR no sindicato SINDPD SP?")
    perguntar("Explique em linguagem simples o cálculo do colaborador de matrícula 32104.")