from ..Interface_LLM import Interface_LLM
from ..Enums_LLM import OpenAIEnums
from openai import OpenAI
import logging
import httpx
from typing import List, Union, Optional, Dict, Any, Tuple
from langsmith.wrappers import wrap_openai
import httpx

class OpenAIProvider(Interface_LLM):
    def __init__(self,  api_key: str, api_url: str=None,
                        default_input_max_characters: int=500,
                       default_generation_max_output_tokens: int=1000,
                       default_generation_temperature: float=0.1,
                        timeout_seconds: float = 30.0):

        self.api_key = api_key
        self.api_url = api_url

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature

        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_dimensions_size = None

        self.enums = OpenAIEnums
        self.logger = logging.getLogger(__name__)

        # CHANGED: keep http client as attribute so we can close it later
        self.http_client = httpx.Client(timeout=timeout_seconds)

        # wrap_openai lines for LangSmith for traces

        self.client = wrap_openai(OpenAI(
            api_key=self.api_key,
            http_client=self.http_client,
            base_url=self.api_url.rstrip("/") if self.api_url else None,
        ))

    # allow clean shutdown
    def close(self) -> None:
        try:
            if getattr(self, "http_client", None):
                self.http_client.close()
        except Exception:
            pass



    def set_generation_model(self, model_id: str): # for change the model type in the runtime
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_dimensions_size: int):
        self.embedding_model_id = model_id
        self.embedding_dimensions_size = embedding_dimensions_size

    def process_text(self, text: str):
        return text[:self.default_input_max_characters].strip()

    def generate_text(
        self,
        prompt: str,
        chat_history: Optional[List[Dict[str, Any]]] = None,
        max_output_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        model_id: Optional[str] = None,  # ADDED: stateless override
    ) -> Optional[Tuple[str, int, str]]:
        """
        Returns: (message, total_tokens, cost_string)
        """
        if not self.client:
            self.logger.error("OpenAI client was not set")
            return None

        model = model_id or self.generation_model_id
        if not model:
            self.logger.error("Generation model for OpenAI was not set")
            return None

        max_output_tokens = max_output_tokens or self.default_generation_max_output_tokens
        temperature = temperature if temperature is not None else self.default_generation_temperature

        # CHANGED: do NOT mutate incoming chat_history in-place (LangGraph safety)
        base_history: List[Dict[str, Any]] = list(chat_history) if chat_history else []
        new_history = base_history + [self.construct_prompt(prompt=prompt, role=self.enums.USER.value)]

        # CHANGED: use max_tokens for chat.completions (more compatible)
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": new_history,
            "max_tokens": int(max_output_tokens),
        }

        # Temperature: keep the rule but add a retry fallback if model rejects it
        restricted_prefixes = ("gpt-5-mini", "o1", "o3")
        if not model.startswith(restricted_prefixes):
            kwargs["temperature"] = float(temperature)

        try:
            response = self.client.chat.completions.create(**kwargs)
        except Exception as e:
            # Retry once without temperature if it seems to be unsupported
            if "temperature" in kwargs:
                self.logger.warning(
                    "Chat completion failed with temperature; retrying without it. Error: %s", e
                )
                kwargs.pop("temperature", None)
                try:
                    response = self.client.chat.completions.create(**kwargs)
                except Exception:
                    self.logger.exception("Chat completion failed after retry (no temperature).")
                    return None
            else:
                self.logger.exception("Chat completion failed.")
                return None

        if not response or not getattr(response, "choices", None) or not response.choices[0].message:
            self.logger.error("Error while generating text with OpenAI")
            return None

        message = response.choices[0].message.content or ""

        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", prompt_tokens + output_tokens) or 0)

        total_cost = self.calc_cost(model_id=model, prompt_tokens=prompt_tokens, output_tokens=output_tokens)
        return message, total_tokens, f"{total_cost:.8f}$"

    def embed_text(self, text: Union[str, List[str]], document_type: str = None):
        """
        Returns: (embeddings, usage_data)
        embeddings: List[List[float]]
        usage_data: dict with tokens + cost string
        """
        if not self.client or not self.embedding_model_id:
            self.logger.error("OpenAI client/model not set")
            return None

        inputs = [text] if isinstance(text, str) else list(text)

        kwargs: Dict[str, Any] = {"model": self.embedding_model_id, "input": inputs}

        # Only text-embedding-3* supports custom dimensions
        if self.embedding_dimensions_size and self.embedding_model_id.startswith("text-embedding-3"):
            kwargs["dimensions"] = int(self.embedding_dimensions_size)

        # CHANGED: actually use kwargs
        try:
            response = self.client.embeddings.create(**kwargs)
        except Exception:
            self.logger.exception("Embedding call failed.")
            return None

        if not response or not response.data or not response.data[0].embedding:
            self.logger.error("Error while embedding text with OpenAI")
            return None

        embeddings = [rec.embedding for rec in response.data]

        usage = getattr(response, "usage", None)
        total_tokens = int(getattr(usage, "total_tokens", 0) or 0)
        prompt_tokens = int(getattr(usage, "prompt_tokens", total_tokens) or 0)

        # NOTE: embedding pricing varies by model; keep simple default or make per-model table
        cost = self.calc_embedding_cost(total_tokens, price_per_million=0.02)

        usage_data = {
            "prompt_tokens": prompt_tokens,
            "total_tokens": total_tokens,
            "total_cost": f"{cost:.8f}$",
        }

        return embeddings, usage_data

    def construct_prompt(self, prompt: str, role: str):

        return {
            "role": role,
            'content': prompt,
        }

    def calc_embedding_cost(self,total_tokens: int, price_per_million: float) -> float:
        return total_tokens * (price_per_million / 1_000_000)


    def calc_cost(self, model_id: str, prompt_tokens: int, output_tokens: int) -> float:
        MODEL_PRICES = {
            "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
            "gpt-4.1": {"input": 5.00, "output": 15.00},
            "gpt-4o": {"input": 5.00, "output": 15.00},
        }

        # CHANGED: safe lookup (avoid KeyError)
        prices = MODEL_PRICES.get(model_id)
        if not prices:
            self.logger.warning("No pricing configured for model '%s'. Returning 0 cost.", model_id)
            return 0.0

        cost_in = float(prompt_tokens) * (float(prices["input"]) / 1_000_000.0)
        cost_out = float(output_tokens) * (float(prices["output"]) / 1_000_000.0)
        return cost_in + cost_out



