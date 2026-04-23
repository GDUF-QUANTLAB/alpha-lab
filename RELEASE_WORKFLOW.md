# Release Workflow (Private + Integration)

## Branching

- `private/*`: 本地私有研发分支，不推送。
- `release/*`: 对外发布集成分支，只保留可公开内容。

## Sync external libs

从同级仓库同步 4 个独立库代码到 `alpha-lab`：

```bash
./scripts/sync_external_libs.sh
```

预览变更（不落盘）：

```bash
./scripts/sync_external_libs.sh --dry-run
```

默认从 `../blazestore`、`../clickhouse_df`、`../xcals`、`../ygo` 同步。  
如需修改源目录，设置 `SOURCE_ROOT`：

```bash
SOURCE_ROOT=/path/to/repos ./scripts/sync_external_libs.sh
```

## Prevent accidental private push

安装 hook（一次）：

```bash
./scripts/install_git_hooks.sh
```

该 hook 会阻止 `private/*` 分支执行 `git push`。
