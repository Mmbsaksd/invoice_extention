import os
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from shared.config import get_env

def get_llm():
    """Deterministic LLM Factory."""
    if get_env("AZURE_OPENAI_API_KEY"):
        return AzureChatOpenAI(
            azure_endpoint=get_env("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=get_env("AZURE_OPENAI_DEPLOYMENT_NAME"),
            api_version=get_env("AZURE_OPENAI_API_VERSION"),
            temperature=0
        )
    if get_env("OPENAI_API_KEY"):
        return ChatOpenAI(model="gpt-4o", temperature=0)
    if get_env("GOOGLE_API_KEY"):
        return ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)
    raise ValueError("Missing API Keys")
