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

# ── Load logo as base64 (so it embeds in HTML) ──────────────────────────────
@st.cache_resource
def load_logo():
    """Load the CAM logo SVG and encode it for inline HTML embedding."""
    logo_path = Path("assets/cam-logo.svg")
    if logo_path.exists():
        with open(logo_path, "r", encoding="utf-8") as f:
            svg = f.read()
        b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
        return f"data:image/svg+xml;base64,{b64}"
    return None

logo_data = load_logo()

# ── Custom styles with company palette ───────────────────────────────────────
st.markdown("""
<style>
    :root {
        --primary:   #003A49;
        --accent:    #00A3E0;
        --accent2:   #0087B4;
        --highlight: #FEC00D;
        --neutral:   #B3B3B3;
    }

    .main-header {
        background: linear-gradient(135deg, #003A49 0%, #0087B4 100%);
        color: white;
        padding: 1.75rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(0, 58, 73, 0.15);
    }
    .main-header-row {
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    .main-header img {
        height: 48px;
        width: auto;
        flex-shrink: 0;
    }
    .main-header h1 {
        margin: 0;
        font-size: 1.5rem;
        font-weight: 700;
        line-height: 1.2;
    }
    .main-header p {
        margin: 0.25rem 0 0;
        opacity: 0.85;
        font-size: 0.9rem;
    }

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

    /* Suggested question buttons */
    .suggestions-container {
        margin: 1rem 0 1.5rem;
    }
    .suggestions-title {
        font-size: 0.85rem;
        color: #5F6B73;
        margin-bottom: 0.5rem;
        font-weight: 500;
    }

    /* Streamlit button override for suggestions */
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
        transition: all 0.2s ease !important;
    }
    div[data-testid="column"] .stButton button:hover {
        background-color: #00A3E0 !important;
        color: white !important;
        border-color: #0087B4 !important;
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0, 163, 224, 0.25);
    }

    /* Default Streamlit button (Enter, New conversation) */
    .stButton button[kind="primary"],
    .stButton button[kind="secondary"] {
        background-color: #00A3E0;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }
    .stButton button[kind="primary"]:hover,
    .stButton button[kind="secondary"]:hover {
        background-color: #0087B4;
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
    """Load all .md files from the docs/ folder on startup."""
    docs_path = Path("docs")
    knowledge = {}

    if not docs_path.exists():
        st.error("⚠️  'docs/' folder not found. Make sure to include your .md files.")
        return {}

    for md_file in sorted(docs_path.glob("*.md")):
        with open(md_file, "r", encoding="utf-8") as f:
            knowledge[md_file.stem] = f.read()

    return knowledge


def build_system_prompt(knowledge: dict) -> list:
    """
    Build the system prompt as a list of content blocks with prompt caching.

    The knowledge base (large, static text) is marked with cache_control so
    Anthropic caches it after the first call. Subsequent calls in the same
    session reuse the cache and consume almost no input TPM, which is the
    primary fix for the rate limit errors.
    """
    if not knowledge:
        return [{"type": "text", "text": "You are a helpful assistant."}]

    company_context = knowledge.get("company-context", "")
    knowledge_docs = {k: v for k, v in knowledge.items() if k != "company-context"}

    docs_section = "\n\n".join([
        f"## Document: {name}\n\n{content}"
        for name, content in knowledge_docs.items()
    ])

    company_section = ""
    if company_context:
        company_section = f"""
## COMPANY CONTEXT

The following is context about the company using this system. Use it to provide
relevant, accurate examples specific to the company's actual business operations
when answering questions about Aspire Cloud.

{company_context}
"""

    instructions = """## YOUR ROLE

You are an expert assistant for **Aspire Cloud** (https://cloud.youraspire.com/),
a management system for landscaping and maintenance companies. Your goal is to help
users understand and use the system effectively.

You work for **CAM Property Services** and your answers should be relevant to their
operations when applicable.

---

## RESPONSE PRINCIPLES

### 1. Clarity Over Technical Jargon
- Use plain and understandable language
- Avoid unnecessary technical jargon
- If you use a technical term, explain it briefly
- Think of your audience as: managers, estimators, salespeople, administrators

### 2. Conciseness
- Short and direct responses
- Get straight to the point
- Don't give unnecessary information
- If the question is simple, the answer should be simple

### 3. Actionable Steps
- When explaining processes, use clear numbered steps
- Include prerequisites if any
- Mention required permissions when relevant

### 4. Honesty About Limitations
If you don't know the answer or it's not in your knowledge base:
- Say it clearly: "I don't have information about that in my knowledge base"
- DON'T make up answers
- Suggest alternatives: recommend checking https://guide.youraspire.com/

---

## RESPONSE FORMATTING

- Short lists (2-3 items): write inline as prose
- Longer lists (4+ items): use bullets
- Comparisons: use tables
- Processes: use numbered steps
- Keep responses as short as the question allows

---

## SPECIAL SITUATIONS

- Outside scope: direct to https://guide.youraspire.com/
- Admin config needed: mention System Administrator permissions required
- Confusing two concepts: clarify the difference explicitly

---

## TONE AND STYLE

Professional but accessible. Patient. Focus on what CAN be done.
After every response ask yourself: does the user know exactly what to do next?
"""

    # Two content blocks:
    # 1. Instructions (smaller, not cached — may change more often)
    # 2. Knowledge base docs + company context (large, static — CACHED)
    return [
        {
            "type": "text",
            "text": instructions,
        },
        {
            "type": "text",
            "text": f"{company_section}\n\n## ASPIRE CLOUD DOCUMENTATION\n\n{docs_section}",
            # cache_control tells Anthropic to cache everything up to this point.
            # Cached tokens don't count against the input TPM limit, which is
            # the root cause of the RateLimitErrors with the Free Tier 10K TPM cap.
            "cache_control": {"type": "ephemeral"},
        },
    ]


# ── Constants ────────────────────────────────────────────────────────────────

# Haiku has higher TPM limits than Sonnet on Tier 1 (50K vs 30K input TPM)
# and is more cost-efficient for short knowledge agent responses.
MODEL = "claude-haiku-4-5-20251001"

# 2048 avoids truncated responses. You only pay for tokens actually generated,
# so raising this limit doesn't increase cost when answers are short.
MAX_TOKENS = 2048

# Keep only the last N messages in the conversation history sent to the API.
# Older turns are dropped to prevent token accumulation across long sessions.
# 10 messages = 5 back-and-forth exchanges, enough context for follow-ups.
MAX_HISTORY = 10

# Retry settings for transient rate limit errors.
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # seconds; doubles each attempt (2 → 4 → 8)


# ── Suggested questions ───────────────────────────────────────────────────────
SUGGESTED_QUESTIONS = [
    "How do I create a new work ticket?",
    "What's the difference between Contract and Work Order?",
    "How do I complete a work ticket?",
    "Explain Fixed Payment vs T&M invoice types",
]


# ── API call with retry + exponential backoff ────────────────────────────────
def send_message(prompt: str, system_prompt: list):
    """
    Send a message to Claude with:
    - Prompt caching on the system prompt (via content blocks built above)
    - Conversation history limited to MAX_HISTORY messages
    - Retry with exponential backoff on rate limit errors
    """
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Trim history before sending: keep only the most recent MAX_HISTORY messages.
    # This prevents token accumulation across long sessions while preserving
    # enough context for follow-up questions.
    trimmed_messages = st.session_state.messages[-MAX_HISTORY:]

    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

    for attempt in range(MAX_RETRIES):
        try:
            with client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=trimmed_messages,
            ) as stream:
                response_text = ""
                for text in stream.text_stream:
                    response_text += text

            st.session_state.messages.append({"role": "assistant", "content": response_text})
            return  # success — exit the retry loop

        except anthropic.RateLimitError:
            if attempt < MAX_RETRIES - 1:
                # Exponential backoff: wait 2s, then 4s, then 8s before retrying.
                # The spinner stays visible so the user knows the app is working.
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                time.sleep(delay)
                continue
            # All retries exhausted
            st.session_state.messages.pop()
            st.session_state.error_message = (
                "⏳ The system is temporarily busy. Please wait a moment and try again."
            )

        except anthropic.AuthenticationError:
            st.session_state.messages.pop()
            st.session_state.error_message = (
                "🔑 There's a configuration issue. Please contact your administrator."
            )
            return

        except anthropic.APIConnectionError:
            st.session_state.messages.pop()
            st.session_state.error_message = (
                "🌐 Couldn't connect to the server. Please check your internet connection and try again."
            )
            return

        except anthropic.APIStatusError as e:
            st.session_state.messages.pop()
            if e.status_code == 529:
                st.session_state.error_message = (
                    "🔧 The service is temporarily undergoing maintenance. Please try again in a few minutes."
                )
            else:
                st.session_state.error_message = (
                    "⚠️ Something unexpected happened. Please try again."
                )
            return

        except Exception:
            st.session_state.messages.pop()
            st.session_state.error_message = (
                "⚠️ Something unexpected happened. Please try again. "
                "If the issue persists, contact your administrator."
            )
            return


# ── Main UI ──────────────────────────────────────────────────────────────────
knowledge = load_knowledge_base()
system_prompt = build_system_prompt(knowledge)

# Header with logo + module badges
HIDDEN_FROM_BADGES = {"company-context", "knowledge-base", "custom-instructions"}
display_modules = {k: v for k, v in knowledge.items() if k not in HIDDEN_FROM_BADGES}
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

# ── Initialize session state ─────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "error_message" not in st.session_state:
    st.session_state.error_message = None
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

# ── Suggested questions (only show when no conversation yet) ─────────────────
if not st.session_state.messages and not st.session_state.pending_question:
    st.markdown('<div class="suggestions-title">💡 Try asking:</div>', unsafe_allow_html=True)
    cols = st.columns(2)
    for i, question in enumerate(SUGGESTED_QUESTIONS):
        with cols[i % 2]:
            if st.button(question, key=f"suggest_{i}", use_container_width=True):
                st.session_state.pending_question = question
                st.rerun()

# ── Show error message if any ────────────────────────────────────────────────
if st.session_state.error_message:
    st.warning(st.session_state.error_message)
    st.session_state.error_message = None

# ── Conversation history ─────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Process pending question from suggestion button ──────────────────────────
if st.session_state.pending_question:
    prompt = st.session_state.pending_question
    st.session_state.pending_question = None

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Checking documentation..."):
            send_message(prompt, system_prompt)
    st.rerun()

# ── User text input ──────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about any Aspire Cloud module..."):
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Checking documentation..."):
            send_message(prompt, system_prompt)
    st.rerun()

# ── Clear conversation button ────────────────────────────────────────────────
if st.session_state.messages:
    if st.button("🗑️  New conversation"):
        st.session_state.messages = []
        st.rerun()
