"""
SessionPilot - 轻量级终端AI会话智能管理工具
SessionPilot - Lightweight Terminal AI Session Manager

零依赖的Python CLI工具，用于管理、搜索、分析和导出
终端AI编码助手的会话历史。
"""

__version__ = "1.0.0"
__author__ = "SessionPilot Team"

from .cli import main
from .scanner import SessionScanner
from .indexer import SessionIndexer
from .searcher import SessionSearcher
from .analyzer import SessionAnalyzer
from .exporter import SessionExporter
from .cleaner import SessionCleaner
from .browser import SessionBrowser
from .reporter import ReportGenerator
from .models import Session, Message, IndexEntry, AnalysisResult

__all__ = [
    "main",
    "SessionScanner",
    "SessionIndexer",
    "SessionSearcher",
    "SessionAnalyzer",
    "SessionExporter",
    "SessionCleaner",
    "SessionBrowser",
    "ReportGenerator",
    "Session",
    "Message",
    "IndexEntry",
    "AnalysisResult",
]
