import pandas as pd
import zipfile
import os


# ========================
# Carga das planilhas
# ========================
def carregar_bases(caminho_zip):
    pasta_temp = "dados/temp"
    os.makedirs(pasta_temp, exist_ok=True)

    with zipfile.ZipFile(caminho_zip, "r") as zip_ref:
        zip_ref.extractall(pasta_temp)

    arquivos = os.listdir(pasta_temp)
    print("Arquivos encontrados no ZIP:", arquivos)

    df_ativos = pd.read_excel(os.path.join(pasta_temp, "ATIVOS.xlsx"))
    df_ferias = pd.read_excel(os.path.join(pasta_temp, "FÉRIAS.xlsx"))
    df_desligados = pd.read_excel(os.path.join(pasta_temp, "DESLIGADOS.xlsx"))
    df_admitidos = pd.read_excel(os.path.join(pasta_temp, "ADMISSÃO ABRIL.xlsx"))
    df_sindicato_valores = pd.read_excel(os.path.join(pasta_temp, "Base sindicato x valor.xlsx"))
    df_dias_uteis = pd.read_excel(os.path.join(pasta_temp, "Base dias uteis.xlsx"))
    df_estagio = pd.read_excel(os.path.join(pasta_temp, "ESTÁGIO.xlsx"))
    df_aprendiz = pd.read_excel(os.path.join(pasta_temp, "APRENDIZ.xlsx"))
    df_afastamentos = pd.read_excel(os.path.join(pasta_temp, "AFASTAMENTOS.xlsx"))
    df_exterior = pd.read_excel(os.path.join(pasta_temp, "EXTERIOR.xlsx"))

    return {
        "ativos": df_ativos,
        "ferias": df_ferias,
        "desligados": df_desligados,
        "admitidos": df_admitidos,
        "sindicato_valores": df_sindicato_valores,
        "dias_uteis": df_dias_uteis,
        "estagio": df_estagio,
        "aprendiz": df_aprendiz,
        "afastamentos": df_afastamentos,
        "exterior": df_exterior,
    }


# ========================
# Consolidação
# ========================
def consolidar_bases(bases: dict) -> pd.DataFrame:
    df_ativos = bases["ativos"].copy()
    df_admitidos = bases["admitidos"].copy()

    # Padroniza nomes
    if "Admissão" in df_admitidos.columns:
        df_admitidos = df_admitidos.rename(
            columns={"Admissão": "DATA_ADMISSAO", "Cargo": "TITULO DO CARGO"}
        )
    if "DATA ADMISSAO" in df_ativos.columns:
        df_ativos = df_ativos.rename(columns={"DATA ADMISSAO": "DATA_ADMISSAO"})

    df_ativos["STATUS"] = "ATIVO"
    df_admitidos["STATUS"] = "ADMITIDO"

    df_base = pd.concat([df_ativos, df_admitidos], ignore_index=True)

    print("\n[DEBUG] Base consolidada criada!")
    print("Colunas disponíveis:", list(df_base.columns))
    print("Total de registros:", len(df_base))
    return df_base


# ========================
# Exclusões
# ========================
def aplicar_regras_exclusao(bases: dict, df_base: pd.DataFrame) -> pd.DataFrame:
    df = df_base.copy()

    def get_matriculas(df_sub):
        if df_sub is None:
            return set()
        # Normaliza qualquer coluna que contenha "MATRIC"
        df_sub = df_sub.rename(
            columns={col: "MATRICULA" for col in df_sub.columns if "MATRIC" in col.upper()}
        )
        if "MATRICULA" in df_sub.columns:
            return set(df_sub["MATRICULA"].astype(str))
        return set()

    matriculas_excluir = set()
    matriculas_excluir |= get_matriculas(bases.get("estagio"))
    matriculas_excluir |= get_matriculas(bases.get("aprendiz"))
    matriculas_excluir |= get_matriculas(bases.get("afastamentos"))
    matriculas_excluir |= get_matriculas(bases.get("exterior"))

    # Diretores pelo cargo
    mask_diretor = df["TITULO DO CARGO"].str.contains("DIRETOR", case=False, na=False)
    matriculas_excluir |= set(df.loc[mask_diretor, "MATRICULA"].astype(str))

    df_filtrada = df[~df["MATRICULA"].astype(str).isin(matriculas_excluir)].copy()

    print(f"\n[DEBUG] Exclusões aplicadas: {len(df) - len(df_filtrada)} colaboradores removidos")
    print("Total após exclusões:", len(df_filtrada))
    return df_filtrada


# ========================
# Cálculo de dias úteis
# ========================
def _preparar_dias_uteis(df_dias_raw: pd.DataFrame) -> pd.DataFrame:
    """
    A planilha 'Base dias uteis.xlsx' vem com os nomes nas 2 primeiras colunas,
    e a primeira linha traz os rótulos 'SINDICADO' / 'DIAS UTEIS'.
    Deixamos no formato: Sindicato | DIAS_UTEIS (numérico)
    """
    df = df_dias_raw.copy().iloc[:, :2]
    df.columns = ["Sindicato", "DIAS_UTEIS"]

    # Se a primeira linha contém "SINDICADO", tratamos como cabeçalho embutido
    if isinstance(df.iloc[0, 0], str) and "SIND" in df.iloc[0, 0].upper():
        df = df.iloc[1:, :]

    df = df.dropna(subset=["Sindicato"])
    df["Sindicato"] = df["Sindicato"].astype(str).str.strip()
    df["DIAS_UTEIS"] = pd.to_numeric(df["DIAS_UTEIS"], errors="coerce")
    return df


def calcular_dias_uteis(df_base: pd.DataFrame, bases: dict) -> pd.DataFrame:
    """
    Calcula os dias úteis de VR por colaborador considerando:
    - Dias úteis do sindicato
    - Férias
    - Admissão (proporcional)
    - Desligamento (regra do dia 15 com comunicado 'OK', senão proporcional)
    """
    df = df_base.copy()

    # --- Dias úteis por sindicato ---
    df_dias = _preparar_dias_uteis(bases["dias_uteis"])
    df = df.merge(df_dias, on="Sindicato", how="left")

    # --- Férias ---
    df_ferias = bases["ferias"].copy()
    df_ferias = df_ferias.rename(
        columns={col: "MATRICULA" for col in df_ferias.columns if "MATRIC" in col.upper()}
    )
    ferias_col = next(
        (c for c in df_ferias.columns if "FÉRIA" in c.upper() or "FERIA" in c.upper()), None
    )
    if ferias_col:
        df_ferias = df_ferias[["MATRICULA", ferias_col]].rename(columns={ferias_col: "FERIAS"})
        df = df.merge(df_ferias, on="MATRICULA", how="left")
    if "FERIAS" not in df.columns:
        df["FERIAS"] = 0
    df["FERIAS"] = pd.to_numeric(df["FERIAS"], errors="coerce").fillna(0)

    # --- Desligados ---
    df_desl = bases["desligados"].copy()
    df_desl = df_desl.rename(
        columns={col: "MATRICULA" for col in df_desl.columns if "MATRIC" in col.upper()}
    )
    dem_col = next((c for c in df_desl.columns if "DEMI" in c.upper()), None)
    com_col = next((c for c in df_desl.columns if "COMUNICADO" in c.upper()), None)

    if dem_col:
        df_desl = df_desl.rename(columns={dem_col: "DATA_DEMISSAO"})
    else:
        df_desl["DATA_DEMISSAO"] = pd.NaT

    if com_col:
        df_desl = df_desl.rename(columns={com_col: "COMUNICADO_DE_DESLIGAMENTO"})
    else:
        df_desl["COMUNICADO_DE_DESLIGAMENTO"] = pd.NA

    # Mantém apenas o necessário
    if "MATRICULA" in df_desl.columns:
        df = df.merge(
            df_desl[["MATRICULA", "DATA_DEMISSAO", "COMUNICADO_DE_DESLIGAMENTO"]],
            on="MATRICULA",
            how="left",
        )

    # Garante colunas mesmo se não houver merge
    if "DATA_DEMISSAO" not in df.columns:
        df["DATA_DEMISSAO"] = pd.NaT
    if "COMUNICADO_DE_DESLIGAMENTO" not in df.columns:
        df["COMUNICADO_DE_DESLIGAMENTO"] = pd.NA

    # --- Cálculo base: dias sindicato - férias ---
    df["DIAS_UTEIS"] = pd.to_numeric(df["DIAS_UTEIS"], errors="coerce").fillna(0)
    df["DIAS_CALCULADOS"] = (df["DIAS_UTEIS"] - df["FERIAS"]).clip(lower=0)

    # --- Admissão (proporção do mês) ---
    if "DATA_ADMISSAO" in df.columns:
        df["DATA_ADMISSAO"] = pd.to_datetime(df["DATA_ADMISSAO"], errors="coerce")
        # Proporcional apenas para quem é ADMITIDO e tem data válida
        mask_adm = (df["STATUS"] == "ADMITIDO") & df["DATA_ADMISSAO"].notna()
        dias_mes_adm = df.loc[mask_adm, "DATA_ADMISSAO"].dt.days_in_month
        fator_adm = (dias_mes_adm - df.loc[mask_adm, "DATA_ADMISSAO"].dt.day + 1) / dias_mes_adm
        df.loc[mask_adm, "DIAS_CALCULADOS"] = (df.loc[mask_adm, "DIAS_CALCULADOS"] * fator_adm).round()

    # --- Desligamento ---
    df["DATA_DEMISSAO"] = pd.to_datetime(df["DATA_DEMISSAO"], errors="coerce")
    df["COMUNICADO_DE_DESLIGAMENTO"] = df["COMUNICADO_DE_DESLIGAMENTO"].astype(str)

    mask_desl = df["DATA_DEMISSAO"].notna()
    dias_mes_desl = df.loc[mask_desl, "DATA_DEMISSAO"].dt.days_in_month
    dia_desl = df.loc[mask_desl, "DATA_DEMISSAO"].dt.day

    # Comunicação OK até dia 15 => zera
    mask_ok15 = mask_desl & (dia_desl <= 15) & (df.loc[mask_desl, "COMUNICADO_DE_DESLIGAMENTO"].str.upper() == "OK")
    df.loc[mask_ok15, "DIAS_CALCULADOS"] = 0

    # Senão, proporcional até o dia do desligamento
    mask_prop = mask_desl & ~mask_ok15
    fator_desl = (dia_desl / dias_mes_desl)
    df.loc[mask_prop, "DIAS_CALCULADOS"] = (df.loc[mask_prop, "DIAS_CALCULADOS"] * fator_desl).round()

    # Sanitiza
    df["DIAS_CALCULADOS"] = pd.to_numeric(df["DIAS_CALCULADOS"], errors="coerce").fillna(0).astype(int)

    print("\n[DEBUG] Dias úteis calculados!")
    return df

def calcular_valores_vr(df_base: pd.DataFrame, bases: dict) -> pd.DataFrame:
    df = df_base.copy()

    df_valores = bases["sindicato_valores"].copy()
    df_valores = df_valores.rename(
        columns={col: "ESTADO" for col in df_valores.columns if "ESTADO" in col.upper()}
    )
    val_col = next((c for c in df_valores.columns if "VALOR" in c.upper()), None)
    if val_col:
        df_valores = df_valores.rename(columns={val_col: "VR_VALOR"})
    else:
        df_valores["VR_VALOR"] = 0

    # Extrair UF do sindicato
    df["UF"] = df["Sindicato"].str.extract(r"\b(SP|RS|RJ|PR)\b", expand=False)

    # Mapear para nomes completos
    map_estado = {
        "SP": "São Paulo",
        "RJ": "Rio de Janeiro",
        "RS": "Rio Grande do Sul",
        "PR": "Paraná"
    }
    df["ESTADO"] = df["UF"].map(map_estado)

    # Merge
    df = df.merge(df_valores[["ESTADO", "VR_VALOR"]], on="ESTADO", how="left")

    # Cálculos finais
    df["VR_TOTAL"] = df["DIAS_CALCULADOS"] * df["VR_VALOR"]
    df["VR_EMPRESA"] = (df["VR_TOTAL"] * 0.8).round(2)
    df["VR_COLABORADOR"] = (df["VR_TOTAL"] * 0.2).round(2)

    print("\n[DEBUG] Valores de VR calculados!")
    return df

def exportar_planilha_final(df_vr: pd.DataFrame, caminho_saida: str = "dados/VR MENSAL 05.2025.xlsx"):
    """
    Exporta a base final no layout esperado da planilha 'VR MENSAL 05.2025'.
    Esse já é o nome obrigatório da entrega.
    """
    df_final = pd.DataFrame({
        "MATRICULA": df_vr["MATRICULA"],
        "NOME/CARGO": df_vr["TITULO DO CARGO"],
        "SINDICATO": df_vr["Sindicato"],
        "DIAS ÚTEIS": df_vr["DIAS_CALCULADOS"],
        "VALOR UNITÁRIO": df_vr["VR_VALOR"],
        "VR TOTAL": df_vr["VR_TOTAL"],
        "EMPRESA (80%)": df_vr["VR_EMPRESA"],
        "COLABORADOR (20%)": df_vr["VR_COLABORADOR"],
    })

    # Salvar diretamente no nome exigido
    df_final.to_excel(caminho_saida, index=False)
    print(f"\n[DEBUG] Planilha final exportada para: {caminho_saida}")
    return df_final