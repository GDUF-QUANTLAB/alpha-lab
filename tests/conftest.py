"""Pytest configuration for alpha-lab tests."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

plt.switch_backend("Agg")
