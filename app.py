import streamlit as st
import anthropic
import os
from pathlib import Path

# ── Configuración de página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="CloudYourAspire · Asistente ERP",
    page_icon="☁️",
    layout="centered",
)

# ── Estilos personalizados con paleta de tu empresa ──────────────────────────
st.markdown("""
<style>
    /* Colores corporativos */
    :root {
        --primary:   #003A49;
        --accent:    #00A3E0;
        --accent2:   #0087B4;
        --highlight: #FEC00D;
        --neutral:   #B3B3B3;
    }

    /* Header superior */
    .main-header {
        background: linear-gradient(135deg, #003A49 0%, #0087B4 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    .main-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; }
    .main-header p  { margin: 0.25rem 0 0; opacity: 0.8; font-size: 0.9rem; }

    /* Badge de módulos disponibles */
    .module-badge {
        display: inline-block;
        background: #FEC00D22;
        border: 1px solid #FEC00D;
        color: #FEC00D;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.75rem;
        margin: 2px;
    }

    /* Ocultar elementos default de Streamlit */
    #MainMenu { visibility: hidden; }
    footer     { visibility: hidden; }
    header     { visibility: hidden; }

    /* Botón de enviar */
    .stButton button {
        background-color: #00A3E0;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }
    .stButton button:hover { background-color: #0087B4; }
</style>
""", unsafe_allow_html=True)


# ── Protección por clave de acceso ───────────────────────────────────────────
ACCESS_KEY = st.secrets.get("ACCESS_KEY", "")

if ACCESS_KEY:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.markdown("""
        <div class="main-header">
            <h1>☁️ CloudYourAspire · Asistente ERP</h1>
            <p>Acceso privado — solo personal autorizado</p>
        </div>
        """, unsafe_allow_html=True)

        clave = st.text_input("Clave de acceso", type="password", placeholder="Ingresa la clave...")
        if st.button("Entrar"):
            if clave == ACCESS_KEY:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Clave incorrecta. Contacta al administrador.")
        st.stop()


# ── Carga de documentos markdown ─────────────────────────────────────────────
@st.cache_resource
def load_knowledge_base():
    """Carga todos los archivos .md de la carpeta docs/ al iniciar la app."""
    docs_path = Path("docs")
    knowledge = {}

    if not docs_path.exists():
        st.error("⚠️  Carpeta 'docs/' no encontrada. Asegúrate de incluir tus archivos .md.")
        return {}

    for md_file in sorted(docs_path.glob("*.md")):
        with open(md_file, "r", encoding="utf-8") as f:
            knowledge[md_file.stem] = f.read()

    return knowledge


def build_system_prompt(knowledge: dict) -> str:
    """Construye el system prompt con todos los documentos de contexto."""
    if not knowledge:
        return "Eres un asistente útil."

    modulos = "\n\n".join([
        f"## Módulo: {nombre}\n\n{contenido}"
        for nombre, contenido in knowledge.items()
    ])

    return f"""Eres el asistente experto del ERP CloudYourAspire. \
Tu función es responder preguntas sobre los módulos del sistema de forma clara, \
precisa y útil para el equipo interno.

INSTRUCCIONES:
- Responde SOLO basándote en la documentación proporcionada.
- Si la respuesta no está en los documentos, dilo claramente: \
"No encuentro esa información en la documentación disponible."
- Usa un tono profesional pero amigable.
- Cuando sea útil, estructura tu respuesta con puntos o pasos numerados.
- Si la pregunta menciona un módulo específico, enfócate en ese módulo.

DOCUMENTACIÓN DEL ERP CLOUDYOURASPIRE:
{modulos}
"""


# ── UI principal ──────────────────────────────────────────────────────────────
knowledge = load_knowledge_base()
system_prompt = build_system_prompt(knowledge)

# Header
modulos_html = "".join([
    f'<span class="module-badge">{nombre}</span>'
    for nombre in knowledge.keys()
])
st.markdown(f"""
<div class="main-header">
    <h1>☁️ CloudYourAspire · Asistente ERP</h1>
    <p>Consulta cualquier duda sobre los módulos del sistema</p>
    <div style="margin-top: 0.75rem">{modulos_html}</div>
</div>
""", unsafe_allow_html=True)

if not knowledge:
    st.warning("Agrega tus archivos .md en la carpeta `docs/` para activar el asistente.")
    st.stop()

# ── Historial de conversación ─────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar historial
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Input del usuario ─────────────────────────────────────────────────────────
if prompt := st.chat_input("Pregunta sobre cualquier módulo de CloudYourAspire..."):

    # Mostrar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Llamar a la API de Claude con streaming
    with st.chat_message("assistant"):
        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

        with st.spinner("Consultando documentación..."):
            with client.messages.stream(
                model="claude-haiku-4-5-20251001",   # económico; cambia a claude-sonnet-4-6 para más calidad
                max_tokens=1024,
                system=system_prompt,
                messages=st.session_state.messages,
            ) as stream:
                response_text = st.write_stream(stream.text_stream)

    st.session_state.messages.append({"role": "assistant", "content": response_text})

# ── Botón para limpiar conversación ──────────────────────────────────────────
if st.session_state.messages:
    if st.button("🗑️  Nueva conversación", use_container_width=False):
        st.session_state.messages = []
        st.rerun()
