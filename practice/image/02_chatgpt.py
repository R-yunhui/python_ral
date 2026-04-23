from openai import OpenAI
import httpx

client = OpenAI(
    base_url="https://chatgpt.com/backend-api/codex",
)

response = client.images.generate(
    model="gpt-image-2",
    prompt="ClaudeCode 的 tool_search 逻辑 生成一张图片，展示其完整的逻辑流程",
    n=1,
    size="1024x1024",
)
print(response.data[0])
