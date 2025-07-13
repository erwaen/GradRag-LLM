from abc import ABC, abstractmethod
from typing import Generator 
from openai import OpenAI
from config import get_settings
from models.cards import Cards as CardsModel
from typing import Generator,  Literal
from abc import ABC, abstractmethod
from google import genai

settings = get_settings()

class LLMModel(ABC):
    @abstractmethod
    def stream(self, messages, temperature, structure_model) -> Generator[str, None, None]:
        pass

class GPTModel(LLMModel):
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"
    
    def stream(self, messages, temperature, structure_model) -> Generator[str, None, None]:
        stream_args = {
            "model": self.model,
            "input": messages,
            "temperature": temperature,
        }

        if structure_model:
            stream_args["text_format"] = CardsModel

        with self.client.responses.stream(**stream_args) as stream:
            for event in stream:
                if event.type == "response.output_text.delta":
                    print(event.delta, end="")
                    yield event.delta



class GeminiModel:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = "gemini-2.5-flash"

    def stream(self, messages, temperature: float = 0.7, structure_model=None) -> Generator[str, None, None]:
        prompt = "\n".join([msg["content"] for msg in messages])

        # Streaming + Structured Output
        for chunk in self.client.models.generate_content_stream(
            model=self.model_name,
            contents=prompt,
            config={
                "temperature": temperature,
                "response_mime_type": "application/json",
                "response_schema": structure_model if structure_model else None,
            },
        ): 
            print(chunk.text, end = "")
            if chunk.text:
                yield chunk.text


            # for event in stream:
            #     print(event)
            #     if event.type == "response.output_text.delta":
            #         yield event.delta


class LLMFactory:
    @staticmethod
    def create_model(model_type: Literal["gpt", "gemini"]) -> LLMModel:
        if model_type == "gpt":  
            return GPTModel()
        elif model_type == "gemini": 
            return GeminiModel()
        else:
            raise ValueError(f"Unsupported model type: {model_type}")

