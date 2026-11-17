import psycopg2
from langflow.custom import Component
from langflow.io import IntInput, MessageInput, MessageTextInput, Output, SecretStrInput
from langflow.schema.message import Message


class PostgreSQLSchemaFetcher(Component):
    display_name = "PostgreSQL Schema Fetcher"
    description = "Connects to PostgreSQL and returns CREATE TABLE DDL for all public tables."
    icon = "database"
    name = "PostgreSQLSchemaFetcher"

    inputs = [
        MessageInput(name="trigger", display_name="Trigger (Chat Input)", required=False,
                     info="Connect to Chat Input so the schema re-fetches on every new question."),
        MessageTextInput(name="host", display_name="Host", value="localhost"),
        IntInput(name="port", display_name="Port", value=5433),
        MessageTextInput(name="database", display_name="Database", value="ruleengine_gen3"),
        MessageTextInput(name="db_user", display_name="User", value="docbot"),
        SecretStrInput(name="password", display_name="Password"),
    ]

    outputs = [
        Output(display_name="Schema DDL", name="schema", method="fetch_schema"),
    ]

    def fetch_schema(self) -> Message:
        conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.db_user,
            password=self.password,
        )
        cur = conn.cursor()

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

        schema = "\n\n".join(ddl_parts)
        self.status = f"Fetched {len(tables)} table(s)"
        return Message(text=schema)
