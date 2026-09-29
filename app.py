import streamlit as st
import yfinance as yf
import requests
import pandas as pd

# Configuración de página
st.set_page_config(
    page_title="Analizador Fundamental 'Estilo Buffett'",
    page_icon="🛡",
    layout="wide"
)

# --- CABECERAS PARA EVITAR BLOQUEO 401 DE YAHOO ---
@st.cache_resource
def get_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })
    return s

@st.cache_data(ttl=1800, show_spinner=False)
def obtener_datos(simbolo):
    simbolo = simbolo.strip().upper()
    session = get_session()
    ticker = yf.Ticker(simbolo, session=session)
    
    info = {}
    try:
        info = ticker.info
    except Exception:
        pass
    
    # Si .info falla por bloqueo (401) o viene vacío, usamos fast_info
    if not info or len(info) < 5:
        try:
            fi = ticker.fast_info
            info = {
                'shortName': simbolo,
                'currentPrice': getattr(fi, 'last_price', None),
                'marketCap': getattr(fi, 'market_cap', None),
                'fiftyTwoWeekHigh': getattr(fi, 'year_high', None),
                'fiftyTwoWeekLow': getattr(fi, 'year_low', None),
                'currency': getattr(fi, 'currency', 'USD'),
                'sector': 'N/D',
                'industry': 'N/D',
            }
        except Exception:
            info = {}
            
    return info

def formato_numero(num, es_moneda=False, simbolo_moneda="$"):
    if num is None or pd.isna(num):
        return "N/D"
    prefijo = f"{simbolo_moneda} " if es_moneda else ""
    if abs(num) >= 1e12:
        return f"{prefijo}{num/1e12:.2f} T"
    elif abs(num) >= 1e9:
        return f"{prefijo}{num/1e9:.2f} B"
    elif abs(num) >= 1e6:
        return f"{prefijo}{num/1e6:.2f} M"
    return f"{prefijo}{num:.2f}"

# --- BARRA LATERAL (BUSCADOR) ---
st.sidebar.header("🔍 Buscador de Empresa")
ticker_input = st.sidebar.text_input("Introduce el Ticker / Símbolo:", value="META").strip().upper()
buscar = st.sidebar.button("Analizar Empresa", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.markdown("**Ejemplos populares:**")
st.sidebar.caption("META, AAPL, MSFT, GOOGL, NVDA, WEYS")

# --- CABECERA PRINCIPAL ---
st.title("🛡️️ Analizador Fundamental 'Estilo Buffett'")
st.caption("Filtro de solvencia, ventajas competitivas, PER y múltiplos de valoración.")
st.markdown("---")

if ticker_input:
    with st.spinner(f"Cargando datos para {ticker_input}..."):
        info = obtener_datos(ticker_input)

    if not info or (not info.get('currentPrice') and not info.get('regularMarketPrice')):
        st.error(f"No se pudieron cargar los datos para '{ticker_input}'. Comprueba que el símbolo sea correcto y vuelve a intentarlo.")
    else:
        # Extraer variables principales
        nombre = info.get('longName') or info.get('shortName') or ticker_input
        sector = info.get('sector', 'N/D')
        industria = info.get('industry', 'N/D')
        precio = info.get('currentPrice') or info.get('regularMarketPrice') or 0.0
        cap_mercado = info.get('marketCap')
        moneda = info.get('currency', 'USD')
        simbolo_divisa = "$" if moneda == "USD" else ("€" if moneda == "EUR" else moneda)

        # Encabezado de la empresa
        st.subheader(f"{nombre} ({ticker_input})")
        st.markdown(f"**Sector:** {sector} &nbsp;|&nbsp; **Industria:** {industria}")

        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Precio Actual", f"{simbolo_divisa} {precio:.2f}")
        col2.metric("Cap. de Mercado", formato_numero(cap_mercado, es_moneda=True, simbolo_moneda=simbolo_divisa))
        
        per = info.get('trailingPE')
        per_fw = info.get('forwardPE')
        col3.metric("PER (TTM)", f"{per:.2f}" if per else "N/D")
        col4.metric("PER (Forward)", f"{per_fw:.2f}" if per_fw else "N/D")

        st.markdown("### 📊 Ratios de Valoración y Múltiplos")
        v_col1, v_col2, v_col3, v_col4 = st.columns(4)
        
        ev_ebitda = info.get('enterpriseToEbitda')
        pb = info.get('priceToBook')
        peg = info.get('pegRatio')
        ps = info.get('priceToSalesTrailing12Months')
        
        v_col1.metric("EV / EBITDA", f"{ev_ebitda:.2f}" if ev_ebitda else "N/D")
        v_col2.metric("Precio / Valor Contable (P/B)", f"{pb:.2f}" if pb else "N/D")
        v_col3.metric("PEG Ratio", f"{peg:.2f}" if peg else "N/D")
        v_col4.metric("Precio / Ventas (P/S)", f"{ps:.2f}" if ps else "N/D")

        st.markdown("### 🏛️ Solvencia y Salud Financiera (Filtro Buffett)")
        s_col1, s_col2, s_col3 = st.columns(3)
        
        debt_to_equity = info.get('debtToEquity')
        current_ratio = info.get('currentRatio')
        free_cash_flow = info.get('freeCashflow')
        
        s_col1.metric("Deuda / Fondos Propios", f"{debt_to_equity:.2f}%" if debt_to_equity else "N/D")
        s_col2.metric("Ratio Corriente (Liquidez)", f"{current_ratio:.2f}" if current_ratio else "N/D")
        s_col3.metric("Free Cash Flow", formato_numero(free_cash_flow, es_moneda=True, simbolo_moneda=simbolo_divisa))

        st.markdown("### 📈 Rentabilidad y Márgenes (Moat)")
        r_col1, r_col2, r_col3 = st.columns(3)
        
        roe = info.get('returnOnEquity')
        roa = info.get('returnOnAssets')
        margen_op = info.get('operatingMargins')
        
        r_col1.metric("ROE (Rentabilidad Financiera)", f"{roe * 100:.2f}%" if roe else "N/D")
        r_col2.metric("ROA", f"{roa * 100:.2f}%" if roa else "N/D")
        r_col3.metric("Margen Operativo", f"{margen_op * 100:.2f}%" if margen_op else "N/D")
