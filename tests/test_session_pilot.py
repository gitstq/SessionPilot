"""
SessionPilot 完整单元测试
覆盖所有模块的核心功能
"""

import json
import os
import sys
import time
import tempfile
import shutil
import unittest

# 确保可以导入包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from session_pilot.models import (
    Session, Message, IndexEntry, AnalysisResult, CleanResult,
    SessionSource, MessageRole
)
from session_pilot.utils import (
    format_size, format_number, format_timestamp, parse_time_str,
    time_range_filter, get_date_key, get_hour_key, estimate_tokens,
    extract_keywords, truncate_text, generate_id, generate_file_hash,
    safe_read_file, safe_write_file, safe_read_json, safe_write_json,
    get_file_size, get_file_mtime, ensure_dir, color_text, supports_color,
    get_home_dir, get_config_dir, get_cache_dir, DEFAULT_SOURCE_DIRS,
    get_source_dirs, get_all_source_dirs, print_table
)
from session_pilot.scanner import SessionScanner
from session_pilot.indexer import SessionIndexer
from session_pilot.searcher import SessionSearcher, SearchOptions, SearchResult
from session_pilot.analyzer import SessionAnalyzer
from session_pilot.exporter import SessionExporter
from session_pilot.cleaner import SessionCleaner, CleanPolicy
from session_pilot.browser import SessionBrowser, format_token_short
from session_pilot.reporter import ReportGenerator
from session_pilot.cli import create_parser, main


class TestModels(unittest.TestCase):
    """数据模型测试"""

    def test_message_creation(self):
        """测试消息创建"""
        msg = Message(
            role="user",
            content="Hello, how are you?",
            timestamp=1700000000.0,
            token_count=10
        )
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "Hello, how are you?")
        self.assertEqual(msg.timestamp, 1700000000.0)
        self.assertEqual(msg.token_count, 10)

    def test_message_to_dict(self):
        """测试消息序列化"""
        msg = Message(role="assistant", content="I'm fine")
        d = msg.to_dict()
        self.assertEqual(d["role"], "assistant")
        self.assertEqual(d["content"], "I'm fine")

    def test_message_from_dict(self):
        """测试消息反序列化"""
        d = {"role": "system", "content": "Be helpful", "token_count": 5}
        msg = Message.from_dict(d)
        self.assertEqual(msg.role, "system")
        self.assertEqual(msg.content, "Be helpful")
        self.assertEqual(msg.token_count, 5)

    def test_message_display_str(self):
        """测试消息显示字符串"""
        msg = Message(role="user", content="A" * 300)
        display = msg.to_display_str(100)
        self.assertTrue(display.endswith("..."))
        self.assertTrue(display.startswith("[user]"))

    def test_session_creation(self):
        """测试会话创建"""
        session = Session(
            id="test123",
            source="claude",
            title="Test Session",
            created_at=1700000000.0,
            updated_at=1700001000.0,
            file_path="/tmp/test.json",
            file_size=1024,
            tags=["test", "demo"]
        )
        self.assertEqual(session.id, "test123")
        self.assertEqual(session.source, "claude")
        self.assertEqual(session.title, "Test Session")
        self.assertEqual(len(session.tags), 2)

    def test_session_properties(self):
        """测试会话属性"""
        session = Session(
            created_at=1700000000.0,
            updated_at=1700001000.0,
        )
        session.messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there"),
        ]
        self.assertEqual(session.message_count, 2)
        self.assertEqual(session.total_tokens, 0)
        self.assertGreater(session.estimated_tokens, 0)
        self.assertIsNotNone(session.duration_minutes)

    def test_session_time_strings(self):
        """测试会话时间格式化"""
        session = Session(created_at=1700000000.0, updated_at=1700001000.0)
        self.assertIn("2023", session.created_time_str)
        self.assertIn("2023", session.updated_time_str)

    def test_session_empty_time(self):
        """测试空时间"""
        session = Session()
        self.assertEqual(session.created_time_str, "未知")
        self.assertEqual(session.updated_time_str, "未知")
        self.assertIsNone(session.duration_minutes)

    def test_session_preview(self):
        """测试会话预览"""
        session = Session()
        session.messages = [Message(role="user", content="Hello world")]
        self.assertEqual(session.get_preview(50), "Hello world")

        session2 = Session()
        self.assertEqual(session2.get_preview(), "(空会话)")

    def test_session_to_from_dict(self):
        """测试会话序列化/反序列化"""
        session = Session(
            id="abc",
            source="codex",
            title="Test",
            messages=[Message(role="user", content="Hi")],
            tags=["t1"]
        )
        d = session.to_dict()
        self.assertEqual(d["id"], "abc")
        self.assertEqual(len(d["messages"]), 1)

        restored = Session.from_dict(d)
        self.assertEqual(restored.id, "abc")
        self.assertEqual(restored.source, "codex")
        self.assertEqual(len(restored.messages), 1)
        self.assertEqual(restored.messages[0].role, "user")

    def test_index_entry_from_session(self):
        """测试索引条目从会话创建"""
        session = Session(
            id="xyz",
            source="cursor",
            title="Cursor Session",
            file_path="/tmp/cursor.json",
            file_size=2048,
            messages=[Message(role="user", content="Help me code")]
        )
        entry = IndexEntry.from_session(session)
        self.assertEqual(entry.session_id, "xyz")
        self.assertEqual(entry.source, "cursor")
        self.assertEqual(entry.title, "Cursor Session")
        self.assertEqual(entry.message_count, 1)
        self.assertGreater(entry.token_estimate, 0)

    def test_analysis_result(self):
        """测试分析结果"""
        result = AnalysisResult(
            total_sessions=10,
            total_messages=100,
            total_tokens_estimate=5000,
            total_size_bytes=1024 * 1024 * 5,
        )
        self.assertEqual(result.total_size_mb, 5.0)
        self.assertIn("MB", result.total_size_display)

    def test_analysis_result_small_size(self):
        """测试小文件大小显示"""
        result = AnalysisResult(total_size_bytes=512)
        self.assertEqual(result.total_size_display, "512 B")

    def test_clean_result(self):
        """测试清理结果"""
        result = CleanResult(
            deleted_count=5,
            freed_bytes=1024 * 1024 * 10,
        )
        self.assertEqual(result.freed_mb, 10.0)
        self.assertIn("MB", result.freed_display)

    def test_session_source_enum(self):
        """测试来源枚举"""
        self.assertEqual(SessionSource.CLAUDE.value, "claude")
        self.assertEqual(SessionSource.CODEX.value, "codex")
        self.assertEqual(SessionSource.CURSOR.value, "cursor")
        self.assertEqual(SessionSource.WINDSURF.value, "windsurf")

    def test_message_role_enum(self):
        """测试角色枚举"""
        self.assertEqual(MessageRole.USER.value, "user")
        self.assertEqual(MessageRole.ASSISTANT.value, "assistant")
        self.assertEqual(MessageRole.SYSTEM.value, "system")


class TestUtils(unittest.TestCase):
    """工具函数测试"""

    def setUp(self):
        """创建临时目录"""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_format_size(self):
        """测试大小格式化"""
        self.assertEqual(format_size(0), "0 B")
        self.assertEqual(format_size(512), "512 B")
        self.assertEqual(format_size(1024), "1.00 KB")
        self.assertEqual(format_size(1536), "1.50 KB")
        self.assertEqual(format_size(1048576), "1.00 MB")
        self.assertEqual(format_size(1073741824), "1.00 GB")

    def test_format_number(self):
        """测试数字格式化"""
        self.assertEqual(format_number(100), "100")
        self.assertEqual(format_number(1500), "1.5K")
        self.assertEqual(format_number(2000000), "2.0M")

    def test_format_timestamp(self):
        """测试时间戳格式化"""
        result = format_timestamp(1700000000.0)
        self.assertIn("2023", result)
        self.assertEqual(format_timestamp(None), "未知")

    def test_parse_time_str_timestamp(self):
        """测试解析时间戳"""
        result = parse_time_str("1700000000")
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result, 1700000000.0)

    def test_parse_time_str_date(self):
        """测试解析日期字符串"""
        result = parse_time_str("2024-01-15")
        self.assertIsNotNone(result)
        self.assertGreater(result, 1700000000.0)

    def test_parse_time_str_datetime(self):
        """测试解析日期时间字符串"""
        result = parse_time_str("2024-01-15 10:30:00")
        self.assertIsNotNone(result)

    def test_parse_time_str_relative_days(self):
        """测试解析相对时间（天）"""
        result = parse_time_str("7 days ago")
        self.assertIsNotNone(result)
        expected = time.time() - 7 * 86400
        self.assertAlmostEqual(result, expected, delta=10)

    def test_parse_time_str_relative_hours(self):
        """测试解析相对时间（小时）"""
        result = parse_time_str("3 hours ago")
        self.assertIsNotNone(result)
        expected = time.time() - 3 * 3600
        self.assertAlmostEqual(result, expected, delta=10)

    def test_parse_time_str_empty(self):
        """测试解析空字符串"""
        self.assertIsNone(parse_time_str(""))
        self.assertIsNone(parse_time_str(None))

    def test_parse_time_str_chinese(self):
        """测试解析中文相对时间"""
        result = parse_time_str("3天 ago")
        self.assertIsNotNone(result)

    def test_time_range_filter(self):
        """测试时间范围过滤"""
        now = time.time()
        self.assertTrue(time_range_filter(now, now - 3600, now + 3600))
        self.assertFalse(time_range_filter(now - 7200, now - 3600, now))
        self.assertTrue(time_range_filter(now, None, None))
        self.assertFalse(time_range_filter(None, now - 3600, now))

    def test_get_date_key(self):
        """测试日期键"""
        result = get_date_key(1700000000.0)
        self.assertEqual(len(result), 10)  # YYYY-MM-DD
        self.assertEqual(get_date_key(None), "unknown")

    def test_get_hour_key(self):
        """测试小时键"""
        result = get_hour_key(1700000000.0)
        self.assertGreaterEqual(result, 0)
        self.assertLessEqual(result, 23)
        self.assertEqual(get_hour_key(None), -1)

    def test_estimate_tokens(self):
        """测试Token估算"""
        self.assertEqual(estimate_tokens(""), 0)
        self.assertEqual(estimate_tokens("hello"), 1)
        self.assertEqual(estimate_tokens("a" * 100), 25)

    def test_extract_keywords_english(self):
        """测试英文关键词提取"""
        text = "python programming language python code function class"
        keywords = extract_keywords(text, top_n=5)
        self.assertIsInstance(keywords, list)
        self.assertGreater(len(keywords), 0)
        # python应该出现
        kw_list = [kw for kw, _ in keywords]
        self.assertIn("python", kw_list)

    def test_extract_keywords_chinese(self):
        """测试中文关键词提取"""
        text = "人工智能 机器学习 深度学习 人工智能 神经网络"
        keywords = extract_keywords(text, top_n=5)
        self.assertGreater(len(keywords), 0)

    def test_extract_keywords_empty(self):
        """测试空文本关键词提取"""
        self.assertEqual(extract_keywords(""), [])

    def test_truncate_text(self):
        """测试文本截断"""
        self.assertEqual(truncate_text("hello", 10), "hello")
        self.assertEqual(truncate_text("a" * 100, 10), "aaaaaaa...")

    def test_generate_id(self):
        """测试ID生成"""
        id1 = generate_id("claude", "/tmp/test.json")
        id2 = generate_id("claude", "/tmp/test.json")
        self.assertEqual(id1, id2)
        self.assertEqual(len(id1), 16)

        id3 = generate_id("codex", "/tmp/other.json")
        self.assertNotEqual(id1, id3)

    def test_safe_read_write_file(self):
        """测试安全文件读写"""
        path = os.path.join(self.test_dir, "test.txt")
        self.assertTrue(safe_write_file(path, "hello world"))
        content = safe_read_file(path)
        self.assertEqual(content, "hello world")

    def test_safe_read_nonexistent(self):
        """测试读取不存在的文件"""
        self.assertIsNone(safe_read_file("/nonexistent/file.txt"))

    def test_safe_read_write_json(self):
        """测试JSON文件读写"""
        path = os.path.join(self.test_dir, "test.json")
        data = {"key": "value", "number": 42}
        self.assertTrue(safe_write_json(path, data))
        loaded = safe_read_json(path)
        self.assertEqual(loaded["key"], "value")
        self.assertEqual(loaded["number"], 42)

    def test_safe_read_invalid_json(self):
        """测试读取无效JSON"""
        path = os.path.join(self.test_dir, "bad.json")
        safe_write_file(path, "not json")
        self.assertIsNone(safe_read_json(path))

    def test_get_file_size(self):
        """测试获取文件大小"""
        path = os.path.join(self.test_dir, "size_test.txt")
        safe_write_file(path, "a" * 100)
        self.assertEqual(get_file_size(path), 100)
        self.assertEqual(get_file_size("/nonexistent"), 0)

    def test_get_file_mtime(self):
        """测试获取文件修改时间"""
        path = os.path.join(self.test_dir, "mtime_test.txt")
        safe_write_file(path, "test")
        mtime = get_file_mtime(path)
        self.assertIsNotNone(mtime)
        self.assertGreater(mtime, 0)
        self.assertIsNone(get_file_mtime("/nonexistent"))

    def test_ensure_dir(self):
        """测试确保目录存在"""
        new_dir = os.path.join(self.test_dir, "sub", "dir")
        self.assertTrue(ensure_dir(new_dir))
        self.assertTrue(os.path.isdir(new_dir))

    def test_color_text(self):
        """测试彩色文本"""
        result = color_text("hello", "red")
        self.assertIn("hello", result)
        self.assertIn("\033", result)
        self.assertEqual(color_text("hello", "unknown_color"), "hello")

    def test_get_home_dir(self):
        """测试获取主目录"""
        home = get_home_dir()
        self.assertTrue(os.path.isdir(home))

    def test_get_config_dir(self):
        """测试获取配置目录"""
        config = get_config_dir()
        self.assertIsInstance(config, str)
        self.assertIn("sessionpilot", config.lower())

    def test_get_cache_dir(self):
        """测试获取缓存目录"""
        cache = get_cache_dir()
        self.assertIsInstance(cache, str)
        self.assertIn("sessionpilot", cache.lower())

    def test_get_source_dirs(self):
        """测试获取来源目录"""
        dirs = get_source_dirs("claude")
        self.assertIsInstance(dirs, list)
        self.assertGreater(len(dirs), 0)
        # 所有目录应该展开~
        for d in dirs:
            self.assertFalse(d.startswith("~"))

    def test_get_all_source_dirs(self):
        """测试获取所有来源目录"""
        all_dirs = get_all_source_dirs()
        self.assertIn("claude", all_dirs)
        self.assertIn("codex", all_dirs)
        self.assertIn("cursor", all_dirs)
        self.assertIn("windsurf", all_dirs)

    def test_print_table(self):
        """测试表格打印（不崩溃）"""
        headers = ["名称", "值"]
        rows = [["a", "1"], ["b", "2"]]
        # 只测试不崩溃
        print_table(headers, rows)
        print_table(headers, [])  # 空行

    def test_generate_file_hash(self):
        """测试文件哈希"""
        path = os.path.join(self.test_dir, "hash_test.txt")
        safe_write_file(path, "test content")
        h = generate_file_hash(path)
        self.assertEqual(len(h), 12)
        # 相同内容相同哈希
        path2 = os.path.join(self.test_dir, "hash_test2.txt")
        safe_write_file(path2, "test content")
        self.assertEqual(generate_file_hash(path), generate_file_hash(path2))


class TestScanner(unittest.TestCase):
    """会话扫描器测试"""

    def setUp(self):
        """创建临时测试目录和文件"""
        self.test_dir = tempfile.mkdtemp()
        self.scanner = SessionScanner()

    def tearDown(self):
        """清理"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_json_session(self, filename, data):
        """创建JSON会话文件"""
        path = os.path.join(self.test_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return path

    def _create_jsonl_session(self, filename, lines):
        """创建JSONL会话文件"""
        path = os.path.join(self.test_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
        return path

    def test_scan_json_with_messages(self):
        """测试扫描带消息的JSON文件"""
        data = {
            "title": "Test Session",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there! How can I help?"},
            ],
            "created_at": 1700000000.0,
            "tags": ["test"]
        }
        self._create_json_session("session_001.json", data)
        sessions = self.scanner.scan_directory(self.test_dir, "claude")
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].title, "Test Session")
        self.assertEqual(sessions[0].message_count, 2)
        self.assertEqual(sessions[0].source, "claude")
        self.assertEqual(sessions[0].tags, ["test"])

    def test_scan_json_conversation_field(self):
        """测试扫描使用conversation字段的JSON"""
        data = {
            "name": "My Chat",
            "conversation": [
                {"role": "human", "content": "Question"},
                {"role": "ai", "content": "Answer"},
            ]
        }
        self._create_json_session("chat_002.json", data)
        sessions = self.scanner.scan_directory(self.test_dir, "codex")
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].title, "My Chat")
        self.assertEqual(sessions[0].message_count, 2)

    def test_scan_jsonl_file(self):
        """测试扫描JSONL文件"""
        lines = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "First response"},
            {"role": "user", "content": "Second message"},
        ]
        self._create_jsonl_session("log_003.jsonl", lines)
        sessions = self.scanner.scan_directory(self.test_dir, "claude")
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].message_count, 3)

    def test_scan_json_list_format(self):
        """测试扫描JSON列表格式"""
        data = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "World"},
        ]
        self._create_json_session("list_004.json", data)
        sessions = self.scanner.scan_directory(self.test_dir, "claude")
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].message_count, 2)

    def test_scan_empty_file(self):
        """测试扫描空文件"""
        path = os.path.join(self.test_dir, "empty.json")
        with open(path, "w") as f:
            pass
        sessions = self.scanner.scan_directory(self.test_dir, "claude")
        self.assertEqual(len(sessions), 0)

    def test_scan_non_json_file(self):
        """测试扫描非JSON文件"""
        path = os.path.join(self.test_dir, "readme.txt")
        with open(path, "w") as f:
            f.write("not a json file")
        sessions = self.scanner.scan_directory(self.test_dir, "claude")
        self.assertEqual(len(sessions), 0)

    def test_scan_nested_directories(self):
        """测试递归扫描嵌套目录"""
        nested = os.path.join(self.test_dir, "sub", "dir")
        os.makedirs(nested, exist_ok=True)
        data = {"messages": [{"role": "user", "content": "Nested test"}]}
        path = os.path.join(nested, "deep_session.json")
        with open(path, "w") as f:
            json.dump(data, f)
        sessions = self.scanner.scan_directory(self.test_dir, "claude")
        self.assertEqual(len(sessions), 1)

    def test_scan_multiple_files(self):
        """测试扫描多个文件"""
        for i in range(5):
            data = {
                "title": f"Session {i}",
                "messages": [{"role": "user", "content": f"Message {i}"}]
            }
            self._create_json_session(f"session_{i:03d}.json", data)
        sessions = self.scanner.scan_directory(self.test_dir, "claude")
        self.assertEqual(len(sessions), 5)

    def test_scan_with_metadata(self):
        """测试扫描带元数据的文件"""
        data = {
            "title": "Meta Session",
            "messages": [{"role": "user", "content": "test"}],
            "custom_field": "custom_value",
            "model": "gpt-4",
        }
        self._create_json_session("meta_session.json", data)
        sessions = self.scanner.scan_directory(self.test_dir, "claude")
        self.assertEqual(len(sessions), 1)
        self.assertIn("custom_field", sessions[0].metadata)

    def test_scan_stats(self):
        """测试扫描统计"""
        data = {"messages": [{"role": "user", "content": "test"}]}
        self._create_json_session("s1.json", data)
        self._create_json_session("s2.json", data)
        self.scanner.scan_directory(self.test_dir, "claude")
        stats = self.scanner.get_scan_stats()
        self.assertEqual(stats["files_scanned"], 2)
        self.assertEqual(stats["files_parsed"], 2)
        self.assertEqual(stats["sessions_found"], 2)

    def test_scan_nonexistent_dir(self):
        """测试扫描不存在的目录"""
        sessions = self.scanner.scan_directory("/nonexistent/dir", "claude")
        self.assertEqual(len(sessions), 0)

    def test_scan_custom_dirs(self):
        """测试自定义目录扫描"""
        data = {"messages": [{"role": "user", "content": "custom"}]}
        self._create_json_session("custom.json", data)
        scanner = SessionScanner(custom_dirs={"custom": [self.test_dir]})
        sessions = scanner.scan_source("custom")
        self.assertEqual(len(sessions), 1)

    def test_scan_source_no_dirs(self):
        """测试扫描不存在的来源"""
        scanner = SessionScanner()
        sessions = scanner.scan_source("claude")
        # 默认目录可能不存在，所以可能返回空列表
        self.assertIsInstance(sessions, list)

    def test_message_extraction_various_roles(self):
        """测试各种角色名称提取"""
        role_tests = [
            ("user", "user"),
            ("human", "user"),
            ("assistant", "assistant"),
            ("ai", "assistant"),
            ("system", "system"),
        ]
        for input_role, expected in role_tests:
            # 每个角色使用独立子目录，避免文件累积
            sub_dir = os.path.join(self.test_dir, f"role_test_{input_role}")
            os.makedirs(sub_dir, exist_ok=True)
            data = {"messages": [{"role": input_role, "content": "test"}]}
            path = os.path.join(sub_dir, "session.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            sessions = self.scanner.scan_directory(sub_dir, "claude")
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0].messages[0].role, expected,
                             f"角色 '{input_role}' 应映射到 '{expected}'")

    def test_message_extraction_various_content_fields(self):
        """测试各种内容字段名"""
        content_fields = ["content", "text", "message", "body"]
        for field in content_fields:
            sub_dir = os.path.join(self.test_dir, f"content_test_{field}")
            os.makedirs(sub_dir, exist_ok=True)
            data = {"messages": [{field: f"test_{field}"}]}
            path = os.path.join(sub_dir, "session.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            sessions = self.scanner.scan_directory(sub_dir, "claude")
            self.assertEqual(len(sessions), 1)
            self.assertIn(f"test_{field}", sessions[0].messages[0].content)


class TestIndexer(unittest.TestCase):
    """索引引擎测试"""

    def setUp(self):
        """创建临时索引目录"""
        self.test_dir = tempfile.mkdtemp()
        self.indexer = SessionIndexer(index_dir=self.test_dir)

    def tearDown(self):
        """清理"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _make_session(self, sid="s1", source="claude", title="Test"):
        """创建测试会话"""
        return Session(
            id=sid,
            source=source,
            title=title,
            created_at=time.time(),
            updated_at=time.time(),
            file_path=f"/tmp/{sid}.json",
            file_size=1024,
            tags=[f"tag_{sid}"],
            messages=[Message(role="user", content=f"Content for {sid}")]
        )

    def test_add_and_get_session(self):
        """测试添加和获取会话"""
        session = self._make_session()
        entry = self.indexer.add_session(session)
        self.assertEqual(entry.session_id, "s1")

        retrieved = self.indexer.get_entry("s1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.title, "Test")

    def test_add_multiple_sessions(self):
        """测试批量添加"""
        sessions = [self._make_session(f"s{i}", title=f"Session {i}") for i in range(10)]
        count = self.indexer.add_sessions(sessions)
        self.assertEqual(count, 10)
        self.assertEqual(self.indexer.total_entries, 10)

    def test_remove_session(self):
        """测试移除会话"""
        session = self._make_session()
        self.indexer.add_session(session)
        self.assertTrue(self.indexer.remove_session("s1"))
        self.assertIsNone(self.indexer.get_entry("s1"))
        self.assertFalse(self.indexer.remove_session("nonexistent"))

    def test_get_entries_by_source(self):
        """测试按来源获取"""
        self.indexer.add_session(self._make_session("s1", "claude"))
        self.indexer.add_session(self._make_session("s2", "codex"))
        self.indexer.add_session(self._make_session("s3", "claude"))

        claude_entries = self.indexer.get_entries_by_source("claude")
        self.assertEqual(len(claude_entries), 2)

        codex_entries = self.indexer.get_entries_by_source("codex")
        self.assertEqual(len(codex_entries), 1)

    def test_get_entries_by_tag(self):
        """测试按标签获取"""
        s1 = self._make_session("s1")
        s1.tags = ["python", "test"]
        s2 = self._make_session("s2")
        s2.tags = ["python", "demo"]
        self.indexer.add_session(s1)
        self.indexer.add_session(s2)

        python_entries = self.indexer.get_entries_by_tag("python")
        self.assertEqual(len(python_entries), 2)

        test_entries = self.indexer.get_entries_by_tag("test")
        self.assertEqual(len(test_entries), 1)

    def test_search_by_keyword(self):
        """测试关键词搜索"""
        self.indexer.add_session(self._make_session("s1", title="Python Programming"))
        self.indexer.add_session(self._make_session("s2", title="Java Development"))
        self.indexer.add_session(self._make_session("s3", title="Python Testing"))

        results = self.indexer.search_by_keyword("python")
        self.assertEqual(len(results), 2)

    def test_search_by_time_range(self):
        """测试时间范围搜索"""
        old_time = time.time() - 86400 * 30
        new_time = time.time()
        s1 = self._make_session("s1")
        s1.created_at = old_time
        s1.updated_at = old_time
        s2 = self._make_session("s2")
        s2.created_at = new_time
        s2.updated_at = new_time
        self.indexer.add_session(s1)
        self.indexer.add_session(s2)

        results = self.indexer.search_by_time_range(
            start_time=time.time() - 86400 * 7
        )
        self.assertEqual(len(results), 1)

    def test_save_and_load_index(self):
        """测试索引保存和加载"""
        sessions = [self._make_session(f"s{i}") for i in range(5)]
        self.indexer.add_sessions(sessions)
        self.assertTrue(self.indexer.save_index())

        # 创建新的indexer实例并加载
        new_indexer = SessionIndexer(index_dir=self.test_dir)
        self.assertTrue(new_indexer.load_index())
        self.assertEqual(new_indexer.total_entries, 5)

    def test_get_all_entries(self):
        """测试获取所有条目"""
        sessions = [self._make_session(f"s{i}") for i in range(3)]
        self.indexer.add_sessions(sessions)
        entries = self.indexer.get_all_entries()
        self.assertEqual(len(entries), 3)

    def test_cleanup_missing(self):
        """测试清理缺失文件"""
        session = self._make_session()
        session.file_path = "/nonexistent/file.json"
        self.indexer.add_session(session)
        removed = self.indexer.cleanup_missing()
        self.assertEqual(removed, 1)
        self.assertEqual(self.indexer.total_entries, 0)

    def test_get_stats(self):
        """测试获取统计"""
        self.indexer.add_session(self._make_session("s1", "claude"))
        self.indexer.add_session(self._make_session("s2", "codex"))
        stats = self.indexer.get_stats()
        self.assertEqual(stats["total_entries"], 2)
        self.assertIn("claude", stats["sources"])

    def test_clear_index(self):
        """测试清空索引"""
        self.indexer.add_session(self._make_session())
        self.indexer.clear_index()
        self.assertEqual(self.indexer.total_entries, 0)

    def test_index_entry_keywords(self):
        """测试索引条目关键词提取"""
        session = self._make_session()
        session.messages = [
            Message(role="user", content="python function class decorator"),
            Message(role="assistant", content="python class method inheritance"),
        ]
        entry = self.indexer.add_session(session)
        self.assertGreater(len(entry.keywords), 0)
        # python应该在关键词中
        self.assertIn("python", [kw.lower() for kw in entry.keywords])


class TestSearcher(unittest.TestCase):
    """搜索引擎测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.indexer = SessionIndexer(index_dir=self.test_dir)
        self.searcher = SessionSearcher(self.indexer)

        # 添加测试会话
        sessions = [
            Session(
                id="s1", source="claude", title="Python Programming Help",
                created_at=time.time() - 86400 * 5,
                updated_at=time.time() - 86400 * 5,
                file_path="/tmp/s1.json", file_size=1024,
                tags=["python"],
                messages=[
                    Message(role="user", content="How to use list comprehension in Python?"),
                    Message(role="assistant", content="List comprehension is a concise way to create lists."),
                ]
            ),
            Session(
                id="s2", source="codex", title="JavaScript Debugging",
                created_at=time.time() - 86400 * 2,
                updated_at=time.time() - 86400 * 2,
                file_path="/tmp/s2.json", file_size=2048,
                tags=["javascript"],
                messages=[
                    Message(role="user", content="How to debug async functions?"),
                    Message(role="assistant", content="Use console.log and breakpoints."),
                ]
            ),
            Session(
                id="s3", source="claude", title="Python Data Analysis",
                created_at=time.time(),
                updated_at=time.time(),
                file_path="/tmp/s3.json", file_size=4096,
                tags=["python", "data"],
                messages=[
                    Message(role="user", content="How to use pandas for data analysis?"),
                    Message(role="assistant", content="Pandas provides DataFrame for data manipulation."),
                ]
            ),
        ]
        self.indexer.add_sessions(sessions)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_keyword_search(self):
        """测试关键词搜索"""
        options = SearchOptions(keyword="python")
        results = self.searcher.search(options)
        self.assertEqual(len(results), 2)

    def test_keyword_search_title(self):
        """测试标题搜索"""
        options = SearchOptions(keyword="JavaScript")
        results = self.searcher.search(options)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].session_id, "s2")

    def test_source_filter(self):
        """测试来源过滤"""
        options = SearchOptions(source="codex")
        results = self.searcher.search(options)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source, "codex")

    def test_tag_filter(self):
        """测试标签过滤"""
        options = SearchOptions(tags=["data"])
        results = self.searcher.search(options)
        self.assertEqual(len(results), 1)

    def test_time_range_filter(self):
        """测试时间范围过滤"""
        options = SearchOptions(
            start_time=time.time() - 86400 * 3,
            end_time=time.time() + 3600,
        )
        results = self.searcher.search(options)
        # s1是5天前（被过滤），s2是2天前，s3是现在 -> 应该匹配2个
        self.assertEqual(len(results), 2)

    def test_regex_search(self):
        """测试正则搜索"""
        options = SearchOptions(regex=r"data\s+analysis")
        results = self.searcher.search(options)
        self.assertGreater(len(results), 0)

    def test_max_results(self):
        """测试最大结果数"""
        options = SearchOptions(max_results=1)
        results = self.searcher.search(options)
        self.assertLessEqual(len(results), 1)

    def test_sort_by_time(self):
        """测试按时间排序"""
        options = SearchOptions(sort_by="time", sort_order="asc")
        results = self.searcher.search(options)
        self.assertEqual(len(results), 3)
        # 最早的最先
        self.assertEqual(results[0].session_id, "s1")

    def test_sort_by_size(self):
        """测试按大小排序"""
        options = SearchOptions(sort_by="size", sort_order="desc")
        results = self.searcher.search(options)
        self.assertEqual(results[0].session_id, "s3")

    def test_quick_search(self):
        """测试快速搜索"""
        results = self.searcher.quick_search("Python")
        self.assertGreater(len(results), 0)

    def test_search_by_source(self):
        """测试按来源搜索"""
        results = self.searcher.search_by_source("claude")
        self.assertEqual(len(results), 2)

    def test_combined_filters(self):
        """测试组合过滤"""
        options = SearchOptions(
            keyword="python",
            source="claude",
        )
        results = self.searcher.search(options)
        self.assertEqual(len(results), 2)

    def test_no_results(self):
        """测试无结果"""
        options = SearchOptions(keyword="nonexistent_keyword_xyz")
        results = self.searcher.search(options)
        self.assertEqual(len(results), 0)

    def test_search_result_properties(self):
        """测试搜索结果属性"""
        options = SearchOptions(keyword="python")
        results = self.searcher.search(options)
        for r in results:
            self.assertIsInstance(r.score, float)
            self.assertGreater(r.score, 0)
            self.assertIsInstance(r.title, str)
            self.assertIsInstance(r.preview, str)


class TestAnalyzer(unittest.TestCase):
    """分析引擎测试"""

    def setUp(self):
        self.analyzer = SessionAnalyzer()
        self.now = time.time()

    def _make_session(self, sid, source, title, msg_count=5, days_ago=0):
        """创建测试会话"""
        ts = self.now - days_ago * 86400
        messages = []
        for i in range(msg_count):
            messages.append(Message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i} about {title} programming"
            ))
        return Session(
            id=sid,
            source=source,
            title=title,
            created_at=ts,
            updated_at=ts,
            file_path=f"/tmp/{sid}.json",
            file_size=1024 * (msg_count + 1),
            messages=messages,
        )

    def test_analyze_empty(self):
        """测试分析空列表"""
        result = self.analyzer.analyze([])
        self.assertEqual(result.total_sessions, 0)
        self.assertEqual(result.total_messages, 0)

    def test_analyze_basic(self):
        """测试基础分析"""
        sessions = [
            self._make_session("s1", "claude", "Python Help", 10),
            self._make_session("s2", "codex", "JS Debug", 5),
        ]
        result = self.analyzer.analyze(sessions)
        self.assertEqual(result.total_sessions, 2)
        self.assertEqual(result.total_messages, 15)
        self.assertGreater(result.total_tokens_estimate, 0)
        self.assertGreater(result.total_size_bytes, 0)

    def test_analyze_source_distribution(self):
        """测试来源分布"""
        sessions = [
            self._make_session("s1", "claude", "A"),
            self._make_session("s2", "claude", "B"),
            self._make_session("s3", "codex", "C"),
        ]
        result = self.analyzer.analyze(sessions)
        self.assertEqual(result.source_distribution["claude"], 2)
        self.assertEqual(result.source_distribution["codex"], 1)

    def test_analyze_time_distribution(self):
        """测试时间分布"""
        sessions = [
            self._make_session("s1", "claude", "A", days_ago=1),
            self._make_session("s2", "claude", "B", days_ago=1),
            self._make_session("s3", "claude", "C", days_ago=5),
        ]
        result = self.analyzer.analyze(sessions)
        self.assertGreater(len(result.daily_distribution), 0)

    def test_analyze_hourly_distribution(self):
        """测试小时分布"""
        sessions = [self._make_session("s1", "claude", "A")]
        result = self.analyzer.analyze(sessions)
        self.assertIn("hourly_distribution", result.to_dict())

    def test_analyze_average(self):
        """测试平均值计算"""
        sessions = [
            self._make_session("s1", "claude", "A", 10),
            self._make_session("s2", "claude", "B", 20),
        ]
        result = self.analyzer.analyze(sessions)
        self.assertEqual(result.average_messages_per_session, 15.0)

    def test_analyze_by_source(self):
        """测试按来源分析"""
        sessions = [
            self._make_session("s1", "claude", "A", 10),
            self._make_session("s2", "codex", "B", 5),
        ]
        by_source = self.analyzer.analyze_by_source(sessions)
        self.assertIn("claude", by_source)
        self.assertIn("codex", by_source)
        self.assertEqual(by_source["claude"]["session_count"], 1)

    def test_analyze_time_trends(self):
        """测试时间趋势分析"""
        sessions = [
            self._make_session("s1", "claude", "A", days_ago=0),
            self._make_session("s2", "claude", "B", days_ago=1),
            self._make_session("s3", "claude", "C", days_ago=1),
        ]
        trends = self.analyzer.analyze_time_trends(sessions)
        self.assertGreater(trends["total_days"], 0)
        self.assertGreater(trends["avg_per_day"], 0)

    def test_analyze_topics(self):
        """测试主题分析"""
        sessions = [
            Session(
                id="s1", source="claude", title="Python Programming",
                messages=[
                    Message(role="user", content="How to use python decorators and classes?"),
                    Message(role="assistant", content="Python decorators are functions that modify other functions."),
                ]
            ),
        ]
        topics = self.analyzer.analyze_topics(sessions)
        self.assertIsInstance(topics, list)
        self.assertGreater(len(topics), 0)
        # 每个主题应该有keyword, frequency, related_sessions, percentage
        for topic in topics:
            self.assertIn("keyword", topic)
            self.assertIn("frequency", topic)
            self.assertIn("related_sessions", topic)
            self.assertIn("percentage", topic)

    def test_analyze_usage_patterns(self):
        """测试使用模式分析"""
        sessions = [
            self._make_session("s1", "claude", "A", 3),
            self._make_session("s2", "claude", "B", 25),
            self._make_session("s3", "claude", "C", 60),
        ]
        patterns = self.analyzer.analyze_usage_patterns(sessions)
        self.assertIn("session_length_distribution", patterns)
        self.assertIn("token_usage_distribution", patterns)
        self.assertIn("file_size_distribution", patterns)

    def test_generate_summary(self):
        """测试生成摘要"""
        sessions = [
            self._make_session("s1", "claude", "Python Help", 10),
            self._make_session("s2", "codex", "JS Debug", 5),
        ]
        summary = self.analyzer.generate_summary(sessions)
        self.assertIn("SessionPilot", summary)
        self.assertIn("2", summary)  # 总会话数
        self.assertIn("15", summary)  # 总消息数

    def test_generate_summary_empty(self):
        """测试空列表摘要"""
        summary = self.analyzer.generate_summary([])
        self.assertIn("没有", summary)


class TestExporter(unittest.TestCase):
    """导出器测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.exporter = SessionExporter(output_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _make_sessions(self):
        """创建测试会话"""
        return [
            Session(
                id="s1", source="claude", title="Test Session 1",
                created_at=1700000000.0, updated_at=1700001000.0,
                file_path="/tmp/s1.json", file_size=1024,
                tags=["test"],
                messages=[
                    Message(role="user", content="Hello"),
                    Message(role="assistant", content="Hi there!"),
                ]
            ),
            Session(
                id="s2", source="codex", title="Test Session 2",
                created_at=1700002000.0, updated_at=1700003000.0,
                file_path="/tmp/s2.json", file_size=2048,
                messages=[
                    Message(role="user", content="Question"),
                ]
            ),
        ]

    def test_export_markdown(self):
        """测试Markdown导出"""
        sessions = self._make_sessions()
        path = self.exporter.export_sessions(sessions, format="markdown")
        self.assertTrue(os.path.exists(path))
        content = open(path, "r", encoding="utf-8").read()
        self.assertIn("SessionPilot", content)
        self.assertIn("Test Session 1", content)
        self.assertIn("Hello", content)

    def test_export_json(self):
        """测试JSON导出"""
        sessions = self._make_sessions()
        path = self.exporter.export_sessions(sessions, format="json")
        self.assertTrue(os.path.exists(path))
        data = json.load(open(path, "r", encoding="utf-8"))
        self.assertEqual(data["total_sessions"], 2)
        self.assertEqual(len(data["sessions"]), 2)

    def test_export_csv(self):
        """测试CSV导出"""
        sessions = self._make_sessions()
        path = self.exporter.export_sessions(sessions, format="csv")
        self.assertTrue(os.path.exists(path))
        content = open(path, "r", encoding="utf-8").read()
        self.assertIn("ID", content)
        self.assertIn("s1", content)

    def test_export_without_messages(self):
        """测试不含消息的导出"""
        sessions = self._make_sessions()
        path = self.exporter.export_sessions(
            sessions, format="json", include_messages=False
        )
        data = json.load(open(path, "r", encoding="utf-8"))
        self.assertNotIn("messages", data["sessions"][0])

    def test_export_custom_path(self):
        """测试自定义输出路径"""
        sessions = self._make_sessions()
        custom_path = os.path.join(self.test_dir, "custom_export.md")
        path = self.exporter.export_sessions(
            sessions, format="markdown", output_path=custom_path
        )
        self.assertEqual(path, custom_path)

    def test_export_empty_raises(self):
        """测试导出空列表"""
        with self.assertRaises(ValueError):
            self.exporter.export_sessions([], format="markdown")

    def test_export_invalid_format(self):
        """测试无效格式"""
        sessions = self._make_sessions()
        with self.assertRaises(ValueError):
            self.exporter.export_sessions(sessions, format="xml")

    def test_export_analysis_markdown(self):
        """测试分析结果Markdown导出"""
        analysis = AnalysisResult(
            total_sessions=5,
            total_messages=50,
            total_tokens_estimate=10000,
            total_size_bytes=1024 * 1024,
            source_distribution={"claude": 3, "codex": 2},
            top_keywords=[("python", 10), ("code", 8)],
        )
        path = self.exporter.export_analysis(analysis, format="markdown")
        self.assertTrue(os.path.exists(path))
        content = open(path, "r", encoding="utf-8").read()
        self.assertIn("SessionPilot", content)
        self.assertIn("5", content)

    def test_export_analysis_json(self):
        """测试分析结果JSON导出"""
        analysis = AnalysisResult(total_sessions=1)
        path = self.exporter.export_analysis(analysis, format="json")
        self.assertTrue(os.path.exists(path))
        data = json.load(open(path, "r", encoding="utf-8"))
        self.assertEqual(data["total_sessions"], 1)


class TestCleaner(unittest.TestCase):
    """清理器测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.indexer = SessionIndexer(index_dir=self.test_dir)
        self.cleaner = SessionCleaner(self.indexer)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _make_session_file(self, sid, size=1024, days_ago=30):
        """创建测试会话文件"""
        path = os.path.join(self.test_dir, f"{sid}.json")
        with open(path, "w") as f:
            f.write("x" * size)
        ts = time.time() - days_ago * 86400
        session = Session(
            id=sid, source="claude", title=f"Session {sid}",
            created_at=ts, updated_at=ts,
            file_path=path, file_size=size,
            messages=[Message(role="user", content="test")]
        )
        return session

    def test_clean_by_age_dry_run(self):
        """测试按时间清理（试运行）"""
        sessions = [
            self._make_session_file("old1", days_ago=60),
            self._make_session_file("old2", days_ago=45),
            self._make_session_file("new1", days_ago=5),
        ]
        policy = CleanPolicy(max_age_days=30, dry_run=True)
        result = self.cleaner.clean(sessions, policy)
        self.assertEqual(result.deleted_count, 2)
        self.assertGreater(result.freed_bytes, 0)
        # 文件应该还在
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "new1.json")))

    def test_clean_by_age_actual(self):
        """测试按时间实际清理"""
        sessions = [
            self._make_session_file("old1", days_ago=60),
            self._make_session_file("new1", days_ago=5),
        ]
        policy = CleanPolicy(max_age_days=30, dry_run=False)
        result = self.cleaner.clean(sessions, policy)
        self.assertEqual(result.deleted_count, 1)
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "old1.json")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "new1.json")))

    def test_clean_by_max_count(self):
        """测试按最大数量清理"""
        sessions = [
            self._make_session_file(f"s{i}", days_ago=i * 10)
            for i in range(5)
        ]
        policy = CleanPolicy(max_file_count=3, dry_run=True)
        result = self.cleaner.clean(sessions, policy)
        self.assertEqual(result.deleted_count, 2)

    def test_clean_by_min_size(self):
        """测试按最小文件大小清理"""
        sessions = [
            self._make_session_file("small1", size=100),
            self._make_session_file("small2", size=200),
            self._make_session_file("big1", size=5000),
        ]
        policy = CleanPolicy(min_file_size_kb=0.5, dry_run=True)
        result = self.cleaner.clean(sessions, policy)
        self.assertEqual(result.deleted_count, 2)

    def test_clean_by_source(self):
        """测试按来源清理"""
        s1 = self._make_session_file("claude1")
        s1.source = "claude"
        s2 = self._make_session_file("codex1")
        s2.source = "codex"
        policy = CleanPolicy(max_age_days=0, source="claude", dry_run=True)
        result = self.cleaner.clean([s1, s2], policy)
        self.assertEqual(result.deleted_count, 1)

    def test_preview_clean(self):
        """测试预览清理"""
        sessions = [
            self._make_session_file("s1", days_ago=60),
            self._make_session_file("s2", days_ago=5),
        ]
        policy = CleanPolicy(max_age_days=30, dry_run=True)
        preview = self.cleaner.preview_clean(sessions, policy)
        self.assertEqual(preview["would_delete"], 1)
        self.assertGreater(preview["would_free_bytes"], 0)

    def test_disk_usage(self):
        """测试磁盘使用统计"""
        sessions = [
            self._make_session_file("s1", size=1024),
            self._make_session_file("s2", size=2048),
        ]
        usage = self.cleaner.get_disk_usage(sessions)
        self.assertEqual(usage["total_files"], 2)
        self.assertEqual(usage["total_size"], 3072)

    def test_clean_empty(self):
        """测试清理空列表"""
        policy = CleanPolicy(dry_run=True)
        result = self.cleaner.clean([], policy)
        self.assertEqual(result.deleted_count, 0)


class TestReporter(unittest.TestCase):
    """报告生成器测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.reporter = ReportGenerator()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _make_sessions(self):
        """创建测试会话"""
        now = time.time()
        return [
            Session(
                id="s1", source="claude", title="Python Help",
                created_at=now - 86400 * 5, updated_at=now - 86400 * 5,
                file_path="/tmp/s1.json", file_size=2048,
                messages=[
                    Message(role="user", content="Help with python"),
                    Message(role="assistant", content="Here is the solution"),
                ]
            ),
            Session(
                id="s2", source="codex", title="JS Question",
                created_at=now, updated_at=now,
                file_path="/tmp/s2.json", file_size=1024,
                messages=[Message(role="user", content="JS question")]
            ),
        ]

    def test_generate_html_report(self):
        """测试生成HTML报告"""
        sessions = self._make_sessions()
        path = self.reporter.generate_report(
            sessions, format="html",
            output_path=os.path.join(self.test_dir, "report.html")
        )
        self.assertTrue(os.path.exists(path))
        content = open(path, "r", encoding="utf-8").read()
        self.assertIn("<html", content)
        self.assertIn("SessionPilot", content)
        # 验证报告包含统计数据
        self.assertIn("2", content)  # 总会话数

    def test_generate_markdown_report(self):
        """测试生成Markdown报告"""
        sessions = self._make_sessions()
        path = self.reporter.generate_report(
            sessions, format="markdown",
            output_path=os.path.join(self.test_dir, "report.md")
        )
        self.assertTrue(os.path.exists(path))
        content = open(path, "r", encoding="utf-8").read()
        self.assertIn("SessionPilot", content)
        self.assertIn("##", content)

    def test_generate_json_report(self):
        """测试生成JSON报告"""
        sessions = self._make_sessions()
        path = self.reporter.generate_report(
            sessions, format="json",
            output_path=os.path.join(self.test_dir, "report.json")
        )
        self.assertTrue(os.path.exists(path))
        data = json.load(open(path, "r", encoding="utf-8"))
        self.assertIn("analysis", data)
        self.assertIn("time_trends", data)
        self.assertIn("topics", data)

    def test_generate_report_empty_raises(self):
        """测试空列表报告"""
        with self.assertRaises(ValueError):
            self.reporter.generate_report([], format="html")

    def test_generate_report_auto_path(self):
        """测试自动生成路径"""
        sessions = self._make_sessions()
        path = self.reporter.generate_report(sessions, format="html")
        self.assertTrue(os.path.exists(path))
        self.assertIn("report", path)


class TestBrowser(unittest.TestCase):
    """TUI浏览器测试"""

    def test_format_token_short(self):
        """测试Token格式化"""
        self.assertEqual(format_token_short(100), "100")
        self.assertEqual(format_token_short(1500), "1.5K")
        self.assertEqual(format_token_short(2000000), "2.0M")

    def test_browser_creation(self):
        """测试浏览器创建"""
        sessions = [
            Session(
                id="s1", source="claude", title="Test",
                created_at=time.time(), updated_at=time.time(),
                file_path="/tmp/s1.json", file_size=1024,
                messages=[Message(role="user", content="Hello")]
            ),
        ]
        browser = SessionBrowser(sessions)
        self.assertEqual(len(browser.sessions), 1)
        self.assertEqual(browser.selected_index, 0)

    def test_browser_empty(self):
        """测试空会话列表"""
        browser = SessionBrowser([])
        # browse() should print message and return None
        # (can't test interactively, but test construction)

    def test_browser_move_cursor(self):
        """测试光标移动"""
        sessions = [
            Session(id=f"s{i}", source="claude", title=f"Session {i}",
                    file_path=f"/tmp/s{i}.json", file_size=1024,
                    messages=[Message(role="user", content="test")])
            for i in range(5)
        ]
        browser = SessionBrowser(sessions)
        browser._move_cursor(1)
        self.assertEqual(browser.selected_index, 1)
        browser._move_cursor(-1)
        self.assertEqual(browser.selected_index, 0)
        # 边界测试
        browser._move_cursor(-100)
        self.assertEqual(browser.selected_index, 0)
        browser.selected_index = 4
        browser._move_cursor(100)
        self.assertEqual(browser.selected_index, 4)


class TestCLI(unittest.TestCase):
    """CLI测试"""

    def test_create_parser(self):
        """测试创建解析器"""
        parser = create_parser()
        self.assertIsNotNone(parser)

    def test_parse_scan_command(self):
        """测试解析scan命令"""
        parser = create_parser()
        args = parser.parse_args(["scan", "--source", "claude"])
        self.assertEqual(args.command, "scan")
        self.assertEqual(args.source, "claude")

    def test_parse_search_command(self):
        """测试解析search命令"""
        parser = create_parser()
        args = parser.parse_args(["search", "python", "--max", "10"])
        self.assertEqual(args.command, "search")
        self.assertEqual(args.keyword, "python")
        self.assertEqual(args.max, 10)

    def test_parse_analyze_command(self):
        """测试解析analyze命令"""
        parser = create_parser()
        args = parser.parse_args(["analyze", "--topics", "--trends"])
        self.assertEqual(args.command, "analyze")
        self.assertTrue(args.topics)
        self.assertTrue(args.trends)

    def test_parse_export_command(self):
        """测试解析export命令"""
        parser = create_parser()
        args = parser.parse_args(["export", "--format", "json", "-o", "out.json"])
        self.assertEqual(args.command, "export")
        self.assertEqual(args.format, "json")
        self.assertEqual(args.output, "out.json")

    def test_parse_report_command(self):
        """测试解析report命令"""
        parser = create_parser()
        args = parser.parse_args(["report", "--format", "html"])
        self.assertEqual(args.command, "report")
        self.assertEqual(args.format, "html")

    def test_parse_clean_command(self):
        """测试解析clean命令"""
        parser = create_parser()
        args = parser.parse_args(["clean", "--dry-run", "--max-age", "30"])
        self.assertEqual(args.command, "clean")
        self.assertTrue(args.dry_run)
        self.assertEqual(args.max_age, 30)

    def test_parse_index_command(self):
        """测试解析index命令"""
        parser = create_parser()
        args = parser.parse_args(["index", "build"])
        self.assertEqual(args.command, "index")
        self.assertEqual(args.action, "build")

    def test_parse_info_command(self):
        """测试解析info命令"""
        parser = create_parser()
        args = parser.parse_args(["info"])
        self.assertEqual(args.command, "info")

    def test_parse_no_command(self):
        """测试无命令"""
        parser = create_parser()
        args = parser.parse_args([])
        self.assertIsNone(args.command)

    def test_main_no_args(self):
        """测试无参数运行"""
        ret = main([])
        self.assertEqual(ret, 0)

    def test_main_info_command(self):
        """测试info命令"""
        ret = main(["info"])
        self.assertEqual(ret, 0)

    def test_main_index_build(self):
        """测试index build命令"""
        ret = main(["index", "build"])
        self.assertEqual(ret, 0)

    def test_main_scan_quiet(self):
        """测试scan --quiet命令"""
        ret = main(["scan", "--quiet", "--no-index"])
        self.assertEqual(ret, 0)

    def test_main_version(self):
        """测试版本号"""
        try:
            ret = main(["--version"])
        except SystemExit as e:
            ret = e.code
        self.assertEqual(ret, 0)


class TestIntegration(unittest.TestCase):
    """集成测试 - 测试完整工作流"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_full_workflow(self):
        """测试完整工作流：扫描 -> 索引 -> 搜索 -> 分析 -> 导出"""
        # 1. 创建测试数据
        claude_dir = os.path.join(self.test_dir, ".claude")
        os.makedirs(claude_dir, exist_ok=True)

        for i in range(5):
            data = {
                "title": f"Python Session {i}",
                "messages": [
                    {"role": "user", "content": f"How to use python feature {i}?"},
                    {"role": "assistant", "content": f"Here is how to use feature {i}."},
                ],
                "created_at": time.time() - i * 86400,
                "tags": ["python"],
            }
            path = os.path.join(claude_dir, f"session_{i}.json")
            with open(path, "w") as f:
                json.dump(data, f)

        # 2. 扫描
        scanner = SessionScanner()
        sessions = scanner.scan_directory(claude_dir, "claude")
        self.assertEqual(len(sessions), 5)

        # 3. 索引
        index_dir = os.path.join(self.test_dir, "index")
        indexer = SessionIndexer(index_dir=index_dir)
        indexer.add_sessions(sessions)
        indexer.save_index()
        self.assertEqual(indexer.total_entries, 5)

        # 4. 搜索
        searcher = SessionSearcher(indexer)
        results = searcher.quick_search("python")
        self.assertEqual(len(results), 5)

        # 搜索标题中的内容
        results = searcher.quick_search("Session 3")
        self.assertGreater(len(results), 0)

        # 5. 分析
        analyzer = SessionAnalyzer()
        analysis = analyzer.analyze(sessions)
        self.assertEqual(analysis.total_sessions, 5)
        self.assertEqual(analysis.total_messages, 10)

        # 6. 导出
        exporter = SessionExporter(output_dir=self.test_dir)
        export_path = exporter.export_sessions(sessions, format="json")
        self.assertTrue(os.path.exists(export_path))

        # 7. 报告
        reporter = ReportGenerator()
        report_path = reporter.generate_report(
            sessions, format="markdown",
            output_path=os.path.join(self.test_dir, "report.md")
        )
        self.assertTrue(os.path.exists(report_path))

    def test_clean_workflow(self):
        """测试清理工作流"""
        # 创建文件
        files = []
        for i in range(10):
            path = os.path.join(self.test_dir, f"session_{i}.json")
            with open(path, "w") as f:
                f.write("x" * 1024)
            ts = time.time() - (i + 1) * 86400
            session = Session(
                id=f"s{i}", source="claude", title=f"Session {i}",
                created_at=ts, updated_at=ts,
                file_path=path, file_size=1024,
                messages=[Message(role="user", content="test")]
            )
            files.append(session)

        # 清理超过5天的
        index_dir = os.path.join(self.test_dir, "index")
        indexer = SessionIndexer(index_dir=index_dir)
        cleaner = SessionCleaner(indexer)

        policy = CleanPolicy(max_age_days=5, dry_run=True)
        preview = cleaner.preview_clean(files, policy)
        self.assertGreater(preview["would_delete"], 0)

        # 实际清理
        policy = CleanPolicy(max_age_days=5, dry_run=False)
        result = cleaner.clean(files, policy)
        self.assertGreater(result.deleted_count, 0)
        self.assertGreater(result.freed_bytes, 0)

    def test_multi_source_workflow(self):
        """测试多来源工作流"""
        # 创建多个来源的数据
        for source in ["claude", "codex", "cursor"]:
            source_dir = os.path.join(self.test_dir, f".{source}")
            os.makedirs(source_dir, exist_ok=True)
            for i in range(3):
                data = {
                    "title": f"{source} session {i}",
                    "messages": [{"role": "user", "content": f"test {source} {i}"}],
                }
                path = os.path.join(source_dir, f"session_{i}.json")
                with open(path, "w") as f:
                    json.dump(data, f)

        scanner = SessionScanner()
        all_sessions = []
        for source in ["claude", "codex", "cursor"]:
            source_dir = os.path.join(self.test_dir, f".{source}")
            sessions = scanner.scan_directory(source_dir, source)
            all_sessions.extend(sessions)

        self.assertEqual(len(all_sessions), 9)

        analyzer = SessionAnalyzer()
        analysis = analyzer.analyze(all_sessions)
        self.assertEqual(analysis.total_sessions, 9)
        self.assertEqual(len(analysis.source_distribution), 3)


if __name__ == "__main__":
    unittest.main()
