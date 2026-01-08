from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import troch
from transformers import AutoModel, AutoModelForCausalLM, AutoTokenizer

from src.llms.Enums_LLM import HFEnums


class HuggingFaceProvider:
    def __init__(self,
        model_id: str,
        *,
        device: Optional[str] = None,          # "cuda", "cpu", "mps" or None (auto)
        device_map: Optional[str] = "auto",    # accelerate mapping
        torch_dtype: Union[str, torch.dtype] = "auto",
        trust_remote_code: bool = False,
        default_input_max_characters: int = 5000,
        default_generation_max_output_tokens: int = 1000,
        default_generation_temperature: float = 0.1,
        default_generation_do_sample: bool = False):


        self.logger = logging.getLogger(__name__)
        self.enums = HFEnums()

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature
        self.default_generation_do_sample = default_generation_do_sample

        self.generation_model_id: Optional[str] = None
        self.embedding_model_id: Optional[str] = None
        self.embedding_dimensions_size: Optional[int] = None

        self._gen_tokenizer = None
        self._gen_model = None

        self._emb_tokenizer = None
        self._emb_model = None

        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self._device_map = device_map
        self._torch_dtype = torch_dtype
        self._trust_remote_code = trust_remote_code

        self.set_generation_model(model_id)

    def close(self) -> None:
        """Free GPU RAM"""
        try:
            self._gen_model = None
            self._gen_tokenizer = None
            self._emb_model = None
            self._emb_tokenizer = None

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    def set_generation_model(self, model_id: str) -> None:
        """Load (or reload) a generation model."""
        self.generation_model_id = model_id

        # otherwise fallback to AutoModelForCausalLM.
        self._gen_tokenizer, self._gen_model = self._load_generation_model(model_id)

    def _load_generation_model(self, model_id: str):
        try:
            from transformers import Mistral3ForConditionalGeneration, MistralCommonBackend  # type: ignore

            tok = MistralCommonBackend.from_pretrained(model_id)
            mdl = Mistral3ForConditionalGeneration.from_pretrained(model_id, device_map=self._device_map)
            mdl.eval()
            return tok, mdl
        except Exception:
            # Not available or not that model. Fall back.
            pass

        # 2) Generic HF
        tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=self._trust_remote_code)

        # Some LMs have no pad token; set it to eos to avoid warnings in batching
        if tok.pad_token_id is None and tok.eos_token_id is not None:
            tok.pad_token = tok.eos_token

        kwargs: Dict[str, Any] = {
            "trust_remote_code": self._trust_remote_code,
        }

        if self._torch_dtype != "auto":
            kwargs["torch_dtype"] = self._torch_dtype

        if self._device_map is not None:
            kwargs["device_map"] = self._device_map

        mdl = AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
        mdl.eval()

        if self._device_map is None:
            mdl.to(self._device)

        return tok, mdl

    # ----------------------------
    # Helpers
    # ----------------------------
    def process_text(self, text: str) -> str:
        return (text or "")[: self.default_input_max_characters].strip()

    def construct_prompt(self, prompt: str, role: str) -> Dict[str, str]:
        return {"role": role, "content": prompt}

    def _normalize_role(self, role: str) -> str:
        r = (role or "").lower().strip()
        if r in ("system", "developer"):
            return self.enums.SYSTEM
        if r in ("assistant", "ai"):
            return self.enums.ASSISTANT
        return self.enums.USER

    def _build_messages(
            self,
            prompt: str,
            chat_history: Optional[List[Dict[str, Any]]],
    ) -> List[Dict[str, str]]:
        base: List[Dict[str, Any]] = list(chat_history) if chat_history else []
        msgs: List[Dict[str, str]] = []

        for m in base:
            msgs.append(
                {
                    "role": self._normalize_role(str(m.get("role", self.enums.USER))),
                    "content": str(m.get("content", "")),
                }
            )

        msgs.append({"role": self.enums.USER, "content": prompt})
        return msgs

    def _format_fallback_prompt(self, messages: List[Dict[str, str]]) -> str:
        parts = []
        for m in messages:
            role = m["role"]
            content = m["content"]
            if role == self.enums.SYSTEM:
                parts.append(f"[SYSTEM]\n{content}\n")
            elif role == self.enums.ASSISTANT:
                parts.append(f"[ASSISTANT]\n{content}\n")
            else:
                parts.append(f"[USER]\n{content}\n")
        parts.append("[ASSISTANT]\n")
        return "\n".join(parts)

    def generate_text(
            self,
            prompt: str,
            chat_history: Optional[List[Dict[str, Any]]] = None,
            max_output_tokens: Optional[int] = None,
            temperature: Optional[float] = None,
            model_id: Optional[str] = None,  # stateless override (reloads if different)
            do_sample: Optional[bool] = None,
    ) -> Optional[Tuple[str, int, str]]:
        """
        Returns: (message, total_tokens, cost_string)
        cost_string is "0$" because it's local inference.
        """
        if model_id and model_id != self.generation_model_id:
            self.set_generation_model(model_id)

        if not self._gen_model or not self._gen_tokenizer:
            self.logger.error("HF generation model not loaded")
            return None

        max_new_tokens = int(max_output_tokens or self.default_generation_max_output_tokens)
        temperature = float(temperature if temperature is not None else self.default_generation_temperature)

        # Usually: do_sample must be True to use temperature meaningfully
        do_sample_final = bool(do_sample if do_sample is not None else self.default_generation_do_sample)
        if temperature <= 0:
            do_sample_final = False

        prompt = self.process_text(prompt)
        messages = self._build_messages(prompt=prompt, chat_history=chat_history)

        # Tokenize with chat template if possible (best)
        try:
            if hasattr(self._gen_tokenizer, "apply_chat_template"):
                tokenized = self._gen_tokenizer.apply_chat_template(
                    conversation=messages,
                    return_tensors="pt",
                    return_dict=True,
                )
                input_ids = tokenized["input_ids"]
            else:
                full_prompt = self._format_fallback_prompt(messages)
                tokenized = self._gen_tokenizer(
                    full_prompt,
                    return_tensors="pt",
                    truncation=True,
                )
                input_ids = tokenized["input_ids"]
        except Exception:
            self.logger.exception("Tokenization failed")
            return None

        if self._device_map is None:
            input_ids = input_ids.to(self._device)
        else:

            if torch.cuda.is_available():
                try:
                    input_ids = input_ids.to("cuda")
                except Exception:
                    pass

        prompt_len = int(input_ids.shape[-1])

        gen_kwargs: Dict[str, Any] = {
            "max_new_tokens": max_new_tokens,
            "do_sample": do_sample_final,
        }
        if do_sample_final:
            gen_kwargs["temperature"] = temperature

        try:
            with torch.no_grad():
                out = self._gen_model.generate(input_ids, **gen_kwargs)
        except Exception:
            self.logger.exception("Generation failed")
            return None

        # out: [batch, prompt+new]
        new_token_ids = out[0, prompt_len:]
        try:
            text = self._gen_tokenizer.decode(new_token_ids, skip_special_tokens=True)
        except Exception:
            self.logger.exception("Decoding failed")
            return None


        total_tokens = int(out.shape[-1])  # prompt + new

        return text.strip(), total_tokens





