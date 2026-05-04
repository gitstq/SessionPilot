"""
SessionPilot - 工具函数
提供跨平台路径处理、时间格式化、Token估算等通用工具
"""

import os
import sys
import re
import json
import time
import hashlib
import platform
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple


# ==================== 路径工具 ====================

def get_home_dir() -> str:
    """获取用户主目录（跨平台）"""
    return os.path.expanduser("~")


def get_config_dir() -> str:
    """获取SessionPilot配置目录"""
    config_base = os.environ.get("XDG_CONFIG_HOME", "")
    if config_base and os.path.isdir(config_base):
        return os.path.join(config_base, "sessionpilot")
    if platform.system() == "Windows":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            return os.path.join(appdata, "SessionPilot")
    return os.path.join(get_home_dir(), ".sessionpilot")


def get_cache_dir() -> str:
    """获取SessionPilot缓存目录"""
    cache_base = os.environ.get("XDG_CACHE_HOME", "")
    if cache_base and os.path.isdir(cache_base):
        return os.path.join(cache_base, "sessionpilot")
    if platform.system() == "Windows":
        localappdata = os.environ.get("LOCALAPPDATA", "")
        if localappdata:
            return os.path.join(localappdata, "SessionPilot", "Cache")
    return os.path.join(get_home_dir(), ".cache", "sessionpilot")


def ensure_dir(path: str) -> bool:
    """确保目录存在，不存在则创建"""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except OSError:
        return False


def safe_read_file(path: str, encoding: str = "utf-8") -> Optional[str]:
    """安全读取文件内容"""
    try:
        with open(path, "r", encoding=encoding, errors="replace") as f:
            return f.read()
    except (OSError, IOError):
        return None


def safe_read_json(path: str, encoding: str = "utf-8") -> Optional[Any]:
    """安全读取JSON文件"""
    content = safe_read_file(path, encoding)
    if content is None:
        return None
    try:
        return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return None


def safe_write_file(path: str, content: str, encoding: str = "utf-8") -> bool:
    """安全写入文件"""
    try:
        ensure_dir(os.path.dirname(path))
        with open(path, "w", encoding=encoding) as f:
            f.write(content)
        return True
    except (OSError, IOError):
        return False


def safe_write_json(path: str, data: Any, indent: int = 2, encoding: str = "utf-8") -> bool:
    """安全写入JSON文件"""
    try:
        content = json.dumps(data, ensure_ascii=False, indent=indent)
        return safe_write_file(path, content, encoding)
    except (TypeError, ValueError):
        return False


def get_file_size(path: str) -> int:
    """获取文件大小（字节）"""
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def get_file_mtime(path: str) -> Optional[float]:
    """获取文件修改时间"""
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def get_file_ctime(path: str) -> Optional[float]:
    """获取文件创建时间"""
    try:
        return os.path.getctime(path)
    except OSError:
        return None


# ==================== 时间工具 ====================

def format_timestamp(ts: Optional[float], fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化时间戳"""
    if ts is None:
        return "未知"
    try:
        return time.strftime(fmt, time.localtime(ts))
    except (ValueError, OSError):
        return "未知"


def parse_time_str(time_str: str) -> Optional[float]:
    """解析时间字符串，支持多种格式
    支持格式：
    - YYYY-MM-DD
    - YYYY-MM-DD HH:MM:SS
    - N days ago / N hours ago / N minutes ago
    - timestamp (纯数字)
    """
    if not time_str:
        return None

    time_str = time_str.strip().lower()

    # 纯数字时间戳
    if time_str.isdigit():
        try:
            ts = int(time_str)
            if ts > 1e12:  # 毫秒级时间戳
                ts = ts / 1000
            return float(ts)
        except ValueError:
            return None

    # 相对时间
    relative_patterns = [
        (r"(\d+)\s*(day|days|天)\s*ago", 86400),
        (r"(\d+)\s*(hour|hours|小时)\s*ago", 3600),
        (r"(\d+)\s*(minute|minutes|分钟)\s*ago", 60),
        (r"(\d+)\s*(week|weeks|周)\s*ago", 604800),
        (r"(\d+)\s*(month|months|月)\s*ago", 2592000),
    ]
    for pattern, seconds in relative_patterns:
        match = re.match(pattern, time_str)
        if match:
            try:
                n = int(match.group(1))
                return time.time() - n * seconds
            except ValueError:
                return None

    # 绝对时间
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(time_str, fmt)
            return dt.timestamp()
        except ValueError:
            continue

    return None


def time_range_filter(
    ts: Optional[float],
    start_time: Optional[float] = None,
    end_time: Optional[float] = None
) -> bool:
    """检查时间戳是否在指定范围内"""
    if ts is None:
        return False
    if start_time is not None and ts < start_time:
        return False
    if end_time is not None and ts > end_time:
        return False
    return True


def get_date_key(ts: Optional[float]) -> str:
    """从时间戳获取日期键（YYYY-MM-DD）"""
    if ts is None:
        return "unknown"
    try:
        return time.strftime("%Y-%m-%d", time.localtime(ts))
    except (ValueError, OSError):
        return "unknown"


def get_hour_key(ts: Optional[float]) -> int:
    """从时间戳获取小时键（0-23）"""
    if ts is None:
        return -1
    try:
        return time.localtime(ts).tm_hour
    except (ValueError, OSError):
        return -1


# ==================== 文本工具 ====================

def estimate_tokens(text: str) -> int:
    """估算文本的Token数量（约4字符=1token）"""
    if not text:
        return 0
    return max(1, len(text) // 4)


def extract_keywords(text: str, top_n: int = 20) -> List[Tuple[str, int]]:
    """从文本中提取关键词（基于词频统计）
    支持中英文混合文本
    """
    if not text:
        return []

    # 英文单词
    english_words = re.findall(r"[a-zA-Z]{3,}", text.lower())

    # 中文单字/双字（简单分词）
    chinese_chars = re.findall(r"[\u4e00-\u9fff]+", text)
    chinese_words = []
    for segment in chinese_chars:
        if len(segment) >= 2:
            # 双字组合
            for i in range(len(segment) - 1):
                chinese_words.append(segment[i:i+2])
        chinese_words.append(segment)

    # 合并所有词
    all_words = english_words + chinese_words

    # 过滤停用词
    stop_words = {
        "the", "and", "for", "are", "but", "not", "you", "all", "can",
        "had", "her", "was", "one", "our", "out", "has", "have", "been",
        "from", "this", "that", "with", "they", "will", "what", "when",
        "make", "like", "just", "over", "such", "take", "than", "them",
        "very", "some", "could", "into", "also", "then", "would", "should",
        "about", "which", "their", "there", "these", "other", "being",
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
        "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你",
        "会", "着", "没有", "看", "好", "自己", "这", "他", "她", "它",
    }
    filtered = [w for w in all_words if w not in stop_words and len(w) >= 2]

    # 统计词频
    freq = {}
    for word in filtered:
        freq[word] = freq.get(word, 0) + 1

    # 排序取前N
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return sorted_words[:top_n]


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """截断文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def generate_id(source: str, file_path: str) -> str:
    """生成会话唯一ID"""
    raw = f"{source}:{file_path}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def generate_file_hash(file_path: str) -> str:
    """生成文件内容的哈希值"""
    content = safe_read_file(file_path)
    if content is None:
        return ""
    return hashlib.md5(content.encode("utf-8")).hexdigest()[:12]


# ==================== 显示工具 ====================

def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 0:
        return "0 B"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_number(n: int) -> str:
    """格式化数字（添加千分位）"""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def print_table(headers: List[str], rows: List[List[str]], col_widths: Optional[List[int]] = None):
    """打印简单表格到终端"""
    if not rows:
        return

    # 计算列宽
    if col_widths is None:
        col_widths = []
        for i, header in enumerate(headers):
            max_w = len(header)
            for row in rows:
                if i < len(row):
                    max_w = max(max_w, len(str(row[i])))
            col_widths.append(min(max_w + 2, 60))

    # 打印表头
    header_line = ""
    for i, header in enumerate(headers):
        w = col_widths[i] if i < len(col_widths) else 20
        header_line += header.ljust(w)
    print(header_line)

    # 打印分隔线
    sep_line = ""
    for w in col_widths:
        sep_line += "-" * w
    print(sep_line)

    # 打印行
    for row in rows:
        line = ""
        for i, cell in enumerate(row):
            w = col_widths[i] if i < len(col_widths) else 20
            text = str(cell)[:w - 1]
            line += text.ljust(w)
        print(line)


def color_text(text: str, color: str = "") -> str:
    """为终端文本添加颜色（ANSI转义码）
    支持: red, green, yellow, blue, magenta, cyan, white, bold, dim
    """
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "reset": "\033[0m",
    }
    reset = colors.get("reset", "")
    c = colors.get(color, "")
    if not c:
        return text
    return f"{c}{text}{reset}"


def supports_color() -> bool:
    """检测终端是否支持颜色"""
    if platform.system() == "Windows":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            return kernel32.GetConsoleMode(kernel32.GetStdHandle(-11)) & 0x0004
        except Exception:
            return False
    if not sys.stdout.isatty():
        return False
    term = os.environ.get("TERM", "")
    return bool(term) and "dumb" not in term.lower()


# ==================== AI工具目录配置 ====================

# 各AI编码助手的默认数据目录
DEFAULT_SOURCE_DIRS = {
    "claude": [
        "~/.claude",
        "~/.claude/projects",
    ],
    "codex": [
        "~/.codex",
        "~/.codex/sessions",
    ],
    "cursor": [
        "~/.cursor",
        "~/.cursor/sessions",
        "~/.cursor/history",
    ],
    "windsurf": [
        "~/.windsurf",
        "~/.windsurf/sessions",
    ],
}

# 各来源支持的文件扩展名
SOURCE_EXTENSIONS = {
    "claude": [".json", ".jsonl"],
    "codex": [".json", ".jsonl"],
    "cursor": [".json", ".jsonl"],
    "windsurf": [".json", ".jsonl"],
}

# 各来源的会话文件匹配模式
SOURCE_PATTERNS = {
    "claude": [r".*\.jsonl?$"],
    "codex": [r".*session.*\.jsonl?$", r".*chat.*\.jsonl?$"],
    "cursor": [r".*session.*\.jsonl?$", r".*history.*\.jsonl?$"],
    "windsurf": [r".*session.*\.jsonl?$"],
}


def get_source_dirs(source: str) -> List[str]:
    """获取指定来源的数据目录列表"""
    dirs = DEFAULT_SOURCE_DIRS.get(source, [])
    return [os.path.expanduser(d) for d in dirs]


def get_all_source_dirs() -> Dict[str, List[str]]:
    """获取所有来源的数据目录"""
    result = {}
    for source in DEFAULT_SOURCE_DIRS:
        result[source] = get_source_dirs(source)
    return result
