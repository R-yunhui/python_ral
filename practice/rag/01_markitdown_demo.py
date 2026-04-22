import os

from dotenv import load_dotenv

from pathlib import Path
from markitdown import MarkItDown
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
)

md = MarkItDown(llm_client=client, llm_model="qwen3.5-plus", enable_plugins=True)

pdf_path = Path(__file__).parent / "example_doc" / "WBTL-QI043-FD002-2025 差旅费管理制度 .pdf"

result = md.convert(str(pdf_path))

print(result.text_content)
