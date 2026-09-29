import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# Configuración de pantalla
st.set_page_config(
    page_title="Buffett Value Screener",
    page_icon="📈",
    layout="wide"
)

st.title("🛡️ Analizador Fundamental 'Estilo Buffett'")
st.caption("Filtro de solvencia, generación de caja real y múltiplos en tiempo real.")

# Barra lateral para buscar acciones
st.sidebar.header("Buscar Empresa")
ticker_input = st.sidebar.text_input(
    "Ticker de la acción (EE. UU.):",
    value="WEYS",
    help="Escribe el símbolo exacto sin símbolos raros: WEYS, HRTG, AAPL, UVE"
).strip().upper().replace("$", "")

# Botones de acceso rápido
st.sidebar.markdown("**Accesos directos:**")
col_b1, col_b2, col_b3 = st.sidebar.columns(3)
if col_b1.button("WEYS"):
    ticker_input = "WEYS"
if col_b2.button("HRTG"):
    ticker_input = "HRTG"
if col_b3.button("UVE"):
    ticker_input = "UVE"

@st.cache_resource(ttl=3600)
def obtener_datos(ticker):
    # Sesión personalizada para esquivar el bloqueo 401 / Invalid Crumb de Yahoo
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    stock = yf.Ticker(ticker, session=session)
    info = stock.info
    divs = stock.dividends
    hist = stock.history(period="5y")
    return stock, info, divs, hist

if ticker_input:
    with st.spinner(f"Analizando balance y dividendos de {ticker_input}..."):
        try:
            stock, info, hist_divs, hist_precios = obtener_datos(ticker_input)
            
            nombre = info.get("shortName", ticker_input)
            sector = info.get("sector", "N/D")
            industria = info.get("industry", "N/D")
            
            precio_actual = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
            cap_mercado = (info.get("marketCap") or 0) / 1e6
            per_ttm = info.get("trailingPE")
            ev_ebitda = info.get("enterpriseToEbitda")
            fcf = (info.get("freeCashflow") or 0) / 1e6
            dividend_yield = (info.get("dividendYield") or 0) * 100
            
            deuda_total = info.get("totalDebt") or 0
            caja_total = info.get("totalCash") or 0
            deuda_neta = (deuda_total - caja_total) / 1e6
            current_ratio = info.get("currentRatio")

            st.subheader(f"{nombre} ({ticker_input})")
            st.write(f"**Sector:** {sector} | **Industria:** {industria}")

            # Fila de métricas principales
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Precio Actual", f"${precio_actual:,.2f}")
            m2.metric("Cap. Mercado", f"${cap_mercado:,.1f} M")
            m3.metric("PER (TTM)", f"{per_ttm:.1f}x" if per_ttm else "En pérdidas")
            m4.metric("VE / EBITDA", f"{ev_ebitda:.1f}x" if ev_ebitda else "N/D")
            m5.metric("Rent. Dividendo", f"{dividend_yield:.2f}%" if dividend_yield > 0 else "0.00%")

            st.markdown("---")
            st.subheader("🚦 El Semáforo Buffett (Calidad y Seguridad)")

            c1, c2, c3, c4 = st.columns(4)

            # 1. PER
            with c1:
                st.markdown("**1. Valoración (PER)**")
                if per_ttm and 0 < per_ttm <= 12.0:
                    st.success(f"✅ Barata ({per_ttm:.1f}x <= 12x)")
                elif per_ttm and per_ttm > 12.0:
                    st.warning(f"⚠️ PER Normal/Alto ({per_ttm:.1f}x)")
                else:
                    st.error("❌ PER Negativo (Pérdidas)")

            # 2. Deuda Neta
            with c2:
                st.markdown("**2. Endeudamiento**")
                if deuda_neta <= 0:
                    st.success(f"✅ Sin Deuda (+${abs(deuda_neta):.1f}M caja)")
                else:
                    st.warning(f"⚠️ Deuda Neta: ${deuda_neta:.1f}M")

            # 3. Liquidez
            with c3:
                st.markdown("**3. Test Liquidez**")
                if current_ratio and current_ratio >= 1.5:
                    st.success(f"✅ Solvente ({current_ratio:.2f}x)")
                elif current_ratio:
                    st.warning(f"⚠️ Justa ({current_ratio:.2f}x)")
                else:
                    st.info("ℹ️ No aplica")

            # 4. FCF
            with c4:
                st.markdown("**4. Caja Libre (FCF)**")
                if fcf > 0:
                    st.success(f"✅ Genera Caja (+${fcf:.1f}M)")
                else:
                    st.error(f"❌ Quema Caja (${fcf:.1f}M)")

            st.markdown("---")

            # Pestañas de gráficos
            tab_divs, tab_precios, tab_detalles = st.tabs(["💰 Dividendos", "📈 Gráfico 5 Años", "📑 Balance"])

            with tab_divs:
                if not hist_divs.empty:
                    df_divs = pd.DataFrame({
                        "Fecha": hist_divs.index.strftime('%Y-%m-%d'),
                        "Dividendo ($)": hist_divs.values
                    }).sort_values("Fecha", ascending=False)

                    g_col1, g_col2 = st.columns([2, 1])
                    with g_col1:
                        fig = go.Figure(go.Bar(
                            x=df_divs["Fecha"].head(16),
                            y=df_divs["Dividendo ($)"].head(16),
                            marker_color='#2ca02c'
                        ))
                        fig.update_layout(title="Últimos pagos (Detecta picos extraordinarios)", height=320)
                        st.plotly_chart(fig, width='stretch')
                    with g_col2:
                        st.write("Historial reciente:")
                        st.dataframe(df_divs.head(8), hide_index=True, width='stretch')
                else:
                    st.info("Esta empresa no tiene historial de dividendos.")

            with tab_precios:
                if not hist_precios.empty:
                    fig_p = go.Figure()
                    fig_p.add_trace(go.Scatter(x=hist_precios.index, y=hist_precios['Close'], mode='lines', name='Cierre'))
                    fig_p.update_layout(height=350, yaxis_title="Precio ($)")
                    st.plotly_chart(fig_p, width='stretch')

            with tab_detalles:
                col_d1, col_d2 = st.columns(2)
                col_d1.write(f"- **Efectivo en caja:** ${caja_total/1e6:,.2f} M")
                col_d1.write(f"- **Deuda bruta:** ${deuda_total/1e6:,.2f} M")
                col_d2.write(f"- **Beneficio por acción (EPS):** ${info.get('trailingEps', 0):.2f}")
                col_d2.write(f"- **Precio / Valor en libros (P/B):** {info.get('priceToBook', 'N/D')}")

        except Exception as e:
            st.error(f"No se pudieron cargar datos para '{ticker_input}'. Comprueba el ticker. Error: {e}")
