import time
import streamlit as st
import anthropic
import base64
from pathlib import Path

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CAM · Aspire Cloud Knowledge Agent",
    page_icon="☁️",
    layout="centered",
)

# ── Load logo as base64 ──────────────────────────────────────────────────────
@st.cache_resource
def load_logo():
    logo_path = Path("assets/cam-logo.svg")
    if logo_path.exists():
        with open(logo_path, "r", encoding="utf-8") as f:
            svg = f.read()
        b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
        return f"data:image/svg+xml;base64,{b64}"
    return None

logo_data = load_logo()

# ── Custom styles ────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #003A49 0%, #0087B4 100%);
        color: white;
        padding: 1.75rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(0, 58, 73, 0.15);
    }
    .main-header-row { display: flex; align-items: center; gap: 1rem; }
    .main-header img { height: 48px; width: auto; flex-shrink: 0; }
    .main-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; line-height: 1.2; }
    .main-header p  { margin: 0.25rem 0 0; opacity: 0.85; font-size: 0.9rem; }

    .module-badge {
        display: inline-block;
        background: #FEC00D22;
        border: 1px solid #FEC00D;
        color: #FEC00D;
        border-radius: 20px;
        padding: 3px 12px;
        font-size: 0.75rem;
        margin: 2px;
        font-weight: 500;
    }
    .token-debug {
        background: #f0f8ff;
        border: 1px solid #00A3E0;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-size: 0.75rem;
        color: #003A49;
        margin-top: 0.5rem;
        font-family: monospace;
    }
    .suggestions-title { font-size: 0.85rem; color: #5F6B73; margin-bottom: 0.5rem; font-weight: 500; }

    div[data-testid="column"] .stButton button {
        background-color: #FFFFFF !important;
        color: #003A49 !important;
        border: 1px solid #00A3E0 !important;
        border-radius: 10px !important;
        font-weight: 500 !important;
        text-align: left !important;
        padding: 0.75rem 1rem !important;
        height: auto !important;
        white-space: normal !important;
        line-height: 1.4 !important;
        font-size: 0.85rem !important;
    }
    div[data-testid="column"] .stButton button:hover {
        background-color: #00A3E0 !important;
        color: white !important;
        border-color: #0087B4 !important;
    }
    #MainMenu { visibility: hidden; }
    footer    { visibility: hidden; }
    header    { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Access protection ────────────────────────────────────────────────────────
ACCESS_KEY = st.secrets.get("ACCESS_KEY", "")

if ACCESS_KEY:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        logo_html = f'<img src="{logo_data}" alt="CAM" />' if logo_data else '☁️'
        st.markdown(f"""
        <div class="main-header">
            <div class="main-header-row">
                {logo_html}
                <div>
                    <h1>Aspire Cloud Knowledge Agent</h1>
                    <p>Private access — authorized personnel only</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        key_input = st.text_input("Access key", type="password", placeholder="Enter your access key...")
        if st.button("Enter"):
            if key_input == ACCESS_KEY:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect key. Contact your administrator.")
        st.stop()

# ── Load markdown documents ──────────────────────────────────────────────────
@st.cache_resource
def load_knowledge_base():
    docs_path = Path("docs")
    knowledge = {}
    if not docs_path.exists():
        st.error("⚠️  'docs/' folder not found.")
        return {}
    for md_file in sorted(docs_path.glob("*.md")):
        with open(md_file, "r", encoding="utf-8") as f:
            knowledge[md_file.stem] = f.read()
    return knowledge


def build_system_prompt(knowledge: dict) -> list:
    if not knowledge:
        return [{"type": "text", "text": "You are a helpful assistant."}]

    company_context = knowledge.get("company-context", "")
    knowledge_docs  = {k: v for k, v in knowledge.items() if k != "company-context"}

    docs_section = "\n\n".join([
        f"## Document: {name}\n\n{content}"
        for name, content in knowledge_docs.items()
    ])

    company_section = ""
    if company_context:
        company_section = f"""
## COMPANY CONTEXT

{company_context}
"""

    instructions = """## YOUR ROLE

You are an expert assistant for **Aspire Cloud** (https://cloud.youraspire.com/).
You work for **CAM Property Services**.

## RESPONSE PRINCIPLES
- Plain, understandable language
- Short and direct — get to the point
- Numbered steps for processes
- Mention required permissions when relevant
- If you don't know: say so and direct to https://guide.youraspire.com/

## FORMATTING
- 2-3 items: prose  |  4+ items: bullets  |  comparisons: tables  |  processes: numbered steps
"""

    return [
        {
            "type": "text",
            "text": instructions,
        },
        {
            "type": "text",
            "text": f"{company_section}\n\n## ASPIRE CLOUD DOCUMENTATION\n\n{docs_section}",
            "cache_control": {"type": "ephemeral"},
        },
    ]


# ── Constants ────────────────────────────────────────────────────────────────
MODEL         = "claude-haiku-4-5-20251001"
MAX_TOKENS    = 2048
MAX_HISTORY   = 10
MAX_RETRIES   = 3
RETRY_BASE_DELAY = 2
DEBUG_TOKENS  = st.secrets.get("DEBUG_TOKENS", True)

SUGGESTED_QUESTIONS = [
    "How do I create a new work ticket?",
    "What's the difference between Contract and Work Order?",
    "How do I complete a work ticket?",
    "Explain Fixed Payment vs T&M invoice types",
]

# ── API call ─────────────────────────────────────────────────────────────────
def send_message(prompt: str, system_prompt: list):
    st.session_state.messages.append({"role": "user", "content": prompt})
    trimmed_messages = st.session_state.messages[-MAX_HISTORY:]
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

    for attempt in range(MAX_RETRIES):
        try:
            # Use standard messages.create with extra_headers to enable
            # prompt caching — compatible with all SDK versions >= 0.20
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=trimmed_messages,
                extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
            )

            response_text = response.content[0].text

            # Token usage logging
            usage         = response.usage
            cache_created = getattr(usage, "cache_creation_input_tokens", 0) or 0
            cache_read    = getattr(usage, "cache_read_input_tokens", 0) or 0
            input_tokens  = getattr(usage, "input_tokens", 0) or 0
            output_tokens = getattr(usage, "output_tokens", 0) or 0

            print(
                f"[TOKENS] input={input_tokens} | output={output_tokens} | "
                f"cache_created={cache_created} | cache_read={cache_read}"
            )

            st.session_state.last_token_usage = {
                "input": input_tokens,
                "output": output_tokens,
                "cache_created": cache_created,
                "cache_read": cache_read,
            }

            st.session_state.messages.append({"role": "assistant", "content": response_text})
            return

        except anthropic.RateLimitError:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                time.sleep(delay)
                continue
            st.session_state.messages.pop()
            st.session_state.error_message = (
                "⏳ The system is temporarily busy. Please wait a moment and try again."
            )

        except anthropic.AuthenticationError:
            st.session_state.messages.pop()
            st.session_state.error_message = (
                "🔑 Configuration issue. Please contact your administrator."
            )
            return

        except anthropic.APIConnectionError:
            st.session_state.messages.pop()
            st.session_state.error_message = (
                "🌐 Connection error. Please check your internet and try again."
            )
            return

        except anthropic.APIStatusError as e:
            st.session_state.messages.pop()
            if e.status_code == 529:
                st.session_state.error_message = (
                    "🔧 Service under maintenance. Please try again in a few minutes."
                )
            else:
                st.session_state.error_message = f"⚠️ API error {e.status_code}. Please try again."
            return

        except Exception as e:
            st.session_state.messages.pop()
            # Show the real error message to help diagnose
            st.session_state.error_message = f"⚠️ Unexpected error: {str(e)}"
            return


# ── Main UI ──────────────────────────────────────────────────────────────────
knowledge     = load_knowledge_base()
system_prompt = build_system_prompt(knowledge)

HIDDEN_FROM_BADGES = {"company-context", "knowledge-base", "custom-instructions"}
display_modules    = {k: v for k, v in knowledge.items() if k not in HIDDEN_FROM_BADGES}
modules_html = "".join([
    f'<span class="module-badge">{name}</span>'
    for name in display_modules.keys()
])
logo_html = f'<img src="{logo_data}" alt="CAM" />' if logo_data else ''

st.markdown(f"""
<div class="main-header">
    <div class="main-header-row">
        {logo_html}
        <div>
            <h1>Aspire Cloud Knowledge Agent</h1>
            <p>Ask anything about the Aspire Cloud modules</p>
        </div>
    </div>
    <div style="margin-top: 1rem">{modules_html}</div>
</div>
""", unsafe_allow_html=True)

if not knowledge:
    st.warning("Add your .md files to the `docs/` folder to activate the agent.")
    st.stop()

# ── Session state ────────────────────────────────────────────────────────────
if "messages"          not in st.session_state: st.session_state.messages          = []
if "error_message"     not in st.session_state: st.session_state.error_message     = None
if "pending_question"  not in st.session_state: st.session_state.pending_question  = None
if "last_token_usage"  not in st.session_state: st.session_state.last_token_usage  = None

# ── Suggested questions ──────────────────────────────────────────────────────
if not st.session_state.messages and not st.session_state.pending_question:
    st.markdown('<div class="suggestions-title">💡 Try asking:</div>', unsafe_allow_html=True)
    cols = st.columns(2)
    for i, question in enumerate(SUGGESTED_QUESTIONS):
        with cols[i % 2]:
            if st.button(question, key=f"suggest_{i}", use_container_width=True):
                st.session_state.pending_question = question
                st.rerun()

# ── Conversation history ─────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Token debug panel ────────────────────────────────────────────────────────
if DEBUG_TOKENS and st.session_state.last_token_usage:
    u = st.session_state.last_token_usage
    if u["cache_read"] > 0:
        cache_status = "✅ cache HIT"
    elif u["cache_created"] > 0:
        cache_status = "🔄 cache WRITTEN"
    else:
        cache_status = "❌ no cache"

    st.markdown(f"""
    <div class="token-debug">
        🔍 <b>Token usage</b> &nbsp;|&nbsp;
        input: {u['input']:,} &nbsp;|&nbsp;
        output: {u['output']:,} &nbsp;|&nbsp;
        cache_created: {u['cache_created']:,} &nbsp;|&nbsp;
        cache_read: {u['cache_read']:,} &nbsp;|&nbsp;
        {cache_status}
    </div>
    """, unsafe_allow_html=True)

# ── Error message ────────────────────────────────────────────────────────────
if st.session_state.error_message:
    st.warning(st.session_state.error_message)
    st.session_state.error_message = None

# ── Pending question ─────────────────────────────────────────────────────────
if st.session_state.pending_question:
    prompt = st.session_state.pending_question
    st.session_state.pending_question = None

    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Checking documentation..."):
            send_message(prompt, system_prompt)
    st.rerun()

# ── Chat input ───────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about any Aspire Cloud module..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Checking documentation..."):
            send_message(prompt, system_prompt)
    st.rerun()

# ── Clear button ─────────────────────────────────────────────────────────────
if st.session_state.messages:
    if st.button("🗑️  New conversation"):
        st.session_state.messages = []
        st.session_state.last_token_usage = None
        st.rerun()
