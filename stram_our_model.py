import streamlit as st
import pandas as pd
import traceback
from app_our_model import nl_to_sql_and_run, get_schema, get_connection, LOGGER, METRICS_LOGGER

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SQL Intelligence — Internal AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CUSTOM CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Base ── */
    .stApp { background: #f5f3ff; }

    /* ── Header ── */
    .main-header {
        background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 40%, #0ea5e9 100%);
        padding: 30px 36px;
        border-radius: 20px;
        margin-bottom: 28px;
        box-shadow: 0 8px 32px rgba(124,58,237,0.35);
        position: relative;
        overflow: hidden;
    }
    .main-header::after {
        content: "";
        position: absolute;
        top: -60px; right: -60px;
        width: 220px; height: 220px;
        background: radial-gradient(circle, rgba(255,255,255,0.18) 0%, transparent 70%);
        border-radius: 50%;
    }
    .main-header::before {
        content: "";
        position: absolute;
        bottom: -40px; left: 30%;
        width: 140px; height: 140px;
        background: radial-gradient(circle, rgba(14,165,233,0.2) 0%, transparent 70%);
        border-radius: 50%;
    }
    .main-header h1 {
        color: #ffffff;
        font-size: 2rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.02em;
        text-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }
    .main-header p {
        color: rgba(255,255,255,0.88);
        margin: 8px 0 0;
        font-size: 0.95rem;
    }
    .model-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(255,255,255,0.2);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255,255,255,0.35);
        color: #ffffff;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 20px;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-top: 12px;
    }

    /* ── Metric cards ── */
    .metric-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 22px 24px;
        text-align: center;
        box-shadow: 0 4px 20px rgba(124,58,237,0.1);
        border: 1px solid #ede9fe;
        transition: transform 0.2s;
    }
    .metric-card:hover { transform: translateY(-2px); box-shadow: 0 8px 28px rgba(124,58,237,0.18); }
    .metric-card .num {
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #7c3aed, #0ea5e9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.1;
    }
    .metric-card .lbl {
        color: #6b7280;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-top: 6px;
        font-weight: 600;
    }

    /* ── SQL block ── */
    .sql-block {
        background: #1e1b4b;
        border-left: 4px solid #7c3aed;
        border-radius: 12px;
        padding: 16px 20px;
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 0.87rem;
        color: #a5f3fc;
        white-space: pre-wrap;
        word-break: break-word;
        margin: 12px 0;
        box-shadow: inset 0 2px 8px rgba(0,0,0,0.3);
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #4f46e5 0%, #7c3aed 100%);
        border-right: none;
    }
    section[data-testid="stSidebar"] * { color: #ffffff !important; }
    section[data-testid="stSidebar"] pre,
    section[data-testid="stSidebar"] code {
        color: #a5f3fc !important;
        background: rgba(0,0,0,0.25) !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
        border-radius: 8px !important;
    }
    section[data-testid="stSidebar"] .stButton > button {
        background: rgba(255,255,255,0.18) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255,255,255,0.35) !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        backdrop-filter: blur(4px);
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255,255,255,0.3) !important;
    }
    section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.25) !important; }
    section[data-testid="stSidebar"] .stAlert {
        background: rgba(255,255,255,0.12) !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
        border-radius: 10px !important;
    }

    /* ── Run button ── */
    .stButton > button {
        background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        padding: 10px 28px !important;
        font-size: 1rem !important;
        box-shadow: 0 4px 16px rgba(124,58,237,0.4) !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover {
        box-shadow: 0 6px 24px rgba(124,58,237,0.55) !important;
        transform: translateY(-1px) !important;
    }

    /* ── Text area ── */
    .stTextArea textarea {
        background: #ffffff !important;
        color: #1e1b4b !important;
        border: 2px solid #ede9fe !important;
        border-radius: 12px !important;
        font-size: 1rem !important;
        box-shadow: 0 2px 8px rgba(124,58,237,0.08) !important;
    }
    .stTextArea textarea:focus {
        border-color: #7c3aed !important;
        box-shadow: 0 0 0 3px rgba(124,58,237,0.15) !important;
    }
    .stTextArea label { color: #4f46e5 !important; font-weight: 700 !important; font-size: 0.95rem !important; }

    /* ── Expander ── */
    details {
        background: #ffffff !important;
        border: 1px solid #ede9fe !important;
        border-radius: 14px !important;
        margin-bottom: 10px !important;
        box-shadow: 0 2px 12px rgba(124,58,237,0.08) !important;
        overflow: hidden !important;
    }
    details summary {
        background: #ffffff !important;
        color: #1e1b4b !important;
        font-weight: 600 !important;
        padding: 14px 18px !important;
    }
    details[open] summary { border-bottom: 1px solid #ede9fe !important; }

    /* ── Dataframe ── */
    .stDataFrame { border: 1px solid #ede9fe !important; border-radius: 12px !important; overflow: hidden; }

    /* ── Divider ── */
    hr { border-color: #ede9fe !important; }

    /* ── Section heading ── */
    .section-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #4f46e5;
        margin: 20px 0 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧠 Internal AI")
    st.markdown("---")

    st.markdown("### ⚡ Model")
    st.code("""Model  : BAI-IVision-SFT-3_2
Type   : Internal LLM
Auth   : No key required""", language="text")

    st.markdown("---")
    st.markdown("### 🗄️ Database")
    st.code("""Host     : localhost
Port     : 5433
Database : ruleengine_gen3
User     : docbot""", language="text")

    if st.button("🔌 Test Connection", use_container_width=True):
        try:
            conn = get_connection()
            conn.close()
            LOGGER.info("Sidebar DB connection test: success.")
            st.success("Connected ✓")
        except Exception as e:
            LOGGER.error("Sidebar DB connection test failed: %s\n%s", e, traceback.format_exc())
            st.error(f"Failed: {e}")

    st.markdown("---")
    st.markdown("### 📐 Schema")
    if st.button("🔍 Show Schema", use_container_width=True):
        try:
            schema = get_schema()
            LOGGER.info("Sidebar schema preview requested.")
            st.code(schema, language="sql")
        except Exception as e:
            LOGGER.error("Sidebar schema fetch failed: %s\n%s", e, traceback.format_exc())
            st.error(str(e))

    st.markdown("---")
    st.caption("NL2SQL · BAI-IVision-SFT-3_2 · PostgreSQL")


# ─── MAIN HEADER ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>🧠 SQL Intelligence — Internal AI</h1>
  <p>Ask your database anything in plain English. Our internal model converts it to SQL and returns live results — no external API needed.</p>
  <div class="model-badge">⚡ BAI-IVision-SFT-3_2 &nbsp;·&nbsp; ruleengine_gen3 &nbsp;·&nbsp; PostgreSQL</div>
</div>
""", unsafe_allow_html=True)

# ─── SESSION STATE ────────────────────────────────────────────────────────────
if "history"     not in st.session_state: st.session_state.history     = []
if "query_count" not in st.session_state: st.session_state.query_count = 0
if "total_rows"  not in st.session_state: st.session_state.total_rows  = 0
if "question"    not in st.session_state: st.session_state.question    = ""

# ─── STATS ROW ────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"""
    <div class="metric-card">
      <div class="num">{st.session_state.query_count}</div>
      <div class="lbl">Queries Run</div>
    </div>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="metric-card">
      <div class="num">{st.session_state.total_rows}</div>
      <div class="lbl">Rows Fetched</div>
    </div>""", unsafe_allow_html=True)
with col3:
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")
        tbl_count = cur.fetchone()[0]
        cur.close(); conn.close()
        LOGGER.debug("Table count fetched: %d.", tbl_count)
    except Exception as e:
        LOGGER.warning("Failed to fetch table count: %s", e)
        tbl_count = "?"
    st.markdown(f"""
    <div class="metric-card">
      <div class="num">{tbl_count}</div>
      <div class="lbl">Tables Connected</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")

# ─── QUESTION INPUT ───────────────────────────────────────────────────────────
question = st.text_area(
    "💬 What would you like to know?",
    value=st.session_state.question,
    height=100,
    placeholder="e.g. Show me the top 10 rules by prompt category this month",
)

run_col, clear_col = st.columns([1, 5])
with run_col:
    run_clicked = st.button("▶  Run Query", use_container_width=True)
with clear_col:
    if st.button("🗑 Clear History", use_container_width=False):
        LOGGER.info("Query history cleared by user.")
        st.session_state.history     = []
        st.session_state.query_count = 0
        st.session_state.total_rows  = 0
        st.session_state.question    = ""
        st.rerun()

# ─── PROCESS QUERY ────────────────────────────────────────────────────────────
if run_clicked and question.strip():
    with st.spinner("🧠 BAI-IVision-SFT-3_2 is generating your query..."):
        try:
            LOGGER.info("UI query submitted: %s", question.strip())
            result = nl_to_sql_and_run(question.strip())

            row_count = len(result.get("rows", []))
            st.session_state.query_count += 1
            st.session_state.total_rows  += row_count

            st.session_state.history.insert(0, {
                "question": question.strip(),
                "sql":      result.get("sql", ""),
                "rows":     result.get("rows", []),
                "columns":  result.get("columns", []),
                "error":    result.get("error"),
            })

            if result.get("error"):
                LOGGER.error("UI query error: %s | SQL: %s", result["error"], result.get("sql", ""))
            else:
                LOGGER.info("UI query success. Rows: %d | SQL: %s", row_count, result.get("sql", ""))
                METRICS_LOGGER.info(
                    "ui_query | question=%s | rows=%d | sql=%s",
                    question.strip(), row_count, result.get("sql", ""),
                )
            st.rerun()

        except Exception as e:
            LOGGER.critical("UI query unhandled exception: %s\n%s", e, traceback.format_exc())
            st.error(f"❌ Error: {str(e)}")

elif run_clicked and not question.strip():
    st.warning("Please enter a question first.")

# ─── RESULTS ──────────────────────────────────────────────────────────────────
if st.session_state.history:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">📋 Query History</div>', unsafe_allow_html=True)
    for i, item in enumerate(st.session_state.history):
        with st.expander(
            f"{'🟢' if not item['error'] else '🔴'}  {item['question']}",
            expanded=(i == 0)
        ):
            st.markdown("**Generated SQL:**")
            st.markdown(f'<div class="sql-block">{item["sql"]}</div>', unsafe_allow_html=True)

            if item["error"]:
                st.error(f"SQL Execution Error: {item['error']}")
            else:
                row_count = len(item["rows"])
                st.success(f"✅ {row_count} row{'s' if row_count != 1 else ''} returned")

                if row_count > 0:
                    df = pd.DataFrame(item["rows"], columns=item["columns"])
                    st.dataframe(df, use_container_width=True, height=300)

                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="⬇ Download CSV",
                        data=csv,
                        file_name=f"query_result_{i+1}.csv",
                        mime="text/csv",
                        key=f"dl_{i}",
                    )
                else:
                    st.info("Query returned no rows.")
