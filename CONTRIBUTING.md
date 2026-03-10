# 贡献指南 (Contributing Guide)

感谢你对 **Alpha Lab** 感兴趣！我们需要你的帮助来让这个项目变得更好。

本文档详细说明了如何参与贡献，包括环境配置、代码规范、测试要求以及 Pull Request (PR) 流程。

## 🛠️ 开发环境配置

本项目强烈推荐使用 [uv](https://github.com/astral-sh/uv) 进行环境管理，它能提供极速的依赖安装体验。

### 1. 安装 uv
如果你还没有安装 uv，请参考官方文档或使用 pip 安装：
```bash
pip install uv
```

### 2. 初始化环境
在项目根目录下运行以下命令，这将自动创建虚拟环境并安装所有依赖（包括开发依赖）：
```bash
uv sync --all-extras
```

### 3. 激活环境
```bash
# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

---

## 🎨 代码规范 (Code Style)

为了保持代码库的一致性和高质量，我们使用 **Ruff** 进行代码检查（Linting）和格式化（Formatting）。

### 规则概览
- **行宽限制**: 88 字符（与 Black 兼容）。
- **Python 版本**: 兼容 Python 3.11+。
- **Lint 规则**: 启用 Pyflakes (F), Pycodestyle (E, W), isort (I), Flake8-bugbear (B), Pyupgrade (UP) 等。

### 本地检查
在提交代码前，请务必运行以下命令确保代码符合规范：

```bash
# 1. 自动修复 Lint 问题
ruff check . --fix

# 2. 格式化代码
ruff format .
```

### Pre-commit 钩子 (推荐)
为了避免遗忘，建议配置 Git 的 pre-commit 钩子，这样在每次 `git commit` 时会自动检查：

1. 安装 pre-commit：
   ```bash
   pip install pre-commit
   ```
2. 安装钩子：
   ```bash
   pre-commit install
   ```

---

## 🧪 测试要求 (Testing)

所有新功能或 Bug 修复都必须包含相应的单元测试。我们使用 `pytest` 作为测试框架。

### 运行测试
```bash
pytest tests/
```

确保所有测试通过后再提交代码。

---

## 🚀 提交规范 (Submission Guidelines)

### Pull Request 流程
1. Fork 本仓库到你的 GitHub 账户。
2. 基于 `main` 分支创建一个新分支：`git checkout -b feature/my-feature`。
3. 完成开发，并确保通过了代码检查和测试。
4. 提交更改。推荐使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式，例如：
    - `feat: 添加新的数据源接口`
    - `fix: 修复 clickhouse 写入时的类型错误`
    - `docs: 更新安装文档`
    - `style: 优化代码格式`
    - `refactor: 重构 blazestore 核心逻辑`
5. 推送到你的远程仓库：`git push origin feature/my-feature`。
6. 在 GitHub 上发起 Pull Request。

### Code Review
项目维护者会尽快 Review 你的代码。如果在 CI 检查中发现问题，请及时修复并更新你的 PR。

---

再次感谢你的贡献！
