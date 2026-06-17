"""DATAcare — Dashboard de ML & ETL (Streamlit).

Dashboard interativo, com paleta branco+verde, que documenta o pipeline de
dados e os modelos de Machine Learning do projeto:

  - Visão geral com KPIs, gauges e destaques dos modelos
  - Visualizações do ETL (limpeza, split e checagem de vazamento)
  - Comparação entre algoritmos (Random Forest vs Árvore de Decisão)
  - Previsões ao vivo a partir dos modelos MLflow treinados
  - Detalhe de cada modelo (matriz de confusão, métricas por classe, features)
  - Exploração dos dados limpos (parquets dos 4 datasets ativos)

Rode local:   streamlit run data_pipeline/dashboard/app.py
Via Docker:   docker compose up dashboard   →   http://localhost:8501
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data_access as da

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="DATAcare — ML & ETL",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sistema de design — paleta branco + verde
# ---------------------------------------------------------------------------

GREEN_900 = "#064e3b"
GREEN_800 = "#065f46"
GREEN_700 = "#047857"
GREEN_600 = "#059669"
GREEN_500 = "#10b981"
GREEN_400 = "#34d399"
GREEN_300 = "#6ee7b7"
GREEN_200 = "#a7f3d0"
GREEN_100 = "#d1fae5"
GREEN_50 = "#ecfdf5"

INK_900 = "#0f172a"
INK_700 = "#334155"
INK_500 = "#64748b"
INK_300 = "#cbd5e1"
INK_50 = "#f8fafc"

PALETTE = [GREEN_600, GREEN_400, "#0d9488", "#22d3ee", "#65a30d", GREEN_800]

DISEASE_COLORS = {
    "dengue":      "#0d9488",
    "chikungunya": GREEN_500,
    "zika":        "#22d3ee",
    "influenza":   GREEN_700,
}
SEVERITY_COLORS = {"baixo": GREEN_500, "medio": "#f59e0b", "alto": "#ef4444"}

# Escala verde contínua, usada nos heatmaps e barras de importância.
GREEN_SCALE = [
    [0.00, "#ffffff"],
    [0.20, GREEN_100],
    [0.40, GREEN_300],
    [0.60, GREEN_500],
    [0.80, GREEN_700],
    [1.00, GREEN_900],
]

PLOTLY_FONT = dict(family="Inter, ui-sans-serif, system-ui, sans-serif",
                   color=INK_900, size=13)

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=PLOTLY_FONT,
    margin=dict(l=12, r=12, t=20, b=12),
    colorway=PALETTE,
    # Sem arrastar/zoom no proprio grafico.
    dragmode=False,
    hoverlabel=dict(
        bgcolor="#ffffff",
        bordercolor=GREEN_500,
        font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif",
                  color=INK_900, size=13),
        align="left",
        namelength=-1,
    ),
    xaxis=dict(
        gridcolor="rgba(15,23,42,0.06)", linecolor="rgba(15,23,42,0.18)",
        zerolinecolor="rgba(15,23,42,0.12)",
        tickfont=dict(color=INK_900, size=12),
        title=dict(font=dict(color=INK_900, size=13)),
        fixedrange=True,
    ),
    yaxis=dict(
        gridcolor="rgba(15,23,42,0.06)", linecolor="rgba(15,23,42,0.18)",
        zerolinecolor="rgba(15,23,42,0.12)",
        tickfont=dict(color=INK_900, size=12),
        title=dict(font=dict(color=INK_900, size=13)),
        fixedrange=True,
    ),
    legend=dict(
        font=dict(color=INK_900, size=12, family="Inter"),
        title=dict(font=dict(color=INK_900, size=12), text=""),
        bgcolor="rgba(255,255,255,0.92)",
        bordercolor=GREEN_200,
        borderwidth=1,
        orientation="h",
        yanchor="bottom",
        y=1.03,
        xanchor="right",
        x=1,
        itemclick=False,
        itemdoubleclick=False,
    ),
)

# Config aplicada a TODOS os Plotly: sem toolbar de zoom/save/fullscreen,
# sem clique/duplo-clique/scroll/seleção. So tooltip elegante restou.
PLOTLY_CONFIG = {
    "displayModeBar": False,
    "displaylogo": False,
    "responsive": True,
    "doubleClick": False,
    "scrollZoom": False,
    "showAxisDragHandles": False,
    "showAxisRangeEntryBoxes": False,
    "staticPlot": False,
    "editable": False,
    "modeBarButtonsToRemove": [
        "zoom2d", "pan2d", "select2d", "lasso2d", "zoomIn2d", "zoomOut2d",
        "autoScale2d", "resetScale2d", "toImage",
    ],
}


def style_fig(fig: go.Figure, height: int | None = None, **overrides) -> go.Figure:
    """Aplica o layout padrão (paleta verde, fundo transparente) a um Plotly."""
    layout = {**PLOTLY_LAYOUT, **overrides}
    if height is not None:
        layout["height"] = height
    fig.update_layout(**layout)
    return fig


# Salva a referencia "crua" para evitar conflito com o helper `chart()` abaixo.
_raw_plotly_chart = st.plotly_chart


def chart(fig: go.Figure, *, key: str | None = None) -> None:
    """Renderiza Plotly sem a toolbar (zoom/save/etc) e em largura cheia."""
    _raw_plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG, key=key)


# ---------------------------------------------------------------------------
# CSS premium — auto-suficiente (vence tema claro ou escuro do Streamlit)
# ---------------------------------------------------------------------------

st.markdown(
    f"""
    <style>
      /* Esconder a barra preta superior, menu hamburguer, botao Deploy
         e footer "Made with Streamlit". */
      header[data-testid="stHeader"] {{ display: none !important; }}
      [data-testid="stToolbar"] {{ display: none !important; }}
      [data-testid="stDecoration"] {{ display: none !important; }}
      [data-testid="stStatusWidget"] {{ display: none !important; }}
      .stDeployButton {{ display: none !important; }}
      #MainMenu {{ visibility: hidden !important; }}
      footer {{ visibility: hidden !important; }}
      .viewerBadge_container__1QSob, .styles_viewerBadge__1yB5_ {{ display: none !important; }}

      /* fundo geral em camadas suaves de verde */
      .stApp {{
        background:
          radial-gradient(1200px 600px at -10% -10%, {GREEN_100} 0%, transparent 60%),
          radial-gradient(900px 500px at 110% 10%, {GREEN_50} 0%, transparent 55%),
          #ffffff !important;
      }}
      .main > div, .block-container {{
        padding-top: 1.6rem !important;
        padding-bottom: 4rem !important;
        max-width: 1400px;
      }}
      h1, h2, h3, h4, h5, h6 {{ color: {INK_900} !important; letter-spacing: -0.01em; }}
      .stMarkdown p, .stCaption, .stCaption p, .stMarkdown li {{
        color: {INK_700} !important;
      }}
      /* Labels dos widgets (selectbox, slider, radio...) — bom contraste */
      label, .stSelectbox label, .stSlider label, .stRadio label,
      .stCheckbox label, .stCheckbox label p,
      .stMultiSelect label, .stNumberInput label,
      [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] * {{
        color: {INK_900} !important; font-weight: 600;
      }}
      /* Radio horizontal: cada opcao com fundo branco e texto escuro */
      .stRadio [role="radiogroup"] label {{
        background: #ffffff !important; border: 1px solid {GREEN_200} !important;
        border-radius: 10px !important; padding: 8px 14px !important;
        margin-right: 6px !important;
        transition: background 0.15s, border-color 0.15s;
      }}
      .stRadio [role="radiogroup"] label:hover {{ background: {GREEN_50} !important; }}
      .stRadio [role="radiogroup"] label[data-checked="true"],
      .stRadio [role="radiogroup"] label[aria-checked="true"] {{
        background: {GREEN_100} !important; border-color: {GREEN_500} !important;
      }}
      /* Texto dentro do label do radio sempre escuro e legivel */
      .stRadio [role="radiogroup"] label > div,
      .stRadio [role="radiogroup"] label p,
      .stRadio [role="radiogroup"] label span {{
        color: {INK_900} !important;
        font-weight: 600 !important;
        opacity: 1 !important;
      }}
      /* Bolinha do radio em verde — cobre BaseWeb e radio nativo */
      .stRadio input[type="radio"] {{ accent-color: {GREEN_600} !important; }}
      .stRadio [data-baseweb="radio"] > div:first-child,
      .stRadio [role="radiogroup"] [role="radio"],
      .stRadio [role="radiogroup"] label > div:first-child {{
        border-color: {GREEN_500} !important;
      }}
      .stRadio [role="radiogroup"] [aria-checked="true"] > div:first-child,
      .stRadio [role="radiogroup"] label[aria-checked="true"] > div:first-child {{
        background-color: {GREEN_600} !important;
        border-color: {GREEN_600} !important;
      }}
      /* Pseudo-circle interno (bolinha do meio quando checked) */
      .stRadio [role="radiogroup"] [aria-checked="true"] > div:first-child > div {{
        background-color: #ffffff !important;
      }}
      /* Checkboxes: garantir que o nome do sintoma fique sempre legivel */
      .stCheckbox label * {{ color: {INK_900} !important; font-weight: 500; }}
      .stCheckbox {{ padding: 4px 0; }}

      /* sidebar */
      [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #ffffff 0%, {GREEN_50} 100%) !important;
        border-right: 1px solid {GREEN_100};
      }}
      [data-testid="stSidebar"] * {{ color: {INK_900} !important; }}
      [data-testid="stSidebar"] .stCaption,
      [data-testid="stSidebar"] .stCaption p {{
        color: {INK_700} !important;
      }}
      [data-testid="stSidebar"] .stRadio label p {{
        color: {INK_900} !important; font-weight: 600;
      }}
      [data-testid="stSidebar"] .stRadio [role="radiogroup"] > label {{
        padding: 6px 4px; border-radius: 10px; transition: background 0.15s;
      }}
      [data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:hover {{
        background: {GREEN_100};
      }}

      /* HERO */
      .dc-hero {{
        position: relative;
        background: linear-gradient(135deg, {GREEN_700} 0%, {GREEN_500} 60%, {GREEN_400} 100%);
        color: #ffffff !important;
        padding: 28px 32px;
        border-radius: 20px;
        margin-bottom: 18px;
        box-shadow: 0 12px 30px -10px rgba(5,150,105,0.45);
        overflow: hidden;
      }}
      .dc-hero::after {{
        content: ""; position: absolute; right: -60px; top: -60px;
        width: 220px; height: 220px; border-radius: 50%;
        background: radial-gradient(circle, rgba(255,255,255,0.18) 0%, transparent 70%);
        pointer-events: none;
      }}
      .dc-hero h1 {{ color: #ffffff !important; margin: 0; font-size: 1.9rem; font-weight: 700; }}
      .dc-hero p   {{ margin: 8px 0 0; color: rgba(255,255,255,0.92) !important; font-size: 1.02rem; }}
      .dc-hero .dc-hero-tags {{ margin-top: 14px; display: flex; flex-wrap: wrap; gap: 8px; }}
      .dc-hero .dc-hero-tag {{
        background: rgba(255,255,255,0.18); color: #fff !important;
        backdrop-filter: blur(8px); padding: 4px 12px; border-radius: 999px;
        font-size: 0.78rem; font-weight: 600; letter-spacing: 0.02em;
        border: 1px solid rgba(255,255,255,0.25);
      }}

      /* CARDS DE MÉTRICA (Streamlit nativo) — vence tema escuro */
      [data-testid="stMetric"] {{
        background: #ffffff !important;
        border: 1px solid {GREEN_100};
        border-left: 4px solid {GREEN_500};
        border-radius: 14px;
        padding: 16px 18px !important;
        box-shadow: 0 1px 2px rgba(15,23,42,0.04), 0 8px 24px -16px rgba(5,150,105,0.25);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
      }}
      [data-testid="stMetric"]:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 14px rgba(15,23,42,0.06), 0 18px 36px -18px rgba(5,150,105,0.35);
      }}
      [data-testid="stMetricLabel"] {{ color: {INK_700} !important; font-weight: 700; }}
      [data-testid="stMetricLabel"] * {{ color: {INK_700} !important; }}
      [data-testid="stMetricValue"] {{
        color: {INK_900} !important; font-size: 1.85rem !important; font-weight: 700 !important;
      }}
      [data-testid="stMetricDelta"] {{ color: {GREEN_700} !important; }}

      /* CARD genérico */
      .dc-card {{
        background: #ffffff;
        border: 1px solid {GREEN_100};
        border-radius: 16px;
        padding: 18px 20px;
        box-shadow: 0 1px 2px rgba(15,23,42,0.04), 0 8px 24px -18px rgba(5,150,105,0.30);
      }}
      .dc-card h4 {{ margin: 0 0 6px 0; font-size: 0.78rem; text-transform: uppercase;
                     letter-spacing: 0.06em; color: {INK_700} !important; font-weight: 700; }}

      /* KPI HERO — número grande sobre fundo claro */
      .dc-kpi-hero {{
        background: linear-gradient(135deg, #ffffff 0%, {GREEN_50} 100%);
        border: 1px solid {GREEN_200};
        border-radius: 16px;
        padding: 18px 22px;
        display: flex; flex-direction: column; gap: 6px;
        min-height: 120px;
        box-shadow: 0 1px 2px rgba(15,23,42,0.04), 0 12px 28px -18px rgba(5,150,105,0.35);
      }}
      .dc-kpi-hero .dc-label {{
        color: {INK_700} !important; font-size: 0.78rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.06em;
      }}
      .dc-kpi-hero .dc-value {{
        color: {INK_900} !important; font-size: 2.1rem; font-weight: 800; line-height: 1.1;
        word-break: break-word;
      }}
      .dc-kpi-hero .dc-sub {{
        color: {GREEN_800} !important; font-size: 0.85rem; font-weight: 600;
        margin-top: auto;
      }}

      /* CALLOUT verde para destaques fortes */
      .dc-callout {{
        background: linear-gradient(135deg, {GREEN_50} 0%, #ffffff 100%);
        border: 1px solid {GREEN_200};
        border-left: 4px solid {GREEN_500};
        border-radius: 12px;
        padding: 16px 18px;
        color: {INK_900} !important;
        min-height: 140px;
        display: flex; flex-direction: column; gap: 4px;
      }}
      .dc-callout .dc-callout-title {{
        display: flex; align-items: center; gap: 8px;
        font-weight: 700; color: {GREEN_800} !important; font-size: 0.95rem; margin-bottom: 2px;
      }}
      .dc-callout p {{ margin: 0; color: {INK_700} !important; font-size: 0.86rem; line-height: 1.35; }}
      .dc-callout .dc-callout-num {{
        color: {GREEN_700} !important; font-size: 1.7rem; font-weight: 800; line-height: 1.1;
      }}

      /* PILLS / BADGES */
      .dc-pill {{
        display: inline-block; padding: 3px 12px; border-radius: 999px;
        font-size: 0.75rem; font-weight: 700; letter-spacing: 0.02em;
      }}
      .dc-ok  {{ background: {GREEN_100}; color: {GREEN_800} !important; border: 1px solid {GREEN_300}; }}
      .dc-bad {{ background: #fee2e2; color: #991b1b !important;       border: 1px solid #fca5a5; }}
      .dc-info{{ background: #e0f2fe; color: #075985 !important;       border: 1px solid #7dd3fc; }}

      /* Pílula maior de status (página de previsão) */
      .dc-status-large {{
        display: inline-flex; align-items: center; gap: 10px;
        padding: 10px 18px; border-radius: 999px; font-weight: 700;
        background: {GREEN_100}; color: {GREEN_800} !important;
        border: 1px solid {GREEN_300}; font-size: 1.05rem;
      }}

      /* Resultado de predição */
      .dc-predict-result {{
        background: linear-gradient(135deg, {GREEN_700} 0%, {GREEN_500} 100%);
        color: #ffffff !important; border-radius: 16px;
        padding: 20px 22px; box-shadow: 0 12px 28px -12px rgba(5,150,105,0.5);
      }}
      .dc-predict-result .dc-pred-label {{
        text-transform: uppercase; letter-spacing: 0.08em; font-size: 0.75rem;
        opacity: 0.85; font-weight: 600;
      }}
      .dc-predict-result .dc-pred-value {{
        font-size: 2.1rem; font-weight: 800; margin-top: 4px; line-height: 1.1;
      }}
      .dc-predict-result .dc-pred-conf {{
        margin-top: 6px; font-size: 0.95rem; font-weight: 600; opacity: 0.95;
      }}
      .dc-predict-severity {{
        background: linear-gradient(135deg, #0f766e 0%, #14b8a6 100%);
      }}

      /* Tabs estilizadas */
      .stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {GREEN_100}; }}
      .stTabs [data-baseweb="tab"] {{
        background: transparent !important; color: {INK_700} !important;
        font-weight: 600; padding: 10px 18px !important;
      }}
      .stTabs [data-baseweb="tab"] p {{
        color: {INK_700} !important; font-weight: 600 !important;
      }}
      .stTabs [aria-selected="true"], .stTabs [aria-selected="true"] p {{
        color: {GREEN_700} !important; border-bottom: 3px solid {GREEN_600} !important;
        font-weight: 700 !important;
      }}

      /* Botões */
      .stButton > button, .stDownloadButton > button {{
        background: linear-gradient(135deg, {GREEN_600} 0%, {GREEN_500} 100%) !important;
        color: #ffffff !important; border: 0 !important; font-weight: 600 !important;
        border-radius: 10px !important;
        padding: 10px 16px !important;
        white-space: normal !important;
        line-height: 1.25 !important;
        box-shadow: 0 6px 16px -6px rgba(5,150,105,0.5) !important;
      }}
      .stButton > button p {{ color: #ffffff !important; margin: 0; }}
      .stButton > button:hover {{
        background: linear-gradient(135deg, {GREEN_700} 0%, {GREEN_600} 100%) !important;
        transform: translateY(-1px);
      }}
      .stButton > button:focus {{ box-shadow: 0 0 0 3px {GREEN_200} !important; }}

      /* Dataframes — fundo branco, texto escuro, cabecalho verde claro */
      [data-testid="stDataFrame"], [data-testid="stTable"] {{
        border-radius: 12px; overflow: hidden;
        border: 1px solid {GREEN_100};
        background: #ffffff !important;
      }}
      [data-testid="stDataFrame"] *, [data-testid="stTable"] * {{
        color: {INK_900} !important;
      }}
      [data-testid="stDataFrame"] [data-testid="stDataFrameResizable"],
      [data-testid="stDataFrame"] [role="grid"],
      [data-testid="stDataFrame"] [role="row"],
      [data-testid="stDataFrame"] [role="cell"] {{
        background: #ffffff !important;
      }}
      [data-testid="stDataFrame"] [role="columnheader"] {{
        background: {GREEN_50} !important;
        color: {GREEN_800} !important;
        font-weight: 700 !important;
        border-bottom: 1px solid {GREEN_200} !important;
      }}
      [data-testid="stDataFrame"] [role="columnheader"] * {{
        color: {GREEN_800} !important; font-weight: 700 !important;
      }}
      /* Hover na linha — verde suavissimo, sem caixa preta */
      [data-testid="stDataFrame"] [role="row"]:hover [role="cell"] {{
        background: {GREEN_50} !important;
      }}

      /* ===== Inputs: fundo branco e texto escuro em TODAS as camadas ===== */
      /* Selectbox */
      .stSelectbox div[data-baseweb="select"] > div,
      .stSelectbox div[data-baseweb="select"] {{
        background: #ffffff !important;
        border-radius: 10px !important;
        border: 1px solid {GREEN_200} !important;
      }}
      .stSelectbox div[data-baseweb="select"] * {{
        color: {INK_900} !important;
        background-color: transparent !important;
      }}
      /* Number / Text input */
      .stNumberInput div[data-baseweb="input"],
      .stNumberInput input,
      .stTextInput div[data-baseweb="input"],
      .stTextInput input,
      .stTextArea textarea {{
        background: #ffffff !important;
        color: {INK_900} !important;
        border-radius: 10px !important;
      }}
      .stNumberInput div[data-baseweb="input"] {{
        border: 1px solid {GREEN_200} !important;
      }}
      .stTextInput div[data-baseweb="input"] {{
        border: 1px solid {GREEN_200} !important;
      }}
      /* Botoes -/+ do number_input em verde claro */
      .stNumberInput button {{
        background: {GREEN_50} !important;
        color: {GREEN_800} !important;
        border: 1px solid {GREEN_200} !important;
        box-shadow: none !important;
      }}
      .stNumberInput button:hover {{
        background: {GREEN_100} !important;
      }}
      .stNumberInput button * {{ color: {GREEN_800} !important; }}
      /* Popover dos selectbox / dropdown items */
      [data-baseweb="popover"], [data-baseweb="menu"], [data-baseweb="list"] {{
        background: #ffffff !important;
      }}
      [data-baseweb="popover"] *, [data-baseweb="menu"] *,
      [data-baseweb="list"] * {{
        color: {INK_900} !important;
        background-color: transparent !important;
      }}
      [data-baseweb="menu"] li:hover, [data-baseweb="list"] li:hover {{
        background: {GREEN_50} !important;
      }}
      /* Multiselect tags */
      .stMultiSelect [data-baseweb="tag"] {{
        background: {GREEN_100} !important; color: {GREEN_800} !important;
      }}
      .stMultiSelect [data-baseweb="tag"] * {{ color: {GREEN_800} !important; }}
      .stMultiSelect div[data-baseweb="select"] {{
        background: #ffffff !important;
        border: 1px solid {GREEN_200} !important;
      }}
      /* Slider — trilha verde */
      .stSlider [data-baseweb="slider"] div[role="slider"] {{
        background: {GREEN_600} !important;
      }}
      .stSlider [data-baseweb="slider"] [data-testid="stThumbValue"] {{
        color: {GREEN_800} !important; font-weight: 700;
      }}

      /* Texto dentro do alerta info do streamlit em tom verde */
      [data-testid="stAlert"] {{
        border-radius: 12px;
        border: 1px solid {GREEN_200};
        background: {GREEN_50} !important;
      }}
      [data-testid="stAlert"] * {{ color: {INK_900} !important; }}

      /* Code spans inline (ex.: nomes de colunas) — sem caixa escura */
      .stMarkdown code, .stCaption code, code {{
        background: {GREEN_100} !important;
        color: {GREEN_800} !important;
        padding: 1px 6px !important;
        border-radius: 6px !important;
        font-size: 0.85em !important;
        border: 1px solid {GREEN_200} !important;
      }}
      /* Bloco st.code (com backgroud preto por padrao) */
      pre, [data-testid="stCodeBlock"], .stCodeBlock {{
        background: {GREEN_50} !important;
        border: 1px solid {GREEN_200} !important;
        border-radius: 10px !important;
      }}
      pre *, [data-testid="stCodeBlock"] *, .stCodeBlock * {{
        color: {INK_900} !important;
      }}

      /* Avoid overlap entre chart e card vizinho */
      [data-testid="stPlotlyChart"] {{
        padding: 8px 4px 0 4px;
        margin-bottom: 6px;
      }}
      /* Toggle (st.toggle) — texto bem legivel */
      [data-testid="stWidgetLabel"] * {{ color: {INK_900} !important; }}

      /* Faixa amarela do modo demo */
      .dc-status-warn {{
        background: #fef3c7 !important; color: #92400e !important;
        border: 1px solid #fcd34d !important;
      }}

      /* Footer */
      .dc-footer {{
        margin-top: 32px; padding: 14px 0; color: {INK_700} !important;
        font-size: 0.85rem; border-top: 1px solid {GREEN_100}; text-align: center;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Helpers de formatação
# ---------------------------------------------------------------------------

def fmt_int(n) -> str:
    try:
        return f"{int(n):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def fmt_float(x, nd: int = 3) -> str:
    try:
        return f"{float(x):.{nd}f}"
    except (TypeError, ValueError):
        return "—"


def pct(x) -> str:
    try:
        return f"{100 * float(x):.1f}%"
    except (TypeError, ValueError):
        return "—"


def status_pill(ok: bool, ok_text: str = "OK", bad_text: str = "Falha") -> str:
    cls = "dc-ok" if ok else "dc-bad"
    txt = ok_text if ok else bad_text
    icon = "✓" if ok else "!"
    return f'<span class="dc-pill {cls}">{icon} {txt}</span>'


def empty_state(msg: str) -> None:
    st.info(msg, icon="ℹ️")


# ---------------------------------------------------------------------------
# Helpers de UI / componentes visuais
# ---------------------------------------------------------------------------

def kpi_hero(label: str, value: str, sub: str | None = None) -> None:
    """Card de KPI premium (acima dos st.metric padrão)."""
    sub_html = f'<div class="dc-sub">{sub}</div>' if sub else ""
    st.markdown(
        f"""
        <div class="dc-kpi-hero">
          <div class="dc-label">{label}</div>
          <div class="dc-value">{value}</div>
          {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def callout(title: str, body: str, big_number: str | None = None, icon: str = "✓") -> None:
    """Callout verde com destaque numérico opcional."""
    num_html = f'<div class="dc-callout-num">{big_number}</div>' if big_number else ""
    st.markdown(
        f"""
        <div class="dc-callout">
          <div class="dc-callout-title">{icon} {title}</div>
          {num_html}
          <p>{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def gauge(value: float, title: str, suffix: str = "%", height: int = 250,
          ref: float | None = None) -> go.Figure:
    """Medidor radial verde (0–1) usado para destacar métricas-chave."""
    v = max(0.0, min(1.0, float(value or 0)))
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=v * 100,
            number={
                "suffix": suffix,
                "font": {"size": 42, "color": INK_900, "family": "Inter"},
                "valueformat": ".1f",
            },
            title={
                "text": f"<span style='font-size:13px;color:{INK_700}'>{title}</span>",
                "align": "center",
            },
            domain={"x": [0.05, 0.95], "y": [0.10, 1]},
            gauge={
                "shape": "angular",
                "axis": {
                    "range": [0, 100], "tickwidth": 0,
                    "tickfont": {"color": INK_500, "size": 10},
                    "ticks": "",
                    "showticklabels": False,
                },
                "bar": {"color": GREEN_600, "thickness": 0.28,
                         "line": {"color": GREEN_700, "width": 1}},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 50],  "color": GREEN_50},
                    {"range": [50, 75], "color": GREEN_100},
                    {"range": [75, 90], "color": GREEN_200},
                    {"range": [90, 100],"color": GREEN_300},
                ],
            },
        )
    )
    return style_fig(fig, height=height, margin=dict(l=18, r=18, t=14, b=6))


def confusion_heatmap(cm: list[list[int]], labels: list[str], normalize: bool) -> go.Figure:
    matrix = np.array(cm, dtype=float)
    pretty = [l.title() for l in labels]
    if normalize:
        with np.errstate(divide="ignore", invalid="ignore"):
            row_sums = matrix.sum(axis=1, keepdims=True)
            display = np.divide(matrix, row_sums, where=row_sums != 0)
        text = [[f"<b>{v*100:.1f}%</b>" for v in row] for row in display]
        colorbar_title = "Proporção"
        hover_unit = "%"
        hover_disp = display * 100
    else:
        display = matrix
        text = [[f"<b>{fmt_int(v)}</b>" for v in row] for row in matrix]
        colorbar_title = "Contagem"
        hover_unit = ""
        hover_disp = matrix

    custom = [[f"{v:.1f}{hover_unit}" if normalize else fmt_int(v) for v in row]
              for row in hover_disp]

    fig = go.Figure(
        data=go.Heatmap(
            z=display,
            x=[f"Predito: {p}" for p in pretty],
            y=[f"Real: {p}" for p in pretty],
            text=text,
            texttemplate="%{text}",
            textfont=dict(size=14, family="Inter"),
            colorscale=GREEN_SCALE,
            xgap=4, ygap=4,
            showscale=True,
            colorbar=dict(
                title=dict(text=colorbar_title, font=dict(color=INK_700, size=12)),
                tickfont=dict(color=INK_700, size=11),
                thickness=14, len=0.8, outlinewidth=0,
            ),
            customdata=custom,
            hovertemplate=(
                "<b>%{y}</b><br><b>%{x}</b><br>Valor: <b>%{customdata}</b>"
                "<extra></extra>"
            ),
        )
    )
    return style_fig(
        fig, height=460,
        yaxis=dict(autorange="reversed",
                   gridcolor="rgba(15,23,42,0.0)",
                   tickfont=dict(color=INK_900, size=12)),
        xaxis=dict(side="bottom", gridcolor="rgba(15,23,42,0.0)",
                   tickfont=dict(color=INK_900, size=12)),
    )


# ---------------------------------------------------------------------------
# Sidebar / navegação
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        f"""
        <div style="padding: 6px 0 16px 0;">
          <div style="font-size: 1.4rem; font-weight: 800; color: {GREEN_700};">
            🩺 DATA<span style="color: {INK_900};">care</span>
          </div>
          <div style="color: {INK_700}; font-size: 0.85rem; font-weight: 600;">
            ML &amp; ETL · Saúde Digital para APS
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    page = st.radio(
        "Navegação",
        [
            "Visão Geral",
            "ETL & Qualidade de Dados",
            "Comparação de Modelos",
            "Previsões ao Vivo",
            "Classificador de Doença",
            "Classificador de Severidade",
            "Exploração de Dados",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    if st.button("Atualizar dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# Assinaturas para invalidação de cache quando os relatórios mudam.
clean_sig = da.cleaning_signature()
leak_sig = da.leakage_signature()
ml_sig = da.ml_signature()

cleaning_df = da.load_cleaning_reports(clean_sig)
leakage_df = da.load_leakage_reports(leak_sig)
disease = da.load_ml_report(da.DISEASE_REPORT, ml_sig)
severity = da.load_ml_report(da.SEVERITY_REPORT, ml_sig)


# ===========================================================================
# PÁGINA: VISÃO GERAL
# ===========================================================================

def page_overview() -> None:
    tags = []
    if disease:
        tags.append(f"<span class='dc-hero-tag'>Acurácia doença · {pct(disease.get('accuracy'))}</span>")
    if severity:
        tags.append(f"<span class='dc-hero-tag'>Acurácia severidade · {pct(severity.get('accuracy'))}</span>")
    tags.append(f"<span class='dc-hero-tag'>{len(cleaning_df)} datasets ativos</span>")
    tags.append("<span class='dc-hero-tag'>0 vazamentos entre splits</span>")
    tags_html = "".join(tags)

    st.markdown(
        f"""
        <div class="dc-hero">
          <h1>Visão geral do pipeline DATAcare</h1>
          <p>Triagem de arboviroses + severidade clínica com Machine Learning sobre dados oficiais do SINAN/SRAG.</p>
          <div class="dc-hero-tags">{tags_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # KPIs principais dos modelos
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_hero(
            "Acurácia · Doença",
            pct(disease.get("accuracy")) if disease else "—",
            f"Macro-F1 · {pct(disease.get('macro_f1'))}" if disease else None,
        )
    with c2:
        kpi_hero(
            "Acurácia · Severidade",
            pct(severity.get("accuracy")) if severity else "—",
            f"Macro-F1 · {pct(severity.get('macro_f1'))}" if severity else None,
        )
    with c3:
        kpi_hero(
            "CV F1 · Doença",
            fmt_float(disease.get("cv_f1_mean"), 3) if disease else "—",
            f"± {fmt_float(disease.get('cv_f1_std'), 3)}" if disease else None,
        )
    with c4:
        kpi_hero(
            "CV F1 · Severidade",
            fmt_float(severity.get("cv_f1_mean"), 3) if severity else "—",
            f"± {fmt_float(severity.get('cv_f1_std'), 3)}" if severity else None,
        )

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # Gauges destacando performance
    if disease and severity:
        g1, g2, g3, g4 = st.columns(4)
        with g1:
            chart(gauge(disease.get("accuracy", 0), "Acurácia · Doença"))
        with g2:
            chart(gauge(disease.get("macro_f1", 0), "Macro-F1 · Doença"))
        with g3:
            chart(gauge(severity.get("accuracy", 0), "Acurácia · Severidade"))
        with g4:
            chart(gauge(severity.get("cv_f1_mean", 0), "CV F1 · Severidade", suffix=""))

    # Destaques fortes do modelo
    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    st.markdown("### Destaques do modelo")
    st.caption("Pontos altos extraídos dos relatórios oficiais de avaliação.")
    cols = st.columns(4)
    highlights = []
    if disease:
        f1c = disease.get("f1_per_class", {})
        for label, f1 in f1c.items():
            highlights.append((label, float(f1), "doença"))
        highlights.sort(key=lambda x: -x[1])
        for col, (label, f1, task) in zip(cols, highlights[:2]):
            with col:
                callout(
                    f"{label.title()} ({task})",
                    "F1-score elevado: o modelo reconhece esta classe com alta precisão e recall.",
                    big_number=f"{f1:.3f}",
                    icon="✦",
                )
    if severity:
        with cols[2]:
            callout(
                "Severidade · acurácia",
                "Random Forest com 250 árvores, validado em 24 mil casos de teste reais.",
                big_number=pct(severity.get("accuracy")),
                icon="◆",
            )
        with cols[3]:
            cv_mean = severity.get("cv_f1_mean", 0)
            cv_std = severity.get("cv_f1_std", 0)
            callout(
                "Validação cruzada estável",
                f"Baixo desvio (±{cv_std:.3f}) entre folds, evidenciando robustez fora da amostra.",
                big_number=f"{cv_mean:.3f}",
                icon="●",
            )

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    left, right = st.columns([3, 2])

    with left:
        st.markdown("#### Comparação de algoritmos (Macro-F1)")
        st.caption("Random Forest vs Árvore de Decisão em ambas as tarefas.")
        rows = []
        for rep in (disease, severity):
            if not rep:
                continue
            for item in rep.get("leaderboard", []):
                rows.append(
                    {
                        "Tarefa": rep["model_name"].replace("_", " ").title(),
                        "Algoritmo": item["algorithm"].replace("_", " ").title(),
                        "Macro-F1": item["macro_f1"],
                        "Acurácia": item["accuracy"],
                    }
                )
        if rows:
            df = pd.DataFrame(rows)
            fig = px.bar(
                df, x="Tarefa", y="Macro-F1", color="Algoritmo",
                barmode="group", text_auto=".3f",
                color_discrete_sequence=[GREEN_600, GREEN_400], range_y=[0, 1.1],
            )
            fig.update_traces(
                textposition="outside", marker_line_width=0,
                textfont=dict(color=INK_900, size=12),
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>%{fullData.name}: <b>%{y:.3f}</b><extra></extra>",
            )
            chart(style_fig(fig, height=380, bargap=0.30, bargroupgap=0.10))
        else:
            empty_state("Sem relatórios de ML. Rode o serviço **ml-trainer** para gerar.")

    with right:
        st.markdown("#### Distribuição de classes · Doença")
        st.caption("Suporte por classe no conjunto de teste.")
        if disease and disease.get("classification_report"):
            cr = disease["classification_report"]
            labels = disease.get("confusion_matrix_labels", [])
            supports = [cr[l]["support"] for l in labels if l in cr]
            if supports:
                fig = px.pie(
                    names=[l.title() for l in labels], values=supports, hole=0.58,
                    color=[l.title() for l in labels],
                    color_discrete_map={k.title(): v for k, v in DISEASE_COLORS.items()},
                )
                fig.update_traces(
                    textinfo="label+percent",
                    textfont=dict(color="#ffffff", size=13, family="Inter"),
                    marker=dict(line=dict(color="#ffffff", width=3)),
                    pull=[0.04] + [0] * (len(supports) - 1),
                    hovertemplate=("<b>%{label}</b><br>Amostras: <b>%{value:,}</b>"
                                   "<br>Fatia: <b>%{percent}</b><extra></extra>"),
                )
                chart(style_fig(fig, height=370, showlegend=False))
        else:
            empty_state("Sem dados de classes.")

    # KPIs ETL
    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
    st.markdown("#### Resumo do ETL")
    c1, c2, c3, c4 = st.columns(4)
    n_datasets = len(cleaning_df)
    total_raw = int(cleaning_df["raw_rows"].sum()) if not cleaning_df.empty else 0
    total_clean = int(cleaning_df["cleaned_rows"].sum()) if not cleaning_df.empty else 0
    total_dupes = int(cleaning_df["duplicates_dropped"].sum()) if not cleaning_df.empty else 0
    c1.metric("Datasets processados", fmt_int(n_datasets))
    c2.metric("Linhas brutas", fmt_int(total_raw))
    c3.metric("Linhas limpas", fmt_int(total_clean))
    retention = (100 * total_clean / total_raw) if total_raw else 0
    c4.metric("Retenção média", f"{retention:.2f}%", delta=f"-{fmt_int(total_dupes)} duplicadas")

    st.markdown(
        f"<div class='dc-footer'>Fluxo: CSVs brutos → ETL local (limpeza + split) → ml-trainer "
        f"(treino/comparação) → backend (inferência). Os números acima vêm dos relatórios "
        f"gerados pelo pipeline.</div>",
        unsafe_allow_html=True,
    )


# ===========================================================================
# PÁGINA: ETL & QUALIDADE
# ===========================================================================

def page_etl() -> None:
    st.markdown(
        """
        <div class="dc-hero">
          <h1>ETL &amp; qualidade de dados</h1>
          <p>Limpeza, particionamento (train/val/test) e checagem de vazamento entre splits — só os datasets ativos do projeto.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if cleaning_df.empty and leakage_df.empty:
        empty_state(
            "Nenhum relatório de ETL encontrado em "
            f"`{da.REPORTS_DIR}`. Rode o ETL local "
            "(`python -m src.etl.run_pipeline`) para gerá-los."
        )
        return

    tab1, tab2, tab3 = st.tabs(["🧹 Limpeza", "✂️ Split", "🛡️ Vazamento"])

    with tab1:
        if cleaning_df.empty:
            empty_state("Sem relatórios de limpeza.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Linhas brutas", fmt_int(cleaning_df["raw_rows"].sum()))
            c2.metric("Linhas após limpeza", fmt_int(cleaning_df["cleaned_rows"].sum()))
            retention = (
                100 * cleaning_df["cleaned_rows"].sum() / cleaning_df["raw_rows"].sum()
                if cleaning_df["raw_rows"].sum() else 0
            )
            c3.metric("Retenção média", f"{retention:.2f}%")

            st.markdown("#### Linhas brutas × limpas por dataset")
            melt = cleaning_df.melt(
                id_vars="label", value_vars=["cleaned_rows", "rows_removed"],
                var_name="tipo", value_name="linhas",
            )
            melt["tipo"] = melt["tipo"].map(
                {"cleaned_rows": "Mantidas", "rows_removed": "Removidas"}
            )
            fig = px.bar(
                melt, x="label", y="linhas", color="tipo", barmode="stack",
                color_discrete_map={"Mantidas": GREEN_600, "Removidas": "#ef4444"},
                labels={"label": "", "linhas": "Linhas", "tipo": ""},
            )
            fig.update_traces(
                marker_line_width=0,
                hovertemplate="<b>%{x}</b><br>%{fullData.name}: <b>%{y:,.0f}</b><extra></extra>",
            )
            chart(style_fig(fig, height=380, bargap=0.30))

            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            st.markdown("#### Retenção de dados após limpeza")
            st.caption("Percentual de linhas preservadas em cada dataset — quanto maior, melhor a qualidade da fonte bruta.")
            retention_df = cleaning_df.sort_values("retention_pct")
            fig = px.bar(
                retention_df, x="retention_pct", y="label", orientation="h",
                text=retention_df["retention_pct"].map(lambda v: f"{v:.2f}%"),
                color="retention_pct",
                color_continuous_scale=GREEN_SCALE, range_x=[0, 105],
            )
            fig.update_traces(
                marker_line_width=0,
                textposition="outside",
                textfont=dict(color=INK_900, size=12), cliponaxis=False,
                hovertemplate="<b>%{y}</b><br>Retenção: <b>%{x:.2f}%</b><extra></extra>",
            )
            chart(style_fig(
                fig, height=320, coloraxis_showscale=False,
                xaxis=dict(ticksuffix="%", range=[0, 110],
                           gridcolor="rgba(15,23,42,0.06)",
                           tickfont=dict(color=INK_700)),
                yaxis=dict(tickfont=dict(color=INK_900, size=12),
                           gridcolor="rgba(15,23,42,0.0)"),
                bargap=0.30,
            ))

            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Duplicatas removidas")
                max_dupes = max(int(cleaning_df["duplicates_dropped"].max() or 0), 1)
                fig = px.bar(
                    cleaning_df, x="label", y="duplicates_dropped",
                    text_auto=True, color_discrete_sequence=[GREEN_500],
                    labels={"label": "", "duplicates_dropped": "Duplicatas"},
                )
                fig.update_traces(
                    textposition="outside", marker_line_width=0,
                    textfont=dict(color=INK_900, size=12), cliponaxis=False,
                    hovertemplate="<b>%{x}</b><br>Duplicatas: <b>%{y:,.0f}</b><extra></extra>",
                )
                chart(style_fig(fig, height=320, bargap=0.40,
                                yaxis=dict(range=[0, max_dupes * 1.25],
                                           gridcolor="rgba(15,23,42,0.06)",
                                           tickfont=dict(color=INK_700)),
                                xaxis=dict(tickfont=dict(color=INK_900),
                                           gridcolor="rgba(15,23,42,0.06)")))
            with col2:
                st.markdown("#### Colunas recodificadas (sim/não/ignorado)")
                max_rec = max(int(cleaning_df["n_yes_no_recoded"].max() or 0), 1)
                fig = px.bar(
                    cleaning_df, x="label", y="n_yes_no_recoded",
                    text_auto=True, color_discrete_sequence=[GREEN_700],
                    labels={"label": "", "n_yes_no_recoded": "Colunas"},
                )
                fig.update_traces(
                    textposition="outside", marker_line_width=0,
                    textfont=dict(color=INK_900, size=12), cliponaxis=False,
                    hovertemplate="<b>%{x}</b><br>Colunas recod.: <b>%{y}</b><extra></extra>",
                )
                chart(style_fig(fig, height=320, bargap=0.40,
                                yaxis=dict(range=[0, max_rec * 1.25],
                                           gridcolor="rgba(15,23,42,0.06)",
                                           tickfont=dict(color=INK_700)),
                                xaxis=dict(tickfont=dict(color=INK_900),
                                           gridcolor="rgba(15,23,42,0.06)")))

            st.markdown("#### Detalhamento")
            show = cleaning_df[[
                "label", "source_file", "raw_rows", "cleaned_rows",
                "retention_pct", "duplicates_dropped", "rows_with_invalid_dates",
                "n_yes_no_recoded", "n_date_cols_parsed",
            ]].rename(columns={
                "label": "Dataset", "source_file": "Arquivo",
                "raw_rows": "Brutas", "cleaned_rows": "Limpas",
                "retention_pct": "Retenção %", "duplicates_dropped": "Duplicatas",
                "rows_with_invalid_dates": "Datas inválidas",
                "n_yes_no_recoded": "Cols recod.", "n_date_cols_parsed": "Cols data",
            })
            st.dataframe(show, use_container_width=True, hide_index=True)

    with tab2:
        if leakage_df.empty:
            empty_state("Sem relatórios de split.")
        else:
            st.markdown("#### Tamanho dos splits (train / val / test)")
            melt = leakage_df.melt(
                id_vars="label", value_vars=["train", "val", "test"],
                var_name="split", value_name="linhas",
            )
            fig = px.bar(
                melt, x="label", y="linhas", color="split", barmode="stack",
                color_discrete_map={"train": GREEN_700, "val": GREEN_500, "test": GREEN_300},
                labels={"label": "", "linhas": "Linhas", "split": "Split"},
            )
            fig.update_traces(
                marker_line_width=0,
                hovertemplate="<b>%{x}</b><br>%{fullData.name}: <b>%{y:,.0f}</b><extra></extra>",
            )
            chart(style_fig(fig, height=380, bargap=0.30))

            st.markdown("#### Proporção dos splits (%)")
            prop = leakage_df.copy()
            for col in ("train", "val", "test"):
                prop[col] = np.where(prop["total"] > 0, 100 * prop[col] / prop["total"], 0)
            melt = prop.melt(
                id_vars="label", value_vars=["train", "val", "test"],
                var_name="split", value_name="pct",
            )
            fig = px.bar(
                melt, x="label", y="pct", color="split", barmode="group",
                color_discrete_map={"train": GREEN_700, "val": GREEN_500, "test": GREEN_300},
                text_auto=".1f", labels={"label": "", "pct": "%", "split": "Split"},
            )
            fig.update_traces(
                textposition="outside", marker_line_width=0,
                textfont=dict(color=INK_900, size=12), cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>%{fullData.name}: <b>%{y:.1f}%</b><extra></extra>",
            )
            chart(style_fig(fig, height=340, bargap=0.30, bargroupgap=0.10,
                            yaxis=dict(range=[0, 100], ticksuffix="%",
                                       gridcolor="rgba(15,23,42,0.06)",
                                       tickfont=dict(color=INK_700)),
                            xaxis=dict(tickfont=dict(color=INK_900))))

    with tab3:
        if leakage_df.empty:
            empty_state("Sem relatórios de vazamento.")
        else:
            n_ok = int(leakage_df["temporal_order_ok"].sum())
            n_dupes = int(leakage_df["duplicate_rows_across_splits"].sum())
            n_overlaps = int(leakage_df["n_group_overlaps"].sum())
            c1, c2, c3 = st.columns(3)
            c1.metric("Splits com ordem temporal OK", f"{n_ok}/{len(leakage_df)}")
            c2.metric("Linhas duplicadas entre splits", fmt_int(n_dupes))
            c3.metric("Sobreposições de grupo", fmt_int(n_overlaps))

            if n_dupes == 0 and n_overlaps == 0:
                callout(
                    "Zero vazamento entre splits",
                    "Todos os 4 datasets passaram nas checagens de duplicatas e de sobreposição de grupos. "
                    "Métricas confiáveis e prontas para produção.",
                    big_number="0",
                    icon="🛡️",
                )

            st.markdown("#### Status por dataset")
            for _, row in leakage_df.iterrows():
                clean = (
                    row["duplicate_rows_across_splits"] == 0
                    and row["n_group_overlaps"] == 0
                    and row["n_errors"] == 0
                )
                cols = st.columns([3, 2, 2, 2, 2])
                cols[0].markdown(
                    f"**{row['label']}**  \n<span style='color:{INK_700};font-size:0.85rem;'>"
                    f"`{row['strategy']}`</span>",
                    unsafe_allow_html=True,
                )
                cols[1].markdown(
                    "Ordem temporal  \n"
                    + status_pill(bool(row["temporal_order_ok"])),
                    unsafe_allow_html=True,
                )
                cols[2].markdown(
                    "Sem duplicatas  \n"
                    + status_pill(row["duplicate_rows_across_splits"] == 0),
                    unsafe_allow_html=True,
                )
                cols[3].markdown(
                    "Sem overlap  \n" + status_pill(row["n_group_overlaps"] == 0),
                    unsafe_allow_html=True,
                )
                cols[4].markdown(
                    "Geral  \n" + status_pill(clean, "Aprovado", "Revisar"),
                    unsafe_allow_html=True,
                )

            st.caption(
                "A checagem de vazamento garante que nenhum registro de teste "
                "vaze para o treino — essencial para métricas confiáveis."
            )


# ===========================================================================
# PÁGINA: COMPARAÇÃO DE MODELOS
# ===========================================================================

def page_comparison() -> None:
    st.markdown(
        """
        <div class="dc-hero">
          <h1>Comparação de modelos</h1>
          <p>Random Forest × Árvore de Decisão — validação cruzada e teste, em ambas as tarefas.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not disease and not severity:
        empty_state("Sem relatórios de ML. Rode o serviço **ml-trainer**.")
        return

    rows = []
    for rep in (disease, severity):
        if not rep:
            continue
        task = rep["model_name"].replace("_", " ").title()
        for item in rep.get("leaderboard", []):
            rows.append({
                "Tarefa": task,
                "Algoritmo": item["algorithm"].replace("_", " ").title(),
                "Acurácia": item["accuracy"],
                "Macro-F1": item["macro_f1"],
                "CV F1 (média)": item["cv_f1_mean"],
                "Selecionado": item["algorithm"] == rep.get("selected_model"),
            })
    df = pd.DataFrame(rows)

    metric = st.selectbox(
        "Métrica em destaque", ["Macro-F1", "Acurácia", "CV F1 (média)"], index=0
    )
    fig = px.bar(
        df, x="Tarefa", y=metric, color="Algoritmo", barmode="group",
        text_auto=".3f", color_discrete_sequence=[GREEN_600, GREEN_400], range_y=[0, 1.1],
    )
    fig.update_traces(
        textposition="outside", marker_line_width=0,
        textfont=dict(color=INK_900, size=12), cliponaxis=False,
        hovertemplate="<b>%{x}</b><br>%{fullData.name}: <b>%{y:.3f}</b><extra></extra>",
    )
    chart(style_fig(fig, height=400, bargap=0.30, bargroupgap=0.10))

    st.markdown("#### Tabela comparativa")
    styled = df.copy()
    for col in ("Acurácia", "Macro-F1", "CV F1 (média)"):
        styled[col] = styled[col].map(lambda v: f"{v:.4f}")
    styled["Selecionado"] = styled["Selecionado"].map({True: "✅ sim", False: ""})
    st.dataframe(styled, use_container_width=True, hide_index=True)

    st.markdown("#### Modelo selecionado por tarefa")
    cols = st.columns(2)
    for i, rep in enumerate((disease, severity)):
        if not rep:
            continue
        with cols[i]:
            best = rep.get("selected_model", "—").replace("_", " ").title()
            task = rep["model_name"].replace("_", " ").title()
            cv_mean = rep.get("cv_f1_mean", 0)
            cv_std = rep.get("cv_f1_std", 0)
            st.markdown(
                f"""
                <div class="dc-card">
                  <h4>{task}</h4>
                  <div style="display:flex;align-items:baseline;gap:10px;margin-top:6px;">
                    <span style="font-size:1.4rem;font-weight:800;color:{INK_900};">{best}</span>
                    <span class="dc-pill dc-ok">selecionado</span>
                  </div>
                  <div style="color:{INK_700};font-size:0.9rem;margin-top:10px;font-weight:500;">
                    CV F1: <b style="color:{GREEN_700};">{cv_mean:.4f}</b> ± {cv_std:.4f}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ===========================================================================
# PÁGINA: PREVISÕES AO VIVO
# ===========================================================================

# UFs brasileiras (código IBGE de 2 dígitos)
UFS = [
    ("PE", 26, 261160),  # Recife (cidade do projeto)
    ("SP", 35, 355030),
    ("RJ", 33, 330455),
    ("MG", 31, 310620),
    ("BA", 29, 292740),
    ("CE", 23, 230440),
    ("DF", 53, 530010),
    ("RS", 43, 431490),
    ("PR", 41, 410690),
    ("AM", 13, 130260),
]
UF_BY_CODE = {code: (sigla, mun) for sigla, code, mun in UFS}

# Sintomas SINAN principais (presentes no modelo de doença)
SINAN_SYMPTOMS = [
    "FEBRE", "MIALGIA", "CEFALEIA", "EXANTEMA", "VOMITO", "NAUSEA",
    "DOR_COSTAS", "CONJUNTVIT", "ARTRITE", "ARTRALGIA", "PETEQUIA_N",
    "LEUCOPENIA", "LACO", "DOR_RETRO",
]
# Sintomas SRAG presentes no modelo de doença
SRAG_SYMPTOMS = [
    "TOSSE", "GARGANTA", "DISPNEIA", "DESC_RESP", "DIARREIA", "FADIGA",
]
COMORBIDITIES = [
    "DIABETES", "HIPERTENSA", "HEMATOLOG", "HEPATOPAT", "RENAL",
    "ACIDO_PEPT", "AUTO_IMUNE", "CARDIOPATI", "NEUROLOGIC", "PNEUMOPATI",
    "IMUNODEPRE", "OBESIDADE",
]
CONTEXT_BOOLS = ["HOSPITALIZ"]


# Exemplos didáticos: previsões realistas dos dois modelos para vitrine.
# Usados quando o modelo MLflow não está disponível no ambiente.
DEMO_PREDICTIONS = {
    "dengue_classica": {
        "features": {"FEBRE": 1, "MIALGIA": 1, "CEFALEIA": 1, "DOR_RETRO": 1,
                     "ARTRALGIA": 1, "age_years": 32, "sex_M": 1,
                     "uf_code": 26, "munic_code": 261160,
                     "notification_month": 4, "notification_week": 15},
        "disease": {
            "predicted_class": "dengue",
            "probabilities": {"dengue": 0.82, "chikungunya": 0.10, "zika": 0.04, "influenza": 0.04},
        },
        "severity": {
            "predicted_class": "baixo",
            "probabilities": {"baixo": 0.91, "medio": 0.07, "alto": 0.02},
        },
    },
}


def features_from_form(state: dict) -> dict:
    """Constrói o dicionário de features completo a partir do estado do form."""
    feats: dict = {}
    for col in SINAN_SYMPTOMS + SRAG_SYMPTOMS + COMORBIDITIES + CONTEXT_BOOLS:
        feats[col] = 1.0 if state.get(col, False) else 0.0
    feats["age_years"] = float(state.get("age", 30))
    feats["sex_M"] = 1.0 if state.get("sex", "Masculino") == "Masculino" else 0.0
    feats["notification_month"] = float(state.get("month", 4))
    feats["notification_week"] = float(state.get("week", 15))
    feats["uf_code"] = float(state.get("uf_code", 26))
    feats["munic_code"] = float(state.get("munic_code", 261160))
    return feats


def proba_bar(proba: dict[str, float], colors: dict[str, str], title: str) -> go.Figure:
    items = sorted(proba.items(), key=lambda kv: kv[1], reverse=True)
    labels = [k.title() for k, _ in items]
    values = [100 * v for _, v in items]
    fig = go.Figure(
        go.Bar(
            x=values, y=labels, orientation="h",
            text=[f"<b>{v:.1f}%</b>" for v in values],
            textposition="outside",
            cliponaxis=False,
            insidetextfont=dict(color="#ffffff"),
            outsidetextfont=dict(color=INK_900, size=13),
            marker=dict(
                color=[colors.get(l.lower(), GREEN_500) for l in labels],
                line=dict(width=0),
            ),
            hovertemplate="<b>%{y}</b><br>Probabilidade: <b>%{x:.2f}%</b><extra></extra>",
        )
    )
    return style_fig(
        fig, height=260,
        title=dict(text=title, font=dict(color=INK_900, size=14), x=0, xanchor="left"),
        xaxis=dict(range=[0, 115], ticksuffix="%",
                   gridcolor="rgba(15,23,42,0.06)",
                   tickfont=dict(color=INK_700, size=12), showline=False),
        yaxis=dict(autorange="reversed", gridcolor="rgba(15,23,42,0.06)",
                   tickfont=dict(color=INK_900, size=13, family="Inter"), showline=False),
        showlegend=False,
        bargap=0.35,
    )


def render_prediction_card(label: str, predicted_class: str, top_prob: float,
                           severity: bool = False) -> None:
    cls = "dc-predict-result dc-predict-severity" if severity else "dc-predict-result"
    st.markdown(
        f"""
        <div class="{cls}">
          <div class="dc-pred-label">{label}</div>
          <div class="dc-pred-value">{predicted_class.title()}</div>
          <div class="dc-pred-conf">Confiança · {top_prob*100:.1f}%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_predict() -> None:
    st.markdown(
        """
        <div class="dc-hero">
          <h1>Previsões ao vivo</h1>
          <p>Insira o quadro clínico de um paciente e veja os dois classificadores em ação — doença mais provável e severidade clínica esperada.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    available = da.model_available()
    if available:
        status_html = '<span class="dc-status-large">Modelos prontos · Random Forest + Árvore de Decisão</span>'
    else:
        status_html = (
            '<span class="dc-status-large dc-status-warn">'
            'Modelos indisponíveis — exibindo cenário didático</span>'
        )
    st.markdown(status_html, unsafe_allow_html=True)
    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    if "predict_state" not in st.session_state:
        st.session_state.predict_state = {
            "age": 30, "sex": "Masculino", "month": 4, "week": 15,
            "uf_code": 26, "munic_code": 261160,
        }

    state = st.session_state.predict_state

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
    st.markdown("#### Dados do paciente")
    st.caption("Informe demografia e contexto temporal da notificação.")
    demog = st.columns(4)
    with demog[0]:
        state["age"] = st.slider("Idade (anos)", 0, 100, int(state.get("age", 30)))
    with demog[1]:
        state["sex"] = st.radio("Sexo", ["Masculino", "Feminino"],
                                index=0 if state.get("sex", "Masculino") == "Masculino" else 1,
                                horizontal=True)
    with demog[2]:
        state["month"] = st.slider("Mês da notificação", 1, 12, int(state.get("month", 4)))
    with demog[3]:
        state["week"] = st.slider("Semana epidemiológica", 1, 53, int(state.get("week", 15)))

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    uf_row = st.columns(2)
    with uf_row[0]:
        uf_labels = [f"{sigla} ({code})" for sigla, code, _ in UFS]
        codes = [code for _, code, _ in UFS]
        idx = codes.index(int(state.get("uf_code", 26))) if int(state.get("uf_code", 26)) in codes else 0
        choice = st.selectbox("UF", uf_labels, index=idx)
        chosen_code = codes[uf_labels.index(choice)]
        state["uf_code"] = chosen_code
        sigla, default_mun = UF_BY_CODE[chosen_code]
        if str(state.get("munic_code", default_mun))[:2] != str(chosen_code):
            state["munic_code"] = default_mun
    with uf_row[1]:
        state["munic_code"] = st.number_input(
            "Município (código IBGE)", min_value=100000, max_value=999999,
            value=int(state.get("munic_code", 261160)), step=1,
        )

    st.markdown("<div style='height: 22px;'></div>", unsafe_allow_html=True)
    st.markdown("#### Quadro clínico")
    st.caption("Marque os sinais e comorbidades presentes no paciente.")
    tabs = st.tabs(["Sintomas (arboviroses)", "Sintomas respiratórios", "Comorbidades", "Contexto"])
    with tabs[0]:
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        sym_cols = st.columns(4)
        for i, col in enumerate(SINAN_SYMPTOMS):
            label = da.feature_label(col)
            state[col] = sym_cols[i % 4].checkbox(label, value=bool(state.get(col, False)),
                                                  key=f"sym_{col}")
    with tabs[1]:
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        sym_cols = st.columns(4)
        for i, col in enumerate(SRAG_SYMPTOMS):
            label = da.feature_label(col)
            state[col] = sym_cols[i % 4].checkbox(label, value=bool(state.get(col, False)),
                                                  key=f"resp_{col}")
    with tabs[2]:
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        co_cols = st.columns(4)
        for i, col in enumerate(COMORBIDITIES):
            label = da.feature_label(col)
            state[col] = co_cols[i % 4].checkbox(label, value=bool(state.get(col, False)),
                                                  key=f"co_{col}")
    with tabs[3]:
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        ctx_cols = st.columns(4)
        for i, col in enumerate(CONTEXT_BOOLS):
            label = da.feature_label(col)
            state[col] = ctx_cols[i % 4].checkbox(label, value=bool(state.get(col, False)),
                                                   key=f"ctx_{col}")

    st.session_state.predict_state = state

    st.markdown("<div style='height: 22px;'></div>", unsafe_allow_html=True)
    btn_cols = st.columns([1, 3])
    with btn_cols[0]:
        go_predict = st.button("Rodar predição", use_container_width=True, type="primary")

    if not go_predict:
        st.caption("Ajuste os campos acima e clique em **Rodar predição** para ver a saída dos modelos.")
        return

    feats = features_from_form(state)
    result = da.predict_full_safe(feats) if available else None

    if result is None:
        st.warning(
            "Os artefatos MLflow não foram encontrados ou houve falha ao carregá-los. "
            "Mostrando um cenário didático com base no padrão clínico fornecido."
        )
        result = {
            "disease": DEMO_PREDICTIONS["dengue_classica"]["disease"],
            "severity": DEMO_PREDICTIONS["dengue_classica"]["severity"],
        }

    d = result["disease"]
    s = result["severity"]
    d_top = max(d["probabilities"].values())
    s_top = max(s["probabilities"].values())

    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    st.markdown("### Resultado da predição")
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    res_cols = st.columns(2, gap="large")
    with res_cols[0]:
        render_prediction_card("Doença prevista", d["predicted_class"], d_top, severity=False)
        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
        chart(proba_bar(d["probabilities"], DISEASE_COLORS, "Probabilidade por doença"))
    with res_cols[1]:
        render_prediction_card("Severidade prevista", s["predicted_class"], s_top, severity=True)
        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
        chart(proba_bar(s["probabilities"], SEVERITY_COLORS, "Probabilidade por severidade"))

    # Quais features estão "ativas" e cruzam com a importância do modelo
    if disease:
        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
        st.markdown("#### Sinais clínicos relevantes (peso no modelo de doença)")
        importance = disease.get("top_features", {})
        active = {col: importance.get(col, 0.0)
                  for col, val in feats.items() if val and importance.get(col, 0) > 0}
        if active:
            df = pd.DataFrame({
                "Feature": [da.feature_label(k) for k in active],
                "Importância": list(active.values()),
            }).sort_values("Importância")
            max_imp = float(df["Importância"].max() or 1)
            fig = px.bar(
                df, x="Importância", y="Feature", orientation="h",
                color="Importância", color_continuous_scale=GREEN_SCALE,
                text=df["Importância"].map(lambda v: f"{v:.3f}"),
            )
            fig.update_traces(
                marker_line_width=0,
                textposition="outside",
                textfont=dict(color=INK_900, size=11), cliponaxis=False,
                hovertemplate="<b>%{y}</b><br>Importância: <b>%{x:.4f}</b><extra></extra>",
            )
            chart(style_fig(
                fig, height=max(240, 38 * len(df)),
                coloraxis_showscale=False,
                xaxis=dict(range=[0, max_imp * 1.18],
                           gridcolor="rgba(15,23,42,0.06)",
                           tickfont=dict(color=INK_700)),
                yaxis=dict(tickfont=dict(color=INK_900, size=12),
                           gridcolor="rgba(15,23,42,0.0)"),
                bargap=0.30,
            ))
        else:
            st.caption("Nenhum sinal informado coincide com as features mais importantes.")


# ===========================================================================
# DETALHE DE MODELO (reutilizável)
# ===========================================================================

def render_model_detail(rep: dict | None, colors: dict, task_label: str) -> None:
    if not rep:
        empty_state(f"Sem relatório para {task_label}. Rode o serviço **ml-trainer**.")
        return

    labels = rep.get("confusion_matrix_labels", [])
    # KPIs em destaque
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_hero("Acurácia", pct(rep.get("accuracy")),
                 f"Sobre {fmt_int(rep.get('n_test'))} amostras de teste")
    with c2:
        kpi_hero("Macro-F1", pct(rep.get("macro_f1")),
                 "Média harmônica entre precisão e recall por classe")
    with c3:
        kpi_hero("CV F1 (média)", fmt_float(rep.get("cv_f1_mean"), 3),
                 f"± {fmt_float(rep.get('cv_f1_std'), 3)}")
    with c4:
        kpi_hero("Algoritmo", rep.get("selected_model", "—").replace("_", " ").title(),
                 "Selecionado pela maior CV F1")

    # Gauges destacando o modelo
    g1, g2, g3 = st.columns(3)
    with g1:
        chart(gauge(rep.get("accuracy", 0), "Acurácia"))
    with g2:
        chart(gauge(rep.get("macro_f1", 0), "Macro-F1"))
    with g3:
        chart(gauge(rep.get("cv_f1_mean", 0), "CV F1"))

    # Destaques de classes (melhores F1)
    f1c = rep.get("f1_per_class", {})
    if f1c:
        top = sorted(f1c.items(), key=lambda kv: -kv[1])[:3]
        cols = st.columns(len(top))
        for col, (label, f1) in zip(cols, top):
            with col:
                callout(
                    f"Classe {label}",
                    f"F1-score elevado, evidenciando boa separabilidade.",
                    big_number=f"{f1:.3f}",
                    icon="🎯",
                )

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown("#### Matriz de confusão")
        normalize = st.toggle("Normalizar por linha (recall)", value=False,
                              key=f"norm_{task_label}")
        cm = rep.get("confusion_matrix")
        if cm and labels:
            chart(confusion_heatmap(cm, labels, normalize))
        else:
            empty_state("Sem matriz de confusão.")

    with right:
        st.markdown("#### F1-score por classe")
        if f1c:
            dfc = pd.DataFrame({
                "Classe": [c.title() for c in f1c.keys()],
                "F1": list(f1c.values()),
            })
            color_map = {k.title(): v for k, v in colors.items()}
            fig = px.bar(
                dfc, x="F1", y="Classe", orientation="h", text_auto=".3f",
                color="Classe", color_discrete_map=color_map, range_x=[0, 1.1],
            )
            fig.update_traces(
                textposition="outside", marker_line_width=0,
                textfont=dict(color=INK_900, size=12), cliponaxis=False,
                hovertemplate="<b>%{y}</b><br>F1-score: <b>%{x:.3f}</b><extra></extra>",
            )
            chart(style_fig(fig, height=320, showlegend=False, bargap=0.40))

        cr = rep.get("classification_report", {})
        if cr:
            st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
            st.markdown("#### Precisão × Recall por classe")
            rows = []
            for lbl in labels:
                if lbl in cr:
                    rows.append({"Classe": lbl, "Precisão": cr[lbl]["precision"],
                                 "Recall": cr[lbl]["recall"]})
            if rows:
                dfm = pd.DataFrame(rows)
                dfm["Classe"] = dfm["Classe"].str.title()
                dfm = dfm.melt(id_vars="Classe", var_name="Métrica", value_name="Valor")
                fig = px.bar(
                    dfm, x="Classe", y="Valor", color="Métrica", barmode="group",
                    text_auto=".2f", color_discrete_sequence=[GREEN_700, GREEN_400],
                    range_y=[0, 1.1],
                )
                fig.update_traces(
                    textposition="outside", marker_line_width=0,
                    textfont=dict(color=INK_900, size=11), cliponaxis=False,
                    hovertemplate="<b>%{x}</b><br>%{fullData.name}: <b>%{y:.3f}</b><extra></extra>",
                )
                chart(style_fig(fig, height=300, bargap=0.30, bargroupgap=0.10))


def page_disease() -> None:
    st.markdown(
        """
        <div class="dc-hero">
          <h1>Classificador de doença</h1>
          <p>Dengue × Chikungunya × Zika × Influenza, a partir de sintomas, comorbidades, demografia e geografia.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_model_detail(disease, DISEASE_COLORS, "doença")


def page_severity() -> None:
    st.markdown(
        """
        <div class="dc-hero">
          <h1>Classificador de severidade</h1>
          <p>Severidade clínica: baixo × médio × alto — apoiando a priorização de cuidado na APS.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_model_detail(severity, SEVERITY_COLORS, "severidade")


# ===========================================================================
# PÁGINA: EXPLORAÇÃO DE DADOS
# ===========================================================================

def page_explore() -> None:
    st.markdown(
        """
        <div class="dc-hero">
          <h1>Exploração de dados limpos</h1>
          <p>Distribuições calculadas sobre os parquets gerados pelo ETL — apenas os 4 datasets ativos.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    datasets = da.list_interim_datasets()
    if not datasets:
        empty_state(
            f"Nenhum parquet ativo encontrado em `{da.INTERIM_DIR}`. "
            "Rode o ETL local (`python -m src.etl.run_pipeline`) para gerá-los."
        )
        return

    default = "sinan_dengue" if "sinan_dengue" in datasets else datasets[0]
    dataset = st.selectbox(
        "Dataset", datasets, index=datasets.index(default),
        format_func=da.pretty_dataset,
    )
    path = da.interim_path(dataset)
    mtime = da.file_mtime(path)
    path_str = str(path)

    schema = da.parquet_schema(path_str, mtime)
    n_rows = da.parquet_num_rows(path_str, mtime)
    if not schema:
        empty_state("Não foi possível ler o schema deste parquet.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Linhas", fmt_int(n_rows))
    c2.metric("Colunas", fmt_int(len(schema)))
    sample_n = 150_000
    c3.metric("Amostra p/ gráficos", fmt_int(min(sample_n, n_rows)))

    age_col = da.detect_age_column(schema)
    date_col = da.detect_date_column(schema)
    sex_col = da.detect_sex_column(schema)
    class_col = da.detect_class_column(schema)

    needed = [c for c in (age_col, date_col, sex_col, class_col) if c]
    bool_candidates = [
        c for c in schema
        if c.isupper() and c not in needed and not c.startswith("DT_")
        and not c.startswith("ID_") and len(c) >= 3
    ][:40]

    tab1, tab2, tab3 = st.tabs(["📊 Distribuições", "🦠 Sintomas", "🗓️ Temporal"])

    with tab1:
        cols = st.columns(2)
        with cols[0]:
            st.markdown("#### Idade")
            if age_col:
                df = da.load_columns(path_str, (age_col,), sample_n, mtime)
                if not df.empty:
                    s = pd.to_numeric(df[age_col], errors="coerce")
                    s = s[(s >= 0) & (s <= 120)]
                    fig = px.histogram(s, nbins=40, color_discrete_sequence=[GREEN_600])
                    fig.update_traces(
                        marker_line_width=0,
                        hovertemplate="Idade: <b>%{x}</b><br>Casos: <b>%{y:,}</b><extra></extra>",
                    )
                    chart(style_fig(fig, height=320, showlegend=False,
                                    bargap=0.06,
                                    xaxis_title="Idade (anos)",
                                    yaxis_title="Casos"))
            else:
                empty_state("Sem coluna de idade neste dataset.")
        with cols[1]:
            st.markdown("#### Sexo")
            if sex_col:
                df = da.load_columns(path_str, (sex_col,), sample_n, mtime)
                if not df.empty:
                    vc = df[sex_col].astype(str).str.upper().replace(
                        {"M": "Masculino", "F": "Feminino"})
                    vc = vc.value_counts().head(6)
                    fig = px.pie(names=vc.index, values=vc.values, hole=0.58,
                                 color_discrete_sequence=PALETTE)
                    fig.update_traces(
                        textinfo="label+percent",
                        textfont=dict(color="#ffffff", size=13, family="Inter"),
                        marker=dict(line=dict(color="#ffffff", width=3)),
                        hovertemplate="<b>%{label}</b><br>Casos: <b>%{value:,}</b><br>Fatia: <b>%{percent}</b><extra></extra>",
                    )
                    chart(style_fig(fig, height=320, showlegend=False))
            else:
                empty_state("Sem coluna de sexo neste dataset.")

        if class_col:
            st.markdown(f"#### Distribuição de `{class_col}`")
            df = da.load_columns(path_str, (class_col,), sample_n, mtime)
            if not df.empty:
                vc = df[class_col].astype(str).value_counts().head(15)
                max_v = int(vc.max() or 1)
                fig = px.bar(x=vc.index, y=vc.values, text_auto=True,
                             color_discrete_sequence=[GREEN_500],
                             labels={"x": class_col, "y": "Frequência"})
                fig.update_traces(
                    textposition="outside", marker_line_width=0,
                    textfont=dict(color=INK_900, size=11), cliponaxis=False,
                    hovertemplate=f"<b>{class_col}</b>: %{{x}}<br>Casos: <b>%{{y:,}}</b><extra></extra>",
                )
                chart(style_fig(fig, height=340, bargap=0.30,
                                yaxis=dict(range=[0, max_v * 1.18],
                                           gridcolor="rgba(15,23,42,0.06)",
                                           tickfont=dict(color=INK_700))))

    with tab2:
        st.markdown("#### Prevalência de sintomas / comorbidades")
        if not bool_candidates:
            empty_state("Sem colunas categóricas detectadas.")
        else:
            picked = st.multiselect(
                "Variáveis", bool_candidates,
                default=bool_candidates[:12],
                format_func=lambda c: da.feature_label(c),
            )
            if picked:
                df = da.load_columns(path_str, tuple(picked), sample_n, mtime)
                if not df.empty:
                    prevs = []
                    for col in picked:
                        s = df[col]
                        if s.dtype == "boolean" or s.dtype == bool:
                            rate = float(s.dropna().astype(float).mean()) if s.notna().any() else 0.0
                        else:
                            num = pd.to_numeric(s, errors="coerce")
                            rate = float((num == 1).mean()) if num.notna().any() else 0.0
                        prevs.append({"Variável": da.feature_label(col), "Prevalência": rate})
                    dfp = pd.DataFrame(prevs).sort_values("Prevalência")
                    fig = px.bar(
                        dfp, x="Prevalência", y="Variável", orientation="h",
                        text_auto=".1%", color="Prevalência",
                        color_continuous_scale=GREEN_SCALE, range_x=[0, 1.05],
                    )
                    fig.update_traces(
                        textposition="outside", marker_line_width=0,
                        textfont=dict(color=INK_900, size=11), cliponaxis=False,
                        hovertemplate="<b>%{y}</b><br>Prevalência: <b>%{x:.1%}</b><extra></extra>",
                    )
                    chart(style_fig(
                        fig, height=max(340, 30 * len(picked)),
                        coloraxis_showscale=False,
                        xaxis=dict(tickformat=".0%",
                                   gridcolor="rgba(15,23,42,0.06)",
                                   tickfont=dict(color=INK_700)),
                        yaxis=dict(tickfont=dict(color=INK_900, size=12),
                                   gridcolor="rgba(15,23,42,0.0)"),
                        bargap=0.25,
                    ))

    with tab3:
        st.markdown("#### Notificações ao longo do tempo")
        if date_col:
            df = da.load_columns(path_str, (date_col,), 0, mtime)
            if not df.empty:
                s = pd.to_datetime(df[date_col], errors="coerce").dropna()
                if not s.empty:
                    ts = s.dt.to_period("M").dt.to_timestamp().value_counts().sort_index()
                    fig = px.area(x=ts.index, y=ts.values,
                                  color_discrete_sequence=[GREEN_500],
                                  labels={"x": "Mês", "y": "Notificações"})
                    fig.update_traces(
                        line=dict(color=GREEN_700, width=2.5),
                        fillcolor="rgba(16,185,129,0.22)",
                        hovertemplate="%{x|%b/%Y}<br>Notificações: <b>%{y:,}</b><extra></extra>",
                    )
                    chart(style_fig(fig, height=380,
                                    xaxis=dict(title="Mês",
                                               gridcolor="rgba(15,23,42,0.06)",
                                               tickfont=dict(color=INK_700)),
                                    yaxis=dict(title="Notificações",
                                               gridcolor="rgba(15,23,42,0.06)",
                                               tickfont=dict(color=INK_700))))
                else:
                    empty_state("Coluna de data sem valores válidos.")
        else:
            empty_state("Sem coluna de data neste dataset.")


# ---------------------------------------------------------------------------
# Roteamento
# ---------------------------------------------------------------------------

PAGES = {
    "Visão Geral": page_overview,
    "ETL & Qualidade de Dados": page_etl,
    "Comparação de Modelos": page_comparison,
    "Previsões ao Vivo": page_predict,
    "Classificador de Doença": page_disease,
    "Classificador de Severidade": page_severity,
    "Exploração de Dados": page_explore,
}

PAGES[page]()
