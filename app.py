import os
import re
import time
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import streamlit as st
import pandas as pd
from datetime import date

# Intento seguro de cargar dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Importación de la librería oficial google-genai
try:
    from google import genai
    from google.genai import types
    GENAI_INSTALADO = True
except ImportError:
    GENAI_INSTALADO = False

# Configuración inicial de la página
st.set_page_config(
    page_title="Sistema Integral de Negocio Vehicular IA",
    page_icon="🚗",
    layout="wide"
)

# Inicializar estado de sesión para la placa de manera global
if "placa_actual" not in st.session_state:
    st.session_state["placa_actual"] = "N/A"

# Función auxiliar para dar formato de pesos colombianos con separador de miles (.)
def formato_cop(valor):
    try:
        return f"${int(valor):,}".replace(",", ".")
    except Exception:
        return "$ 0"

# ==========================================
# BASE DE DATOS INFORMATIVA DE VEHÍCULOS ALTA ROTACIÓN
# ==========================================
CARROS_ALTA_ROTACION = [
    {
        "Marca": "Kia",
        "Línea / Modelo": "Picanto (All New / ION)",
        "Rango de Años": "2015 - 2023",
        "Rango Precio Estimado (COP)": "$32M - $55M",
        "Días Promedio Rotación": "7 - 15 días",
        "Nivel de Riesgo": "🟢 Muy Bajo",
        "Público Objetivo": "Primer carro, plataformas, uso diario",
        "Versión Recomendada": "Vibrant / Zenith (1.25L)"
    },
    {
        "Marca": "Chevrolet",
        "Línea / Modelo": "Onix / Joy",
        "Rango de Años": "2017 - 2023",
        "Rango Precio Estimado (COP)": "$38M - $62M",
        "Días Promedio Rotación": "10 - 18 días",
        "Nivel de Riesgo": "🟢 Muy Bajo",
        "Público Objetivo": "Jóvenes, ejecutivos, familias pequeñas",
        "Versión Recomendada": "LTZ / Premier / Joy 1.4"
    },
    {
        "Marca": "Renault",
        "Línea / Modelo": "Sandero / Stepway",
        "Rango de Años": "2016 - 2022",
        "Rango Precio Estimado (COP)": "$35M - $58M",
        "Días Promedio Rotación": "10 - 20 días",
        "Nivel de Riesgo": "🟢 Muy Bajo",
        "Público Objetivo": "Familias, viajes, todo propósito",
        "Versión Recomendada": "Dynamique / Intens / Expression 1.6"
    },
    {
        "Marca": "Renault",
        "Línea / Modelo": "Logan",
        "Rango de Años": "2016 - 2022",
        "Rango Precio Estimado (COP)": "$33M - $52M",
        "Días Promedio Rotación": "12 - 20 días",
        "Nivel de Riesgo": "🟢 Muy Bajo",
        "Público Objetivo": "Trabajo, plataformas, familias",
        "Versión Recomendada": "Life / Intens 1.6 16v"
    },
    {
        "Marca": "Renault",
        "Línea / Modelo": "Duster",
        "Rango de Años": "2015 - 2022",
        "Rango Precio Estimado (COP)": "$48M - $75M",
        "Días Promedio Rotación": "10 - 15 días",
        "Nivel de Riesgo": "🟢 Muy Bajo",
        "Público Objetivo": "Familias, terreno destapado, viajes",
        "Versión Recomendada": "Dynamique 2.0 4x4 / 1.3 Turbo"
    },
    {
        "Marca": "Chevrolet",
        "Línea / Modelo": "Tracker",
        "Rango de Años": "2016 - 2022",
        "Rango Precio Estimado (COP)": "$48M - $78M",
        "Días Promedio Rotación": "15 - 25 días",
        "Nivel de Riesgo": "🟡 Bajo",
        "Público Objetivo": "Familias urbanas, mujeres, viajes",
        "Versión Recomendada": "LTZ / LS Turbo"
    },
    {
        "Marca": "Suzuki",
        "Línea / Modelo": "Swift",
        "Rango de Años": "2018 - 2023",
        "Rango Precio Estimado (COP)": "$42M - $65M",
        "Días Promedio Rotación": "12 - 20 días",
        "Nivel de Riesgo": "🟢 Muy Bajo",
        "Público Objetivo": "Universitarios, ahorradores de gasolina",
        "Versión Recomendada": "1.2 Dualjet / Hybrid"
    },
    {
        "Marca": "Mazda",
        "Línea / Modelo": "Mazda 2",
        "Rango de Años": "2016 - 2022",
        "Rango Precio Estimado (COP)": "$48M - $70M",
        "Días Promedio Rotación": "15 - 22 días",
        "Nivel de Riesgo": "🟢 Muy Bajo",
        "Público Objetivo": "Jóvenes, profesionales",
        "Versión Recomendada": "Grand Touring / Touring"
    },
    {
        "Marca": "Renault",
        "Línea / Modelo": "Kwid",
        "Rango de Años": "2019 - 2023",
        "Rango Precio Estimado (COP)": "$30M - $43M",
        "Días Promedio Rotación": "10 - 18 días",
        "Nivel de Riesgo": "🟢 Muy Bajo",
        "Público Objetivo": "Primer auto, ciudad",
        "Versión Recomendada": "Outsider / Zen"
    },
    {
        "Marca": "Nissan",
        "Línea / Modelo": "March",
        "Rango de Años": "2015 - 2021",
        "Rango Precio Estimado (COP)": "$32M - $48M",
        "Días Promedio Rotación": "12 - 20 días",
        "Nivel de Riesgo": "🟢 Muy Bajo",
        "Público Objetivo": "Uso diario, excelente fuerza",
        "Versión Recomendada": "Sense / Connect 1.6"
    }
]

# ==========================================
# CONFIGURACIÓN DE BARRA LATERAL
# ==========================================
st.sidebar.title("🎛️ Menú Principal")
modulo_seleccionado = st.sidebar.selectbox(
    "Seleccione el Módulo de Trabajo:",
    ["🚗 Módulo COMPRA (Peritaje & Oferta)", "🏷️ Módulo VENTA", "📜 Módulo CONTRATO"]
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Configuración de Inteligencia Artificial")

usar_ia_local = st.sidebar.checkbox("🏠 Usar IA Local (Ollama - Llama Vision)", value=False, help="Requiere tener instalado Ollama en tu equipo")

if not GENAI_INSTALADO:
    st.sidebar.error("⚠️ Falta la librería oficial. Ejecuta en terminal: `pip install google-genai`")

api_key_gemini_guardada = os.getenv("GEMINI_API_KEY", "")

api_key = st.sidebar.text_input(
    "Llave de API de Google Gemini (Gratuita)", 
    value=api_key_gemini_guardada,
    type="password", 
    help="Principal (Google AI Studio - gemini-3.8-flash)"
)

if api_key:
    st.sidebar.success("🔑 Gemini API cargada")

# ==========================================
# MOTOR INTERNO ANTI-BLOQUEO (JINA AI + SCRAPING)
# ==========================================
def extraer_publicacion_y_fotos(url_raw):
    url_limpia = url_raw.split("#")[0].split("?")[0]
    titulo = ""
    precio = None
    fotos_representativas = []
    placa_detectada = "N/A"

    try:
        jina_url = f"https://r.jina.ai/{url_limpia}"
        headers_jina = {"Accept": "application/json", "X-With-Generated-Alt": "true"}
        res_jina = requests.get(jina_url, headers=headers_jina, timeout=15)
        
        if res_jina.status_code == 200:
            content = res_jina.text
            
            for line in content.split("\n"):
                if line.startswith("# "):
                    titulo = line.replace("# ", "").strip()
                    break
            
            if not titulo or "Mercado Libre" in titulo:
                match_slug = re.search(r'/MCO-\d+-(.*?)(?:-JM)?$', url_limpia)
                if match_slug:
                    titulo = match_slug.group(1).replace("-", " ").title()

            precios_match = re.findall(r"\$\s*([\d\.,]+)", content)
            for p_raw in precios_match:
                p_clean = re.sub(r"[^\d]", "", p_raw)
                if len(p_clean) >= 7:
                    val = int(p_clean)
                    if val >= 5000000:
                        precio = val
                        break

            ids_unicos = []
            patron_ml = r'https?://http2\.mlstatic\.com/D_NQ_NP_([0-9A-Za-z_-]+)\.(?:jpg|jpeg|png|webp)'
            for match in re.findall(patron_ml, content):
                clean_id = re.sub(r'^(?:2X_|3X_|\d+X_)', '', match)
                clean_id = re.sub(r'-[OIVFDS]$', '', clean_id)
                if clean_id not in ids_unicos and len(clean_id) > 5:
                    ids_unicos.append(clean_id)

            palabras_basura = ["meli", "logo", "banner", "icon", "cashback", "garantia", "credito", "publicidad", "financiacion", "footer", "header"]
            fotos_candidatas = []
            for clean_id in ids_unicos:
                if any(bad in clean_id.lower() for bad in palabras_basura):
                    continue
                url_hd = f"https://http2.mlstatic.com/D_NQ_NP_{clean_id}-O.jpg"
                if url_hd not in fotos_candidatas:
                    fotos_candidatas.append(url_hd)

            total_cand = len(fotos_candidatas)
            if total_cand <= 5:
                fotos_representativas = fotos_candidatas
            elif total_cand > 5:
                indices = [0, int(total_cand * 0.25), int(total_cand * 0.50), int(total_cand * 0.75), total_cand - 1]
                for idx in indices:
                    fotos_representativas.append(fotos_candidatas[idx])

            match_p = re.search(r'\b([A-Za-z]{3}\s*-?\s*\d{3})\b', content)
            if match_p:
                cand = match_p.group(1).upper().replace("-", "").replace(" ", "")
                if not any(bad in cand for bad in ["BMW", "AUD", "CHE", "REN", "NIS", "COP"]):
                    placa_detectada = cand

            if fotos_representativas:
                return titulo, precio, fotos_representativas, placa_detectada, None
    except Exception:
        pass

    return titulo, precio, fotos_representativas, placa_detectada, None

# ==========================================
# CÁLCULO DE SOAT Y TECNO
# ==========================================
def calcular_costos_documentos_por_vehiculo(titulo_vehiculo):
    titulo_lower = titulo_vehiculo.lower() if titulo_vehiculo else ""
    es_suv_o_grande = any(k in titulo_lower for k in [
        "camioneta", "suv", "captur", "duster", "koleos", "prado", "fortuner", 
        "tucson", "sportage", "escape", "ecosport", "tracker", "rav4", "CX-", 
        "2.0", "2.2", "2.4", "2.5", "3.0", "4x4", "turbo"
    ])
    
    soat_estimado = 1180000 if es_suv_o_grande else 800000
    tecno_estimada = 200000
    return soat_estimado, tecno_estimada

# ==========================================
# EXTRACCIÓN INTELIGENTE EN CASCADA PARA PLACA Y ARREGLOS
# ==========================================
def optimizar_imagen_para_ia(img_pil, max_size=(500, 500)):
    img_copy = img_pil.copy()
    img_copy.thumbnail(max_size, Image.Resampling.LANCZOS)
    if img_copy.mode in ("RGBA", "P"):
        img_copy = img_copy.convert("RGB")
    return img_copy

def extraer_placa_de_dictamen(texto_dictamen):
    if not texto_dictamen:
        return None
    
    match = re.search(r'(?:PLACA\s*DETECTADA|PLACA)\s*[:\*\_]*\s*\[?\s*([A-Za-z]{3}\s*-?\s*\d{3})\s*\]?', texto_dictamen, re.IGNORECASE)
    if match:
        cand = match.group(1).upper().replace("-", "").replace(" ", "")
        if cand != "N/A" and len(cand) == 6:
            return cand
    
    matches_gen = re.findall(r'\b([A-Za-z]{3}\s*-?\s*\d{3})\b', texto_dictamen)
    for m in matches_gen:
        cand = m.upper().replace("-", "").replace(" ", "")
        if not any(bad in cand for bad in ["BMW", "AUD", "CHE", "REN", "NIS", "COP", "SOAT"]):
            return cand
            
    return None

def extraer_monto_arreglos_de_dictamen(texto_dictamen):
    if not texto_dictamen:
        return 800000
    
    match = re.search(r'(?:Cá?lculo\s*Estimado\s*de\s*Arreglos|6\.\s*).*?[:\$\s]*([\d\.,]{5,10})', texto_dictamen, re.IGNORECASE)
    if match:
        raw_val = match.group(1).replace(".", "").replace(",", "").strip()
        if raw_val.isdigit():
            val = int(raw_val)
            if 50000 <= val <= 30000000:
                return val
    
    numeros = re.findall(r'\$?\s*(\d{1,3}(?:\.\d{3}){1,2}|\d{6,8})', texto_dictamen)
    for n in numeros:
        v = int(n.replace(".", ""))
        if 100000 <= v <= 20000000:
            return v

    return 800000

def analizar_con_ollama_local(imagenes_pil):
    import base64
    imgs_b64 = []
    for img in imagenes_pil[:5]:
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=75)
        imgs_b64.append(base64.b64encode(buffered.getvalue()).decode("utf-8"))

    payload = {
        "model": "llama3.2-vision",
        "prompt": "Eres perito en vehículos en Colombia. 1. PLACA DETECTADA: [Identifica la placa visible ej: HCZ515, o N/A]. 2. Exterior. 3. Interior. 4. Puntos Fuertes. 5. Puntos de Negociación. 6. Cálculo Estimado de Arreglos (COP).",
        "images": imgs_b64,
        "stream": False
    }

    try:
        res = requests.post("http://localhost:11434/api/generate", json=payload, timeout=30)
        if res.status_code == 200:
            return f"🏠 [Dictamen generado por IA Local (Ollama)]:\n\n" + res.json().get("response", ""), None
        else:
            return None, f"Ollama HTTP {res.status_code}"
    except Exception as e:
        return None, f"Ollama Error: {str(e)}"

def analizar_imagenes_con_ia(imagenes_pil, key_gemini, activar_local):
    imgs_optimizadas = [optimizar_imagen_para_ia(img) for img in imagenes_pil[:5]]
    
    prompt = """
    Eres perito experto en autos usados en Colombia. Analiza minuciosamente las imágenes adjuntas (hasta 5 fotos):
    1. **PLACA DETECTADA:** Indica claramente la placa encontrada (3 letras y 3 números, ej: HCZ515) o N/A si ninguna es visible.
    2. **Exterior:** Pintura y latonería.
    3. **Interior:** Tapicería y tablero.
    4. **Puntos Fuertes:** Ventajas.
    5. **Puntos de Negociación:** Imperfecciones.
    6. **Cálculo Estimado de Arreglos (COP):** Solo valor numérico (ej: 850000).
    """

    errores_proceso = []

    if activar_local:
        res_local, err_local = analizar_con_ollama_local(imgs_optimizadas)
        if res_local:
            return res_local
        if err_local:
            errores_proceso.append(err_local)

    if key_gemini and GENAI_INSTALADO:
        try:
            client = genai.Client(api_key=key_gemini)
            
            partes_contenido = [prompt]
            for img in imgs_optimizadas:
                buf = BytesIO()
                img.save(buf, format="JPEG", quality=80)
                partes_contenido.append(
                    types.Part.from_bytes(
                        data=buf.getvalue(),
                        mime_type="image/jpeg"
                    )
                )

            for intento in range(3):
                try:
                    response = client.models.generate_content(
                        model='gemini-3.8-flash', 
                        contents=partes_contenido
                    )
                    if response and response.text:
                        return f"🤖 [Dictamen generado por Google Gemini (gemini-3.8-flash)]:\n\n" + response.text
                except Exception as e_mod:
                    err_msg = str(e_mod)
                    if "503" in err_msg and intento < 2:
                        time.sleep(3)
                        continue
                    errores_proceso.append(f"Gemini (gemini-3.8-flash): {err_msg}")
                    break

        except Exception as e_genai:
            errores_proceso.append(f"Gemini Init Error: {str(e_genai)}")

    txt_errores = " | ".join(errores_proceso) if errores_proceso else "No se pudo obtener respuesta de los modelos."
    st.error(f"❌ No se pudo completar la inspección. Detalle de los errores encontrados:\n\n{txt_errores}")
    return None

# =====================================================================
# MÓDULO 1: COMPRA
# =====================================================================
if modulo_seleccionado == "🚗 Módulo COMPRA (Peritaje & Oferta)":
    st.title("🚗 Módulo de COMPRA - Valuador e Inspector Inteligente (Colombia - COP)")
    st.caption("Análisis de mercado comercial, inspección visual con Inteligencia Artificial y calculadora de oferta.")

    st.subheader("🔗 1. Ingrese el Enlace del Vehículo")
    url_input = st.text_input("Pegue la URL de la publicación (TuCarro / MercadoLibre / CarroYa, etc.):", placeholder="https://carro.mercadolibre.com.co/...")

    titulo_vehiculo = ""
    precio_publicado = None
    fotos_encontradas = []
    placa_extraida = "N/A"

    if url_input:
        with st.spinner("Extrayendo inteligentemente título, precio y fotos del enlace..."):
            titulo_vehiculo, precio_publicado, fotos_encontradas, placa_extraida, error = extraer_publicacion_y_fotos(url_input)
            if error:
                st.warning(f"⚠️ Nota: {error}")
            else:
                txt_titulo = titulo_vehiculo if titulo_vehiculo else "Vehículo Mercado Libre"
                st.success(f"✅ **Vehículo identificado:** {txt_titulo}")
                if precio_publicado:
                    st.info(f"💵 **Precio en la publicación:** {formato_cop(precio_publicado)} PESOS")
                
                if "url_anterior" not in st.session_state or st.session_state.get("url_anterior") != url_input:
                    if placa_extraida and placa_extraida != "N/A":
                        st.session_state["placa_actual"] = placa_extraida
                    st.session_state["url_anterior"] = url_input

    st.markdown("---")

    tab_comercial, tab_ranking, tab_ia, tab_docs, tab_legales = st.tabs([
        "📈 Análisis Comercial de Mercado",
        "⭐ Guía de Carros de Mayor Rotación",
        "👁️ Inspección de Fotos (IA / Manual)",
        "📄 Documentos y Calculadora de Oferta",
        "⚖️ Enlaces Legales Oficiales"
    ])

    # TAB 1: ANÁLISIS COMERCIAL
    with tab_comercial:
        st.header("📈 Análisis Comercial, Oferta y Demanda en el Mercado")
        st.markdown("Evalúa la competitividad del vehículo analizado frente a la oferta actual y la demanda real en Colombia.")

        col_m1, col_m2 = st.columns(2)
        val_inicial = precio_publicado if precio_publicado else 59000000

        with col_m1:
            st.subheader("💰 Parámetros de Precio")
            precio_publicado_input = st.number_input("Precio de la Publicación Analizada (PESOS)", value=int(val_inicial), step=1000000, format="%d")
            st.caption(f"Valor en texto: **{formato_cop(precio_publicado_input)}**")
            
            ref_min = st.number_input("Precio Mínimo de Mercado (Piso)", value=int(val_inicial * 0.9), step=1000000, format="%d")
            st.caption(f"Valor en texto: **{formato_cop(ref_min)}**")
            
            ref_max = st.number_input("Precio Máximo de Mercado (Techo)", value=int(val_inicial * 1.1), step=1000000, format="%d")
            st.caption(f"Valor en texto: **{formato_cop(ref_max)}**")

        with col_m2:
            st.subheader("📊 Diagnóstico de Oferta y Demanda")
            precio_promedio_mercado = (ref_min + ref_max) / 2
            st.metric(label="📊 Precio Promedio de Mercado", value=f"{formato_cop(precio_promedio_mercado)} PESOS")

            diferencia = precio_publicado_input - precio_promedio_mercado
            
            st.markdown("---")
            if diferencia > 0:
                st.error(f"⚠️ **DEMANDA BAJA / SOBREPRECIO:** Este vehículo está **{formato_cop(diferencia)} por encima** del promedio. Hay mucha oferta similar más barata, por lo que tardará más tiempo en venderse a menos que negocies una rebaja fuerte.")
            else:
                st.success(f"🚀 **ALTA DEMANDA / OPORTUNIDAD:** Este vehículo está **{formato_cop(abs(diferencia))} por debajo** del promedio. Su rotación estimada en el mercado será rápida (menor a 15 días) debido a la alta demanda.")

            st.info("💡 **Índice de Liquidez:** Vehículos en este rango de precio rotan comercialmente entre **10 a 20 días** si se encuentran en colores comerciales (Blanco, Gris, Negro).")

    # TAB 2: GUÍA DE ROTACIÓN
    with tab_ranking:
        st.header("⭐ Listado Estratégico de Vehículos de Alta Rotación (Menor Riesgo)")
        st.caption("Esta guía interactiva te ayuda a identificar cuáles vehículos comprar para vender rápido y asegurar liquidez constante.")

        df_rotacion = pd.DataFrame(CARROS_ALTA_ROTACION)

        marcas_disponibles = ["Todas"] + list(df_rotacion["Marca"].unique())
        marca_filtrada = st.selectbox("🔍 Filtrar por Marca:", marcas_disponibles)

        if marca_filtrada != "Todas":
            df_mostrar = df_rotacion[df_rotacion["Marca"] == marca_filtrada]
        else:
            df_mostrar = df_rotacion

        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)

        st.markdown("""
        ---
        ### 💡 Reglas de Oro para Compra y Venta de Alta Rotación en Colombia:
        1. **Colores Comerciales:** Prefiere siempre **Blanco, Gris Plata, Gris Plomo y Negro**. Los colores exóticos (Rojo, Amarillo) tardan hasta el doble de tiempo en venderse.
        2. **Caja Mecánica vs. Automática:** En citycars (Picanto, Onix, Kwid), la caja mecánica se vende muy rápido a jóvenes o conductores de app; la caja automática se vende a mejor precio.
        3. **Límite de Kilometraje:** Procura adquirir vehículos con menos de **15.000 km por año de uso**.
        """)

    # TAB 3: INSPECCIÓN IA
    with tab_ia:
        st.header("👁️ Inspección Visual y Registro de Peritaje")
        
        imgs_pil_list = []

        if fotos_encontradas:
            st.subheader(f"📸 Fotos principales extraídas del enlace ({len(fotos_encontradas)} fotos):")
            cols = st.columns(min(len(fotos_encontradas), 5))
            for j, img_url in enumerate(fotos_encontradas[:5]):
                with cols[j]:
                    st.image(img_url, use_container_width=True, caption=f"Foto {j + 1}")
            
            for url_f in fotos_encontradas[:5]:
                try:
                    res_f = requests.get(url_f, timeout=8)
                    if res_f.status_code == 200:
                        imgs_pil_list.append(Image.open(BytesIO(res_f.content)))
                except Exception:
                    pass

        st.markdown("---")
        archivos_cargados = st.file_uploader(
            "Cargar o tomar fotos desde el celular (Opcional - Respaldo):", 
            type=["jpg", "jpeg", "png", "webp"], 
            accept_multiple_files=True
        )

        if archivos_cargados:
            for archivo in archivos_cargados[:5]:
                img_subida = Image.open(archivo)
                if img_subida not in imgs_pil_list:
                    imgs_pil_list.append(img_subida)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔍 Iniciar Inspección por IA"):
            # Verificación flexible: permite usar fotos extraídas o fotos subidas manualmente
            if not api_key and not usar_ia_local:
                st.error("⚠️ Por favor ingresa tu Llave de API de Google Gemini en la barra lateral o activa la IA local.")
            elif imgs_pil_list:
                with st.spinner("Generando dictamen pericial con Inteligencia Artificial..."):
                    resultado_ia = analizar_imagenes_con_ia(imgs_pil_list, api_key, usar_ia_local)
                    if resultado_ia:
                        st.session_state["dictamen_peritaje"] = resultado_ia
                        
                        placa_detectada_ia = extraer_placa_de_dictamen(resultado_ia)
                        if placa_detectada_ia and placa_detectada_ia != "N/A":
                            st.session_state["placa_actual"] = placa_detectada_ia

                        costo_extraido = extraer_monto_arreglos_de_dictamen(resultado_ia)
                        st.session_state["costo_arreglos_estimado"] = costo_extraido
            else:
                st.error("⚠️ No hay fotos disponibles. El enlace no pudo extraer imágenes o debes cargar al menos una foto manualmente usando el botón 'Upload' de arriba.")

        st.markdown("---")
        st.subheader("📝 Dictamen del Peritaje (Editable / Manual)")
        
        dictamen_defecto = st.session_state.get("dictamen_peritaje", "• Carrocería: Sin detalles graves de pintura visibles.\n• Interior: Cojinería y tablero en aceptable estado.\n• Mecánica/Llantas: Requiere revisión técnica presencial.\n\n4. **Puntos Fuertes:** Buena conservación estética exterior e interior.\n5. **Puntos de Negociación:** Raspones leves o desgaste visible.\n6. **Cálculo Estimado de Arreglos (COP):** 800000")
        
        observaciones_manuales = st.text_area(
            "Escribe o ajusta las observaciones del estado del vehículo:", 
            value=dictamen_defecto, 
            height=200
        )
        st.info("💡 Este dictamen te sirve de soporte para la negociación con el vendedor.")

    # TAB 4: CALCULADORA
    with tab_docs:
        st.header("📄 Calculadora Financiera y Gastos de Traspaso")

        col_f1, col_f2 = st.columns(2)

        with col_f1:
            presupuesto_disponible = st.number_input("Tu Presupuesto Máximo Disponible (PESOS)", value=59000000, step=1000000, format="%d")
            st.caption(f"Valor en texto: **{formato_cop(presupuesto_disponible)}**")
            
            pct_bajar_vender = st.slider("PORCENTAJE A BAJAR PARA VENDER (%)", min_value=1, max_value=15, value=4)

        with col_f2:
            venc_soat = st.date_input("Vencimiento SOAT", value=date.today())
            venc_tecno = st.date_input("Vencimiento Tecnomecánica", value=date.today())

        st.markdown("---")
        st.subheader("🏛️ Estimación de Gastos de Traspaso (Normativa Colombia)")

        col_traspaso1, col_traspaso2 = st.columns(2)
        derechos_traspaso_base = 260400  

        with col_traspaso1:
            modalidad_traspaso = st.radio(
                "Distribución de Derechos de Traspaso del Organismo de Tránsito:",
                ["Pagar 50% Comprador / 50% Vendedor (Estándar)", "Pagar 100% Comprador"]
            )
            gasto_derechos_comprador = (derechos_traspaso_base / 2) if "50%" in modalidad_traspaso else derechos_traspaso_base

        valor_inicial_vehiculo = float(precio_publicado_input) if 'precio_publicado_input' in locals() else 59000000
        pct_bajar_decimal = pct_bajar_vender / 100.0

        with col_traspaso2:
            incluir_retefuente = st.checkbox("Asumir la Retención en la Fuente del 1% (Legalmente a cargo del Vendedor)", value=False)
            val_reventa_preliminar = valor_inicial_vehiculo * (1.0 - pct_bajar_decimal)
            monto_retefuente = (val_reventa_preliminar * 0.01) if incluir_retefuente else 0

        costo_traspaso_auto = int(gasto_derechos_comprador + monto_retefuente)

        st.markdown("---")
        st.subheader("📋 Cuadro Integrado de Costos Fijos y Variables (Fórmulas formula3.xlsx)")

        soat_sugerido_web, tecno_sugerido_web = calcular_costos_documentos_por_vehiculo(titulo_vehiculo if 'titulo_vehiculo' in locals() else "")

        hoy = date.today()
        soat_vencido_flag = venc_soat < hoy
        tecno_vencido_flag = venc_tecno < hoy

        costo_soat = 0
        costo_tecno = 0

        valor_arreglos_inicial = st.session_state.get("costo_arreglos_estimado", 800000)

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            costo_peritaje = st.number_input("COSTO PERITAJE (PESOS)", value=180000, step=20000, format="%d")
            st.caption(f"Valor en texto: **{formato_cop(costo_peritaje)}**")
        with col_c2:
            costo_arreglos = st.number_input(
                "COSTOS ARREGLOS (IA / Taller) (PESOS)", 
                value=int(valor_arreglos_inicial), 
                step=50000, 
                format="%d"
            )
            st.caption(f"Valor en texto: **{formato_cop(costo_arreglos)}**")

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            if soat_vencido_flag:
                costo_soat = st.number_input("COSTO DE SOAT (Vencido - Según Vehículo)", value=int(soat_sugerido_web), step=50000, format="%d")
                st.caption(f"Valor en texto: **{formato_cop(costo_soat)}**")
            else:
                st.markdown("✅ **SOAT Vigente** (Costo: $0)")
                costo_soat = 0

        with col_d2:
            if tecno_vencido_flag:
                costo_tecno = st.number_input("COSTO TECNO (Vencida - Trámite CDA)", value=int(tecno_sugerido_web), step=50000, format="%d")
                st.caption(f"Valor en texto: **{formato_cop(costo_tecno)}**")
            else:
                st.markdown("✅ **Tecnomecánica Vigente** (Costo: $0)")
                costo_tecno = 0

        st.markdown("<br>", unsafe_allow_html=True)
        costo_traspaso_input = st.number_input(
            "costo TRASPASO (Editable según Opciones)", 
            value=int(costo_traspaso_auto), 
            step=10000, 
            format="%d"
        )
        st.caption(f"Valor en texto: **{formato_cop(costo_traspaso_input)}**")

        utilidad_esperada = st.number_input("UTILIDAD ESPERADA (PESOS)", value=3000000, step=500000, format="%d")
        st.caption(f"Valor en texto: **{formato_cop(utilidad_esperada)}**")

        # FÓRMULAS EXACTAS DE formula3.xlsx
        valor_reventa_rapida = valor_inicial_vehiculo - (valor_inicial_vehiculo * pct_bajar_decimal)
        
        valor_oferta = (
            valor_reventa_rapida 
            - costo_soat 
            - costo_tecno 
            - costo_traspaso_input 
            - costo_arreglos 
            - utilidad_esperada 
            - costo_peritaje
        )

        diferencia_pub_oferta = valor_inicial_vehiculo - valor_oferta
        porcentaje_utilidad = (utilidad_esperada / valor_oferta) if valor_oferta > 0 else 0
        porcentaje_precio_final_ofertado = (diferencia_pub_oferta / valor_inicial_vehiculo) if valor_inicial_vehiculo > 0 else 0

        st.markdown("---")
        st.subheader("🎯 Resultado de Oferta Sugerida (Fórmulas formula3.xlsx)")

        res_c1, res_c2, res_c3, res_c4, res_c5 = st.columns(5)
        with res_c1:
            st.metric(label="VALOR REVENTA RÁPIDA", value=f"{formato_cop(valor_reventa_rapida)} PESOS")
        with res_c2:
            st.metric(label="VALOR OFERTA", value=f"{formato_cop(valor_oferta)} PESOS")
            if valor_oferta > presupuesto_disponible:
                st.warning("⚠️ La oferta supera tu presupuesto disponible.")
            else:
                st.success("✅ Oferta dentro de tu presupuesto.")
        with res_c3:
            st.metric(label="DIFERENCIA PUB. Y OFERTA", value=f"{formato_cop(diferencia_pub_oferta)} PESOS")
        with res_c4:
            st.metric(label="PORCENTAJE UTILIDAD", value=f"{porcentaje_utilidad * 100:.2f}%")
        with res_c5:
            st.metric(label="% PRECIO FINAL OFERTADO", value=f"{porcentaje_precio_final_ofertado * 100:.2f}%")

    # TAB 5: ENLACES LEGALES
    with tab_legales:
        st.header("⚖️ Verificación de Antecedentes y Trámites Legales")
        
        val_placa_state = st.session_state.get("placa_actual", "N/A")
        
        col_pl1, col_pl2 = st.columns([1, 2])
        with col_pl1:
            placa_consulta = st.text_input(
                "🚘 Placa del Vehículo (Lectura por IA / Editable):", 
                value=val_placa_state,
                placeholder="Ej: HHZ127 o N/A",
                max_chars=7
            )
            st.session_state["placa_actual"] = placa_consulta.upper().strip()

        with col_pl2:
            if placa_consulta and placa_consulta.upper() != "N/A":
                placa_clean = placa_consulta.upper().strip()
                st.markdown("**📋 Haz clic en el botón flotante en la esquina del recuadro para copiar la placa:**")
                st.code(placa_clean, language=None)
            else:
                st.warning("⚠️ La placa no fue indicada en el texto de la publicación. Presiona '🔍 Iniciar Inspección por IA' en la pestaña de fotos para que la IA la lea directamente de la foto o digítala manualmente.")

        st.markdown("---")
        st.markdown("""
        * 📋 **[RUNT - Consulta de Histórico Vehicular](https://www.runt.gov.co/actores/ciudadano/consulta-historico-vehicular):** **(CONSULTA CLAVE)** Informe detallado con historial de propietarios, embargos, prendas y licencias.
        * 💥 **[FASECOLDA - Historial de Accidentes](https://www.fasecolda.com/ramos/automoviles/historial-de-accidentes-de-vehiculos-asegurados/):** **(CONSULTA OBLIGATORIA)** Historial de siniestros y reclamaciones por pérdida parcial o total.
        * 🚦 **[SIMIT - Portal Oficial FCM](https://www.fcm.org.co/simit/#/home-public):** Consulta nacional de comparendos e infracciones de tránsito.
        * 🏛️ **[Movilidad Bogotá - Web Fénix](https://webfenix.movilidadbogota.gov.co/#/consulta-pagos):** Consulta específica de comparendos en Bogotá.
        """)

# =====================================================================
# MÓDULO 2: VENTA
# =====================================================================
elif modulo_seleccionado == "🏷️ Módulo VENTA":
    st.title("🏷️ Módulo de VENTA - Estrategia Comercial y Publicación")
    st.info("📌 Estrategia comercial y precio objetivo de venta.")
    
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.subheader("📋 Datos de Publicación")
        st.text_input("Título de la Publicación de Venta")
        val_compra_v = st.number_input("Precio de Compra Real (COP)", value=55000000, step=1000000, format="%d")
        st.caption(f"Valor in texto: **{formato_cop(val_compra_v)}**")
        val_rep_v = st.number_input("Inversión Real en Reparaciones/Adecuaciones (COP)", value=1500000, step=100000, format="%d")
        st.caption(f"Valor in texto: **{formato_cop(val_rep_v)}**")
    with col_v2:
        st.subheader("🎯 Definición de Precio de Venta")
        val_obj_v = st.number_input("Precio Objetivo de Venta (COP)", value=63000000, step=1000000, format="%d")
        st.caption(f"Valor in texto: **{formato_cop(val_obj_v)}**")
        val_com_v = st.number_input("Comisión o Gastos de Publicación (COP)", value=300000, step=50000, format="%d")
        st.caption(f"Valor in texto: **{formato_cop(val_com_v)}**")

# =====================================================================
# MÓDULO 3: CONTRATO
# =====================================================================
elif modulo_seleccionado == "📜 Módulo CONTRATO":
    st.title("📜 Módulo de CONTRATO - Generador Legal de Compraventa")
    
    placa_para_contrato = st.session_state.get("placa_actual", "N/A")

    col_k1, col_k2 = st.columns(2)
    with col_k1:
        st.subheader("👤 Datos del Vendedor")
        st.text_input("Nombre Completo Vendedor")
        st.text_input("Cédula / NIT Vendedor")
    with col_k2:
        st.subheader("🚘 Datos del Vehículo y Transacción")
        placa_contrato_input = st.text_input("Placa del Vehículo", value=placa_para_contrato, placeholder="Ej: HCZ515")
        val_acordado_k = st.number_input("Valor Acordado de Compraventa (COP)", value=58000000, step=1000000, format="%d")
        st.caption(f"Valor in texto: **{formato_cop(val_acordado_k)}**")