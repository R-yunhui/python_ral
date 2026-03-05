"""进度事件模型定义 - 支持实时推送 Agent 执行情况"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class ProgressEventType(str, Enum):
    """进度事件类型枚举"""
    
    START = "start"
    """开始生成工作流"""
    
    AGENT_START = "agent_start"
    """Agent 开始执行"""
    
    AGENT_COMPLETE = "agent_complete"
    """Agent 执行完成"""
    
    AGENT_ERROR = "agent_error"
    """Agent 执行失败"""
    
    COMPLETE = "complete"
    """全部完成"""
    
    ERROR = "error"
    """生成失败"""


class AgentName(str, Enum):
    """Agent 名称枚举"""
    
    INTENT_UNDERSTANDING = "intent_understanding"
    """意图理解 Agent"""
    
    TOOL_SELECTION = "tool_selection"
    """工具选择 Agent"""
    
    KNOWLEDGE_MATCHING = "knowledge_matching"
    """知识库匹配 Agent"""
    
    WORKFLOW_GENERATION = "workflow_generation"
    """工作流生成 Agent"""

    IMPORT = "import"
    """导入到毕昇平台"""


class ProgressEvent(BaseModel):
    """
    进度事件模型
    
    用于实时推送工作流生成过程中的各个阶段状态
    """
    
    # ========== 核心字段 ==========
    
    event_type: ProgressEventType = Field(
        ...,
        description="事件类型",
        examples=["start", "agent_complete", "complete"]
    )
    
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="事件时间戳 (ISO 格式)",
        examples=["2026-03-03T21:18:11.623Z"]
    )
    
    # ========== Agent 相关信息 ==========
    
    agent_name: Optional[AgentName] = Field(
        default=None,
        description="Agent 名称（仅 agent_* 类型事件需要）",
        examples=["intent_understanding", "tool_selection"]
    )
    
    # ========== 数据载荷 ==========
    
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="事件数据载荷",
        examples=[
            {"workflow_type": "工具调用", "needs_tool": True},
            {"selected_tools": ["天气 API", "政策搜索"]}
        ]
    )
    
    # ========== 人类可读消息 ==========
    
    message: str = Field(
        ...,
        description="人类可读的事件描述",
        examples=["✅ 意图理解完成：工作流类型=工具调用"]
    )
    
    # ========== 元数据 ==========
    
    progress: Optional[float] = Field(
        default=None,
        description="进度百分比 (0-100)",
        examples=[25.0, 50.0, 75.0, 100.0],
        ge=0,
        le=100
    )
    
    duration_ms: Optional[float] = Field(
        default=None,
        description="Agent 执行耗时 (毫秒)",
        examples=[2100.5, 1800.3]
    )
    
    # ========== 错误信息 ==========
    
    error: Optional[str] = Field(
        default=None,
        description="错误信息（仅 error 和 agent_error 类型需要）",
        examples=["意图理解失败：LLM 调用超时"]
    )
    
    # ========== 便捷方法 ==========
    
    @classmethod
    def create_start_event(cls, user_input: str) -> "ProgressEvent":
        """创建开始事件"""
        return cls(
            event_type=ProgressEventType.START,
            message=f"🚀 开始生成工作流",
            data={"user_input": user_input[:50] + "..." if len(user_input) > 50 else user_input},
            progress=0.0
        )
    
    @classmethod
    def create_agent_start_event(cls, agent_name: AgentName) -> "ProgressEvent":
        """创建 Agent 开始执行事件"""
        agent_display_names = {
            AgentName.INTENT_UNDERSTANDING: "意图理解",
            AgentName.TOOL_SELECTION: "工具选择",
            AgentName.KNOWLEDGE_MATCHING: "知识库匹配",
            AgentName.WORKFLOW_GENERATION: "工作流生成",
            AgentName.IMPORT: "导入到毕昇",
        }
        return cls(
            event_type=ProgressEventType.AGENT_START,
            agent_name=agent_name,
            message=f"⏳ 正在执行：{agent_display_names.get(agent_name, agent_name)}",
            progress=cls._get_agent_progress(agent_name) - 12.5
        )
    
    @classmethod
    def create_agent_complete_event(
        cls,
        agent_name: AgentName,
        data: Dict[str, Any],
        duration_ms: float
    ) -> "ProgressEvent":
        """创建 Agent 执行完成事件"""
        agent_display_names = {
            AgentName.INTENT_UNDERSTANDING: "意图理解",
            AgentName.TOOL_SELECTION: "工具选择",
            AgentName.KNOWLEDGE_MATCHING: "知识库匹配",
            AgentName.WORKFLOW_GENERATION: "工作流生成",
            AgentName.IMPORT: "导入到毕昇",
        }
        
        # 根据 Agent 类型生成不同的消息
        message = cls._generate_complete_message(agent_name, data)
        
        return cls(
            event_type=ProgressEventType.AGENT_COMPLETE,
            agent_name=agent_name,
            message=message,
            data=data,
            duration_ms=duration_ms,
            progress=cls._get_agent_progress(agent_name)
        )
    
    @classmethod
    def create_agent_error_event(
        cls,
        agent_name: AgentName,
        error: str,
        duration_ms: float
    ) -> "ProgressEvent":
        """创建 Agent 执行失败事件"""
        agent_display_names = {
            AgentName.INTENT_UNDERSTANDING: "意图理解",
            AgentName.TOOL_SELECTION: "工具选择",
            AgentName.KNOWLEDGE_MATCHING: "知识库匹配",
            AgentName.WORKFLOW_GENERATION: "工作流生成",
            AgentName.IMPORT: "导入到毕昇",
        }
        
        return cls(
            event_type=ProgressEventType.AGENT_ERROR,
            agent_name=agent_name,
            message=f"❌ {agent_display_names.get(agent_name, agent_name)}失败",
            error=error,
            duration_ms=duration_ms,
            progress=cls._get_agent_progress(agent_name) - 12.5
        )
    
    @classmethod
    def create_complete_event(cls, workflow: Dict[str, Any], metadata: Dict[str, Any]) -> "ProgressEvent":
        """创建完成事件"""
        return cls(
            event_type=ProgressEventType.COMPLETE,
            message="✅ 工作流生成完成！",
            data={
                "workflow": workflow,
                "metadata": metadata
            },
            progress=100.0
        )
    
    @classmethod
    def create_error_event(cls, error: str) -> "ProgressEvent":
        """创建错误事件"""
        return cls(
            event_type=ProgressEventType.ERROR,
            message="❌ 生成失败",
            error=error,
            progress=0.0
        )
    
    @staticmethod
    def _get_agent_progress(agent_name: AgentName) -> float:
        """获取 Agent 对应的进度百分比"""
        progress_map = {
            AgentName.INTENT_UNDERSTANDING: 25.0,
            AgentName.TOOL_SELECTION: 50.0,
            AgentName.KNOWLEDGE_MATCHING: 75.0,
            AgentName.WORKFLOW_GENERATION: 95.0,
            AgentName.IMPORT: 100.0,
        }
        return progress_map.get(agent_name, 0.0)
    
    @staticmethod
    def _generate_complete_message(agent_name: AgentName, data: Dict[str, Any]) -> str:
        """根据 Agent 类型生成完成消息"""
        if agent_name == AgentName.INTENT_UNDERSTANDING:
            workflow_type = data.get("workflow_type", "未知")
            return f"✅ 意图理解完成：工作流类型={workflow_type}"
        
        elif agent_name == AgentName.TOOL_SELECTION:
            tools_count = data.get("tools_count", 0)
            return f"✅ 工具选择完成：选中 {tools_count} 个工具"
        
        elif agent_name == AgentName.KNOWLEDGE_MATCHING:
            knowledge_count = data.get("knowledge_count", 0)
            return f"✅ 知识库匹配完成：匹配到 {knowledge_count} 个知识库"
        
        elif agent_name == AgentName.WORKFLOW_GENERATION:
            return "✅ 工作流生成完成"
        
        elif agent_name == AgentName.IMPORT:
            flow_id = data.get("flow_id", "")
            return f"✅ 已导入到毕昇：flow_id={flow_id}" if flow_id else "✅ 导入到毕昇完成"
        
        return f"✅ {agent_name} 完成"
    
    class Config:
        json_schema_extra = {
            "description": "进度事件模型，用于实时推送工作流生成过程",
            "examples": [
                {
                    "event_type": "agent_complete",
                    "agent_name": "intent_understanding",
                    "timestamp": "2026-03-03T21:18:11.623Z",
                    "message": "✅ 意图理解完成：工作流类型=工具调用",
                    "data": {
                        "workflow_type": "工具调用",
                        "needs_tool": True,
                        "needs_knowledge": True
                    },
                    "progress": 25.0,
                    "duration_ms": 2100.5
                }
            ]
        }


class StreamResponse(BaseModel):
    """
    SSE 流式响应包装器
    
    用于将 ProgressEvent 序列化为 SSE 格式
    """
    
    event: ProgressEvent
    
    def to_sse(self) -> str:
        """转换为 SSE 格式"""
        import json
        
        # SSE 格式：
        # event: progress
        # data: {"event_type": "...", ...}
        #
        
        event_data = self.event.model_dump(mode="json")
        return f"event: progress\ndata: {json.dumps(event_data, ensure_ascii=False)}\n\n"
