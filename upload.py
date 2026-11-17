import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# --- Connection ---
conn = psycopg2.connect(
    host="localhost",
    port=5433,
    dbname="ruleengine_gen3",
    user="docbot",
    password="tobcod"
)
cur = conn.cursor()

# --- Create table ---
cur.execute("""
    CREATE TABLE IF NOT EXISTS stocks (
        id     SERIAL PRIMARY KEY,
        date   DATE,
        open   NUMERIC(10,2),
        high   NUMERIC(10,2),
        low    NUMERIC(10,2),
        close  NUMERIC(10,2),
        volume BIGINT,
        ticker VARCHAR(10)
    );
""")

# --- Load CSV ---
# Update this path if your CSV is somewhere else
df = pd.read_csv("/home/muralik/Downloads/all_stocks_30000_rows.csv")
df.columns = [c.lower().strip() for c in df.columns]
df.rename(columns={"name": "ticker"}, inplace=True)
df["date"] = pd.to_datetime(df["date"]).dt.date

rows = list(df[["date","open","high","low","close","volume","ticker"]].itertuples(index=False, name=None))
execute_values(cur, "INSERT INTO stocks (date, open, high, low, close, volume, ticker) VALUES %s", rows, page_size=1000)

conn.commit()
print(f"✅ Inserted {len(rows)} rows into stocks table.")
cur.close()
conn.close()