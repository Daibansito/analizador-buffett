import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# Configuración de pantalla
st.set_page_config(
    page_title="Buffett Value Screener Pro",
    page_icon="📈",
    layout="wide"
)

st.title("🛡️ Analizador Fundamental 'Estilo Buffett'")
st.caption("Filtro de solvencia, ventajas competitivas, previsiones de beneficios y valoración intrínseca.")

# Barra lateral para buscar acciones
st.sidebar.header("Buscar Empresa")
ticker_input = st.sidebar.text_input(
    "Ticker de la acción (EE. UU.):",
    value="WEYS",
    help="Escribe el símbolo exacto: WEYS, HRTG, FLXS, UVE, AAPL"
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

# Enlaces externos rápidos
if ticker_input:
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"🔗 [Ver ficha en Investing.com](https://es.investing.com/search/?q={ticker_input})")
    st.sidebar.markdown(f"🔗 [Ver ficha en Yahoo Finance](https://finance.yahoo.com/quote/{ticker_input})")

@st.cache_resource(ttl=3600)
def obtener_datos(ticker):
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    stock = yf.Ticker(ticker, session=session)
    info = stock.info
    divs = stock.dividends
    hist = stock.history(period="5y")
    return stock, info, divs, hist

def analizar_foso_y_riesgos(sector, deuda_neta, fcf, margin_ebitda, current_ratio):
    """Genera fortalezas (Moat) y debilidades según el balance y sector."""
    ventajas = []
    desventajas = []

    # Ventajas Competitivas
    if deuda_neta <= 0:
        ventajas.append("🛡️ **Balance Blindado:** Caja neta positiva. Puede recomprar acciones, pagar dividendos o adquirir rivales débiles en recesión sin pedir crédito.")
    if fcf > 0:
        ventajas.append("💰 **Generación Real de Flujo Libre:** El beneficio neto se traduce en liquidez tangible, protegiendo a la empresa de suspensiones de dividendo.")
    if margin_ebitda and margin_ebitda > 0.15:
        ventajas.append(f"📊 **Poder de Fijación de Precios:** Margen EBITDA saludable ({margin_ebitda*100:.1f}%), síntoma de costes controlados o marca reconocida.")
    if "Insurance" in sector or "Financial" in sector:
        ventajas.append("🏦 **Float Financiero:** Capta liquidez por adelantado antes de abonar siniestros, generando rendimiento sobre el saldo invertido.")
    elif "Consumer" in sector:
        ventajas.append("👟 **Resiliencia de Cartera:** Marcas asentadas en nichos de consumo recurrente con lealtad de clientes.")

    # Desventajas y Riesgos
    if deuda_neta > 0:
        desventajas.append(f"⚠️ **Carga Financiera:** Tiene una deuda neta de ${deuda_neta:.1f}M que condiciona el flujo libre de caja ante tipos altos.")
    if fcf <= 0:
        desventajas.append("🔴 **Consumo de Caja:** No genera flujo de caja libre positivo; depende de reservas previas o financiación ajena.")
    if "Insurance" in sector:
        desventajas.append("🌪️ **Riesgo Climatológico/Catastrófico:** Temporadas severas de huracanes o tormentas pueden disparar el ratio combinado y mermar reservas.")
    elif "Cyclical" in sector or "Industrial" in sector:
        desventajas.append("📉 **Exposición Cíclica:** Alta sensibilidad a la desaceleración del PIB, fletes y costes de materias primas.")
    if current_ratio and current_ratio < 1.3:
        desventajas.append(f"⚠️ **Liquidez Justa:** Cobertura de pasivos a corto plazo ajustada ({current_ratio:.2f}x).")

    return ventajas, desventajas

if ticker_input:
    with st.spinner(f"Analizando balance, previsiones y modelo de negocio de {ticker_input}..."):
        try:
            stock, info, hist_divs, hist_precios = obtener_datos(ticker_input)
            
            nombre = info.get("shortName", ticker_input)
            sector = info.get("sector", "N/D")
            industria = info.get("industry", "N/D")
            resumen_negocio = info.get("longBusinessSummary", "No hay descripción detallada disponible.")
            
            # Métricas actuales
            precio_actual = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
            cap_mercado = (info.get("marketCap") or 0) / 1e6
            per_ttm = info.get("trailingPE")
            ev_ebitda = info.get("enterpriseToEbitda")
            fcf = (info.get("freeCashflow") or 0) / 1e6
            dividend_yield = (info.get("dividendYield") or 0) * 100
            
            # Previsiones y Ratios Futuros (Forward Metrics)
            forward_pe = info.get("forwardPE")
            forward_eps = info.get("forwardEps")
            trailing_eps = info.get("trailingEps")
            peg_ratio = info.get("pegRatio")
            rev_growth = info.get("revenueGrowth")
            
            # Balance
            deuda_total = info.get("totalDebt") or 0
            caja_total = info.get("totalCash") or 0
            deuda_neta = (deuda_total - caja_total) / 1e6
            current_ratio = info.get("currentRatio")
            margin_ebitda = info.get("ebitdaMargins")

            st.subheader(f"{nombre} ({ticker_input})")
            st.write(f"**Sector:** {sector} | **Industria:** {industria}")

            # FILA 1: Métricas de Valoración y Mercado Actuales
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Precio Actual", f"${precio_actual:,.2f}")
            m2.metric("Cap. Mercado", f"${cap_mercado:,.1f} M")
            m3.metric("PER (TTM)", f"{per_ttm:.1f}x" if per_ttm else "En pérdidas")
            m4.metric("VE / EBITDA", f"{ev_ebitda:.1f}x" if ev_ebitda else "N/D")
            m5.metric("Rent. Dividendo", f"{dividend_yield:.2f}%" if dividend_yield > 0 else "0.00%")

            # FILA 2: Métricas de Previsión Futura
            st.markdown("##### 🔮 Previsión de Beneficios y Múltiplos Futuros")
            p1, p2, p3, p4 = st.columns(4)
            
            # Variación esperada del EPS
            delta_eps = None
            if forward_eps and trailing_eps and trailing_eps != 0:
                delta_eps = f"{((forward_eps - trailing_eps) / abs(trailing_eps)) * 100:+.1f}% vs actual"
            
            p1.metric("Forward P/E (Esperado)", f"{forward_pe:.1f}x" if forward_pe else "N/D", 
                      delta=f"{(forward_pe - per_ttm):.1f}x" if (forward_pe and per_ttm) else None, delta_color="inverse")
            p2.metric("BPA Previsto (Forward EPS)", f"${forward_eps:.2f}" if forward_eps else "N/D", delta=delta_eps)
            p3.metric("Ratio PEG (Precio/Crecimiento)", f"{peg_ratio:.2f}" if peg_ratio else "N/D",
                      help="Un PEG < 1.0 indica que cotiza por debajo de su tasa de crecimiento esperada.")
            p4.metric("Crecimiento de Ingresos", f"{rev_growth*100:+.1f}%" if rev_growth else "N/D")

            st.markdown("---")

            # SECCIÓN 3: DESCRIPCIÓN DEL NEGOCIO, FOSO Y RIESGOS
            st.subheader("🏢 Modelo de Negocio, Ventajas y Desventajas")
            
            col_desc, col_foso = st.columns([1.2, 1])
            
            with col_desc:
                st.markdown("**¿A qué se dedica la empresa?**")
                st.write(resumen_negocio)
                
            with col_foso:
                ventajas, desventajas = analizar_foso_y_riesgos(sector, deuda_neta, fcf, margin_ebitda, current_ratio)
                st.markdown("**Ventajas Competitivas (*Moat*):**")
                for v in ventajas:
                    st.write(v)
                st.markdown("**Desventajas y Riesgos:**")
                for d in desventajas:
                    st.write(d)

            st.markdown("---")

            # SECCIÓN 4: SEMÁFORO BUFFETT
            st.subheader("🚦 El Semáforo Buffett (Calidad y Solvencia)")
            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.markdown("**1. Valoración (PER)**")
                if per_ttm and 0 < per_ttm <= 12.0:
                    st.success(f"✅ Barata ({per_ttm:.1f}x <= 12x)")
                elif per_ttm and per_ttm > 12.0:
                    st.warning(f"⚠️ PER Normal/Alto ({per_ttm:.1f}x)")
                else:
                    st.error("❌ PER Negativo (Pérdidas)")

            with c2:
                st.markdown("**2. Endeudamiento**")
                if deuda_neta <= 0:
                    st.success(f"✅ Sin Deuda (+${abs(deuda_neta):.1f}M caja)")
                else:
                    st.warning(f"⚠️ Deuda Neta: ${deuda_neta:.1f}M")

            with c3:
                st.markdown("**3. Test Liquidez**")
                if current_ratio and current_ratio >= 1.5:
                    st.success(f"✅ Solvente ({current_ratio:.2f}x)")
                elif current_ratio:
                    st.warning(f"⚠️ Justa ({current_ratio:.2f}x)")
                else:
                    st.info("ℹ️ No aplica")

            with c4:
                st.markdown("**4. Caja Libre (FCF)**")
                if fcf > 0:
                    st.success(f"✅ Genera Caja (+${fcf:.1f}M)")
                else:
                    st.error(f"❌ Quema Caja (${fcf:.1f}M)")

            st.markdown("---")

            # SECCIÓN 5: GRÁFICOS Y HISTORIAL
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
                        fig.update_layout(title="Historial de Pagos (Detecta Picos Extraordinarios)", height=320)
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
                col_d2.write(f"- **Beneficio por acción actual (EPS TTM):** ${info.get('trailingEps', 0):.2f}")
                col_d2.write(f"- **Precio / Valor contable (P/B):** {info.get('priceToBook', 'N/D')}")

        except Exception as e:
            st.error(f"No se pudieron cargar datos para '{ticker_input}'. Comprueba el ticker. Error: {e}")
