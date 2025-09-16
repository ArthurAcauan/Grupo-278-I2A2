# agente_validacao.py
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

# LLM
from langchain_google_genai import ChatGoogleGenerativeAI

# ---------- CONFIG ----------
GENERATED_PATH = "dados/VR_MENSAL_CALCULADO.xlsx"  # saída do processamento
TEMPLATE_PATH = "dados/VR MENSAL 05.2025.xlsx"     # modelo original (se disponível)
FINAL_OUTPUT_PATH = "dados/VR MENSAL 05.2025.xlsx" # nome exigido
DIAG_CSV = "dados/diag_validacao.csv"
RELATORIO_MD = "dados/relatorio_entrega.md"

# Se o professor indicou um total esperado, configure aqui:
EXPECTED_TOTAL_VR = 1380178.00
TOTAL_TOLERANCE_PCT = 0.02  # tolerância percentual (2%) ao comparar com EXPECTED_TOTAL_VR
# ----------------------------

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("⚠️ GOOGLE_API_KEY não encontrada no .env. O LLM não poderá gerar o relatório.")
# Inicializa LLM (só usado para texto do relatório; validação é feita com pandas)
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0, google_api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None

def read_sheet(path):
    if not os.path.exists(path):
        return None
    return pd.read_excel(path)

def parse_number_like(s):
    """Tenta transformar strings numéricas com pontuação BR/EN em float.
    Lógica robusta para pontos como milhares e vírgulas como decimais."""
    if pd.isna(s):
        return np.nan
    if isinstance(s, (int, float, np.number)):
        return float(s)
    s = str(s).strip()
    if s == "":
        return np.nan
    s = s.replace(" ", "")
    # casos: "1.234,56" -> remove '.' e substitui ',' por '.'
    if "." in s and "," in s:
        if s.find(".") < s.find(","):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    # remove qualquer caractere que não seja dígito, sinal ou ponto
    import re
    m = re.search(r"-?\d+(\.\d+)?", s)
    if not m:
        return np.nan
    try:
        return float(m.group(0))
    except:
        return np.nan

def try_convert_columns(df, cols):
    """Tenta converter colunas listadas para numérico usando parse_number_like.
       Retorna dict com alterações (antes->depois counts)."""
    changes = {}
    for c in cols:
        if c not in df.columns:
            changes[c] = {"status": "missing"}
            continue
        before_non_numeric = df[c].apply(lambda x: not pd.isna(x) and not isinstance(x, (int, float, np.number))).sum()
        df[c + "__orig"] = df[c]  # guarda original para auditoria
        df[c] = df[c].apply(parse_number_like)
        after_non_numeric = df[c].isna().sum()
        changes[c] = {
            "status": "converted",
            "before_non_numeric": int(before_non_numeric),
            "after_na_count": int(after_non_numeric),
            "nan_positions_sample": df[df[c].isna()].head(3).index.tolist()
        }
    return changes

def validate_and_fix(df, template_cols=None):
    """Valida dataframe e aplica correções possíveis. Retorna (df_fixed, diagnostics)."""
    diag = {}
    df = df.copy()

    # 1) Colunas do template
    diag['template_present'] = bool(template_cols)
    if template_cols:
        # colunas faltando
        missing = [c for c in template_cols if c not in df.columns]
        extra = [c for c in df.columns if c not in template_cols]
        diag['missing_columns'] = missing
        diag['extra_columns'] = extra
        # Reordenar / preencher colunas faltantes com NaN
        if missing:
            for c in missing:
                df[c] = np.nan
        # Reordena para match do template (mantendo extras no final)
        ordered_cols = [c for c in template_cols if c in df.columns] + [c for c in df.columns if c not in template_cols]
        df = df[ordered_cols]
    else:
        diag['missing_columns'] = []
        diag['extra_columns'] = []

    # 2) Normalize whitespace in column names
    df.columns = [str(c).strip() for c in df.columns]

    # 3) Colunas que devem ser numéricas (heurística)
    numeric_candidates = []
    for col in df.columns:
        if any(k in col.upper() for k in ["VALOR", "VR TOTAL", "EMPRESA", "COLABORADOR", "DIAS"]):
            numeric_candidates.append(col)

    diag['numeric_candidates'] = numeric_candidates

    # 4) Converter números (attempt)
    conv_report = try_convert_columns(df, numeric_candidates)
    diag['conversion_report'] = conv_report

    # 5) Verifica negativos e nulos essenciais
    issues = {}
    # Essenciais: MATRICULA, DIAS, VALOR UNITÁRIO, VR TOTAL
    essentials = []
    for c in df.columns:
        cu = c.upper()
        if "MATRIC" in cu:
            essentials.append(c)
        if cu in ["DIAS ÚTEIS", "DIAS UTEIS", "DIAS_UTEIS"] and c not in essentials:
            essentials.append(c)
        if "VALOR" in cu and "UNIT" in cu:
            essentials.append(c)
        if "VR TOTAL" in cu or "VR_TOTAL" in cu:
            essentials.append(c)
    essentials = list(dict.fromkeys(essentials))
    diag['essentials'] = essentials

    # nulos essencias
    nulls = {c: int(df[c].isna().sum()) for c in essentials if c in df.columns}
    diag['nulls_essenciais'] = nulls

    # negativos nas colunas numéricas
    negs = {}
    for c in numeric_candidates:
        if c in df.columns:
            try:
                negs[c] = int((df[c] < 0).sum())
            except Exception:
                negs[c] = "error"
    diag['negatives'] = negs

    # 6) Totais
    total_vr_col = next((c for c in df.columns if "VR TOTAL" in c.upper() or "VR_TOTAL" in c.upper()), None)
    total_empresa_col = next((c for c in df.columns if "EMPRESA" in c.upper() and "80" in c), None)
    total_colab_col = next((c for c in df.columns if "COLABORADOR" in c.upper() and "20" in c), None)

    total_vr = float(df[total_vr_col].sum()) if total_vr_col and total_vr_col in df.columns else None
    total_emp = float(df[total_empresa_col].sum()) if total_empresa_col and total_empresa_col in df.columns else None
    total_col = float(df[total_colab_col].sum()) if total_colab_col and total_colab_col in df.columns else None
    diag['totals'] = {'total_vr': total_vr, 'total_empresa': total_emp, 'total_colaborador': total_col}

    # 7) Comparar com expected
    if total_vr is not None and EXPECTED_TOTAL_VR:
        diff = total_vr - EXPECTED_TOTAL_VR
        pct = abs(diff) / EXPECTED_TOTAL_VR
        diag['expected_total_check'] = {'expected': EXPECTED_TOTAL_VR, 'actual': total_vr, 'diff': diff, 'pct_diff': pct, 'ok': pct <= TOTAL_TOLERANCE_PCT}
    else:
        diag['expected_total_check'] = None

    # 8) Preparar relatório de linhas com problemas (nulos ou negativos)
    problem_rows = pd.DataFrame()
    # qualquer linha com nulo em essenciais
    essential_mask = False
    for c in essentials:
        if c in df.columns:
            essential_mask = essential_mask | df[c].isna()
    if essential_mask is not False:
        problem_rows = df[essential_mask].copy()
    # quaisquer negativos
    neg_mask = False
    for c in numeric_candidates:
        if c in df.columns:
            neg_mask = neg_mask | (df[c] < 0)
    if neg_mask is not False:
        problem_rows = pd.concat([problem_rows, df[neg_mask]], axis=0).drop_duplicates()

    diag['problem_rows_count'] = len(problem_rows)
    # salvar amostra diagnóstica
    if not problem_rows.empty:
        problem_rows.head(200).to_csv(DIAG_CSV, index=False)

    return df, diag, problem_rows

def produce_markdown_report(diag, llm_summary=None, group_name="Grupo X", members=None, solution_diagram_path=None):
    """Gera markdown a partir do diagnóstico e, se houver, anexos do LLM."""
    members = members or ["Integrante 1", "Integrante 2"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md = []
    md.append(f"# Relatório de Validação - Entrega Desafio 4\n\n**Data:** {now}\n\n")
    md.append("## 1 — Resumo executivo\n")
    md.append(f"- Grupo: **{group_name}**\n")
    md.append(f"- Componentes: {', '.join(members)}\n")
    md.append("\n### Resultado da validação\n")
    md.append(f"- Totais encontrados: {diag.get('totals')}\n")
    et = diag.get('expected_total_check')
    if et:
        ok_txt = "OK" if et['ok'] else "Fora da tolerância"
        md.append(f"- Comparação com total esperado: esperado={et['expected']}, atual={et['actual']}, diff={et['diff']} ({et['pct_diff']*100:.2f}%) → **{ok_txt}**\n")
    md.append(f"- Problemas detectados: {diag.get('problem_rows_count')} linhas com anomalias (arquivo {DIAG_CSV} salvo com amostra)\n")
    if llm_summary:
        md.append("\n## 2 — Sumário gerado pelo agente LLM\n")
        md.append(llm_summary + "\n")
    md.append("\n## 3 — Ações automatizadas executadas\n")
    md.append("- Conversão de formatos numéricos (vírgula/ponto) nas colunas candidatas.\n")
    md.append("- Preenchimento de colunas que faltavam no template (com NaN) e reordenação para o layout do template.\n")
    md.append("\n## 4 — Instruções para envio\n")
    md.append(f"- Arquivo final salvo em: `{FINAL_OUTPUT_PATH}`\n")
    md.append(f"- Relatório gerado: `{RELATORIO_MD}`\n")
    md.append(f"- Diagnóstico amostral: `{DIAG_CSV}`\n")
    md.append("\n## 5 — Onde o agente foi usado\n")
    md.append("- Validação de consistência de dados (pandas).\n- Geração do texto do relatório e explicações (LLM Gemini).\n")
    md.append("\n## 6 — Observações finais\n")
    md.append("- Verifique manualmente linhas listadas em `diag_validacao.csv` antes do envio.\n")
    return "\n".join(md)

def generate_llm_summary(diag):
    if llm is None:
        return None
    # Cria prompt curto com diagnóstico para o LLM sintetizar em linguagem natural
    prompt = f"""
Você é um analista de QA de dados. Recebi o seguinte diagnóstico (dicionário JSON) sobre a planilha final de VR:
{diag}

Por favor, gere um resumo em português (2-4 parágrafos) explicando:
- O que foi verificado
- Principais problemas detectados
- Ações que o time deve tomar antes da submissão final (passos práticos)
Responda em português.
"""
    res = llm.invoke(prompt)
    # a API retorna um objeto com .content (string)
    try:
        text = res.content if hasattr(res, "content") else str(res)
    except:
        text = str(res)
    return text

def main():
    print("[INFO] Carregando planilha gerada pelo processamento...")
    df_gen = read_sheet(GENERATED_PATH)
    if df_gen is None:
        print(f"⛔ Arquivo gerado não encontrado em {GENERATED_PATH}. Rode o processamento primeiro.")
        sys.exit(1)

    print(f"[DEBUG] Planilha carregada com {len(df_gen)} registros e {len(df_gen.columns)} colunas.")

    # tenta carregar template (opcional)
    template_df = read_sheet(TEMPLATE_PATH)
    template_cols = None
    if template_df is not None:
        template_cols = list(template_df.columns)
        print("[INFO] Template encontrado. Usarei o layout deste template para reordenar/validar.")

    # Roda validação/fix
    df_fixed, diag, problem_rows = validate_and_fix(df_gen, template_cols=template_cols)

    # gera resumo via LLM (opcional)
    llm_summary = None
    if GOOGLE_API_KEY:
        try:
            llm_summary = generate_llm_summary({k: v for k, v in diag.items() if k != 'conversion_report'})
        except Exception as e:
            print("⚠️ Erro ao gerar sumário com LLM:", e)

    # produce markdown report
    md = produce_markdown_report(diag, llm_summary=llm_summary, group_name="Grupo-278-I2A2", members=["Arthur Acauan", "..."])
    with open(RELATORIO_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[INFO] Relatório salvo em {RELATORIO_MD}")

    # salva arquivo final com nome e layout exigidos
    # garante que colunas do template (se houver) venham primeiro
    if template_cols:
        cols_final = [c for c in template_cols if c in df_fixed.columns] + [c for c in df_fixed.columns if c not in (template_cols or [])]
    else:
        cols_final = df_fixed.columns.tolist()
    df_to_save = df_fixed[cols_final]
    # salva como excel (numéricos mantidos como numéricos)
    df_to_save.to_excel(FINAL_OUTPUT_PATH, index=False)
    print(f"[INFO] Arquivo final salvo como {FINAL_OUTPUT_PATH}")

    # salva diagnóstico completo
    diag_path = DIAG_CSV
    try:
        # converter diag conversion_report para DF resumido
        conv_summ = []
        for col, info in diag.get('conversion_report', {}).items():
            row = {'column': col}
            row.update((info if isinstance(info, dict) else {'status': info}))
            conv_summ.append(row)
        pd.DataFrame(conv_summ).to_csv(diag_path, index=False)
        print(f"[INFO] Diagnóstico salvo em {diag_path}")
    except Exception as e:
        print("⚠️ Não foi possível salvar diagnóstico resumido:", e)

    # Se houver problemas críticos (linhas com NULLs ou negativos), retorna código 2
    critical = False
    if diag.get('problem_rows_count', 0) > 0:
        critical = True

    if critical:
        print("❗ Foram detectadas anomalias. Revise 'diag_validacao.csv' e o relatório antes de submeter.")
        sys.exit(2)
    else:
        print("✅ Validação final OK. Pronto para submissão.")
        sys.exit(0)

if __name__ == "__main__":
    main()
