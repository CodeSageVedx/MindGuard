from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from src.config import settings

class SentimentResult(BaseModel):
    score: float = Field(..., description="Sentiment score from -1.0 to 1.0")
    label: str = Field(..., description="POSITIVE, NEGATIVE, or NEUTRAL")
    emotion: str = Field(..., description="Primary detected emotion like JOY, SADNESS, ANGER, FEAR, CALM")


# Parser(strict to ensure output is same as schemas)
parser = PydanticOutputParser(pydantic_object=SentimentResult)

llm = ChatGoogleGenerativeAI(
    model=settings.GEMINI_MODEL,
    google_api_key=settings.GEMINI_API_KEY,
    temperature=0.2
)


# Agent instructions
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an emotion and sentiment analysis AI.

Analyze the user's message and return:
1. Sentiment score between -1.0 and 1.0
2. Sentiment label: POSITIVE, NEGATIVE, NEUTRAL
3. Primary emotion (ANGER, JOY, SADNESS, FEAR, CALM, STRESS, etc.)

{format_instructions}
"""
        ),
        ("human", "{text}"),
    ]
).partial(format_instructions=parser.get_format_instructions())


# Chaining prompt, LLM, and parser
sentiment_chain = prompt | llm | parser

async def analyze_sentiment(text: str) -> dict:
    try:
        result: SentimentResult = await sentiment_chain.ainvoke({"text": text})
        return result.model_dump()

    except Exception as e:
        print("Sentiment parsing error:", e)
        return {
            "score": 0.0,
            "label": "NEUTRAL",
            "emotion": "UNKNOWN"
        }

# Brach commit