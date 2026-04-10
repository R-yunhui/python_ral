from langchain_openai import ChatOpenAI


class LLMClient:
    """统一 LLM 调用接口，支持多模型路由"""

    def __init__(self, model: str, api_key: str, base_url: str = ""):
        kwargs: dict = {"model": model, "api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = ChatOpenAI(**kwargs)

    async def invoke(self, prompt: str, max_tokens: int = 500) -> str:
        response = await self._client.ainvoke(prompt)
        return response.content
