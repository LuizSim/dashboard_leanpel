import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import base64
from groq import Groq
import os

# ── CONFIGURAÇÃO DA PÁGINA ────────────────────────────────────────────
st.set_page_config(
    page_title="Leanpel — Dashboard de Avaliações",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── CONFIGURAÇÃO DA API GROQ ───────────────────────────────────────────
CHAVE_API = os.getenv("GROQ_API_KEY")
cliente_groq = Groq(api_key=CHAVE_API)

# ── ÍCONES DO CHAT ────────────────────────────────────────────────────
icon_user_svg = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40">
    <rect width="40" height="40" rx="10" fill="#34D399"/>
    <path d="M20 21a4.5 4.5 0 1 0 0-9 4.5 4.5 0 0 0 0 9zm0 2c-3.3 0-10 1.7-10 5v2h20v-2c0-3.3-6.7-5-10-5z" fill="white"/>
</svg>
"""
icon_user = f"data:image/svg+xml;base64,{base64.b64encode(icon_user_svg.encode()).decode()}"

icon_kamui_svg = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40">
    <rect width="40" height="40" rx="10" fill="#22D3EE"/>
    <path d="M10 16a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H12a2 2 0 0 1-2-2V16zm4 3a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm12 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm-11 6h10v1H15v-1zm4-12h2V9h-2v2z" fill="white"/>
</svg>
"""
icon_kamui = f"data:image/svg+xml;base64,{base64.b64encode(icon_kamui_svg.encode()).decode()}"

# ── ESTILIZAÇÃO CSS ───────────────────────────────────────────────────
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=Playfair+Display:wght@700&display=swap');

        .stApp { background-color: #071A4A; color: #FFFFFF; }
        h1, h2, h3, p, span, label { color: #FFFFFF !important; font-family: 'DM Sans', sans-serif; }

        div[data-testid="stMetric"] {
            background-color: #163380;
            border: 1px solid rgba(74,144,217,0.3);
            padding: 18px; border-radius: 16px; text-align: center;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(74,144,217,0.25);
        }
        div[data-testid="stMetricValue"] { color: #FFFFFF !important; font-weight: 700; font-size: 2rem; }
        div[data-testid="stMetricLabel"] { color: #8BA4C8 !important; font-size: 0.85rem; }

        div[data-testid="stPlotlyChart"] { animation: slideUp 0.5s ease-out; }

        .card-comentario {
            background-color: #163380;
            padding: 18px; border-radius: 14px; margin-bottom: 12px;
            border-left: 4px solid #4A90D9;
        }
        hr { border-color: rgba(74,144,217,0.2); }

        /* Filtros */
        div[data-testid="stHorizontalBlock"] button {
            border-radius: 10px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }

        @keyframes slideUp {
            from { opacity: 0; transform: translateY(20px); }
            to   { opacity: 1; transform: translateY(0); }
        }

        .badge-todas    { background:#4A90D9; color:#fff; padding:3px 12px; border-radius:20px; font-size:12px; font-weight:700; }
        .badge-parciais { background:#F59E0B; color:#fff; padding:3px 12px; border-radius:20px; font-size:12px; font-weight:700; }
        .badge-criticas { background:#EF4444; color:#fff; padding:3px 12px; border-radius:20px; font-size:12px; font-weight:700; }

        .filtro-info {
            background: rgba(74,144,217,0.1);
            border: 1px solid rgba(74,144,217,0.25);
            border-radius: 10px;
            padding: 10px 16px;
            font-size: 13px;
            color: #8BA4C8;
            margin-bottom: 16px;
        }
    </style>
""", unsafe_allow_html=True)

# ── COLUNAS DE NOTAS ─────────────────────────────────────────────────
COLUNAS_NOTAS = ["Atendimento", "Tempo de Espera", "Produtos", "Higiene", "Ambiente", "Preços"]

# ── FUNÇÃO: CLASSIFICAR LINHA ─────────────────────────────────────────
def classificar_linha(row):
    """
    Critica  → alguma nota < 5  (vermelho ou laranja = há problema grave)
    Parcial  → todas >= 5 mas alguma < 8 (laranja, sem vermelho)
    Positiva → todas >= 8 (verde)
    """
    notas = [row[c] for c in COLUNAS_NOTAS if c in row.index]
    if any(n < 5 for n in notas):
        return "Crítica"
    elif any(n < 8 for n in notas):
        return "Parcial"
    else:
        return "Positiva"

# ── FUNÇÕES DA INTELIGÊNCIA ARTIFICIAL KAMUI ─────────────────────────
def get_kamui_context(df):
    """Prepara o contexto dos dados do Leanpel para a IA analisar"""
    df_c = df.copy()
    df_c['Data Solo'] = pd.to_datetime(df_c['Data e Hora'], dayfirst=True).dt.date
    
    dias_unicos = int(df_c['Data Solo'].nunique())
    total_feedbacks = int(len(df_c))
    
    # Colunas do Leanpel
    colunas_notas = ['Atendimento', 'Tempo de Espera', 'Produtos', 'Higiene', 'Ambiente', 'Preços']
    
    # Agrupamento diário com todas as notas do Leanpel
    agg_dict = {col: 'mean' for col in colunas_notas if col in df_c.columns}
    daily_stats = df_c.groupby('Data Solo').agg(agg_dict).reset_index()
    
    contexto_csv = daily_stats.to_csv(index=False, sep='|')
    
    # Comentários
    col_com = "Comentário" if "Comentário" in df_c.columns else None
    if col_com:
        comentarios = " | ".join(df_c[col_com].dropna().tail(10).tolist())
    else:
        comentarios = "Nenhum comentário disponível"
    
    # Estatísticas gerais
    medias = {col: round(df_c[col].mean(), 2) for col in colunas_notas if col in df_c.columns}
    
    return {
        "dias_unicos": dias_unicos,
        "total_feedbacks": total_feedbacks,
        "tabela": contexto_csv,
        "comentarios": comentarios,
        "medias": medias
    }

def responder_kamui(pergunta, ctx):
    """Responde perguntas usando a IA Groq"""
    try:
        prompt = f"""
        Seu nome é Kamui, você é uma IA de análise lógica sênior criada exclusivamente para analisar dados da loja "Leanpel".
        
        Missão:
        Analisar dados, notas e comentários de clientes, identificando padrões, falhas, variações e evolução de desempenho.
        
        Escopo:
        Você está restrita ao contexto da Leanpel. Qualquer solicitação fora desse contexto deve ser recusada educadamente.
        
        Saudação (REGRA ESTRITA):
        - Se a mensagem for APENAS uma saudação (ex: "oi", "olá"), responda EXCLUSIVAMENTE: "Olá meu nome é Kamui, estou aqui para analisar seus dados e auxiliar em seus propósitos." (Não use esta frase em respostas de análise).
        - Se o usuário perguntar quem você é, responda: "Sou Kamui, uma IA especializada na análise dos dados do restaurante Estação Londres. Meu papel é identificar padrões, falhas e variações nas avaliações dos clientes."
        - Se o usuário fizer uma perguntar sem uma saudação inicial responda apenas com oque ele pediu sem saudação, apenas sauda se ousuário fizer uma pergunta com saudação, caso contrário responda apenas a pergunta sem saudação.
        
        Agradecimento (REGRA ESTRITA):
        - Se a mensagem for APENAS um agradecimento (ex: "obrigado", "valeu"), responda EXCLUSIVAMENTE: "De nada! Estou sempre aqui para ajudar com a análise dos seus dados." (Não use esta frase em respostas de análise).
        
        REGRAS IMPORTANTES:
        - Os dados atuais mostram EXATAMENTE {ctx['dias_unicos']} dias operacionais únicos.
        - Houve um total de {ctx['total_feedbacks']} avaliações no período.
        - É PROIBIDO contar o número de avaliações como o número de dias.
        - Use SEMPRE as médias do Leanpel: {ctx['medias']}
        
        Estrutura da resposta de análise:
        1. Quantidade de dias analisados
        2. Médias gerais por categoria
        3. Análise da evolução temporal
        4. Conclusão direta

        Dados para Processamento:
        TABELA DIÁRIA (médias por dia):
        {ctx['tabela']}
        
        COMENTÁRIOS RECENTES DOS CLIENTES:
        {ctx['comentarios']}
        """

        response = cliente_groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": pergunta}],
            temperature=0.1
        )
        
        if response.choices:
            return response.choices[0].message.content
        else:
            return "A Kamui não conseguiu gerar uma resposta. Verifique a conexão com a API."
            
    except Exception as e:
        return f"Oscilação nos sistemas Kamui: {e}"

# ── CARREGAR DADOS ────────────────────────────────────────────────────
try:
    df_raw = pd.read_csv("Avaliação.csv", sep=";", encoding="utf-8-sig")
    df_raw["Data Objeto"] = pd.to_datetime(df_raw["Data e Hora"], dayfirst=True)
    df_raw["Data Exibicao"] = df_raw["Data Objeto"].dt.strftime("%d/%m")
    df_raw["Classificação"] = df_raw.apply(classificar_linha, axis=1)

except FileNotFoundError:
    st.error("Arquivo 'Avaliação.csv' não encontrado. Rode o extrator_leanpel.py primeiro.")
    st.stop()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

# ── CABEÇALHO ─────────────────────────────────────────────────────────
col_titulo, col_ia = st.columns([0.88, 0.12])
with col_titulo:
    st.markdown("<h1 style='font-family:Playfair Display,serif;font-size:2rem;'>Leanpel — Dashboard de Avaliações</h1>", unsafe_allow_html=True)

with col_ia:
    with st.popover("🌀"): 
        st.markdown("### 🌀 Terminal Kamui")
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                avatar = icon_user if msg["role"] == "user" else icon_kamui
                with st.chat_message(msg["role"], avatar=avatar):
                    st.markdown(msg["content"])

        if p := st.chat_input("Perguntar à Kamui..."):
            st.session_state.chat_history.append({"role": "user", "content": p})
            with chat_container:
                with st.chat_message("user", avatar=icon_user):
                    st.markdown(p)
                with st.chat_message("assistant", avatar=icon_kamui):
                    ctx_data = get_kamui_context(df_raw)
                    resp = responder_kamui(p, ctx_data)
                    st.markdown(resp)
                    st.session_state.chat_history.append({"role": "assistant", "content": resp})

st.markdown("<hr>", unsafe_allow_html=True)

# ── FILTROS DE CRITICIDADE ────────────────────────────────────────────
st.markdown("### Filtrar avaliações")

col_f1, col_f2, col_f3, col_f4 = st.columns([1, 1, 1, 3])

if "filtro" not in st.session_state:
    st.session_state.filtro = "Todas"

with col_f1:
    if st.button("🔵  Todas", use_container_width=True,
                 type="primary" if st.session_state.filtro == "Todas" else "secondary"):
        st.session_state.filtro = "Todas"; st.rerun()

with col_f2:
    if st.button("🟡  Parciais", use_container_width=True,
                 type="primary" if st.session_state.filtro == "Parciais" else "secondary"):
        st.session_state.filtro = "Parciais"; st.rerun()

with col_f3:
    if st.button("🔴  Críticas", use_container_width=True,
                 type="primary" if st.session_state.filtro == "Críticas" else "secondary"):
        st.session_state.filtro = "Críticas"; st.rerun()

# Aplicar filtro
filtro_ativo = st.session_state.filtro
if filtro_ativo == "Todas":
    df = df_raw.copy()
    desc = "Exibindo <b>todas</b> as avaliações — verde (≥8), laranja (5–7) e vermelho (&lt;5)."
elif filtro_ativo == "Parciais":
    # Parciais = notas laranjas e verdes (sem críticas — sem vermelho)
    df = df_raw[df_raw["Classificação"].isin(["Parcial", "Positiva"])].copy()
    desc = "Exibindo avaliações <b>parciais e positivas</b> — apenas notas ≥ 5 (laranja e verde). Críticas excluídas."
else:
    # Críticas = laranjas e vermelhas (tem pelo menos uma nota ruim)
    df = df_raw[df_raw["Classificação"].isin(["Crítica", "Parcial"])].copy()
    desc = "Exibindo avaliações <b>críticas e parciais</b> — com pelo menos uma nota &lt; 8 (laranja ou vermelho)."

total_filtrado = len(df)
total_geral    = len(df_raw)

st.markdown(f'<div class="filtro-info">{desc} &nbsp;|&nbsp; <b>{total_filtrado}</b> de <b>{total_geral}</b> registros.</div>', unsafe_allow_html=True)

if df.empty:
    st.info("Nenhum registro encontrado para este filtro.")
    st.stop()

st.markdown("<hr>", unsafe_allow_html=True)

# ── MÉTRICAS ──────────────────────────────────────────────────────────
medias = {c: df[c].mean() for c in COLUNAS_NOTAS if c in df.columns}
media_geral = sum(medias.values()) / len(medias) if medias else 0

cols_m = st.columns(len(COLUNAS_NOTAS) + 1)
cols_m[0].metric("⭐ Média Geral", f"{media_geral:.1f}")
for i, (col, val) in enumerate(medias.items()):
    cols_m[i + 1].metric(col, f"{val:.1f}")

st.write(" ")

# ── GRÁFICOS ──────────────────────────────────────────────────────────
g1, g2 = st.columns([1, 2])

cores_graf = {
    "Atendimento":   "#4A90D9",
    "Tempo de Espera": "#6FB3F5",
    "Produtos":      "#34D399",
    "Higiene":       "#22D3EE",
    "Ambiente":      "#818CF8",
    "Preços":        "#F59E0B",
}

with g1:
    st.markdown("### Mix de Satisfação")
    somas = {c: df[c].sum() for c in COLUNAS_NOTAS if c in df.columns}
    df_p = pd.DataFrame(list(somas.items()), columns=["Critério", "Pontos"])
    fig_p = px.pie(
        df_p, values="Pontos", names="Critério", hole=0.55,
        color="Critério", color_discrete_map=cores_graf
    )
    fig_p.update_traces(textinfo="percent", textfont=dict(color="white", size=13))
    fig_p.update_layout(
        showlegend=True, height=380,
        margin=dict(t=30, b=0, l=0, r=0),
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(font=dict(color="white"))
    )
    st.plotly_chart(fig_p, use_container_width=True)

with g2:
    st.markdown("### Evolução Diária")
    if "criterio_sel" not in st.session_state:
        st.session_state.criterio_sel = COLUNAS_NOTAS[0]

    btn_cols = st.columns(len(COLUNAS_NOTAS))
    for i, c in enumerate(COLUNAS_NOTAS):
        if btn_cols[i].button(c, use_container_width=True,
                              type="primary" if st.session_state.criterio_sel == c else "secondary"):
            st.session_state.criterio_sel = c; st.rerun()

    crit = st.session_state.criterio_sel
    if crit in df.columns:
        df_ev = df.groupby("Data Exibicao")[crit].mean().reset_index()
        fig_ev = px.bar(df_ev, x="Data Exibicao", y=crit, text_auto=".1f")
        fig_ev.update_traces(
            marker_color=cores_graf.get(crit, "#4A90D9"),
            width=0.35, textposition="outside",
            textfont=dict(color="white", size=12)
        )
        fig_ev.update_layout(
            height=320, yaxis_range=[0, 11],
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, tickfont=dict(color="white"), title=""),
            yaxis=dict(visible=False)
        )
        st.plotly_chart(fig_ev, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── DISTRIBUIÇÃO POR CLASSIFICAÇÃO ───────────────────────────────────
st.markdown("### Distribuição por Classificação")
col_d1, col_d2, col_d3 = st.columns(3)

positivas = len(df[df["Classificação"] == "Positiva"])
parciais   = len(df[df["Classificação"] == "Parcial"])
criticas   = len(df[df["Classificação"] == "Crítica"])

col_d1.metric("Positivas (verde)", positivas)
col_d2.metric("Parciais (laranja)", parciais)
col_d3.metric("Críticas (vermelho)", criticas)

st.markdown("<hr>", unsafe_allow_html=True)

# ── COMENTÁRIOS ───────────────────────────────────────────────────────
col_titulo_com, col_botao_com = st.columns([0.8, 0.2])
with col_titulo_com:
    st.markdown("### 💬 Comentários")

with col_botao_com:
    # Contagem de TODAS as avaliações
    col_nome = "Nome do Cliente" if "Nome do Cliente" in df_raw.columns else None
    col_com  = "Comentário" if "Comentário" in df_raw.columns else None
    total_com = len(df_raw)
    
    if "mostrar_todos_comentarios" not in st.session_state:
        st.session_state.mostrar_todos_comentarios = False
    
    if st.button(f"📋 Ver Todos ({total_com})", use_container_width=True):
        st.session_state.mostrar_todos_comentarios = not st.session_state.mostrar_todos_comentarios
        st.rerun()

if col_com:
    # Mostra todas as avaliações, mesmo sem comentário
    df_c = df_raw.copy()
    df_c = df_c.sort_values(by="Data Objeto", ascending=False)
    
    if not df_c.empty:
        def badge_class(classif):
            if classif == "Positiva": return "#4A90D9"
            if classif == "Parcial":  return "#F59E0B"
            return "#EF4444"

        qtd_mostrar = len(df_c) if st.session_state.mostrar_todos_comentarios else 10

        for _, row in df_c.head(qtd_mostrar).iterrows():
            nome   = str(row[col_nome]).upper() if col_nome else "CLIENTE"
            data   = row.get("Data e Hora", "")
            com    = row[col_com] if row[col_com] and str(row[col_com]).strip() else "(sem comentário)"
            cor    = badge_class(row["Classificação"])
            media_r = row.get("Média Geral", "")
            media_str = f" &nbsp;|&nbsp; Média: <b>{media_r}</b>" if media_r != "" else ""
            st.markdown(
                f'<div class="card-comentario">'
                f'<b>{nome}</b> &nbsp; <span style="color:#8BA4C8;font-size:12px">{data}</span>'
                f'<span style="background:{cor};color:#fff;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:700;margin-left:10px">{row["Classificação"]}</span>'
                f'{media_str}<br><br>"{com}"'
                f'</div>',
                unsafe_allow_html=True
            )

        if not st.session_state.mostrar_todos_comentarios and len(df_c) > 10:
            st.info(f"Mostrando 10 de {len(df_c)} avaliações. Clique em 'Ver Todos' para exibir todas.")
    else:
        st.info("Nenhuma avaliação encontrada.")
else:
    st.info("Coluna 'Comentário' não encontrada no CSV.")