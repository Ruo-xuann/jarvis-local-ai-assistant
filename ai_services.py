import json
import os

from openai import OpenAI


SETTINGS_FILE = "settings.json"


DEFAULT_SETTINGS = {
    "provider": "ollama",
    "model": "qwen2.5-coder:7b",
    "base_url": "http://localhost:11434/v1",
    "api_key": "ollama"
}


class AIProvider:

    def __init__(self):
        self.provider = "ollama"
        self.model = "qwen2.5-coder:7b"
        self.base_url = "http://localhost:11434/v1"
        self.api_key = "ollama"

        self.load()

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )


    # ========================================================
    # SETTINGS
    # ========================================================

    def load(self):

        settings = DEFAULT_SETTINGS.copy()

        if os.path.exists(SETTINGS_FILE):

            try:

                with open(
                    SETTINGS_FILE,
                    "r",
                    encoding="utf-8"
                ) as file:

                    saved = json.load(file)

                if isinstance(saved, dict):
                    settings.update(saved)

            except Exception:
                pass

        self.provider = settings.get(
            "provider",
            "ollama"
        )

        self.model = settings.get(
            "model",
            "qwen2.5-coder:7b"
        )

        self.base_url = settings.get(
            "base_url",
            "http://localhost:11434/v1"
        )

        self.api_key = settings.get(
            "api_key",
            "ollama"
        )


    def save(
        self,
        provider,
        model,
        base_url,
        api_key
    ):

        self.provider = provider
        self.model = model
        self.base_url = base_url
        self.api_key = api_key

        settings = {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "api_key": self.api_key
        }

        with open(
            SETTINGS_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                settings,
                file,
                indent=2
            )

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )


    # ========================================================
    # CHAT
    # ========================================================

    def chat(
        self,
        messages,
        temperature=0.7
    ):

        if isinstance(messages, str):

            messages = [
                {
                    "role": "user",
                    "content": messages
                }
            ]

        try:

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature
            )

            return response.choices[0].message.content

        except Exception as error:

            raise RuntimeError(
                f"{type(error).__name__}: {error}"
            ) from error


    # ========================================================
    # CONNECTION TEST
    # ========================================================

    def test_connection(self):

        try:

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": "Say hello in one short sentence."
                    }
                ],
                temperature=0.2
            )

            text = response.choices[0].message.content

            return True, text

        except Exception as error:

            return False, str(error)