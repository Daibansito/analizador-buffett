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
st.caption("Filtro de solvencia, generación de caja real, dictamen experto y valoración de Small Caps.")

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

def generar_opinion_experta(nombre, per, deuda_neta, fcf, current_ratio, div_yield, cap_mercado):
    """Genera un análisis fundamental cualitativo estilo Buffett/Munger."""
    analisis = []
    
    # 1. Evaluación de Rentabilidad / Múltiplos
    if per is None or per <= 0:
        analisis.append("⚠️ **Beneficios en negativo:** La compañía reporta pérdidas contables en los últimos 12 meses. Desde el prisma de Buffett, entrar aquí implica asumir riesgo de giro (*turnaround*) o ciclo recesivo no superado.")
    elif per < 8:
        analisis.append(f"🟢 **Múltiplo de Valor Profundo (PER {per:.1f}x):** Cotiza con un descuento severo frente al mercado. Si el modelo es recurrente, ofrece un margen de seguridad amplio frente a caídas.")
    elif per <= 14:
        analisis.append(f"🔵 **Valoración Razonable (PER {per:.1f}x):** Precio equilibrado. No es una ganga extrema, pero encaja en la máxima de 'comprar una empresa buena a un precio justo'.")
    else:
        analisis.append(f"🟠 **Múltiplo Exigente (PER {per:.1f}x):** Cotiza sin holgura de valoración para una empresa de este tamaño. El margen de seguridad es reducido ante un trimestre flojo.")

    # 2. Evaluación de Solvencia y Balance
    if deuda_neta <= 0:
        analisis.append(f"🟢 **Fortaleza Financiera Sobresaliente:** Dispone de caja neta (+${abs(deuda_neta):.1f}M). No depende de la banca ni de refinanciaciones caras, eliminando el riesgo de quiebra.")
    elif deuda_neta < (fcf * 3) if fcf > 0 else False:
        analisis.append(f"🔵 **Deuda Gestionable:** La deuda neta (${deuda_neta:.1f}M) está respaldada por su generación de caja operativa.")
    else:
        analisis.append(f"🔴 **Apalancamiento Considerables:** La deuda neta de ${deuda_neta:.1f}M compromete la flexibilidad del negocio frente a subidas de tipos o contracción de márgenes.")

    # 3. Flujo de Caja y Dividendos
    if fcf > 0 and div_yield > 2.5:
        analisis.append(f"🟢 **Retorno Efectivo al Accionista:** Genera flujo de caja libre positivo (+${fcf:.1f}M) que financia de manera orgánica un dividendo de {div_yield:.2f}%.")
    elif fcf > 0:
        analisis.append(f"🔵 **Generador de Caja:** Genera FCF positivo (+${fcf:.1f}M), lo que le permite reinvertir en el negocio sin emitir nuevas acciones ni endeudarse.")
    else:
        analisis.append(f"🔴 **Déficit de Flujo Libre:** Registra FCF negativo. El beneficio contable no se está traduciendo en dinero real en cuenta corriente.")

    # Conclusión / Veredicto
    if (per is not None and 0 < per <= 12) and deuda_neta <= 0 and fcf > 0:
        veredicto = "🌟 **Oportunidad de Calidad / Valor (Candidata Buffett pura)**: Cumple los tres pilares esenciales: barata por múltiplos, sin deuda neta y con caja libre positiva."
    elif (per is not None and per > 0) and deuda_neta <= 0 and fcf > 0:
        veredicto = "🛡️ **Negocio Sólido pero Precio No Barato**: Compañía financieramente intachable, ideal para esperar recortes o consolidaciones de precio antes de entrar."
    elif per is None or per <= 0:
        veredicto = "🚫 **Descarte Preventivo / Esperar Giro**: En pérdidas operativas. Mantener en lista de seguimiento hasta que recupere beneficios netos recurrentes."
    else:
        veredicto = "⚖️ **Perfil Mixto / Análisis Detallado Requerido**: Presenta áreas favorables combinadas con endeudamiento o márgenes ajustados."

    return veredicto, analisis

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

            # Métricas principales
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Precio Actual", f"${precio_actual:,.2f}")
            m2.metric("Cap. Mercado", f"${cap_mercado:,.1f} M")
            m3.metric("PER (TTM)", f"{per_ttm:.1f}x" if per_ttm else "En pérdidas")
            m4.metric("VE / EBITDA", f"{ev_ebitda:.1f}x" if ev_ebitda else "N/D")
            m5.metric("Rent. Dividendo", f"{dividend_yield:.2f}%" if dividend_yield > 0 else "0.00%")

            st.markdown("---")
            
            # SECCIÓN NUEVA: OPINIÓN EXPERTA BUFFETT
            st.subheader("🧐 Dictamen Experto de Inversión")
            veredicto, puntos_analisis = generar_opinion_experta(
                nombre, per_ttm, deuda_neta, fcf, current_ratio, dividend_yield, cap_mercado
            )
            
            st.info(veredicto)
            for punto in puntos_analisis:
                st.write(punto)

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
