from __future__ import annotations


class FactorError(Exception):
    """
    因子异常类。

    所有因子异常的基类，提供统一的错误处理接口。
    """

    def __init__(
        self, message: str, original_exception: Exception | None = None
    ) -> None:
        """
        初始化异常。

        Args:
            message: 错误消息
            original_exception: 原始异常（如果有）
        """
        super().__init__(message)
        self.original_exception = original_exception


class FunctionComputeError(FactorError):
    """
    函数计算异常。

    当函数计算过程中发生错误时抛出。
    """

    pass


class FactorContextLoadDependError(FactorError):
    """
    FactorContext 加载依赖因子异常

    当 FactorContext 出现加载异常抛出
    """

    pass
