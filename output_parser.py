from langflow.custom import Component
from langflow.io import MessageInput, Output
from langflow.schema.message import Message


class OutputParser(Component):
    display_name = "Output Parser"
    description = "Passes Query Runner markdown output directly to Chat Output."
    icon = "file-text"
    name = "OutputParser"

    inputs = [
        MessageInput(name="raw_output", display_name="Raw Output"),
    ]

    outputs = [
        Output(display_name="Formatted Response", name="response", method="parse"),
    ]

    def parse(self) -> Message:
        raw = self.raw_output.text if hasattr(self.raw_output, "text") else str(self.raw_output)
        self.status = "Done"
        return Message(text=raw)
