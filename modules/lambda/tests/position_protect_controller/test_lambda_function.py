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

os.environ["LEVERAGE"] = "3"
os.environ["SECRET_NAME"] = "test"
os.environ["ACCOUNT_MODE"] = "test"
_credentials = {
    "OANDA_ACCOUNT_ID": "test",
    "OANDA_RESTAPI_TOKEN": "test",
    "OANDA_API_URL": "test",
}

from position_protect_controller.resources.lambda_function import (
    execute_position_protect,
    execute_merge_tickets,
    OANDA,
    PositionProtect,
)


@pytest.fixture
def position_protect():
    OANDA._get_credentials = MagicMock().return_value(_credentials)
    OANDA._create_client = MagicMock()
    oanda = OANDA(account_mode="test")
    position_protect = PositionProtect(oanda, 3)
    return position_protect


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


@patch("position_protect_controller.resources.lambda_function.OANDA")
@patch("position_protect_controller.resources.lambda_function.execute_merge_tickets")
@patch(
    "position_protect_controller.resources.lambda_function.PositionProtect.is_under_threshold"
)
@patch(
    "position_protect_controller.resources.lambda_function.PositionProtect.get_total_tickets_amount"
)
def test_execute_position_protect_not_called_execute_merge_tickets(
    mock_get_total_tickets_amount,
    mock_is_under_threshold,
    mock_execute_merge_tickets,
    mock_oanda,
):
    # チケット枚数が 800枚以下のときは実行されないことをテストする
    mock_is_under_threshold.side_effect = [False]
    mock_get_total_tickets_amount.return_value = 799
    execute_position_protect()

    mock_execute_merge_tickets.call_count == 0


@patch("position_protect_controller.resources.lambda_function.OANDA")
@patch("position_protect_controller.resources.lambda_function.execute_merge_tickets")
@patch(
    "position_protect_controller.resources.lambda_function.PositionProtect.is_under_threshold"
)
@patch(
    "position_protect_controller.resources.lambda_function.PositionProtect.get_total_tickets_amount"
)
def test_execute_position_protect_called_once_execute_merge_tickets(
    mock_get_total_tickets_amount,
    mock_is_under_threshold,
    mock_execute_merge_tickets,
    mock_oanda,
):
    # チケット枚数が 800枚以上のときは実行されることをテストする
    mock_is_under_threshold.side_effect = [False]
    mock_get_total_tickets_amount.return_value = 801
    execute_position_protect()

    mock_execute_merge_tickets.call_count == 1


@patch(
    "position_protect_controller.resources.lambda_function.PositionProtect.get_top_losing_positions_by_pair"
)
def test_execute_merge_tickets_called_correct_args_request_close_order(
    mock_get_top_losing_positions_by_pair,
    position_protect,
):
    # 取得した each_currency_position に伴い、順番に close 注文がされていることをテストする
    position_protect.platform.trade._make_close_order_data = MagicMock()
    position_protect.platform.trade._make_close_order_data.return_value = {}
    position_protect.platform.trade.request_close_order = MagicMock()
    position_protect.platform.trade.request_place_order = MagicMock()
    mock_get_top_losing_positions_by_pair.return_value = {
        "USD_JPY": [
            {
                "instrument": "USD_JPY",
                "id": "1",
                "currentUnits": "1",
                "price": "test",
            },
            {
                "instrument": "USD_JPY",
                "id": "2",
                "currentUnits": "2",
                "price": "test",
            },
            {
                "instrument": "USD_JPY",
                "id": "3",
                "currentUnits": "3",
                "price": "test",
            },
        ],
        "USD_MXN": [
            {
                "instrument": "USD_MXN",
                "id": "11",
                "currentUnits": "11",
                "price": "test",
            },
            {
                "instrument": "USD_MXN",
                "id": "22",
                "currentUnits": "22",
                "price": "test",
            },
            {
                "instrument": "USD_MXN",
                "id": "33",
                "currentUnits": "33",
                "price": "test",
            },
        ],
        "TRY_JPY": [
            {
                "instrument": "TRY_JPY",
                "id": "101",
                "currentUnits": "101",
                "price": "test",
            },
            {
                "instrument": "TRY_JPY",
                "id": "202",
                "currentUnits": "202",
                "price": "test",
            },
            {
                "instrument": "TRY_JPY",
                "id": "303",
                "currentUnits": "303",
                "price": "test",
            },
        ],
    }
    expected_call_list = [
        call(trade_id="1", close_data={}),
        call(trade_id="2", close_data={}),
        call(trade_id="3", close_data={}),
        call(trade_id="11", close_data={}),
        call(trade_id="22", close_data={}),
        call(trade_id="33", close_data={}),
        call(trade_id="101", close_data={}),
        call(trade_id="202", close_data={}),
        call(trade_id="303", close_data={}),
    ]

    execute_merge_tickets(position_protect)

    assert (
        position_protect.platform.trade.request_close_order.call_args_list
        == expected_call_list
    )


@patch(
    "position_protect_controller.resources.lambda_function.PositionProtect.get_top_losing_positions_by_pair"
)
def test_execute_merge_tickets_called_correct_args_request_place_order(
    mock_get_top_losing_positions_by_pair,
    position_protect,
):
    # 取得した each_currency_position に伴い、順番に order 注文がされていることをテストする
    position_protect.platform.trade._make_close_order_data = MagicMock()
    position_protect.platform.trade._make_close_order_data.return_value = {}
    position_protect.platform.trade.request_close_order = MagicMock()
    position_protect.platform.trade.request_place_order = MagicMock()
    mock_get_top_losing_positions_by_pair.return_value = {
        "USD_JPY": [
            {
                "instrument": "USD_JPY",
                "id": "1",
                "currentUnits": "1",
                "price": "test",
            },
            {
                "instrument": "USD_JPY",
                "id": "2",
                "currentUnits": "2",
                "price": "test",
            },
            {
                "instrument": "USD_JPY",
                "id": "3",
                "currentUnits": "3",
                "price": "test",
            },
        ],
        "USD_MXN": [
            {
                "instrument": "USD_MXN",
                "id": "11",
                "currentUnits": "11",
                "price": "test",
            },
            {
                "instrument": "USD_MXN",
                "id": "22",
                "currentUnits": "22",
                "price": "test",
            },
            {
                "instrument": "USD_MXN",
                "id": "33",
                "currentUnits": "33",
                "price": "test",
            },
        ],
        "TRY_JPY": [
            {
                "instrument": "TRY_JPY",
                "id": "101",
                "currentUnits": "101",
                "price": "test",
            },
            {
                "instrument": "TRY_JPY",
                "id": "202",
                "currentUnits": "202",
                "price": "test",
            },
            {
                "instrument": "TRY_JPY",
                "id": "303",
                "currentUnits": "303",
                "price": "test",
            },
        ],
    }
    expected_call_list = [
        call(
            {
                "order": {
                    "units": "6",
                    "instrument": "USD_JPY",
                    "timeInForce": "FOK",
                    "type": "MARKET",
                    "positionFill": "DEFAULT",
                }
            }
        ),
        call(
            {
                "order": {
                    "units": "66",
                    "instrument": "USD_MXN",
                    "timeInForce": "FOK",
                    "type": "MARKET",
                    "positionFill": "DEFAULT",
                }
            }
        ),
        call(
            {
                "order": {
                    "units": "606",
                    "instrument": "TRY_JPY",
                    "timeInForce": "FOK",
                    "type": "MARKET",
                    "positionFill": "DEFAULT",
                }
            }
        ),
    ]

    execute_merge_tickets(position_protect)

    assert (
        position_protect.platform.trade.request_place_order.call_args_list
        == expected_call_list
    )


@patch("position_protect_controller.resources.lambda_function.OANDA")
@patch(
    "position_protect_controller.resources.lambda_function.PositionProtect.is_under_threshold"
)
@patch(
    "position_protect_controller.resources.lambda_function.PositionProtect.trim_position"
)
def test_execute_position_protect_stop_after_max_tries(
    mock_trim_position, mock_is_under_threshold, mock_oanda
):
    # 最大試行回数を上回ったら stop することをテストする
    mock_trim_position.return_value = {}
    mock_is_under_threshold.side_effect = [
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    ]

    execute_position_protect()

    assert mock_is_under_threshold.call_count == 11
