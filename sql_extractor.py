import re

from langflow.custom import Component
from langflow.io import MessageInput, Output
from langflow.schema.message import Message


class SQLExtractor(Component):
    display_name = "SQL Extractor"
    description = "Strips markdown fences from LLM output and returns clean SQL. Blocks destructive statements."
    icon = "code"
    name = "SQLExtractor"

    inputs = [
        MessageInput(name="llm_output", display_name="LLM Output"),
    ]

    outputs = [
        Output(display_name="Clean SQL", name="sql", method="extract_sql"),
    ]

    def extract_sql(self) -> Message:
        raw = self.llm_output.text if hasattr(self.llm_output, "text") else str(self.llm_output)

        match = re.search(r"```sql\s*(.*?)```", raw, re.DOTALL | re.IGNORECASE)
        if match:
            sql = match.group(1).strip()
        else:
            sql = raw.strip()
            for keyword in ("SELECT", "WITH", "INSERT", "UPDATE"):
                idx = raw.upper().rfind(keyword)
                if idx != -1:
                    sql = raw[idx:].strip()
                    # Only cut at blank line if the remaining text looks like commentary
                    # (i.e. the blank line is followed by non-SQL text)
                    break

        first_word = sql.split()[0].upper() if sql.split() else ""
        blocked = {"DROP", "DELETE", "TRUNCATE", "ALTER", "UPDATE", "INSERT", "CREATE"}
        if first_word in blocked:
            raise ValueError(f"Blocked destructive SQL starting with '{first_word}'.")

        self.status = sql
        return Message(text=sql)
