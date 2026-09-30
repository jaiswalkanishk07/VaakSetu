import logging
from typing import Any
from google.api_core.exceptions import ResourceExhausted

from langchain_google_genai import ChatGoogleGenerativeAI
from google.generativeai import configure, GenerativeModel

from task1_ai_core.config import GEMINI_API_KEYS, LLM_MODEL_NAME

logger = logging.getLogger(__name__)

class LLMFactory:
    """
    Central factory for providing robust Gemini LLM clients with multi-key failover.
    """
    
    @staticmethod
    def get_robust_langchain_llm(temperature: float = 0.0) -> ChatGoogleGenerativeAI | Any:
        """
        Returns a ChatGoogleGenerativeAI instance that automatically falls back
        to alternative API keys if the primary key gets rate limited (ResourceExhausted).
        """
        if not GEMINI_API_KEYS:
            raise ValueError("No Gemini API keys found in config. Please set GEMINI_API_KEYS in .env")
            
        # Initialize an LLM for each key
        llms = [
            ChatGoogleGenerativeAI(
                model=LLM_MODEL_NAME, 
                temperature=temperature, 
                google_api_key=key,
                max_retries=0  # Force immediate failover on 429
            )
            for key in GEMINI_API_KEYS
        ]
        
        primary_llm = llms[0]
        fallbacks = llms[1:]
        
        if fallbacks:
            # Native LangChain failover: Try primary, if fails, try fallback 1, etc.
            # Only fallback on Rate Limit (429) to prevent massive delays on 404/403 errors.
            robust_llm = primary_llm.with_fallbacks(
                fallbacks, 
                exceptions_to_handle=(ResourceExhausted,)
            )
            return robust_llm
        
        return primary_llm

    @staticmethod
    async def invoke_raw_gemini(prompt: str, json_mode: bool = False) -> str:
        """
        Used by the reward_engine. Manually loops through keys if one hits a rate limit.
        """
        if not GEMINI_API_KEYS:
            raise ValueError("No Gemini API keys found in config.")
            
        last_exception = None
        for key in GEMINI_API_KEYS:
            try:
                configure(api_key=key)
                model = GenerativeModel(LLM_MODEL_NAME)
                
                # We could set response_mime_type="application/json" if json_mode=True
                # but currently we just ask for JSON in the prompt.
                generation_config = {"temperature": 0.1}
                if json_mode:
                    generation_config["response_mime_type"] = "application/json"
                    
                # We need to run sync code in thread to avoid blocking loop,
                # though google.generativeai supports generate_content_async.
                from google.api_core import retry
                response = await model.generate_content_async(
                    prompt, 
                    generation_config=generation_config,
                    request_options={"retry": retry.Retry(initial=0, maximum=0, multiplier=0, timeout=0)}
                )
                return response.text
                
            except ResourceExhausted as e:
                logger.warning(f"Gemini API key exhausted, falling back to next key. Error: {e}")
                last_exception = e
                continue
            except Exception as e:
                # For any other error (like syntax, blocked content), don't failover, just bubble it up
                raise
                
        raise RuntimeError(f"All Gemini API keys exhausted or failed. Last error: {last_exception}")
