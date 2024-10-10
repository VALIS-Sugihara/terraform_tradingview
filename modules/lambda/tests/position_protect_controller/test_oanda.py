import os
import sys
from unittest.mock import patch, MagicMock
import pytest

# Add the directory (terraform_tradingview/modules/lambda/functions) to sys.path
path_ = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../../modules/lambda/functions")
)
sys.path.insert(0, path_)

os.environ["OANDA_ACCOUNT_ID"] = "test"
os.environ["OANDA_RESTAPI_TOKEN"] = "test"
os.environ["OANDA_API_URL"] = "test"
os.environ["ACCOUNT_MODE"] = "test"

from position_protect_controller.resources.lambda_function import OANDA


@pytest.fixture
def oanda():
    OANDA._create_client = MagicMock()
    oanda = OANDA(
        account_id=os.environ["OANDA_ACCOUNT_ID"],
        api_key=os.environ["OANDA_RESTAPI_TOKEN"],
        api_url=os.environ["OANDA_API_URL"],
        account_mode=os.environ["ACCOUNT_MODE"],
    )

    return oanda


class TestTrade:

    @patch("position_protect_controller.resources.lambda_function.orders.OrderCreate")
    def test_request_place_order_take_collect_args(self, mock_order_create, oanda):
        # orders.OrderCreate が正しい引数を受けているかテストする
        expected_order_data = {
            "order": {
                "units": "100",  # 正の値は買い、負の値は売り
                "instrument": "USD_JPY",
                "timeInForce": "FOK",
                "type": "MARKET",
                "positionFill": "DEFAULT",
                "stopLossOnFill": {"price": "120.000"},
                "takeProfitOnFill": {"price": "240.000"},
            }
        }

        oanda.trade.request_place_order(expected_order_data)

        mock_order_create.assert_called_once_with(
            oanda.account_id, data=expected_order_data
        )

    def test__make_place_order_data_return_collect_data(self, oanda):
        # order_data が正しい形で生成されているかテストする
        arg_data = {
            "units": "100",  # 正の値は買い、負の値は売り
            "instrument": "USD_JPY",
            # "timeInForce": "FOK",
            # "type": "MARKET",
            # "positionFill": "DEFAULT",
            # "stopLossOnFill": {"price": "120.000"},
            # "takeProfitOnFill": {"price": "240.000"},
        }
        expected_order_data = {
            "order": {
                **arg_data,
                "timeInForce": "FOK",
                "type": "MARKET",
                "positionFill": "DEFAULT",
            }
        }
        actual_order_data = oanda.trade._make_place_order_data(**arg_data)
        assert actual_order_data == expected_order_data

    @patch(
        "position_protect_controller.resources.lambda_function.positions.PositionClose"
    )
    def test_request_close_all_positions_take_collect_args(
        self, mock_position_close, oanda
    ):
        # positions.PositionClose が正しい引数を受けているかテストする
        expected_data = {
            "accountID": oanda.account_id,
            "instrument": "USD_JPY",
            "data": {"longUnits": "ALL"},
        }
        oanda.trade.request_close_all_positions({"longUnits": "ALL"}, "USD_JPY")
        mock_position_close.assert_called_once_with(**expected_data)

    def test__make_all_positions_data_return_collect_data(self, oanda):
        # all_positions_data が正しい形で生成されているかテストする
        expected_all_positions_data = {"longUnits": "ALL"}
        actual_all_positions_data = oanda.trade._make_all_positions_data("long")
        assert actual_all_positions_data == expected_all_positions_data

    def test__make_all_positions_data_exception(self, oanda):
        # long or short 以外の引数に対して例外が送出されることを確認する
        with pytest.raises(Exception) as exc_info:
            oanda.trade._make_all_positions_data("wrongparam")

        # 例外メッセージが正しいかを確認
        assert str(exc_info.value) == "Error: close action 'wrongparam' is wrong"

    def test_request_position_close(self, oanda):
        # positions.PositionClose が正しい引数を受けているかテストする
        pass

    def test__make_position_data(self, oanda):
        # position_data が正しい形で生成されているかテストする
        pass

    @patch("position_protect_controller.resources.lambda_function.trades.TradesList")
    def test_request_trade_list_take_collect_args(self, mock_trade_list, oanda):
        # trades.TradesList が正しい引数を受けているかテストする
        expected_data = {
            "accountID": oanda.account_id,
        }
        oanda.trade.request_trade_list()
        mock_trade_list.assert_called_once_with(**expected_data)

    @patch("position_protect_controller.resources.lambda_function.trades.OpenTrades")
    def test_request_open_trades_take_collect_args(self, mock_open_trades, oanda):
        # trades.OpenTrades が正しい引数を受けているかテストする
        expected_data = {
            "accountID": oanda.account_id,
        }
        oanda.trade.request_open_trades()
        mock_open_trades.assert_called_once_with(**expected_data)

    @patch("position_protect_controller.resources.lambda_function.trades.TradeClose")
    def test_request_close_order_take_collect_args(self, mock_close_order, oanda):
        # trades.TradeClose が正しい引数を受けているかテストする
        expected_data = {
            "accountID": oanda.account_id,
            "tradeID": "100",
            "data": {"units": "50"},
        }
        args = {"trade_id": "100", "close_data": {"units": "50"}}
        oanda.trade.request_close_order(**args)
        mock_close_order.assert_called_once_with(**expected_data)

    def test__make_close_order_data_return_collect_default_data(self, oanda):
        # close_order_data が正しくデフォルトの形で生成されているかテストする
        expected_close_order_data = {"units": "ALL"}
        actual_close_order_data = oanda.trade._make_close_order_data()
        assert actual_close_order_data == expected_close_order_data

    def test__make_close_order_data_return_collect_specific_data(self, oanda):
        # close_order_data が正しく指定の形で生成されているかテストする
        expected_close_order_data = {"units": "123"}
        actual_close_order_data = oanda.trade._make_close_order_data("123")
        assert actual_close_order_data == expected_close_order_data


class TestPrice:

    def test__generate_price_map(self, oanda):
        expected_data = {
            "USD_JPY": (1, 2, 3),
            "USD_MXN": (4, 5, 6),
            "TRY_JPY": (7, 8, 9),
        }
        with patch(
            "position_protect_controller.resources.lambda_function.OANDA.Price.request_price",
            side_effect=[(1, 2, 3), (4, 5, 6), (7, 8, 9)],
        ):
            oanda.price._generate_price_map()
        assert oanda.price.price_map["USD_JPY"] == expected_data["USD_JPY"]
        assert oanda.price.price_map["USD_MXN"] == expected_data["USD_MXN"]
        assert oanda.price.price_map["TRY_JPY"] == expected_data["TRY_JPY"]

    @patch("position_protect_controller.resources.lambda_function.pricing.PricingInfo")
    def test_request_price_take_collect_args(self, mock_pricing_info, oanda):
        # 正しい引数を受け取っているかをテストする
        expected_data = {
            "accountID": oanda.account_id,
            "params": {"instruments": "USD_JPY"},
        }
        oanda.price.request_price("USD_JPY")
        mock_pricing_info.assert_called_once_with(**expected_data)

    def test_request_price_returns_collect_values(self, oanda):
        # 返す値が正しいかをテストする
        oanda.client.request.return_value = {
            "prices": [{"bids": [{"price": "100.000"}], "asks": [{"price": "200.000"}]}]
        }
        prices = oanda.price.request_price("USD_JPY")

        assert prices.bid == 100.000
        assert prices.ask == 200.000
        assert prices.mid == 150.000

        oanda.client.request = MagicMock()

    def test_request_price_returns_PriceMap(self, oanda):
        # 返す型が正しいかをテストする
        oanda.client.request.return_value = {
            "prices": [{"bids": [{"price": "100.000"}], "asks": [{"price": "200.000"}]}]
        }
        prices = oanda.price.request_price("USD_JPY")

        # 返り値が PriceMap (Dict[str, Prices]) かどうか確認
        assert isinstance(prices, oanda.Price.Prices)

        oanda.client.request = MagicMock()


class TestAccount:

    @patch(
        "position_protect_controller.resources.lambda_function.accounts.AccountSummary"
    )
    def test__request_account_summary_take_collect_args(
        self, mock_account_summary, oanda
    ):
        # 正しい引数を受け取っているかをテストする
        expected_data = oanda.account_id
        oanda.account._request_account_summary()
        mock_account_summary.assert_called_once_with(expected_data)

    @patch(
        "position_protect_controller.resources.lambda_function.transactions.TransactionList"
    )
    def test_request_transaction_list_between_dates_take_collect_args(
        self, mock_transaction_list, oanda
    ):
        # 正しい引数を受け取っているかをテストする
        args = {
            "from_date": "2099-10-01",
            "to_date": "2099-10-05",
            "transaction_type": "test_transaction_type",
        }
        expected_data = {
            "accountID": oanda.account_id,
            "params": {
                "from": args["from_date"],
                "to": args["to_date"],
                "type": args["transaction_type"],
                "pageSize": 100,
            },
        }
        oanda.account.request_transaction_list_between_dates(**args)
        mock_transaction_list.assert_called_once_with(**expected_data)

    def test_get_transaction_id_by_list_return_collect_from_id(self, oanda):
        # from の id が正しく返っていることをテストする
        expected_data = "111"
        list_data = {
            "dummy": "dummy",
            "pages": [
                "https://api-fxpractice.oanda.com/v3/accounts/101-009-30020937-001/transactions/idrange?from=111&to=999&type=DAILY_FINANCING"
            ],
        }
        key = "from"
        actual_data = oanda.account.get_transaction_id_by_list(
            list_data=list_data, key=key
        )
        assert expected_data == actual_data

    def test_get_transaction_id_by_list_return_collect_to_id(self, oanda):
        # to の id が正しく返っていることをテストする
        expected_data = "999"
        list_data = {
            "dummy": "dummy",
            "pages": [
                "https://api-fxpractice.oanda.com/v3/accounts/101-009-30020937-001/transactions/idrange?from=111&to=999&type=DAILY_FINANCING"
            ],
        }
        key = "to"
        actual_data = oanda.account.get_transaction_id_by_list(
            list_data=list_data, key=key
        )
        assert expected_data == actual_data

    @patch(
        "position_protect_controller.resources.lambda_function.transactions.TransactionDetails"
    )
    def test_request_transaction_details_by_id_take_collect_args(
        self, mock_transaction_details, oanda
    ):
        # 正しい引数を受け取っているかをテストする
        args = {"id": 1}
        expected_data = {"accountID": oanda.account_id, "transactionID": args["id"]}
        oanda.account.request_transaction_details_by_id(**args)
        mock_transaction_details.assert_called_once_with(**expected_data)

    @patch(
        "position_protect_controller.resources.lambda_function.transactions.TransactionIDRange"
    )
    def test_request_transaction_id_range_take_collect_args(
        self, mock_transaction_id_range, oanda
    ):
        # 正しい引数を受け取っているかをテストする
        args = {"from_id": 1, "to_id": 2, "transaction_type": "ORDER_FILL"}
        expected_data = {
            "accountID": oanda.account_id,
            "params": {
                "from": args["from_id"],
                "to": args["to_id"],
                "type": args["transaction_type"],
                "pageSize": 100,
            },
        }
        oanda.account.request_transaction_id_range(**args)
        mock_transaction_id_range.assert_called_once_with(**expected_data)

    def test_get_financing_by_transaction_details_return_collect_value(self, oanda):
        # 正しい値を返しているかをテスト
        expected_value = 123456.789
        details_data = {
            "id": "121",
            "accountID": "101-009-30020937-001",
            "userID": 30020937,
            "type": "DAILY_FINANCING",
            "financing": "123456.789",
            "positionFinancings": [
                {
                    "instrument": "USD_JPY",
                }
            ],
        }
        actual_value = oanda.account.get_financing_by_transaction_details(
            details_data=details_data
        )
        assert expected_value == actual_value

    def test_get_financing_by_transaction_details_return_float(self, oanda):
        # float を返しているかをテスト
        details_data = {
            "id": "121",
            "accountID": "101-009-30020937-001",
            "userID": 30020937,
            "type": "DAILY_FINANCING",
            "financing": "123456.789",
            "positionFinancings": [
                {
                    "instrument": "USD_JPY",
                }
            ],
        }
        actual_value = oanda.account.get_financing_by_transaction_details(
            details_data=details_data
        )
        assert isinstance(actual_value, float) is True

    @patch(
        "position_protect_controller.resources.lambda_function.OANDA.Account._request_account_summary"
    )
    def test_update_account_summary_is_updated(
        self, mock__request_account_summary, oanda
    ):
        # 口座情報が更新後のものになっているかテストする
        oanda.account.account_summary = {"account_summary": "is not updated"}
        expected_value = {"account_summary": "is updated"}
        mock__request_account_summary.return_value = expected_value
        oanda.account.update_account_summary()
        assert expected_value == oanda.account.account_summary
