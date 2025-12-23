from ..Interface_LLM import Interface_LLM
from ..Enums_LLM import OpenAIEnums
from openai import OpenAI
import logging
import httpx
from typing import List, Union

class OpenAIProvider(Interface_LLM):
    def __init__(self,  api_key: str, api_url: str=None,
                        default_input_max_characters: int=500,
                       default_generation_max_output_tokens: int=1000,
                       default_generation_temperature: float=0.1):

        self.api_key = api_key
        self.api_url = api_url

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature

        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_dimensions_size = None

        http_client = httpx.Client(timeout=30.0)  # httpx 0.27.x

        self.client = OpenAI(
            api_key=self.api_key,
            http_client=http_client,
            base_url=self.api_url.rstrip("/") if self.api_url else None, # User OpenAPI or OLLAMA
        )


        self.enums = OpenAIEnums

        self.logger = logging.getLogger(__name__)


    def set_generation_model(self, model_id: str): # for change the model type in the runtime
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_dimensions_size: int):
        self.embedding_model_id = model_id
        self.embedding_dimensions_size = embedding_dimensions_size

    def process_text(self, text: str):
        return text[:self.default_input_max_characters].strip()

    def generate_text(self, prompt: str, chat_history: list = None, max_output_tokens: int = None,
                      temperature: float = None):

        if chat_history is None:
            chat_history = []

        if not self.client:
            self.logger.error("OpenAI client was not set")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for OpenAI was not set")
            return None

        max_output_tokens = max_output_tokens or self.default_generation_max_output_tokens
        temperature = temperature or self.default_generation_temperature

        chat_history.append(
            self.construct_prompt(prompt=prompt, role=OpenAIEnums.USER.value)
        )

        # Build request kwargs dynamically
        kwargs = {
            "model": self.generation_model_id,
            "messages": chat_history,
            "max_completion_tokens": max_output_tokens
        }

        # Some models (including gpt-5-mini-2025-08-07) DO NOT support temperature
        restricted_models = ("gpt-5-mini", "o1", "o3")

        if not self.generation_model_id.startswith(restricted_models):
            kwargs["temperature"] = temperature

        # Send request
        response = self.client.chat.completions.create(**kwargs)


        if not response or not response.choices or not response.choices[0].message:
            self.logger.error("Error while generating text with OpenAI")
            return None

        message = response.choices[0].message.content

        # ---- cost calculation ----
        usage = response.usage  # top-level, not in choices[0]

        # Extract usage info
        prompt_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        total_tokens = response.usage.total_tokens

        # ---- Cost calculation using your function ----
        total_cost = self.calc_cost(
            model_id=self.generation_model_id,
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens
        )

        # return message, tokens, and formatted cost string
        return message, total_tokens, f"{total_cost:.8f}$"

    def embed_text(self, text: Union[str,List[str]], document_type: str = None):


        if not self.client or not self.embedding_model_id:
            self.logger.error("OpenAI client/model not set")
            return None

        if isinstance(text, str):
            text = [text]


        kwargs = {"model": self.embedding_model_id, "input": text}

        # Only v3 models support custom dimensions
        if self.embedding_dimensions_size and self.embedding_model_id.startswith("text-embedding-3"):
            kwargs["dimensions"] = int(self.embedding_dimensions_size)

        response=self.client.embeddings.create(model=self.embedding_model_id,input=text)

        if not response or not response.data or len(response.data) == 0 or not response.data[0].embedding:
            self.logger.error("Error while embedding text with OpenAI")
            return None

        cost = self.calc_embedding_cost(response.usage.total_tokens, price_per_million=0.02)

        embeddings = [rec.embedding for rec in response.data]
        usage_data = {
            "prompt_tokens": response.usage.prompt_tokens,
            "total_tokens": response.usage.total_tokens,
            "total_cost": f"{cost:.8f}$",
        }

        return embeddings ,usage_data

    def construct_prompt(self, prompt: str, role: str):

        return {
            "role": role,
            'content': prompt,
        }

    def calc_embedding_cost(self,total_tokens: int, price_per_million: float) -> float:
        return total_tokens * (price_per_million / 1_000_000)

    def calc_cost(self,model_id, prompt_tokens, output_tokens):
        MODEL_PRICES = {
            "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
            "gpt-4.1": {"input": 5.00, "output": 15.00},
            "gpt-4o": {"input": 5.00, "output": 15.00},

        }
        prices = MODEL_PRICES[model_id]
        cost_in = prompt_tokens * (prices["input"] / 1_000_000)
        cost_out = output_tokens * (prices["output"] / 1_000_000)
        return cost_in + cost_out



