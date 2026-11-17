from __future__ import annotations

import httpx

from langflow.custom import Component
from langflow.io import DataInput, MessageInput, MessageTextInput, Output, SecretStrInput, StrInput
from langflow.schema import Data
from langflow.schema.message import Message


class ModelComponent(Component):
    display_name = "Custom Model Component"
    description = "Call any OpenAI-compatible /chat/completions endpoint with optional images."
    icon = "bot"
    name = "ModelComponent"

    inputs = [
        StrInput(
            name="base_url",
            display_name="Base URL",
            info="Full chat completions endpoint",
            required=True,
        ),
        StrInput(
            name="model_name",
            display_name="Model Name",
            info="Model identifier sent in the request body.",
            value="BAI-IVision-SFT-3_2",
            required=True,
        ),
        MessageInput(
            name="prompt",
            display_name="Prompt",
            info="Connect to Prompt Template output.",
            required=True,
        ),
        DataInput(
            name="images",
            display_name="Images",
            info="Optional Data object with key 'images' (list of base64 data URLs).",
            required=False,
        ),
        SecretStrInput(
            name="api_key",
            display_name="API Key",
            info="Bearer token. Leave blank if the endpoint is unauthenticated.",
            required=False,
        ),
        MessageTextInput(
            name="system_message",
            display_name="System Message",
            info="Optional system prompt prepended to the conversation.",
            required=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Message", name="message", method="invoke"),
    ]

    def _build_user_content(self) -> list[dict] | str:
        # Properly extract text from Message objects passed by Langflow components
        if hasattr(self.prompt, "text"):
            prompt_text = self.prompt.text
        else:
            prompt_text = str(self.prompt)

        image_urls: list[str] = []
        if self.images is not None:
            payload = self.images.data if isinstance(self.images, Data) else self.images
            if isinstance(payload, dict):
                image_urls = payload.get("images", []) or []
            elif isinstance(payload, list):
                image_urls = payload

        if not image_urls:
            return prompt_text

        parts: list[dict] = [{"type": "text", "text": prompt_text}]
        for url in image_urls:
            parts.append({"type": "image_url", "image_url": {"url": url}})
        return parts

    def invoke(self) -> Message:
        messages: list[dict] = []
        if self.system_message:
            messages.append({"role": "system", "content": str(self.system_message)})
        messages.append({"role": "user", "content": self._build_user_content()})

        payload = {"model": self.model_name, "messages": messages}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        with httpx.Client(timeout=180) as client:
            r = client.post(self.base_url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()

        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(f"Unexpected response shape: {data}") from e

        self.status = text
        return Message(text=text)
