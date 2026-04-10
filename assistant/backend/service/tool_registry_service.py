from pydantic import BaseModel


class ToolDefinition(BaseModel):
    name: str
    description: str
    is_write: bool
    input_schema: dict


class ToolNotFoundError(Exception):
    pass


class ToolRegistry:
    """工具注册中心，限制 LLM 权限边界"""
    _tools: dict[str, ToolDefinition] = {}

    @classmethod
    def register(cls, tool: ToolDefinition):
        cls._tools[tool.name] = tool

    @classmethod
    def validate_tool_call(cls, tool_name: str, params: dict) -> bool:
        """校验工具是否已注册"""
        if tool_name not in cls._tools:
            raise ToolNotFoundError(f"Tool '{tool_name}' is not registered")
        # TODO: 加上 params schema 校验
        return True

    @classmethod
    def get_tool(cls, tool_name: str) -> ToolDefinition | None:
        return cls._tools.get(tool_name)


# 注册只读工具
ToolRegistry.register(ToolDefinition(
    name="structured_query",
    description="查询 SQLite 财务数据",
    is_write=False,
    input_schema={"type": "object"},
))
ToolRegistry.register(ToolDefinition(
    name="resolve_category",
    description="分类标准化：将用户输入的自然语言分类映射为标准分类",
    is_write=False,
    input_schema={"type": "object"},
))
ToolRegistry.register(ToolDefinition(
    name="long_memory",
    description="查询/写入 mem0 长期记忆",
    is_write=True,
    input_schema={"type": "object"},
))

# 注册写入工具
ToolRegistry.register(ToolDefinition(
    name="structured_store",
    description="写入 SQLite 收支/预算记录",
    is_write=True,
    input_schema={"type": "object"},
))
