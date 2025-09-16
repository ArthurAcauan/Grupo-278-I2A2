import pandas as pd
import os

# Arquivos
entrada = "dados/VR_MENSAL_CALCULADO.xlsx"
saida_corrigida = "dados/VR MENSAL 05.2025.xlsx"

print("[INFO] Carregando planilha gerada pelo processamento...")
df = pd.read_excel(entrada)
print(f"[DEBUG] Planilha carregada com {len(df)} registros e {len(df.columns)} colunas.")

# ====== 1. Mapear valores padrão por UF ======
map_valor_padrao = {
    "SP": 37.5,
    "RS": 35.0,
    "RJ": 33.0,
    "PR": 32.0
}

# Extrair UF a partir do sindicato
df["UF"] = df["SINDICATO"].str.extract(r"\b(SP|RS|RJ|PR)\b", expand=False)

# ====== 2. Preencher VALOR UNITÁRIO ======
# Usa valor existente, senão tenta usar VR_VALOR, senão usa o padrão da UF
df["VALOR UNITÁRIO"] = (
    df["VALOR UNITÁRIO"]
    .fillna(df["VALOR UNITÁRIO"].mode()[0])   # preenche nulos com valor mais comum
    .round(2)
)

# ====== 3. Recalcular valores ======
df["VR TOTAL"] = (df["DIAS ÚTEIS"].fillna(0) * df["VALOR UNITÁRIO"]).round(2)
df["EMPRESA (80%)"] = (df["VR TOTAL"] * 0.8).round(2)
df["COLABORADOR (20%)"] = (df["VR TOTAL"] * 0.2).round(2)

# ====== 4. Garantir que não existam negativos ======
for col in ["DIAS ÚTEIS", "VALOR UNITÁRIO", "VR TOTAL", "EMPRESA (80%)", "COLABORADOR (20%)"]:
    df[col] = df[col].clip(lower=0)

# ====== 5. Salvar no formato exigido ======
df = df.drop(columns=["UF"], errors="ignore")  # coluna auxiliar não entra na planilha final
df.to_excel(saida_corrigida, index=False)

print(f"[INFO] Planilha corrigida salva em: {saida_corrigida}")
print("Registros:", len(df))
print("Total VR:", df["VR TOTAL"].sum())
