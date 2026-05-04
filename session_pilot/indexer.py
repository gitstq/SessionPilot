"""
SessionPilot - 索引引擎
建立和管理会话的本地索引，支持快速查询
"""

import os
import json
import time
from typing import List, Optional, Dict, Any, Set

from .models import Session, IndexEntry
from .utils import (
    get_cache_dir, ensure_dir, safe_read_json, safe_write_json,
    get_file_mtime, generate_id
)


class SessionIndexer:
    """会话索引引擎 - 建立和管理本地会话索引"""

    # 索引文件名
    INDEX_FILENAME = "session_index.json"

    def __init__(self, index_dir: Optional[str] = None):
        """
        初始化索引引擎

        Args:
            index_dir: 索引文件存储目录，默认使用缓存目录
        """
        if index_dir:
            self.index_dir = index_dir
        else:
            self.index_dir = os.path.join(get_cache_dir(), "index")
        ensure_dir(self.index_dir)

        self._index_path = os.path.join(self.index_dir, self.INDEX_FILENAME)
        self._entries: Dict[str, IndexEntry] = {}  # session_id -> IndexEntry
        self._source_index: Dict[str, Set[str]] = {}  # source -> {session_ids}
        self._tag_index: Dict[str, Set[str]] = {}  # tag -> {session_ids}
        self._loaded = False

    def load_index(self) -> bool:
        """从磁盘加载索引"""
        data = safe_read_json(self._index_path)
        if data is None:
            self._entries = {}
            self._source_index = {}
            self._tag_index = {}
            self._loaded = True
            return False

        try:
            entries_data = data.get("entries", {})
            self._entries = {}
            for sid, entry_data in entries_data.items():
                self._entries[sid] = IndexEntry(**entry_data)

            # 重建倒排索引
            self._rebuild_inverted_indexes()
            self._loaded = True
            return True
        except (TypeError, KeyError, ValueError):
            self._entries = {}
            self._source_index = {}
            self._tag_index = {}
            self._loaded = True
            return False

    def save_index(self) -> bool:
        """保存索引到磁盘"""
        entries_data = {}
        for sid, entry in self._entries.items():
            entries_data[sid] = entry.to_dict()

        data = {
            "version": "1.0",
            "updated_at": time.time(),
            "total_entries": len(entries_data),
            "entries": entries_data,
        }
        return safe_write_json(self._index_path, data)

    def _ensure_loaded(self):
        """确保索引已加载"""
        if not self._loaded:
            self.load_index()

    def _rebuild_inverted_indexes(self):
        """重建倒排索引"""
        self._source_index = {}
        self._tag_index = {}

        for sid, entry in self._entries.items():
            # 来源索引
            source = entry.source
            if source not in self._source_index:
                self._source_index[source] = set()
            self._source_index[source].add(sid)

            # 标签索引
            for tag in entry.tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = set()
                self._tag_index[tag].add(sid)

    def add_session(self, session: Session) -> IndexEntry:
        """
        添加或更新会话索引

        Args:
            session: 会话对象

        Returns:
            索引条目
        """
        self._ensure_loaded()

        entry = IndexEntry.from_session(session)

        # 提取关键词
        all_text = " ".join(m.content for m in session.messages)
        from .utils import extract_keywords
        entry.keywords = [kw for kw, _ in extract_keywords(all_text, top_n=15)]

        # 更新主索引
        self._entries[session.id] = entry

        # 更新来源索引
        if session.source not in self._source_index:
            self._source_index[session.source] = set()
        self._source_index[session.source].add(session.id)

        # 更新标签索引
        for tag in entry.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(session.id)

        return entry

    def add_sessions(self, sessions: List[Session]) -> int:
        """
        批量添加会话索引

        Args:
            sessions: 会话列表

        Returns:
            添加的条目数
        """
        self._ensure_loaded()
        count = 0
        for session in sessions:
            self.add_session(session)
            count += 1
        return count

    def remove_session(self, session_id: str) -> bool:
        """
        移除会话索引

        Args:
            session_id: 会话ID

        Returns:
            是否成功移除
        """
        self._ensure_loaded()

        if session_id not in self._entries:
            return False

        entry = self._entries[session_id]

        # 从来源索引中移除
        if entry.source in self._source_index:
            self._source_index[entry.source].discard(session_id)
            if not self._source_index[entry.source]:
                del self._source_index[entry.source]

        # 从标签索引中移除
        for tag in entry.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(session_id)
                if not self._tag_index[tag]:
                    del self._tag_index[tag]

        # 从主索引中移除
        del self._entries[session_id]
        return True

    def get_entry(self, session_id: str) -> Optional[IndexEntry]:
        """获取指定会话的索引条目"""
        self._ensure_loaded()
        return self._entries.get(session_id)

    def get_all_entries(self) -> List[IndexEntry]:
        """获取所有索引条目"""
        self._ensure_loaded()
        return list(self._entries.values())

    def get_entries_by_source(self, source: str) -> List[IndexEntry]:
        """获取指定来源的所有索引条目"""
        self._ensure_loaded()
        sids = self._source_index.get(source, set())
        return [self._entries[sid] for sid in sids if sid in self._entries]

    def get_entries_by_tag(self, tag: str) -> List[IndexEntry]:
        """获取指定标签的所有索引条目"""
        self._ensure_loaded()
        sids = self._tag_index.get(tag, set())
        return [self._entries[sid] for sid in sids if sid in self._entries]

    def search_by_keyword(self, keyword: str) -> List[IndexEntry]:
        """
        关键词搜索（在标题、预览、关键词中搜索）

        Args:
            keyword: 搜索关键词

        Returns:
            匹配的索引条目列表
        """
        self._ensure_loaded()
        keyword_lower = keyword.lower()
        results = []

        for entry in self._entries.values():
            # 在标题中搜索
            if keyword_lower in entry.title.lower():
                results.append(entry)
                continue

            # 在预览中搜索
            if keyword_lower in entry.preview.lower():
                results.append(entry)
                continue

            # 在关键词中搜索
            if any(keyword_lower in kw.lower() for kw in entry.keywords):
                results.append(entry)
                continue

        return results

    def search_by_time_range(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> List[IndexEntry]:
        """
        时间范围搜索

        Args:
            start_time: 起始时间戳
            end_time: 结束时间戳

        Returns:
            匹配的索引条目列表
        """
        self._ensure_loaded()
        results = []

        for entry in self._entries.values():
            ts = entry.updated_at or entry.created_at
            if ts is None:
                continue
            if start_time is not None and ts < start_time:
                continue
            if end_time is not None and ts > end_time:
                continue
            results.append(entry)

        return results

    def get_stale_entries(self, max_age_seconds: float = 86400 * 30) -> List[IndexEntry]:
        """
        获取过期的索引条目（文件可能已被删除或修改）

        Args:
            max_age_seconds: 最大索引年龄（秒）

        Returns:
            可能过期的索引条目列表
        """
        self._ensure_loaded()
        stale = []
        now = time.time()

        for entry in self._entries.values():
            # 检查文件是否存在
            if not os.path.exists(entry.file_path):
                stale.append(entry)
                continue

            # 检查文件是否被修改过
            current_mtime = get_file_mtime(entry.file_path)
            if current_mtime is not None and entry.updated_at is not None:
                if current_mtime > entry.updated_at:
                    stale.append(entry)
                    continue

            # 检查索引是否过期
            if entry.updated_at and (now - entry.updated_at) > max_age_seconds:
                stale.append(entry)

        return stale

    def cleanup_missing(self) -> int:
        """清理指向不存在文件的索引条目"""
        self._ensure_loaded()
        to_remove = []

        for sid, entry in self._entries.items():
            if not os.path.exists(entry.file_path):
                to_remove.append(sid)

        for sid in to_remove:
            self.remove_session(sid)

        return len(to_remove)

    def get_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        self._ensure_loaded()
        source_counts = {}
        for source, sids in self._source_index.items():
            source_counts[source] = len(sids)

        return {
            "total_entries": len(self._entries),
            "sources": source_counts,
            "total_tags": len(self._tag_index),
            "index_path": self._index_path,
        }

    def clear_index(self):
        """清空索引"""
        self._entries = {}
        self._source_index = {}
        self._tag_index = {}

    @property
    def total_entries(self) -> int:
        """索引条目总数"""
        self._ensure_loaded()
        return len(self._entries)
