"""提示词加载器：从 prompts 目录读取 .md/.txt，支持占位符 {var}"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 默认 prompts 目录：bisheng_generator/prompts
_DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class PromptLoader:
    """从文件加载提示词，文件不存在时返回 None，由调用方使用内置默认值"""

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Args:
            base_dir: 提示词根目录，默认为 bisheng_generator/prompts
        """
        self.base_dir = Path(base_dir) if base_dir else _DEFAULT_PROMPTS_DIR

    def load(self, rel_path: str) -> Optional[str]:
        """
        加载相对路径对应的提示词文件内容。

        Args:
            rel_path: 相对 base_dir 的路径，如 "intent/system.md"

        Returns:
            文件内容（strip 后），文件不存在或读失败时返回 None
        """
        path = self.base_dir / rel_path
        if not path.is_file():
            logger.debug("提示词文件不存在，使用内置默认: %s", rel_path)
            return None
        try:
            text = path.read_text(encoding="utf-8")
            return text.strip()
        except Exception as e:
            logger.warning("读取提示词文件失败 %s: %s", rel_path, e)
            return None


def get_prompt_loader(prompts_dir: Optional[str] = None) -> PromptLoader:
    """获取 PromptLoader 实例。prompts_dir 为空时使用默认目录。"""
    base = Path(prompts_dir) if prompts_dir else None
    return PromptLoader(base_dir=base)
