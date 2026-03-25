"""
数据整合框架

提供因子数据与行情数据的整合功能，与因子计算模块解耦。

职责:
    1. 接受因子数据(DataFrame)格式
    2. 加载 prices 相关数据并缓存
    3. 拼接对齐后提供给 polens 或其他控件
    4. 支持更换因子数据，但 prices 仍然使用缓存

Example:
    >>> import polars as pl
    >>> from alphamaster.rack import Rack
    >>>
    >>> factor_df = pl.DataFrame({
    ...     "date": ["2023-01-01", "2023-01-01"],
    ...     "asset": ["A", "B"],
    ...     "value": [0.1, 0.2],
    ... }).with_columns(pl.col("date").str.to_date())
    >>>
    >>> rack = Rack()
    >>> rack.load_prices("2023-01-01", "2023-12-31")
    >>> rack.set_factor(factor_df)
    >>> data = rack.get_data()
"""

from __future__ import annotations

import polars as pl

from .loader import get_all_prices


class Rack:
    """数据整合器。

    整合因子数据与行情数据，支持 prices 缓存复用。

    Attributes:
        factor_df: 因子数据
        prices_df: 行情数据（缓存）
        merged_df: 合并后的数据

    Example:
        >>> rack = Rack()
        >>> rack.load_prices("2023-01-01", "2023-12-31")
        >>> rack.set_factor(factor_df)
        >>> data = rack.get_data()
    """

    def __init__(self) -> None:
        self._factor_df: pl.DataFrame | None = None
        self._prices_df: pl.DataFrame | None = None
        self._merged_df: pl.DataFrame | None = None

        self._prices_range: tuple[str, str] | None = None

    @property
    def factor_df(self) -> pl.DataFrame | None:
        return self._factor_df

    @property
    def prices_df(self) -> pl.DataFrame | None:
        return self._prices_df

    @property
    def merged_df(self) -> pl.DataFrame | None:
        return self._merged_df

    def load_prices(
        self,
        beg_date: str,
        end_date: str,
        beg_time: str = "09:30:00",
        end_time: str = "15:00:00",
        *,
        force_reload: bool = False,
    ) -> Rack:
        """加载行情数据并缓存。

        如果已有缓存且日期范围相同，则跳过加载。

        Args:
            beg_date: 开始日期
            end_date: 结束日期
            beg_time: VWAP 计算开始时间
            end_time: VWAP 计算结束时间
            force_reload: 是否强制重新加载

        Returns:
            self，支持链式调用
        """
        if not force_reload and self._prices_df is not None:
            if self._prices_range == (beg_date, end_date):
                return self

        self._prices_df = get_all_prices(
            beg_date=beg_date,
            end_date=end_date,
            beg_time=beg_time,
            end_time=end_time,
        )
        self._prices_range = (beg_date, end_date)
        self._merged_df = None

        return self

    def set_factor(
        self,
        factor_df: pl.DataFrame,
        value_col: str = "value",
    ) -> Rack:
        """设置因子数据。

        Args:
            factor_df: 因子数据，必须包含 date, asset, value_col 列
            value_col: 因子值列名，默认 "value"

        Returns:
            self，支持链式调用

        Raises:
            ValueError: 数据缺少必需列
        """
        required_cols = {"date", "asset", value_col}
        missing_cols = required_cols - set(factor_df.columns)
        if missing_cols:
            raise ValueError(f"因子数据缺少必需列: {missing_cols}")

        if value_col != "value":
            factor_df = factor_df.with_columns(pl.col(value_col).alias("value")).drop(
                value_col
            )

        self._factor_df = factor_df.select("date", "asset", "value")
        self._merged_df = None

        return self

    def merge(self) -> pl.DataFrame:
        """合并因子数据与行情数据。

        Returns:
            合并后的数据，包含 date, asset, value, vwap, adj_factor 列

        Raises:
            RuntimeError: 未加载因子数据或行情数据
        """
        if self._factor_df is None:
            raise RuntimeError("请先调用 set_factor() 设置因子数据")

        if self._prices_df is None:
            raise RuntimeError("请先调用 load_prices() 加载行情数据")

        self._merged_df = (
            self._prices_df.join(
                self._factor_df,
                on=["date", "asset"],
                how="left",
            )
            .sort("date", "asset")
            .with_columns(
                pl.col("limit_up").forward_fill().over("asset", order_by="date"),
                pl.col("limit_down").forward_fill().over("asset", order_by="date"),
                pl.col("close").forward_fill().over("asset", order_by="date"),
                pl.col("prev_close").forward_fill().over("asset", order_by="date"),
                pl.col("adj_factor")
                .forward_fill()
                .over("asset", order_by="date")
                .fill_null(1.0),
            )
        )

        return self._merged_df

    def get_data(self) -> pl.DataFrame:
        """获取合并后的数据。

        如果尚未合并，则自动调用 merge()。

        Returns:
            合并后的数据
        """
        if self._merged_df is None:
            return self.merge()
        return self._merged_df

    def clear_factor(self) -> Rack:
        """清除因子数据，保留行情缓存。

        用于更换因子数据时复用行情缓存。

        Returns:
            self，支持链式调用
        """
        self._factor_df = None
        self._merged_df = None
        return self

    def clear_all(self) -> Rack:
        """清除所有数据。

        Returns:
            self，支持链式调用
        """
        self._factor_df = None
        self._prices_df = None
        self._merged_df = None
        self._prices_range = None
        return self
