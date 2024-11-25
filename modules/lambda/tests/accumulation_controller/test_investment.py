import os
import sys
from unittest.mock import patch, MagicMock, call
import pytest
from datetime import date, datetime, timezone, timedelta

# Add the directory (terraform_tradingview/modules/lambda/functions) to sys.path
path_ = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../../modules/lambda/functions")
)
sys.path.insert(0, path_)

os.environ["SECRET_NAME"] = "test"
os.environ["ACCOUNT_MODE"] = "test"
_credentials = {
    "OANDA_ACCOUNT_ID": "test",
    "OANDA_RESTAPI_TOKEN": "test",
    "OANDA_API_URL": "test",
}

from accumulation_controller.resources.lambda_function import (
    Investment,
    Accumulation,
    OANDA,
)


@pytest.fixture
def investment():
    OANDA._get_credentials = MagicMock().return_value(_credentials)
    OANDA._create_client = MagicMock()
    oanda = OANDA(account_mode="test")

    investment = Investment(oanda, 3)
    # OANDA の規定レバレッジを設定
    investment.platform.leverages = {"USD_JPY": 0.022, "USD_MXN": 0.05, "TRY_JPY": 0.25}

    return investment


@pytest.fixture
def accumulation():
    OANDA._get_credentials = MagicMock().return_value(_credentials)
    OANDA._create_client = MagicMock()
    oanda = OANDA(account_mode="test")

    accumulation = Accumulation(oanda, 3)

    return accumulation


class TestInvestment:

    def test_calcurate_usdjpy_amount_return_collect_value(self, investment):
        # 正しい値が返っていることをテストする
        price_map = {"USD_JPY": OANDA.Price.Prices(90, 100, 95)}  # bid,ask,mid
        # USD_JPY: 100円の時に 150000円分買うとレバレッジが適用され 3倍であれば 4500枚
        jpy_amount = 150000
        expected_usd_amount = 4500
        actual_usd_amount = investment.calcurate_usdjpy_amount(jpy_amount, price_map)
        assert expected_usd_amount == actual_usd_amount

    def test_calcurate_tryjpy_amount_return_collect_value(self, investment):
        # 正しい値が返っていることをテストする
        # 150000円分買うとレバレッジ分割られて 3倍であれば 50000枚
        jpy_amount = 150000
        expected_try_amount = 50000
        actual_try_amount = investment.calcurate_tryjpy_amount(jpy_amount)
        assert expected_try_amount == actual_try_amount

    def test_calculate_required_margin_return_collect_value(self, investment):
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

    @patch(
        "accumulation_controller.resources.lambda_function.OANDA.Account.get_margin_available"
    )
    @patch(
        "accumulation_controller.resources.lambda_function.OANDA.Account.get_margin_used"
    )
    @patch(
        "accumulation_controller.resources.lambda_function.OANDA.Account.get_net_asset_value"
    )
    def test_verify_purchase_requirements_just_value_is_true(
        self,
        mock_get_net_asset_value,
        mock_get_margin_used,
        mock_get_margin_available,
        investment,
    ):
        # 証拠金がピッタリの時には True が返ることをテストする
        mock_get_margin_available.return_value = 22000
        mock_get_margin_used.return_value = 100000
        mock_get_net_asset_value.return_value = 1000000

        expected_flag = True
        currency_pair_amounts = {"USD_JPY": 10000}
        price_map = {"USD_JPY": OANDA.Price.Prices(90, 100, 95)}  # bid,ask,mid
        actual_flag = investment.verify_purchase_requirements(
            currency_pair_amounts, price_map
        )

        assert expected_flag == actual_flag
        investment.platform.account.get_margin_available.return_value = 1000000

    @patch(
        "accumulation_controller.resources.lambda_function.OANDA.Account.get_margin_available"
    )
    @patch(
        "accumulation_controller.resources.lambda_function.OANDA.Account.get_margin_used"
    )
    @patch(
        "accumulation_controller.resources.lambda_function.OANDA.Account.get_net_asset_value"
    )
    def test_verify_purchase_requirements_not_availeble_margin(
        self,
        mock_get_net_asset_value,
        mock_get_margin_used,
        mock_get_margin_available,
        investment,
    ):
        # 証拠金不足の時に False が返ることをテストする
        mock_get_margin_available.return_value = 1000
        mock_get_margin_used.return_value = 100000
        mock_get_net_asset_value.return_value = 1000000

        expected_flag = False
        currency_pair_amounts = {"USD_JPY": 10000}
        price_map = {"USD_JPY": OANDA.Price.Prices(90, 100, 95)}  # bid,ask,mid
        actual_flag = investment.verify_purchase_requirements(
            currency_pair_amounts, price_map
        )

        assert expected_flag == actual_flag
        investment.platform.account.get_margin_available.return_value = 1000000

    @patch(
        "accumulation_controller.resources.lambda_function.OANDA.Account.get_margin_available"
    )
    @patch(
        "accumulation_controller.resources.lambda_function.OANDA.Account.get_margin_used"
    )
    @patch(
        "accumulation_controller.resources.lambda_function.OANDA.Account.get_net_asset_value"
    )
    def test_verify_purchase_requirements_collect_flag(
        self,
        mock_get_net_asset_value,
        mock_get_margin_used,
        mock_get_margin_available,
        investment,
    ):
        # ダミーのように十分な条件の時には True が返ることをテストする
        mock_get_margin_available.return_value = 100000
        mock_get_margin_used.return_value = 100000
        mock_get_net_asset_value.return_value = 1000000

        expected_flag = True
        currency_pair_amounts = {"USD_JPY": 10000}
        price_map = {"USD_JPY": OANDA.Price.Prices(90, 100, 95)}  # bid,ask,mid
        actual_flag = investment.verify_purchase_requirements(
            currency_pair_amounts, price_map
        )
        assert expected_flag == actual_flag

    @patch(
        "accumulation_controller.resources.lambda_function.OANDA.Account.get_margin_available"
    )
    @patch(
        "accumulation_controller.resources.lambda_function.OANDA.Account.get_margin_used"
    )
    @patch(
        "accumulation_controller.resources.lambda_function.OANDA.Account.get_net_asset_value"
    )
    def test_verify_purchase_requirements_not_nav(
        self,
        mock_get_net_asset_value,
        mock_get_margin_used,
        mock_get_margin_available,
        investment,
    ):
        # 有効残高 / 維持証拠金 が 110% 以下の場合は False が返ることをテストする
        mock_get_margin_available.return_value = 1000000
        mock_get_margin_used.return_value = 2000000
        mock_get_net_asset_value.return_value = 2100000
        expected_flag = False
        currency_pair_amounts = {"USD_JPY": 10000}
        price_map = {"USD_JPY": OANDA.Price.Prices(90, 100, 95)}  # bid,ask,mid
        actual_flag = investment.verify_purchase_requirements(
            currency_pair_amounts, price_map
        )
        assert expected_flag == actual_flag
        investment.platform.account.get_margin_used.return_value = 500000
        investment.platform.account.get_net_asset_value.return_value = 3000000

    @patch(
        "accumulation_controller.resources.lambda_function.OANDA.Account.get_margin_available"
    )
    @patch(
        "accumulation_controller.resources.lambda_function.OANDA.Account.get_margin_used"
    )
    @patch(
        "accumulation_controller.resources.lambda_function.OANDA.Account.get_net_asset_value"
    )
    def test_verify_purchase_requirements_division_zero_is_true(
        self,
        mock_get_net_asset_value,
        mock_get_margin_used,
        mock_get_margin_available,
        investment,
    ):
        # 維持証拠金 が 0円の場合は回避し True が返ることをテストする
        mock_get_margin_available.return_value = 1000000
        mock_get_margin_used.return_value = 0
        mock_get_net_asset_value.return_value = 2100000
        expected_flag = True
        currency_pair_amounts = {"USD_JPY": 10000}
        price_map = {"USD_JPY": OANDA.Price.Prices(90, 100, 95)}  # bid,ask,mid
        actual_flag = investment.verify_purchase_requirements(
            currency_pair_amounts, price_map
        )
        assert expected_flag == actual_flag
        investment.platform.account.get_margin_used.return_value = 500000
        investment.platform.account.get_net_asset_value.return_value = 3000000

    def test_count_weekdays_in_month(self, investment):
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

    @patch(
        "accumulation_controller.resources.lambda_function.Accumulation.verify_purchase_requirements"
    )
    @patch(
        "accumulation_controller.resources.lambda_function.Accumulation.calcurate_usdjpy_amount"
    )
    @patch(
        "accumulation_controller.resources.lambda_function.Accumulation.calcurate_tryjpy_amount"
    )
    @patch(
        "accumulation_controller.resources.lambda_function.OANDA.Trade.request_place_order"
    )
    def test_execute_purchase_take_collect_args(
        self,
        mock_request_place_order,
        mock_calcurate_tryjpy_amount,
        mock_calcurate_usdjpy_amount,
        mock_verify_purchase_requirements,
        accumulation,
    ):
        # place_order が正しい値を受け取っていることをテストする
        mock_verify_purchase_requirements.return_value = True
        mock_calcurate_usdjpy_amount.return_value = 100
        mock_calcurate_tryjpy_amount.return_value = 300

        accumulation.execute_purchase(100)

        # 注）2回目だけ Short なので - が入っているかを検証
        mock_request_place_order.assert_has_calls(
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

    def test_is_additional_purchase_day(self, accumulation):
        # 追加購入日の判定が正しいことを確認する
        pass

    def test_get_25th_or_previous_friday_return_25th(self):
        # 25日が平日の月の場合、25日日付が返ることをテストする
        JST = timezone(timedelta(hours=9))
        target_date = datetime(2024, 10, 3, tzinfo=JST)  # 2024/10/25 は金曜日
        excepted_value = date(2024, 10, 25)  # 2024/10/25 は金曜日
        actual_value = Accumulation.get_25th_or_previous_friday(target_date)
        assert excepted_value == actual_value

    def test_get_25th_or_previous_friday_return_previous_friday(self):
        # 25日が土日の月の場合、直前の金曜日の日付が返ることをテストする
        JST = timezone(timedelta(hours=9))
        target_date = datetime(2024, 8, 25, tzinfo=JST)  # 2024/08/25 は土曜日
        excepted_value = date(2024, 8, 23)  # 2024/08/23 は金曜日
        actual_value = Accumulation.get_25th_or_previous_friday(target_date)
        assert excepted_value == actual_value

    def test_is_25th_or_previous_friday_return_true(self):
        # 25日が平日の月の場合、25日に実行すると True が返ることをテストする
        target_date = date(2024, 10, 25)  # 2024/10/25 は金曜日
        execution_date = date(2024, 10, 25)  # 2024/10/25 は金曜日
        excepted_value = True
        actual_value = Accumulation.is_25th_or_previous_friday_today(
            target_date, execution_date
        )
        assert excepted_value == actual_value
        # 25日が土日の月の場合、指定日に実行すると true が返ることをテストする
        target_date = date(2024, 8, 23)  # 2024/8/23 は金曜日
        execution_date = date(2024, 8, 23)  # 2024/8/23 は金曜日
        excepted_value = True
        actual_value = Accumulation.is_25th_or_previous_friday_today(
            target_date, execution_date
        )
        assert excepted_value == actual_value

    def test_is_25th_or_previous_friday_return_false(self):
        # 25日が平日の月の場合、違う日に実行すると False が返ることをテストする
        target_date = date(2024, 10, 25)  # 2024/10/25 は金曜日
        execution_date = date(2024, 10, 24)  # 2024/10/24 は木曜日
        excepted_value = False
        actual_value = Accumulation.is_25th_or_previous_friday_today(
            target_date, execution_date
        )
        assert excepted_value == actual_value
        # 25日が土日の月の場合、25日に実行すると False が返ることをテストする
        target_date = date(2024, 8, 23)  # 2024/8/23 は金曜日
        execution_date = date(2024, 8, 25)  # 2024/8/25 は日曜日
        excepted_value = False
        actual_value = Accumulation.is_25th_or_previous_friday_today(
            target_date, execution_date
        )
        assert excepted_value == actual_value
