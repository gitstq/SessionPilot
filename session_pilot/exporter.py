"""
SessionPilot - 导出器
支持导出会话数据为Markdown、JSON、CSV格式
"""

import os
import json
import csv
import io
import time
from typing import List, Optional, Dict, Any

from .models import Session, AnalysisResult
from .utils import (
    format_timestamp, format_size, truncate_text, ensure_dir, safe_write_file
)


class SessionExporter:
    """会话导出器"""

    def __init__(self, output_dir: str = "."):
        """
        初始化导出器

        Args:
            output_dir: 默认输出目录
        """
        self.output_dir = output_dir
        ensure_dir(output_dir)

    def export_sessions(
        self,
        sessions: List[Session],
        format: str = "markdown",
        output_path: Optional[str] = None,
        include_messages: bool = True,
    ) -> str:
        """
        导出会话列表

        Args:
            sessions: 会话列表
            format: 导出格式 (markdown/json/csv)
            output_path: 输出文件路径，None则自动生成
            include_messages: 是否包含消息内容

        Returns:
            输出文件路径
        """
        if not sessions:
            raise ValueError("没有可导出的会话数据")

        if format in ("md", "markdown"):
            content = self._export_markdown(sessions, include_messages)
            ext = ".md"
        elif format == "json":
            content = self._export_json(sessions, include_messages)
            ext = ".json"
        elif format == "csv":
            content = self._export_csv(sessions, include_messages)
            ext = ".csv"
        else:
            raise ValueError(f"不支持的导出格式: {format}")

        if output_path is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(
                self.output_dir,
                f"sessionpilot_export_{timestamp}{ext}"
            )

        ensure_dir(os.path.dirname(output_path) or ".")
        safe_write_file(output_path, content)
        return output_path

    def _export_markdown(
        self, sessions: List[Session], include_messages: bool
    ) -> str:
        """导出为Markdown格式"""
        lines = []
        lines.append("# SessionPilot 会话导出")
        lines.append("")
        lines.append(f"导出时间: {format_timestamp(time.time())}")
        lines.append(f"会话总数: {len(sessions)}")
        lines.append("")

        for i, session in enumerate(sessions, 1):
            lines.append("---")
            lines.append("")
            lines.append(f"## 会话 #{i}")
            lines.append("")
            lines.append(f"- **ID**: `{session.id}`")
            lines.append(f"- **来源**: {session.source}")
            lines.append(f"- **标题**: {session.title or '(无标题)'}")
            lines.append(f"- **创建时间**: {session.created_time_str}")
            lines.append(f"- **更新时间**: {session.updated_time_str}")
            lines.append(f"- **消息数**: {session.message_count}")
            lines.append(f"- **估算Token**: {session.estimated_tokens}")
            lines.append(f"- **文件大小**: {format_size(session.file_size)}")
            lines.append(f"- **文件路径**: `{session.file_path}`")

            if session.tags:
                lines.append(f"- **标签**: {', '.join(session.tags)}")

            if session.duration_minutes is not None:
                lines.append(f"- **持续时间**: {session.duration_minutes:.1f} 分钟")

            lines.append("")

            if include_messages and session.messages:
                lines.append("### 消息记录")
                lines.append("")
                for j, msg in enumerate(session.messages, 1):
                    role_display = {
                        "user": "用户",
                        "assistant": "助手",
                        "system": "系统",
                    }.get(msg.role, msg.role)

                    lines.append(f"#### [{role_display}] #{j}")
                    if msg.timestamp:
                        lines.append(f"*{format_timestamp(msg.timestamp)}*")
                    lines.append("")
                    # 对长内容进行代码块包裹
                    content = msg.content
                    if "\n" in content:
                        lines.append("```")
                        lines.append(content)
                        lines.append("```")
                    else:
                        lines.append(content)
                    lines.append("")

        return "\n".join(lines)

    def _export_json(
        self, sessions: List[Session], include_messages: bool
    ) -> str:
        """导出为JSON格式"""
        data = {
            "export_time": time.time(),
            "export_time_str": format_timestamp(time.time()),
            "total_sessions": len(sessions),
            "sessions": [],
        }

        for session in sessions:
            session_dict = {
                "id": session.id,
                "source": session.source,
                "title": session.title,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "created_time_str": session.created_time_str,
                "updated_time_str": session.updated_time_str,
                "message_count": session.message_count,
                "estimated_tokens": session.estimated_tokens,
                "file_size": session.file_size,
                "file_path": session.file_path,
                "tags": session.tags,
                "duration_minutes": session.duration_minutes,
            }

            if include_messages:
                session_dict["messages"] = [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp,
                        "token_count": msg.token_count,
                    }
                    for msg in session.messages
                ]

            data["sessions"].append(session_dict)

        return json.dumps(data, ensure_ascii=False, indent=2)

    def _export_csv(
        self, sessions: List[Session], include_messages: bool
    ) -> str:
        """导出为CSV格式"""
        output = io.StringIO()
        writer = csv.writer(output)

        # 写入表头
        headers = [
            "ID", "来源", "标题", "创建时间", "更新时间",
            "消息数", "估算Token", "文件大小", "文件路径", "标签"
        ]
        writer.writerow(headers)

        for session in sessions:
            row = [
                session.id,
                session.source,
                session.title,
                session.created_time_str,
                session.updated_time_str,
                session.message_count,
                session.estimated_tokens,
                session.file_size,
                session.file_path,
                ";".join(session.tags),
            ]
            writer.writerow(row)

        return output.getvalue()

    def export_analysis(
        self,
        analysis: AnalysisResult,
        format: str = "markdown",
        output_path: Optional[str] = None,
    ) -> str:
        """
        导出分析结果

        Args:
            analysis: 分析结果
            format: 导出格式
            output_path: 输出文件路径

        Returns:
            输出文件路径
        """
        if format in ("md", "markdown"):
            content = self._export_analysis_markdown(analysis)
            ext = ".md"
        elif format == "json":
            content = json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2)
            ext = ".json"
        else:
            raise ValueError(f"不支持的导出格式: {format}")

        if output_path is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(
                self.output_dir,
                f"sessionpilot_analysis_{timestamp}{ext}"
            )

        ensure_dir(os.path.dirname(output_path) or ".")
        safe_write_file(output_path, content)
        return output_path

    def _export_analysis_markdown(self, analysis: AnalysisResult) -> str:
        """导出分析结果为Markdown"""
        lines = []
        lines.append("# SessionPilot 分析报告")
        lines.append("")
        lines.append(f"生成时间: {format_timestamp(time.time())}")
        lines.append("")

        # 概览
        lines.append("## 概览 Overview")
        lines.append("")
        lines.append(f"| 指标 | 值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 总会话数 | {analysis.total_sessions} |")
        lines.append(f"| 总消息数 | {analysis.total_messages} |")
        lines.append(f"| 估算Token总量 | {analysis.total_tokens_estimate:,} |")
        lines.append(f"| 总存储大小 | {analysis.total_size_display} |")
        lines.append(f"| 平均每会话消息数 | {analysis.average_messages_per_session:.1f} |")
        lines.append(f"| 平均每会话Token数 | {analysis.average_tokens_per_session:.0f} |")
        lines.append(f"| 时间范围 | {format_timestamp(analysis.oldest_session, '%Y-%m-%d')} ~ {format_timestamp(analysis.newest_session, '%Y-%m-%d')} |")
        lines.append("")

        # 来源分布
        if analysis.source_distribution:
            lines.append("## 来源分布 Source Distribution")
            lines.append("")
            lines.append("| 来源 | 会话数 | 占比 |")
            lines.append("|------|--------|------|")
            for source, count in analysis.source_distribution.items():
                pct = count / max(analysis.total_sessions, 1) * 100
                lines.append(f"| {source} | {count} | {pct:.1f}% |")
            lines.append("")

        # 每日分布
        if analysis.daily_distribution:
            lines.append("## 每日会话分布 Daily Distribution")
            lines.append("")
            lines.append("| 日期 | 会话数 |")
            lines.append("|------|--------|")
            for date, count in sorted(analysis.daily_distribution.items()):
                lines.append(f"| {date} | {count} |")
            lines.append("")

        # 每小时分布
        if analysis.hourly_distribution:
            lines.append("## 每小时会话分布 Hourly Distribution")
            lines.append("")
            lines.append("| 时段 | 会话数 |")
            lines.append("|------|--------|")
            for hour, count in sorted(analysis.hourly_distribution.items()):
                lines.append(f"| {hour}:00 | {count} |")
            lines.append("")

        # 热门关键词
        if analysis.top_keywords:
            lines.append("## 热门关键词 Top Keywords")
            lines.append("")
            lines.append("| 关键词 | 频次 |")
            lines.append("|--------|------|")
            for keyword, count in analysis.top_keywords:
                lines.append(f"| {keyword} | {count} |")
            lines.append("")

        # 最大的会话文件
        if analysis.sessions_by_size:
            lines.append("## 最大的会话文件 Largest Session Files")
            lines.append("")
            lines.append("| 文件 | 大小 |")
            lines.append("|------|------|")
            for path, size in analysis.sessions_by_size[:10]:
                fname = os.path.basename(path)
                lines.append(f"| {fname} | {format_size(size)} |")
            lines.append("")

        return "\n".join(lines)
