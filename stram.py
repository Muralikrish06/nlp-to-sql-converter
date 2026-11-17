import os
import traceback
import streamlit as st
import pandas as pd
from main import nl_to_sql_and_run, get_schema, get_connection, LOGGER, METRICS_LOGGER

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NL2SQL Dashboard",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── CUSTOM CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Base */
    .stApp { background-color: #0f172a; color: #e2e8f0; }

    /* Hide default sidebar toggle & footer */
    footer { visibility: hidden; }
    [data-testid="collapsedControl"] { display: none; }

    /* Top bar */
    .topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 14px 24px;
        margin-bottom: 20px;
    }
    .topbar-title { font-size: 1.3rem; font-weight: 800; color: #f1f5f9; letter-spacing: -0.01em; }
    .topbar-sub   { font-size: 0.8rem; color: #94a3b8; margin-top: 2px; }
    .topbar-badge {
        background: #22c55e22;
        color: #22c55e;
        border: 1px solid #22c55e55;
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    /* Panel card */
    .panel {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px 22px;
        height: 100%;
    }
    .panel-title {
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #64748b;
        margin-bottom: 14px;
    }

    /* Sample question pills */
    .sample-pill {
        display: inline-block;
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 20px;
        padding: 5px 12px;
        font-size: 0.78rem;
        color: #94a3b8;
        cursor: pointer;
        margin: 3px 3px 3px 0;
        transition: background 0.15s, color 0.15s;
    }
    .sample-pill:hover { background: #334155; color: #f1f5f9; }

    /* Stat chips */
    .stat-row { display: flex; gap: 10px; margin-bottom: 18px; }
    .stat-chip {
        flex: 1;
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 10px 12px;
        text-align: center;
    }
    .stat-num { font-size: 1.4rem; font-weight: 800; color: #38bdf8; }
    .stat-lbl { font-size: 0.65rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em; }

    /* SQL code block */
    .sql-block {
        background: #0f172a;
        border: 1px solid #334155;
        border-left: 3px solid #38bdf8;
        border-radius: 8px;
        padding: 14px 16px;
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 0.84rem;
        color: #7dd3fc;
        white-space: pre-wrap;
        word-break: break-word;
        margin-bottom: 16px;
    }

    /* Divider */
    .divider { border: none; border-top: 1px solid #334155; margin: 14px 0; }

    /* Override streamlit elements inside panels */
    .stTextArea textarea {
        background: #0f172a !important;
        color: #e2e8f0 !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        font-size: 0.95rem !important;
    }
    .stTextArea textarea:focus { border-color: #38bdf8 !important; box-shadow: 0 0 0 2px #38bdf822 !important; }
    .stTextArea label { color: #94a3b8 !important; font-size: 0.78rem !important; }

    .stTextInput input {
        background: #0f172a !important;
        color: #e2e8f0 !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        font-size: 0.88rem !important;
    }
    .stTextInput label { color: #94a3b8 !important; font-size: 0.78rem !important; }

    /* Buttons */
    .stButton > button {
        background: #38bdf8 !important;
        color: #0f172a !important;
        border: none !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        font-size: 0.9rem !important;
        transition: opacity 0.15s !important;
    }
    .stButton > button:hover { opacity: 0.85 !important; }

    /* Secondary (clear) button — last button in a columns block */
    div[data-testid="column"]:last-child .stButton > button {
        background: #1e293b !important;
        color: #94a3b8 !important;
        border: 1px solid #334155 !important;
    }

    /* Dataframe */
    .stDataFrame { border: 1px solid #334155 !important; border-radius: 8px !important; }

    /* Alert */
    .stAlert { border-radius: 8px !important; }

    /* Expander */
    .streamlit-expanderHeader {
        background: #0f172a !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        color: #e2e8f0 !important;
    }

    /* Success / warning / error */
    div[data-testid="stNotification"] { border-radius: 8px !important; }

    /* Download button */
    .stDownloadButton > button {
        background: #1e293b !important;
        color: #38bdf8 !important;
        border: 1px solid #38bdf855 !important;
        font-size: 0.82rem !important;
    }

    /* Result header */
    .result-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
    }
    .result-q {
        font-size: 0.92rem;
        font-weight: 600;
        color: #f1f5f9;
        flex: 1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-right: 12px;
    }
    .badge-ok  { background:#22c55e22; color:#22c55e; border:1px solid #22c55e55; border-radius:12px; padding:2px 10px; font-size:0.72rem; font-weight:700; }
    .badge-err { background:#ef444422; color:#ef4444; border:1px solid #ef444455; border-radius:12px; padding:2px 10px; font-size:0.72rem; font-weight:700; }

    /* Schema code */
    .stCodeBlock { border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ─── SESSION STATE ────────────────────────────────────────────────────────────
if "history"     not in st.session_state: st.session_state.history     = []
if "query_count" not in st.session_state: st.session_state.query_count = 0
if "total_rows"  not in st.session_state: st.session_state.total_rows  = 0
if "question"    not in st.session_state: st.session_state.question    = ""
if "fill_sample" not in st.session_state: st.session_state.fill_sample = ""

SAMPLE_QUESTIONS = [
    "Show total revenue by department",
    "List top 10 customers by order value",
    "Monthly sales trend for this year",
    "Which products have low stock?",
    "Average order value per region",
]

# ─── TOP BAR ─────────────────────────────────────────────────────────────────
try:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")
    tbl_count = cur.fetchone()[0]
    cur.close(); conn.close()
    db_status = "Connected"
except Exception:
    tbl_count = "?"
    db_status = "Offline"

st.markdown(f"""
<div class="topbar">
  <div>
    <div class="topbar-title">🗄️ NL2SQL Dashboard</div>
    <div class="topbar-sub">Ask questions in plain English — AI generates & runs SQL instantly</div>
  </div>
  <div class="topbar-badge">{'🟢 DB ' + db_status}</div>
</div>
""", unsafe_allow_html=True)

# ─── SPLIT LAYOUT ─────────────────────────────────────────────────────────────
left, right = st.columns([1, 2], gap="medium")

# ══════════════════════════════════════════════════════════════════════════════
# LEFT PANEL — Query Input
# ══════════════════════════════════════════════════════════════════════════════
with left:
    st.markdown('<div class="panel-title">Query Panel</div>', unsafe_allow_html=True)

    # Stats chips
    st.markdown(f"""
    <div class="stat-row">
      <div class="stat-chip"><div class="stat-num">{st.session_state.query_count}</div><div class="stat-lbl">Queries</div></div>
      <div class="stat-chip"><div class="stat-num">{st.session_state.total_rows}</div><div class="stat-lbl">Rows</div></div>
      <div class="stat-chip"><div class="stat-num">{tbl_count}</div><div class="stat-lbl">Tables</div></div>
    </div>
    """, unsafe_allow_html=True)

    # API key
    groq_key = st.text_input(
        "Groq API Key",
        type="password",
        placeholder="gsk_xxxxxxxxxxxxxxxxxxxx",
        help="Get your free key at console.groq.com",
    )
    if groq_key:
        os.environ["GROQ_API_KEY"] = groq_key
        LOGGER.info("Groq API key updated.")
        st.success("API key set ✓")

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Question input — prefill from sample click
    default_q = st.session_state.fill_sample or st.session_state.question
    question = st.text_area(
        "Your question",
        value=default_q,
        height=110,
        placeholder="e.g. What is the total revenue by department this quarter?",
    )
    st.session_state.fill_sample = ""  # consume prefill

    btn_col, clr_col = st.columns([3, 2])
    with btn_col:
        run_clicked = st.button("▶ Run Query", use_container_width=True)
    with clr_col:
        if st.button("Clear", use_container_width=True):
            LOGGER.info("History cleared.")
            st.session_state.history     = []
            st.session_state.query_count = 0
            st.session_state.total_rows  = 0
            st.session_state.question    = ""
            st.rerun()

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Sample Questions</div>', unsafe_allow_html=True)
    for sample in SAMPLE_QUESTIONS:
        if st.button(sample, key=f"sample_{sample}", use_container_width=True):
            st.session_state.fill_sample = sample
            st.rerun()

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    with st.expander("DB Connection"):
        st.code("Host  : localhost\nPort  : 5432\nDB    : postgres\nUser  : docbot", language="text")
        if st.button("Test Connection"):
            try:
                c = get_connection(); c.close()
                st.success("PostgreSQL connected ✓")
            except Exception as e:
                st.error(f"Failed: {e}")

    with st.expander("Schema Preview"):
        if st.button("Load Schema"):
            try:
                st.code(get_schema(), language="sql")
            except Exception as e:
                st.error(str(e))

# ─── PROCESS QUERY ────────────────────────────────────────────────────────────
if run_clicked and question.strip():
    if not os.getenv("GROQ_API_KEY", ""):
        LOGGER.warning("Query attempted without API key.")
        st.error("⚠️ Please enter your Groq API key first.")
    else:
        with st.spinner("Generating SQL…"):
            try:
                LOGGER.info("UI query: %s", question.strip())
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
                    LOGGER.error("UI error: %s | SQL: %s", result["error"], result.get("sql", ""))
                else:
                    LOGGER.info("UI success. Rows: %d | SQL: %s", row_count, result.get("sql", ""))
                    METRICS_LOGGER.info(
                        "ui_query | question=%s | rows=%d | sql=%s",
                        question.strip(), row_count, result.get("sql", ""),
                    )
                st.rerun()
            except Exception as e:
                LOGGER.critical("UI unhandled: %s\n%s", e, traceback.format_exc())
                st.error(f"❌ {e}")

elif run_clicked and not question.strip():
    st.warning("Please enter a question first.")

# ══════════════════════════════════════════════════════════════════════════════
# RIGHT PANEL — Results
# ══════════════════════════════════════════════════════════════════════════════
with right:
    st.markdown('<div class="panel-title">Results Panel</div>', unsafe_allow_html=True)

    if not st.session_state.history:
        st.markdown("""
        <div style="text-align:center; padding: 80px 20px; color: #475569;">
            <div style="font-size:3rem; margin-bottom:12px;">🔍</div>
            <div style="font-size:1rem; font-weight:600; color:#64748b;">No queries yet</div>
            <div style="font-size:0.85rem; margin-top:6px;">Enter a question on the left and click <strong>Run Query</strong></div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for i, item in enumerate(st.session_state.history):
            badge = '<span class="badge-ok">✓ OK</span>' if not item["error"] else '<span class="badge-err">✗ Error</span>'
            st.markdown(f"""
            <div class="result-header">
              <div class="result-q" title="{item['question']}">{item['question']}</div>
              {badge}
            </div>
            """, unsafe_allow_html=True)

            with st.expander("Generated SQL", expanded=(i == 0)):
                st.markdown(f'<div class="sql-block">{item["sql"]}</div>', unsafe_allow_html=True)

            if item["error"]:
                st.error(f"SQL Error: {item['error']}")
            else:
                row_count = len(item["rows"])
                if row_count > 0:
                    df = pd.DataFrame(item["rows"], columns=item["columns"])
                    st.dataframe(df, use_container_width=True, height=280)
                    st.download_button(
                        label="⬇ Download CSV",
                        data=df.to_csv(index=False),
                        file_name=f"result_{i+1}.csv",
                        mime="text/csv",
                        key=f"dl_{i}",
                    )
                else:
                    st.info("Query returned no rows.")

            if i < len(st.session_state.history) - 1:
                st.markdown('<hr class="divider">', unsafe_allow_html=True)
