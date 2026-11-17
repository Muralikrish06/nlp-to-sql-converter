import psycopg2
import psycopg2.extras
from langflow.custom import Component
from langflow.io import IntInput, MessageInput, MessageTextInput, Output, SecretStrInput
from langflow.schema.message import Message


class PostgreSQLQueryRunner(Component):
    display_name = "PostgreSQL Query Runner"
    description = "Executes a SELECT SQL query against PostgreSQL and returns results as formatted text."
    icon = "database"
    name = "PostgreSQLQueryRunner"

    inputs = [
        MessageInput(name="question", display_name="Question"),
        MessageInput(name="sql", display_name="SQL Query"),
        MessageTextInput(name="host", display_name="Host", value="localhost"),
        IntInput(name="port", display_name="Port", value=5433),
        MessageTextInput(name="database", display_name="Database", value="ruleengine_gen3"),
        MessageTextInput(name="db_user", display_name="User", value="docbot"),
        SecretStrInput(name="password", display_name="Password"),
    ]

    outputs = [
        Output(display_name="Query Results", name="results", method="run_query"),
    ]

    def _markdown_table(self, columns: list, rows: list) -> str:
        if not rows:
            return "_No rows returned._"
        header = "| " + " | ".join(columns) + " |"
        divider = "| " + " | ".join("---" for _ in columns) + " |"
        data_rows = [
            "| " + " | ".join(str(dict(r).get(c, "")) for c in columns) + " |"
            for r in rows
        ]
        return "\n".join([header, divider] + data_rows)

    def run_query(self) -> Message:
        question_text = self.question.text if hasattr(self.question, "text") else str(self.question)
        sql_text = self.sql.text if hasattr(self.sql, "text") else str(self.sql)

        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.db_user,
                password=self.password,
            )
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            try:
                cur.execute(sql_text)
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description] if cur.description else []
                conn.commit()

                table_md = self._markdown_table(columns, rows)
                result_text = (
                    f"**Generated SQL:**\n```sql\n{sql_text}\n```\n\n"
                    f"**Results ({len(rows)} rows):**\n{table_md}\n\n"
                    f"---\n_Ask your next question below._"
                )
                self.status = f"{len(rows)} row(s) returned"
                return Message(text=result_text)
            except Exception as exc:
                conn.rollback()
                result_text = (
                    f"**Generated SQL:**\n```sql\n{sql_text}\n```\n\n"
                    f"**Error:** {exc}\n\n"
                    f"---\n_Ask your next question below._"
                )
                self.status = f"Query failed: {exc}"
                return Message(text=result_text)
            finally:
                cur.close()
                conn.close()
        except Exception as conn_exc:
            return Message(text=f"**Connection Error:** {conn_exc}")
