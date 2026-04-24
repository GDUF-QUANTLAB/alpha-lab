# 贡献指南 (Contributing Guide)

感谢你对 Alpha Lab 感兴趣！我们需要你的帮助来让这个项目变得更好。

本文档详细说明了如何参与贡献，包括环境配置、代码规范、测试要求以及 Pull Request (PR) 流程。**所有贡献者（包括项目维护者）都应遵守本指南。**

## 项目边界

`alpha-lab` 是面向量化研究员的一体化研究工具包，当前代码由本仓库统一维护。

研究员主要使用以下顶层包：

- `xcals`: 交易日历工具
- `datacenter`: 行情和基础信息访问入口
- `alphamaster`: 因子数据整合和因子分析工具

以下顶层包作为基础设施随 `alpha-lab` 一起发布，服务于数据存储、数据库访问和任务执行。
它们仍然保留顶层 import 路径，但通常不是研究员文档中的主入口：

- `blazestore`
- `clickhouse_df`
- `ygo`

维护代码时应保持现有顶层包兼容性，避免为了“内部化”而迁移 import 路径。

## 🛠️ 开发环境配置

本项目强烈推荐使用 uv 进行环境管理，它能提供极速的依赖安装体验。

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

## 🎨 代码规范 (Code Style)

为了保持代码库的一致性和高质量，我们使用 Ruff 进行代码检查（Linting）和格式化（Formatting）。

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

### Pre-commit 钩子 (强烈推荐)

为了避免遗忘，建议配置 Git 的 pre-commit 钩子，这样在每次 `git commit` 时会自动检查：
```bash
# 安装 pre-commit
pip install pre-commit

# 安装钩子
pre-commit install
```

## 🧪 测试要求 (Testing)

所有新功能或 Bug 修复都必须包含相应的单元测试。我们使用 `pytest` 作为测试框架。

### 运行测试
```bash
pytest tests/
```
确保所有测试通过后再提交代码。

## 📝 提交规范 (Commit Convention)

我们推荐使用 **Conventional Commits** 格式，使提交历史清晰、便于自动化生成变更日志。提交信息格式如下：

```
<类型>: <简短描述>

<详细描述（可选）>
<关联 Issue（可选）>
```

### 常用类型说明

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 添加数据源接口` |
| `fix` | Bug 修复 | `fix: 修复 ClickHouse 写入时的类型错误` |
| `docs` | 仅文档变更 | `docs: 更新安装文档` |
| `style` | 代码格式调整（不影响逻辑） | `style: 优化代码格式` |
| `refactor` | 重构（既非新功能也非修复） | `refactor: 重构 BlazeStore 核心逻辑` |
| `test` | 添加或修正测试 | `test: 增加认证模块单元测试` |
| `chore` | 构建过程或辅助工具变更 | `chore: 升级 ruff 版本` |

## 🚀 Pull Request 流程

所有变更（包括项目维护者）都必须通过 Pull Request 提交到 `main` 分支。`main` 分支受保护，禁止直接推送。

### 标准 PR 流程

1. **Fork 本仓库**（外部贡献者）或**直接获取最新代码**（项目成员）：
   - 外部贡献者：Fork 仓库到你的 GitHub 账户。
   - 项目成员：`git checkout main && git pull origin main`

2. **创建新分支**（使用有意义的命名）：
   ```bash
   git checkout -b feature/my-feature    # 新功能
   # 或
   git checkout -b fix/bug-description   # Bug 修复
   ```

3. **完成开发**，确保：
   - 代码符合规范（已运行 `ruff check . --fix` 和 `ruff format .`）
   - 所有测试通过（`pytest tests/`）
   - 提交信息符合 Conventional Commits 格式

4. **推送分支**：
   ```bash
   git push -u origin feature/my-feature
   ```

5. **发起 Pull Request**：
   - 访问仓库页面，点击 “Pull requests” → “New pull request”
   - 选择 `main` 作为目标分支，你的功能分支作为对比分支
   - **务必使用项目提供的 [PR 模板](.github/PULL_REQUEST_TEMPLATE.md)**，清晰描述：
     - 变更内容
     - 关联的 Issue（如有，使用 `Closes #issue`）
     - 测试情况
     - 是否影响现有功能

6. **等待代码审查**：
   - 项目维护者会尽快审查你的 PR
   - **重要**：所有 PR 必须获得**至少一名其他核心成员的批准**后才能合并（包括项目所有者）
   - 如果 CI 检查失败，请及时修复并更新你的 PR（直接推送即可，PR 会自动更新）

7. **合并与清理**：
   - PR 合并后，你的功能分支将被自动删除（如已配置）
   - 本地可执行 `git checkout main && git pull origin main` 同步最新代码

### 紧急修复 (Hotfix) 流程

对于需要快速修复的严重问题：
1. 从 `main` 分支创建 `hotfix/critical-fix` 分支
2. 完成修复并确保 CI 通过
3. 发起 PR，标题添加 `[URGENT]` 前缀
4. 在团队沟通渠道通知核心成员优先审查

## 📌 沟通与帮助

- **有问题或建议**：请先在 [Issues](链接) 中搜索是否已有相关讨论，若无则创建新 Issue。
- **想讨论或提问**：欢迎加入 [Discussions](链接) 进行交流。
- **安全漏洞**：请勿公开提交 Issue，参考 [SECURITY.md](链接) 中的指引私下报告。

再次感谢你的贡献！你的每一行代码、每一个建议，都会让 Alpha Lab 变得更好。
