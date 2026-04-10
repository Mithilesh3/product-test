from typing import Dict, Any
from openai import AzureOpenAI
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

azure_client = AzureOpenAI(
    api_key=settings.AZURE_OPENAI_API_KEY,
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    api_version=settings.AZURE_OPENAI_API_VERSION,
    max_retries=0,
    timeout=float(getattr(settings, "AI_REPORT_AZURE_REQUEST_TIMEOUT_SECONDS", 15.0) or 15.0),
)

DEPLOYMENT_NAME = settings.AZURE_OPENAI_DEPLOYMENT


def build_token_param(max_tokens: int) -> Dict[str, Any]:
    """
    Azure OpenAI now expects max_completion_tokens for chat completions.
    Keep a single helper so all clients stay compatible.
    """
    return {"max_completion_tokens": int(max_tokens)}


def build_prompt(flat_data: Dict[str, Any], scores: Dict[str, Any]) -> str:
    return f"""
User Profile:
{flat_data}

System Scores:
{scores}

Generate a structured professional life analysis report.
"""


def generate_ai_narrative(flat_data: Dict[str, Any], scores: Dict[str, Any]) -> Dict[str, Any]:
    prompt = build_prompt(flat_data, scores)

    response = azure_client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=[
            {"role": "system", "content": "You are a behavioral intelligence strategist."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        **build_token_param(1500),
    )

    content = response.choices[0].message.content

    usage = response.usage

    logger.info(
        f"AI Usage - Prompt: {usage.prompt_tokens}, "
        f"Completion: {usage.completion_tokens}, "
        f"Total: {usage.total_tokens}"
    )

    return {
        "ai_full_narrative": content,
        "token_usage": usage.total_tokens,
    }
