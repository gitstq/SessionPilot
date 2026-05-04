"""
SessionPilot - 搜索引擎
支持关键词搜索、正则搜索、时间范围过滤、标签过滤
"""

import re
import time
from typing import List, Optional, Dict, Any, Tuple, Set

from .models import Session, IndexEntry
from .indexer import SessionIndexer
from .scanner import SessionScanner
from .utils import (
    time_range_filter, parse_time_str, extract_keywords, truncate_text
)


class SearchOptions:
    """搜索选项"""

    def __init__(
        self,
        keyword: str = "",
        regex: str = "",
        source: str = "",
        tags: Optional[List[str]] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        start_time_str: str = "",
        end_time_str: str = "",
        max_results: int = 100,
        sort_by: str = "relevance",  # relevance, time, size
        sort_order: str = "desc",  # asc, desc
        search_content: bool = True,
        search_title: bool = True,
        case_sensitive: bool = False,
    ):
        self.keyword = keyword
        self.regex = regex
        self.source = source
        self.tags = tags or []
        self.start_time = start_time
        self.end_time = end_time
        self.max_results = max_results
        self.sort_by = sort_by
        self.sort_order = sort_order
        self.search_content = search_content
        self.search_title = search_title
        self.case_sensitive = case_sensitive

        # 解析时间字符串
        if start_time_str and self.start_time is None:
            self.start_time = parse_time_str(start_time_str)
        if end_time_str and self.end_time is None:
            self.end_time = parse_time_str(end_time_str)


class SearchResult:
    """搜索结果"""

    def __init__(
        self,
        session: Session,
        score: float = 0.0,
        matched_content: str = "",
        match_positions: Optional[List[Tuple[int, int]]] = None,
    ):
        self.session = session
        self.score = score
        self.matched_content = matched_content
        self.match_positions = match_positions or []

    @property
    def session_id(self) -> str:
        return self.session.id

    @property
    def title(self) -> str:
        return self.session.title

    @property
    def source(self) -> str:
        return self.session.source

    @property
    def preview(self) -> str:
        return self.session.get_preview(150)


class SessionSearcher:
    """会话搜索引擎"""

    def __init__(self, indexer: Optional[SessionIndexer] = None):
        """
        初始化搜索引擎

        Args:
            indexer: 索引引擎实例
        """
        self.indexer = indexer or SessionIndexer()

    def search(self, options: SearchOptions) -> List[SearchResult]:
        """
        执行搜索

        Args:
            options: 搜索选项

        Returns:
            搜索结果列表
        """
        # 第一步：获取候选会话
        candidates = self._get_candidates(options)

        # 第二步：过滤
        filtered = self._apply_filters(candidates, options)

        # 第三步：评分和排序
        scored = self._score_and_sort(filtered, options)

        # 第四步：限制结果数量
        return scored[:options.max_results]

    def _get_candidates(self, options: SearchOptions) -> List[Session]:
        """获取候选会话列表"""
        # 如果有关键词，先从索引搜索
        if options.keyword:
            entries = self.indexer.search_by_keyword(options.keyword)
            if entries:
                sessions = self._entries_to_sessions(entries)
                return sessions
            # 索引搜索无结果时，回退到全量搜索（让后续内容过滤处理）
            entries = self.indexer.get_all_entries()
            sessions = self._entries_to_sessions(entries)
            return sessions

        if options.regex:
            # 正则搜索需要全量数据
            entries = self.indexer.get_all_entries()
            sessions = self._entries_to_sessions(entries)
            return sessions

        if options.source:
            entries = self.indexer.get_entries_by_source(options.source)
            sessions = self._entries_to_sessions(entries)
            return sessions

        if options.tags:
            all_entries = []
            for tag in options.tags:
                all_entries.extend(self.indexer.get_entries_by_tag(tag))
            # 去重
            seen = set()
            unique_entries = []
            for e in all_entries:
                if e.session_id not in seen:
                    seen.add(e.session_id)
                    unique_entries.append(e)
            sessions = self._entries_to_sessions(unique_entries)
            return sessions

        # 无特定条件，返回所有
        entries = self.indexer.get_all_entries()
        return self._entries_to_sessions(entries)

    def _entries_to_sessions(self, entries: List[IndexEntry]) -> List[Session]:
        """将索引条目转换为轻量会话对象"""
        sessions = []
        for entry in entries:
            session = Session(
                id=entry.session_id,
                source=entry.source,
                title=entry.title,
                created_at=entry.created_at,
                updated_at=entry.updated_at,
                file_path=entry.file_path,
                file_size=entry.file_size,
                tags=entry.tags,
            )
            sessions.append(session)
        return sessions

    def _apply_filters(self, sessions: List[Session], options: SearchOptions) -> List[Session]:
        """应用过滤条件"""
        filtered = []

        for session in sessions:
            # 来源过滤
            if options.source and session.source != options.source:
                continue

            # 标签过滤
            if options.tags:
                if not any(tag in session.tags for tag in options.tags):
                    continue

            # 时间范围过滤
            ts = session.updated_at or session.created_at
            if not time_range_filter(ts, options.start_time, options.end_time):
                continue

            # 正则过滤
            if options.regex:
                flags = 0 if options.case_sensitive else re.IGNORECASE
                try:
                    pattern = re.compile(options.regex, flags)
                except re.error:
                    continue

                matched = False
                if options.search_title and pattern.search(session.title):
                    matched = True
                if not matched and options.search_content:
                    for msg in session.messages:
                        if pattern.search(msg.content):
                            matched = True
                            break
                if not matched:
                    continue

            # 关键词内容过滤（精确匹配）
            if options.keyword and options.search_content:
                kw = options.keyword
                if not options.case_sensitive:
                    kw = kw.lower()
                # 如果会话有消息内容，在消息中搜索
                if session.messages:
                    found = False
                    for msg in session.messages:
                        content = msg.content if options.case_sensitive else msg.content.lower()
                        if kw in content:
                            found = True
                            break
                    if not found:
                        # 消息中没找到，但标题中可能已匹配（由索引搜索保证）
                        title = session.title if options.case_sensitive else session.title.lower()
                        if kw not in title:
                            continue
                else:
                    # 没有消息内容（轻量会话），检查标题匹配
                    title = session.title if options.case_sensitive else session.title.lower()
                    if kw not in title:
                        continue

            filtered.append(session)

        return filtered

    def _score_and_sort(
        self, sessions: List[Session], options: SearchOptions
    ) -> List[SearchResult]:
        """评分和排序"""
        results = []

        for session in sessions:
            score = self._calculate_score(session, options)
            matched_content = self._extract_matched_content(session, options)
            match_positions = self._find_match_positions(session, options)

            result = SearchResult(
                session=session,
                score=score,
                matched_content=matched_content,
                match_positions=match_positions,
            )
            results.append(result)

        # 排序
        reverse = options.sort_order == "desc"
        if options.sort_by == "relevance":
            results.sort(key=lambda r: r.score, reverse=reverse)
        elif options.sort_by == "time":
            results.sort(
                key=lambda r: r.session.updated_at or r.session.created_at or 0,
                reverse=reverse
            )
        elif options.sort_by == "size":
            results.sort(key=lambda r: r.session.file_size, reverse=reverse)

        return results

    def _calculate_score(self, session: Session, options: SearchOptions) -> float:
        """计算搜索结果的相关性评分"""
        score = 0.0

        if not options.keyword:
            # 无关键词时，基于会话新鲜度和大小评分
            if session.updated_at:
                age_hours = (time.time() - session.updated_at) / 3600
                score = max(0, 100 - age_hours)
            score += min(session.message_count, 50) * 0.5
            return score

        keyword = options.keyword.lower() if not options.case_sensitive else options.keyword

        # 标题匹配（权重高）
        title = session.title.lower() if not options.case_sensitive else session.title
        if keyword in title:
            score += 50
            # 完全匹配标题
            if keyword == title:
                score += 30

        # 内容匹配
        match_count = 0
        total_matches = 0
        for msg in session.messages:
            content = msg.content.lower() if not options.case_sensitive else msg.content
            count = content.count(keyword)
            if count > 0:
                match_count += 1
                total_matches += count

        score += match_count * 5
        score += min(total_matches, 20) * 2

        # 新鲜度加分
        if session.updated_at:
            age_hours = (time.time() - session.updated_at) / 3600
            score += max(0, 10 - age_hours / 24)

        # 消息数量加分
        score += min(session.message_count, 20) * 0.3

        return score

    def _extract_matched_content(self, session: Session, options: SearchOptions) -> str:
        """提取匹配的内容片段"""
        if not options.keyword and not options.regex:
            return ""

        keyword = options.keyword
        if keyword and not options.case_sensitive:
            keyword = keyword.lower()

        for msg in session.messages:
            content = msg.content if options.case_sensitive else msg.content.lower()
            search_kw = keyword if keyword else ""

            if options.regex:
                flags = 0 if options.case_sensitive else re.IGNORECASE
                try:
                    pattern = re.compile(options.regex, flags)
                    match = pattern.search(msg.content)
                    if match:
                        start = max(0, match.start() - 30)
                        end = min(len(msg.content), match.end() + 30)
                        return msg.content[start:end]
                except re.error:
                    continue
            elif search_kw and search_kw in content:
                idx = content.index(search_kw)
                start = max(0, idx - 30)
                end = min(len(msg.content), idx + len(search_kw) + 30)
                result = msg.content[start:end]
                if start > 0:
                    result = "..." + result
                if end < len(msg.content):
                    result = result + "..."
                return result

        return ""

    def _find_match_positions(
        self, session: Session, options: SearchOptions
    ) -> List[Tuple[int, int]]:
        """查找匹配位置（消息索引，字符位置）"""
        positions = []
        keyword = options.keyword
        if keyword and not options.case_sensitive:
            keyword = keyword.lower()

        for i, msg in enumerate(session.messages):
            content = msg.content if options.case_sensitive else msg.content.lower()
            search_kw = keyword if keyword else ""

            if options.regex:
                flags = 0 if options.case_sensitive else re.IGNORECASE
                try:
                    pattern = re.compile(options.regex, flags)
                    for match in pattern.finditer(msg.content):
                        positions.append((i, match.start(), match.end()))
                except re.error:
                    continue
            elif search_kw:
                idx = 0
                while True:
                    pos = content.find(search_kw, idx)
                    if pos == -1:
                        break
                    positions.append((i, pos, pos + len(search_kw)))
                    idx = pos + 1

        return positions

    def quick_search(self, keyword: str, max_results: int = 20) -> List[SearchResult]:
        """
        快速搜索（简化接口）

        Args:
            keyword: 搜索关键词
            max_results: 最大结果数

        Returns:
            搜索结果列表
        """
        options = SearchOptions(keyword=keyword, max_results=max_results)
        return self.search(options)

    def search_by_source(
        self, source: str, max_results: int = 100
    ) -> List[SearchResult]:
        """
        按来源搜索

        Args:
            source: 来源名称
            max_results: 最大结果数

        Returns:
            搜索结果列表
        """
        options = SearchOptions(source=source, max_results=max_results)
        return self.search(options)

    def search_by_time_range(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        max_results: int = 100,
    ) -> List[SearchResult]:
        """
        按时间范围搜索

        Args:
            start_time: 起始时间戳
            end_time: 结束时间戳
            max_results: 最大结果数

        Returns:
            搜索结果列表
        """
        options = SearchOptions(
            start_time=start_time,
            end_time=end_time,
            max_results=max_results,
            sort_by="time",
        )
        return self.search(options)

    def regex_search(
        self, pattern: str, max_results: int = 100
    ) -> List[SearchResult]:
        """
        正则表达式搜索

        Args:
            pattern: 正则表达式
            max_results: 最大结果数

        Returns:
            搜索结果列表
        """
        options = SearchOptions(regex=pattern, max_results=max_results)
        return self.search(options)
