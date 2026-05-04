# SessionPilot

轻量级终端AI会话智能管理CLI工具。

## 安装

```bash
pip install -e .
```

## 使用

```bash
sessionpilot scan          # 扫描AI会话
sessionpilot search "关键词"  # 搜索会话
sessionpilot analyze       # 分析统计
sessionpilot browse        # 交互式浏览
sessionpilot export        # 导出数据
sessionpilot report        # 生成报告
sessionpilot clean         # 清理旧会话
sessionpilot info          # 显示信息
```

## 功能

- 会话扫描与索引
- 智能搜索（关键词/正则/时间/标签）
- 会话分析（统计/趋势/主题/模式）
- 多格式导出（Markdown/JSON/CSV）
- 会话清理
- 交互式TUI浏览
- 多格式报告（HTML/Markdown/JSON）

## 技术要求

- Python 3.8+
- 零外部依赖
