# import logging
import os
import sys
from unittest.mock import patch, MagicMock, call
import pytest
from datetime import date

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

from accumulation_controller.resources.lambda_function import (
    Investment,
    Accumulation,
    OANDA,
)

OANDA._create_client = MagicMock()
oanda = OANDA(
    account_id="test",
    api_key="test",
    api_url="test",
    account_mode="test",
)

platform = oanda
investment = Investment(platform, 3)
# OANDA の規定レバレッジを設定
investment.platform.leverages = {"USD_JPY": 0.022, "USD_MXN": 0.05, "TRY_JPY": 0.25}
investment.platform.account.get_margin_available = MagicMock()
investment.platform.account.get_margin_available.return_value = 1230195
investment.platform.account.get_margin_used = MagicMock()
investment.platform.account.get_margin_used.return_value = 3951594
investment.platform.account.get_net_asset_value = MagicMock()
investment.platform.account.get_net_asset_value.return_value = 5181699

accumulation = Accumulation(platform, 3)


class TestInvestment:

    def test_calcurate_usdjpy_amount_return_collect_value(self):
        # 正しい値が返っていることをテストする
        price_map = {"USD_JPY": OANDA.Price.Prices(90, 100, 95)}  # bid,ask,mid
        # USD_JPY: 100円の時に 150000円分買うとレバレッジが適用され 3倍であれば 4500枚
        jpy_amount = 150000
        expected_usd_amount = 4500
        actual_usd_amount = investment.calcurate_usdjpy_amount(jpy_amount, price_map)
        assert expected_usd_amount == actual_usd_amount

    def test_calcurate_tryjpy_amount_return_collect_value(self):
        # 正しい値が返っていることをテストする
        # 150000円分買うとレバレッジ分割られて 3倍であれば 50000枚
        jpy_amount = 150000
        expected_try_amount = 50000
        actual_try_amount = investment.calcurate_tryjpy_amount(jpy_amount)
        assert expected_try_amount == actual_try_amount

    def test_calculate_required_margin_return_collect_value(self):
        # 正しい値が返っていることをテストする

        # USD_JPY: 100円 であれば、USD を 10000枚買うには 22,000円必要
        instrument = "USD_JPY"
        amount = 10000
        price_map = {"USD_JPY": OANDA.Price.Prices(90, 100, 95)}  # bid,ask,mid
        expected_required_margin = 22000  # 100*10000*0.022
        actual_required_margin = investment.calculate_required_margin(
            instrument=instrument, amount=amount, price_map=price_map
        )
        assert expected_required_margin == actual_required_margin

        # TRY_JPY: 4円 であれば、TRY を 30000枚買うには 120,000円必要
        instrument = "TRY_JPY"
        amount = 30000
        price_map = {"TRY_JPY": OANDA.Price.Prices(3, 4, 4.5)}  # bid,ask,mid
        expected_required_margin = 30000  # 4*30000*0.25
        actual_required_margin = investment.calculate_required_margin(
            instrument=instrument, amount=amount, price_map=price_map
        )
        assert expected_required_margin == actual_required_margin

    def test_verify_purchase_requirements_just_value_is_true(self):
        # 証拠金がピッタリの時には True が返ることをテストする
        investment.platform.account.get_margin_available = MagicMock()
        investment.platform.account.get_margin_available.return_value = 22000

        expected_flag = True
        currency_pair_amounts = {"USD_JPY": 10000}
        price_map = {"USD_JPY": OANDA.Price.Prices(90, 100, 95)}  # bid,ask,mid
        actual_flag = investment.verify_purchase_requirements(
            currency_pair_amounts, price_map
        )

        assert expected_flag == actual_flag
        investment.platform.account.get_margin_available.return_value = 1000000

    def test_verify_purchase_requirements_not_availeble_margin(self):
        # 証拠金不足の時に False が返ることをテストする
        investment.platform.account.get_margin_available = MagicMock()
        investment.platform.account.get_margin_available.return_value = 1000

        expected_flag = False
        currency_pair_amounts = {"USD_JPY": 10000}
        price_map = {"USD_JPY": OANDA.Price.Prices(90, 100, 95)}  # bid,ask,mid
        actual_flag = investment.verify_purchase_requirements(
            currency_pair_amounts, price_map
        )

        assert expected_flag == actual_flag
        investment.platform.account.get_margin_available.return_value = 1000000

    def test_verify_purchase_requirements_collect_flag(self):
        # ダミーのように十分な条件の時には True が返ることをテストする
        expected_flag = True
        currency_pair_amounts = {"USD_JPY": 10000}
        price_map = {"USD_JPY": OANDA.Price.Prices(90, 100, 95)}  # bid,ask,mid
        actual_flag = investment.verify_purchase_requirements(
            currency_pair_amounts, price_map
        )
        assert expected_flag == actual_flag

    def test_verify_purchase_requirements_not_nav(self):
        # 有効残高 / 維持証拠金 が 110% 以下の場合は False が返ることをテストする
        investment.platform.account.get_margin_used = MagicMock()
        investment.platform.account.get_margin_used.return_value = 2000000
        investment.platform.account.get_net_asset_value = MagicMock()
        investment.platform.account.get_net_asset_value.return_value = 2100000
        expected_flag = False
        currency_pair_amounts = {"USD_JPY": 10000}
        price_map = {"USD_JPY": OANDA.Price.Prices(90, 100, 95)}  # bid,ask,mid
        actual_flag = investment.verify_purchase_requirements(
            currency_pair_amounts, price_map
        )
        assert expected_flag == actual_flag
        investment.platform.account.get_margin_used.return_value = 500000
        investment.platform.account.get_net_asset_value.return_value = 3000000

    def test_verify_purchase_requirements_division_zero_is_true(self):
        # 維持証拠金 が 0円の場合は回避し True が返ることをテストする
        investment.platform.account.get_margin_used = MagicMock()
        investment.platform.account.get_margin_used.return_value = 0
        investment.platform.account.get_net_asset_value = MagicMock()
        investment.platform.account.get_net_asset_value.return_value = 2100000
        expected_flag = True
        currency_pair_amounts = {"USD_JPY": 10000}
        price_map = {"USD_JPY": OANDA.Price.Prices(90, 100, 95)}  # bid,ask,mid
        actual_flag = investment.verify_purchase_requirements(
            currency_pair_amounts, price_map
        )
        assert expected_flag == actual_flag
        investment.platform.account.get_margin_used.return_value = 500000
        investment.platform.account.get_net_asset_value.return_value = 3000000

    def test_count_weekdays_in_month(self):
        # 正しい値が返っているかをテストする
        # 2024/09 は平日が 21日
        expected_weekday_count = 21
        weekday_count = Investment.count_weekdays_in_month(date(2024, 9, 1))
        assert expected_weekday_count == weekday_count
        # 2024/10 は平日が 23日
        expected_weekday_count = 23
        weekday_count = Investment.count_weekdays_in_month(date(2024, 10, 1))
        assert expected_weekday_count == weekday_count


class TestAccumulation:

    def test_execute_purchase_take_collect_args(self):
        # place_order が正しい値を受け取っていることをテストする
        accumulation.verify_purchase_requirements = MagicMock()
        accumulation.verify_purchase_requirements.return_value = True
        accumulation.calcurate_usdjpy_amount = MagicMock()
        accumulation.calcurate_usdjpy_amount.return_value = 100
        accumulation.calcurate_tryjpy_amount = MagicMock()
        accumulation.calcurate_tryjpy_amount.return_value = 300
        accumulation.platform.trade.request_place_order = MagicMock()

        accumulation.execute_purchase(100)

        # 注）2回目だけ Short なので - が入っているかを検証
        accumulation.platform.trade.request_place_order.assert_has_calls(
            [
                call(
                    {
                        "order": {
                            "units": "100",
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
                            "units": "-100",
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
                            "units": "300",
                            "instrument": "TRY_JPY",
                            "timeInForce": "FOK",
                            "type": "MARKET",
                            "positionFill": "DEFAULT",
                        }
                    }
                ),
            ]
        )

    def test_get_daily_amount_return_collect_value(self):
        # 正しい値を返していることをテストする
        target_date = date(2024, 10, 1)
        monthly_amount = 230000
        # 2024/10 は 平日 23 日なので 230,000 / 23 = 10,000/day として返ってくる
        expected_daily_amount = 10000
        actual_daily_amount = Accumulation.get_daily_amount(monthly_amount, target_date)
        assert expected_daily_amount == actual_daily_amount
