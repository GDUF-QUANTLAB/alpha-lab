# Changelog

All notable changes to alpha-lab will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-06-03

### Added

- **xcals**: 新增 `if_safe` 参数，支持按披露截止日过滤财报日期 ([#14](https://github.com/GDUF-QUANTLAB/alpha-lab/pull/14))
- **xcals**: 将日历数据 (`.xcals`) 嵌入包内，首次使用无需手动下载 ([#14](https://github.com/GDUF-QUANTLAB/alpha-lab/pull/14))
- **ygo**: 新增 `Pool.submit_batch` 批量提交任务接口，提升大规模任务分发效率

### Fixed

- **alphamaster**: 修复 `Rack.set_factor` 丢失额外列的问题 — 现在除 `date`/`asset`/`value` 核心列外，自动保留 `factor_df` 中的其他元数据列（如行业分组 `Lv1`），确保 `FactorAnalyzer` 分组分析正常工作 ([#19](https://github.com/GDUF-QUANTLAB/alpha-lab/pull/19))
- **xcals**: 修复 `get_previous_report_dates` 对非法 `season` 参数的校验 — 恢复 `ValueError` 异常抛出 ([#15](https://github.com/GDUF-QUANTLAB/alpha-lab/pull/15))

### Changed

- 停止跟踪 `docs/` 目录，将其加入 `.gitignore`
- 清理 `alphamaster` 中未使用的 import

---

## [0.1.9] — 2025-04-29

_Initial tracked release._
