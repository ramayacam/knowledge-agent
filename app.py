import streamlit as st
import anthropic
from pathlib import Path

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CAM · Aspire Cloud Knowledge Agent",
    page_icon="☁️",
    layout="centered",
)

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
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    .main-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; }
    .main-header p  { margin: 0.25rem 0 0; opacity: 0.8; font-size: 0.9rem; }

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

    #MainMenu { visibility: hidden; }
    footer     { visibility: hidden; }
    header     { visibility: hidden; }

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


# ── Access protection ────────────────────────────────────────────────────────
ACCESS_KEY = st.secrets.get("ACCESS_KEY", "")

if ACCESS_KEY:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.markdown("""
        <div class="main-header">
            <h1>☁️ CAM · Aspire Cloud Knowledge Agent</h1>
            <p>Private access — authorized personnel only</p>
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


def build_system_prompt(knowledge: dict) -> str:
    """Build the system prompt with all context documents and agent instructions."""
    if not knowledge:
        return "You are a helpful assistant."

    # Separate company context from knowledge documents
    company_context = knowledge.get("company-context", "")
    knowledge_docs = {k: v for k, v in knowledge.items() if k != "company-context"}

    # Build the documentation section
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

    return f"""## YOUR ROLE

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
- Suggest alternatives: "What I can tell you is..." or "I recommend checking the official documentation at https://guide.youraspire.com/"

---

## KNOWLEDGE BASE STRUCTURE

Your knowledge is organized in these documents:

### knowledge-base.md
The master index. Consult it when:
- You need to understand system hierarchy
- You don't know which module to look in
- You want a quick overview

### invoices-module.md (Work Tickets)
Everything about work tickets. Consult it when asked about:
- Ticket statuses (Open, Scheduled, Complete, etc.)
- Completing or cancelling tickets
- Bulk actions
- Dynamic Forecasting
- Multi-year contracts

### opportunities-module.md
Everything about opportunities. Consult it when asked about:
- Creating opportunities
- Opportunity types (Contracts vs Work Orders)
- Invoice types (Fixed Payment, Per Service, T&M, etc.)
- Creating estimates
- Payment schedules
- Change orders
- Contract renewals
- Job Dashboard

---

## COMMON QUESTION PATTERNS

### "How do I do X?"
1. Identify relevant module
2. Find specific process
3. Respond with clear steps
4. Mention permissions if applicable

### "What is X?"
1. Define in simple language
2. Give practical example
3. Explain when it's used

### "What's the difference between X and Y?"
1. Define both terms
2. Create comparison table
3. Give examples of when to use each

### "Why can't I do X?"
1. Identify possible causes (missing permission, wrong status, system restriction)
2. Explain the cause
3. Give solution or alternative

---

## RESPONSE FORMATTING

**For short lists (2-3 items):** Write in prose.
**For longer lists (4+ items):** Use bullets.
**For comparisons:** Use tables.
**For processes:** Use numbered steps.

---

## CONTEXT HANDLING

- Maintain conversation context across follow-up questions
- Connect with what you already explained
- Don't repeat everything from scratch
- If context isn't clear, ask for clarification

---

## SPECIAL SITUATIONS

### When Asked About Other Modules
"My knowledge focuses on the Work Tickets and Opportunities modules. For [topic X], 
I recommend checking the official documentation at https://guide.youraspire.com/ 
or contacting Aspire support."

### When Asked About Advanced Configuration
"That configuration is done in Administration > [section]. For Administration changes, 
you need System Administrator permissions. I recommend working with your system 
administrator or checking: https://guide.youraspire.com/"

### When You Identify Common Confusion
"It seems you're confusing [X] with [Y]. Let me clarify..."

---

## TONE AND STYLE

- Professional but accessible: like a helpful colleague, not a robot
- Patient: the same questions may be asked multiple times
- Positive: focus on what CAN be done
- Empathetic: acknowledge when something is confusing or complicated

---

## REMEMBER

Your goal is to empower the user to use Aspire effectively. It's not about showing 
how much you know, but about making them understand and be able to act.

Guiding question: After reading my response, does the user know exactly what to do?

---

{company_section}

## ASPIRE CLOUD DOCUMENTATION

{docs_section}
"""


# ── Main UI ──────────────────────────────────────────────────────────────────
knowledge = load_knowledge_base()
system_prompt = build_system_prompt(knowledge)

# Header with module badges (exclude support files from display)
HIDDEN_FROM_BADGES = {"company-context", "knowledge-base", "custom-instructions"}
display_modules = {k: v for k, v in knowledge.items() if k not in HIDDEN_FROM_BADGES}
modules_html = "".join([
    f'<span class="module-badge">{name}</span>'
    for name in display_modules.keys()
])
st.markdown(f"""
<div class="main-header">
    <h1>☁️ CAM · Aspire Cloud Knowledge Agent</h1>
    <p>Ask anything about the Aspire Cloud modules</p>
    <div style="margin-top: 0.75rem">{modules_html}</div>
</div>
""", unsafe_allow_html=True)

if not knowledge:
    st.warning("Add your .md files to the `docs/` folder to activate the agent.")
    st.stop()

# ── Conversation history ─────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── User input ───────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about any Aspire Cloud module..."):

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

        try:
            with st.spinner("Checking documentation..."):
                with client.messages.stream(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=1024,
                    system=system_prompt,
                    messages=st.session_state.messages,
                ) as stream:
                    response_text = st.write_stream(stream.text_stream)

            st.session_state.messages.append({"role": "assistant", "content": response_text})

        except anthropic.RateLimitError:
            response_text = "⏳ The system is temporarily busy. Please wait a moment and try again."
            st.warning(response_text)
            st.session_state.messages.pop()  # Remove the user message so they can retry

        except anthropic.AuthenticationError:
            response_text = "🔑 There's a configuration issue. Please contact your administrator."
            st.error(response_text)
            st.session_state.messages.pop()

        except anthropic.APIConnectionError:
            response_text = "🌐 Couldn't connect to the server. Please check your internet connection and try again."
            st.warning(response_text)
            st.session_state.messages.pop()

        except anthropic.APIStatusError as e:
            if e.status_code == 529:
                response_text = "🔧 The service is temporarily undergoing maintenance. Please try again in a few minutes."
            else:
                response_text = "⚠️ Something unexpected happened. Please try again. If the issue persists, contact your administrator."
            st.warning(response_text)
            st.session_state.messages.pop()

        except Exception:
            response_text = "⚠️ Something unexpected happened. Please try again. If the issue persists, contact your administrator."
            st.warning(response_text)
            st.session_state.messages.pop()

# ── Clear conversation button ────────────────────────────────────────────────
if st.session_state.messages:
    if st.button("🗑️  New conversation", use_container_width=False):
        st.session_state.messages = []
        st.rerun()
