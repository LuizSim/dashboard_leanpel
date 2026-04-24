import os
import pandas as pd
from supabase import create_client
from datetime import datetime

# ── CONFIGURAÇÕES ─────────────────────────────────────────────────────
URL = "https://oxpecakuswuvjpeddisi.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im94cGVjYWt1c3d1dmpwZWRkaXNpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY1NTI0NTcsImV4cCI6MjA5MjEyODQ1N30.uLkCoikYJykAZR8dkaGawzv0LM9gBFVAm2LbbObySTc"

NOME_ARQUIVO = "Avaliação.csv"

COLUNAS_NOTAS = {
    "atendimento": "Atendimento",
    "espera":      "Tempo de Espera",
    "produtos":    "Produtos",
    "higiene":     "Higiene",
    "ambiente":    "Ambiente",
    "precos":      "Preços",
}
# ─────────────────────────────────────────────────────────────────────

def cor_terminal(nota):
    try:
        n = float(nota)
    except (TypeError, ValueError):
        return str(nota)
    if n >= 8:
        return f"\033[92m{nota}\033[0m"
    elif n >= 5:
        return f"\033[93m{nota}\033[0m"
    else:
        return f"\033[91m{nota}\033[0m"

def extrair_dados():
    try:
        print("Conectando ao Supabase...")
        supabase = create_client(URL, KEY)

        response = supabase.table("leanpel_feedbacks").select("*").execute()

        if not response.data:
            print("AVISO: Nenhum dado encontrado no banco.")
            return

        df = pd.DataFrame(response.data)

        # Ordenar por data crescente
        df["criado_em"] = pd.to_datetime(df["criado_em"])
        df = df.sort_values(by="criado_em", ascending=True)
        df["criado_em"] = df["criado_em"].dt.strftime("%d/%m/%Y %H:%M")

        # Renomear colunas
        rename_map = {
            "nome":       "Nome do Cliente",
            "criado_em":  "Data e Hora",
            "media":      "Média Geral",
            "comentario": "Comentário",
        }
        rename_map.update({k: v for k, v in COLUNAS_NOTAS.items()})
        df = df.rename(columns=rename_map)

        # Remover ID
        if "id" in df.columns:
            df = df.drop(columns=["id"])

        # Ordem das colunas
        ordem = (
            ["Nome do Cliente", "Data e Hora"]
            + list(COLUNAS_NOTAS.values())
            + ["Média Geral", "Comentário"]
        )
        ordem = [c for c in ordem if c in df.columns]
        df = df[ordem]

        # ── VERIFICAR SE O ARQUIVO JÁ EXISTE ─────────────────────────
        if os.path.exists(NOME_ARQUIVO):
            print(f"Arquivo '{NOME_ARQUIVO}' encontrado — atualizando...")
            acao = "atualizado"
        else:
            print(f"Arquivo '{NOME_ARQUIVO}' não encontrado — criando...")
            acao = "criado"

        # Salva (sobrescreve ou cria)
        df.to_csv(NOME_ARQUIVO, index=False, sep=";", encoding="utf-8-sig")

        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        print(f"\nSUCESSO! Arquivo '{NOME_ARQUIVO}' {acao} em {agora}")
        print(f"Total de registros: {len(df)}\n")

        # ── PRÉVIA COLORIDA NO TERMINAL ───────────────────────────────
        colunas_nota = list(COLUNAS_NOTAS.values()) + ["Média Geral"]
        print("=" * 80)
        print("PRÉVIA  (\033[92mverde ≥8\033[0m | \033[93mlaranja 5-7\033[0m | \033[91mvermelho ≤4\033[0m)")
        print("=" * 80)

        header = " | ".join(f"{c:^14}" for c in df.columns)
        print(f"\033[1m{header}\033[0m")
        print("-" * 80)

        for _, row in df.iterrows():
            linha = []
            for col in df.columns:
                val = row[col] if pd.notna(row[col]) else ""
                if col in colunas_nota:
                    linha.append(f"{cor_terminal(val):^14}")
                else:
                    linha.append(f"{str(val)[:14]:^14}")
            print(" | ".join(linha))

        print("=" * 80)
        return df

    except Exception as e:
        print(f"\nERRO: {e}")
        raise

if __name__ == "__main__":
    extrair_dados()