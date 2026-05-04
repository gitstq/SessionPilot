"""
SessionPilot - TUI浏览器
交互式终端会话列表浏览，支持键盘导航
"""

import os
import sys
import time
import termios
import tty
import signal
from typing import List, Optional, Callable

from .models import Session
from .utils import (
    format_timestamp, format_size, truncate_text, supports_color, color_text
)


# 键盘按键定义
KEY_UP = "\x1b[A"
KEY_DOWN = "\x1b[B"
KEY_PGUP = "\x1b[5~"
KEY_PGDN = "\x1b[6~"
KEY_HOME = "\x1b[H"
KEY_END = "\x1b[F"
KEY_ENTER = "\r"
KEY_q = "q"
KEY_Q = "Q"
KEY_SLASH = "/"
KEY_n = "n"
KEY_d = "d"
KEY_e = "E"
KEY_j = "j"
KEY_k = "k"
KEY_G = "G"
KEY_g = "g"
KEY_ESC = "\x1b"
KEY_CTRL_C = "\x03"
KEY_CTRL_L = "\x0c"


class TerminalHelper:
    """终端辅助类 - 处理原始输入模式"""

    def __init__(self):
        self._old_settings = None

    def enter_raw_mode(self):
        """进入原始输入模式"""
        try:
            fd = sys.stdin.fileno()
            self._old_settings = termios.tcgetattr(fd)
            tty.setraw(fd)
        except (OSError, termios.error):
            self._old_settings = None

    def exit_raw_mode(self):
        """退出原始输入模式"""
        if self._old_settings is not None:
            try:
                fd = sys.stdin.fileno()
                termios.tcsetattr(fd, termios.TCSADRAIN, self._old_settings)
            except (OSError, termios.error):
                pass
            self._old_settings = None

    def read_key(self) -> str:
        """读取单个按键"""
        try:
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                # 可能是转义序列
                ch2 = sys.stdin.read(1) if self._kbhit() else ""
                ch3 = sys.stdin.read(1) if self._kbhit() else ""
                return ch + ch2 + ch3
            return ch
        except (IOError, OSError):
            return ""

    def _kbhit(self) -> bool:
        """检查是否有更多输入"""
        try:
            import select
            dr, _, _ = select.select([sys.stdin], [], [], 0.01)
            return bool(dr)
        except (OSError, ImportError):
            return False

    def get_terminal_size(self) -> tuple:
        """获取终端大小"""
        try:
            cols, rows = os.get_terminal_size()
            return rows, cols
        except OSError:
            return 24, 80


class SessionBrowser:
    """会话浏览器 - TUI风格的交互式浏览"""

    def __init__(self, sessions: List[Session]):
        """
        初始化浏览器

        Args:
            sessions: 会话列表
        """
        self.sessions = sessions
        self.selected_index = 0
        self.scroll_offset = 0
        self.term = TerminalHelper()
        self._running = False
        self._search_mode = False
        self._search_query = ""
        self._filtered_sessions = list(sessions)
        self._use_color = supports_color()
        self._status_message = ""
        self._status_time = 0

        # 显示列配置
        self._col_source = 10
        self._col_title = 0  # 动态计算
        self._col_time = 16
        self._col_msgs = 6
        self._col_tokens = 10
        self._col_size = 10

    def browse(self) -> Optional[Session]:
        """
        启动交互式浏览

        Returns:
            用户选中的会话，或None
        """
        if not self.sessions:
            print("没有可浏览的会话。")
            return None

        # 检查是否支持TUI
        if not sys.stdin.isatty():
            print("交互式浏览需要终端环境。")
            return None

        self._running = True
        self.term.enter_raw_mode()

        # 设置信号处理
        original_sigint = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._handle_signal)

        try:
            self._draw()
            while self._running:
                key = self.term.read_key()
                self._handle_key(key)
        finally:
            self.term.exit_raw_mode()
            signal.signal(signal.SIGINT, original_sigint)
            # 清屏
            print("\033[2J\033[H", end="")
            print("浏览结束。")

        if 0 <= self.selected_index < len(self._filtered_sessions):
            return self._filtered_sessions[self.selected_index]
        return None

    def _handle_signal(self, signum, frame):
        """处理信号"""
        self._running = False

    def _handle_key(self, key: str):
        """处理按键输入"""
        if self._search_mode:
            self._handle_search_key(key)
            return

        if key in (KEY_q, KEY_Q, KEY_CTRL_C):
            self._running = False
        elif key in (KEY_UP, KEY_k):
            self._move_cursor(-1)
        elif key in (KEY_DOWN, KEY_j):
            self._move_cursor(1)
        elif key == KEY_PGUP:
            self._move_cursor(-10)
        elif key == KEY_PGDN:
            self._move_cursor(10)
        elif key == KEY_HOME or key == KEY_g:
            self.selected_index = 0
            self.scroll_offset = 0
            self._draw()
        elif key == KEY_END or key == KEY_G:
            self.selected_index = len(self._filtered_sessions) - 1
            self._adjust_scroll()
            self._draw()
        elif key == KEY_ENTER:
            self._show_detail()
        elif key == KEY_SLASH:
            self._enter_search()
        elif key == KEY_n:
            self._show_next_match()
        elif key == KEY_d:
            self._show_detail()
        elif key == KEY_e:
            self._export_current()
        elif key == KEY_CTRL_L:
            self._draw()

    def _handle_search_key(self, key: str):
        """处理搜索模式下的按键"""
        if key == KEY_ENTER:
            self._search_mode = False
            self._apply_search()
            self._draw()
        elif key == KEY_ESC:
            self._search_mode = False
            self._search_query = ""
            self._filtered_sessions = list(self.sessions)
            self._draw()
        elif key == "\x7f" or key == "\x08":  # Backspace
            self._search_query = self._search_query[:-1]
            self._draw_search_bar()
        elif len(key) == 1 and key.isprintable():
            self._search_query += key
            self._draw_search_bar()

    def _enter_search(self):
        """进入搜索模式"""
        self._search_mode = True
        self._search_query = ""
        self._draw_search_bar()

    def _apply_search(self):
        """应用搜索过滤"""
        if not self._search_query:
            self._filtered_sessions = list(self.sessions)
        else:
            query = self._search_query.lower()
            self._filtered_sessions = [
                s for s in self.sessions
                if query in s.title.lower()
                or query in s.source.lower()
                or any(query in m.content.lower() for m in s.messages)
            ]
        self.selected_index = 0
        self.scroll_offset = 0
        self._set_status(f"找到 {len(self._filtered_sessions)} 个匹配会话")

    def _move_cursor(self, delta: int):
        """移动光标"""
        new_index = self.selected_index + delta
        new_index = max(0, min(new_index, len(self._filtered_sessions) - 1))
        self.selected_index = new_index
        self._adjust_scroll()
        self._draw()

    def _adjust_scroll(self):
        """调整滚动偏移"""
        rows, _ = self.term.get_terminal_size()
        visible_rows = rows - 4  # 留出头部和状态栏

        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + visible_rows:
            self.scroll_offset = self.selected_index - visible_rows + 1

    def _draw(self):
        """绘制界面"""
        rows, cols = self.term.get_terminal_size()
        visible_rows = rows - 4

        # 清屏
        sys.stdout.write("\033[2J\033[H")

        # 标题栏
        title = f" SessionPilot Browser - {len(self._filtered_sessions)}/{len(self.sessions)} 会话 "
        if self._search_query:
            title += f"[搜索: {self._search_query}] "
        title = title.ljust(cols)
        if self._use_color:
            sys.stdout.write(f"\033[44;37m{title}\033[0m\r\n")
        else:
            sys.stdout.write(f"{title}\r\n")

        # 表头
        header = self._format_header(cols)
        if self._use_color:
            sys.stdout.write(f"\033[1m{header}\033[0m\r\n")
        else:
            sys.stdout.write(f"{header}\r\n")

        # 分隔线
        sys.stdout.write("-" * cols + "\r\n")

        # 会话列表
        start = self.scroll_offset
        end = min(start + visible_rows, len(self._filtered_sessions))

        for i in range(start, end):
            line = self._format_session_line(i, cols)
            if i == self.selected_index:
                if self._use_color:
                    sys.stdout.write(f"\033[7m{line}\033[0m\r\n")
                else:
                    sys.stdout.write(f"> {line}\r\n")
            else:
                sys.stdout.write(f"  {line}\r\n")

        # 填充空行
        for _ in range(end, start + visible_rows):
            sys.stdout.write("\r\n")

        # 状态栏
        status = self._format_status(cols)
        if self._use_color:
            sys.stdout.write(f"\033[47;30m{status}\033[0m\r\n")
        else:
            sys.stdout.write(f"{status}\r\n")

        sys.stdout.flush()

    def _draw_search_bar(self):
        """绘制搜索栏"""
        rows, cols = self.term.get_terminal_size()
        # 清屏并重绘
        sys.stdout.write("\033[2J\033[H")
        title = f" SessionPilot Browser - {len(self._filtered_sessions)}/{len(self.sessions)} 会话 "
        title = title.ljust(cols)
        if self._use_color:
            sys.stdout.write(f"\033[44;37m{title}\033[0m\r\n")
        else:
            sys.stdout.write(f"{title}\r\n")

        # 搜索输入行
        search_line = f" 搜索: {self._search_query}_".ljust(cols)
        if self._use_color:
            sys.stdout.write(f"\033[43;30m{search_line}\033[0m\r\n")
        else:
            sys.stdout.write(f"{search_line}\r\n")

        sys.stdout.write("-" * cols + "\r\n")

        # 显示当前过滤结果
        visible_rows = rows - 5
        start = 0
        end = min(visible_rows, len(self._filtered_sessions))
        for i in range(start, end):
            line = self._format_session_line(i, cols)
            sys.stdout.write(f"  {line}\r\n")

        sys.stdout.flush()

    def _format_header(self, cols: int) -> str:
        """格式化表头"""
        title_width = cols - self._col_source - self._col_time - self._col_msgs - self._col_tokens - self._col_size - 10
        title_width = max(title_width, 10)
        self._col_title = title_width

        header = (
            f"{'来源':^{self._col_source}}"
            f"{'标题':<{title_width}}"
            f"{'时间':^{self._col_time}}"
            f"{'消息':^{self._col_msgs}}"
            f"{'Token':^{self._col_tokens}}"
            f"{'大小':^{self._col_size}}"
        )
        return header[:cols]

    def _format_session_line(self, index: int, cols: int) -> str:
        """格式化会话行"""
        session = self._filtered_sessions[index]
        title_width = self._col_title

        source = session.source[:self._col_source].ljust(self._col_source)
        title = truncate_text(session.title or "(无标题)", title_width).ljust(title_width)
        time_str = format_timestamp(session.updated_at or session.created_at, "%m-%d %H:%M")
        time_str = time_str[:self._col_time].ljust(self._col_time)
        msgs = str(session.message_count).rjust(self._col_msgs - 1) + " "
        tokens = format_token_short(session.estimated_tokens).rjust(self._col_tokens - 1) + " "
        size = format_size(session.file_size)[:self._col_size].rjust(self._col_size)

        line = f"{source}{title}{time_str}{msgs}{tokens}{size}"
        return line[:cols]

    def _format_status(self, cols: int) -> str:
        """格式化状态栏"""
        if self._status_message and (time.time() - self._status_time) < 5:
            msg = self._status_message
        else:
            msg = ""

        parts = []
        if 0 <= self.selected_index < len(self._filtered_sessions):
            session = self._filtered_sessions[self.selected_index]
            parts.append(f"[{self.selected_index + 1}/{len(self._filtered_sessions)}]")
            parts.append(f"来源:{session.source}")
            parts.append(f"消息:{session.message_count}")

        if msg:
            parts.append(msg)

        help_text = "j/k:移动 Enter:详情 /:搜索 q:退出"
        status = " ".join(parts)
        status = status.ljust(cols - len(help_text) - 1) + help_text
        return status[:cols]

    def _show_detail(self):
        """显示会话详情"""
        if not (0 <= self.selected_index < len(self._filtered_sessions)):
            return

        session = self._filtered_sessions[self.selected_index]
        self.term.exit_raw_mode()

        print("\n" + "=" * 60)
        print(f"  会话详情 - {session.title or '(无标题)'}")
        print("=" * 60)
        print(f"  ID:        {session.id}")
        print(f"  来源:      {session.source}")
        print(f"  创建时间:  {session.created_time_str}")
        print(f"  更新时间:  {session.updated_time_str}")
        print(f"  消息数:    {session.message_count}")
        print(f"  估算Token: {session.estimated_tokens}")
        print(f"  文件大小:  {format_size(session.file_size)}")
        print(f"  文件路径:  {session.file_path}")
        if session.tags:
            print(f"  标签:      {', '.join(session.tags)}")
        if session.duration_minutes is not None:
            print(f"  持续时间:  {session.duration_minutes:.1f} 分钟")
        print("-" * 60)

        # 显示消息预览
        max_preview = 5
        for i, msg in enumerate(session.messages[:max_preview]):
            role_display = {"user": "用户", "assistant": "助手", "system": "系统"}.get(msg.role, msg.role)
            content = truncate_text(msg.content, 80)
            print(f"  [{role_display}] {content}")

        if session.message_count > max_preview:
            print(f"  ... 还有 {session.message_count - max_preview} 条消息")

        print("=" * 60)
        print("  按 Enter 返回列表...")

        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass

        self.term.enter_raw_mode()
        self._draw()

    def _show_next_match(self):
        """跳转到下一个搜索匹配"""
        if not self._search_query:
            return
        query = self._search_query.lower()
        for i in range(self.selected_index + 1, len(self._filtered_sessions)):
            s = self._filtered_sessions[i]
            if query in s.title.lower() or query in s.source.lower():
                self.selected_index = i
                self._adjust_scroll()
                self._draw()
                return
        self._set_status("没有更多匹配")

    def _export_current(self):
        """导出当前选中的会话"""
        if not (0 <= self.selected_index < len(self._filtered_sessions)):
            return
        session = self._filtered_sessions[self.selected_index]
        self.term.exit_raw_mode()

        print(f"\n导出会话: {session.title}")
        print(f"文件路径: {session.file_path}")
        self._set_status("导出功能请在CLI模式下使用 (sessionpilot export)")

        self.term.enter_raw_mode()
        self._draw()

    def _set_status(self, message: str):
        """设置状态消息"""
        self._status_message = message
        self._status_time = time.time()


def format_token_short(tokens: int) -> str:
    """格式化Token数量（简短）"""
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    elif tokens >= 1_000:
        return f"{tokens / 1_000:.1f}K"
    return str(tokens)
