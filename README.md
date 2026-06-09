# PaperCutter ✂️

> 智能 PDF 试题切分工具 — 自动将 PDF 试卷按空白区域切分为单题页面，支持在线预览与手动调整。

## 功能特性

- **自动切分** — 按文字结构（`split_by_whitespace`）或图像空白区域（`split_by_image`）两种策略，自动检测试题边界
- **在线编辑器** — Vue 3 + Vite 前端，上传 PDF 后可视化预览，拖拽调整切分区域
- **灵活导出** — 支持自定义排版构建输出 PDF（`build_output_original_size`）
- **FastAPI 后端** — 高性能 RESTful API，支持批量处理与页面级操作

## 快速开始

### 前置要求

- Python 3.10+
- Node.js 18+
- npm 9+

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/normal-pcer/PaperCutter.git
cd PaperCutter

# 2. 安装后端依赖
pip install -r backend/requirements.txt

# 3. 安装前端依赖
cd frontend && npm install && cd ..
```

### 启动

```bash
# 终端 1：启动后端 (http://localhost:8000)
cd backend && python server.py

# 终端 2：启动前端 (http://localhost:5173)
cd frontend && npm run dev
```

### 快速使用 CLI 模式

```bash
python main.py
```
默认使用 `split_by_whitespace` 和 `split_by_image` 处理当前目录下的 `1.pdf`，输出 `out_text.pdf` 和 `out_image.pdf`。

## 项目结构

```
PaperCutter/
├── main.py                 # CLI 入口（单次切分）
├── backend/
│   ├── server.py           # FastAPI 服务
│   ├── cutter.py           # 自动切分核心逻辑
│   ├── builder.py          # 输出 PDF 构建
│   └── requirements.txt
├── frontend/
│   ├── src/                # Vue 3 源码
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
├── start.bat               # Windows 启动 & 推送脚本
├── start.sh                # Linux/macOS 启动 & 推送脚本
└── README.md
```

## 技术栈

| 层级     | 技术                                        |
| -------- | ------------------------------------------- |
| 前端     | Vue 3, TypeScript, Vite, Pinia, Axios       |
| 后端     | Python, FastAPI, PyMuPDF, NumPy, Uvicorn    |
| 切分引擎 | PyMuPDF (PDF 解析), NumPy (图像分析)        |

## API 概览

| 端点                              | 说明                       |
| --------------------------------- | -------------------------- |
| `POST /api/pdf/upload`            | 上传 PDF 文件              |
| `POST /api/auto-cut/{file_id}`    | 自动切分（content / image）|
| `POST /api/build`                 | 构建输出 PDF               |
| `GET  /api/pdf/{file_id}/info`    | 获取 PDF 元数据            |
| `GET  /api/pdf/{file_id}/page/{pageNum}/image` | 渲染页面为 PNG |

## 许可证

MIT
