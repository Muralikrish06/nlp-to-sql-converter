import logging
import os
import re
import traceback
import requests
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

load_dotenv(dotenv_path="env")


# ─── Logging Setup ────────────────────────────────────────────────────────────

def setup_logger(logger_name, log_file, log_level_env, backup_count=10, max_bytes=20_000_000):
    """Setup a logger with rotating file handler."""
    log_dir = os.getenv("LOG_DIRECTORY", "./")
    logger_file_path = os.path.join(str(log_dir), log_file)

    log_level_dict = {
        "DEBUG":    logging.DEBUG,
        "INFO":     logging.INFO,
        "WARNING":  logging.WARNING,
        "ERROR":    logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    log_level = log_level_dict.get(log_level_env, logging.INFO)

    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)

    handler = RotatingFileHandler(logger_file_path, maxBytes=max_bytes, backupCount=backup_count)
    handler.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(filename)s] [ %(lineno)s:%(funcName)5s()] %(message)s",
        datefmt="%Y-%b-%d %H:%M:%S",
    ))
    logger.addHandler(handler)
    return logger, log_level


_log_level_env = os.getenv("LOG_LEVEL", "INFO")
LOGGER, LOG_LEVEL = setup_logger(
    "NL_TO_SQL_LOGGER",
    "nl-to-sql.log",
    _log_level_env,
)

_metrics_log_level_env = os.getenv("METRICS_LOG_LEVEL", "INFO")
METRICS_LOGGER, METRICS_LOG_LEVEL = setup_logger(
    "NL_TO_SQL_METRICS_LOGGER",
    "nl-to-sql-metrics.log",
    _metrics_log_level_env,
)

# ──────────────────────────────────────────────────────────────────────────────

# ─── DB CONFIG ────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "44.253.21.216"),
    "port":     int(os.getenv("DB_PORT", 9420)),
    "database": os.getenv("DB_NAME",     "braindb"),
    "user":     os.getenv("DB_USER",     "braindbuser"),
    "password": os.getenv("DB_PASSWORD", "OYbj4muRoR0l"),
}

# ─── LLM CONFIG ──────────────────────────────────────────────────────────────
GROQ_MODEL   = "BAI-IVision-SFT-3_2"
GROQ_API_URL = "https://llm-extract-api-3.aptimeta.com/v1/chat/completions"


# ─── PROMPT TEMPLATE ─────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "You are an expert SQL assistant. "
    "Given a database schema and a user question, return ONLY a valid PostgreSQL SELECT query — "
    "no explanation, no markdown fences, no extra text. Just the raw SQL ending with a semicolon. "
    "Always wrap every column name in double quotes (e.g. \"businessDomain\", \"promptCategory\") "
    "to preserve exact case sensitivity in PostgreSQL. "
    "Do not add double quotes for table names. "
    "Only query tables and columns that are explicitly defined in the provided schema — "
    "never use system catalogs like pg_tables, information_schema, or any table not in the schema."
)

USER_PROMPT_TEMPLATE = """Database schema:
{schema}

Question: {question}

SQL query:"""


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def get_connection():
    """Return a psycopg2 connection using DB_CONFIG."""
    return psycopg2.connect(**DB_CONFIG)


def get_schema() -> str:
    """
    Auto-reads all public tables from Postgres and returns
    CREATE TABLE DDL statements for the SQLCoder prompt.
    """
    LOGGER.info("Fetching database schema from Postgres.")
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    tables = [row[0] for row in cur.fetchall()]

    ddl_parts = []
    for tbl in tables:
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position;
        """, (tbl,))
        cols = cur.fetchall()
        col_defs = ",\n    ".join(
            f"{c[0]} {c[1].upper()}" + (" NOT NULL" if c[2] == "NO" else "")
            for c in cols
        )
        ddl_parts.append(f"CREATE TABLE {tbl} (\n    {col_defs}\n);")

    cur.close()
    conn.close()
    LOGGER.info("Schema fetched: %d table(s).", len(tables))
    return "\n\n".join(ddl_parts)


def generate_sql(question: str, schema: str) -> str:
    """
    Calls the LLM via OpenAI-compatible chat completions API.
    Returns the generated SQL string.
    """
    LOGGER.info("Calling Groq API. Model: %s | Question: %s", GROQ_MODEL, question)
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": USER_PROMPT_TEMPLATE.format(question=question, schema=schema)},
        ],
        "max_tokens": 512,
        "temperature": 0.01,
    }

    headers = {
        "Content-Type": "application/json",
    }
    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)

    if response.status_code != 200:
        LOGGER.error("LLM API error %d: %s", response.status_code, response.text)
        raise RuntimeError(
            f"LLM API error {response.status_code}: {response.text}"
        )

    data = response.json()
    raw = data["choices"][0]["message"]["content"].strip()
    sql = extract_clean_sql(raw)
    LOGGER.info("SQL generated successfully.")
    LOGGER.debug("Generated SQL:\n%s", sql)
    return sql


def extract_clean_sql(raw: str) -> str:
    """
    Pull only the SQL from the model output.
    Strips markdown fences and trailing commentary.
    """
    # Try to grab content inside ```sql ... ```
    match = re.search(r"```sql\s*(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if match:
        sql = match.group(1).strip()
    else:
        # Fallback: everything after last occurrence of SELECT/WITH
        upper = raw.upper()
        for keyword in ("SELECT", "WITH", "INSERT", "UPDATE"):
            idx = raw.upper().rfind(keyword)
            if idx != -1:
                sql = raw[idx:].strip()
                # Cut at first blank line or semicolon
                sql = re.split(r"\n\s*\n", sql)[0].strip()
                break
        else:
            sql = raw.strip()

    # Safety guard — block destructive statements
    first_word = sql.split()[0].upper() if sql.split() else ""
    blocked = {"DROP", "DELETE", "TRUNCATE", "ALTER", "UPDATE", "INSERT", "CREATE"}
    if first_word in blocked:
        LOGGER.warning("Blocked destructive SQL statement starting with '%s'.", first_word)
        raise ValueError(
            f"Generated SQL starts with '{first_word}' — "
            "only SELECT queries are allowed in this demo."
        )

    return sql


def run_query(sql: str) -> dict:
    """
    Execute SQL against Postgres.
    Returns {"columns": [...], "rows": [...], "error": None | str}
    """
    LOGGER.info("Executing SQL query.")
    LOGGER.debug("SQL:\n%s", sql)
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(sql)
        rows    = cur.fetchmany(500)
        columns = [desc[0] for desc in cur.description] if cur.description else []
        conn.commit()
        LOGGER.info("Query executed successfully. Rows returned: %d.", len(rows))
        return {"columns": columns, "rows": [dict(r) for r in rows], "error": None}
    except Exception as exc:
        conn.rollback()
        LOGGER.error("Query execution failed: %s\n%s", exc, traceback.format_exc())
        return {"columns": [], "rows": [], "error": str(exc)}
    finally:
        cur.close()
        conn.close()


def nl_to_sql_and_run(question: str) -> dict:
    """
    End-to-end pipeline:
      question → schema fetch → SQLCoder → SQL → execute → results
    Returns a dict with keys: sql, columns, rows, error
    """
    LOGGER.info("Pipeline started. Question: %s", question)
    try:
        schema = get_schema()
        sql    = generate_sql(question, schema)
        result = run_query(sql)
        result["sql"] = sql
        if result["error"]:
            LOGGER.warning("Pipeline completed with query error: %s", result["error"])
        else:
            LOGGER.info(
                "Pipeline complete. Rows: %d | Columns: %s",
                len(result["rows"]), result["columns"],
            )
            METRICS_LOGGER.info(
                "nl_to_sql | question=%s | rows=%d | sql=%s",
                question, len(result["rows"]), sql,
            )
        return result
    except Exception as exc:
        LOGGER.critical("Pipeline failed: %s\n%s", exc, traceback.format_exc())
        raise


# ─── CLI TEST ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    LOGGER.info("Application started.")
    try:
        q = input("Enter your question: ")
        LOGGER.info("User question: %s", q)
        out = nl_to_sql_and_run(q)
        print("\n── Generated SQL ──")
        print(out["sql"])
        print(f"\n── Results ({len(out['rows'])} rows) ──")
        if out["error"]:
            LOGGER.error("Query error: %s", out["error"])
            print("Error:", out["error"])
        else:
            for row in out["rows"][:10]:
                print(row)
        LOGGER.info("Application finished successfully.")
    except Exception as exc:
        LOGGER.critical("Unhandled exception at top level: %s\n%s", exc, traceback.format_exc())
        raise