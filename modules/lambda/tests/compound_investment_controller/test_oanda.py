# import logging
import os
import sys
from unittest.mock import patch, MagicMock
import pytest

# Add the directory (terraform_tradingview/modules/lambda/functions) to sys.path
path_ = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../../modules/lambda/functions")
)
sys.path.insert(0, path_)

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
# logger.info("Starting test_oanda...")

os.environ["OANDA_ACCOUNT_ID"] = "test"
os.environ["OANDA_RESTAPI_TOKEN"] = "test"
os.environ["OANDA_API_URL"] = "test"
os.environ["ACCOUNT_MODE"] = "test"

from compound_investment_controller.resources.lambda_function import OANDA


oanda = OANDA(
    account_id=os.environ["OANDA_ACCOUNT_ID"],
    api_key=os.environ["OANDA_RESTAPI_TOKEN"],
    api_url=os.environ["OANDA_API_URL"],
    account_mode=os.environ["ACCOUNT_MODE"],
)
oanda.client = MagicMock()


class TestTrade:

    @patch(
        "compound_investment_controller.resources.lambda_function.orders.OrderCreate"
    )
    def test_place_order(self, mock_order_create):
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

        oanda.trade.place_order(expected_order_data)

        mock_order_create.assert_called_once_with(
            oanda.account_id, data=expected_order_data
        )

    def test__make_order_data(self):
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
        actual_order_data = oanda.trade._make_order_data(**arg_data)
        assert actual_order_data == expected_order_data

    @patch(
        "compound_investment_controller.resources.lambda_function.positions.PositionClose"
    )
    def test_close_all_positions(self, mock_position_close):
        # positions.PositionClose が正しい引数を受けているかテストする
        expected_data = {
            "accountID": oanda.account_id,
            "instrument": "USD_JPY",
            "data": {"longUnits": "ALL"},
        }
        oanda.trade.close_all_positions({"longUnits": "ALL"}, "USD_JPY")
        mock_position_close.assert_called_once_with(**expected_data)

    def test__make_all_positions_data(self):
        # all_positions_data が正しい形で生成されているかテストする
        expected_all_positions_data = {"longUnits": "ALL"}
        actual_all_positions_data = oanda.trade._make_all_positions_data("long")
        assert actual_all_positions_data == expected_all_positions_data

    def test__make_all_positions_data_exception(self):
        # long or short 以外の引数に対して例外が送出されることを確認する
        with pytest.raises(Exception) as exc_info:
            oanda.trade._make_all_positions_data("wrongparam")

        # 例外メッセージが正しいかを確認
        assert str(exc_info.value) == "Error: close action 'wrongparam' is wrong"

    def test_close_position(self):
        # positions.PositionClose が正しい引数を受けているかテストする
        pass

    def test__make_position_data(self):
        # position_data が正しい形で生成されているかテストする
        pass


class TestPrice:

    def test_generate_price_map(self):
        expected_data = {
            "USD_JPY": (1, 2, 3),
            "USD_MXN": (4, 5, 6),
            "TRY_JPY": (7, 8, 9),
        }
        with patch(
            "compound_investment_controller.resources.lambda_function.OANDA.Price.get_price",
            side_effect=[(1, 2, 3), (4, 5, 6), (7, 8, 9)],
        ):
            oanda.price.generate_price_map()
        assert oanda.price.price_map["USD_JPY"] == expected_data["USD_JPY"]
        assert oanda.price.price_map["USD_MXN"] == expected_data["USD_MXN"]
        assert oanda.price.price_map["TRY_JPY"] == expected_data["TRY_JPY"]

    @patch(
        "compound_investment_controller.resources.lambda_function.pricing.PricingInfo"
    )
    def test_get_price_take_collect_args(self, mock_pricing_info):
        # 正しい引数を受け取っているかをテストする
        expected_data = {
            "accountID": oanda.account_id,
            "params": {"instruments": "USD_JPY"},
        }
        oanda.price.get_price("USD_JPY")
        mock_pricing_info.assert_called_once_with(**expected_data)

    def test_get_price_returns_collect_values(self):
        # 返す値が正しいかをテストする
        oanda.client.request.return_value = {
            "prices": [{"bids": [{"price": "100.000"}], "asks": [{"price": "200.000"}]}]
        }
        prices = oanda.price.get_price("USD_JPY")

        assert prices.bid == 100.000
        assert prices.ask == 200.000
        assert prices.mid == 150.000

        oanda.client.request = MagicMock()

    def test_get_price_returns_PriceMap(self):
        # 返す型が正しいかをテストする
        oanda.client.request.return_value = {
            "prices": [{"bids": [{"price": "100.000"}], "asks": [{"price": "200.000"}]}]
        }
        prices = oanda.price.get_price("USD_JPY")

        # 返り値が PriceMap (Dict[str, Prices]) かどうか確認
        assert isinstance(prices, oanda.Price.Prices)

        oanda.client.request = MagicMock()


class TestAccount:

    @patch(
        "compound_investment_controller.resources.lambda_function.accounts.AccountSummary"
    )
    def test_get_margin_available_take_collect_args(self, mock_account_summary):
        # 正しい引数を受け取っているかをテストする
        expected_data = oanda.account_id
        oanda.account.get_margin_available()
        mock_account_summary.assert_called_once_with(expected_data)

    def test_get_swap_points(self):
        pass
