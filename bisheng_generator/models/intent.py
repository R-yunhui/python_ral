"""意图模型定义 - 简化版（支持混合类型）"""
from pydantic import BaseModel, Field
from typing import List, Optional


class EnhancedIntent(BaseModel):
    """
    增强的意图描述（简化版）
    
    设计原则：
    1. 只保留核心字段
    2. 支持混合类型（可以同时需要工具和知识库）
    3. 使用布尔标记，而不是枚举
    """
    
    # ========== 核心字段 ==========
    
    original_input: str = Field(
        ..., 
        description="用户原始输入",
        examples=["帮我做个查天气的助手"]
    )
    
    rewritten_input: str = Field(
        ..., 
        description="重写后的清晰描述",
        examples=["创建一个天气查询助手，用户输入城市名称，调用天气 API 返回实时天气信息"]
    )
    
    # ========== 功能标记（支持混合） ==========
    
    needs_tool: bool = Field(
        default=False,
        description="是否需要调用工具/API"
    )
    
    needs_knowledge: bool = Field(
        default=False,
        description="是否需要检索知识库"
    )
    
    # ========== 其他配置 ==========
    
    multi_turn: bool = Field(
        default=True,
        description="是否支持多轮对话"
    )
    
    # ========== 便捷方法 ==========
    
    def get_workflow_type(self) -> str:
        """根据意图标记返回工作流类型"""
        types = []
        if self.needs_tool:
            types.append("工具调用")
        if self.needs_knowledge:
            types.append("知识库检索")
        
        if not types:
            return "基础对话"
        elif len(types) == 1:
            return types[0]
        else:
            return "混合类型：" + " + ".join(types)
    
    def is_mixed(self) -> bool:
        """判断是否是混合类型"""
        count = sum([
            self.needs_tool,
            self.needs_knowledge
        ])
        return count > 1
    
    def to_description(self) -> str:
        """转换为描述字符串"""
        parts = [f"用户需求：{self.rewritten_input}"]
        
        # 功能标记
        features = []
        if self.needs_tool:
            features.append("调用工具")
        if self.needs_knowledge:
            features.append("检索知识库")
        
        if features:
            parts.append(f"功能：{', '.join(features)}")
        
        # 多轮对话
        if self.multi_turn:
            parts.append("支持多轮对话")
        
        return "\n".join(parts)
    
    class Config:
        json_schema_extra = {
            "description": "增强的意图描述（简化版，支持混合类型）",
            "examples": [
                {
                    "original_input": "帮我做个查天气的助手",
                    "rewritten_input": "创建一个天气查询助手，用户输入城市名称，调用天气 API 返回实时天气信息",
                    "needs_tool": True,
                    "needs_knowledge": False,
                    "multi_turn": True
                },
                {
                    "original_input": "做一个基于公司文档的智能客服",
                    "rewritten_input": "创建一个智能客服系统，从公司知识库检索答案，必要时调用工单系统 API",
                    "needs_tool": True,
                    "needs_knowledge": True,
                    "multi_turn": True
                }
            ]
        }
