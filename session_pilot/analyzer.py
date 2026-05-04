"""
SessionPilot - 分析引擎
统计会话数量、频率、主题分布、Token使用估算、时间趋势分析
"""

import time
import os
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict

from .models import Session, AnalysisResult, IndexEntry
from .utils import (
    extract_keywords, format_timestamp, get_date_key, get_hour_key,
    format_size, format_number
)


class SessionAnalyzer:
    """会话分析引擎"""

    def __init__(self):
        """初始化分析引擎"""
        pass

    def analyze(self, sessions: List[Session]) -> AnalysisResult:
        """
        分析会话列表

        Args:
            sessions: 会话列表

        Returns:
            分析结果
        """
        result = AnalysisResult()

        if not sessions:
            return result

        result.total_sessions = len(sessions)
        result.total_size_bytes = sum(s.file_size for s in sessions)

        # 统计消息和Token
        total_messages = 0
        total_tokens = 0
        oldest_ts = None
        newest_ts = None
        daily_counts = Counter()
        hourly_counts = Counter()
        source_counts = Counter()
        all_text = ""
        size_list = []

        for session in sessions:
            msg_count = session.message_count
            total_messages += msg_count
            total_tokens += session.estimated_tokens

            # 时间统计
            ts = session.updated_at or session.created_at
            if ts:
                if oldest_ts is None or ts < oldest_ts:
                    oldest_ts = ts
                if newest_ts is None or ts > newest_ts:
                    newest_ts = ts
                daily_counts[get_date_key(ts)] += 1
                hour = get_hour_key(ts)
                if hour >= 0:
                    hourly_counts[hour] += 1

            # 来源统计
            source_counts[session.source] += 1

            # 收集文本用于关键词提取
            for msg in session.messages:
                all_text += msg.content + " "

            # 大小列表
            size_list.append((session.file_path, session.file_size))

        result.total_messages = total_messages
        result.total_tokens_estimate = total_tokens
        result.oldest_session = oldest_ts
        result.newest_session = newest_ts
        result.daily_distribution = dict(daily_counts.most_common())
        result.hourly_distribution = dict(sorted(hourly_counts.items()))
        result.source_distribution = dict(source_counts.most_common())

        # 平均值
        if result.total_sessions > 0:
            result.average_messages_per_session = total_messages / result.total_sessions
            result.average_tokens_per_session = total_tokens / result.total_sessions

        # 关键词提取
        result.top_keywords = extract_keywords(all_text, top_n=20)

        # 按大小排序的会话
        size_list.sort(key=lambda x: x[1], reverse=True)
        result.sessions_by_size = size_list[:20]

        return result

    def analyze_by_source(self, sessions: List[Session]) -> Dict[str, Dict[str, Any]]:
        """
        按来源分组分析

        Args:
            sessions: 会话列表

        Returns:
            按来源分组的分析结果
        """
        groups = defaultdict(list)
        for session in sessions:
            groups[session.source].append(session)

        result = {}
        for source, source_sessions in groups.items():
            analysis = self.analyze(source_sessions)
            result[source] = {
                "session_count": analysis.total_sessions,
                "total_messages": analysis.total_messages,
                "total_tokens": analysis.total_tokens_estimate,
                "total_size": analysis.total_size_display,
                "avg_messages": round(analysis.average_messages_per_session, 1),
                "oldest": format_timestamp(analysis.oldest_session, "%Y-%m-%d"),
                "newest": format_timestamp(analysis.newest_session, "%Y-%m-%d"),
            }

        return result

    def analyze_time_trends(self, sessions: List[Session]) -> Dict[str, Any]:
        """
        分析时间趋势

        Args:
            sessions: 会话列表

        Returns:
            时间趋势分析结果
        """
        if not sessions:
            return {"daily": {}, "hourly": {}, "weekly": {}}

        daily_counts = Counter()
        weekly_counts = Counter()
        hourly_counts = Counter()

        for session in sessions:
            ts = session.updated_at or session.created_at
            if ts is None:
                continue

            date_key = get_date_key(ts)
            daily_counts[date_key] += 1

            # 周统计
            try:
                t = time.localtime(ts)
                week_key = f"{t.tm_year}-W{t.tm_yday // 7:02d}"
                weekly_counts[week_key] += 1
            except (ValueError, OSError):
                pass

            hour = get_hour_key(ts)
            if hour >= 0:
                hourly_counts[hour] += 1

        # 计算每日平均
        avg_daily = 0.0
        if daily_counts:
            avg_daily = sum(daily_counts.values()) / len(daily_counts)

        # 找出最活跃的日期和时段
        most_active_day = daily_counts.most_common(1)[0] if daily_counts else ("无", 0)
        most_active_hour = hourly_counts.most_common(1)[0] if hourly_counts else ("无", 0)

        return {
            "daily": dict(daily_counts.most_common(30)),
            "weekly": dict(weekly_counts.most_common(12)),
            "hourly": dict(sorted(hourly_counts.items())),
            "avg_per_day": round(avg_daily, 1),
            "most_active_day": most_active_day,
            "most_active_hour": most_active_hour,
            "total_days": len(daily_counts),
        }

    def analyze_topics(self, sessions: List[Session], top_n: int = 10) -> List[Dict[str, Any]]:
        """
        分析会话主题分布

        Args:
            sessions: 会话列表
            top_n: 返回前N个主题

        Returns:
            主题列表
        """
        all_text = ""
        for session in sessions:
            # 标题权重更高
            all_text += (session.title + " ") * 3
            for msg in session.messages:
                all_text += msg.content + " "

        keywords = extract_keywords(all_text, top_n=top_n * 2)

        topics = []
        for keyword, count in keywords[:top_n]:
            # 统计包含该关键词的会话数
            related_sessions = 0
            for session in sessions:
                if keyword.lower() in session.title.lower():
                    related_sessions += 1
                    continue
                for msg in session.messages:
                    if keyword.lower() in msg.content.lower():
                        related_sessions += 1
                        break

            topics.append({
                "keyword": keyword,
                "frequency": count,
                "related_sessions": related_sessions,
                "percentage": round(related_sessions / max(len(sessions), 1) * 100, 1),
            })

        return topics

    def analyze_usage_patterns(self, sessions: List[Session]) -> Dict[str, Any]:
        """
        分析使用模式

        Args:
            sessions: 会话列表

        Returns:
            使用模式分析结果
        """
        if not sessions:
            return {}

        # 会话长度分布
        length_buckets = Counter()
        for session in sessions:
            msg_count = session.message_count
            if msg_count <= 5:
                length_buckets["短(1-5)"] += 1
            elif msg_count <= 20:
                length_buckets["中(6-20)"] += 1
            elif msg_count <= 50:
                length_buckets["长(21-50)"] += 1
            else:
                length_buckets["超长(50+)"] += 1

        # Token使用分布
        token_buckets = Counter()
        for session in sessions:
            tokens = session.estimated_tokens
            if tokens <= 500:
                token_buckets["小(<500)"] += 1
            elif tokens <= 2000:
                token_buckets["中(500-2K)"] += 1
            elif tokens <= 10000:
                token_buckets["大(2K-10K)"] += 1
            else:
                token_buckets["超大(10K+)"] += 1

        # 文件大小分布
        size_buckets = Counter()
        for session in sessions:
            size = session.file_size
            if size <= 1024:
                size_buckets["小(<1KB)"] += 1
            elif size <= 10240:
                size_buckets["中(1-10KB)"] += 1
            elif size <= 102400:
                size_buckets["大(10-100KB)"] += 1
            else:
                size_buckets["超大(100KB+)"] += 1

        # 计算会话间隔
        timestamps = []
        for session in sessions:
            ts = session.updated_at or session.created_at
            if ts:
                timestamps.append(ts)
        timestamps.sort()

        avg_interval = 0.0
        median_interval = 0.0
        if len(timestamps) >= 2:
            intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps) - 1)]
            avg_interval = sum(intervals) / len(intervals)
            sorted_intervals = sorted(intervals)
            mid = len(sorted_intervals) // 2
            if len(sorted_intervals) % 2 == 0:
                median_interval = (sorted_intervals[mid-1] + sorted_intervals[mid]) / 2
            else:
                median_interval = sorted_intervals[mid]

        return {
            "session_length_distribution": dict(length_buckets),
            "token_usage_distribution": dict(token_buckets),
            "file_size_distribution": dict(size_buckets),
            "avg_session_interval_hours": round(avg_interval / 3600, 1),
            "median_session_interval_hours": round(median_interval / 3600, 1),
        }

    def generate_summary(self, sessions: List[Session]) -> str:
        """
        生成分析摘要文本

        Args:
            sessions: 会话列表

        Returns:
            摘要文本
        """
        if not sessions:
            return "没有找到任何会话数据。"

        result = self.analyze(sessions)
        trends = self.analyze_time_trends(sessions)

        lines = []
        lines.append("=" * 50)
        lines.append("  SessionPilot 会话分析摘要")
        lines.append("=" * 50)
        lines.append("")

        lines.append(f"总会话数: {result.total_sessions}")
        lines.append(f"总消息数: {result.total_messages}")
        lines.append(f"估算Token总量: {format_number(result.total_tokens_estimate)}")
        lines.append(f"总存储大小: {result.total_size_display}")
        lines.append(f"平均每会话消息数: {result.average_messages_per_session:.1f}")
        lines.append(f"平均每会话Token数: {format_number(int(result.average_tokens_per_session))}")
        lines.append("")

        # 来源分布
        if result.source_distribution:
            lines.append("来源分布:")
            for source, count in result.source_distribution.items():
                pct = count / result.total_sessions * 100
                lines.append(f"  {source}: {count} ({pct:.1f}%)")
            lines.append("")

        # 时间范围
        lines.append(f"时间范围: {format_timestamp(result.oldest_session, '%Y-%m-%d')} ~ {format_timestamp(result.newest_session, '%Y-%m-%d')}")
        lines.append(f"活跃天数: {trends.get('total_days', 0)}")
        lines.append(f"日均会话: {trends.get('avg_per_day', 0)}")
        if trends.get('most_active_day'):
            day, count = trends['most_active_day']
            lines.append(f"最活跃日期: {day} ({count}个会话)")
        if trends.get('most_active_hour'):
            hour, count = trends['most_active_hour']
            lines.append(f"最活跃时段: {hour}:00 ({count}个会话)")
        lines.append("")

        # 热门关键词
        if result.top_keywords:
            lines.append("热门关键词:")
            kw_str = ", ".join(f"{kw}({count})" for kw, count in result.top_keywords[:10])
            lines.append(f"  {kw_str}")
        lines.append("")

        # Top 5 大文件
        if result.sessions_by_size:
            lines.append("最大的会话文件:")
            for path, size in result.sessions_by_size[:5]:
                fname = os.path.basename(path)
                lines.append(f"  {fname}: {format_size(size)}")

        lines.append("")
        lines.append("=" * 50)

        return "\n".join(lines)
