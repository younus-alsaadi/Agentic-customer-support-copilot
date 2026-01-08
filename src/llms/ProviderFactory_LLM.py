from .Enums_LLM import Enums_LLM
from .provider import OpenAIProvider, CoHereProvider
from .provider.AzureOpenAIProvider import AzureOpenAIProvider
from .provider.HuggingFaceProvider import HuggingFaceProvider


class LLMProviderFactory:
    def __init__(self, config: dict):
        self.config = config

    def create(self, provider: str):
        if provider==Enums_LLM.OPENAI.value:
            return OpenAIProvider(
                api_key=self.config.OPENAI_API_KEY,
                api_url=self.config.OPENAI_API_URL,
                default_input_max_characters=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperature=self.config.GENERATION_DAFAULT_TEMPERATURE
            )

        if provider==Enums_LLM.COHERE.value:
            return CoHereProvider(
                api_key=self.config.COHERE_API_KEY,
                default_input_max_characters=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperature=self.config.GENERATION_DAFAULT_TEMPERATURE
            )

        if provider==Enums_LLM.AZUREOPENAI.value:
            return AzureOpenAIProvider(
                api_key=self.config.AZURE_OPENAI_API_KEY,
                azure_endpoint=self.config.AZURE_OPENAI_ENDPOINT,
                api_version= self.config.AZURE_OPENAI_API_VERSION,
                generation_model_id=self.config.AZURE_OPENAI_CHAT_DEPLOYMENT,
                default_input_max_characters=self.config.INPUT_DAFAULT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.GENERATION_DAFAULT_MAX_TOKENS,
                default_generation_temperature=self.config.GENERATION_DAFAULT_TEMPERATURE
            )

        if provider==Enums_LLM.HF.value:
            return HuggingFaceProvider(
                model_id=self.config.HF_GENERATION_MODEL_ID,
                device_map="auto",
                default_generation_do_sample=False
            )

        return None

