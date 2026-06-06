# 推送到 GitHub — 三种方式,从最简单到最灵活

项目已经完整写好(`realtime-earth/`),所有 60+ 个文件就位、文档齐全、Docker 一键启动。
现在只差把它推到 GitHub 上。

下面有三种方式,任选一种。

---

## 方式 1:GitHub Desktop(最简单,推荐)

适合不想碰命令行的用户。

1. 下载 GitHub Desktop: <https://desktop.github.com/>
2. 登录你的 GitHub 账号
3. `File` → `Add local repository` → 选择 `realtime-earth/` 文件夹
4. 首次添加会问"create a repository",点 **create**
5. 顶部点 **Publish repository** → 选 Public(开源)或 Private
6. 完成!

之后每次改代码,在 GitHub Desktop 里点 **Commit to main** + **Push origin** 即可。

---

## 方式 2:命令行(最灵活)

### 一次性设置

如果你还没装 Git:

- **Windows**: <https://git-scm.com/download/win>(安装时全选默认)
- **macOS**: `xcode-select --install`
- **Linux**: `sudo apt install git`(Debian/Ubuntu)或 `sudo dnf install git`(Fedora)

### 推送步骤

打开终端/PowerShell,`cd` 到 `realtime-earth/` 文件夹,然后执行:

```bash
cd realtime-earth

# 1. 初始化仓库
git init
git branch -M main

# 2. 配置身份(首次使用 Git 时)
git config user.name "你的名字"
git config user.email "你的邮箱@example.com"

# 3. 添加并提交所有文件
git add .
git commit -m "Initial commit: Realtime Earth v0.1.0

- Backend: FastAPI + APScheduler, 6 data source adapters
  (CelesTrak TLE/SGP4, Blitzortung, USGS, NASA FIRMS, GVP, NOAA SWPC)
- Frontend: Vue 3 + CesiumJS 3D globe, WebSocket real-time push
- Docker Compose one-command deploy
- Full docs (README, ARCHITECTURE, DATA_SOURCES, DEVELOPMENT, OPERATIONS)"

# 4. 在 GitHub 上创建空仓库
#    访问 https://github.com/new
#    - Repository name: realtime-earth
#    - Public(开源)或 Private
#    - 不要勾选 "Add a README" / "Add .gitignore"(我们已经有了)

# 5. 关联远程并推送
git remote add origin https://github.com/<你的用户名>/realtime-earth.git
git push -u origin main
```

### 方式 2b:用 gh CLI 一步到位

如果你装了 [GitHub CLI](https://cli.github.com/)(`brew install gh` / `winget install GitHub.cli`):

```bash
cd realtime-earth
gh auth login                                    # 一次性登录
git init
git add .
git commit -m "Initial commit: Realtime Earth v0.1.0"
gh repo create realtime-earth --public --source=. --remote=origin --push
```

这一条命令直接创建 GitHub repo + 推送,不需要先去网页点。

---

## 方式 3:用项目里提供的脚本(Windows 自动化)

仓库根目录有一个 **`push-to-github.ps1`** 脚本。装好 Git 之后:

1. 在项目根目录按住 Shift + 右键 → "在此处打开 PowerShell 窗口"
2. 运行:

```powershell
.\push-to-github.ps1
```

脚本会引导你:
- 输入 GitHub 用户名
- 决定 Public / Private
- 决定用什么方式(自动检测有没有装 `gh` CLI)
- 自动执行 init / commit / push

如果检测到没装 `gh` CLI,会让你先去 <https://github.com/new> 创建一个空仓库(脚本会暂停,等你创建完按回车继续)。

---

## 验证推送成功

推送完后访问 `https://github.com/<你的用户名>/realtime-earth`,你应该看到:

- ✅ 60+ 个文件
- ✅ README.md 自动渲染
- ✅ LICENSE 显示 MIT
- ✅ 文档目录 `docs/`
- ✅ `.github/workflows/ci.yml` 触发 CI(可能因为 GitHub 资源限制失败,但文件存在)

## 让别人能跑你的项目

推送后告诉用户:

```bash
git clone https://github.com/<你的用户名>/realtime-earth.git
cd realtime-earth
cp .env.example .env
docker compose up -d
# 打开 http://localhost:8080
```

就这样。一个命令起服务。

---

## 推送时遇到问题?

| 问题 | 解决 |
|------|------|
| `git: command not found` | 装 Git: <https://git-scm.com/download/win> |
| `gh: command not found` | 装 GitHub CLI: <https://cli.github.com/> |
| `Permission denied (publickey)` | 用 HTTPS URL 而不是 SSH,或者 `gh auth login` 配 SSH key |
| `remote: Repository not found` | 检查 GitHub 上 repo 名是否和你 push 的一致 |
| `Updates were rejected` | 远程已经有内容,先 `git pull --rebase origin main` 再 push |
| 大文件 push 失败 | 项目里**没有**大文件;如果失败,检查 `.gitignore` 是否覆盖了 `node_modules` 和 `.cache` |
| 推送后 GitHub Actions 失败 | CI 失败**不影响**项目本身,文件已经推上去了 |

---

如果还有问题,直接把错误信息发给我,我帮你看。
