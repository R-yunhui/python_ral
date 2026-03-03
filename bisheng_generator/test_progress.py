"""测试实时进度推送功能"""

import asyncio
import json
from models.progress import ProgressEvent, ProgressEventType, AgentName


async def test_progress_callback(event: ProgressEvent):
    """测试用的进度回调函数"""
    print(f"\n{'='*60}")
    print(f"收到进度事件:")
    print(f"  类型：{event.event_type.value}")
    print(f"  时间：{event.timestamp}")
    
    if event.agent_name:
        print(f"  Agent: {event.agent_name.value}")
    
    print(f"  消息：{event.message}")
    print(f"  进度：{event.progress}%")
    
    if event.duration_ms:
        print(f"  耗时：{event.duration_ms / 1000:.2f}秒")
    
    if event.data:
        print(f"  数据：{json.dumps(event.data, ensure_ascii=False, indent=2)}")
    
    if event.error:
        print(f"  错误：{event.error}")


async def test_progress_events():
    """测试各种进度事件的创建"""
    print("\n" + "="*60)
    print("测试进度事件创建")
    print("="*60)
    
    # 测试开始事件
    print("\n[测试 1] 创建开始事件")
    start_event = ProgressEvent.create_start_event("创建一个天气查询助手")
    await test_progress_callback(start_event)
    
    # 测试 Agent 开始事件
    print("\n[测试 2] 创建 Agent 开始事件（意图理解）")
    agent_start = ProgressEvent.create_agent_start_event(AgentName.INTENT_UNDERSTANDING)
    await test_progress_callback(agent_start)
    
    # 测试 Agent 完成事件
    print("\n[测试 3] 创建 Agent 完成事件（意图理解）")
    agent_complete = ProgressEvent.create_agent_complete_event(
        agent_name=AgentName.INTENT_UNDERSTANDING,
        data={
            "workflow_type": "工具调用",
            "needs_tool": True,
            "needs_knowledge": False,
            "rewritten_input": "创建一个天气查询助手，用户输入城市名称，返回实时天气信息"
        },
        duration_ms=2100.5
    )
    await test_progress_callback(agent_complete)
    
    # 测试 Agent 完成事件（工具选择）
    print("\n[测试 4] 创建 Agent 完成事件（工具选择）")
    tool_complete = ProgressEvent.create_agent_complete_event(
        agent_name=AgentName.TOOL_SELECTION,
        data={
            "tools_count": 3,
            "selected_tools": [
                {"name": "天气 API", "description": "查询实时天气"},
                {"name": "政策搜索", "description": "搜索政策信息"},
                {"name": "新闻 API", "description": "获取最新新闻"}
            ]
        },
        duration_ms=1800.3
    )
    await test_progress_callback(tool_complete)
    
    # 测试 Agent 完成事件（知识库匹配）
    print("\n[测试 5] 创建 Agent 完成事件（知识库匹配）")
    knowledge_complete = ProgressEvent.create_agent_complete_event(
        agent_name=AgentName.KNOWLEDGE_MATCHING,
        data={
            "knowledge_count": 2,
            "matched_knowledge_bases": [
                {"name": "深汕政策库", "description": "深汕特别合作区政策文件"},
                {"name": "海洋政策库", "description": "海洋相关政策文件"}
            ]
        },
        duration_ms=500.2
    )
    await test_progress_callback(knowledge_complete)
    
    # 测试 Agent 完成事件（工作流生成）
    print("\n[测试 6] 创建 Agent 完成事件（工作流生成）")
    workflow_complete = ProgressEvent.create_agent_complete_event(
        agent_name=AgentName.WORKFLOW_GENERATION,
        data={"workflow_generated": True},
        duration_ms=3200.8
    )
    await test_progress_callback(workflow_complete)
    
    # 测试完成事件
    print("\n[测试 7] 创建完成事件")
    complete_event = ProgressEvent.create_complete_event(
        workflow={"nodes": [], "edges": []},
        metadata={
            "intent": {"workflow_type": "工具调用"},
            "tools_count": 3,
            "knowledge_count": 2
        }
    )
    await test_progress_callback(complete_event)
    
    # 测试错误事件
    print("\n[测试 8] 创建错误事件")
    error_event = ProgressEvent.create_error_event("LLM 调用超时")
    await test_progress_callback(error_event)
    
    # 测试 Agent 错误事件
    print("\n[测试 9] 创建 Agent 错误事件")
    agent_error = ProgressEvent.create_agent_error_event(
        agent_name=AgentName.TOOL_SELECTION,
        error="工具库为空，无法选择工具",
        duration_ms=100.5
    )
    await test_progress_callback(agent_error)
    
    print("\n" + "="*60)
    print("所有测试完成！")
    print("="*60)


async def test_workflow_orchestrator():
    """测试编排器的进度推送功能"""
    print("\n" + "="*60)
    print("测试编排器进度推送")
    print("="*60)
    
    try:
        from core.graph import WorkflowOrchestrator
        from config.config import config
        
        # 创建编排器
        print("\n初始化编排器...")
        orchestrator = WorkflowOrchestrator(
            config_obj=config,
            progress_callback=test_progress_callback
        )
        print("编排器初始化完成")
        
        # 测试生成
        test_query = "创建一个简单的天气查询助手"
        print(f"\n开始生成：{test_query}")
        
        result = await orchestrator.generate_with_progress(
            user_input=test_query,
            progress_callback=test_progress_callback
        )
        
        print("\n生成结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except ImportError as e:
        print(f"\n跳过编排器测试（依赖未安装）：{e}")
    except Exception as e:
        print(f"\n编排器测试失败：{e}")


async def main():
    """主函数"""
    print("\n" + "🚀"*30)
    print("毕昇工作流生成器 - 实时进度推送测试")
    print("🚀"*30)
    
    # 测试进度事件创建
    await test_progress_events()
    
    # 测试编排器
    # await test_workflow_orchestrator()
    
    print("\n✅ 所有测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
