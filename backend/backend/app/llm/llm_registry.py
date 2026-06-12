import httpx
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import ChatHuggingFace
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from app.core.config import settings


def _build_enterprise_http_client() -> httpx.Client:
    return httpx.Client(verify=False)


def build_llm_model():
    llm_provider = settings.llm_provider
    model = settings.coding_chat_model
    temperature = settings.llm_temperature

    # Base configuration common to most models
    base_config = {
        "model": model,
        "max_tokens": 2048,
    }

    # Use None as the sentinel value in your settings instead of -10
    if temperature is not None:
        base_config["temperature"] = temperature

    return _get_llm_provider(
        provider=llm_provider,
        base_config=base_config
    )


def _get_llm_provider(provider: str, base_config: dict):
    # Map providers to their initialization logic to handle specific kwargs
    if provider == 'openai':
        return ChatOpenAI(
            **base_config,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,# For astream support
            stream_usage=True # Ensure stream usage is captured if stream_options isn't fully supported
        )

    elif provider == 'anthropic':
        return ChatAnthropic(
            **base_config,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url
        )

    elif provider == 'google-genai':
        return ChatGoogleGenerativeAI(
            **base_config,
            google_api_key=settings.llm_api_key,
            # Note: base_url is typically handled differently in Google SDKs
            # unless routing through Vertex AI specific endpoints.
        )

    elif provider == 'ollama':
        return ChatOllama(
            **base_config,
            base_url=settings.llm_base_url,
            # Ollama does not need an API key
        )

    elif provider == "huggingface":
        # Rename 'model' to 'model_id' to match Hugging Face expected parameters
        hf_config = base_config.copy()
        model_id = hf_config.pop("model")

        return ChatHuggingFace.from_model_id(
            model_id=model_id,
            huggingfacehub_api_token=settings.llm_api_key,
            # Pass any remaining valid kwargs (like temperature) into model_kwargs
            model_kwargs={
                "max_new_tokens": hf_config.pop("max_tokens", 4096),
                **hf_config,
            },
        )

    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")