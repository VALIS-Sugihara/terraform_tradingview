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
    PositionProtect,
    OANDA,
)


@pytest.fixture
def position_protect():
    OANDA._create_client = MagicMock()
    oanda = OANDA(
        account_id="test",
        api_key="test",
        api_url="test",
        account_mode="test",
    )

    position_protect = PositionProtect(oanda)

    return position_protect


class TestPositionProtect:

    @patch(
        "position_protect_controller.resources.lambda_function.OANDA.Account.get_margin_used"
    )
    @patch(
        "position_protect_controller.resources.lambda_function.OANDA.Account.get_net_asset_value"
    )
    def test_is_under_threshold_is_healthful(
        self, mock_get_net_asset_value, mock_get_margin_used, position_protect
    ):
        # 閾値以上の際の判定が正しいことを確認する
        mock_get_margin_used.return_value = 100
        mock_get_net_asset_value.return_value = 105

        expected_value = False
        acutual_value = position_protect.is_under_threshold()
        assert expected_value == acutual_value

        position_protect.platform.account.get_margin_used = MagicMock()
        position_protect.platform.account.get_net_asset_value = MagicMock()

    @patch(
        "position_protect_controller.resources.lambda_function.OANDA.Account.get_margin_used"
    )
    @patch(
        "position_protect_controller.resources.lambda_function.OANDA.Account.get_net_asset_value"
    )
    def test_is_under_threshold_is_under(
        self, mock_get_net_asset_value, mock_get_margin_used, position_protect
    ):
        # 閾値以下の際の判定が正しいことを確認する
        mock_get_margin_used.return_value = 100
        mock_get_net_asset_value.return_value = 104

        expected_value = True
        acutual_value = position_protect.is_under_threshold()
        assert expected_value == acutual_value

        position_protect.platform.account.get_margin_used = MagicMock()
        position_protect.platform.account.get_net_asset_value = MagicMock()

    @patch(
        "position_protect_controller.resources.lambda_function.OANDA.Trade.request_open_trades"
    )
    def test_get_top_losing_positions_by_pair_return_correct_value(
        self, mock_request_open_trades, position_protect
    ):
        # 正しい値を返していることをテストする
        mock_request_open_trades.return_value = {
            "trades": [
                {
                    "id": "1",
                    "instrument": "USD_JPY",
                    "price": "111.111",
                    "currentUnits": "18",
                },
                {
                    "id": "20",
                    "instrument": "USD_JPY",
                    "price": "222.000",
                    "currentUnits": "18",
                },
                {
                    "id": "2",
                    "instrument": "USD_MXN",
                    "price": "22.222",
                    "currentUnits": "-18",
                },
                {
                    "id": "300",
                    "instrument": "USD_MXN",
                    "price": "33.000",
                    "currentUnits": "-18",
                },
                {
                    "id": "3",
                    "instrument": "TRY_JPY",
                    "price": "3.333",
                    "currentUnits": "18",
                },
                {
                    "id": "4000",
                    "instrument": "TRY_JPY",
                    "price": "4.000",
                    "currentUnits": "18",
                },
            ]
        }
        expected_value = {
            "USD_JPY": [
                {
                    "id": "20",
                    "instrument": "USD_JPY",
                    "price": "222.000",
                    "currentUnits": "18",
                },
                {
                    "id": "1",
                    "instrument": "USD_JPY",
                    "price": "111.111",
                    "currentUnits": "18",
                },
            ],
            "USD_MXN": [
                {
                    "id": "2",
                    "instrument": "USD_MXN",
                    "price": "22.222",
                    "currentUnits": "-18",
                },
                {
                    "id": "300",
                    "instrument": "USD_MXN",
                    "price": "33.000",
                    "currentUnits": "-18",
                },
            ],
            "TRY_JPY": [
                {
                    "id": "4000",
                    "instrument": "TRY_JPY",
                    "price": "4.000",
                    "currentUnits": "18",
                },
                {
                    "id": "3",
                    "instrument": "TRY_JPY",
                    "price": "3.333",
                    "currentUnits": "18",
                },
            ],
        }
        actual_value = position_protect.get_top_losing_positions_by_pair(top_n=10)
        assert expected_value == actual_value
        position_protect.platform.trade.request_open_trades = MagicMock()

    @patch(
        "position_protect_controller.resources.lambda_function.OANDA.Trade.request_open_trades"
    )
    def test_get_top_losing_positions_by_pair_return_correct_top_n_value(
        self, mock_request_open_trades, position_protect
    ):
        # top_n 個分の正しい値を返していることをテストする
        mock_request_open_trades.return_value = {
            "trades": [
                {
                    "id": "1",
                    "instrument": "USD_JPY",
                    "price": "111.111",
                    "currentUnits": "18",
                },
                {
                    "id": "20",
                    "instrument": "USD_JPY",
                    "price": "222.000",
                    "currentUnits": "18",
                },
                {
                    "id": "2",
                    "instrument": "USD_MXN",
                    "price": "22.222",
                    "currentUnits": "-18",
                },
                {
                    "id": "300",
                    "instrument": "USD_MXN",
                    "price": "33.000",
                    "currentUnits": "-18",
                },
                {
                    "id": "3",
                    "instrument": "TRY_JPY",
                    "price": "3.333",
                    "currentUnits": "18",
                },
                {
                    "id": "4000",
                    "instrument": "TRY_JPY",
                    "price": "4.000",
                    "currentUnits": "18",
                },
            ]
        }
        expected_value = {
            "USD_JPY": [
                {
                    "id": "20",
                    "instrument": "USD_JPY",
                    "price": "222.000",
                    "currentUnits": "18",
                },
            ],
            "USD_MXN": [
                {
                    "id": "2",
                    "instrument": "USD_MXN",
                    "price": "22.222",
                    "currentUnits": "-18",
                },
            ],
            "TRY_JPY": [
                {
                    "id": "4000",
                    "instrument": "TRY_JPY",
                    "price": "4.000",
                    "currentUnits": "18",
                },
            ],
        }
        actual_value = position_protect.get_top_losing_positions_by_pair(top_n=1)
        assert expected_value == actual_value

    def test__filter_each_currency_position_by_open_trades_list_return_correct_value(
        self,
        position_protect,
    ):
        # 正しく通貨ペア毎に分類された値が返っているかをテストする
        args = [
            {
                "id": "1",
                "instrument": "USD_JPY",
                "price": "111.111",
                "currentUnits": "18",
            },
            {
                "id": "20",
                "instrument": "USD_JPY",
                "price": "222.000",
                "currentUnits": "18",
            },
            {
                "id": "2",
                "instrument": "USD_MXN",
                "price": "22.222",
                "currentUnits": "-18",
            },
            {
                "id": "300",
                "instrument": "USD_MXN",
                "price": "33.000",
                "currentUnits": "-18",
            },
            {
                "id": "3",
                "instrument": "TRY_JPY",
                "price": "3.333",
                "currentUnits": "18",
            },
            {
                "id": "4000",
                "instrument": "TRY_JPY",
                "price": "4.000",
                "currentUnits": "18",
            },
        ]
        expected_value = {
            "USD_JPY": [
                {
                    "id": "1",
                    "instrument": "USD_JPY",
                    "price": "111.111",
                    "currentUnits": "18",
                },
                {
                    "id": "20",
                    "instrument": "USD_JPY",
                    "price": "222.000",
                    "currentUnits": "18",
                },
            ],
            "USD_MXN": [
                {
                    "id": "2",
                    "instrument": "USD_MXN",
                    "price": "22.222",
                    "currentUnits": "-18",
                },
                {
                    "id": "300",
                    "instrument": "USD_MXN",
                    "price": "33.000",
                    "currentUnits": "-18",
                },
            ],
            "TRY_JPY": [
                {
                    "id": "3",
                    "instrument": "TRY_JPY",
                    "price": "3.333",
                    "currentUnits": "18",
                },
                {
                    "id": "4000",
                    "instrument": "TRY_JPY",
                    "price": "4.000",
                    "currentUnits": "18",
                },
            ],
        }
        actual_value = (
            position_protect._filter_each_currency_position_by_open_trades_list(args)
        )
        assert expected_value == actual_value

    def test__sort_top_losing_positions_by_each_currency_position_return_correct_sorted_value(
        self,
        position_protect,
    ):
        # 正しくソートされた値が返っているかをテストする
        args = {
            "USD_JPY": [
                {
                    "id": "1",
                    "instrument": "USD_JPY",
                    "price": "111.111",
                    "currentUnits": "18",
                },
                {
                    "id": "20",
                    "instrument": "USD_JPY",
                    "price": "222.000",
                    "currentUnits": "18",
                },
            ],
            "USD_MXN": [
                {
                    "id": "2",
                    "instrument": "USD_MXN",
                    "price": "22.222",
                    "currentUnits": "-18",
                },
                {
                    "id": "300",
                    "instrument": "USD_MXN",
                    "price": "33.000",
                    "currentUnits": "-18",
                },
            ],
            "TRY_JPY": [
                {
                    "id": "3",
                    "instrument": "TRY_JPY",
                    "price": "3.333",
                    "currentUnits": "18",
                },
                {
                    "id": "4000",
                    "instrument": "TRY_JPY",
                    "price": "4.000",
                    "currentUnits": "18",
                },
            ],
        }
        expected_value = {
            "USD_JPY": [
                {
                    "id": "20",
                    "instrument": "USD_JPY",
                    "price": "222.000",
                    "currentUnits": "18",
                },
                {
                    "id": "1",
                    "instrument": "USD_JPY",
                    "price": "111.111",
                    "currentUnits": "18",
                },
            ],
            "USD_MXN": [
                {
                    "id": "2",
                    "instrument": "USD_MXN",
                    "price": "22.222",
                    "currentUnits": "-18",
                },
                {
                    "id": "300",
                    "instrument": "USD_MXN",
                    "price": "33.000",
                    "currentUnits": "-18",
                },
            ],
            "TRY_JPY": [
                {
                    "id": "4000",
                    "instrument": "TRY_JPY",
                    "price": "4.000",
                    "currentUnits": "18",
                },
                {
                    "id": "3",
                    "instrument": "TRY_JPY",
                    "price": "3.333",
                    "currentUnits": "18",
                },
            ],
        }
        actual_value = (
            position_protect._sort_top_losing_positions_by_each_currency_position(args)
        )
        assert expected_value == actual_value

    def test__sort_top_losing_positions_by_each_currency_position_return_correct_top_n_value(
        self,
        position_protect,
    ):
        # 正しく top_n 分の個数が返っているかをテストする
        args = {
            "USD_JPY": [
                {
                    "id": "1",
                    "instrument": "USD_JPY",
                    "price": "111.111",
                    "currentUnits": "18",
                },
                {
                    "id": "20",
                    "instrument": "USD_JPY",
                    "price": "222.000",
                    "currentUnits": "18",
                },
            ],
            "USD_MXN": [
                {
                    "id": "2",
                    "instrument": "USD_MXN",
                    "price": "22.222",
                    "currentUnits": "-18",
                },
                {
                    "id": "300",
                    "instrument": "USD_MXN",
                    "price": "33.000",
                    "currentUnits": "-18",
                },
            ],
            "TRY_JPY": [
                {
                    "id": "3",
                    "instrument": "TRY_JPY",
                    "price": "3.333",
                    "currentUnits": "18",
                },
                {
                    "id": "4000",
                    "instrument": "TRY_JPY",
                    "price": "4.000",
                    "currentUnits": "18",
                },
            ],
        }
        expected_value = {
            "USD_JPY": [
                {
                    "id": "20",
                    "instrument": "USD_JPY",
                    "price": "222.000",
                    "currentUnits": "18",
                },
            ],
            "USD_MXN": [
                {
                    "id": "2",
                    "instrument": "USD_MXN",
                    "price": "22.222",
                    "currentUnits": "-18",
                },
            ],
            "TRY_JPY": [
                {
                    "id": "4000",
                    "instrument": "TRY_JPY",
                    "price": "4.000",
                    "currentUnits": "18",
                },
            ],
        }
        actual_value = (
            position_protect._sort_top_losing_positions_by_each_currency_position(
                args, 1
            )
        )
        assert expected_value == actual_value

    def test_is_correct_currency_is_true(self, position_protect):
        # 判定する通貨が正しいことをテストする
        expected_flag = True
        actual_flag = position_protect.is_correct_currency("USD_JPY")
        assert expected_flag == actual_flag

    def test_is_correct_currency_is_false(self, position_protect):
        # 判定する通貨が誤っていることをテストする
        expected_flag = False
        actual_flag = position_protect.is_correct_currency("EUR_HKD")
        assert expected_flag == actual_flag

    @patch(
        "position_protect_controller.resources.lambda_function.PositionProtect.get_top_losing_positions_by_pair"
    )
    @patch(
        "position_protect_controller.resources.lambda_function.OANDA.Trade.request_close_order"
    )
    def test_trim_position_take_correct_args_by_default(
        self,
        mock_request_close_order,
        mock_get_top_losing_positions_by_pair,
        position_protect,
    ):
        # オープンポジション情報を新たに取得し決済していることを確認する
        mock_get_top_losing_positions_by_pair.return_value = {
            "USD_JPY": [
                {
                    "id": "123",
                    "instrument": "USD_JPY",
                    "price": "test",
                    "currentUnits": "test",
                }
            ],
            "USD_MXN": [
                {
                    "id": "456",
                    "instrument": "USD_MXN",
                    "price": "test",
                    "currentUnits": "test",
                }
            ],
            "TRY_JPY": [
                {
                    "id": "789",
                    "instrument": "TRY_JPY",
                    "price": "test",
                    "currentUnits": "test",
                }
            ],
        }

        position_protect.trim_position()
        mock_request_close_order.assert_has_calls(
            [
                call(trade_id="123", close_data={"units": "ALL"}),
                call(trade_id="456", close_data={"units": "ALL"}),
                call(trade_id="789", close_data={"units": "ALL"}),
            ]
        )

    @patch(
        "position_protect_controller.resources.lambda_function.OANDA.Trade.request_close_order"
    )
    def test_trim_position_take_correct_args_by_args(
        self, mock_request_close_order, position_protect
    ):
        # 渡したオープンポジション情報を元に決済していることを確認する
        args = {
            "USD_JPY": [
                {
                    "id": "1230",
                    "instrument": "USD_JPY",
                    "price": "test",
                    "currentUnits": "test",
                }
            ],
            "USD_MXN": [
                {
                    "id": "4560",
                    "instrument": "USD_MXN",
                    "price": "test",
                    "currentUnits": "test",
                }
            ],
            "TRY_JPY": [
                {
                    "id": "7890",
                    "instrument": "TRY_JPY",
                    "price": "test",
                    "currentUnits": "test",
                }
            ],
        }

        position_protect.trim_position(args)
        mock_request_close_order.assert_has_calls(
            [
                call(trade_id="1230", close_data={"units": "ALL"}),
                call(trade_id="4560", close_data={"units": "ALL"}),
                call(trade_id="7890", close_data={"units": "ALL"}),
            ]
        )

    @patch(
        "position_protect_controller.resources.lambda_function.PositionProtect.get_top_losing_positions_by_pair"
    )
    @patch(
        "position_protect_controller.resources.lambda_function.OANDA.Trade.request_close_order"
    )
    def test_trim_position_take_correct_args_by_empty_list(
        self,
        mock_request_close_order,
        mock_get_top_losing_positions_by_pair,
        position_protect,
    ):
        # 途中で空になった場合に途中まで実行し空の dict を return していることをテストする
        mock_get_top_losing_positions_by_pair.return_value = {
            "USD_JPY": [
                {
                    "id": "1230",
                    "instrument": "USD_JPY",
                    "price": "test",
                    "currentUnits": "test",
                }
            ],
            "USD_MXN": [],
            "TRY_JPY": [
                {
                    "id": "7890",
                    "instrument": "TRY_JPY",
                    "price": "test",
                    "currentUnits": "test",
                }
            ],
        }
        expected_response = {}

        actual_response = position_protect.trim_position()
        mock_request_close_order.assert_has_calls(
            [call(trade_id="1230", close_data={"units": "ALL"})]
        )
        assert expected_response == actual_response

    def test_trim_position_recursive(self, position_protect):
        # 条件を満たさなかった場合再帰的に呼び出しされていることを確認する
        pass

    def test_is_within_business_hours(self, position_protect):
        # 営業時間内の判定が正しいことを確認する
        # 6:00 mon -05:59 sat JST
        # ・午前 6 時 59 分から午前 7 時 5 分 （米国標準時間適用期間）
        # ・午前 5 時 59 分から午前 6 時 5 分 （米国夏時間適用期間）
        # ※米国東部時間　午後 4 時 59 分から午後 5 時 05 分の 6 分間
        pass
