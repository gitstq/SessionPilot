"""
SessionPilot - CLI入口
轻量级终端AI会话智能管理工具
"""

import argparse
import sys
import os
import time
from typing import Optional

from .scanner import SessionScanner
from .indexer import SessionIndexer
from .searcher import SessionSearcher, SearchOptions
from .analyzer import SessionAnalyzer
from .exporter import SessionExporter
from .cleaner import SessionCleaner, CleanPolicy
from .browser import SessionBrowser
from .reporter import ReportGenerator
from .utils import (
    format_size, format_number, format_timestamp,
    supports_color, color_text, print_table, get_cache_dir
)


def create_parser() -> argparse.ArgumentParser:
    """创建CLI参数解析器"""
    parser = argparse.ArgumentParser(
        prog="sessionpilot",
        description="SessionPilot - 轻量级终端AI会话智能管理工具\n"
                    "SessionPilot - Lightweight Terminal AI Session Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例/Examples:
  %(prog)s scan                    扫描所有AI会话
  %(prog)s scan --source claude    仅扫描Claude会话
  %(prog)s search "关键词"         搜索会话
  %(prog)s analyze                 分析会话统计
  %(prog)s browse                  交互式浏览会话
  %(prog)s export --format md      导出为Markdown
  %(prog)s report --format html    生成HTML报告
  %(prog)s clean --dry-run         预览清理操作
        """,
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version="%(prog)s 1.0.0"
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令/Available commands")

    # scan 命令
    scan_parser = subparsers.add_parser(
        "scan",
        help="扫描AI会话数据 / Scan AI session data",
        description="扫描本地AI编码助手的会话数据目录"
    )
    scan_parser.add_argument(
        "-s", "--source",
        choices=["claude", "codex", "cursor", "windsurf", "all"],
        default="all",
        help="扫描来源 / Source to scan (default: all)"
    )
    scan_parser.add_argument(
        "-d", "--dir",
        action="append",
        default=[],
        metavar="PATH",
        help="自定义扫描目录 / Custom scan directory"
    )
    scan_parser.add_argument(
        "--no-index",
        action="store_true",
        help="不更新索引 / Do not update index"
    )
    scan_parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="静默模式 / Quiet mode"
    )

    # search 命令
    search_parser = subparsers.add_parser(
        "search",
        help="搜索会话 / Search sessions",
        description="使用关键词、正则表达式等搜索会话"
    )
    search_parser.add_argument(
        "keyword",
        nargs="?",
        default="",
        help="搜索关键词 / Search keyword"
    )
    search_parser.add_argument(
        "-r", "--regex",
        default="",
        help="正则表达式搜索 / Regex search pattern"
    )
    search_parser.add_argument(
        "-s", "--source",
        default="",
        help="按来源过滤 / Filter by source"
    )
    search_parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="按标签过滤 / Filter by tag"
    )
    search_parser.add_argument(
        "--after",
        default="",
        help="起始时间 / Start time (e.g., '2024-01-01', '7 days ago')"
    )
    search_parser.add_argument(
        "--before",
        default="",
        help="结束时间 / End time"
    )
    search_parser.add_argument(
        "-n", "--max",
        type=int,
        default=20,
        help="最大结果数 / Max results (default: 20)"
    )
    search_parser.add_argument(
        "--sort",
        choices=["relevance", "time", "size"],
        default="relevance",
        help="排序方式 / Sort by (default: relevance)"
    )
    search_parser.add_argument(
        "--content-only",
        action="store_true",
        help="仅搜索内容 / Search content only"
    )

    # analyze 命令
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="分析会话统计 / Analyze session statistics",
        description="统计会话数量、频率、主题分布、Token使用等"
    )
    analyze_parser.add_argument(
        "-s", "--source",
        default="",
        help="按来源分析 / Analyze specific source"
    )
    analyze_parser.add_argument(
        "--topics",
        action="store_true",
        help="显示主题分析 / Show topic analysis"
    )
    analyze_parser.add_argument(
        "--trends",
        action="store_true",
        help="显示时间趋势 / Show time trends"
    )
    analyze_parser.add_argument(
        "--patterns",
        action="store_true",
        help="显示使用模式 / Show usage patterns"
    )

    # browse 命令
    browse_parser = subparsers.add_parser(
        "browse",
        help="交互式浏览会话 / Interactive session browser",
        description="TUI风格的会话列表浏览，支持键盘导航"
    )
    browse_parser.add_argument(
        "-s", "--source",
        default="",
        help="按来源过滤 / Filter by source"
    )

    # export 命令
    export_parser = subparsers.add_parser(
        "export",
        help="导出会话数据 / Export session data",
        description="导出会话为Markdown、JSON、CSV格式"
    )
    export_parser.add_argument(
        "-f", "--format",
        choices=["markdown", "md", "json", "csv"],
        default="markdown",
        help="导出格式 / Export format (default: markdown)"
    )
    export_parser.add_argument(
        "-o", "--output",
        default="",
        help="输出文件路径 / Output file path"
    )
    export_parser.add_argument(
        "--no-messages",
        action="store_true",
        help="不包含消息内容 / Exclude message content"
    )
    export_parser.add_argument(
        "-s", "--source",
        default="",
        help="按来源过滤 / Filter by source"
    )

    # report 命令
    report_parser = subparsers.add_parser(
        "report",
        help="生成分析报告 / Generate analysis report",
        description="生成HTML、Markdown、JSON格式的分析报告"
    )
    report_parser.add_argument(
        "-f", "--format",
        choices=["html", "markdown", "md", "json"],
        default="html",
        help="报告格式 / Report format (default: html)"
    )
    report_parser.add_argument(
        "-o", "--output",
        default="",
        help="输出文件路径 / Output file path"
    )
    report_parser.add_argument(
        "-t", "--title",
        default="SessionPilot 分析报告",
        help="报告标题 / Report title"
    )

    # clean 命令
    clean_parser = subparsers.add_parser(
        "clean",
        help="清理旧会话 / Clean old sessions",
        description="按时间/大小/数量清理旧会话，释放磁盘空间"
    )
    clean_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行模式 / Dry run mode"
    )
    clean_parser.add_argument(
        "--max-age",
        type=int,
        default=0,
        metavar="DAYS",
        help="最大保留天数 / Max age in days"
    )
    clean_parser.add_argument(
        "--max-size",
        type=float,
        default=0,
        metavar="MB",
        help="最大总大小MB / Max total size in MB"
    )
    clean_parser.add_argument(
        "--max-count",
        type=int,
        default=0,
        help="最大文件数量 / Max file count"
    )
    clean_parser.add_argument(
        "--min-size",
        type=float,
        default=0,
        metavar="KB",
        help="最小文件大小KB，小于此值的将被清理 / Min file size in KB"
    )
    clean_parser.add_argument(
        "-s", "--source",
        default="",
        help="仅清理指定来源 / Clean specific source only"
    )
    clean_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="跳过确认 / Skip confirmation"
    )

    # index 命令
    index_parser = subparsers.add_parser(
        "index",
        help="管理索引 / Manage index",
        description="管理本地会话索引"
    )
    index_parser.add_argument(
        "action",
        choices=["build", "stats", "clean", "clear"],
        help="索引操作 / Index action"
    )

    # info 命令
    info_parser = subparsers.add_parser(
        "info",
        help="显示信息 / Show information",
        description="显示配置和系统信息"
    )

    return parser


def cmd_scan(args) -> int:
    """执行扫描命令"""
    scanner = SessionScanner()

    # 自定义目录
    custom_dirs = {}
    if args.dir:
        custom_dirs["custom"] = args.dir

    # 确定扫描来源
    if args.source == "all":
        sources = None
    else:
        sources = [args.source]

    if not args.quiet:
        print(color_text("正在扫描AI会话数据...", "cyan"))
        print()

    start_time = time.time()
    sessions = scanner.scan_all(sources)
    elapsed = time.time() - start_time

    if not args.quiet:
        stats = scanner.get_scan_stats()
        print(f"扫描完成！耗时 {elapsed:.2f}秒")
        print(f"  扫描文件: {stats['files_scanned']}")
        print(f"  解析成功: {stats['files_parsed']}")
        print(f"  解析失败: {stats['files_failed']}")
        print(f"  发现会话: {stats['sessions_found']}")
        print()

        if sessions:
            print(f"{'来源':<12} {'会话数':>8} {'总大小':>12}")
            print("-" * 34)
            from collections import Counter
            source_counts = Counter(s.source for s in sessions)
            source_sizes = {}
            for s in sessions:
                source_sizes[s.source] = source_sizes.get(s.source, 0) + s.file_size
            for source, count in source_counts.most_common():
                size = source_sizes.get(source, 0)
                print(f"{source:<12} {count:>8} {format_size(size):>12}")

    # 更新索引
    if not args.no_index and sessions:
        indexer = SessionIndexer()
        indexer.load_index()
        indexer.add_sessions(sessions)
        indexer.save_index()
        if not args.quiet:
            print(f"\n索引已更新 ({indexer.total_entries} 条)")

    return 0


def cmd_search(args) -> int:
    """执行搜索命令"""
    indexer = SessionIndexer()
    indexer.load_index()

    if indexer.total_entries == 0:
        print(color_text("索引为空，请先执行 scan 命令。", "yellow"))
        return 1

    searcher = SessionSearcher(indexer)

    options = SearchOptions(
        keyword=args.keyword,
        regex=args.regex,
        source=args.source,
        tags=args.tags,
        start_time_str=args.after,
        end_time_str=args.before,
        max_results=args.max,
        sort_by=args.sort,
    )

    results = searcher.search(options)

    if not results:
        print("没有找到匹配的会话。")
        return 0

    print(f"找到 {len(results)} 个匹配会话:\n")

    rows = []
    for i, r in enumerate(results, 1):
        rows.append([
            str(i),
            r.source,
            truncate_text(r.title, 40),
            format_timestamp(r.session.updated_at or r.session.created_at, "%m-%d %H:%M"),
            str(r.session.message_count),
            format_token_short(r.session.estimated_tokens),
            format_size(r.session.file_size),
        ])

    print_table(
        ["#", "来源", "标题", "时间", "消息", "Token", "大小"],
        rows,
        [4, 10, 42, 16, 6, 10, 10]
    )

    return 0


def cmd_analyze(args) -> int:
    """执行分析命令"""
    indexer = SessionIndexer()
    indexer.load_index()

    if indexer.total_entries == 0:
        print(color_text("索引为空，请先执行 scan 命令。", "yellow"))
        return 1

    analyzer = SessionAnalyzer()
    entries = indexer.get_all_entries()

    # 转换为会话对象
    from .models import Session
    sessions = [
        Session(
            id=e.session_id,
            source=e.source,
            title=e.title,
            created_at=e.created_at,
            updated_at=e.updated_at,
            file_path=e.file_path,
            file_size=e.file_size,
            tags=e.tags,
        )
        for e in entries
    ]

    if args.source:
        sessions = [s for s in sessions if s.source == args.source]

    if not sessions:
        print("没有找到可分析的会话。")
        return 1

    # 基础分析
    print(analyzer.generate_summary(sessions))

    # 主题分析
    if args.topics:
        print("\n主题分析:")
        topics = analyzer.analyze_topics(sessions)
        for topic in topics:
            print(f"  {topic['keyword']}: {topic['frequency']}次, "
                  f"覆盖{topic['percentage']}%的会话")

    # 时间趋势
    if args.trends:
        print("\n时间趋势:")
        trends = analyzer.analyze_time_trends(sessions)
        print(f"  活跃天数: {trends.get('total_days', 0)}")
        print(f"  日均会话: {trends.get('avg_per_day', 0)}")
        if trends.get('most_active_day'):
            day, count = trends['most_active_day']
            print(f"  最活跃日期: {day} ({count}个)")
        if trends.get('most_active_hour'):
            hour, count = trends['most_active_hour']
            print(f"  最活跃时段: {hour}:00 ({count}个)")

    # 使用模式
    if args.patterns:
        print("\n使用模式:")
        patterns = analyzer.analyze_usage_patterns(sessions)
        length_dist = patterns.get("session_length_distribution", {})
        if length_dist:
            print("  会话长度分布:")
            for bucket, count in length_dist.items():
                bar = "#" * min(count * 2, 30)
                print(f"    {bucket}: {count} {bar}")

    return 0


def cmd_browse(args) -> int:
    """执行浏览命令"""
    indexer = SessionIndexer()
    indexer.load_index()

    if indexer.total_entries == 0:
        print(color_text("索引为空，请先执行 scan 命令。", "yellow"))
        return 1

    entries = indexer.get_all_entries()

    if args.source:
        entries = [e for e in entries if e.source == args.source]

    if not entries:
        print("没有可浏览的会话。")
        return 1

    from .models import Session
    sessions = [
        Session(
            id=e.session_id,
            source=e.source,
            title=e.title,
            created_at=e.created_at,
            updated_at=e.updated_at,
            file_path=e.file_path,
            file_size=e.file_size,
            tags=e.tags,
        )
        for e in entries
    ]

    browser = SessionBrowser(sessions)
    browser.browse()

    return 0


def cmd_export(args) -> int:
    """执行导出命令"""
    indexer = SessionIndexer()
    indexer.load_index()

    if indexer.total_entries == 0:
        print(color_text("索引为空，请先执行 scan 命令。", "yellow"))
        return 1

    entries = indexer.get_all_entries()

    if args.source:
        entries = [e for e in entries if e.source == args.source]

    if not entries:
        print("没有可导出的会话。")
        return 1

    from .models import Session
    sessions = [
        Session(
            id=e.session_id,
            source=e.source,
            title=e.title,
            created_at=e.created_at,
            updated_at=e.updated_at,
            file_path=e.file_path,
            file_size=e.file_size,
            tags=e.tags,
        )
        for e in entries
    ]

    exporter = SessionExporter()
    try:
        output_path = exporter.export_sessions(
            sessions=sessions,
            format=args.format,
            output_path=args.output or None,
            include_messages=not args.no_messages,
        )
        print(f"导出成功: {output_path}")
        print(f"  会话数: {len(sessions)}")
        print(f"  格式: {args.format}")
        return 0
    except ValueError as e:
        print(f"导出失败: {e}")
        return 1


def cmd_report(args) -> int:
    """执行报告命令"""
    indexer = SessionIndexer()
    indexer.load_index()

    if indexer.total_entries == 0:
        print(color_text("索引为空，请先执行 scan 命令。", "yellow"))
        return 1

    entries = indexer.get_all_entries()

    from .models import Session
    sessions = [
        Session(
            id=e.session_id,
            source=e.source,
            title=e.title,
            created_at=e.created_at,
            updated_at=e.updated_at,
            file_path=e.file_path,
            file_size=e.file_size,
            tags=e.tags,
        )
        for e in entries
    ]

    reporter = ReportGenerator()
    try:
        output_path = reporter.generate_report(
            sessions=sessions,
            format=args.format,
            output_path=args.output or None,
            title=args.title,
        )
        print(f"报告已生成: {output_path}")
        return 0
    except ValueError as e:
        print(f"报告生成失败: {e}")
        return 1


def cmd_clean(args) -> int:
    """执行清理命令"""
    indexer = SessionIndexer()
    indexer.load_index()

    if indexer.total_entries == 0:
        print(color_text("索引为空，请先执行 scan 命令。", "yellow"))
        return 1

    entries = indexer.get_all_entries()

    from .models import Session
    sessions = [
        Session(
            id=e.session_id,
            source=e.source,
            title=e.title,
            created_at=e.created_at,
            updated_at=e.updated_at,
            file_path=e.file_path,
            file_size=e.file_size,
            tags=e.tags,
        )
        for e in entries
    ]

    policy = CleanPolicy(
        max_age_days=args.max_age,
        max_total_size_mb=args.max_size,
        max_file_count=args.max_count,
        min_file_size_kb=args.min_size,
        dry_run=args.dry_run,
        source=args.source,
    )

    cleaner = SessionCleaner(indexer)

    # 预览
    preview = cleaner.preview_clean(sessions, policy)
    print(f"将{'[试运行] ' if policy.dry_run else ''}清理 {preview['would_delete']} 个会话文件")
    print(f"将释放: {preview['would_free_display']}")
    print()

    if preview['by_source']:
        print("按来源:")
        for source, count in preview['by_source'].items():
            print(f"  {source}: {count}个")

    if preview['files']:
        print(f"\n部分文件:")
        for f in preview['files'][:10]:
            print(f"  {f['path']} ({f['size']})")

    if not args.dry_run and not args.yes:
        print()
        confirm = input("确认清理? (y/N): ").strip().lower()
        if confirm != "y":
            print("已取消。")
            return 0

    result = cleaner.clean(sessions, policy)
    print(f"\n清理完成:")
    print(f"  删除文件: {result.deleted_count}")
    print(f"  释放空间: {result.freed_display}")
    if result.failed_count > 0:
        print(f"  失败: {result.failed_count}")
        for err in result.errors[:5]:
            print(f"    - {err}")

    # 保存索引
    indexer.save_index()

    return 0


def cmd_index(args) -> int:
    """执行索引管理命令"""
    indexer = SessionIndexer()

    if args.action == "build":
        print("正在构建索引...")
        scanner = SessionScanner()
        sessions = scanner.scan_all()
        indexer.load_index()
        count = indexer.add_sessions(sessions)
        indexer.save_index()
        print(f"索引构建完成: {count} 条记录")

    elif args.action == "stats":
        indexer.load_index()
        stats = indexer.get_stats()
        print("索引统计:")
        print(f"  总条目: {stats['total_entries']}")
        print(f"  来源: {stats['sources']}")
        print(f"  标签数: {stats['total_tags']}")
        print(f"  索引路径: {stats['index_path']}")

    elif args.action == "clean":
        indexer.load_index()
        removed = indexer.cleanup_missing()
        indexer.save_index()
        print(f"清理完成: 移除了 {removed} 个无效索引条目")

    elif args.action == "clear":
        indexer.load_index()
        indexer.clear_index()
        indexer.save_index()
        print("索引已清空。")

    return 0


def cmd_info(args) -> int:
    """显示信息"""
    import platform

    print("SessionPilot v1.0.0")
    print("=" * 40)
    print(f"Python版本: {platform.python_version()}")
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"架构: {platform.machine()}")
    print(f"配置目录: {get_cache_dir()}")
    print(f"终端颜色: {'支持' if supports_color() else '不支持'}")
    print()

    # 检查各来源目录
    from .utils import get_all_source_dirs
    all_dirs = get_all_source_dirs()
    print("AI工具数据目录:")
    for source, dirs in all_dirs.items():
        exists = [d for d in dirs if os.path.isdir(d)]
        status = f"{len(exists)}/{len(dirs)} 存在"
        print(f"  {source}: {status}")
        for d in dirs:
            mark = "✓" if os.path.isdir(d) else "✗"
            print(f"    [{mark}] {d}")

    return 0


def truncate_text(text: str, max_length: int) -> str:
    """截断文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def format_token_short(tokens: int) -> str:
    """格式化Token数量"""
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    elif tokens >= 1_000:
        return f"{tokens / 1_000:.1f}K"
    return str(tokens)


def main(argv: Optional[list] = None) -> int:
    """主入口函数"""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    # 命令分发
    commands = {
        "scan": cmd_scan,
        "search": cmd_search,
        "analyze": cmd_analyze,
        "browse": cmd_browse,
        "export": cmd_export,
        "report": cmd_report,
        "clean": cmd_clean,
        "index": cmd_index,
        "info": cmd_info,
    }

    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    try:
        return handler(args)
    except KeyboardInterrupt:
        print("\n操作已取消。")
        return 130
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
