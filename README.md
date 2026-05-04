<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/Dependencies-Zero-success.svg" alt="Zero Dependencies">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg" alt="Cross Platform">
  <img src="https://img.shields.io/badge/Tests-148%20Passed-brightgreen.svg" alt="Tests">
</p>

<h1 align="center">🧭 SessionPilot</h1>

<p align="center">
  <strong>轻量级终端AI会话智能管理引擎</strong><br>
  <strong>Lightweight Terminal AI Session Intelligent Management Engine</strong>
</p>

<p align="center">
  <a href="#简体中文">简体中文</a> ·
  <a href="#繁體中文">繁體中文</a> ·
  <a href="#english">English</a>
</p>

---

<a id="简体中文"></a>

## 🎉 项目介绍

**SessionPilot** 是一款轻量级的终端AI会话智能管理CLI工具，专为管理 Claude Code、Codex、Cursor、Windsurf 等AI编码助手的会话历史而设计。

### 💡 解决的痛点

- **会话数据散落各处**：AI编码助手的会话数据分散在多个隐藏目录中，难以统一管理和检索
- **历史对话无法搜索**：当需要回顾之前与AI的对话时，只能手动翻找，效率极低
- **磁盘空间浪费**：大量历史会话文件占用磁盘空间，但缺乏有效的清理手段
- **使用习惯不透明**：不清楚自己与AI助手的交互频率、主题分布和使用模式

### ✨ 自研差异化亮点

- 🚀 **零依赖设计**：仅使用Python标准库，无需安装任何第三方包
- 🔍 **多维度搜索引擎**：支持关键词、正则表达式、时间范围、标签、来源等多维度组合搜索
- 📊 **深度分析引擎**：会话统计、时间趋势、主题分布、使用模式等多维度分析
- 🖥️ **交互式TUI浏览器**：终端原生键盘导航，支持实时搜索和详情查看
- 📤 **多格式导出**：Markdown、JSON、CSV三种格式灵活导出
- 🧹 **智能清理策略**：按时间、大小、数量等多维度智能清理旧会话
- 📋 **精美报告生成**：HTML暗色主题报告（含可视化图表）、Markdown、JSON格式

---

## ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 🔎 **智能扫描** | 自动扫描 `~/.claude`、`~/.codex`、`~/.cursor`、`~/.windsurf` 等目录，支持JSON/JSONL多格式解析 |
| 🔍 **全文搜索** | 关键词搜索、正则搜索、时间范围过滤、标签过滤、来源过滤，多维度组合查询 |
| 📊 **数据分析** | 会话统计、来源分布、每日/每小时趋势、主题提取、使用模式分析 |
| 📤 **多格式导出** | 支持 **Markdown**、**JSON**、**CSV** 三种格式导出，可选是否包含消息内容 |
| 🧹 **智能清理** | 按时间/大小/数量/最小文件大小策略清理，支持 **dry-run** 预览模式 |
| 🖥️ **TUI浏览器** | 终端原生交互界面，`j/k` 上下移动、`/` 实时搜索、`Enter` 查看详情 |
| 📋 **报告生成** | **HTML** 暗色主题报告（含柱状图）、**Markdown** 报告、**JSON** 报告 |
| ⚡ **零依赖** | 仅使用Python标准库，`pip install` 后即可使用，无任何第三方依赖 |
| 🌍 **跨平台** | 完美支持 **Windows**、**macOS**、**Linux** 三大平台 |

---

## 🚀 快速开始

### 环境要求

- **Python 3.8** 或更高版本
- 无需任何第三方依赖

### 安装

```bash
# 克隆仓库
git clone https://github.com/gitstq/SessionPilot.git
cd SessionPilot

# 安装（开发模式）
pip install -e .

# 或者直接运行（无需安装）
python -m session_pilot --help
```

### 基本使用

```bash
# 扫描所有AI会话数据
sessionpilot scan

# 仅扫描Claude会话
sessionpilot scan --source claude

# 搜索包含关键词的会话
sessionpilot search "refactor"

# 使用正则搜索
sessionpilot search --regex "error|exception|bug"

# 按时间范围搜索
sessionpilot search --after "2026-01-01" --before "2026-05-01"

# 分析会话统计
sessionpilot analyze

# 交互式浏览会话
sessionpilot browse

# 导出为Markdown
sessionpilot export --format md --output sessions.md

# 导出为JSON
sessionpilot export --format json --output sessions.json

# 导出为CSV
sessionpilot export --format csv --output sessions.csv

# 生成HTML报告
sessionpilot report --format html --output report.html

# 生成Markdown报告
sessionpilot report --format md --output report.md

# 预览清理操作（不实际删除）
sessionpilot clean --dry-run --older-than 30d

# 清理30天前的会话
sessionpilot clean --older-than 30d

# 显示系统信息和支持的来源
sessionpilot info
```

---

## 📖 详细使用指南

### 扫描会话

```bash
# 扫描所有来源
sessionpilot scan

# 扫描指定来源
sessionpilot scan --source claude
sessionpilot scan --source cursor
sessionpilot scan --source codex
sessionpilot scan --source windsurf

# 添加自定义扫描目录
sessionpilot scan --dir /path/to/custom/sessions

# 静默模式（仅输出结果数量）
sessionpilot scan --quiet

# 扫描但不更新索引
sessionpilot scan --no-index
```

### 搜索会话

```bash
# 关键词搜索
sessionpilot search "authentication"

# 正则搜索
sessionpilot search --regex "fix|bug|patch"

# 组合搜索：关键词 + 时间范围 + 来源
sessionpilot search "API" --after "2026-04-01" --source claude

# 限制结果数量
sessionpilot search "database" --limit 20

# 按时间排序
sessionpilot search "test" --sort time
```

### 分析会话

```bash
# 基础分析
sessionpilot analyze

# 按来源分析
sessionpilot analyze --by-source

# 详细模式（含趋势和模式分析）
sessionpilot analyze --detailed

# 输出为JSON格式
sessionpilot analyze --format json
```

### 清理会话

```bash
# 预览模式（不实际删除）
sessionpilot clean --dry-run

# 清理30天前的会话
sessionpilot clean --older-than 30d

# 清理超过100MB的会话
sessionpilot clean --max-size 100MB

# 保留最近50个会话
sessionpilot clean --keep 50

# 组合策略
sessionpilot clean --older-than 60d --max-size 500MB --keep 100
```

### 导出数据

```bash
# 导出为Markdown（含消息内容）
sessionpilot export --format md --output all_sessions.md

# 导出为JSON（不含消息内容，仅元数据）
sessionpilot export --format json --output metadata.json --no-content

# 导出为CSV
sessionpilot export --format csv --output sessions.csv

# 按来源过滤导出
sessionpilot export --source claude --format md --output claude_sessions.md
```

---

## 💡 设计思路与迭代规划

### 设计理念

SessionPilot 的核心设计理念是 **"让AI会话数据可搜索、可分析、可管理"**。随着AI编码助手在日常开发中的普及，会话数据的管理成为一个被忽视但日益重要的需求。

### 技术选型

- **Python标准库**：选择零依赖设计，降低用户使用门槛，确保在任何Python环境中都能直接运行
- **JSON索引**：使用轻量级JSON文件作为索引存储，避免引入数据库依赖
- **终端原生TUI**：利用终端原始模式实现交互式浏览，无需额外UI框架

### 后续迭代计划

- [ ] 🔄 支持 Copilot、Gemini CLI 等更多AI助手
- [ ] 📊 增加更多可视化图表类型
- [ ] 🔔 会话监控模式，实时跟踪新会话
- [ ] 📡 支持远程会话数据源
- [ ] 🧠 基于关键词的智能标签推荐
- [ ] 📦 会话打包归档功能

---

## 📦 打包与部署指南

### 本地安装

```bash
# 开发模式安装
pip install -e .

# 生产安装
pip install .
```

### 直接运行

```bash
# 无需安装，直接运行
python -m session_pilot [命令]
```

### 兼容环境

| 平台 | Python版本 | 状态 |
|------|-----------|------|
| Windows 10/11 | 3.8+ | ✅ 支持 |
| macOS 12+ | 3.8+ | ✅ 支持 |
| Ubuntu 20.04+ | 3.8+ | ✅ 支持 |
| CentOS 7+ | 3.8+ | ✅ 支持 |

---

## 🤝 贡献指南

欢迎贡献代码！请遵循以下规范：

1. **Fork** 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m "feat: 添加某功能"`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 **Pull Request**

### 提交规范

遵循 Angular 提交规范：
- `feat:` 新增功能
- `fix:` 修复问题
- `docs:` 文档更新
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具变更

### Issue 反馈

请使用 [GitHub Issues](https://github.com/gitstq/SessionPilot/issues) 提交Bug报告或功能建议。

---

## 📄 开源协议

本项目基于 [MIT License](LICENSE) 开源。

---

<a id="繁體中文"></a>

## 🎉 專案介紹

**SessionPilot** 是一款輕量級的終端AI會話智慧管理CLI工具，專為管理 Claude Code、Codex、Cursor、Windsurf 等AI編碼助手的會話歷史而設計。

### 💡 解決的痛點

- **會話資料散落各處**：AI編碼助手的會話資料分散在多個隱藏目錄中，難以統一管理和檢索
- **歷史對話無法搜尋**：當需要回顧之前與AI的對話時，只能手動翻找，效率極低
- **磁碟空間浪費**：大量歷史會話檔案佔用磁碟空間，但缺乏有效的清理手段
- **使用習慣不透明**：不清楚自己與AI助手的互動頻率、主題分佈和使用模式

### ✨ 自研差異化亮點

- 🚀 **零依賴設計**：僅使用Python標準庫，無需安裝任何第三方套件
- 🔍 **多維度搜尋引擎**：支援關鍵字、正規表達式、時間範圍、標籤、來源等多維度組合搜尋
- 📊 **深度分析引擎**：會話統計、時間趨勢、主題分佈、使用模式等多維度分析
- 🖥️ **互動式TUI瀏覽器**：終端原生鍵盤導航，支援即時搜尋和詳情查看
- 📤 **多格式匯出**：Markdown、JSON、CSV三種格式靈活匯出
- 🧹 **智慧清理策略**：按時間、大小、數量等多維度智慧清理舊會話
- 📋 **精美報告生成**：HTML暗色主題報告（含視覺化圖表）、Markdown、JSON格式

---

## ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 🔎 **智慧掃描** | 自動掃描 `~/.claude`、`~/.codex`、`~/.cursor`、`~/.windsurf` 等目錄，支援JSON/JSONL多格式解析 |
| 🔍 **全文搜尋** | 關鍵字搜尋、正規搜尋、時間範圍過濾、標籤過濾、來源過濾，多維度組合查詢 |
| 📊 **資料分析** | 會話統計、來源分佈、每日/每小時趨勢、主題提取、使用模式分析 |
| 📤 **多格式匯出** | 支援 **Markdown**、**JSON**、**CSV** 三種格式匯出，可選是否包含訊息內容 |
| 🧹 **智慧清理** | 按時間/大小/數量/最小檔案大小策略清理，支援 **dry-run** 預覽模式 |
| 🖥️ **TUI瀏覽器** | 終端原生互動介面，`j/k` 上下移動、`/` 即時搜尋、`Enter` 查看詳情 |
| 📋 **報告生成** | **HTML** 暗色主題報告（含柱狀圖）、**Markdown** 報告、**JSON** 報告 |
| ⚡ **零依賴** | 僅使用Python標準庫，`pip install` 後即可使用，無任何第三方依賴 |
| 🌍 **跨平台** | 完美支援 **Windows**、**macOS**、**Linux** 三大平台 |

---

## 🚀 快速開始

### 環境要求

- **Python 3.8** 或更高版本
- 無需任何第三方依賴

### 安裝

```bash
# 克隆倉庫
git clone https://github.com/gitstq/SessionPilot.git
cd SessionPilot

# 安裝（開發模式）
pip install -e .

# 或者直接執行（無需安裝）
python -m session_pilot --help
```

### 基本使用

```bash
# 掃描所有AI會話資料
sessionpilot scan

# 僅掃描Claude會話
sessionpilot scan --source claude

# 搜尋包含關鍵字的會話
sessionpilot search "refactor"

# 使用正規搜尋
sessionpilot search --regex "error|exception|bug"

# 按時間範圍搜尋
sessionpilot search --after "2026-01-01" --before "2026-05-01"

# 分析會話統計
sessionpilot analyze

# 互動式瀏覽會話
sessionpilot browse

# 匯出為Markdown
sessionpilot export --format md --output sessions.md

# 匯出為JSON
sessionpilot export --format json --output sessions.json

# 匯出為CSV
sessionpilot export --format csv --output sessions.csv

# 生成HTML報告
sessionpilot report --format html --output report.html

# 預覽清理操作（不實際刪除）
sessionpilot clean --dry-run --older-than 30d

# 清理30天前的會話
sessionpilot clean --older-than 30d

# 顯示系統資訊和支援的來源
sessionpilot info
```

---

## 📖 詳細使用指南

### 掃描會話

```bash
# 掃描所有來源
sessionpilot scan

# 掃描指定來源
sessionpilot scan --source claude
sessionpilot scan --source cursor
sessionpilot scan --source codex
sessionpilot scan --source windsurf

# 新增自訂掃描目錄
sessionpilot scan --dir /path/to/custom/sessions

# 靜默模式（僅輸出結果數量）
sessionpilot scan --quiet

# 掃描但不更新索引
sessionpilot scan --no-index
```

### 搜尋會話

```bash
# 關鍵字搜尋
sessionpilot search "authentication"

# 正規搜尋
sessionpilot search --regex "fix|bug|patch"

# 組合搜尋：關鍵字 + 時間範圍 + 來源
sessionpilot search "API" --after "2026-04-01" --source claude

# 限制結果數量
sessionpilot search "database" --limit 20

# 按時間排序
sessionpilot search "test" --sort time
```

### 分析會話

```bash
# 基礎分析
sessionpilot analyze

# 按來源分析
sessionpilot analyze --by-source

# 詳細模式（含趨勢和模式分析）
sessionpilot analyze --detailed

# 輸出為JSON格式
sessionpilot analyze --format json
```

### 清理會話

```bash
# 預覽模式（不實際刪除）
sessionpilot clean --dry-run

# 清理30天前的會話
sessionpilot clean --older-than 30d

# 清理超過100MB的會話
sessionpilot clean --max-size 100MB

# 保留最近50個會話
sessionpilot clean --keep 50

# 組合策略
sessionpilot clean --older-than 60d --max-size 500MB --keep 100
```

### 匯出資料

```bash
# 匯出為Markdown（含訊息內容）
sessionpilot export --format md --output all_sessions.md

# 匯出為JSON（不含訊息內容，僅元資料）
sessionpilot export --format json --output metadata.json --no-content

# 匯出為CSV
sessionpilot export --format csv --output sessions.csv

# 按來源過濾匯出
sessionpilot export --source claude --format md --output claude_sessions.md
```

---

## 💡 設計思路與迭代規劃

### 設計理念

SessionPilot 的核心設計理念是 **「讓AI會話資料可搜尋、可分析、可管理」**。隨著AI編碼助手在日常開發中的普及，會話資料的管理成為一個被忽視但日益重要的需求。

### 技術選型

- **Python標準庫**：選擇零依賴設計，降低使用者使用門檻，確保在任何Python環境中都能直接執行
- **JSON索引**：使用輕量級JSON檔案作為索引儲存，避免引入資料庫依賴
- **終端原生TUI**：利用終端原始模式實現互動式瀏覽，無需額外UI框架

### 後續迭代計畫

- [ ] 🔄 支援 Copilot、Gemini CLI 等更多AI助手
- [ ] 📊 增加更多視覺化圖表類型
- [ ] 🔔 會話監控模式，即時追蹤新會話
- [ ] 📡 支援遠端會話資料來源
- [ ] 🧠 基於關鍵字的智慧標籤推薦
- [ ] 📦 會話打包歸檔功能

---

## 📦 打包與部署指南

### 本地安裝

```bash
# 開發模式安裝
pip install -e .

# 生產安裝
pip install .
```

### 直接執行

```bash
# 無需安裝，直接執行
python -m session_pilot [命令]
```

### 相容環境

| 平台 | Python版本 | 狀態 |
|------|-----------|------|
| Windows 10/11 | 3.8+ | ✅ 支援 |
| macOS 12+ | 3.8+ | ✅ 支援 |
| Ubuntu 20.04+ | 3.8+ | ✅ 支援 |
| CentOS 7+ | 3.8+ | ✅ 支援 |

---

## 🤝 貢獻指南

歡迎貢獻程式碼！請遵循以下規範：

1. **Fork** 本倉庫
2. 建立特性分支：`git checkout -b feature/your-feature`
3. 提交變更：`git commit -m "feat: 新增某功能"`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 **Pull Request**

### 提交規範

遵循 Angular 提交規範：
- `feat:` 新增功能
- `fix:` 修復問題
- `docs:` 文件更新
- `refactor:` 程式碼重構
- `test:` 測試相關
- `chore:` 建構/工具變更

### Issue 回饋

請使用 [GitHub Issues](https://github.com/gitstq/SessionPilot/issues) 提交Bug報告或功能建議。

---

## 📄 開源協議

本專案基於 [MIT License](LICENSE) 開源。

---

<a id="english"></a>

## 🎉 Introduction

**SessionPilot** is a lightweight CLI tool for intelligently managing terminal AI coding assistant session history. It is designed specifically for managing conversations from Claude Code, Codex, Cursor, Windsurf, and other AI coding assistants.

### 💡 Problems Solved

- **Scattered session data**: AI coding assistant session data is spread across multiple hidden directories, making it difficult to manage and search
- **Unsearchable conversation history**: When you need to revisit previous AI conversations, manual browsing is the only option — extremely inefficient
- **Wasted disk space**: Large amounts of historical session files consume disk space without effective cleanup tools
- **Opaque usage patterns**: No visibility into interaction frequency, topic distribution, and usage patterns with AI assistants

### ✨ Key Differentiators

- 🚀 **Zero dependencies**: Uses only Python standard library — no third-party packages needed
- 🔍 **Multi-dimensional search**: Keyword, regex, time range, tag, and source filtering with combinable queries
- 📊 **Deep analytics**: Session statistics, time trends, topic distribution, and usage pattern analysis
- 🖥️ **Interactive TUI browser**: Native terminal keyboard navigation with real-time search and detail view
- 📤 **Multi-format export**: Flexible export to Markdown, JSON, and CSV formats
- 🧹 **Smart cleanup**: Intelligent cleanup by time, size, count, and minimum file size strategies
- 📋 **Beautiful reports**: HTML dark-themed reports (with charts), Markdown, and JSON formats

---

## ✨ Core Features

| Feature | Description |
|---------|-------------|
| 🔎 **Smart Scanning** | Auto-scans `~/.claude`, `~/.codex`, `~/.cursor`, `~/.windsurf` directories with JSON/JSONL multi-format parsing |
| 🔍 **Full-text Search** | Keyword search, regex search, time range filtering, tag filtering, source filtering with combinable multi-dimensional queries |
| 📊 **Data Analytics** | Session statistics, source distribution, daily/hourly trends, topic extraction, and usage pattern analysis |
| 📤 **Multi-format Export** | Supports **Markdown**, **JSON**, **CSV** export with optional message content inclusion |
| 🧹 **Smart Cleanup** | Cleanup by time/size/count/min-file-size strategies with **dry-run** preview mode |
| 🖥️ **TUI Browser** | Native terminal interactive UI — `j/k` to navigate, `/` to search, `Enter` for details |
| 📋 **Report Generation** | **HTML** dark-themed reports (with bar charts), **Markdown** reports, **JSON** reports |
| ⚡ **Zero Dependencies** | Only Python standard library — works out of the box after `pip install` |
| 🌍 **Cross-platform** | Full support for **Windows**, **macOS**, and **Linux** |

---

## 🚀 Quick Start

### Requirements

- **Python 3.8** or higher
- No third-party dependencies required

### Installation

```bash
# Clone the repository
git clone https://github.com/gitstq/SessionPilot.git
cd SessionPilot

# Install (development mode)
pip install -e .

# Or run directly (no installation needed)
python -m session_pilot --help
```

### Basic Usage

```bash
# Scan all AI session data
sessionpilot scan

# Scan only Claude sessions
sessionpilot scan --source claude

# Search sessions by keyword
sessionpilot search "refactor"

# Search with regex
sessionpilot search --regex "error|exception|bug"

# Search by time range
sessionpilot search --after "2026-01-01" --before "2026-05-01"

# Analyze session statistics
sessionpilot analyze

# Interactive session browser
sessionpilot browse

# Export as Markdown
sessionpilot export --format md --output sessions.md

# Export as JSON
sessionpilot export --format json --output sessions.json

# Export as CSV
sessionpilot export --format csv --output sessions.csv

# Generate HTML report
sessionpilot report --format html --output report.html

# Generate Markdown report
sessionpilot report --format md --output report.md

# Preview cleanup (dry run)
sessionpilot clean --dry-run --older-than 30d

# Clean sessions older than 30 days
sessionpilot clean --older-than 30d

# Show system info and supported sources
sessionpilot info
```

---

## 📖 Detailed Usage Guide

### Scanning Sessions

```bash
# Scan all sources
sessionpilot scan

# Scan specific source
sessionpilot scan --source claude
sessionpilot scan --source cursor
sessionpilot scan --source codex
sessionpilot scan --source windsurf

# Add custom scan directories
sessionpilot scan --dir /path/to/custom/sessions

# Quiet mode (output count only)
sessionpilot scan --quiet

# Scan without updating index
sessionpilot scan --no-index
```

### Searching Sessions

```bash
# Keyword search
sessionpilot search "authentication"

# Regex search
sessionpilot search --regex "fix|bug|patch"

# Combined search: keyword + time range + source
sessionpilot search "API" --after "2026-04-01" --source claude

# Limit results
sessionpilot search "database" --limit 20

# Sort by time
sessionpilot search "test" --sort time
```

### Analyzing Sessions

```bash
# Basic analysis
sessionpilot analyze

# Analyze by source
sessionpilot analyze --by-source

# Detailed mode (with trends and patterns)
sessionpilot analyze --detailed

# Output as JSON
sessionpilot analyze --format json
```

### Cleaning Sessions

```bash
# Preview mode (no actual deletion)
sessionpilot clean --dry-run

# Clean sessions older than 30 days
sessionpilot clean --older-than 30d

# Clean sessions larger than 100MB
sessionpilot clean --max-size 100MB

# Keep only the latest 50 sessions
sessionpilot clean --keep 50

# Combined strategy
sessionpilot clean --older-than 60d --max-size 500MB --keep 100
```

### Exporting Data

```bash
# Export as Markdown (with message content)
sessionpilot export --format md --output all_sessions.md

# Export as JSON (metadata only, no content)
sessionpilot export --format json --output metadata.json --no-content

# Export as CSV
sessionpilot export --format csv --output sessions.csv

# Filter by source before export
sessionpilot export --source claude --format md --output claude_sessions.md
```

---

## 💡 Design Philosophy & Roadmap

### Design Philosophy

SessionPilot's core philosophy is **"Make AI session data searchable, analyzable, and manageable."** As AI coding assistants become ubiquitous in daily development, session data management has emerged as an overlooked but increasingly important need.

### Technology Choices

- **Python Standard Library**: Zero-dependency design lowers the barrier to entry and ensures it runs in any Python environment
- **JSON Indexing**: Lightweight JSON file-based indexing avoids database dependencies
- **Native Terminal TUI**: Terminal raw mode for interactive browsing without additional UI frameworks

### Roadmap

- [ ] 🔄 Support for Copilot, Gemini CLI, and more AI assistants
- [ ] 📊 Additional visualization chart types
- [ ] 🔔 Session monitoring mode with real-time tracking
- [ ] 📡 Remote session data source support
- [ ] 🧠 Keyword-based smart tag recommendations
- [ ] 📦 Session archiving and bundling

---

## 📦 Packaging & Deployment

### Local Installation

```bash
# Development mode
pip install -e .

# Production install
pip install .
```

### Direct Execution

```bash
# No installation needed
python -m session_pilot [command]
```

### Compatible Environments

| Platform | Python Version | Status |
|----------|---------------|--------|
| Windows 10/11 | 3.8+ | ✅ Supported |
| macOS 12+ | 3.8+ | ✅ Supported |
| Ubuntu 20.04+ | 3.8+ | ✅ Supported |
| CentOS 7+ | 3.8+ | ✅ Supported |

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork** this repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "feat: add some feature"`
4. Push the branch: `git push origin feature/your-feature`
5. Submit a **Pull Request**

### Commit Convention

Follow the Angular commit convention:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation update
- `refactor:` Code refactoring
- `test:` Test-related changes
- `chore:` Build/tooling changes

### Issue Reporting

Please use [GitHub Issues](https://github.com/gitstq/SessionPilot/issues) to submit bug reports or feature requests.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/gitstq">gitstq</a>
</p>
