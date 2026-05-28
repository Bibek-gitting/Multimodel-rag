import os
from typing import List, cast
from openai import OpenAI, RateLimitError
from openai.types.chat import ChatCompletionMessageParam
from dotenv import load_dotenv
import time
load_dotenv()

class CallLlm():
    def __init__(self, query, context, history: list):
        self.query = query.lower()
        self.context = context
        self.messages = list(history) if history else []
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key= os.getenv("OPENROUTER_API_KEY"),
        )
        self.messages.append({
                        "role": "user",
                        "content": self.context
                    })

    def needs_reasoning(self)-> bool:
        query = self.query
        keywords = [
            "compare", "difference", "why", "how",
            "explain", "analyze", "pros and cons",
            "when to use", "advantages"
        ]

        return any(k in query for k in keywords)
    
    def select_model(self):
        if self.needs_reasoning():
            return self.llm_with_reasoning()   # reasoning model (via OpenRouter)
        else:
            return self.llm_without_reasoning()   # cheap/default model

    def llm_with_reasoning(self, max_retries=3, retry_delay=2):
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="google/gemma-4-26b-a4b-it:free",
                    messages = cast(list[ChatCompletionMessageParam], self.messages),
                    extra_body={"reasoning": {"enabled": True}}
                )

                # Validate response
                if response is None or not response.choices or len(response.choices) == 0:
                    raise RuntimeError("Invalid response from reasoning model: empty or null choices")
                

                # Extract the assistant message with reasoning_details
                msg = response.choices[0].message
                self.messages.append({
                    "role": "assistant",
                    "content": msg.content,
                    "reasoning_details": getattr(msg, "reasoning_details", None)
                })
                return self.messages
            except (RateLimitError, RuntimeError, Exception) as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay*(2 ** attempt))
                else:
                    self.messages.append({
                        "role": "assistant",
                        "content": f"Model unavailable after {max_retries} attempts: {str(e)}"
                    })
                    return self.messages

    def llm_without_reasoning(self, max_retries=2, retry_delay=2):
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="minimax/minimax-m2.5:free",
                    messages = cast(list[ChatCompletionMessageParam], self.messages)
                )
                if not response or not response.choices or len(response.choices) == 0:
                    raise RuntimeError("Invalid response from non-reasoning model: empty or null choices")
                content = response.choices[0].message.content
                self.messages.append({
                    "role": "assistant",
                    "content": content
                })
                if self.fallback_llm_switch(content):
                    self.messages.pop()
                    return self.llm_with_reasoning()
                return self.messages
            except RateLimitError as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay*(2 ** attempt))
                else:
                    raise RuntimeError("Exceeded maximum retries for non-reasoning model due to rate limits") from e
        
    
    def fallback_llm_switch(self, answer: str|None) -> bool:
        """
        Detect if the non-reasoning model failed to answer,
        and a reasoning model should be tried instead.
        """
        if not answer or not answer.strip():
            return True

        fallback_phrases = [
            "not found in context",
            "i don't know",
            "i am not sure",
            "i cannot answer",
            "unable to answer",
            "insufficient information",
            "no information available",
            "cannot determine",
        ]

        return any(phrase in answer.lower() for phrase in fallback_phrases)