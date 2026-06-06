# 🌍 Realtime Earth — 实时 3D 地球数据可视化

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](#-启动)

> **一个 3D 地球，把全球公开的实时数据流汇集到一起：卫星轨道 / 闪电 / 地震 / 野火 / 火山 / 太阳活动。**

![preview](docs/preview.png) <!-- 可选 -->

---

## ✨ 你能看到什么

| 模块 | 内容 | 更新频率 | 数据源 |
|------|------|----------|--------|
| 🛰 **卫星** | ISS / 中国天宫 / 哈勃 / 詹姆斯·韦伯 / Starlink 等 80+ 颗在轨卫星 | 30s | CelesTrak TLE |
| ⚡ **闪电** | 全球闪电实时打点，含正/负极性 | 10s | Blitzortung 社区网络 |
| 🔥 **野火** | NASA 热异常 (VIIRS/MODIS)，亮度/辐射功率 | 30min | NASA FIRMS |
| 🌋 **火山** | Smithsonian 全球活火山活动状态 | 每周 | Smithsonian GVP |
| 💢 **地震** | 全球 M0+ 地震，含深度/海啸标志 | 1min | USGS GeoJSON |
| ☀️ **太阳** | Kp 指数、太阳风、X 射线等级、极光预测 | 1min | NOAA SWPC |

全部**免费 / 公开 / 无需 API key**。无追踪，无登录，无广告。

---

## 🚀 启动 (任何一台电脑，三步搞定)

### 前置要求

- **Python 3.11+** ([下载](https://www.python.org/downloads/))
  - Windows 安装时务必勾选 ✅ "Add Python to PATH"
  - macOS / Linux 通常自带，或用 `brew install python@3.12` / `apt install python3.12`
- 大约 **500 MB 磁盘空间** (虚拟环境 + 依赖)
- 联网 (首次安装依赖 + 拉取实时数据)

### 启动方式

#### Windows 用户 (最简单)

**双击 `start.bat`** — 完事。

或者命令行：
```powershell
python start.py
```

#### macOS / Linux 用户

```bash
chmod +x start.sh   # 首次需要赋予执行权限
./start.sh
```

或直接：
```bash
python3 start.py
```

### 它做了什么 (无需手动操作)

`start.py` 会自动：
1. ✅ 在 PATH 上找一个 Python ≥ 3.11
2. ✅ 在 `backend/.venv` 创建虚拟环境 (只在首次)
3. ✅ `pip install` 后端依赖 (只在首次,约 1-2 分钟)
4. ✅ 复制 `.env.example` 到 `.env` (如果不存在)
5. ✅ 自动释放端口 8000 (杀死残留进程)
6. ✅ 启动 uvicorn,**同一进程**同时服务 API + 前端

首次启动看到 `Application startup complete` 后,**打开浏览器**:

| 地址 | 用途 |
|------|------|
| <http://localhost:8000> | 🌍 3D 地球主界面 |
| <http://localhost:8000/docs> | FastAPI Swagger 文档 |
| <http://localhost:8000/healthz> | 各数据源健康状态 |
| <http://localhost:8000/diag.html> | WebGL 诊断 (黑屏时看这里) |

按 **Ctrl+C** 停止。

---

## 🐛 排查

### 浏览器打开是黑色的地球?

打开 <http://localhost:8000/diag.html>。如果显示 `WebGL 2 — Software` 或 `WebGL 不可用`，说明浏览器没有启用硬件加速：

- **Chrome / Edge**: 地址栏输入 `chrome://settings/system` → 打开 "可用时使用图形加速" → 重启浏览器
- **VS Code 内置浏览器** (Code 1.x): 不支持 WebGL Workers，**请用真正的 Chrome / Edge / Firefox 打开**

### 端口 8000 已被占用?

`start.py` 会自动杀死占用进程。如果还是失败,改端口:
```powershell
$env:REALTIME_EARTH_PORT=9000; python start.py    # Windows PowerShell
REALTIME_EARTH_PORT=9000 python3 start.py          # macOS / Linux
```

### 依赖安装失败 (网络问题 / 编译错误)?

- **numpy 编译错误**: 你装的是 Python 3.13。换 Python 3.12,wheel 都是预编译的,秒装。
- **网络慢**: 用国内镜像
  ```powershell
  cd backend
  .venv\Scripts\python.exe -m pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
  ```

### 闪电图层是空的?

Blitzortung 的数据服务器在中国大陆部分网络下不可达。**这是网络限制，不是 bug** — 后端会优雅降级，其他图层正常工作。

---

## 🏗 架构

```
                ┌──────────────────────────────┐
                │  CelesTrak / Blitzortung /   │
                │  NASA / USGS / NOAA / GVP    │   (公开 API)
                └──────────────┬───────────────┘
                               │ 定时拉取
                ┌──────────────▼───────────────┐
                │   Source Adapters            │   Python: BaseSource 子类
                │   backend/app/sources/*.py   │
                └──────────────┬───────────────┘
                               │ 内存状态 + APScheduler
                ┌──────────────▼───────────────┐
                │   FastAPI + WebSocket        │
                │   (backend/app/main.py)      │
                │   + 挂载 frontend/dist       │
                └──────────────┬───────────────┘
                               │ HTTP / WS (同一端口 8000)
                ┌──────────────▼───────────────┐
                │   Vue 3 + Cesium 1.121       │
                │   (单一 3D 地球)              │
                └──────────────────────────────┘
```

技术栈：
- **后端** — Python 3.11+, FastAPI, asyncio, httpx, sgp4, APScheduler, Pydantic v2
- **前端** — Vue 3, TypeScript, Vite, Pinia, **CesiumJS 1.121**, Tailwind, ECharts
- **实时** — WebSocket 推送各数据源
- **部署** — 单进程 uvicorn 同时服务 API + SPA (无需 nginx / docker)

详见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

---

## 📂 项目结构

```
realtime-earth/
├── start.py            # 跨平台启动器 (核心)
├── start.bat           # Windows 双击启动
├── start.sh            # macOS / Linux 启动
├── .env.example        # 配置模板 (start.py 自动复制为 .env)
│
├── backend/            # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py         # 入口 (FastAPI + 挂载 frontend/dist)
│   │   ├── sources/        # 数据源适配器 (每个一个文件)
│   │   ├── routers/        # REST 路由
│   │   ├── models/         # Pydantic 数据模型
│   │   └── core/           # 配置 / scheduler / WebSocket
│   ├── tests/
│   ├── pyproject.toml      # 依赖声明
│   └── Dockerfile          # (可选,本仓库不用 Docker)
│
├── frontend/           # Vue 3 + Cesium 前端
│   ├── src/                # 源码
│   ├── public/             # 静态资源 (含 diag.html)
│   ├── dist/               # ✅ 预先构建好的产物 (12MB,含 Cesium)
│   │                         直接被后端挂载,用户不用 npm install
│   ├── package.json
│   └── vite.config.ts
│
└── docs/               # 文档
```

---

## 🛠 开发者：如何修改并重新构建前端

如果你想改前端代码，需要装 Node.js 20+：

```bash
cd frontend
npm install           # 装依赖 (~200MB)
npm run dev           # 开发模式,http://localhost:5173,热更新
npm run build         # 重新构建 dist/
```

构建完毕后再运行 `python start.py`，新的 `dist/` 会被自动挂载。

添加一个新的数据源 → 看 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md),`BaseSource` 子类 + 在 `core/scheduler.py` 注册即可。

---

## 📜 数据源版权

| 数据源 | License | 链接 |
|--------|---------|------|
| CelesTrak (TLE) | Public Domain | <https://celestrak.org/> |
| Blitzortung Lightning | 非商业用途免费,需署名 | <https://www.blitzortung.org/> |
| NASA FIRMS | Public Domain | <https://firms.modaps.eosdis.nasa.gov/> |
| USGS Earthquake | Public Domain | <https://earthquake.usgs.gov/> |
| Smithsonian GVP | 非商业用途免费,需署名 | <https://volcano.si.edu/> |
| NOAA SWPC | Public Domain | <https://www.swpc.noaa.gov/> |
| NASA SDO | Public Domain | <https://sdo.gsfc.nasa.gov/> |

本项目代码采用 **MIT** 协议,见 [LICENSE](LICENSE)。
数据层保留原版权,前端会在地球右下角显示来源。

---

## 🎯 为什么做这个?

大多数人知道航班追踪和 ISS 追踪。但很少人知道你可以**实时看到全球的闪电**、**南美哪片雨林正在燃烧**、**Starlink 卫星此刻飞过你头顶的轨迹**,或者**今天 Kp 指数 7 极光圈已经压到北京**。

Realtime Earth 把这些"公开但没人留意"的数据流汇集成一个画面。

---

## 🙏 贡献

Issue / PR 欢迎。如果你想新增数据源、调色板、UI 组件，请先看 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)。

---

> **遇到问题?** 先打开 <http://localhost:8000/healthz> 和 <http://localhost:8000/diag.html>,
> 99% 的问题在这两个页面能找到答案。然后再开 Issue,贴上这两个页面的输出。
