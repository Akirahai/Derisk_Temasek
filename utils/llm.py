import os
from typing import Any, Dict, Iterable, List, Optional
import time
import random 

from dotenv import load_dotenv
from loguru import logger
from openai import AzureOpenAI

from utils.tokens import DEFAULT_MODEL, log_usage

DEFAULT_MAX_TOKENS = 1200
DEFAULT_TEMPERATURE = 0.0
DEFAULT_TOP_P = 1.0
DEFAULT_FREQUENCY_PENALTY = 0.0
DEFAULT_PRESENCE_PENALTY = 0.0
DEFAULT_N_PAST_MESSAGES = 10
DEFAULT_SEED = None

LOG_FILEPATH = "./logs/out.log"
load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
    api_version=os.getenv("OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )

if os.environ.get("DISABLE_LOG_TO_TERMINAL", "").lower() == "true":
    logger.remove()

logger.add(LOG_FILEPATH)


# References
# https://cookbook.openai.com/examples/how_to_format_inputs_to_chatgpt_models#2-an-example-chat-completion-api-call
# https://cookbook.openai.com/examples/how_to_stream_completions
# https://platform.openai.com/docs/guides/text-generation/how-should-i-set-the-temperature-parameter
# https://platform.openai.com/docs/guides/text-generation/frequency-and-presence-penalties
# https://platform.openai.com/docs/guides/text-generation/reproducible-outputs
def get_completionCustom(
    messages: List[Dict[str, str]],
    max_tokens: Optional[int] = DEFAULT_MAX_TOKENS,
    temperature: Optional[float] = DEFAULT_TEMPERATURE,
    top_p: Optional[float] = DEFAULT_TOP_P,
    frequency_penalty: Optional[float] = DEFAULT_FREQUENCY_PENALTY,
    presence_penalty: Optional[float] = DEFAULT_PRESENCE_PENALTY,
    seed: Optional[int] = DEFAULT_SEED,
    max_retries: int = 10,  # Maximum number of retries
    min_retry_delay: float = 0.01,  # Minimum delay between retries in seconds
    max_retry_delay: float = 0.2,  # Maximum delay between retries in seconds
):
    retries = 0
    while retries < max_retries:
        try:
            response = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                seed=seed,
                stream=False,
            )
            reply_content = response.choices[0].message.content
            if reply_content:
                log_usage(prompt=messages, completion=reply_content)
                return reply_content
            else:
                raise ValueError("No reply content from API response!")
        except Exception as e:
            if "rate limit" in str(e).lower():  # Check if the error is due to rate limiting
                retries += 1
                if retries < max_retries:
                    retry_delay = random.uniform(min_retry_delay, max_retry_delay)
                    print(f"Rate limit exceeded, retrying in {retry_delay:.2f} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise Exception("Max retries reached due to rate limit errors.")
            else:
                raise e  # Re-raise the exception if it's not related to rate limiting


class CompletionStream:
    def __init__(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = DEFAULT_MAX_TOKENS,
        temperature: Optional[float] = DEFAULT_TEMPERATURE,
        top_p: Optional[float] = DEFAULT_TOP_P,
        frequency_penalty: Optional[float] = DEFAULT_FREQUENCY_PENALTY,
        presence_penalty: Optional[float] = DEFAULT_PRESENCE_PENALTY,
        seed: Optional[int] = DEFAULT_SEED,
    ):
        self.messages = messages
        self.completion: Optional[str] = None
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.seed = seed

    def __enter__(self):
        self.completion = None
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=self.messages,  # type: ignore
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            frequency_penalty=self.frequency_penalty,
            presence_penalty=self.presence_penalty,
            seed=self.seed,
            stream=True,
        )
        return response

    def __exit__(self, exc_type, exc_value, traceback):
        if self.completion is None:
            raise ValueError(
                "Ensure CompletionStream's `completion` attribute is set at the end of streaming"
            )
        log_usage(prompt=self.messages, completion=self.completion)


def print_stream(response: Iterable[Any]):
    """Print chat completion streaming response in chunks"""
    collected_messages = []
    for chunk in response:
        chunk_message = chunk.choices[0].delta.content
        if chunk_message is not None:
            collected_messages.append(chunk_message)
            print(chunk_message, end="", sep="", flush=True)

    return "".join(collected_messages)
