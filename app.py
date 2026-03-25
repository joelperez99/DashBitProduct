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
CREDS_FILE = os.path.join(os.path.dirname(__file__), "master-plateau-489706-m4-685e52dee3cc.json")
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
</style>
""", unsafe_allow_html=True)


# ─── DATA LOADING ────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data():
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    sh = client.open_by_key(SHEET_ID)

    # Try to find the main sheet (first sheet or one named 'trades'/'data')
    ws = sh.worksheets()
    sheet_names = [w.title for w in ws]

    # Pick first worksheet
    wsheet = ws[0]
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

    # ── tier: last word/letter of "Volumen BTC (v Tier)" ─────────────────
    vol_col = next((c for c in df.columns if "volumen" in c.lower() or "tier" in c.lower()), None)
    if vol_col:
        # e.g. "136.4 C" → "C",  "225.79 B" → "B"
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
    pred_col = next((c for c in df.columns if "prediccion" in c.lower() or "pric pred" in c.lower()), None)
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
    st.markdown(f"### Detalle — día {selected_day.day:02d}")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class='det-card'>
          <div class='det-label'>Total resultados</div>
          <div class='det-value'>{total}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class='det-card'>
          <div class='det-label'>SI (gana)</div>
          <div class='det-value det-green'>{wins}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class='det-card'>
          <div class='det-label'>NO (pierde)</div>
          <div class='det-value det-red'>{losses}</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        color_cls = "det-green" if net >= 0 else "det-red"
        sign = "+" if net >= 0 else ""
        st.markdown(f"""<div class='det-card'>
          <div class='det-label'>Balance neto</div>
          <div class='det-value {color_cls}'>{sign}${net:,.0f}</div>
        </div>""", unsafe_allow_html=True)

    c5, c6, c7 = st.columns(3)
    with c5:
        st.markdown(f"""<div class='det-card'>
          <div class='det-label'>Banco inicial</div>
          <div class='det-value'>${banco_inicial:,.0f}</div>
        </div>""", unsafe_allow_html=True)
    with c6:
        color_cls = "det-green" if banco_final >= banco_inicial else "det-red"
        diff = banco_final - banco_inicial
        sign = "+" if diff >= 0 else ""
        st.markdown(f"""<div class='det-card'>
          <div class='det-label'>Banco final</div>
          <div class='det-value {color_cls}'>${banco_final:,.0f}<br>
          <small style='font-size:13px'>{sign}${diff:,.0f}</small></div>
        </div>""", unsafe_allow_html=True)
    with c7:
        st.markdown(f"""<div class='det-card'>
          <div class='det-label'>Win rate</div>
          <div class='det-value'>{win_rate:.1f}%</div>
        </div>""", unsafe_allow_html=True)

    c8, c9 = st.columns(2)
    with c8:
        st.markdown(f"""<div class='det-card'>
          <div class='det-label'>Banco mínimo del día</div>
          <div class='det-value det-red'>${banco_min:,.0f}</div>
          <div style='font-size:12px;color:#888'>Resultado #{idx_min}</div>
        </div>""", unsafe_allow_html=True)
    with c9:
        st.markdown(f"""<div class='det-card'>
          <div class='det-label'>Banco máximo del día</div>
          <div class='det-value det-green'>${banco_max:,.0f}</div>
          <div style='font-size:12px;color:#888'>Resultado #{idx_max}</div>
        </div>""", unsafe_allow_html=True)

    # ── Bank curve chart ──────────────────────────────────────────────────
    x_labels = ["Inicio"] + [f"#{i+1}" for i in range(len(pnl_seq))]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_labels, y=bank_curve,
        mode="lines+markers",
        line=dict(color="#2e7d32", width=2),
        marker=dict(color="#2e7d32", size=6),
        fill="tozeroy",
        fillcolor="rgba(46,125,50,0.08)",
    ))
    fig.update_layout(
        paper_bgcolor="#f8f5f0",
        plot_bgcolor="#f8f5f0",
        font=dict(color="#1a1a1a"),
        margin=dict(l=40, r=20, t=20, b=40),
        height=260,
        xaxis=dict(showgrid=False),
        yaxis=dict(tickformat="$,.0f", showgrid=True, gridcolor="#e0e0e0"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Sequence pills ────────────────────────────────────────────────────
    st.markdown("**Secuencia de resultados**")
    pills_html = " ".join(
        f"<span class='seq-pill {'pill-si' if r == 'SI' else 'pill-no'}'>{r}</span>"
        for r in seq
    )
    st.markdown(f"<div style='margin-top:8px'>{pills_html}</div>", unsafe_allow_html=True)

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
def render_calendar(agg: pd.DataFrame, year: int, month: int):
    """Render the clickable calendar grid; returns the clicked day (int) or None."""
    day_map = {}
    if not agg.empty:
        for _, row in agg.iterrows():
            if row["day"].year == year and row["day"].month == month:
                day_map[row["day"].day] = row

    best_day  = max(day_map, key=lambda d: day_map[d]["pnl"], default=None)
    worst_day = min(day_map, key=lambda d: day_map[d]["pnl"], default=None)

    # Build matrix (weeks × 7)
    cal = calendar.monthcalendar(year, month)
    WEEKDAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    clicked = None

    # Header row
    cols = st.columns(7)
    for i, wd in enumerate(WEEKDAYS):
        cols[i].markdown(f"<div style='text-align:center;color:#8b949e;font-size:12px;padding-bottom:4px'>{wd}</div>",
                         unsafe_allow_html=True)

    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].markdown("<div style='min-height:80px'></div>", unsafe_allow_html=True)
                continue

            row = day_map.get(day)
            pnl = row["pnl"] if row is not None else None
            trades = int(row["trades"]) if row is not None else 0
            wins   = int(row["wins"])   if row is not None else 0
            losses = int(row["losses"]) if row is not None else 0

            if pnl is None:
                pnl_cls = "pnl-zero"
                pnl_str = "$+0"
            elif pnl > 0:
                pnl_cls = "pnl-pos"
                pnl_str = f"$+{pnl:,.0f}"
            elif pnl < 0:
                pnl_cls = "pnl-neg"
                pnl_str = f"$-{abs(pnl):,.0f}"
            else:
                pnl_cls = "pnl-zero"
                pnl_str = "$+0"

            border_extra = ""
            if day == best_day:  border_extra = "best"
            if day == worst_day: border_extra = "worst"

            meta = f"{wins}W/{losses}L · {trades}tr" if trades else ""

            card_html = f"""
            <div class='day-card {border_extra}'>
              <div class='day-num'>{day:02d}</div>
              <div class='day-pnl {pnl_cls}'>{pnl_str}</div>
              <div class='day-meta'>{meta}</div>
            </div>"""

            with cols[i]:
                st.markdown(card_html, unsafe_allow_html=True)
                if trades > 0:
                    if st.button("", key=f"day_{year}_{month}_{day}",
                                 help=f"Ver detalle día {day}",
                                 use_container_width=True):
                        clicked = day

    return clicked


# ─── MAIN APP ────────────────────────────────────────────────────────────────
def main():
    # ── Sidebar ──────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## ⚙️ Configuración")

        tiers_sel = st.multiselect(
            "Tiers activos",
            options=ALL_TIERS,
            default=["S", "A", "B"],
            help="Filtra las operaciones por tier"
        )

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
        st.markdown(f"<small style='color:#8b949e'>Tiers: {' + '.join(tiers_sel) if tiers_sel else 'Ninguno'}</small>",
                    unsafe_allow_html=True)

    # ── Load data ─────────────────────────────────────────────────────────
    try:
        raw_df, sheet_names = load_data()
        df = prepare_df(raw_df)
    except Exception as e:
        st.error(f"❌ Error cargando datos: {e}")
        st.info("Asegúrate de compartir la hoja con: **messaging@master-plateau-489706-m4.iam.gserviceaccount.com**")
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
    cal_col, det_col = st.columns([3, 2], gap="large")

    with cal_col:
        if "selected_day" not in st.session_state:
            st.session_state["selected_day"] = None

        clicked = render_calendar(month_agg, sel_year, sel_month)
        if clicked is not None:
            st.session_state["selected_day"] = clicked

    with det_col:
        sel = st.session_state.get("selected_day")
        if sel:
            sel_date = date(sel_year, sel_month, sel)
            show_day_detail(df, sel_date, tiers_sel)
        else:
            st.markdown("""
            <div style='color:#8b949e; margin-top: 60px; text-align:center'>
              <div style='font-size:40px'>📅</div>
              <div style='margin-top:12px'>Haz clic en un día del calendario<br>para ver el detalle</div>
            </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
