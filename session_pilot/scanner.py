"""
SessionPilot - 会话扫描器
自动扫描各AI编码助手的数据目录，解析会话文件
"""

import os
import re
import json
import time
from typing import List, Optional, Dict, Any, Tuple

from .models import Session, Message
from .utils import (
    get_source_dirs, SOURCE_EXTENSIONS, SOURCE_PATTERNS,
    safe_read_file, safe_read_json, get_file_size, get_file_mtime,
    get_file_ctime, generate_id, estimate_tokens, ensure_dir
)


class SessionScanner:
    """会话扫描器 - 扫描并解析AI会话文件"""

    def __init__(self, custom_dirs: Optional[Dict[str, List[str]]] = None):
        """
        初始化扫描器

        Args:
            custom_dirs: 自定义数据目录映射 {source: [dir_paths]}
        """
        self.custom_dirs = custom_dirs or {}
        self._scan_stats = {
            "files_scanned": 0,
            "files_parsed": 0,
            "files_failed": 0,
            "sessions_found": 0,
        }

    def get_scan_dirs(self, source: str) -> List[str]:
        """获取指定来源的扫描目录列表"""
        dirs = self.custom_dirs.get(source, [])
        if not dirs:
            dirs = get_source_dirs(source)
        # 过滤存在的目录
        return [d for d in dirs if os.path.isdir(d)]

    def scan_all(self, sources: Optional[List[str]] = None) -> List[Session]:
        """
        扫描所有来源的会话

        Args:
            sources: 要扫描的来源列表，None表示扫描所有

        Returns:
            解析后的会话列表
        """
        all_sessions = []
        if sources is None:
            sources = ["claude", "codex", "cursor", "windsurf"]

        for source in sources:
            sessions = self.scan_source(source)
            all_sessions.extend(sessions)

        return all_sessions

    def scan_source(self, source: str) -> List[Session]:
        """
        扫描指定来源的会话

        Args:
            source: 来源名称 (claude/codex/cursor/windsurf)

        Returns:
            解析后的会话列表
        """
        sessions = []
        dirs = self.get_scan_dirs(source)

        if not dirs:
            return sessions

        for dir_path in dirs:
            file_sessions = self._scan_directory(dir_path, source)
            sessions.extend(file_sessions)

        return sessions

    def scan_directory(self, dir_path: str, source: str = "unknown") -> List[Session]:
        """
        扫描指定目录

        Args:
            dir_path: 目录路径
            source: 来源名称

        Returns:
            解析后的会话列表
        """
        if not os.path.isdir(dir_path):
            return []
        return self._scan_directory(dir_path, source)

    def _scan_directory(self, dir_path: str, source: str) -> List[Session]:
        """递归扫描目录中的会话文件"""
        sessions = []
        extensions = SOURCE_EXTENSIONS.get(source, [".json", ".jsonl"])
        patterns = SOURCE_PATTERNS.get(source, [r".*\.jsonl?$"])

        # 编译正则模式
        compiled_patterns = [re.compile(p) for p in patterns]

        try:
            for root, dirs, files in os.walk(dir_path):
                for filename in files:
                    filepath = os.path.join(root, filename)

                    # 检查文件扩展名
                    _, ext = os.path.splitext(filename)
                    if ext.lower() not in extensions:
                        continue

                    # 检查文件名模式
                    matched = any(p.match(filename) for p in compiled_patterns)
                    if not matched:
                        continue

                    self._scan_stats["files_scanned"] += 1

                    # 解析文件
                    session = self._parse_file(filepath, source)
                    if session:
                        sessions.append(session)
                        self._scan_stats["files_parsed"] += 1
                        self._scan_stats["sessions_found"] += 1
                    else:
                        self._scan_stats["files_failed"] += 1

        except PermissionError:
            pass

        return sessions

    def _parse_file(self, filepath: str, source: str) -> Optional[Session]:
        """
        解析单个会话文件

        根据来源不同，使用不同的解析策略
        """
        try:
            file_size = get_file_size(filepath)
            if file_size == 0:
                return None

            # 尝试读取JSON
            data = safe_read_json(filepath)

            if data is not None:
                if isinstance(data, list):
                    # JSONL格式（列表）
                    return self._parse_jsonl_data(data, filepath, source)
                elif isinstance(data, dict):
                    # JSON格式（字典）
                    return self._parse_json_data(data, filepath, source)
            else:
                # 尝试按JSONL行格式解析
                return self._parse_jsonl_file(filepath, source)

        except Exception:
            return None

        return None

    def _parse_json_data(self, data: Dict[str, Any], filepath: str, source: str) -> Optional[Session]:
        """解析JSON格式的会话数据"""
        messages = []
        title = ""
        created_at = None
        updated_at = None
        tags = []
        metadata = {}

        # 尝试多种常见字段名提取消息
        msg_fields = ["messages", "conversation", "history", "chat", "dialogue", "turns"]
        messages_data = None
        for field in msg_fields:
            if field in data and isinstance(data[field], list):
                messages_data = data[field]
                break

        if messages_data:
            for item in messages_data:
                if isinstance(item, dict):
                    msg = self._extract_message(item)
                    if msg:
                        messages.append(msg)
                elif isinstance(item, str):
                    messages.append(Message(role="unknown", content=item))

        # 提取标题
        title_fields = ["title", "name", "subject", "summary", "topic", "description"]
        for field in title_fields:
            if field in data and isinstance(data[field], str):
                title = data[field]
                break

        # 如果没有标题，使用第一条消息的前50个字符
        if not title and messages:
            title = messages[0].content[:50]
            if len(messages[0].content) > 50:
                title += "..."

        # 提取时间
        time_fields = [
            ("created_at", "createdAt", "create_time", "createTime", "started_at"),
            ("updated_at", "updatedAt", "update_time", "updateTime", "last_active"),
        ]
        for candidates in time_fields:
            for field in candidates:
                if field in data:
                    val = data[field]
                    if isinstance(val, (int, float)):
                        if created_at is None and "create" in field.lower() or "start" in field.lower():
                            created_at = float(val)
                        elif updated_at is None:
                            updated_at = float(val)
                    elif isinstance(val, str):
                        ts = self._parse_time_value(val)
                        if ts:
                            if created_at is None:
                                created_at = ts
                            elif updated_at is None:
                                updated_at = ts

        # 提取标签
        if "tags" in data and isinstance(data["tags"], list):
            tags = [str(t) for t in data["tags"]]

        # 存储原始元数据（排除已提取的字段）
        skip_keys = set(msg_fields + title_fields)
        for key in ["created_at", "createdAt", "updated_at", "updatedAt", "tags"]:
            skip_keys.add(key)
        metadata = {k: v for k, v in data.items() if k not in skip_keys}

        # 如果没有时间信息，使用文件时间
        if created_at is None:
            created_at = get_file_ctime(filepath)
        if updated_at is None:
            updated_at = get_file_mtime(filepath)

        session_id = generate_id(source, filepath)

        return Session(
            id=session_id,
            source=source,
            title=title,
            created_at=created_at,
            updated_at=updated_at,
            messages=messages,
            file_path=filepath,
            file_size=get_file_size(filepath),
            tags=tags,
            metadata=metadata
        )

    def _parse_jsonl_data(self, data: List[Any], filepath: str, source: str) -> Optional[Session]:
        """解析JSONL格式（作为列表）的会话数据"""
        messages = []
        title = ""
        created_at = None
        updated_at = None

        for item in data:
            if isinstance(item, dict):
                # 检查是否是消息
                msg = self._extract_message(item)
                if msg:
                    messages.append(msg)
                    continue

                # 检查是否包含会话元信息
                if "title" in item and not title:
                    title = str(item["title"])
                if "created_at" in item and created_at is None:
                    created_at = self._parse_time_value(item["created_at"])
                if "updated_at" in item and updated_at is None:
                    updated_at = self._parse_time_value(item["updated_at"])

            elif isinstance(item, str):
                messages.append(Message(role="unknown", content=item))

        if not messages:
            return None

        if not title and messages:
            title = messages[0].content[:50]
            if len(messages[0].content) > 50:
                title += "..."

        if created_at is None:
            created_at = get_file_ctime(filepath)
        if updated_at is None:
            updated_at = get_file_mtime(filepath)

        session_id = generate_id(source, filepath)

        return Session(
            id=session_id,
            source=source,
            title=title,
            created_at=created_at,
            updated_at=updated_at,
            messages=messages,
            file_path=filepath,
            file_size=get_file_size(filepath),
        )

    def _parse_jsonl_file(self, filepath: str, source: str) -> Optional[Session]:
        """按行解析JSONL文件"""
        content = safe_read_file(filepath)
        if not content:
            return None

        messages = []
        title = ""
        created_at = None
        updated_at = None

        for line_no, line in enumerate(content.strip().split("\n")):
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                # 非JSON行，作为消息内容
                messages.append(Message(role="unknown", content=line))
                continue

            if isinstance(obj, dict):
                msg = self._extract_message(obj)
                if msg:
                    messages.append(msg)
                    continue

                if "title" in obj and not title:
                    title = str(obj["title"])
                if "created_at" in obj and created_at is None:
                    created_at = self._parse_time_value(obj["created_at"])
                if "updated_at" in obj and updated_at is None:
                    updated_at = self._parse_time_value(obj["updated_at"])

        if not messages:
            return None

        if not title and messages:
            title = messages[0].content[:50]
            if len(messages[0].content) > 50:
                title += "..."

        if created_at is None:
            created_at = get_file_ctime(filepath)
        if updated_at is None:
            updated_at = get_file_mtime(filepath)

        session_id = generate_id(source, filepath)

        return Session(
            id=session_id,
            source=source,
            title=title,
            created_at=created_at,
            updated_at=updated_at,
            messages=messages,
            file_path=filepath,
            file_size=get_file_size(filepath),
        )

    def _extract_message(self, obj: Dict[str, Any]) -> Optional[Message]:
        """从字典中提取消息"""
        # 检测角色字段
        role = ""
        role_fields = ["role", "type", "speaker", "from", "author", "actor"]
        for field in role_fields:
            if field in obj:
                val = str(obj[field]).lower()
                if val in ("user", "human", "customer", "client"):
                    role = "user"
                elif val in ("system", "instruction"):
                    role = "system"
                elif val in ("assistant", "ai", "bot", "model"):
                    role = "assistant"
                else:
                    role = val
                break

        # 检测内容字段
        content = ""
        content_fields = ["content", "text", "message", "body", "value", "output", "input", "prompt", "response"]
        for field in content_fields:
            if field in obj:
                val = obj[field]
                if isinstance(val, str):
                    content = val
                elif isinstance(val, list):
                    # 处理内容块列表
                    parts = []
                    for block in val:
                        if isinstance(block, dict) and "text" in block:
                            parts.append(str(block["text"]))
                        elif isinstance(block, str):
                            parts.append(block)
                    content = "\n".join(parts)
                elif isinstance(val, dict):
                    # 处理嵌套内容
                    if "text" in val:
                        content = str(val["text"])
                    else:
                        content = json.dumps(val, ensure_ascii=False)
                if content:
                    break

        if not content:
            return None

        # 提取时间戳
        timestamp = None
        ts_fields = ["timestamp", "time", "created_at", "createdAt", "ts"]
        for field in ts_fields:
            if field in obj:
                val = obj[field]
                if isinstance(val, (int, float)):
                    timestamp = float(val)
                    break
                elif isinstance(val, str):
                    ts = self._parse_time_value(val)
                    if ts:
                        timestamp = ts
                        break

        # 估算Token
        token_count = estimate_tokens(content)

        return Message(
            role=role or "unknown",
            content=content,
            timestamp=timestamp,
            token_count=token_count
        )

    def _parse_time_value(self, value: Any) -> Optional[float]:
        """解析各种格式的时间值"""
        if isinstance(value, (int, float)):
            ts = float(value)
            # 判断是否是秒级时间戳（大于2000-01-01）
            if ts > 946684800:
                return ts
            # 毫秒级时间戳
            if ts > 946684800000:
                return ts / 1000
            return None

        if isinstance(value, str):
            # ISO格式
            from datetime import datetime
            iso_formats = [
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
            ]
            for fmt in iso_formats:
                try:
                    dt = datetime.strptime(value.replace("Z", "").split("+")[0], fmt)
                    return dt.timestamp()
                except ValueError:
                    continue
            return None

        return None

    def get_scan_stats(self) -> Dict[str, int]:
        """获取扫描统计信息"""
        return dict(self._scan_stats)

    def reset_stats(self):
        """重置扫描统计"""
        self._scan_stats = {
            "files_scanned": 0,
            "files_parsed": 0,
            "files_failed": 0,
            "sessions_found": 0,
        }
