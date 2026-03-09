"""提示词加载器：从 prompts 目录读取 .md/.txt，支持通过 index.yaml 集中管理路径"""

import logging
from pathlib import Path
from typing import Dict, Optional

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class PromptLoader:
    """从文件加载提示词。

    支持两种使用方式：
    - ``load(rel_path)``：直接按相对路径加载（向后兼容）
    - ``get(agent, key)``：通过 index.yaml 中定义的 agent/key 映射加载（推荐）
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir) if base_dir else _DEFAULT_PROMPTS_DIR
        self._index: Dict[str, Dict[str, str]] = self._load_index()

    def _load_index(self) -> Dict[str, Dict[str, str]]:
        index_path = self.base_dir / "index.yaml"
        if not index_path.is_file():
            return {}
        try:
            data = yaml.safe_load(index_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {}
            return {
                k: v for k, v in data.items()
                if isinstance(v, dict)
            }
        except Exception as e:
            logger.warning("解析 index.yaml 失败: %s", e)
            return {}

    def get(self, agent: str, key: str) -> Optional[str]:
        """通过 agent 名和 key 获取提示词内容。

        路径从 index.yaml 中查找，例如 ``get("intent", "system")``
        会读取 index.yaml 中 ``intent.system`` 对应的文件。
        """
        rel_path = self._index.get(agent, {}).get(key)
        if not rel_path:
            logger.debug("index.yaml 中未找到 %s.%s", agent, key)
            return None
        return self.load(rel_path)

    def load(self, rel_path: str) -> Optional[str]:
        """按相对路径加载提示词文件内容（向后兼容）。"""
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


_loader_cache: Dict[str, PromptLoader] = {}


def get_prompt_loader(prompts_dir: Optional[str] = None) -> PromptLoader:
    """获取 PromptLoader 实例（同一 prompts_dir 只创建一次）。"""
    cache_key = prompts_dir or ""
    if cache_key not in _loader_cache:
        base = Path(prompts_dir) if prompts_dir else None
        _loader_cache[cache_key] = PromptLoader(base_dir=base)
    return _loader_cache[cache_key]
