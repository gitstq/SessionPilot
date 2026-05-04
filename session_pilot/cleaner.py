"""
SessionPilot - 清理器
按时间/大小/数量清理旧会话，释放磁盘空间
"""

import os
import time
from typing import List, Optional, Dict, Any, Tuple

from .models import Session, CleanResult
from .indexer import SessionIndexer
from .utils import get_file_size, format_size


class CleanPolicy:
    """清理策略"""

    def __init__(
        self,
        max_age_days: int = 0,
        max_total_size_mb: float = 0,
        max_file_count: int = 0,
        min_file_size_kb: float = 0,
        dry_run: bool = True,
        source: str = "",
        confirm_each: bool = False,
    ):
        """
        初始化清理策略

        Args:
            max_age_days: 最大保留天数（0=不限制）
            max_total_size_mb: 最大总大小MB（0=不限制）
            max_file_count: 最大文件数量（0=不限制）
            min_file_size_kb: 最小文件大小KB，小于此值的文件将被清理
            dry_run: 试运行模式（不实际删除）
            source: 仅清理指定来源
            confirm_each: 逐个确认
        """
        self.max_age_days = max_age_days
        self.max_total_size_mb = max_total_size_mb
        self.max_file_count = max_file_count
        self.min_file_size_kb = min_file_size_kb
        self.dry_run = dry_run
        self.source = source
        self.confirm_each = confirm_each


class SessionCleaner:
    """会话清理器"""

    def __init__(self, indexer: Optional[SessionIndexer] = None):
        """
        初始化清理器

        Args:
            indexer: 索引引擎实例
        """
        self.indexer = indexer or SessionIndexer()

    def clean(self, sessions: List["Session"], policy: CleanPolicy) -> CleanResult:
        """
        执行清理

        Args:
            sessions: 会话列表
            policy: 清理策略

        Returns:
            清理结果
        """
        result = CleanResult()

        # 过滤要清理的会话
        to_clean = self._select_for_cleaning(sessions, policy)

        if not to_clean:
            return result

        # 按时间排序（最旧的优先）
        to_clean.sort(key=lambda s: s.updated_at or s.created_at or 0)

        # 执行清理
        for session in to_clean:
            try:
                if policy.dry_run:
                    # 试运行模式，只记录
                    result.deleted_files.append(session.file_path)
                    result.deleted_count += 1
                    result.freed_bytes += session.file_size
                else:
                    # 实际删除
                    if os.path.exists(session.file_path):
                        os.remove(session.file_path)
                        result.deleted_files.append(session.file_path)
                        result.deleted_count += 1
                        result.freed_bytes += session.file_size

                        # 从索引中移除
                        self.indexer.remove_session(session.id)
                    else:
                        result.failed_count += 1
                        result.errors.append(f"文件不存在: {session.file_path}")
            except PermissionError as e:
                result.failed_count += 1
                result.errors.append(f"权限不足: {session.file_path} - {e}")
            except OSError as e:
                result.failed_count += 1
                result.errors.append(f"删除失败: {session.file_path} - {e}")

        return result

    def _select_for_cleaning(
        self, sessions: List["Session"], policy: CleanPolicy
    ) -> List["Session"]:
        """
        根据策略选择要清理的会话

        Args:
            sessions: 会话列表
            policy: 清理策略

        Returns:
            待清理的会话列表
        """
        candidates = list(sessions)

        # 来源过滤
        if policy.source:
            candidates = [s for s in candidates if s.source == policy.source]

        # 按时间过滤
        if policy.max_age_days > 0:
            cutoff = time.time() - policy.max_age_days * 86400
            age_candidates = []
            for s in candidates:
                ts = s.updated_at or s.created_at
                if ts and ts < cutoff:
                    age_candidates.append(s)
            if age_candidates:
                candidates = age_candidates

        # 按最小文件大小过滤
        if policy.min_file_size_kb > 0:
            min_bytes = policy.min_file_size_kb * 1024
            candidates = [s for s in candidates if s.file_size < min_bytes]

        # 按最大文件数量过滤
        if policy.max_file_count > 0 and len(candidates) > policy.max_file_count:
            # 按时间排序，保留最新的
            candidates.sort(key=lambda s: s.updated_at or s.created_at or 0, reverse=True)
            candidates = candidates[policy.max_file_count:]

        # 按最大总大小过滤
        if policy.max_total_size_mb > 0:
            max_bytes = policy.max_total_size_mb * 1024 * 1024
            # 按时间排序（最旧的优先删除）
            candidates.sort(key=lambda s: s.updated_at or s.created_at or 0)
            total = 0
            to_keep = []
            to_remove = []
            for s in reversed(candidates):  # 从最新的开始保留
                if total + s.file_size <= max_bytes:
                    to_keep.append(s)
                    total += s.file_size
                else:
                    to_remove.append(s)
            candidates = to_remove

        return candidates

    def preview_clean(
        self, sessions: List["Session"], policy: CleanPolicy
    ) -> Dict[str, Any]:
        """
        预览清理操作（不实际执行）

        Args:
            sessions: 会话列表
            policy: 清理策略

        Returns:
            预览信息
        """
        to_clean = self._select_for_cleaning(sessions, policy)
        total_size = sum(s.file_size for s in to_clean)

        # 按来源分组
        by_source = {}
        for s in to_clean:
            if s.source not in by_source:
                by_source[s.source] = 0
            by_source[s.source] += 1

        return {
            "would_delete": len(to_clean),
            "would_free_bytes": total_size,
            "would_free_display": format_size(total_size),
            "by_source": by_source,
            "dry_run": policy.dry_run,
            "files": [
                {
                    "path": s.file_path,
                    "size": format_size(s.file_size),
                    "source": s.source,
                    "updated": s.updated_time_str,
                }
                for s in to_clean[:20]  # 最多显示20个
            ],
        }

    def get_disk_usage(self, sessions: List["Session"]) -> Dict[str, Any]:
        """
        获取磁盘使用情况

        Args:
            sessions: 会话列表

        Returns:
            磁盘使用统计
        """
        total_size = sum(s.file_size for s in sessions)
        by_source = {}
        for s in sessions:
            if s.source not in by_source:
                by_source[s.source] = {"count": 0, "size": 0}
            by_source[s.source]["count"] += 1
            by_source[s.source]["size"] += s.file_size

        return {
            "total_size": total_size,
            "total_display": format_size(total_size),
            "total_files": len(sessions),
            "by_source": {
                k: {
                    "count": v["count"],
                    "size": format_size(v["size"]),
                    "size_bytes": v["size"],
                }
                for k, v in by_source.items()
            },
        }
