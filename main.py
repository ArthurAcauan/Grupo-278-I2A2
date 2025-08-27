from processamento import (
    carregar_bases,
    consolidar_bases,
    aplicar_regras_exclusao,
    calcular_dias_uteis,
    calcular_valores_vr,
    exportar_planilha_final,
)

# 1) Carrega tudo
bases = carregar_bases("dados/Desafio 4 - Dados.zip")

# 2) Consolida ativos + admitidos
df_base = consolidar_bases(bases)

# 3) Aplica exclusões
df_filtrada = aplicar_regras_exclusao(bases, df_base)

# 4) Calcula dias úteis
df_dias = calcular_dias_uteis(df_filtrada, bases)

# 5) Calcula valores VR
df_vr = calcular_valores_vr(df_dias, bases)

# 6) Exporta planilha final
df_final = exportar_planilha_final(df_vr)

print("\n--- AMOSTRA DA PLANILHA FINAL ---")
print(df_final.head(20))