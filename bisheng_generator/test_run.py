"""简单测试脚本"""

import asyncio
import sys
from pathlib import Path

# 添加当前目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from config.config import config
from core.graph import WorkflowOrchestrator, ModelInitializer
import json
import time

async def test(query: str, test_name: str):
    """测试单个用例"""
    print(f"\n{'='*80}")
    print(f"测试：{test_name}")
    print(f"查询：{query}")
    print(f"{'='*80}")
    
    try:
        orchestrator = WorkflowOrchestrator(config)
        result = await orchestrator.generate(query)
        
        if result.get("status") == "success":
            print(f"[OK] 测试通过")
            metadata = result.get("metadata", {})
            print(f"  - 工作流类型：{metadata.get('intent', {}).get('workflow_type', '未知')}")
            print(f"  - 选中工具数：{metadata.get('tools_count', 0)}")
            print(f"  - 匹配知识库数：{metadata.get('knowledge_count', 0)}")
            
            # 保存工作流
            workflow = result.get("workflow")
            if workflow:
                safe_name = "".join(c for c in test_name if c.isalnum() or c in " _-").strip()
                output_path = Path("test_output")
                output_path.mkdir(exist_ok=True)
                filepath = output_path / f"workflow_{safe_name}.json"
                
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(workflow, f, ensure_ascii=False, indent=2)
                print(f"  - 工作流已保存到：{filepath}")
            return True
        else:
            print(f"[ERROR] 测试失败")
            print(f"  - 错误信息：{result.get('message', '未知错误')}")
            return False
    except Exception as e:
        print(f"[ERROR] 测试异常：{e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    # 测试用例
    tests = [
        ("简单问答", "生成一个简单问答助手"),
        ("天气查询", "创建一个用于天气查询的毕升工作流"),
        ("汇率查询", "做一个查询实时汇率的工作流"),
    ]
    
    print(f"\n{'='*80}")
    print("毕昇工作流生成器 - 快速测试")
    print(f"{'='*80}")
    print(f"LLM: {config.llm_model}")
    print(f"测试用例数：{len(tests)}")
    print(f"{'='*80}")
    
    # 测试 LLM
    try:
        llm = ModelInitializer.get_llm(config)
        print(f"[OK] LLM 初始化成功：{llm.model_name}\n")
    except Exception as e:
        print(f"[ERROR] LLM 初始化失败：{e}\n")
        return
    
    results = []
    for name, query in tests:
        success = await test(query, name)
        results.append((name, success))
    
    # 汇总
    print(f"\n{'='*80}")
    print("测试汇总")
    print(f"{'='*80}")
    passed = sum(1 for _, s in results if s)
    for name, success in results:
        status = "[OK]" if success else "[ERROR]"
        print(f"{status} {name}")
    print(f"\n总计：{passed}/{len(tests)} 通过 ({passed/len(tests)*100:.1f}%)")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(main())
