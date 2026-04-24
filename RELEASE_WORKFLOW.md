# Release Workflow

## Branching

- `release/*`: 对外发布集成分支，只保留可公开内容。

## Maintenance Direction

`alpha-lab` 是面向量化研究员的一体化研究工具包。研究员主要使用
`xcals`、`datacenter` 和 `alphamaster`；其他底层模块作为内部基础设施随包发布。

当前发布包已经包含这些模块。后续维护方向是将它们作为 `alpha-lab` 的整体交付内容管理，
而不是继续强调独立库拆分。

## Release Checks

发布前至少运行：

```bash
uv run --extra dev ruff format --check .
uv run --extra dev ruff check .
uv run --extra dev pytest tests/
uv build --no-sources
```
