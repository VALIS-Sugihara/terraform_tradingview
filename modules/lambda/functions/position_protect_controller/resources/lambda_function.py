import os
import oandapyV20
from oandapyV20.endpoints import (
    orders,
    positions,
    accounts,
    pricing,
    transactions,
    trades,
)
from typing import NamedTuple, Dict, List, Tuple
from datetime import datetime, timedelta, date, UTC, timezone, time
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
PROTECTION_THRESHOLD = 105  # ポジション整理の基準となる閾値

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

        def request_trade_list(self):
            """トレード一覧を送信する関数

            Args:
                order_data (dict): self._make_place_order_data()
            Returns:
                (dict): トレード一覧 ※おそらく state: CLOSE 分も含む
                {
                    "trades": [
                        {
                            "id": "210",
                            "instrument": "TRY_JPY",
                            "price": "4.352",
                            "openTime": "2024-10-08T00:30:24.527704550Z",
                            "initialUnits": "18",
                            "initialMarginRequired": "7.7616",
                            "state": "OPEN",
                            "currentUnits": "18",
                            "realizedPL": "0.0000",
                            "financing": "0.0000",
                            "dividendAdjustment": "0.0000",
                            "unrealizedPL": "-1.4760",
                            "marginUsed": "7.7580",
                        },
                        ...
                    ],
                    'lastTransactionID': '210'
                }
            """
            r = trades.TradesList(accountID=self.oanda.account_id)
            response = self.oanda.client.request(r)
            return response

        def request_open_trades(self):
            """オープントレード一覧を送信する関数

            Returns:
                (dict): オープントレード一覧
                {
                    "trades": [
                        {
                            "id": "210",
                            "instrument": "TRY_JPY",
                            "price": "4.352",
                            "openTime": "2024-10-08T00:30:24.527704550Z",
                            "initialUnits": "18",
                            "initialMarginRequired": "7.7616",
                            "state": "OPEN",
                            "currentUnits": "18",
                            "realizedPL": "0.0000",
                            "financing": "0.0000",
                            "dividendAdjustment": "0.0000",
                            "unrealizedPL": "-1.4760",
                            "marginUsed": "7.7580",
                        },
                        ...
                    ],
                    'lastTransactionID': '210'
                }
            """
            r = trades.OpenTrades(accountID=self.oanda.account_id)
            response = self.oanda.client.request(r)
            return response

        def request_place_order(self, order_data: dict):
            """マーケットオーダーを送信する関数

            Args:
                order_data (dict): self._make_place_order_data()
            Returns:
                _type_: _description_
            """
            r = orders.OrderCreate(self.oanda.account_id, data=order_data)
            response = self.oanda.client.request(r)
            return response

        def _make_place_order_data(
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
                (dict): place_order データに沿った以下の形式
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

        def request_close_order(self, trade_id: str, close_data: dict):
            """チケットのクローズオーダーを送信する関数

            Args:
                close_data (dict): self._make_close_data()
            Returns:
                (dict): クローズオーダー情報
                {
                    "orderCreateTransaction": {
                        "id": "213",
                        "accountID": "101-009-30020937-001",
                        "userID": 30020937,
                        "batchID": "213",
                        "requestID": "61292424904719777",
                        "time": "2024-10-08T01:29:27.901550405Z",
                        "type": "MARKET_ORDER",
                        "instrument": "TRY_JPY",
                        "units": "-2",
                        "timeInForce": "FOK",
                        "positionFill": "REDUCE_ONLY",
                        "reason": "TRADE_CLOSE",
                        "tradeClose": {"units": "2", "tradeID": "210"},
                    },
                    "orderFillTransaction": {
                        "id": "214",
                        "accountID": "101-009-30020937-001",
                        "userID": 30020937,
                        "batchID": "213",
                        "requestID": "61292424904719777",
                        "time": "2024-10-08T01:29:27.901550405Z",
                        "type": "ORDER_FILL",
                        "orderID": "213",
                        "instrument": "TRY_JPY",
                        "units": "-2",
                        "requestedUnits": "-2",
                        "price": "4.272",
                        "pl": "-0.1600",
                        "quotePL": "-0.160",
                        "financing": "0.0000",
                        "baseFinancing": "0.00000000000000",
                        "commission": "0.0000",
                        "accountBalance": "3379876.1987",
                        "gainQuoteHomeConversionFactor": "1",
                        "lossQuoteHomeConversionFactor": "1",
                        "guaranteedExecutionFee": "0.0000",
                        "quoteGuaranteedExecutionFee": "0",
                        "halfSpreadCost": "0.0800",
                        "fullVWAP": "4.272",
                        "reason": "MARKET_ORDER_TRADE_CLOSE",
                        "tradeReduced": {
                            "tradeID": "210",
                            "units": "-2",
                            "realizedPL": "-0.1600",
                            "financing": "0.0000",
                            "baseFinancing": "0.00000000000000",
                            "price": "4.272",
                            "guaranteedExecutionFee": "0.0000",
                            "quoteGuaranteedExecutionFee": "0",
                            "halfSpreadCost": "0.0800",
                        },
                        "fullPrice": {
                            "closeoutBid": "4.272",
                            "closeoutAsk": "4.352",
                            "timestamp": "2024-10-08T01:29:05.488584473Z",
                            "bids": [{"price": "4.272", "liquidity": "250000.0"}],
                            "asks": [{"price": "4.352", "liquidity": "250000.0"}],
                        },
                        "homeConversionFactors": {
                            "gainQuoteHome": {"factor": "1"},
                            "lossQuoteHome": {"factor": "1"},
                            "gainBaseHome": {"factor": "4.303376"},
                            "lossBaseHome": {"factor": "4.320624"},
                        },
                    },
                    "relatedTransactionIDs": ["213", "214"],
                    "lastTransactionID": "214",
                }
            """
            r = trades.TradeClose(
                accountID=self.oanda.account_id, tradeID=trade_id, data=close_data
            )
            response = self.oanda.client.request(r)
            return response

        def _make_close_order_data(self, units: str = "ALL"):
            """close_order に request するデータを生成し返す

            Args:
                units (str): ALL or 決済数量.

            Returns:
                (dict): close_order データに沿った以下の形式
                {
                    "units": "ALL" or 数量
                }
            """
            close_order_data = {"units": units}
            return close_order_data

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

        def __init__(self, oanda):
            self.oanda = oanda
            self._generate_price_map()

        def _generate_price_map(self):
            self.price_map = {}
            for currency_pair in self.main_currency_pairs:
                prices = self.request_price(instruments=currency_pair)
                self.price_map[currency_pair] = prices

        def request_price(self, instruments: str):
            """価格取得関数
                bid, ask, mid(計算したもの) を返す
            Args:
                instruments (str): 取得したい通過ペア. ex) USD_JPY
            Returns:
                (self.Prices): self.Prices(bid, ask, mid)
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

        def update_account_summary(self):
            """決済後にアカウント情報を更新し再セットするための関数"""
            self.account_summary = self._request_account_summary()

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


class PositionProtect:
    """ロスカットを防ぐため閾値以下になるとポジションを決済し口座維持率を調整するためのクラス"""

    platform: OANDA  # OANDA などの Platform クラス
    protection_threshold: int  # 既定 % 以下になると調整する

    def __init__(self, platform: OANDA, protection_threshold: int = 105) -> None:
        self.platform = platform
        self.protection_threshold = int(protection_threshold)

    def is_under_threshold(self):
        """口座維持率が閾値以下となっているかどうかを判定する関数

        Returns:
            (boolean): True | False
        """
        flag = False
        # 有効残高 / 維持証拠金 が閾値以下の場合は True
        margin_used = self.platform.account.get_margin_used()
        nav = self.platform.account.get_net_asset_value()
        if margin_used != 0 and (nav / margin_used) * 100 < self.protection_threshold:
            flag = True

        return flag

    def trim_position(self, each_currency_position: dict = {}):
        """実際にポジションを決済しポジション数を調整する関数

        Args:
            each_currency_position (dict, optional): ポジション毎のオープントレードをまとめた dict. Defaults to {}.
        """
        # each_currency_position が渡されていた時はそのまま利用する
        if not each_currency_position:
            each_currency_position = self.get_top_losing_positions_by_pair()
        for instrument in self.platform.Price.main_currency_pairs:
            close_trade_id = (
                each_currency_position[instrument][0]["id"]
                if each_currency_position[instrument]
                else None
            )
            if (
                close_trade_id is None
            ):  # いずれか１つでも空になった場合は初期化してリターンする
                each_currency_position = {}
                break
            close_order_data = (
                self.platform.trade._make_close_order_data()
            )  # TODO: 一旦、units:ALL とする
            self.platform.trade.request_close_order(
                trade_id=close_trade_id, close_data=close_order_data
            )
            logger.info(f"id:{each_currency_position[instrument][0]["id"]}, {each_currency_position[instrument][0]["instrument"]}:{each_currency_position[instrument][0]["price"]} のポジションを {each_currency_position[instrument][0]["currentUnits"]}枚決済しました")
            # クローズしたポジションを削除する
            del each_currency_position[instrument][0]

        return each_currency_position

    def get_top_losing_positions_by_pair(self, top_n: int = 10):
        """最も現在価格と乖離している（=損失を出している）ポジションを通貨ペア毎に N ポジション選び取った dict を返す関数

        Args:
            top_n (int): いくつ分ポジションを選び取るかを指定する Default: 10

        Returns:
            (dict): ポジション毎のオープントレードを top_n 個分まとめた dict
            {
                "USD_JPY": [
                    {
                        "id": "210",
                        "instrument": "TRY_JPY",
                        "price": "4.352",
                        "openTime": "2024-10-08T00:30:24.527704550Z",
                        "initialUnits": "18",
                        "initialMarginRequired": "7.7616",
                        "state": "OPEN",
                        "currentUnits": "18",
                        "realizedPL": "0.0000",
                        "financing": "0.0000",
                        "dividendAdjustment": "0.0000",
                        "unrealizedPL": "-1.4760",
                        "marginUsed": "7.7580",
                    },
                    ...
                ],
                "USD_MXN": [
                    {
                        "id": "210",
                        "instrument": "TRY_JPY",
                        "price": "4.352",
                        "openTime": "2024-10-08T00:30:24.527704550Z",
                        "initialUnits": "18",
                        "initialMarginRequired": "7.7616",
                        "state": "OPEN",
                        "currentUnits": "18",
                        "realizedPL": "0.0000",
                        "financing": "0.0000",
                        "dividendAdjustment": "0.0000",
                        "unrealizedPL": "-1.4760",
                        "marginUsed": "7.7580",
                    },
                    ...
                ],
                "TRY_JPY": [
                    {
                        "id": "210",
                        "instrument": "TRY_JPY",
                        "price": "4.352",
                        "openTime": "2024-10-08T00:30:24.527704550Z",
                        "initialUnits": "18",
                        "initialMarginRequired": "7.7616",
                        "state": "OPEN",
                        "currentUnits": "18",
                        "realizedPL": "0.0000",
                        "financing": "0.0000",
                        "dividendAdjustment": "0.0000",
                        "unrealizedPL": "-1.4760",
                        "marginUsed": "7.7580",
                    },
                    ...
                ],
            }
        """
        # TODO: request_open_trades() に対するページャー処理と再帰呼び出し
        open_trades_response = self.platform.trade.request_open_trades()
        open_trades_list = open_trades_response["trades"]
        each_currency_position = (
            self._filter_each_currency_position_by_open_trades_list(open_trades_list)
        )
        each_currency_position = (
            self._sort_top_losing_positions_by_each_currency_position(
                each_currency_position, top_n
            )
        )
        return each_currency_position

    def _filter_each_currency_position_by_open_trades_list(
        self, open_trades_list: list
    ):
        """オープントレードのリストからそれぞれの通貨ペア毎にポジションをまとめ直した dict を返す関数

        Args:
            open_trades_list (list): self.platform.trade.request_open_trades()["trades"]

        Returns:
            (dict): ポジション毎のオープントレードをまとめた dict
            {
                "USD_JPY": [
                    {
                        "id": "210",
                        "instrument": "TRY_JPY",
                        "price": "4.352",
                        "openTime": "2024-10-08T00:30:24.527704550Z",
                        "initialUnits": "18",
                        "initialMarginRequired": "7.7616",
                        "state": "OPEN",
                        "currentUnits": "18",
                        "realizedPL": "0.0000",
                        "financing": "0.0000",
                        "dividendAdjustment": "0.0000",
                        "unrealizedPL": "-1.4760",
                        "marginUsed": "7.7580",
                    },
                    ...
                ],
                "USD_MXN": [
                    {
                        "id": "210",
                        "instrument": "TRY_JPY",
                        "price": "4.352",
                        "openTime": "2024-10-08T00:30:24.527704550Z",
                        "initialUnits": "18",
                        "initialMarginRequired": "7.7616",
                        "state": "OPEN",
                        "currentUnits": "18",
                        "realizedPL": "0.0000",
                        "financing": "0.0000",
                        "dividendAdjustment": "0.0000",
                        "unrealizedPL": "-1.4760",
                        "marginUsed": "7.7580",
                    },
                    ...
                ],
                "TRY_JPY": [
                    {
                        "id": "210",
                        "instrument": "TRY_JPY",
                        "price": "4.352",
                        "openTime": "2024-10-08T00:30:24.527704550Z",
                        "initialUnits": "18",
                        "initialMarginRequired": "7.7616",
                        "state": "OPEN",
                        "currentUnits": "18",
                        "realizedPL": "0.0000",
                        "financing": "0.0000",
                        "dividendAdjustment": "0.0000",
                        "unrealizedPL": "-1.4760",
                        "marginUsed": "7.7580",
                    },
                    ...
                ],
            }
        """
        each_currency_position = {
            currency_pair: []
            for currency_pair in self.platform.Price.main_currency_pairs
        }
        for open_trade in open_trades_list:
            if self.is_correct_currency(open_trade["instrument"]):
                each_currency_position[open_trade["instrument"]].append(open_trade)

        return each_currency_position

    def _sort_top_losing_positions_by_each_currency_position(
        self, each_currency_position: dict, top_n: int = 10
    ):
        """ポジション毎にまとめられたオープントレードの最も高いor安いものから top_n 個分抽出した dict を返す関数

        Args:
            each_currency_position (dict): 通貨ペア毎の open_trades のポジションリスト
            top_n (int): いくつ分ポジションを選び取るかを指定する Default: 10

        Returns:
            (dict): ポジション毎のオープントレードを top_n 個分まとめた dict
            {
                "USD_JPY": [
                    {
                        "id": "210",
                        "instrument": "TRY_JPY",
                        "price": "4.352",
                        "openTime": "2024-10-08T00:30:24.527704550Z",
                        "initialUnits": "18",
                        "initialMarginRequired": "7.7616",
                        "state": "OPEN",
                        "currentUnits": "18",
                        "realizedPL": "0.0000",
                        "financing": "0.0000",
                        "dividendAdjustment": "0.0000",
                        "unrealizedPL": "-1.4760",
                        "marginUsed": "7.7580",
                    },
                    ...*top_n 個
                ],
                "USD_MXN": [
                    {
                        "id": "210",
                        "instrument": "TRY_JPY",
                        "price": "4.352",
                        "openTime": "2024-10-08T00:30:24.527704550Z",
                        "initialUnits": "18",
                        "initialMarginRequired": "7.7616",
                        "state": "OPEN",
                        "currentUnits": "18",
                        "realizedPL": "0.0000",
                        "financing": "0.0000",
                        "dividendAdjustment": "0.0000",
                        "unrealizedPL": "-1.4760",
                        "marginUsed": "7.7580",
                    },
                    ...*top_n 個
                ],
                "TRY_JPY": [
                    {
                        "id": "210",
                        "instrument": "TRY_JPY",
                        "price": "4.352",
                        "openTime": "2024-10-08T00:30:24.527704550Z",
                        "initialUnits": "18",
                        "initialMarginRequired": "7.7616",
                        "state": "OPEN",
                        "currentUnits": "18",
                        "realizedPL": "0.0000",
                        "financing": "0.0000",
                        "dividendAdjustment": "0.0000",
                        "unrealizedPL": "-1.4760",
                        "marginUsed": "7.7580",
                    },
                    ...*top_n 個
                ],
            }
        """
        for instrument, open_trades_list in each_currency_position.items():
            # 念の為 open_trades_list が空だった場合に break
            if len(open_trades_list) < 1:
                break
            # units 数から long か short かを判断
            if (
                float(open_trades_list[0]["currentUnits"]) > 0
            ):  # long の場合最も高い値段のものを選択し決済
                open_trades_list.sort(key=lambda x: float(x["price"]), reverse=True)
            else:  # short の場合最も低い値段のものを選択し決済
                open_trades_list.sort(key=lambda x: float(x["price"]))
            each_currency_position[instrument] = open_trades_list[0:top_n]

        return each_currency_position

    def is_correct_currency(self, instrument: str):
        """扱う通貨ペアに含まれているかを判定する関数

        Args:
            instrument (str): 通貨ペア名 ex.USD_JPY

        Returns:
            (boolean): True | False
        """
        return instrument in self.platform.Price.main_currency_pairs

    @classmethod
    def is_within_business_hours_of_oanda(cls, target_utc_datetime: datetime = None):
        """OANDA の下記営業時間内かどうかを判定する関数
            月曜 6:00 - 土曜 05:59 JST
            ・午前 6 時 59 分から午前 7 時 5 分 （米国標準時間適用期間）
            ・午前 5 時 59 分から午前 6 時 5 分 （米国夏時間適用期間）
            ※米国東部時間 午後 4 時 59 分から午後 5 時 05 分の 6 分間

        Args:
            target_utc_datetime (datetime): UTC ベースでの指定日時  Default.None

        Returns:
            (boolean): True | False
        """
        # 現在の UTC 時刻を取得、または指定 UTC 時刻を取得
        now_utc = datetime.now(timezone.utc) if not target_utc_datetime else target_utc_datetime
        # ここで 9 時間加算した上で JST に変換する
        now_jst = now_utc + timedelta(hours=9)

        # 営業時間帯の除外リストを設定
        # 午前 6 時 59 分から午前 7 時 5 分
        excluded_times_morning = [
            (time(6, 59), time(7, 5))
        ]
        # 午前 5 時 59 分から午前 6 時 5 分
        excluded_times_night = [
            (time(5, 59), time(6, 5))
        ]

        # 現在時刻が除外時間内に入っているかどうかをチェック
        for start, end in excluded_times_morning + excluded_times_night:
            if start <= now_jst.time() <= end:
                return False

        # 営業開始は月曜日 06:00 JST
        start_of_business = now_jst.replace(hour=6, minute=0, second=0, microsecond=0)
        while start_of_business.weekday() != 0:  # 0 = Monday
            start_of_business -= timedelta(days=1)

        # 営業終了は土曜日 05:59 JST
        end_of_business = start_of_business + timedelta(days=4, hours=23, minutes=59)

        # 現在が営業時間内であれば True を返す
        return start_of_business <= now_jst <= end_of_business


# Lambdaハンドラー関数
def lambda_handler(event, context):
    """閾値を下回っていた場合ポジション数の調整を行う"""
    try:
        execute_position_protect()
        return {"statusCode": 200, "body": "Success position protect"}
    except Exception as e:
        logger.error(str(e))
        logger.error(traceback.format_exc())
        logger.error("Error position protect")
        return {"statusCode": 500, "body": "Error position protect"}


def execute_position_protect():
    # 5分おきに実行の想定のため営業時間の判定を設ける
    if PositionProtect.is_within_business_hours_of_oanda():
        # PositionProtect クラスの実体化
        oanda = OANDA(
            account_id=OANDA_ACCOUNT_ID,
            api_key=OANDA_API_KEY,
            api_url=OANDA_API_URL,
            account_mode=ACCOUNT_MODE,
        )
        position_protect = PositionProtect(oanda, PROTECTION_THRESHOLD)

        each_currency_position = {}
        while position_protect.is_under_threshold() is True:
            logger.info(f"口座維持率が {PROTECTION_THRESHOLD}% を下回りました。ポジション調整を行います...")
            each_currency_position = position_protect.trim_position(each_currency_position)
            position_protect.platform.account.update_account_summary()
            logger.info(f"現在の口座維持率は {(position_protect.platform.account.get_net_asset_value()/position_protect.platform.account.get_margin_used())*100}% です")


# ローカルテスト
if __name__ == "__main__":
    lambda_handler(None, None)
