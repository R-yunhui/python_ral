"""工作流 JSON 的本地读写（保存到文件等）"""

import json
import time
from pathlib import Path


def save_workflow(workflow: dict, output_dir: str = "output") -> Path:
    """
    保存工作流 JSON 到本地文件。

    Args:
        workflow: 工作流 JSON 字典
        output_dir: 输出目录，默认 "output"

    Returns:
        保存后的文件路径
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    timestamp = int(time.time())
    filename = f"workflow_{timestamp}.json"
    filepath = output_path / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(workflow, f, ensure_ascii=False, indent=2)
    return filepath
