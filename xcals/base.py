from __future__ import annotations

import bisect
import importlib.resources
import os
import shutil

import polars as pl

USERHOME = os.path.expanduser("~")
FILE_PATH = os.path.join(USERHOME, ".xcals")
FILE_URL = "https://raw.githubusercontent.com/link-yundi/xcals/refs/heads/main/.xcals"
PACKAGE_XCALS = importlib.resources.files("xcals").joinpath(".xcals")


class Calendar:
    """
    A singleton class for managing trading calendar data.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._df: pl.DataFrame | None = None
        self._dates_list: list[str] = []
        self._dates_set: set[str] = set()
        self._initialized = True

    def _ensure_loaded(self):
        """
        Ensures that the calendar data is loaded from the file.
        """
        if self._df is not None:
            return

        if not os.path.exists(FILE_PATH):
            # 从包内复制到用户目录
            os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)
            shutil.copy(PACKAGE_XCALS, FILE_PATH)

        if not os.path.exists(FILE_PATH):
            raise FileNotFoundError(f"Calendar file not found at {FILE_PATH}")

        self._df = (
            pl.read_csv(
                FILE_PATH,
                has_header=False,
                new_columns=["date"],
            )
            .with_columns(pl.col("date").str.to_date("%Y-%m-%d").alias("Date"))
            .sort("date")
        )
        # Pre-compute Python structures for faster lookup
        self._dates_list = self._df["date"].to_list()
        self._dates_set = set(self._dates_list)

    def update(self):
        """
        Downloads the latest calendar file from the remote URL.
        """
        import urllib.request

        try:
            print(f"Downloading calendar from {FILE_URL} to {FILE_PATH}...")
            # Create directory if not exists
            os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)
            urllib.request.urlretrieve(FILE_URL, FILE_PATH)
            print("Download completed.")
            # Reload data if it was already loaded
            if self._initialized and self._df is not None:
                self._df = None
                self._ensure_loaded()
        except Exception as e:
            print(f"Failed to download calendar: {e}")
            raise

    def get_tradingdays(
        self,
        beg_date: str | None = None,
        end_date: str | None = None,
    ) -> pl.DataFrame:
        """
        Get trading days within a range.

        Args:
            beg_date: Start date (inclusive).
            end_date: End date (inclusive).

        Returns:
            pl.DataFrame: DataFrame with 'date' column.
        """
        self._ensure_loaded()
        result = self._df
        if beg_date is not None:
            result = result.filter(pl.col("date") >= beg_date)
        if end_date is not None:
            result = result.filter(pl.col("date") <= end_date)

        return result.select(pl.col("Date").alias("date"))

    def get_tradingdays_lag(self, date: str, num: int) -> pl.DataFrame:
        """
        Get the last 'num' trading days up to 'date'.

        Args:
            date: The end date.
            num: Number of trading days to retrieve.

        Returns:
            pl.DataFrame: DataFrame containing the last 'num' trading days.
        """
        self._ensure_loaded()
        return self._df.filter(pl.col("date") <= date).tail(abs(num))

    def get_recent_tradeday(self, date: str) -> str:
        """
        Get the most recent trading day on or before 'date'.

        Args:
            date: The reference date.

        Returns:
            str: The most recent trading day.

        Raises:
            ValueError: If no trading day is found before or on 'date'.
        """
        self._ensure_loaded()
        # Find the first date strictly greater than 'date'
        idx = bisect.bisect_right(self._dates_list, date)
        if idx == 0:
            raise ValueError(f"No trading day found before or on {date}")
        # The element before it is <= date
        return self._dates_list[idx - 1]

    def shift_tradeday(self, date: str, num: int = 1) -> str:
        """
        Shift a date by 'num' trading days.

        Strategy for non-trading days:
        - If num > 0: Start from the *next* trading day.
        - If num < 0: Start from the *previous* trading day.

        Args:
            date: Base date.
            num: Number of trading days to shift.

        Returns:
            str: Shifted date.

        Raises:
            IndexError: If the shifted date is out of range.
        """
        if num == 0:
            return date

        self._ensure_loaded()

        if num > 0:
            # Shift Forward
            # bisect_left returns first index >= date.
            # If date is trading day: returns its index.
            # If date is non-trading: returns index of Next trading day.
            # We add num to this index.
            idx = bisect.bisect_left(self._dates_list, date)
            target_idx = idx + num
        else:
            # Shift Backward
            # bisect_right returns first index > date.
            # If date is trading day (i): returns i+1.
            #   target = i+1 + num - 1 = i + num. (Correct)
            # If date is non-trading (between i and i+1): returns i+1 (Next).
            #   target = i+1 + num - 1 = i + num.
            #   Since 'i' is the Previous trading day, this effectively calculates:
            #   Prev_Index + num.
            idx = bisect.bisect_right(self._dates_list, date)
            target_idx = idx + num - 1

        if 0 <= target_idx < len(self._dates_list):
            return self._dates_list[target_idx]
        else:
            raise IndexError(f"Shifted date out of range: {date} + {num}")

    def is_tradeday(self, date: str) -> bool:
        """
        Check if a date is a trading day.

        Args:
            date: Date string in YYYY-MM-DD format.

        Returns:
            bool: True if it is a trading day, False otherwise.
        """
        self._ensure_loaded()
        return date in self._dates_set

    def is_reportdate(self, date: str) -> bool:
        """
        Check if a date is a standard financial report date (quarterly).

        Args:
            date: Date string in YYYY-MM-DD format.

        Returns:
            bool: True if it is a report date (03-31, 06-30, 09-30, 12-31), False otherwise.
        """
        try:
            _, m, d = map(int, date.split("-"))
            if m in [6, 9]:
                if d == 30:
                    return True
            if m in [3, 12]:
                if d == 31:
                    return True
            return False
        except ValueError:
            return False
