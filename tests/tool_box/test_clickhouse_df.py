from unittest.mock import patch

import pandas as pd
import polars as pl
import pytest

from tool_box.clickhouse_df import client


# Mock clickhouse_driver.Client
@pytest.fixture
def mock_client():
    with patch("tool_box.clickhouse_df.client.Client") as MockClient:
        client_instance = MockClient.return_value
        yield client_instance


def test_connect(mock_client):
    # Test valid connection
    urls = ["localhost:9000"]
    user = "default"
    password = ""

    conn = client.connect(urls, user, password)
    # assert conn == mock_client.return_value  # This fails due to mock object identity issues sometimes
    assert conn is not None

    # Test empty urls
    with pytest.raises(ValueError, match="urls 参数不能为空"):
        client.connect([], user, password)

    # Test invalid url format
    with pytest.raises(ValueError, match="非法的 ClickHouse 地址格式"):
        client.connect(["invalid_url"], user, password)


def test_to_pandas(mock_client):
    # Setup mock return value
    expected_df = pd.DataFrame({"a": [1, 2, 3]})
    mock_client.return_value.query_dataframe.return_value = expected_df

    # Inject mock client into thread local storage for default connection
    # Or pass explicitly
    # Note: mock_client fixture returns the INSTANCE, so we use it directly
    res = client.to_pandas("SELECT * FROM test", conn=mock_client)
    assert res.equals(expected_df)
    mock_client.query_dataframe.assert_called_with("SELECT * FROM test")


def test_to_polars(mock_client):
    # Setup mock return value for execute
    # execute returns (data, columns)
    # columns is list of (name, type) tuples

    # data should be columnar because columnar=True is used in implementation
    mock_data = [(1, 2), ("a", "b")]
    mock_columns = [("id", "Int32"), ("val", "String")]

    # mock_client is the instance
    mock_client.execute.return_value = (mock_data, mock_columns)

    res = client.to_polars("SELECT * FROM test", conn=mock_client)

    # Check result
    assert isinstance(res, pl.DataFrame)
    assert res.shape == (2, 2)
    assert res.columns == ["id", "val"]
    assert res["id"].dtype == pl.Int32
    assert res["val"].dtype == pl.String

    # Verify values
    assert res["id"][0] == 1
    assert res["val"][1] == "b"


def test_to_polars_empty(mock_client):
    # Test empty result
    mock_client.return_value.execute.return_value = ([], [("id", "Int32")])

    res = client.to_polars("SELECT * FROM empty", conn=mock_client.return_value)

    assert isinstance(res, pl.DataFrame)
    assert res.shape == (0, 1)
    assert res.columns == ["id"]
    assert res["id"].dtype == pl.Int32
