from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, validator


class MessageRole(str, Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class MessageType(str, Enum):
    """消息类型枚举"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    AUDIO = "audio"

class Message(BaseModel):
    """消息数据模型"""
    id: str | None = Field(None, description="消息ID")
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., min_length=1, max_length=5000, description="消息内容")
    message_type: MessageType = Field(default=MessageType.TEXT, description="消息类型")
    agent_name: str | None = Field(None, max_length=64, description="处理消息的Agent名称")
    metadata: dict | None = Field(default_factory=dict, description="消息元数据")
    created_at: datetime | None = Field(default_factory=datetime.now, description="创建时间")

    @validator('content')
    def validate_content(cls, v, values):
        """根据消息类型验证内容"""
        if 'message_type' in values:
            message_type = values['message_type']
            if message_type == MessageType.TEXT and len(v.strip()) == 0:
                raise ValueError('文本消息内容不能为空')
        return v

class Conversation(BaseModel):
    """对话数据模型"""
    session_id: str = Field(..., description="会话ID")
    user_id: str | None = Field(None, description="用户ID")
    title: str | None = Field(None, description="对话标题")
    status: str = Field(default="active", description="对话状态")
    messages: list[Message] = Field(default_factory=list, description="消息列表")
    metadata: dict | None = Field(default_factory=dict, description="对话元数据")
    created_at: datetime | None = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime | None = Field(default_factory=datetime.now, description="更新时间")

    @property
    def message_count(self) -> int:
        """获取消息数量"""
        return len(self.messages)

    @property
    def last_message(self) -> Message | None:
        """获取最后一条消息"""
        return self.messages[-1] if self.messages else None

    def add_message(self, message: Message):
        """添加消息到对话"""
        self.messages.append(message)
        self.updated_at = datetime.now()

    def get_messages_by_role(self, role: MessageRole) -> list[Message]:
        """根据角色获取消息"""
        return [msg for msg in self.messages if msg.role == role]

    def get_recent_messages(self, limit: int = 10) -> list[Message]:
        """获取最近的消息"""
        return self.messages[-limit:] if self.messages else []

class ConversationCreate(BaseModel):
    """创建对话请求模型"""
    user_id: str | None = Field(None, max_length=64, description="用户ID")
    title: str | None = Field(None, max_length=128, description="对话标题")
    metadata: dict | None = Field(default_factory=dict, description="对话元数据")

class ConversationUpdate(BaseModel):
    """更新对话请求模型"""
    title: str | None = Field(None, description="对话标题")
    status: str | None = Field(None, description="对话状态")
    metadata: dict | None = Field(None, description="对话元数据")

class MessageCreate(BaseModel):
    """创建消息请求模型"""
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., min_length=1, max_length=5000, description="消息内容")
    message_type: MessageType = Field(default=MessageType.TEXT, description="消息类型")
    agent_name: str | None = Field(None, max_length=64, description="处理消息的Agent名称")
    metadata: dict | None = Field(default_factory=dict, description="消息元数据")

class ChatRequest(BaseModel):
    """聊天请求模型"""
    session_id: str = Field(..., min_length=8, max_length=128, description="会话ID")
    message: str = Field(..., min_length=1, max_length=2000, description="用户消息")
    current_agent: str | None = Field(None, max_length=64, description="当前活跃的Agent名称")

class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str = Field(..., description="AI回复内容")
    agent: str = Field(..., description="处理请求的Agent名称")
    session_id: str = Field(..., description="会话ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
