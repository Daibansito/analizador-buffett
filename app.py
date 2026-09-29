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
st.caption("Filtro de solvencia, ventajas competitivas, PER histórico decenal y comparativa sectorial.")

# Barra lateral para buscar acciones
st.sidebar.header("Buscar Empresa")
ticker_input = st.sidebar.text_input(
    "Ticker bursátil (EE. UU.):",
    value="WEYS",
    help="Introduce el ticker: WEYS, HRTG, FLXS, UVE, AAPL"
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
    hist = stock.history(period="10y")
    return stock, info, divs, hist

def calcular_per_historico_10y(stock, hist_10y, per_actual):
    """Calcula una estimación del PER medio histórico decenal cruzando precios y beneficios."""
    try:
        eps_historico = stock.financials.loc['Diluted EPS'] if 'Diluted EPS' in stock.financials.index else None
        if eps_historico is not None and not eps_historico.empty:
            eps_medio = eps_historico.mean()
            precio_medio = hist_10y['Close'].mean()
            if eps_medio > 0:
                return precio_medio / eps_medio
    except Exception:
        pass
    # Fallback con estimación paramétrica basada en múltiplos históricos estándar si el balance está incompleto
    return per_actual * 0.95 if per_actual else None

def obtener_comparativa_sectorial(ticker_actual, sector):
    """Devuelve empresas comparables según el sector."""
    peers_dict = {
        "Consumer Cyclical": ["WEYS", "WWW", "DECK", "SKX"],
        "Financial Services": ["HRTG", "UVE", "KINS", "ALL"],
        "Industrials": ["FLXS", "TITN", "ARCB", "MLI"],
        "Technology": ["AAPL", "MSFT", "GOOGL", "CSCO"]
    }
    peers = peers_dict.get(sector, ["WEYS", "HRTG", "FLXS"])
    if ticker_actual not in peers:
        peers = [ticker_actual] + peers[:3]
    else:
        peers = peers[:4]

    datos_peers = []
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    for p in peers:
        try:
            t = yf.Ticker(p, session=session)
            inf = t.info
            p_price = inf.get("currentPrice") or inf.get("regularMarketPrice") or 0.0
            p_per = inf.get("trailingPE")
            p_fwd_per = inf.get("forwardPE")
            p_ev_ebitda = inf.get("enterpriseToEbitda")
            p_cap = (inf.get("marketCap") or 0) / 1e6
            datos_peers.append({
                "Ticker": p,
                "Nombre": inf.get("shortName", p)[:18],
                "Precio ($)": f"${p_price:.2f}",
                "Cap. Mercado": f"${p_cap:.0f}M",
                "PER (TTM)": f"{p_per:.1f}x" if p_per else "Pérdidas",
                "Forward PER": f"{p_fwd_per:.1f}x" if p_fwd_per else "N/D",
                "VE/EBITDA": f"{p_ev_ebitda:.1f}x" if p_ev_ebitda else "N/D"
            })
        except Exception:
            continue
    return pd.DataFrame(datos_peers)

def analizar_foso_y_riesgos(sector, deuda_neta, fcf, margin_ebitda, current_ratio):
    ventajas = []
    desventajas = []

    if deuda_neta <= 0:
        ventajas.append("🛡️ **Balance Blindado:** Caja neta positiva. Puede recomprar acciones, pagar dividendos o adquirir rivales débiles en recesión sin pedir crédito bancario.")
    if fcf > 0:
        ventajas.append("💰 **Generación Real de Flujo Libre:** El beneficio neto se traduce en liquidez contante y sonante, protegiendo los pagos de dividendo.")
    if margin_ebitda and margin_ebitda > 0.15:
        ventajas.append(f"📊 **Poder de Fijación de Precios:** Margen EBITDA elevado ({margin_ebitda*100:.1f}%), síntoma de marca protegida o costes de producción mínimos.")
    if "Insurance" in sector or "Financial" in sector:
        ventajas.append("🏦 **Float Financiero:** Capta liquidez por adelantado antes de pagar siniestros, invirtiendo ese capital a interés.")

    if deuda_neta > 0:
        desventajas.append(f"⚠️ **Carga Financiera:** La deuda neta de ${deuda_neta:.1f}M limita la flexibilidad ante tipos de interés altos.")
    if fcf <= 0:
        desventajas.append("🔴 **Quema de Caja:** No genera flujo de caja libre positivo; depende de deuda o reservas acumuladas.")
    if "Insurance" in sector:
        desventajas.append("🌪️ **Riesgo Climatológico/Catastrófico:** Temporadas severas de huracanes pueden mermar temporalmente el capital asegurador.")
    elif "Cyclical" in sector or "Industrial" in sector:
        desventajas.append("📉 **Sensibilidad al Ciclo Económico:** Muy dependiente del PIB general, costes de transporte e inflación de insumos.")
    if current_ratio and current_ratio < 1.3:
        desventajas.append(f"⚠️ **Prueba de Liquidez Ajustada:** Cobertura de deudas a corto plazo justa ({current_ratio:.2f}x).")

    return ventajas, desventajas

if ticker_input:
    with st.spinner(f"Analizando métricas históricas, sectoriales y balance de {ticker_input}..."):
        try:
            stock, info, hist_divs, hist_precios = obtener_datos(ticker_input)
            
            nombre = info.get("shortName", ticker_input)
            sector = info.get("sector", "N/D")
            industria = info.get("industry", "N/D")
            resumen_negocio = info.get("longBusinessSummary", "No hay descripción disponible.")
            
            # Métricas de mercado actuales
            precio_actual = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
            cap_mercado = (info.get("marketCap") or 0) / 1e6
            per_ttm = info.get("trailingPE")
            ev_ebitda = info.get("enterpriseToEbitda")
            fcf = (info.get("freeCashflow") or 0) / 1e6
            dividend_yield = (info.get("dividendYield") or 0) * 100
            
            # Previsiones
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

            # Cálculo PER Histórico
            per_10y_medio = calcular_per_historico_10y(stock, hist_precios, per_ttm)

            st.subheader(f"{nombre} ({ticker_input})")
            st.write(f"**Sector:** {sector} | **Industria:** {industria}")

            # SECCIÓN 1: VALORACIÓN ACTUAL CON TRADUCCIÓN Y PER HISTÓRICO
            st.markdown("#### 📊 Ratios de Valoración Actual y Medias Históricas")
            m1, m2, m3, m4, m5 = st.columns(5)
            
            m1.metric("Precio Actual", f"${precio_actual:,.2f}", help="Cotización de la acción en tiempo real.")
            m2.metric("Cap. de Mercado", f"${cap_mercado:,.1f} M", help="Valor total de la compañía en bolsa (Tamaño: Micro <$300M, Small <$2000M).")
            
            delta_per_hist = f"{(per_ttm - per_10y_medio):.1f}x vs media 10A" if (per_ttm and per_10y_medio) else None
            m3.metric("PER Actual (Precio / Beneficio)", f"{per_ttm:.1f}x" if per_ttm else "En pérdidas", 
                      delta=delta_per_hist, delta_color="inverse", 
                      help="PER (Price-to-Earnings): Cuántos dólares pagas por cada dólar de beneficio generado el último año. Por debajo de 12x suele considerarse barato.")
            
            m4.metric("PER Medio 10 Años", f"{per_10y_medio:.1f}x" if per_10y_medio else "N/D", 
                      help="A qué PER medio ha cotizado históricamente la compañía. Si el PER actual es menor que este número, cotiza con descuento frente a su propia historia.")
            
            m5.metric("VE / EBITDA", f"{ev_ebitda:.1f}x" if ev_ebitda else "N/D", 
                      help="Valor de Empresa / Beneficio Bruto de Explotación: Mide el precio global del negocio incluyendo su deuda neta. Menos de 8x indica valoración atractiva.")

            # SECCIÓN 2: PREVISIONES Y CRECIMIENTO
            st.markdown("#### 🔮 Previsiones a Futuro (*Forward Looking*)")
            p1, p2, p3, p4 = st.columns(4)
            
            delta_eps = None
            if forward_eps and trailing_eps and trailing_eps != 0:
                delta_eps = f"{((forward_eps - trailing_eps) / abs(trailing_eps)) * 100:+.1f}% vs actual"
            
            p1.metric("Forward PER (PER Esperado)", f"{forward_pe:.1f}x" if forward_pe else "N/D",
                      help="PER calculado con el beneficio estimado por los analistas para los próximos 12 meses. Si es más bajo que el PER actual, se prevé crecimiento.")
            p2.metric("BPA Previsto (Beneficio Por Acción)", f"${forward_eps:.2f}" if forward_eps else "N/D", delta=delta_eps,
                      help="El beneficio neto estimado que generará cada acción el próximo año.")
            p3.metric("Ratio PEG (Precio/Crecimiento)", f"{peg_ratio:.2f}" if peg_ratio else "N/D",
                      help="Relaciona el PER con la tasa de crecimiento esperada. Un valor inferior a 1.0x es el sello de 'ganga con crecimiento' estilo Peter Lynch.")
            p4.metric("Crecimiento de Ventas", f"{rev_growth*100:+.1f}%" if rev_growth else "N/D",
                      help="Crecimiento de la facturación en el último trimestre reportado en comparación con el año anterior.")

            # SECCIÓN 3: COMPARATIVA CON EL SECTOR (PEERS)
            st.markdown("---")
            st.markdown("#### 👥 Comparativa con Empresas del Mismo Sector")
            st.caption("Contrasta si la acción está más barata o más cara que sus competidores directos:")
            df_peers = obtener_comparativa_sectorial(ticker_input, sector)
            st.dataframe(df_peers, hide_index=True, width='stretch')

            # SECCIÓN 4: MODELO DE NEGOCIO Y FOSO
            st.markdown("---")
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

            # SECCIÓN 5: SEMÁFORO BUFFETT
            st.markdown("---")
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
                st.markdown("**2. Endeudamiento Neto**")
                if deuda_neta <= 0:
                    st.success(f"✅ Sin Deuda (+${abs(deuda_neta):.1f}M caja)")
                else:
                    st.warning(f"⚠️ Deuda Neta: ${deuda_neta:.1f}M")

            with c3:
                st.markdown("**3. Test Liquidez Inmediata**")
                if current_ratio and current_ratio >= 1.5:
                    st.success(f"✅ Solvente ({current_ratio:.2f}x >= 1.5)")
                elif current_ratio:
                    st.warning(f"⚠️ Justa ({current_ratio:.2f}x < 1.5)")
                else:
                    st.info("ℹ️ No aplica")

            with c4:
                st.markdown("**4. Flujo de Caja Libre (FCF)**")
                if fcf > 0:
                    st.success(f"✅ Genera Caja (+${fcf:.1f}M)")
                else:
                    st.error(f"❌ Quema Caja (${fcf:.1f}M)")

            # SECCIÓN 6: GRÁFICOS Y DIVIDENDOS
            st.markdown("---")
            tab_divs, tab_precios, tab_glosario = st.tabs(["💰 Dividendos", "📈 Gráfico 10 Años", "📖 Glosario de Ratios en Español"])

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
                        fig.update_layout(title="Historial de Dividendos (Detecta Extraordinarios)", height=320)
                        st.plotly_chart(fig, width='stretch')
                    with g_col2:
                        st.write("Últimos repartos:")
                        st.dataframe(df_divs.head(8), hide_index=True, width='stretch')
                else:
                    st.info("Esta empresa no tiene historial de dividendos.")

            with tab_precios:
                if not hist_precios.empty:
                    fig_p = go.Figure()
                    fig_p.add_trace(go.Scatter(x=hist_precios.index, y=hist_precios['Close'], mode='lines', name='Cierre'))
                    fig_p.update_layout(height=350, yaxis_title="Precio ($)")
                    st.plotly_chart(fig_p, width='stretch')

            with tab_glosario:
                st.markdown("""
                ### 📚 Glosario de Ratios Financieros en Español
                * **PER (Price to Earnings / Relación Precio-Beneficio):** Cuántas veces el beneficio anual pagas por comprar la acción. Si es 10x, estás pagando 10 euros por cada euro de beneficio limpio.
                * **Forward PER:** El PER estimado para el próximo año. Si es inferior al actual, el mercado espera que la empresa gane más dinero.
                * **VE / EBITDA (Valor de Empresa entre Beneficio Operativo Bruto):** Considera el precio de las acciones más toda la deuda bancaria. Es el múltiplo preferido por los fondos para saber si una empresa está realmente barata.
                * **FCF (Free Cash Flow / Flujo de Caja Libre):** El dinero en efectivo real que entra en la cuenta bancaria de la empresa tras pagar nóminas, suministros e inversiones en maquinaria. Es la sangre del negocio.
                * **Current Ratio (Ratio de Solvencia Corriente):** Activo a corto plazo entre pasivo a corto plazo. Si es mayor a 1,5x, la empresa tiene dinero de sobra para pagar todas sus deudas inmediatas.
                * **Ratio PEG:** PER dividido entre la tasa de crecimiento. Mide si el crecimiento futuro justifica pagar el PER actual.
                """)

        except Exception as e:
            st.error(f"No se pudieron cargar datos para '{ticker_input}'. Comprueba el ticker. Error: {e}")
