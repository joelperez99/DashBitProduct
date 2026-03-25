import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date
import calendar
import os

# ─── CONFIG ──────────────────────────────────────────────────────────────────
SHEET_ID = "1LOnmIKg0IZtoftPYoNIIfWWl3oJTP-DH6AEZGWPZci4"
CREDS_FILE = os.path.join(os.path.dirname(__file__), "master-plateau-489706-m4-21b87b659f87.json")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

ALL_TIERS = ["S", "A", "B", "C", "D"]

st.set_page_config(page_title="Dashboard de Ganancias", layout="wide", page_icon="📈")

# ─── STYLES ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  body, .stApp { background-color: #0d1117; color: #e6edf3; }
  .block-container { padding: 1rem 2rem; }

  /* Day card */
  .day-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px 10px;
    text-align: center;
    min-height: 80px;
    cursor: pointer;
    transition: border-color .15s;
    position: relative;
  }
  .day-card:hover { border-color: #58a6ff; }
  .day-card.best  { border: 2px solid #3fb950; }
  .day-card.worst { border: 2px solid #f85149; }

  .day-num   { font-size: 11px; color: #8b949e; text-align: left; }
  .day-pnl   { font-size: 18px; font-weight: 700; margin: 4px 0 2px; }
  .day-meta  { font-size: 10px; color: #8b949e; }
  .pnl-pos   { color: #3fb950; }
  .pnl-neg   { color: #f85149; }
  .pnl-zero  { color: #8b949e; }

  /* Summary cards */
  .sum-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 14px 18px;
    text-align: center;
  }
  .sum-label { font-size: 12px; color: #8b949e; margin-bottom: 4px; }
  .sum-value { font-size: 22px; font-weight: 700; }

  /* Detail panel */
  .det-card {
    background: #f8f5f0;
    border-radius: 10px;
    padding: 18px 22px;
    color: #1a1a1a;
    margin-bottom: 12px;
  }
  .det-label { font-size: 12px; color: #666; }
  .det-value { font-size: 24px; font-weight: 700; }
  .det-green { color: #2e7d32; }
  .det-red   { color: #c62828; }

  .seq-pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
    margin: 2px 2px;
  }
  .pill-si { background: #c8e6c9; color: #1b5e20; }
  .pill-no { background: #ffcdd2; color: #b71c1c; }

  .header-title {
    font-size: 18px;
    font-weight: 700;
    color: #e6edf3;
    margin-bottom: 16px;
  }

  /* ── Transiciones del panel de detalle ─────────────────────────────── */
  @keyframes fadeSlideUp {
    0%   { opacity: 0; transform: translateY(22px) scale(0.98); filter: blur(3px); }
    60%  { opacity: .85; filter: blur(.5px); }
    100% { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
  }
  @keyframes wipeLine {
    0%   { transform: scaleX(0); opacity: 1; }
    100% { transform: scaleX(1); opacity: 1; }
  }
  @keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
  }
  @keyframes calPulse {
    0%   { box-shadow: 0 0 0 0 rgba(88,166,255,0.55); }
    60%  { box-shadow: 0 0 0 10px rgba(88,166,255,0); }
    100% { box-shadow: 0 0 0 0  rgba(88,166,255,0); }
  }

  /* Panel completo entra con fadeSlideUp */
  .detail-enter {
    animation: fadeSlideUp .45s cubic-bezier(0.16,1,0.3,1) both;
  }
  /* Línea wipe en la parte superior */
  .detail-wipe-line {
    height: 3px;
    border-radius: 2px;
    transform-origin: left center;
    animation: wipeLine .4s cubic-bezier(0.16,1,0.3,1) both;
    margin-bottom: 14px;
  }
  /* Cada card entra escalonado */
  .det-card { animation: fadeSlideUp .4s cubic-bezier(0.16,1,0.3,1) both; }
  .det-card:nth-child(1) { animation-delay: .04s; }
  .det-card:nth-child(2) { animation-delay: .09s; }
  .det-card:nth-child(3) { animation-delay: .14s; }
  .det-card:nth-child(4) { animation-delay: .19s; }
  .det-card:nth-child(5) { animation-delay: .24s; }
  .det-card:nth-child(6) { animation-delay: .29s; }
  .det-card:nth-child(7) { animation-delay: .34s; }
  .det-card:nth-child(8) { animation-delay: .39s; }
  .det-card:nth-child(9) { animation-delay: .44s; }

  /* Día seleccionado pulsa en el calendario */
  div:has(>span[id^="cal-"]) ~ div button:not(:disabled):focus,
  div:has(>span[id^="cal-"]) ~ div button:not(:disabled):active {
    animation: calPulse .5s ease-out;
  }

  /* ── Botones del calendario estilizados como cards ── */
  div[data-testid="stColumn"] div[data-testid="stButton"] button {
    background-color: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    min-height: 85px !important;
    width: 100% !important;
    padding: 8px 6px !important;
    white-space: pre-wrap !important;
    text-align: center !important;
    font-size: 12px !important;
    line-height: 1.5 !important;
    transition: border-color .15s !important;
    color: #8b949e !important;
  }
  div[data-testid="stColumn"] div[data-testid="stButton"] button:hover {
    border-color: #58a6ff !important;
    background-color: #1c2128 !important;
  }
  /* Celdas vacías */
  .cal-empty { min-height: 85px; }
  /* Clases de color para PnL — inyectadas por Python */
  .cal-pos button { color: #3fb950 !important; }
  .cal-neg button { color: #f85149 !important; }
  .cal-zero button { color: #8b949e !important; }
  .cal-best button { border: 2px solid #3fb950 !important; }
  .cal-worst button { border: 2px solid #f85149 !important; }
  .cal-selected button { border: 2px solid #58a6ff !important; background-color: #1c2128 !important; }
</style>
""", unsafe_allow_html=True)


# ─── DATA LOADING ────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data():
    # Streamlit Cloud → lee de st.secrets
    # Local → lee del archivo JSON
    if "gcp_service_account" in st.secrets:
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]),
            scopes=SCOPES
        )
    else:
        creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    sh = client.open_by_key(SHEET_ID)

    ws = sh.worksheets()
    sheet_names = [w.title for w in ws]

    # Use "BitPredict Live" if it exists, else first non-empty sheet
    wsheet = next(
        (w for w in ws if w.title == "BitPredict Live"),
        next((w for w in ws if w.row_count > 1), ws[0])
    )
    data = wsheet.get_all_records()
    df = pd.DataFrame(data)
    return df, sheet_names


def prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse the Google Sheet with columns:
      Timestamp CST | Hora Local | Open Price | Pric Prediccion | Confianza % |
      UP % | DOWN % | Volumen BTC (v Tier) | En Filtro | Close Price |
      Direccion Real | Correcto | Pct Move % | Senales
    """
    # Normalize column names
    df.columns = [str(c).strip() for c in df.columns]

    # ── fecha: from "Timestamp CST" ──────────────────────────────────────
    ts_col = next((c for c in df.columns if "timestamp" in c.lower() or "hora local" in c.lower()), None)
    if ts_col:
        df["fecha"] = pd.to_datetime(df[ts_col], errors="coerce")
    else:
        df["fecha"] = pd.NaT

    # ── tier: columna "Tier" separada (S, A, B, C, D) ───────────────────
    tier_col = next((c for c in df.columns if c.strip().lower() == "tier"), None)
    if tier_col:
        df["tier"] = df[tier_col].astype(str).str.strip().str.upper()
    else:
        # fallback: extraer letra del campo Volumen BTC
        vol_col = next((c for c in df.columns if "volumen" in c.lower()), None)
        if vol_col:
            df["tier"] = (df[vol_col].astype(str)
                          .str.strip()
                          .str.extract(r"([A-Za-z]+)\s*$")[0]
                          .str.upper())
        else:
            df["tier"] = "?"

    # ── resultado: "Correcto" column (SI / NO) ────────────────────────────
    corr_col = next((c for c in df.columns if c.strip().lower() == "correcto"), None)
    if corr_col:
        df["resultado"] = df[corr_col].astype(str).str.strip().str.upper()
    else:
        df["resultado"] = "?"

    # ── pnl: $1000 per trade (win +1000, loss -1000) ─────────────────────
    df["pnl"] = df["resultado"].map({"SI": 1000, "NO": -1000}).fillna(0)

    # ── extra useful columns ──────────────────────────────────────────────
    pred_col = next((c for c in df.columns if "prediccion" in c.lower() or "prediction" in c.lower()), None)
    if pred_col:
        df["prediccion"] = df[pred_col].astype(str).str.strip().str.upper()

    real_col = next((c for c in df.columns if "direccion real" in c.lower()), None)
    if real_col:
        df["dir_real"] = df[real_col].astype(str).str.strip().str.upper()

    conf_col = next((c for c in df.columns if "confianza" in c.lower()), None)
    if conf_col:
        df["confianza"] = pd.to_numeric(df[conf_col], errors="coerce")

    filtro_col = next((c for c in df.columns if "filtro" in c.lower()), None)
    if filtro_col:
        df["en_filtro"] = df[filtro_col].astype(str).str.strip().str.upper()

    return df


def aggregate_by_day(df: pd.DataFrame, tiers: list) -> pd.DataFrame:
    """Return one row per calendar day with aggregated stats."""
    if df.empty or "fecha" not in df.columns:
        return pd.DataFrame()

    fdf = df[df["tier"].isin(tiers)] if "tier" in df.columns and tiers else df
    fdf = fdf.dropna(subset=["fecha"])

    grp = fdf.groupby(fdf["fecha"].dt.date)
    agg = grp.agg(
        pnl=("pnl", "sum"),
        trades=("pnl", "count"),
        wins=("resultado", lambda x: (x == "SI").sum()),
        losses=("resultado", lambda x: (x == "NO").sum()),
    ).reset_index()
    agg.columns = ["day", "pnl", "trades", "wins", "losses"]
    agg["day"] = pd.to_datetime(agg["day"])
    return agg


# ─── DETAIL VIEW ─────────────────────────────────────────────────────────────
def show_day_detail(df: pd.DataFrame, selected_day: date, tiers: list):
    fdf = df[df["tier"].isin(tiers)] if "tier" in df.columns and tiers else df
    fdf = fdf[fdf["fecha"].dt.date == selected_day].copy()

    if fdf.empty:
        st.info("No hay operaciones para este día con los tiers seleccionados.")
        return

    trades = fdf.to_dict("records")
    total = len(trades)
    wins = int((fdf["resultado"] == "SI").sum()) if "resultado" in fdf.columns else 0
    losses = total - wins
    win_rate = wins / total * 100 if total else 0
    net = fdf["pnl"].sum()

    # ── Simulate running bank (assume a fixed starting bank for the day) ──
    # We'll reconstruct from the sequence of individual trade P&Ls
    pnl_seq = fdf["pnl"].tolist()
    banco_inicial = 100_000  # default; adjust if known
    bank_curve = [banco_inicial]
    for p in pnl_seq:
        bank_curve.append(bank_curve[-1] + p)

    banco_final = bank_curve[-1]
    banco_min = min(bank_curve)
    banco_max = max(bank_curve)
    idx_min = bank_curve.index(banco_min)
    idx_max = bank_curve.index(banco_max)

    seq = fdf["resultado"].tolist() if "resultado" in fdf.columns else []

    # ── Layout ────────────────────────────────────────────────────────────
    # Color de acento según resultado del día
    accent = "#3fb950" if net >= 0 else "#f85149"

    # Contenedor principal con animación de entrada + línea wipe
    st.markdown(f"""
    <div class="detail-enter">
      <div class="detail-wipe-line" style="background:{accent}"></div>
      <div style="font-size:15px;font-weight:700;color:#e6edf3;margin-bottom:12px;letter-spacing:.5px">
        Detalle — día {selected_day.day:02d}
        <span style="font-size:12px;color:{accent};margin-left:8px">
          {'▲ Ganancia' if net >= 0 else '▼ Pérdida'}
        </span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    def det_card(label, value_html, delay_s=0):
        return (f"<div class='det-card' style='animation-delay:{delay_s:.2f}s'>"
                f"<div class='det-label'>{label}</div>"
                f"<div class='det-value'>{value_html}</div></div>")

    color_net = "det-green" if net >= 0 else "det-red"
    sign_net  = "+" if net >= 0 else ""
    color_fin = "det-green" if banco_final >= banco_inicial else "det-red"
    diff      = banco_final - banco_inicial
    sign_diff = "+" if diff >= 0 else ""

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(det_card("Total resultados", str(total), .04), unsafe_allow_html=True)
    with c2:
        st.markdown(det_card("SI (gana)", f"<span class='det-green'>{wins}</span>", .09), unsafe_allow_html=True)
    with c3:
        st.markdown(det_card("NO (pierde)", f"<span class='det-red'>{losses}</span>", .14), unsafe_allow_html=True)
    with c4:
        st.markdown(det_card("Balance neto", f"<span class='{color_net}'>{sign_net}${net:,.0f}</span>", .19), unsafe_allow_html=True)

    c5, c6, c7 = st.columns(3)
    with c5:
        st.markdown(det_card("Banco inicial", f"${banco_inicial:,.0f}", .24), unsafe_allow_html=True)
    with c6:
        st.markdown(det_card("Banco final",
            f"<span class='{color_fin}'>${banco_final:,.0f}</span>"
            f"<small style='display:block;font-size:12px;margin-top:2px'>{sign_diff}${diff:,.0f}</small>", .29),
            unsafe_allow_html=True)
    with c7:
        st.markdown(det_card("Win rate", f"{win_rate:.1f}%", .34), unsafe_allow_html=True)

    c8, c9 = st.columns(2)
    with c8:
        st.markdown(det_card("Banco mínimo del día",
            f"<span class='det-red'>${banco_min:,.0f}</span>"
            f"<small style='display:block;font-size:11px;color:#888;margin-top:2px'>Resultado #{idx_min}</small>", .39),
            unsafe_allow_html=True)
    with c9:
        st.markdown(det_card("Banco máximo del día",
            f"<span class='det-green'>${banco_max:,.0f}</span>"
            f"<small style='display:block;font-size:11px;color:#888;margin-top:2px'>Resultado #{idx_max}</small>", .44),
            unsafe_allow_html=True)

    # ── Bank curve chart ──────────────────────────────────────────────────
    # Color: verde si ganó el día, rojo si perdió
    line_color = "#2e7d32" if banco_final >= banco_inicial else "#c62828"
    fill_color  = "rgba(46,125,50,0.12)" if banco_final >= banco_inicial else "rgba(198,40,40,0.12)"

    x_labels = ["Inicio"] + [f"#{i+1}" for i in range(len(pnl_seq))]

    fig = go.Figure()

    # Línea base invisible (banco_inicial) para rellenar entre curva y baseline
    fig.add_trace(go.Scatter(
        x=x_labels,
        y=[banco_inicial] * len(x_labels),
        mode="lines",
        line=dict(width=0, color=line_color),
        showlegend=False,
        hoverinfo="skip",
    ))
    # Curva del banco
    fig.add_trace(go.Scatter(
        x=x_labels,
        y=bank_curve,
        mode="lines+markers",
        line=dict(color=line_color, width=2),
        marker=dict(color=line_color, size=5),
        fill="tonexty",          # rellena entre curva y la línea base
        fillcolor=fill_color,
        hovertemplate="Resultado %{x}<br>Banco: $%{y:,.0f}<extra></extra>",
    ))

    # Rango Y con 5% de margen
    y_min = min(bank_curve) * 0.97
    y_max = max(bank_curve) * 1.02

    fig.update_layout(
        paper_bgcolor="#f8f5f0",
        plot_bgcolor="#f8f5f0",
        font=dict(color="#1a1a1a", size=11),
        margin=dict(l=10, r=10, t=10, b=40),
        height=280,
        xaxis=dict(
            showgrid=False,
            tickangle=0,
            tickfont=dict(size=10),
            # Mostrar ticks cada ~13 operaciones para no saturar
            tickmode="array",
            tickvals=[x_labels[0]] + [x_labels[i] for i in range(12, len(x_labels), 13)],
        ),
        yaxis=dict(
            tickformat="$,.0f",
            showgrid=True,
            gridcolor="#e0e0e0",
            range=[y_min, y_max],
        ),
        hovermode="x unified",
    )
    st.markdown("<div style='animation:fadeSlideUp .5s cubic-bezier(0.16,1,0.3,1) .5s both'>",
                unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Sequence pills ────────────────────────────────────────────────────
    st.markdown("<div style='animation:fadeSlideUp .4s cubic-bezier(0.16,1,0.3,1) .62s both'>",
                unsafe_allow_html=True)
    st.markdown("**Secuencia de resultados**")
    pills_html = " ".join(
        f"<span class='seq-pill {'pill-si' if r == 'SI' else 'pill-no'}'>{r}</span>"
        for r in seq
    )
    st.markdown(f"<div style='margin-top:8px'>{pills_html}</div></div>", unsafe_allow_html=True)

    # ── Trade table ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**Operaciones del día**")
    show_cols = ["fecha", "prediccion", "dir_real", "resultado", "confianza", "tier", "en_filtro", "pnl"]
    available = [c for c in show_cols if c in fdf.columns]
    display = fdf[available].copy()
    display["fecha"] = display["fecha"].dt.strftime("%H:%M") if "fecha" in display.columns else ""
    col_labels = {
        "fecha": "Hora", "prediccion": "Predicción", "dir_real": "Real",
        "resultado": "Correcto", "confianza": "Confianza %",
        "tier": "Tier", "en_filtro": "En Filtro", "pnl": "P&L"
    }
    display = display.rename(columns={k: v for k, v in col_labels.items() if k in display.columns})
    st.dataframe(display, use_container_width=True, hide_index=True)


# ─── CALENDAR ────────────────────────────────────────────────────────────────
def set_selected_day(day: int):
    st.session_state["selected_day"] = day


def render_calendar(agg: pd.DataFrame, year: int, month: int):
    """Render the clickable calendar grid using styled st.button as cards."""
    day_map = {}
    if not agg.empty:
        for _, row in agg.iterrows():
            if row["day"].year == year and row["day"].month == month:
                day_map[row["day"].day] = row

    best_day  = max(day_map, key=lambda d: day_map[d]["pnl"], default=None) if day_map else None
    worst_day = min(day_map, key=lambda d: day_map[d]["pnl"], default=None) if day_map else None
    selected  = st.session_state.get("selected_day")

    cal_matrix = calendar.monthcalendar(year, month)
    WEEKDAYS   = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    # ── Pre-generate per-day CSS using :has() ────────────────────────────
    # Each button gets a hidden <span id="cal-KEY"> as a preceding sibling.
    # :has() lets us target the column that contains that span.
    css_rules = []
    for day, row in day_map.items():
        key = f"day_{year}_{month}_{day}"
        pnl = float(row["pnl"])
        if day == selected:
            color  = "#58a6ff"
            border = "2px solid #58a6ff"
        elif day == best_day:
            color  = "#3fb950"
            border = "2px solid #3fb950"
        elif day == worst_day:
            color  = "#f85149"
            border = "2px solid #f85149"
        elif pnl > 0:
            color  = "#3fb950"
            border = "1px solid #30363d"
        elif pnl < 0:
            color  = "#f85149"
            border = "1px solid #30363d"
        else:
            color  = "#8b949e"
            border = "1px solid #30363d"

        # Busca el div que tiene el span como HIJO DIRECTO (>),
        # luego apunta al botón en el div hermano siguiente (~).
        # Esto es exactamente el element-container del span → siguiente element-container con el botón.
        # No sube a contenedores padre, evitando colorear toda la columna exterior.
        css_rules.append(
            f"div:has(>span#cal-{key})~div button{{"
            f"color:{color}!important;border:{border}!important;}}"
        )

    if css_rules:
        st.markdown(f"<style>{''.join(css_rules)}</style>", unsafe_allow_html=True)

    # ── Header row ───────────────────────────────────────────────────────
    header_cols = st.columns(7)
    for i, wd in enumerate(WEEKDAYS):
        header_cols[i].markdown(
            f"<div style='text-align:center;color:#8b949e;font-size:12px;"
            f"padding-bottom:4px'>{wd}</div>",
            unsafe_allow_html=True,
        )

    # ── Calendar rows ────────────────────────────────────────────────────
    for week in cal_matrix:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.markdown("<div class='cal-empty'></div>", unsafe_allow_html=True)
                    continue

                row    = day_map.get(day)
                pnl    = float(row["pnl"])  if row is not None else 0.0
                trades = int(row["trades"]) if row is not None else 0
                wins   = int(row["wins"])   if row is not None else 0
                losses = int(row["losses"]) if row is not None else 0

                if trades > 0:
                    pnl_str = (f"$+{pnl:,.0f}" if pnl > 0
                               else f"-${abs(pnl):,.0f}" if pnl < 0
                               else "$+0")
                    label = f"{day:02d}\n{pnl_str}\n{wins}W/{losses}L · {trades}tr"
                else:
                    label = f"{day:02d}\n$+0\n "

                key = f"day_{year}_{month}_{day}"
                # Hidden marker so :has(#cal-KEY) CSS selector can find this column
                st.markdown(f'<span id="cal-{key}"></span>', unsafe_allow_html=True)
                st.button(
                    label,
                    key=key,
                    on_click=set_selected_day,
                    args=(day,),
                    use_container_width=True,
                    disabled=(trades == 0),
                )


# ─── MAIN APP ────────────────────────────────────────────────────────────────
def main():
    # ── Sidebar ──────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## ⚙️ Configuración")

        # ── Tier pills ────────────────────────────────────────────────────
        st.markdown("**Tiers activos**")

        if "tiers_state" not in st.session_state:
            st.session_state["tiers_state"] = {t: (t in ["S", "A", "B"]) for t in ALL_TIERS}

        # CSS toggle chips — réplica exacta de la imagen de referencia
        st.markdown("""<style>
        /* ── Base compartido ── */
        section[data-testid="stSidebar"]
          div[data-testid="stHorizontalBlock"]
          button {
            border-radius: 14px !important;
            font-size: 15px !important;
            font-weight: 800 !important;
            height: 48px !important;
            min-height: 0 !important;
            letter-spacing: .5px !important;
            transition: transform .12s, box-shadow .12s !important;
            padding: 0 10px !important;
        }
        /* ── Chip INACTIVO — gris claro ── */
        section[data-testid="stSidebar"]
          div[data-testid="stHorizontalBlock"]
          button[data-testid="baseButton-secondary"] {
            background: #d1d5db !important;
            color: #374151 !important;
            border: none !important;
            box-shadow: 0 2px 4px rgba(0,0,0,.15) !important;
        }
        /* ── Chip ACTIVO — azul con sombra ── */
        section[data-testid="stSidebar"]
          div[data-testid="stHorizontalBlock"]
          button[data-testid="baseButton-primary"] {
            background: linear-gradient(135deg,#5aabf5 0%,#3b82f6 100%) !important;
            color: #ffffff !important;
            border: none !important;
            box-shadow: 0 3px 8px rgba(59,130,246,.45) !important;
        }
        /* ── Hover / press ── */
        section[data-testid="stSidebar"]
          div[data-testid="stHorizontalBlock"]
          button:hover {
            transform: translateY(-2px) scale(1.04) !important;
            box-shadow: 0 5px 12px rgba(0,0,0,.2) !important;
        }
        section[data-testid="stSidebar"]
          div[data-testid="stHorizontalBlock"]
          button:active {
            transform: translateY(0) scale(.96) !important;
        }
        /* Quitar outline de focus */
        section[data-testid="stSidebar"]
          div[data-testid="stHorizontalBlock"]
          button:focus { outline: none !important; box-shadow: inherit !important; }
        </style>""", unsafe_allow_html=True)

        cols_t = st.columns(len(ALL_TIERS))
        for i, t in enumerate(ALL_TIERS):
            active = st.session_state["tiers_state"][t]
            # Checkmark circular para activos (igual que la imagen)
            label  = f"{t}  ✅" if active else t
            with cols_t[i]:
                if st.button(label, key=f"tier_btn_{t}",
                             type="primary" if active else "secondary",
                             use_container_width=True):
                    st.session_state["tiers_state"][t] = not active
                    st.rerun()

        tiers_sel = [t for t, on in st.session_state["tiers_state"].items() if on]

        today = date.today()
        months_es = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                     "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        col1, col2 = st.columns(2)
        with col1:
            sel_month = st.selectbox("Mes", range(1, 13),
                                     index=today.month - 1,
                                     format_func=lambda m: months_es[m - 1])
        with col2:
            sel_year = st.number_input("Año", min_value=2020, max_value=2030,
                                       value=today.year, step=1)

        st.markdown("---")
        if st.button("🔄 Recargar datos"):
            st.cache_data.clear()
            st.rerun()

        debug_mode = st.toggle("🔍 Debug (ver columnas raw)", value=False)

        st.markdown("---")

    # ── Load data ─────────────────────────────────────────────────────────
    try:
        raw_df, sheet_names = load_data()
        df = prepare_df(raw_df)
    except Exception as e:
        st.error(f"❌ Error cargando datos: {e}")
        st.info("Asegúrate de compartir la hoja con: **predict@master-plateau-489706-m4.iam.gserviceaccount.com**")
        st.stop()

    if debug_mode:
        st.subheader("🔍 Columnas raw del Sheet")
        st.write("Hojas:", sheet_names)
        st.write("Columnas originales:", list(raw_df.columns))
        st.write("Columnas procesadas:", list(df.columns))
        st.dataframe(df.head(20), use_container_width=True)
        st.stop()

    # ── Filter by month/year and tiers ────────────────────────────────────
    if not tiers_sel:
        st.warning("Selecciona al menos un tier en la barra lateral.")
        st.stop()

    agg = aggregate_by_day(df, tiers_sel)

    # Filter to selected month
    month_agg = agg[(agg["day"].dt.year == sel_year) & (agg["day"].dt.month == sel_month)] if not agg.empty else agg

    # ── Summary KPIs ──────────────────────────────────────────────────────
    if not month_agg.empty:
        total_pnl   = month_agg["pnl"].sum()
        gain_days   = int((month_agg["pnl"] > 0).sum())
        loss_days   = int((month_agg["pnl"] < 0).sum())
        best_row    = month_agg.loc[month_agg["pnl"].idxmax()]
        worst_row   = month_agg.loc[month_agg["pnl"].idxmin()]
        max_risk_row= month_agg.loc[month_agg["trades"].idxmax()]
        max_exposure = max_risk_row["trades"] * 1000  # $1000/trade assumption
    else:
        total_pnl = gain_days = loss_days = 0
        best_row = worst_row = max_risk_row = None
        max_exposure = 0

    tier_label = " · ".join(f"tiers {t}" for t in tiers_sel)
    st.markdown(f"<div class='header-title'>Calendario de Ganancias por Día &nbsp;($1000/trade · {tier_label})</div>",
                unsafe_allow_html=True)

    k1, k2, k3, k4, k5, k6 = st.columns(6)

    def kpi(col, label, value, color="#e6edf3"):
        col.markdown(f"""<div class='sum-card'>
          <div class='sum-label'>{label}</div>
          <div class='sum-value' style='color:{color}'>{value}</div>
        </div>""", unsafe_allow_html=True)

    sign = "+" if total_pnl >= 0 else ""
    kpi(k1, "P&L Total Mes", f"${sign}{total_pnl:,.0f}", "#3fb950" if total_pnl >= 0 else "#f85149")
    kpi(k2, "Días con ganancia", str(gain_days), "#3fb950")
    kpi(k3, "Días con pérdida",  str(loss_days), "#f85149")
    if best_row is not None:
        kpi(k4, "Mejor día",
            f"{int(best_row['day'].day):02d} (+${best_row['pnl']:,.0f})", "#3fb950")
        kpi(k5, "Peor día",
            f"{int(worst_row['day'].day):02d} (${worst_row['pnl']:,.0f})", "#f85149")
        kpi(k6, "Máx. Riesgo/día",
            f"${max_exposure:,.0f} (día {int(max_risk_row['day'].day):02d} · {int(max_risk_row['trades'])}tr)",
            "#e3b341")
    else:
        kpi(k4, "Mejor día", "—")
        kpi(k5, "Peor día",  "—")
        kpi(k6, "Máx. Riesgo/día", "—")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Calendar + Detail layout ──────────────────────────────────────────
    if "selected_day" not in st.session_state:
        st.session_state["selected_day"] = None

    cal_col, det_col = st.columns([3, 2], gap="large")

    with cal_col:
        render_calendar(month_agg, sel_year, sel_month)

    with det_col:
        sel = st.session_state.get("selected_day")
        if sel:
            sel_date = date(sel_year, sel_month, sel)
            try:
                show_day_detail(df, sel_date, tiers_sel)
            except Exception as e:
                st.error(f"Error al mostrar detalle: {e}")
        else:
            st.markdown("""
            <div style='color:#8b949e; margin-top: 60px; text-align:center'>
              <div style='font-size:40px'>📅</div>
              <div style='margin-top:12px'>Haz clic en un día del calendario<br>para ver el detalle</div>
            </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
