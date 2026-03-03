"""
工作流生成 Agent

使用 agentskills-langchain 加载 bisheng-workflow-generator skill，
结合上下文信息（工具、知识库、用户需求）生成毕昇工作流。
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

from langchain_core.language_models import BaseChatModel
from langchain.agents import create_agent
from agentskills_core import SkillRegistry
from agentskills_fs import LocalFileSystemSkillProvider
from agentskills_langchain import get_tools, get_tools_usage_instructions
from langchain_core.runnables.config import RunnableConfig
from langchain_core.callbacks import UsageMetadataCallbackHandler

from models.intent import EnhancedIntent
from agents.tool_agent import ToolPlan
from agents.knowledge_agent import KnowledgeMatch

logger = logging.getLogger(__name__)


class WorkflowAgent:
    """工作流生成专家"""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        self._tools: Optional[List] = None
        self._usage_callback = UsageMetadataCallbackHandler()

    async def _get_tools(self) -> List:
        """懒加载工具"""
        if self._tools is None:
            self._tools = await self._load_skill()
        return self._tools

    async def _load_skill(self) -> List:
        """
        加载 bisheng-workflow-generator skill

        Returns:
            LangChain tools 列表
        """
        logger.info("加载 bisheng-workflow-generator skill")
        # 设置 skills 根路径（Provider 会在根目录下查找 skill 子目录）
        skills_root = Path(__file__).parent.parent.parent / "skills"
        
        # 创建 Provider 和 Registry
        provider = LocalFileSystemSkillProvider(skills_root)
        registry = SkillRegistry()

        # 注册 skill (异步调用)
        await registry.register("bisheng-workflow-generator", provider)

        # 生成 LangChain 工具
        tools = get_tools(registry)
        logger.info(f"skill 加载完成，获取到 {len(tools)} 个工具")

        return tools

    async def generate_workflow(
        self,
        intent: EnhancedIntent,
        tool_plan: ToolPlan,
        knowledge_match: KnowledgeMatch,
    ) -> Dict[str, Any]:
        """
        生成毕昇工作流

        Args:
            intent: 用户意图
            tool_plan: 工具计划
            knowledge_match: 知识库匹配结果

        Returns:
            毕昇工作流 JSON 字典
        """
        logger.info("开始生成工作流")
        
        # 准备工作上下文信息
        tools_info = self._format_tools_info(tool_plan)
        knowledge_info = self._format_knowledge_info(knowledge_match)

        # 生成系统提示
        logger.info("获取 skills 目录和工具使用说明")
        catalog = await self._get_skills_catalog()
        instructions = get_tools_usage_instructions()

        system_prompt = f"""
                    你是一个专业的毕昇工作流生成专家，可以使用以下技能和数据完成毕升工作流的创建：

                    {catalog}

                    {instructions}

                    【当前上下文信息】
                    用户需求：{intent.rewritten_input}

                    可用工具：
                    {tools_info}

                    可用知识库：
                    {knowledge_info}

                    【输出要求】
                    - 你必须始终以 JSON 格式返回最终结果
                    - JSON 必须使用 ```json 代码块包裹
                    - 确保 JSON 格式正确，可以被 json.loads() 解析
                    - 如果任务有结构化数据，请放在 JSON 对象中
                """

        # 创建 agent
        logger.info("创建工作流生成 Agent")
        agent = create_agent(
            model=self.llm,
            tools=await self._get_tools(),
            system_prompt=system_prompt,
            debug=False,
        )

        # 运行 agent
        logger.info("调用 LLM 生成工作流")
        result = await agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": f"请根据提供的上下文信息，生成一个完整的毕昇工作流。用户需求：{intent.rewritten_input}",
                    }
                ]
            },
            config=RunnableConfig(callbacks=[self._usage_callback])
        )
        
        logger.info(f"工作流生成完成，使用情况：{self._usage_callback.usage_metadata}")

        # 提取 JSON
        content = result["messages"][-1].content
        workflow_json = self._extract_json(content)

        if not workflow_json:
            logger.warning("工作流 JSON 提取失败")
            # 如果生成失败，返回错误信息
            return {"error": "工作流生成失败", "content": content}

        logger.info(f"工作流生成成功，包含 {len(workflow_json)} 个节点")
        return workflow_json

    def _format_tools_info(self, tool_plan: ToolPlan) -> str:
        """格式化工具信息"""
        if not tool_plan.selected_tools:
            return "无工具调用需求"

        lines = []
        for tool in tool_plan.selected_tools:
            lines.append(f"- tool_key: {tool.tool_key}")
            lines.append(f"  名称：{tool.name}")
            lines.append(f"  描述：{tool.desc}")
            if tool.parameters:
                params = [p.get("name") for p in tool.parameters]
                lines.append(f"  参数：{params}")

        return "\n".join(lines)

    def _format_knowledge_info(self, knowledge_match: KnowledgeMatch) -> str:
        """格式化知识库信息"""
        if not knowledge_match.matched_knowledge_bases:
            return "无知识库检索需求"

        lines = []
        for kb in knowledge_match.matched_knowledge_bases:
            lines.append(f"- ID: {kb.id}")
            lines.append(f"  名称：{kb.name}")
            lines.append(f"  描述：{kb.desc}")
            if kb.extra:
                collection = kb.extra.get("collection_name", "")
                if collection:
                    lines.append(f"  collection: {collection}")

        return "\n".join(lines)

    async def _get_skills_catalog(self) -> str:
        """获取 skills 目录"""
        try:
            skills_path = Path(__file__).parent.parent.parent / "skills"
            provider = LocalFileSystemSkillProvider(skills_path)
            registry = SkillRegistry()
            await registry.register("bisheng-workflow-generator", provider)
            return await registry.get_skills_catalog(format="xml")
        except Exception as e:
            return f"获取 skills 目录失败：{e}"

    def _extract_json(self, content: str) -> Optional[Dict[str, Any]]:
        """从内容中提取 JSON"""
        if not content.strip():
            return None

        # 尝试提取 ```json 代码块
        json_block = re.search(r"```json\s*([\s\S]*?)```", content)
        if json_block:
            json_str = json_block.group(1).strip()
        else:
            # 尝试提取任意 ``` 代码块
            code_block = re.search(r"```\s*([\s\S]*?)```", content)
            if code_block:
                json_str = code_block.group(1).strip()
            else:
                # 尝试查找第一个 { 到最后一个 }
                json_match = re.search(r"\{[\s\S]*\}", content)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = content.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
