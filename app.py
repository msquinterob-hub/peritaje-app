import os
import re
import time
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import streamlit as st
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
api_key_openai_guardada = os.getenv("OPENAI_API_KEY", "")

api_key = st.sidebar.text_input(
    "Llave de API de Google Gemini", 
    value=api_key_gemini_guardada,
    type="password", 
    help="Principal (Google AI Studio)"
)

api_key_openai = st.sidebar.text_input(
    "Llave de API de OpenAI (ChatGPT - Respaldo)", 
    value=api_key_openai_guardada,
    type="password", 
    help="Opcional: Respaldo automático"
)

if api_key:
    st.sidebar.success("🔑 Gemini API cargada")
if api_key_openai:
    st.sidebar.success("🔑 OpenAI API cargada")

# ==========================================
# FUNCIONES DE SCRAPING Y EXTRACCIÓN EN CASCADA
# ==========================================
def limpiar_url_mercadolibre(raw_url):
    """Limpia anclas y parámetros pesados de la URL para evitar bloqueos"""
    clean = raw_url.split("#")[0]
    return clean

def extraer_publicacion_y_fotos(url):
    url_limpia = limpiar_url_mercadolibre(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-CO,es-419;q=0.9,es;q=0.8"
    }
    try:
        response = requests.get(url_limpia, headers=headers, timeout=15)
        if response.status_code != 200:
            return None, None, [], "N/A", f"No se pudo acceder a la página (Código HTTP {response.status_code})."

        html = response.text
        soup = BeautifulSoup(html, "html.parser")

        # 1. Título
        titulo = ""
        if soup.find("h1", class_="ui-pdp-title"):
            titulo = soup.find("h1", class_="ui-pdp-title").get_text(strip=True)
        elif soup.find("h1"):
            titulo = soup.find("h1").get_text(strip=True)
        elif soup.title:
            titulo = soup.title.get_text(strip=True)

        # 2. Precio
        precio = None
        precio_span = soup.find("span", class_="andes-money-amount__fraction")
        if precio_span:
            precio_texto = re.sub(r"[^\d]", "", precio_span.text.strip())
            if precio_texto:
                precio = int(precio_texto)
        
        if not precio:
            precios_encontrados = re.findall(r"\$\s*(\d{1,3}(?:\.\d{3}){2,3}|\d{7,9})", html)
            for p_raw in precios_encontrados:
                val = int(p_raw.replace(".", ""))
                if val >= 5000000:
                    precio = val
                    break

        # 3. Placa en el texto del anuncio
        placa_detectada = "N/A"
        patron_placa = r'\b([A-Za-z]{3}\s*-?\s*\d{3})\b'
        texto_busqueda = titulo
        ficha_tech = soup.find("table", class_="andino-specs-table") or soup.find("div", class_="ui-pdp-description")
        if ficha_tech:
            texto_busqueda += " " + ficha_tech.get_text()

        match_placa = re.search(patron_placa, texto_busqueda)
        if match_placa:
            cand = match_placa.group(1).upper().replace("-", "").replace(" ", "")
            if not any(bad in cand for bad in ["BMW", "AUD", "CHEV", "RENA", "NISS", "COP"]):
                placa_detectada = cand

        # 4. Extracción de Galería de Fotos (Imágenes de alta resolución)
        ids_imagenes_unicos = []
        fotos_candidatas = []
        patron_ml = r'https://http2\.mlstatic\.com/D_NQ_NP_([0-9A-Za-z_-]+)\.(?:jpg|jpeg|png|webp)'
        palabras_basura = ["meli", "logo", "banner", "icon", "cashback", "garantia", "credito", "publicidad", "financiacion"]

        # Buscar IDs de MercadoLibre en todo el código HTML
        coincidencias = re.findall(patron_ml, html)

        for img_id in coincidencias:
            clean_id = re.sub(r'^(?:2X_|3X_|\d+X_)', '', img_id)
            clean_id = re.sub(r'-[OIVFDS]$', '', clean_id)
            if any(bad in clean_id.lower() for bad in palabras_basura):
                continue
            if clean_id not in ids_imagenes_unicos:
                ids_imagenes_unicos.append(clean_id)
                url_hd = f"https://http2.mlstatic.com/D_NQ_NP_{clean_id}-O.jpg"
                if url_hd not in fotos_candidatas:
                    fotos_candidatas.append(url_hd)

        # Respaldo con etiquetas img / og:image
        if not fotos_candidatas:
            for meta in soup.find_all("meta", property="og:image"):
                src = meta.get("content")
                if src and "mlstatic.com" in src:
                    src_hd = re.sub(r"-[I|V|D|F]\.jpg", "-O.jpg", src)
                    if src_hd not in fotos_candidatas:
                        fotos_candidatas.append(src_hd)

        fotos_representativas = []
        total_cand = len(fotos_candidatas)
        if total_cand <= 5:
            fotos_representativas = fotos_candidatas
        else:
            indices = [0, int(total_cand * 0.25), int(total_cand * 0.50), int(total_cand * 0.75), total_cand - 1]
            for idx in indices:
                url_sel = fotos_candidatas[idx]
                if url_sel not in fotos_representativas:
                    fotos_representativas.append(url_sel)

        return titulo, precio, fotos_representativas, placa_detectada, None

    except Exception as e:
        return None, None, [], "N/A", f"Error al procesar la URL: {str(e)}"

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
        "prompt": "Eres perito en vehículos en Colombia. 1. PLACA DETECTADA: [Identifica obligatoriamente la placa visible en las fotos en formato de 3 letras y 3 números, ej: HCZ515, o N/A]. 2. Exterior. 3. Interior. 4. Puntos Fuertes. 5. Puntos de Negociación. 6. Cálculo Estimado de Arreglos (COP).",
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

def analizar_con_openai(imagenes_pil, key_openai):
    import base64
    clean_key = key_openai.strip()
    if clean_key.startswith("k-"):
        clean_key = "s" + clean_key

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {clean_key}"
    }
    
    content_payload = [{
        "type": "text",
        "text": "Eres un perito experto en autos usados en Colombia.\n1. **PLACA DETECTADA:** Analiza detalladamente las fotos de las placas y escribe exactamente el código detectado (3 letras y 3 números, ej: HCZ515) o N/A si no se ve.\n2. **Exterior:** Estado de pintura.\n3. **Interior:** Estado general.\n4. **Puntos Fuertes:** Ventajas.\n5. **Puntos de Negociación:** Imperfecciones.\n6. **Cálculo Estimado de Arreglos (COP):** Número exacto en pesos (ej: 850000)."
    }]
    
    for img in imagenes_pil[:5]:
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=75)
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        content_payload.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}
        })

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": content_payload}],
        "max_tokens": 600
    }

    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=25)
        if response.status_code == 200:
            res_json = response.json()
            return f"🤖 [Dictamen generado por ChatGPT / OpenAI de Respaldo]:\n\n" + res_json["choices"][0]["message"]["content"], None
        else:
            return None, f"OpenAI API HTTP {response.status_code}: {response.text}"
    except Exception as e:
        return None, f"OpenAI Error: {str(e)}"

def analizar_imagenes_con_ia(imagenes_pil, key_gemini, key_openai, activar_local):
    imgs_optimizadas = [optimizar_imagen_para_ia(img) for img in imagenes_pil[:5]]
    
    prompt = """
    Eres perito experto en autos usados en Colombia. Analiza minuciosamente las imágenes adjuntas (hasta 5 fotos):
    1. **PLACA DETECTADA:** Observa las placas físicas en la carrocería (delantera o trasera). Indica claramente la placa encontrada (3 letras y 3 números unidos, ej: HCZ515) o N/A si ninguna es visible.
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

            for intento in range(2):
                try:
                    response = client.models.generate_content(
                        model='gemini-3.8-flash', 
                        contents=partes_contenido
                    )
                    if response and response.text:
                        return f"🤖 [Dictamen generado por Google Gemini (gemini-3.8-flash)]:\n\n" + response.text
                except Exception as e_mod:
                    err_msg = str(e_mod)
                    if "503" in err_msg and intento == 0:
                        time.sleep(2)
                        continue
                    errores_proceso.append(f"Gemini (gemini-3.8-flash): {err_msg}")
                    break

        except Exception as e_genai:
            errores_proceso.append(f"Gemini Init Error: {str(e_genai)}")

    if key_openai:
        res_openai, err_openai = analizar_con_openai(imagenes_pil, key_openai)
        if res_openai:
            return f"⚠️ *Nota: Google Gemini estuvo inaccesible o saturado temporalmente. Se utilizó automáticamente OpenAI (ChatGPT) de respaldo.*\n\n" + res_openai
        if err_openai:
            errores_proceso.append(err_openai)

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
        with st.spinner("Cargando y analizando fotos de la publicación..."):
            titulo_vehiculo, precio_publicado, fotos_encontradas, placa_extraida, error = extraer_publicacion_y_fotos(url_input)
            if error:
                st.error(error)
            else:
                txt_titulo = titulo_vehiculo if titulo_vehiculo else "Mercado Libre"
                st.success(f"✅ **Vehículo identificado:** {txt_titulo}")
                if precio_publicado:
                    st.info(f"💵 **Precio en la publicación:** {formato_cop(precio_publicado)} PESOS")
                
                if "url_anterior" not in st.session_state or st.session_state.get("url_anterior") != url_input:
                    if placa_extraida and placa_extraida != "N/A":
                        st.session_state["placa_actual"] = placa_extraida
                    st.session_state["url_anterior"] = url_input

    st.markdown("---")

    tab_comercial, tab_ia, tab_docs, tab_legales = st.tabs([
        "📈 Análisis Comercial de Mercado",
        "👁️ Inspección de Fotos (IA / Manual)",
        "📄 Documentos y Calculadora de Oferta",
        "⚖️ Enlaces Legales Oficiales"
    ])

    # TAB 1: ANÁLISIS COMERCIAL
    with tab_comercial:
        st.header("📈 Análisis Comercial y Estimación de Reventa")

        col_m1, col_m2 = st.columns(2)
        val_inicial = precio_publicado if precio_publicado else 59000000

        with col_m1:
            precio_publicado_input = st.number_input("Precio de la Publicación Analizada (PESOS)", value=int(val_inicial), step=1000000, format="%d")
            st.caption(f"Valor en texto: **{formato_cop(precio_publicado_input)}**")
            
            ref_min = st.number_input("Precio Mínimo de Mercado para este modelo (PESOS)", value=int(val_inicial * 0.9), step=1000000, format="%d")
            st.caption(f"Valor en texto: **{formato_cop(ref_min)}**")
            
            ref_max = st.number_input("Precio Máximo de Mercado para este modelo (PESOS)", value=int(val_inicial * 1.1), step=1000000, format="%d")
            st.caption(f"Valor en texto: **{formato_cop(ref_max)}**")

        with col_m2:
            precio_promedio_mercado = (ref_min + ref_max) / 2
            st.metric(label="📊 Precio Promedio de Mercado", value=f"{formato_cop(precio_promedio_mercado)} PESOS")

            diferencia = precio_publicado_input - precio_promedio_mercado
            if diferencia > 0:
                st.warning(f"⚠️ La publicación está **{formato_cop(diferencia)} PESOS por encima** del precio promedio de mercado.")
            else:
                st.success(f"🎉 La publicación está **{formato_cop(abs(diferencia))} PESOS por debajo** del precio promedio de mercado (Posible Oportunidad).")

    # TAB 2: INSPECCIÓN IA
    with tab_ia:
        st.header("👁️ Inspección Visual y Registro de Peritaje")
        
        imgs_pil_list = []

        # Mostrar exactamente las 5 fotos principales en 5 columnas paralelas (como la versión original)
        if fotos_encontradas:
            cols = st.columns(min(len(fotos_encontradas), 5))
            for j, img_url in enumerate(fotos_encontradas[:5]):
                with cols[j]:
                    st.image(img_url, use_container_width=True, caption=f"Foto {j + 1}")
            
            # Cargar imágenes a memoria PIL para la IA
            for url_f in fotos_encontradas[:5]:
                try:
                    res_f = requests.get(url_f, timeout=8)
                    if res_f.status_code == 200:
                        imgs_pil_list.append(Image.open(BytesIO(res_f.content)))
                except Exception:
                    pass

        # Carga opcional manual si no hay fotos o se quieren añadir más
        archivos_cargados = st.file_uploader(
            "Cargar o tomar fotos desde el dispositivo (Opcional):", 
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
            if imgs_pil_list:
                with st.spinner("Generando dictamen pericial con Inteligencia Artificial..."):
                    resultado_ia = analizar_imagenes_con_ia(imgs_pil_list, api_key, api_key_openai, usar_ia_local)
                    if resultado_ia:
                        st.session_state["dictamen_peritaje"] = resultado_ia
                        
                        placa_detectada_ia = extraer_placa_de_dictamen(resultado_ia)
                        if placa_detectada_ia and placa_detectada_ia != "N/A":
                            st.session_state["placa_actual"] = placa_detectada_ia

                        costo_extraido = extraer_monto_arreglos_de_dictamen(resultado_ia)
                        st.session_state["costo_arreglos_estimado"] = costo_extraido
            else:
                st.error("⚠️ Ingrese un enlace con fotos o cargue imágenes manualmente para iniciar el análisis.")

        st.markdown("---")
        st.subheader("📝 Dictamen del Peritaje (Editable / Manual)")
        
        dictamen_defecto = st.session_state.get("dictamen_peritaje", "• Carrocería: Sin detalles graves de pintura visibles.\n• Interior: Cojinería y tablero en aceptable estado.\n• Mecánica/Llantas: Requiere revisión técnica presencial.\n\n4. **Puntos Fuertes:** Buena conservación estética exterior e interior.\n5. **Puntos de Negociación:** Raspones leves o desgaste visible.\n6. **Cálculo Estimado de Arreglos (COP):** 800000")
        
        observaciones_manuales = st.text_area(
            "Escribe o ajusta las observaciones del estado del vehículo:", 
            value=dictamen_defecto, 
            height=200
        )
        st.info("💡 Este dictamen te sirve de soporte para la negociación con el vendedor.")

    # TAB 3: CALCULADORA
    with tab_docs:
        st.header("📄 Calculadora Financiera y Gastos de Traspaso")

        col_f1, col_f