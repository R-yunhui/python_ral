"""毕昇工作流生成器 - 主入口"""

import asyncio
import logging
import json
import time
from typing import Optional
from pathlib import Path

from config.config import Config, config
from core.graph import WorkflowOrchestrator, ModelInitializer

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format="%(asctime)s - %(name)s - [%(filename)s:%(lineno)d] - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def generate_workflow(
    query: str,
    orchestrator: Optional[WorkflowOrchestrator] = None,
    config_obj: Optional[Config] = None,
) -> dict:
    """
    使用 LangGraph 编排生成毕昇工作流

    Args:
        query: 用户查询
        orchestrator: 已初始化的编排器（若传入则复用；否则临时创建且不加载知识库）
        config_obj: Config 配置对象，orchestrator 为 None 时使用

    Returns:
        工作流生成结果
    """
    if orchestrator is not None:
        return await orchestrator.generate(query)
    # 兼容：未传入编排器时临时创建（不执行 initialize，知识库列表为空）
    temp = WorkflowOrchestrator(config_obj)
    return await temp.generate(query)


def save_workflow(workflow: dict, output_dir: str = "output"):
    """
    保存工作流到文件

    Args:
        workflow: 工作流 JSON
        output_dir: 输出目录
    """
    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 生成文件名（使用时间戳）
    timestamp = int(time.time())
    filename = f"workflow_{timestamp}.json"
    filepath = output_path / filename

    # 保存文件
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(workflow, f, ensure_ascii=False, indent=2)

    return filepath


async def _run_interactive(orchestrator: WorkflowOrchestrator) -> None:
    """交互式循环：使用已初始化的编排器（已加载知识库）"""
    print("\n请输入工作流需求（输入 'q' 退出）：")
    print("示例：")
    print("  - 创建一个深汕招商政策查询助手")
    print("  - 帮我做一个海洋政策咨询工作流")
    print("  - 生成一个简单问答助手\n")

    while True:
        try:
            user_input = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if user_input.lower() == "q":
            print("再见！")
            break

        if not user_input:
            continue

        try:
            print("\n⏳ 正在生成工作流，请稍候...\n")
            result = await orchestrator.generate(user_input)

            print("\n" + "=" * 60)
            print("生成结果：")
            print("=" * 60)

            if result.get("status") == "success":
                print("[OK] 工作流生成成功！\n")

                metadata = result.get("metadata", {})
                if metadata:
                    print(
                        f"工作流类型：{metadata.get('intent', {}).get('workflow_type', '未知')}"
                    )
                    print(f"选中工具数：{metadata.get('tools_count', 0)}")
                    print(f"匹配知识库数：{metadata.get('knowledge_count', 0)}")
                    print()

                workflow = result.get("workflow")
                if workflow:
                    filepath = save_workflow(workflow)
                    print(f"[OK] 工作流已保存到：{filepath}")
                else:
                    print("[WARNING] 工作流数据为空")
            else:
                print("[ERROR] 工作流生成失败")
                print(f"错误信息：{result.get('message', '未知错误')}")

            print("=" * 60 + "\n")

        except Exception as e:
            print(f"\n[ERROR] 生成失败：{e}\n")
            logger.exception("工作流生成出现异常")


def main():
    """主函数"""
    print("=" * 60)
    print("毕昇工作流生成器 v0.2.0 (LangGraph 编排)")
    print("=" * 60)
    print(f"LLM 提供商：{config.llm_provider}")
    print(f"LLM 模型：{config.llm_model}")
    print(f"API 地址：{config.llm_base_url}")
    print(f"毕昇接口：{config.bisheng_base_url}")
    print(f"日志级别：{config.log_level}")
    print("=" * 60)

    try:
        llm = ModelInitializer.get_llm(config)
        print(f"[OK] LLM 初始化成功：{llm.model_name}")
    except Exception as e:
        print(f"[ERROR] LLM 初始化失败：{e}")
        return

    # 创建编排器并在启动时异步加载知识库
    orchestrator = WorkflowOrchestrator(config)

    async def bootstrap() -> None:
        print("\n⏳ 正在从毕昇接口加载知识库列表...")
        await orchestrator.initialize()
        kb_count = len(orchestrator.knowledge_agent.knowledge_catalog)
        print(f"[OK] 知识库加载完成，共 {kb_count} 个\n")
        await _run_interactive(orchestrator)

    asyncio.run(bootstrap())


if __name__ == "__main__":
    main()
