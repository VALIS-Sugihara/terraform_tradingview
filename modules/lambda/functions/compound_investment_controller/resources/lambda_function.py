import os
import oandapyV20
from oandapyV20.endpoints import (
    orders,
    positions,
    accounts,
    pricing,
    transactions,
)
from oandapyV20.endpoints.transactions import TransactionIDRange
from typing import NamedTuple, Dict, List, Tuple
from datetime import datetime, timedelta, date, UTC, timezone
from zoneinfo import ZoneInfo
import logging
import traceback
import re


JST = ZoneInfo("Asia/Tokyo")

# OANDAのAPI設定
OANDA_ACCOUNT_ID = os.environ["OANDA_ACCOUNT_ID"]
OANDA_API_KEY = os.environ["OANDA_RESTAPI_TOKEN"]
OANDA_API_URL = os.environ["OANDA_API_URL"]

LEVERAGE = float(os.environ["LEVERAGE"])  # カスタム設定レバレッジ

try:
    ACCOUNT_MODE = os.environ["ACCOUNT_MODE"]
except Exception:
    raise Exception("ACCOUNT_MODE が設定されていません")


logger = logging.getLogger(__name__)
# ロガーのログレベルを設定する
logger.setLevel(logging.INFO)

# フォーマットの設定  [INFO] 2024-10-04 01:51:05,787 : <PERS> : test
formatter = logging.Formatter(
    f"[%(levelname)s] %(asctime)s : <{ACCOUNT_MODE}> : %(message)s"
)

# ハンドラーの設定
handler = logging.StreamHandler()  # Lambda の標準出力にログを出力
handler.setFormatter(formatter)  # ハンドラーにフォーマッターを適用

# ロガーにハンドラーを追加
logger.handlers = [handler]  # 既存のハンドラーを上書きするため、リストで設定


class OANDA:
    """OANDA API を実行するためのクラス

    Raises:
        Exception: 全ての例外
    """

    account_id: str  # OANDA_ACCOUNT_ID
    api_key: str  # OANDA_API_KEY
    api_url: str  # OANDA_API_URL
    account_mode: str  # ACCOUNT_MODE
    client: oandapyV20.API  # API クライアント
    leverages: dict  # OANDA の規定レバレッジ

    def __init__(
        self, account_id: str, api_key: str, api_url: str, account_mode: str
    ) -> None:
        self.account_id = account_id
        self.api_key = api_key
        self.api_url = api_url
        self.account_mode = account_mode
        self.client = self._create_client()
        self.leverages = self._define_leverage()
        self.trade = self.Trade(self)  # trade_manager
        self.price = self.Price(self)  # price_manager
        self.account = self.Account(self)  # account_manager

    def _create_client(self):
        # Create and return an oandapyV20 API client instance using api_key and api_url
        environment = "practice" if ACCOUNT_MODE == "DEMO" else "live"
        return oandapyV20.API(access_token=self.api_key, environment=environment)

    def _define_leverage(self):
        leverages = {}
        if self.account_mode == "PERS":  # 個人口座の場合のレバレッジ
            leverages["USD_JPY"] = 0.04
            leverages["USD_MXN"] = 0.08
            leverages["TRY_JPY"] = 0.25
        elif self.account_mode == "CORP":  # 法人口座の場合のレバレッジ
            leverages["USD_JPY"] = 0.022
            leverages["USD_MXN"] = 0.05
            leverages["TRY_JPY"] = 0.25
        elif self.account_mode == "DEMO":  # デモ口座の場合のレバレッジ
            leverages["USD_JPY"] = 0.022
            leverages["USD_MXN"] = 0.05
            leverages["TRY_JPY"] = 0.25

        return leverages

    class Trade:
        """OANDA でのトレードをまとめたクラス

        Raises:
            Exception: 全ての例外
        """

        def __init__(self, oanda) -> None:
            self.oanda = oanda

        def request_place_order(self, order_data: dict):
            """マーケットオーダーを送信する関数

            Args:
                order_data (dict): self._make_order_data()
            Returns:
                _type_: _description_
            """
            r = orders.OrderCreate(self.oanda.account_id, data=order_data)
            response = self.oanda.client.request(r)
            return response

        def _make_order_data(
            self,
            units: int,
            instrument: str = "USD_JPY",
            stop_loss_pips=0,
            take_profit_pips=0,
        ):
            """place_order に request するデータを生成し返す

            Args:
                units (int): 注文数量.
                instrument (str, optional): 注文通貨ペア. Defaults to "USD_JPY".
                stop_loss_pips (int, optional): ストップロスの pips 数. Defaults to 0.
                take_profit_pips (int, optional): 利確の pips 数. Defaults to 0.

            Returns:
                dict: place_order データに沿った以下の形式
                {
                    "order": {
                        "units": str(units),  # 正の値は買い、負の値は売り
                        "instrument": instrument,
                        "timeInForce": "FOK",
                        "type": "MARKET",
                        "positionFill": "DEFAULT",
                }
            """
            order_data = {
                "order": {
                    "units": str(units),  # 正の値は買い、負の値は売り
                    "instrument": instrument,
                    "timeInForce": "FOK",
                    "type": "MARKET",
                    "positionFill": "DEFAULT",
                    # "stopLossOnFill": {"price": f"{stop_loss_price:.5f}"},
                    # "takeProfitOnFill": {"price": f"{take_profit_price:.5f}"},
                }
            }
            return order_data

        def request_close_all_positions(
            self,
            all_positions_data: dict,
            instrument="USD_JPY",
        ):
            """全 Long|Short ポジションの決済を送信する関数

            Args:
                all_position_data (dict): self._make_all_position_data()
                instrument (str): 決済する通貨ペア. Defaults to "USD_JPY".

            Raises:
                Exception: Error: {instrument}:{close_action} position is NOT closing

            Returns:
                _type_: _description_
            """
            try:
                request = positions.PositionClose(
                    accountID=self.oanda.account_id,
                    instrument=instrument,
                    data=all_positions_data,
                )
                response = self.oanda.client.request(request)

                # logger.info(
                #     "position close: {} at {}. pl: {}".format(
                #         response.get(f"{close_action}OrderFillTransaction").get(
                #             "units"
                #         ),
                #         response.get(f"{close_action}OrderFillTransaction").get(
                #             "price"
                #         ),
                #         response.get(f"{close_action}OrderFillTransaction").get("pl"),
                #     )
                # )

                return response

            except Exception as e:
                logger.error(str(e))
                raise Exception(
                    f"Error: {instrument}:{all_positions_data.keys[0]} position is NOT closing"
                )

        def _make_all_positions_data(self, close_action: str):
            """positions.PositionClose に request するデータを生成し返す

            Args:
                close_action (str): 決済するポジション. long | short

            Raises:
                Exception: Error: close action {close_action} is wrong

            Returns:
                dict: close_all_positions データに沿った以下の形式
                {"longUnits | shortUnits": "ALL"}
            """
            if close_action not in ["long", "short"]:
                raise Exception(f"Error: close action '{close_action}' is wrong")
            # Long ポジション or Short ポジションの決済指定
            all_positions_data = (
                {"longUnits": "ALL"}
                if close_action == "long"
                else {"shortUnits": "ALL"}
            )
            return all_positions_data

        # ポジション決済を送信する関数
        def request_position_close(
            self,
            close_action: str,
            units,
            instrument="USD_JPY",
            stop_loss_pips=10,
            take_profit_pips=20,
        ):
            """ポジション決済を送信する関数

            Args:
                close_action (_type_): 決済するポジション. long | short
                units (_type_): 決済数量
                instrument (str, optional): 決済する通貨ぺあ. Defaults to "USD_JPY".
                stop_loss_pips (int, optional): _description_. Defaults to 10.
                take_profit_pips (int, optional): _description_. Defaults to 20.

            Raises:
                Exception: _description_

            Returns:
                _type_: _description_
            """
            try:
                # Long ポジションの決済
                if close_action == "long":
                    data = {"longUnits": "ALL"}
                    request = positions.PositionClose(
                        accountID=self.oanda.account_id,
                        instrument=instrument,
                        data=data,
                    )
                    response = self.oanda.client.request(request)

                    logger.info(
                        "position close: {} at {}. pl: {}".format(
                            response.get("longOrderFillTransaction").get("units"),
                            response.get("longOrderFillTransaction").get("price"),
                            response.get("longOrderFillTransaction").get("pl"),
                        )
                    )

                    return response

                # Short ポジションの決済
                elif close_action == "short":
                    data = {"shortUnits": "ALL"}
                    request = positions.PositionClose(
                        accountID=OANDA_ACCOUNT_ID,
                        instrument=instrument,
                        data=data,
                    )
                    response = self.oanda.client.request(request)

                    logger.info(
                        "position close: {} at {}. pl: {}".format(
                            response.get("shortOrderFillTransaction").get("units"),
                            response.get("shortOrderFillTransaction").get("price"),
                            response.get("shortOrderFillTransaction").get("pl"),
                        )
                    )

                    return response

                else:
                    raise Exception("ポジションを決済できませんでした")

            except Exception as e:
                logger.error(str(e))
                return {"statusCode": 500, "body": "Error Position Closing"}

    class Price:
        """OANDA での価格に関する情報を扱うクラス"""

        class Prices(NamedTuple):
            bid: float  # 売値
            ask: float  # 買値
            mid: float  # 中値

        PriceMap = Dict[str, Prices]
        price_map: PriceMap
        main_currency_pairs = ("USD_JPY", "USD_MXN", "TRY_JPY")
        main_currencies = (
            "USD",
            "JPY",
            "MXN",
        )

        def __init__(self, oanda):
            self.oanda = oanda
            self._generate_price_map()

        def _generate_price_map(self):
            self.price_map = {}
            logger.info("price_map を生成します")
            for currency_pair in self.main_currency_pairs:
                prices = self.request_price(instruments=currency_pair)
                self.price_map[currency_pair] = prices
            logger.info(f"{self.price_map=}")

        def request_price(self, instruments: str):
            """価格取得関数
                中値を計算し返す > bid, ask, mid を返す
            Args:
                instruments (str): 取得したい通過ペア. ex) USD_JPY
            Returns:
                tuple: bid, ask, middle_price
            """
            # 価格情報を取得するエンドポイントの設定
            params = {"instruments": instruments}
            pricing_info = pricing.PricingInfo(
                accountID=self.oanda.account_id, params=params
            )

            # リクエストを送信して現在価格を取得
            try:
                response = self.oanda.client.request(pricing_info)
                prices = response["prices"][0]
                bid = float(prices["bids"][0]["price"])
                ask = float(prices["asks"][0]["price"])
                mid = (float(bid) + float(ask)) / 2  # 中値
                return self.Prices(bid, ask, mid)
            except Exception as e:
                logger.error(f"Error: {e}")
                raise Exception("価格を取得できませんでした")

        def get_price_from_pricemap(self, instruments, bid_ask_mid="mid"):
            target_price = self.price_map.get(instruments, False)
            if target_price is False:
                # ない時は逆数を返す
                l, r = instruments.split("_")[0], instruments.split("_")[1]
                target_price = self.price_map[f"{r}_{l}"]
                if bid_ask_mid == "bid":
                    return 1 / target_price.ask
                if bid_ask_mid == "ask":
                    return 1 / target_price.bid
                if bid_ask_mid == "mid":
                    return 1 / target_price.mid
            else:
                if bid_ask_mid == "bid":
                    return target_price.bid
                if bid_ask_mid == "ask":
                    return target_price.ask
                if bid_ask_mid == "mid":
                    return target_price.mid

    class Account:
        """OANDA での口座情報をまとめたクラス"""

        account_summary: dict  # 口座情報を取得しておく

        def __init__(self, oanda) -> None:
            self.oanda = oanda
            self.account_summary = self._request_account_summary()

        def _request_account_summary(self):
            """口座情報を取得する関数

            Returns:
                account_summary (dict): 口座情報
                {
                    'guaranteedStopLossOrderMode': 'DISABLED',
                    'hedgingEnabled': True,
                    'id': '101-009-30020937-001',
                    'createdTime': '2024-10-01T00:57:23.803531367Z',
                    'currency': 'JPY',
                    'createdByUserID': 30020937,
                    'alias': 'fxTradeDEMO',
                    'marginRate': '0.02',
                    'lastTransactionID': '5',
                    'balance': '3000000.0000',
                    'openTradeCount': 1,
                    'openPositionCount': 1,
                    'pendingOrderCount': 0,
                    'pl': '0.0000',
                    'resettablePL': '0.0000',
                    'resettablePLTime': '0',
                    'financing': '0.0000',
                    'commission': '0.0000',
                    'dividendAdjustment': '0',
                    'guaranteedExecutionFees': '0.0000',
                    'unrealizedPL': '6400.0000',
                    'NAV': '3006400.0000',
                    'marginUsed': '577296.0000',
                    'marginAvailable': '2429304.0000',
                    'positionValue': '14432400.0000',
                    'marginCloseoutUnrealizedPL': '6600.0000',
                    'marginCloseoutNAV': '3006600.0000',
                    'marginCloseoutMarginUsed': '577296.0000',
                    'marginCloseoutPositionValue': '14432400.0000',
                    'marginCloseoutPercent': '0.19201',
                    'withdrawalLimit': '2429304.0000'
                }
            """
            endpoint = accounts.AccountSummary(self.oanda.account_id)
            response = self.oanda.client.request(endpoint)
            """ response
            {
                'account': {
                    'guaranteedStopLossOrderMode': 'DISABLED',
                    'hedgingEnabled': True,
                    'id': '101-009-30020937-001',
                    'createdTime': '2024-10-01T00:57:23.803531367Z',
                    'currency': 'JPY',
                    'createdByUserID': 30020937,
                    'alias': 'fxTradeDEMO',
                    'marginRate': '0.02',
                    'lastTransactionID': '3',
                    'balance': '3000000.0000',
                    'openTradeCount': 0,
                    'openPositionCount': 0,
                    'pendingOrderCount': 0,
                    'pl': '0.0000',
                    'resettablePL': '0.0000',
                    'resettablePLTime': '0',
                    'financing': '0.0000',
                    'commission': '0.0000',
                    'dividendAdjustment': '0',
                    'guaranteedExecutionFees': '0.0000',
                    'unrealizedPL': '0.0000',
                    'NAV': '3000000.0000',
                    'marginUsed': '0.0000',
                    'marginAvailable': '3000000.0000',
                    'positionValue': '0.0000',
                    'marginCloseoutUnrealizedPL': '0.0000',
                    'marginCloseoutNAV': '3000000.0000',
                    'marginCloseoutMarginUsed': '0.0000',
                    'marginCloseoutPositionValue': '0.0000',
                    'marginCloseoutPercent': '0.00000',
                    'withdrawalLimit': '3000000.0000'
                },
                'lastTransactionID': '3'
            }
            """
            return response["account"]

        def get_margin_available(self):
            """利用可能証拠金を取得する関数

            Returns:
                margin_available (float): 証拠金残高
            """
            margin_available = float(self.account_summary["marginAvailable"])
            return margin_available

        def get_margin_used(self):
            """維持証拠金を取得する関数

            Returns:
                margin_used (float): marginUsed
            """
            margin_used = float(self.account_summary["marginUsed"])
            return margin_used

        def get_net_asset_value(self):
            """有効残高を取得する関数

            Returns:
                nav (float): 有効残高（含み益や含み損を含む）
            """
            nav = float(self.account_summary["NAV"])
            return nav

        def request_transaction_list_between_dates(
            self,
            from_date: str,
            to_date: str,
            transaction_type: str = "DAILY_FINANCING",
        ):
            """トランザクションリストを日付間指定で取得する関数

            Args:
                from_date (str): from の日付. 2024-10-02 の形式
                to_date (str): to の日付. 2024-10-03 の形式
                transaction_type (str): DAILY_FINANCING etc...

            Returns:
                (dict): 以下の形式のトランザクションデータ
                response={
                    'from': '2024-10-01T04:00:00.000000000Z',
                    'to': '2024-10-03T04:00:00.000000000Z',
                    'pageSize': 100,
                    'type': ['DAILY_FINANCING'],
                    'count': 2,
                    'pages': ['https://api-fxpractice.oanda.com/v3/accounts/101-009-30020937-001/transactions/idrange?from=114&to=121&type=DAILY_FINANCING'],
                    'lastTransactionID': '121'
                }
            """
            # Get the transactions
            params = {
                "from": from_date,
                "to": to_date,
                "type": transaction_type,  # Filter for DAILY_INTEREST transaction types
                "pageSize": 100,  # Adjust page size as needed
            }
            request = transactions.TransactionList(
                accountID=self.oanda.account_id, params=params
            )
            response = self.oanda.client.request(request)
            return response

        def get_transaction_id_by_list(self, list_data: dict, key: str):
            """トランザクションリストの返り値から目的の id を抽出する
                'pages': ['https://api-fxpractice.oanda.com/v3/accounts/101-009-30020937-001/transactions/idrange?from=114&to=121&type=DAILY_FINANCING'],
            のようになっており、from や to の =114 から 114 を正規表現で抜き出して返す
            TODO: pages のデータが存在しており 1つであることを前提としているためエラーハンドリングについて考慮

            Args:
                list_data (dict): self.request_transaction_list_between_dates()
                key (str): 目的のキー ex) "from", "to" etc...

            Returns:
                str: 目的の id
            """
            page = list_data["pages"][0]
            ptn = re.compile(rf"{key}=(\d+)")
            target_id = re.findall(ptn, page)[0]
            return target_id

        def request_transaction_details_by_id(self, id: int):
            """トランザクション詳細を id から取得する関数

            Args:
                id (int): transactionID

            Returns:
                (dict): 以下の形式のトランザクション詳細データ
                response = {
                    "transaction": {
                        "id": "121",
                        "accountID": "101-009-30020937-001",
                        "userID": 30020937,
                        "batchID": "121",
                        "time": "2024-10-02T21:00:00.000000000Z",
                        "type": "DAILY_FINANCING",
                        "financing": "308.7064",
                        "accountBalance": "3000583.9766",
                        "positionFinancings": [
                            {
                                "instrument": "USD_JPY",
                                "financing": "-296.9144",
                                "baseFinancing": "-2.02303561643840",
                                "accountFinancingMode": "DAILY_INSTRUMENT",
                                "homeConversionFactors": {
                                    "gainQuoteHome": None,
                                    "lossQuoteHome": None,
                                    "gainBaseHome": {"factor": "146.181052"},
                                    "lossBaseHome": {"factor": "146.766948"},
                                },
                                "openTradeFinancings": [
                                    {
                                        "tradeID": "5",
                                        "financing": "-221.1557",
                                        "baseFinancing": "-1.50684931506849",
                                        "financingRate": "-0.0055",
                                        "baseHomeConversionCost": "-0.42183945205479",
                                        "homeConversionCost": "-0.42183945205479",
                                    },
                                ],
                            },
                        ],
                        "baseHomeConversionCost": "-1.42472923877042",
                        "homeConversionCost": "-1.42472923877042",
                    },
                    "lastTransactionID": "121",
                }
            """
            request = transactions.TransactionDetails(
                accountID=self.oanda.account_id, transactionID=id
            )
            response = self.oanda.client.request(request)
            return response

        def request_transaction_id_range(
            self,
            from_id: str,
            to_id: str,
            transaction_type: str = "DAILY_FINANCING",
        ):
            """トランザクションリストを日付間指定で取得する関数

            Args:
                from_id (str): from の id. str でも int でも良さそう
                to_id (str): to の id. str でも int でも良さそう
                transaction_type (str): DAILY_FINANCING etc...

            Returns:
                (dict): 以下の形式のトランザクションデータ
                response={
                    'transactions': [
                        self.request_transaction_details_by_id(),
                        self.request_transaction_details_by_id(),
                        ...
                    ]
                }
            """

            # Get the transactions
            params = {
                "from": from_id,
                "to": to_id,
                "type": transaction_type,  # Filter for DAILY_INTEREST transaction types
                "pageSize": 100,  # Adjust page size as needed
            }
            request = transactions.TransactionIDRange(
                accountID=self.oanda.account_id, params=params
            )
            response = self.oanda.client.request(request)
            return response

        def get_financing_by_transaction_details(self, details_data: dict):
            """トランザクション詳細データから swap である financing の値を float にして返す

            Args:
                details_data (dict): self.request_transaction_details_by_id()

            Returns:
                (float): swap 額
            """
            financing = details_data["financing"]
            return float(financing)

        def get_swap_points(self):
            # オープンポジションの情報を取得
            r = positions.OpenPositions(accountID=self.oanda.account_id)
            response = self.oanda.client.request(r)
            logger.info(f"{response=}")

            # レスポンスからスワップポイントを抽出
            open_positions = r.response.get("positions", [])
            for position in open_positions:
                instrument = position["instrument"]
                long_swap = position["long"]["financing"]
                short_swap = position["short"]["financing"]
                logger.info(
                    f"Instrument: {instrument}, Long Swap: {long_swap}, Short Swap: {short_swap}"
                )
                """
                Instrument: USD_MXN, Long Swap: 0.0000, Short Swap: 409.4515
                Instrument: USD_JPY, Long Swap: 434.2470, Short Swap: 0.0000
                """

        def get_transactions_last_month(self):
            # 先月の開始日と終了日を計算
            now = datetime.now()
            last_month_end = now.replace(day=1) - timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)

            # 先月の取引を取得
            # params = {
            #     "from": last_month_start.isoformat() + "Z",
            #     "to": last_month_end.isoformat() + "Z",
            # }
            # 先月の開始日と終了日を 'YYYY-MM-DD' 形式に変換
            last_month_start_str = last_month_start.strftime("%Y-%m-%d")
            last_month_end_str = last_month_end.strftime("%Y-%m-%d")

            # 取引履歴を取得
            params = {
                "type": "ORDER_FILL",
                "from": last_month_start_str,
                "to": last_month_end_str,
            }

            r = transactions.TransactionList(
                accountID=self.oanda.account_id, params=params
            )
            response = self.oanda.client.request(r)
            logger.info(params)
            logger.info(f"{response=}")
            exit()
            # transactions = TransactionIDRange(accountID=self.oanda.account_id, params=params)
            # response = self.oanda.client.request(transactions)

            # ポジションに関連する取引を抽出
            for transaction in response["transactions"]:
                if transaction["type"] in [
                    "ORDER_FILL",
                    "TRADE_OPEN",
                    "TRADE_CLOSE",
                ]:
                    logger.info(transaction)


class Investment:
    """投資の際の共通ロジックを集約するクラス。

    Raises:
        Exception: 全ての例外
    """

    platform: any  # OANDA などの Platform クラス
    leverage: float  # 独自で設定したレバレッジ

    def __init__(self, platform: any, leverage: float):
        self.platform = platform
        self.leverage = leverage

    def calcurate_usdjpy_amount(self, jpy_amount: int, price_map: dict):
        """USD_JPY の購入枚数を計算する関数

        Args:
            jpy_amount (int): 円単位での通貨量
            price_map (dict): プライスマップ OANDA.Price.PriceMap
        """
        value = jpy_amount * self.leverage
        usd_amount = round(value / price_map["USD_JPY"].ask)

        return usd_amount

    def calcurate_tryjpy_amount(self, jpy_amount: int):
        """TRY_JPY の購入枚数を計算する関数

        Args:
            jpy_amount (int): 円単位での通貨量
        """
        # TRY_JPY についてはレバレッジで割った枚数とする
        try_amount = round(jpy_amount / self.leverage)

        return try_amount

    def calculate_required_margin(self, instrument: str, amount: int, price_map: dict):
        """必要証拠金を計算する関数

        Args:
            amount (int): 外貨での通貨量
            instrument (str): 通貨ペア USD_JPY etc...
            price_map (dict): プライスマップ OANDA.Price.PriceMap
        """
        # ベースとなる通貨を抜き出す ex) USD_MXN の場合 USD レートを参照するため
        base_instrument = instrument.split("_")[0]
        # レートより円換算する
        jpy_amount = price_map[f"{base_instrument}_JPY"].ask * amount
        # 規定レバレッジより必要証拠金を計算
        required_margin = jpy_amount * self.platform.leverages[instrument]

        return required_margin

    def verify_purchase_requirements(
        self, currency_pair_amounts: dict, price_map: dict
    ):
        """購入条件を満たしているかを確認する

        Args:
            currency_pairs (list): 通貨ペアと数量のリスト ex){"USD_JPY": 1000, "USD_MXN": 1000, "TRY_JPY": 3000}
            price_map (dict): プライスマップ OANDA.Price.PriceMap
        """
        flag = True
        # アカウントの有効証拠金残高の確認
        margin_available = self.platform.account.get_margin_available()
        # それぞれの必要証拠金の合計額を計算する
        required_margin = 0
        for instrument, amount in currency_pair_amounts.items():
            required_margin += self.calculate_required_margin(
                instrument=instrument, amount=amount, price_map=price_map
            )
        # 必要証拠金が購入金額以下の場合は False
        if margin_available < required_margin:
            flag = False
            return flag

        # 有効残高 / 維持証拠金 が 110% 以下の場合は False
        margin_used = self.platform.account.get_margin_used()
        nav = self.platform.account.get_net_asset_value()
        if (
            margin_used != 0 and (nav / margin_used) * 100 < 110
        ):  # 初期状態では維持証拠金 0円のため回避
            flag = False
            return flag

        return flag

    @classmethod
    def count_weekdays_in_month(cls, target_date: date = None):
        # 日付が指定されていない場合現在の日付を取得
        today = date.today() if target_date is None else target_date

        # 当月の初日と最終日を取得
        first_day_of_month = today.replace(day=1)
        last_day_of_month = first_day_of_month.replace(
            month=today.month + 1, day=1
        ) - timedelta(days=1)

        # 平日をカウントする変数
        weekday_count = 0

        # 当月の各日をループして平日をカウント
        for day in range(first_day_of_month.day, last_day_of_month.day + 1):
            current_day = today.replace(day=day)
            if current_day.weekday() < 5:  # 0=月曜日, 1=火曜日, ..., 4=金曜日
                weekday_count += 1

        return weekday_count

    @classmethod
    def convert_jpy_to_usd(cls, price_map: dict):
        """JPY の通貨量を USD 単位へ変換する関数

        Args:
            price_map (dict): プライスマップ

        Raises:
            Exception: 全ての例外

        Returns:
            usd_amount (int): USD の通貨量
        """
        usd_rate = price_map["USD_JPY"].mid / price_map["USD_MXN"].mid
        usd_amount = int(cls.daily_amount / usd_rate)
        return usd_amount


class CompoundInvestment(Investment):
    """複利投資を実行するためのクラス

    Args:
        Investment (class): 投資共通クラス
    """

    platform: any  # OANDA などの Platform クラス
    leverage: float  # 独自で設定したレバレッジ

    def __init__(self, platform: any, leverage: float) -> None:
        super().__init__(platform=platform, leverage=leverage)

    def execute_purchase(self, daily_amount: int):
        # プライスマップの取得
        price_map = self.platform.price.price_map
        # USD_JPY の購入枚数の計算
        usd_amount = self.calcurate_usdjpy_amount(daily_amount, price_map)
        # USD_MXN の購入枚数の計算（USD 単位なので同量を購入
        mxn_amount = usd_amount
        # TRY_JPY の購入枚数の計算
        try_amount = self.calcurate_tryjpy_amount(daily_amount)
        # 与信確認
        currency_pair_amounts = {
            "USD_JPY": usd_amount,
            "USD_MXN": mxn_amount,
            "TRY_JPY": try_amount,
        }
        if self.verify_purchase_requirements(currency_pair_amounts, price_map):
            # USD_JPY の Long
            # TODO: stoploss の設定
            usd_order_data = self.platform.trade._make_order_data(
                units=usd_amount, instrument="USD_JPY"
            )
            self.platform.trade.request_place_order(usd_order_data)
            logger.info(f"USD_JPY を {usd_amount} 枚発注しました")
            # USD_MXN の Short
            # TODO: stoploss の設定
            mxn_amount = -1 * mxn_amount  # Short のため - 数量にする
            mxn_order_data = self.platform.trade._make_order_data(
                units=mxn_amount, instrument="USD_MXN"
            )
            self.platform.trade.request_place_order(mxn_order_data)
            logger.info(f"USD_MXN を {mxn_amount} 枚発注しました")
            # TRY_JPY の Long
            # TODO: stoploss の設定
            try_order_data = self.platform.trade._make_order_data(
                units=try_amount, instrument="TRY_JPY"
            )
            self.platform.trade.request_place_order(try_order_data)
            logger.info(f"TRY_JPY を {try_amount} 枚発注しました")

    def get_daily_swap_points(self):
        """最新の swappoint を取得するための関数"""
        # 対象日付を取得する
        from_date, to_date = CompoundInvestment.make_between_dates_based_on_day()
        # トランザクション一覧を取得する
        list_data = self.platform.account.request_transaction_list_between_dates(
            from_date=from_date, to_date=to_date, transaction_type="DAILY_FINANCING"
        )
        # 一覧から from id を求める
        from_id = self.platform.account.get_transaction_id_by_list(list_data, "from")
        # 一覧から to id を求める
        to_id = self.platform.account.get_transaction_id_by_list(list_data, "to")
        # トランザクション詳細を from-to の id から取得する
        transaction_details = self.platform.account.request_transaction_id_range(
            from_id=from_id, to_id=to_id, transaction_type="DAILY_FINANCING"
        )
        # それぞれの financing の値を合計して返す
        financing = 0
        for transaction_detail in transaction_details["transactions"]:
            financing += self.platform.account.get_financing_by_transaction_details(
                transaction_detail
            )

        return financing

    @classmethod
    def make_between_dates_based_on_day(cls, target_datetime: datetime = None):
        """月曜日であれば
                from: 3日前（土曜日）の yyyy-mm-dd と to: 当日の yyyy-mm-dd を
            それ以外であれば、
                from: 1日前の yyyy-mm-dd と 当日の yyyy-mm-dd を返す
        注）OANDA が一部土曜日の 6:00 に swap が入るため月曜日にまとめて処理するため、
            また、JST 10/3 6:00 の swap を取得するためには、from-to が 10/02-10/03 で指定する必要があるため

        Returns:
            (tuple): (from: str, to: str) 対象日の yyyy-mm-dd の組み合わせ
        """
        # UTC ベースで算出（月曜 09:30 JST 実行時には UTC でも月曜日になっているため月曜日を判定する）
        today = datetime.now(UTC) if target_datetime is None else target_datetime
        if today.weekday() == 0:  # 0 is Monday
            from_date = today - timedelta(days=3)
        else:
            from_date = today - timedelta(days=1)
        to_date = today
        return from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d")


# 購入 units 数を計算する関数
def calculate_units(entry_price, margin, risk_percentage=0.02, stop_loss_pips=50):
    """
    entry_price: エントリー価格 (例えば、USD/JPY の 価格)
    margin: 証拠金の額
    risk_percentage: リスクとして設定する証拠金の割合 (デフォルトは 2%)
    stop_loss_pips: 設定するストップロスまでの pips (デフォルトは 50 pips)

    # 例: USD/JPY = 150.00 でエントリー、証拠金が 500,000 円、ストップロスを 50 pips に設定する場合
    entry_price = 150.00
    margin = 500000  # 証拠金
    stop_loss_pips = 50  # ストップロスまでの pips

    units = calculate_units(entry_price, margin, stop_loss_pips=stop_loss_pips)
    logger.info(f"購入するユニット数: {int(units)}")
    """
    risk_amount = margin * risk_percentage  # 証拠金の 2% の金額
    pip_value = (
        0.01 / entry_price if entry_price > 1 else 0.0001 / entry_price
    )  # 1 pip の価値

    # ユニット数を計算
    units = int(risk_amount / (stop_loss_pips * pip_value))

    return units


# Lambdaハンドラー関数
def lambda_handler(event, context):
    """スワップ分を再投資し複利運用を行う"""
    try:
        logger.info("Starting execute_compound_investment ...")
        execute_compound_investment()
        logger.info("Success placing orders")
        return {"statusCode": 200, "body": "Success placing orders"}
    except Exception as e:
        logger.error(str(e))
        logger.error(traceback.format_exc())
        logger.error("Error placing orders")
        return {"statusCode": 500, "body": "Error placing orders"}


def execute_compound_investment():
    # CompoundInvestment クラスの実体化
    oanda = OANDA(
        account_id=OANDA_ACCOUNT_ID,
        api_key=OANDA_API_KEY,
        api_url=OANDA_API_URL,
        account_mode=ACCOUNT_MODE,
    )
    compound_investment = CompoundInvestment(platform=oanda, leverage=LEVERAGE)
    # 当日スワップポイントの取得
    swap_points = compound_investment.get_daily_swap_points()
    logger.info(f"スワップポイント: {swap_points} 円 分の買付けを行います")
    if swap_points == 0:
        logger.error("買付け計算金額が 0円です")
        return
    # 買付け実施
    compound_investment.execute_purchase(swap_points)


# ローカルテスト
if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    # ロガーのログレベルを設定する
    logger.setLevel(logging.INFO)
    logger.error("test")
    exit()

    lambda_handler(None, None)
