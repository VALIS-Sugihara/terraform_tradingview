# import logging
import os
import sys
from unittest.mock import patch, MagicMock
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

# from compound_investment_controller.resources.lambda_function import OANDA


# oanda = OANDA(
#     account_id=os.environ["OANDA_ACCOUNT_ID"],
#     api_key=os.environ["OANDA_RESTAPI_TOKEN"],
#     api_url=os.environ["OANDA_API_URL"],
#     account_mode=os.environ["ACCOUNT_MODE"],
# )
# oanda.client = MagicMock()

from compound_investment_controller.resources.lambda_function import Investment


class TestInvestment:

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
