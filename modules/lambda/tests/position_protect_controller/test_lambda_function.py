import os
import sys
from unittest.mock import patch, MagicMock, call
import pytest
from datetime import date, datetime

# Add the directory (terraform_tradingview/modules/lambda/functions) to sys.path
path_ = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../../modules/lambda/functions")
)
sys.path.insert(0, path_)

os.environ["OANDA_ACCOUNT_ID"] = "test"
os.environ["OANDA_RESTAPI_TOKEN"] = "test"
os.environ["OANDA_API_URL"] = "test"
os.environ["ACCOUNT_MODE"] = "test"

from position_protect_controller.resources.lambda_function import (
    execute_position_protect,
)


@patch("position_protect_controller.resources.lambda_function.OANDA")
@patch(
    "position_protect_controller.resources.lambda_function.PositionProtect.is_under_threshold"
)
@patch(
    "position_protect_controller.resources.lambda_function.PositionProtect.trim_position"
)
def test_execute_position_protect_not_called_trim_position(
    mock_trim_position, mock_is_under_threshold, mock_oanda
):
    # 閾値以上の時は実行されていないことをテストする
    mock_is_under_threshold.side_effect = [False]
    execute_position_protect()

    assert mock_trim_position.call_count == 0


@patch("position_protect_controller.resources.lambda_function.OANDA")
@patch(
    "position_protect_controller.resources.lambda_function.PositionProtect.is_under_threshold"
)
@patch(
    "position_protect_controller.resources.lambda_function.PositionProtect.trim_position"
)
def test_execute_position_protect_called_once_trim_position(
    mock_trim_position, mock_is_under_threshold, mock_oanda
):
    # １度だけ閾値以下の時に１度だけ実行されていることをテストする
    mock_is_under_threshold.side_effect = [True, False]
    execute_position_protect()

    assert mock_trim_position.call_count == 1


@patch("position_protect_controller.resources.lambda_function.OANDA")
@patch(
    "position_protect_controller.resources.lambda_function.PositionProtect.is_under_threshold"
)
@patch(
    "position_protect_controller.resources.lambda_function.PositionProtect.trim_position"
)
def test_execute_position_protect_called_twice_trim_position(
    mock_trim_position, mock_is_under_threshold, mock_oanda
):
    # ２度だけ閾値以下の時に２度だけ実行されていることをテストする
    mock_is_under_threshold.side_effect = [True, True, False]
    execute_position_protect()

    assert mock_trim_position.call_count == 2


@patch("position_protect_controller.resources.lambda_function.OANDA")
@patch(
    "position_protect_controller.resources.lambda_function.PositionProtect.is_under_threshold"
)
@patch(
    "position_protect_controller.resources.lambda_function.PositionProtect.trim_position"
)
def test_execute_position_protect_called_three_times_trim_position(
    mock_trim_position, mock_is_under_threshold, mock_oanda
):
    # ３度だけ閾値以下の時に３度だけ実行されていることをテストする
    mock_is_under_threshold.side_effect = [True, True, True, False]
    execute_position_protect()

    assert mock_trim_position.call_count == 3


@patch("position_protect_controller.resources.lambda_function.OANDA")
@patch(
    "position_protect_controller.resources.lambda_function.PositionProtect.is_under_threshold"
)
@patch(
    "position_protect_controller.resources.lambda_function.PositionProtect.trim_position"
)
def test_execute_position_protect_called_once_take_correct_args(
    mock_trim_position, mock_is_under_threshold, mock_oanda
):
    # １度だけ閾値以下の時に空の dict が渡されていることをテストする
    mock_is_under_threshold.side_effect = [True, False]
    execute_position_protect()

    mock_trim_position.assert_has_calls(
        [
            call({}),
        ]
    )


@patch("position_protect_controller.resources.lambda_function.OANDA")
@patch(
    "position_protect_controller.resources.lambda_function.PositionProtect.is_under_threshold"
)
@patch(
    "position_protect_controller.resources.lambda_function.PositionProtect.trim_position"
)
def test_execute_position_protect_called_twice_take_correct_args(
    mock_trim_position, mock_is_under_threshold, mock_oanda
):
    # ２度閾値以下の時に想定の dict が渡されていることをテストする
    mock_is_under_threshold.side_effect = [True, True, False]
    mock_trim_position.side_effect = [
        {"USD_JPY": [{"id": "1"}, {"id": "2"}]},
        {"USD_JPY": [{"id": "2"}]},
    ]
    execute_position_protect()

    mock_trim_position.assert_has_calls(
        [
            call({}),
            call({"USD_JPY": [{"id": "1"}, {"id": "2"}]}),
        ]
    )
