"""
SessionPilot - 数据模型定义
定义会话、消息、索引等核心数据结构
"""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from enum import Enum


class SessionSource(Enum):
    """会话来源枚举"""
    CLAUDE = "claude"
    CODEX = "codex"
    CURSOR = "cursor"
    WINDSURF = "windsurf"
    UNKNOWN = "unknown"


class MessageRole(Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """单条消息模型"""
    role: str = ""
    content: str = ""
    timestamp: Optional[float] = None
    token_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def to_display_str(self, max_length: int = 200) -> str:
        """生成显示用字符串"""
        preview = self.content[:max_length]
        if len(self.content) > max_length:
            preview += "..."
        return f"[{self.role}] {preview}"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """从字典创建消息对象"""
        return cls(
            role=data.get("role", ""),
            content=data.get("content", ""),
            timestamp=data.get("timestamp"),
            token_count=data.get("token_count", 0)
        )


@dataclass
class Session:
    """会话模型"""
    id: str = ""
    source: str = "unknown"
    title: str = ""
    created_at: Optional[float] = None
    updated_at: Optional[float] = None
    messages: List[Message] = field(default_factory=list)
    file_path: str = ""
    file_size: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result["messages"] = [m.to_dict() for m in self.messages]
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """从字典创建会话对象"""
        messages = []
        for m_data in data.get("messages", []):
            messages.append(Message.from_dict(m_data))
        return cls(
            id=data.get("id", ""),
            source=data.get("source", "unknown"),
            title=data.get("title", ""),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            messages=messages,
            file_path=data.get("file_path", ""),
            file_size=data.get("file_size", 0),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )

    @property
    def message_count(self) -> int:
        """消息数量"""
        return len(self.messages)

    @property
    def total_tokens(self) -> int:
        """估算总Token数"""
        return sum(m.token_count for m in self.messages)

    @property
    def estimated_tokens(self) -> int:
        """基于文本长度估算Token数（约4字符=1token）"""
        total_chars = sum(len(m.content) for m in self.messages)
        return total_chars // 4

    @property
    def duration_minutes(self) -> Optional[float]:
        """会话持续时间（分钟）"""
        if self.created_at and self.updated_at:
            return (self.updated_at - self.created_at) / 60.0
        return None

    @property
    def created_time_str(self) -> str:
        """格式化的创建时间"""
        if self.created_at:
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.created_at))
        return "未知"

    @property
    def updated_time_str(self) -> str:
        """格式化的更新时间"""
        if self.updated_at:
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.updated_at))
        return "未知"

    def get_preview(self, max_length: int = 100) -> str:
        """获取会话预览"""
        if self.messages:
            first_content = self.messages[0].content[:max_length]
            if len(self.messages[0].content) > max_length:
                first_content += "..."
            return first_content
        return "(空会话)"


@dataclass
class IndexEntry:
    """索引条目模型"""
    session_id: str = ""
    source: str = "unknown"
    title: str = ""
    file_path: str = ""
    created_at: Optional[float] = None
    updated_at: Optional[float] = None
    message_count: int = 0
    token_estimate: int = 0
    file_size: int = 0
    tags: List[str] = field(default_factory=list)
    preview: str = ""
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_session(cls, session: Session) -> "IndexEntry":
        """从会话对象创建索引条目"""
        return cls(
            session_id=session.id,
            source=session.source,
            title=session.title,
            file_path=session.file_path,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=session.message_count,
            token_estimate=session.estimated_tokens,
            file_size=session.file_size,
            tags=session.tags,
            preview=session.get_preview(150)
        )


@dataclass
class AnalysisResult:
    """分析结果模型"""
    total_sessions: int = 0
    total_messages: int = 0
    total_tokens_estimate: int = 0
    total_size_bytes: int = 0
    source_distribution: Dict[str, int] = field(default_factory=dict)
    daily_distribution: Dict[str, int] = field(default_factory=dict)
    hourly_distribution: Dict[int, int] = field(default_factory=dict)
    top_keywords: List[tuple] = field(default_factory=list)
    average_messages_per_session: float = 0.0
    average_tokens_per_session: float = 0.0
    oldest_session: Optional[float] = None
    newest_session: Optional[float] = None
    sessions_by_size: List[tuple] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @property
    def total_size_mb(self) -> float:
        """总大小（MB）"""
        return self.total_size_bytes / (1024 * 1024)

    @property
    def total_size_display(self) -> str:
        """人类可读的大小显示"""
        if self.total_size_bytes < 1024:
            return f"{self.total_size_bytes} B"
        elif self.total_size_bytes < 1024 * 1024:
            return f"{self.total_size_bytes / 1024:.2f} KB"
        elif self.total_size_bytes < 1024 * 1024 * 1024:
            return f"{self.total_size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{self.total_size_bytes / (1024 * 1024 * 1024):.2f} GB"


@dataclass
class CleanResult:
    """清理结果模型"""
    deleted_count: int = 0
    freed_bytes: int = 0
    failed_count: int = 0
    errors: List[str] = field(default_factory=list)
    deleted_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @property
    def freed_mb(self) -> float:
        """释放的空间（MB）"""
        return self.freed_bytes / (1024 * 1024)

    @property
    def freed_display(self) -> str:
        """人类可读的释放空间"""
        if self.freed_bytes < 1024:
            return f"{self.freed_bytes} B"
        elif self.freed_bytes < 1024 * 1024:
            return f"{self.freed_bytes / 1024:.2f} KB"
        elif self.freed_bytes < 1024 * 1024 * 1024:
            return f"{self.freed_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{self.freed_bytes / (1024 * 1024 * 1024):.2f} GB"
