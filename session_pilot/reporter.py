"""
SessionPilot - 报告生成器
生成HTML、Markdown、JSON格式的分析报告
"""

import os
import json
import time
from typing import List, Optional, Dict, Any

from .models import Session, AnalysisResult
from .analyzer import SessionAnalyzer
from .utils import (
    format_timestamp, format_size, format_number, ensure_dir, safe_write_file
)


class ReportGenerator:
    """报告生成器"""

    def __init__(self):
        """初始化报告生成器"""
        self.analyzer = SessionAnalyzer()

    def generate_report(
        self,
        sessions: List[Session],
        format: str = "html",
        output_path: Optional[str] = None,
        title: str = "SessionPilot 分析报告",
    ) -> str:
        """
        生成分析报告

        Args:
            sessions: 会话列表
            format: 报告格式 (html/markdown/json)
            output_path: 输出文件路径
            title: 报告标题

        Returns:
            输出文件路径
        """
        if not sessions:
            raise ValueError("没有可分析的会话数据")

        analysis = self.analyzer.analyze(sessions)
        time_trends = self.analyzer.analyze_time_trends(sessions)
        topics = self.analyzer.analyze_topics(sessions)
        usage = self.analyzer.analyze_usage_patterns(sessions)
        source_analysis = self.analyzer.analyze_by_source(sessions)

        if format == "html":
            content = self._generate_html(
                analysis, time_trends, topics, usage, source_analysis, title
            )
            ext = ".html"
        elif format in ("md", "markdown"):
            content = self._generate_markdown(
                analysis, time_trends, topics, usage, source_analysis, title
            )
            ext = ".md"
        elif format == "json":
            report_data = {
                "title": title,
                "generated_at": time.time(),
                "generated_at_str": format_timestamp(time.time()),
                "analysis": analysis.to_dict(),
                "time_trends": time_trends,
                "topics": topics,
                "usage_patterns": usage,
                "source_analysis": source_analysis,
            }
            content = json.dumps(report_data, ensure_ascii=False, indent=2)
            ext = ".json"
        else:
            raise ValueError(f"不支持的报告格式: {format}")

        if output_path is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_path = f"sessionpilot_report_{timestamp}{ext}"

        ensure_dir(os.path.dirname(output_path) or ".")
        safe_write_file(output_path, content)
        return output_path

    def _generate_html(
        self,
        analysis: AnalysisResult,
        time_trends: Dict[str, Any],
        topics: List[Dict[str, Any]],
        usage: Dict[str, Any],
        source_analysis: Dict[str, Any],
        title: str,
    ) -> str:
        """生成HTML报告"""
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{
            color: #58a6ff;
            border-bottom: 2px solid #30363d;
            padding-bottom: 16px;
            margin-bottom: 24px;
            font-size: 2em;
        }}
        h2 {{
            color: #79c0ff;
            margin-top: 32px;
            margin-bottom: 16px;
            font-size: 1.4em;
        }}
        .meta {{
            color: #8b949e;
            margin-bottom: 24px;
            font-size: 0.9em;
        }}
        .cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}
        .card {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 20px;
        }}
        .card .label {{
            color: #8b949e;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .card .value {{
            color: #f0f6fc;
            font-size: 1.8em;
            font-weight: bold;
            margin-top: 4px;
        }}
        .card .value.small {{ font-size: 1.2em; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 24px;
            background: #161b22;
            border-radius: 8px;
            overflow: hidden;
        }}
        th {{
            background: #21262d;
            color: #c9d1d9;
            padding: 12px 16px;
            text-align: left;
            font-weight: 600;
            border-bottom: 1px solid #30363d;
        }}
        td {{
            padding: 10px 16px;
            border-bottom: 1px solid #21262d;
        }}
        tr:hover {{ background: #1c2128; }}
        .bar-container {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .bar {{
            height: 20px;
            background: #1f6feb;
            border-radius: 4px;
            min-width: 4px;
        }}
        .bar-label {{ min-width: 40px; }}
        .tag {{
            display: inline-block;
            background: #1f6feb22;
            color: #58a6ff;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.85em;
            margin: 2px;
        }}
        .section {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 24px;
        }}
        .chart-bar {{
            display: flex;
            align-items: flex-end;
            gap: 4px;
            height: 120px;
            padding: 8px 0;
        }}
        .chart-bar .bar {{
            flex: 1;
            min-width: 8px;
            max-width: 40px;
            background: #1f6feb;
            border-radius: 4px 4px 0 0;
            position: relative;
        }}
        .chart-bar .bar:hover {{ background: #388bfd; }}
        .chart-labels {{
            display: flex;
            gap: 4px;
            font-size: 0.7em;
            color: #8b949e;
        }}
        .chart-labels span {{
            flex: 1;
            min-width: 8px;
            max-width: 40px;
            text-align: center;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .footer {{
            text-align: center;
            color: #484f58;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #21262d;
        }}
    </style>
</head>
<body>
<div class="container">
    <h1>{title}</h1>
    <p class="meta">生成时间: {format_timestamp(time.time())} | SessionPilot v1.0</p>

    <!-- 概览卡片 -->
    <div class="cards">
        <div class="card">
            <div class="label">总会话数</div>
            <div class="value">{analysis.total_sessions}</div>
        </div>
        <div class="card">
            <div class="label">总消息数</div>
            <div class="value">{analysis.total_messages:,}</div>
        </div>
        <div class="card">
            <div class="label">估算Token总量</div>
            <div class="value">{format_number(analysis.total_tokens_estimate)}</div>
        </div>
        <div class="card">
            <div class="label">总存储大小</div>
            <div class="value small">{analysis.total_size_display}</div>
        </div>
        <div class="card">
            <div class="label">平均消息/会话</div>
            <div class="value">{analysis.average_messages_per_session:.1f}</div>
        </div>
        <div class="card">
            <div class="label">时间范围</div>
            <div class="value small">{format_timestamp(analysis.oldest_session, '%Y-%m-%d')} ~ {format_timestamp(analysis.newest_session, '%Y-%m-%d')}</div>
        </div>
    </div>

    <!-- 来源分布 -->
    <div class="section">
        <h2>来源分布 Source Distribution</h2>
        <table>
            <tr><th>来源</th><th>会话数</th><th>占比</th><th>分布</th></tr>"""

        if analysis.source_distribution:
            max_count = max(analysis.source_distribution.values())
            for source, count in analysis.source_distribution.items():
                pct = count / max(analysis.total_sessions, 1) * 100
                bar_width = int(count / max(max_count, 1) * 100)
                html += f"""
            <tr>
                <td><strong>{source}</strong></td>
                <td>{count}</td>
                <td>{pct:.1f}%</td>
                <td><div class="bar-container">
                    <div class="bar" style="width:{bar_width}%;max-width:300px;"></div>
                    <span class="bar-label">{count}</span>
                </div></td>
            </tr>"""

        html += """
        </table>
    </div>

    <!-- 每日趋势 -->
    <div class="section">
        <h2>每日会话趋势 Daily Trends</h2>"""

        daily = time_trends.get("daily", {})
        if daily:
            daily_items = sorted(daily.items())
            max_daily = max(daily.values()) if daily else 1
            html += """
        <div class="chart-bar">"""
            for date, count in daily_items[-30:]:  # 最近30天
                bar_height = int(count / max(max_daily, 1) * 100)
                html += f'<div class="bar" style="height:{bar_height}%" title="{date}: {count}"></div>'
            html += """
        </div>
        <div class="chart-labels">"""
            for date, count in daily_items[-30:]:
                short_date = date[5:] if len(date) > 5 else date
                html += f"<span>{short_date}</span>"
            html += """
        </div>"""

        html += f"""
        <p style="margin-top:12px;color:#8b949e;">
            活跃天数: {time_trends.get('total_days', 0)} |
            日均会话: {time_trends.get('avg_per_day', 0)} |
            最活跃日: {time_trends.get('most_active_day', ('N/A', 0))[0]} ({time_trends.get('most_active_day', ('N/A', 0))[1]}个)
        </p>
    </div>

    <!-- 每小时分布 -->
    <div class="section">
        <h2>每小时活跃分布 Hourly Distribution</h2>
        <table>
            <tr><th>时段</th><th>会话数</th><th>分布</th></tr>"""

        hourly = time_trends.get("hourly", {})
        if hourly:
            max_hourly = max(hourly.values()) if hourly else 1
            for hour in range(24):
                count = hourly.get(hour, 0)
                bar_width = int(count / max(max_hourly, 1) * 100)
                html += f"""
            <tr>
                <td>{hour:02d}:00 - {hour:02d}:59</td>
                <td>{count}</td>
                <td><div class="bar-container">
                    <div class="bar" style="width:{bar_width}%;max-width:300px;"></div>
                </div></td>
            </tr>"""

        html += """
        </table>
    </div>

    <!-- 热门关键词 -->
    <div class="section">
        <h2>热门关键词 Top Keywords</h2>
        <div style="display:flex;flex-wrap:wrap;gap:4px;">"""

        for topic in topics[:15]:
            size = min(1.5, 0.8 + topic["percentage"] / 50)
            html += f'<span class="tag" style="font-size:{size}em;">{topic["keyword"]} ({topic["frequency"]})</span>'

        html += """
        </div>
    </div>

    <!-- 使用模式 -->
    <div class="section">
        <h2>使用模式 Usage Patterns</h2>
        <div class="cards">
            <div class="card">
                <div class="label">会话长度分布</div>"""

        length_dist = usage.get("session_length_distribution", {})
        for bucket, count in length_dist.items():
            html += f'<div class="value small">{bucket}: {count}</div>'

        html += """
            </div>
            <div class="card">
                <div class="label">Token使用分布</div>"""

        token_dist = usage.get("token_usage_distribution", {})
        for bucket, count in token_dist.items():
            html += f'<div class="value small">{bucket}: {count}</div>'

        html += f"""
            </div>
            <div class="card">
                <div class="label">会话间隔</div>
                <div class="value small">平均: {usage.get("avg_session_interval_hours", 0)}小时</div>
                <div class="value small">中位数: {usage.get("median_session_interval_hours", 0)}小时</div>
            </div>
        </div>
    </div>

    <!-- 最大的文件 -->
    <div class="section">
        <h2>最大的会话文件 Largest Files</h2>
        <table>
            <tr><th>文件</th><th>大小</th></tr>"""

        for path, size in analysis.sessions_by_size[:10]:
            fname = os.path.basename(path)
            html += f"""
            <tr>
                <td>{fname}</td>
                <td>{format_size(size)}</td>
            </tr>"""

        html += """
        </table>
    </div>

    <div class="footer">
        <p>由 SessionPilot 生成 | SessionPilot Report Generator v1.0</p>
    </div>
</div>
</body>
</html>"""
        return html

    def _generate_markdown(
        self,
        analysis: AnalysisResult,
        time_trends: Dict[str, Any],
        topics: List[Dict[str, Any]],
        usage: Dict[str, Any],
        source_analysis: Dict[str, Any],
        title: str,
    ) -> str:
        """生成Markdown报告"""
        lines = []
        lines.append(f"# {title}")
        lines.append("")
        lines.append(f"> 生成时间: {format_timestamp(time.time())}")
        lines.append("")

        # 概览
        lines.append("## 概览")
        lines.append("")
        lines.append(f"| 指标 | 值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 总会话数 | {analysis.total_sessions} |")
        lines.append(f"| 总消息数 | {analysis.total_messages:,} |")
        lines.append(f"| 估算Token总量 | {format_number(analysis.total_tokens_estimate)} |")
        lines.append(f"| 总存储大小 | {analysis.total_size_display} |")
        lines.append(f"| 平均消息/会话 | {analysis.average_messages_per_session:.1f} |")
        lines.append(f"| 时间范围 | {format_timestamp(analysis.oldest_session, '%Y-%m-%d')} ~ {format_timestamp(analysis.newest_session, '%Y-%m-%d')} |")
        lines.append("")

        # 来源分布
        lines.append("## 来源分布")
        lines.append("")
        lines.append("| 来源 | 会话数 | 占比 |")
        lines.append("|------|--------|------|")
        for source, count in analysis.source_distribution.items():
            pct = count / max(analysis.total_sessions, 1) * 100
            lines.append(f"| {source} | {count} | {pct:.1f}% |")
        lines.append("")

        # 时间趋势
        lines.append("## 时间趋势")
        lines.append("")
        lines.append(f"- 活跃天数: {time_trends.get('total_days', 0)}")
        lines.append(f"- 日均会话: {time_trends.get('avg_per_day', 0)}")
        if time_trends.get('most_active_day'):
            day, count = time_trends['most_active_day']
            lines.append(f"- 最活跃日期: {day} ({count}个会话)")
        if time_trends.get('most_active_hour'):
            hour, count = time_trends['most_active_hour']
            lines.append(f"- 最活跃时段: {hour}:00 ({count}个会话)")
        lines.append("")

        # 每日分布
        daily = time_trends.get("daily", {})
        if daily:
            lines.append("### 每日分布")
            lines.append("")
            lines.append("| 日期 | 会话数 |")
            lines.append("|------|--------|")
            for date, count in sorted(daily.items())[-14:]:
                bar = "#" * min(count, 30)
                lines.append(f"| {date} | {count} {bar} |")
            lines.append("")

        # 热门关键词
        lines.append("## 热门关键词")
        lines.append("")
        for topic in topics[:10]:
            lines.append(f"- **{topic['keyword']}**: 出现{topic['frequency']}次, 覆盖{topic['percentage']}%的会话")
        lines.append("")

        # 使用模式
        lines.append("## 使用模式")
        lines.append("")
        length_dist = usage.get("session_length_distribution", {})
        if length_dist:
            lines.append("### 会话长度分布")
            lines.append("")
            for bucket, count in length_dist.items():
                bar = "#" * min(count * 2, 40)
                lines.append(f"- {bucket}: {count} {bar}")
            lines.append("")

        lines.append(f"- 平均会话间隔: {usage.get('avg_session_interval_hours', 0)}小时")
        lines.append(f"- 中位数会话间隔: {usage.get('median_session_interval_hours', 0)}小时")
        lines.append("")

        # 最大文件
        if analysis.sessions_by_size:
            lines.append("## 最大的会话文件")
            lines.append("")
            lines.append("| 文件 | 大小 |")
            lines.append("|------|------|")
            for path, size in analysis.sessions_by_size[:10]:
                fname = os.path.basename(path)
                lines.append(f"| {fname} | {format_size(size)} |")
            lines.append("")

        lines.append("---")
        lines.append("*由 SessionPilot 生成*")

        return "\n".join(lines)
