from ..Interface_LLM import Interface_LLM
from ..Enums_LLM import OpenAIEnums

import logging
import httpx
from typing import List, Union, Optional, Dict, Any, Tuple

from openai import AzureOpenAI
from langsmith.wrappers import wrap_openai


class AzureOpenAIProvider(Interface_LLM):
    def __init__(
        self,
        api_key: str,
        azure_endpoint: str,
        api_version: str,
        generation_model_id : str,
        default_input_max_characters: int = 500,
        default_generation_max_output_tokens: int = 1000,
        default_generation_temperature: float = 0.1,
        timeout_seconds: float = 30.0,
    ):
        self.api_key = api_key
        self.azure_endpoint = azure_endpoint
        self.api_version = api_version

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature

        # In Azure, these are typically DEPLOYMENT names
        self.generation_model_id = generation_model_id
        self.embedding_model_id = None
        self.embedding_dimensions_size = None

        self.enums = OpenAIEnums
        self.logger = logging.getLogger(__name__)

        self.http_client = httpx.Client(timeout=timeout_seconds)


        print(f"AzureOpenAI api {api_key}")
        print(f"AzureOpenAI endpoint {azure_endpoint}")
        print(f"AzureOpenAI model {generation_model_id}")

        self.client = wrap_openai(
            AzureOpenAI(
                api_key=self.api_key,
                azure_endpoint=self.azure_endpoint.rstrip("/"),
                api_version=self.api_version,
                http_client=self.http_client,
            )
        )

    def close(self) -> None:
        try:
            if getattr(self, "http_client", None):
                self.http_client.close()
        except Exception:
            pass

    def set_generation_model(self, model_id: str):
        # IMPORTANT: Azure expects the deployment name here
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_dimensions_size: int = None):
        # IMPORTANT: Azure expects the deployment name here
        self.embedding_model_id = model_id
        self.embedding_dimensions_size = embedding_dimensions_size

    def process_text(self, text: str):
        return text[: self.default_input_max_characters].strip()

    def construct_prompt(self, prompt: str, role: str):
        return {"role": role, "content": prompt}

    def generate_text(
            self,
            prompt: str,
            chat_history: Optional[List[Dict[str, Any]]] = None,
            max_output_tokens: Optional[int] = None,
            temperature: Optional[float] = None,
            model_id: Optional[str] = None,  # override (deployment name)
    ) -> Optional[Tuple[str, int, str]]:
        if not self.client:
            self.logger.error("AzureOpenAI client was not set")
            return None

        deployment = model_id or self.generation_model_id
        if not deployment:
            self.logger.error("Generation deployment name for Azure OpenAI was not set")
            return None

        max_output_tokens = max_output_tokens or self.default_generation_max_output_tokens
        temperature = temperature if temperature is not None else self.default_generation_temperature

        base_history: List[Dict[str, Any]] = list(chat_history) if chat_history else []
        new_history = base_history + [self.construct_prompt(prompt=prompt, role=self.enums.USER.value)]

        kwargs: Dict[str, Any] = {
            "model": deployment,  # Azure: deployment name
            "messages": new_history,
            "max_tokens": int(max_output_tokens),
            "temperature": float(temperature),
        }

        try:
            response = self.client.chat.completions.create(**kwargs)
        except Exception as e:
            # retry without temperature (some deployments/settings can reject it)
            self.logger.warning("Chat completion failed; retrying without temperature. Error: %s", e)
            kwargs.pop("temperature", None)
            try:
                response = self.client.chat.completions.create(**kwargs)
            except Exception:
                self.logger.exception("Chat completion failed after retry.")
                return None

        if not response or not getattr(response, "choices", None) or not response.choices[0].message:
            self.logger.error("Error while generating text with Azure OpenAI")
            return None

        message = response.choices[0].message.content or ""

        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", prompt_tokens + output_tokens) or 0)

        # Pricing on Azure depends on region + your offer; keep 0 or your own mapping
        total_cost = 0.0
        return message, total_tokens, f"{total_cost:.8f}$"

    def embed_text(self, text: Union[str, List[str]], document_type: str = None):
        if not self.client or not self.embedding_model_id:
            self.logger.error("AzureOpenAI client/deployment not set for embeddings")
            return None

        inputs = [text] if isinstance(text, str) else list(text)

        kwargs: Dict[str, Any] = {
            "model": self.embedding_model_id,  # Azure: embedding deployment name
            "input": inputs,
        }

        # Many Azure deployments ignore "dimensions"; only keep if you know your deployment supports it
        if self.embedding_dimensions_size is not None:
            kwargs["dimensions"] = int(self.embedding_dimensions_size)

        try:
            response = self.client.embeddings.create(**kwargs)
        except Exception:
            self.logger.exception("Embedding call failed.")
            return None

        if not response or not response.data or not response.data[0].embedding:
            self.logger.error("Error while embedding text with Azure OpenAI")
            return None

        embeddings = [rec.embedding for rec in response.data]

        usage = getattr(response, "usage", None)
        total_tokens = int(getattr(usage, "total_tokens", 0) or 0)

        usage_data = {
            "prompt_tokens": total_tokens,
            "total_tokens": total_tokens,
            "total_cost": f"{0.0:.8f}$",
        }
        return embeddings, usage_data