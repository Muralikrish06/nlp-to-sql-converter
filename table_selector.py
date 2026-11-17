from langflow.custom import Component
from langflow.io import DropdownInput, StrInput, IntInput, MessageInput, SecretStrInput, Output
from langflow.schema import Message


class TableSelectorComponent(Component):
    display_name = "Table Selector"
    description = "Connects to PostgreSQL and provides a dropdown of available tables. Outputs the selected table name and its schema DDL."
    icon = "database"

    inputs = [
        MessageInput(
            name="trigger",
            display_name="Trigger (Chat Input)",
            info="Connect Chat Input here so the component re-runs on each question.",
        ),
        StrInput(name="host", display_name="Host", value="44.253.21.216"),
        IntInput(name="port", display_name="Port", value=9420),
        StrInput(name="database", display_name="Database", value="braindb"),
        StrInput(name="user", display_name="User", value="braindbuser"),
        SecretStrInput(name="password", display_name="Password", value="OYbj4muRoR0l"),
        DropdownInput(
            name="selected_table",
            display_name="Select Table",
            options=["(connect to load tables)"],
            real_time_refresh=True,
            info="Select which table to query. Change Host/Port/DB above and click refresh to reload.",
        ),
    ]

    outputs = [
        Output(display_name="Table Name", name="table_name", method="get_table_name"),
        Output(display_name="Table Schema", name="table_schema", method="get_table_schema"),
    ]

    def update_build_config(self, build_config, field_value, field_name=None):
        if field_name in ("host", "port", "database", "user", "password", "selected_table"):
            try:
                import psycopg2

                conn = psycopg2.connect(
                    host=build_config["host"]["value"],
                    port=int(build_config["port"]["value"]),
                    database=build_config["database"]["value"],
                    user=build_config["user"]["value"],
                    password=build_config["password"]["value"],
                )
                cur = conn.cursor()
                cur.execute(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
                )
                tables = [row[0] for row in cur.fetchall()]
                cur.close()
                conn.close()
                if tables:
                    build_config["selected_table"]["options"] = tables
                    if build_config["selected_table"].get("value") not in tables:
                        build_config["selected_table"]["value"] = tables[0]
            except Exception as e:
                build_config["selected_table"]["options"] = [f"Error: {str(e)[:80]}"]
        return build_config

    def _connect(self):
        import psycopg2

        return psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
        )

    def get_table_name(self) -> Message:
        return Message(text=self.selected_table)

    def get_table_schema(self) -> Message:
        try:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    'CREATE TABLE ' || c.table_name || ' (' || E'\n' ||
                    string_agg(
                        '    ' || c.column_name || ' ' ||
                        UPPER(c.data_type) ||
                        CASE
                            WHEN c.character_maximum_length IS NOT NULL
                            THEN '(' || c.character_maximum_length || ')'
                            WHEN c.data_type IN ('numeric', 'decimal') AND c.numeric_precision IS NOT NULL
                            THEN '(' || c.numeric_precision || ',' || COALESCE(c.numeric_scale, 0) || ')'
                            ELSE ''
                        END,
                        ',' || E'\n'
                        ORDER BY c.ordinal_position
                    ) || E'\n);'
                FROM information_schema.columns c
                WHERE c.table_schema = 'public' AND c.table_name = %s
                GROUP BY c.table_name
                """,
                (self.selected_table,),
            )
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                return Message(text=row[0])
            return Message(text=f"Table '{self.selected_table}' not found in public schema.")
        except Exception as e:
            return Message(text=f"Schema fetch error: {str(e)}")
