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
from datetime import datetime, timedelta, date
import logging
import traceback

logger = logging.getLogger(__name__)
# ロガーのログレベルを設定する
logger.setLevel(logging.INFO)

# OANDAのAPI設定
OANDA_ACCOUNT_ID = os.environ["OANDA_ACCOUNT_ID"]
OANDA_API_KEY = os.environ["OANDA_RESTAPI_TOKEN"]
OANDA_API_URL = os.environ["OANDA_API_URL"]

MONTHLY_AMOUNT = int(os.environ["MONTHLY_AMOUNT"])  # 月単位の設定積立額
LEVERAGE = float(os.environ["LEVERAGE"])  # カスタム設定レバレッジ

try:
    ACCOUNT_MODE = os.environ["ACCOUNT_MODE"]
except Exception:
    raise Exception("ACCOUNT_MODE が設定されていません")


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

        def place_order(self, order_data: dict):
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

        def close_all_positions(
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

                # print(
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
        def position_close(
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

                    print(
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

                    print(
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
                prices = self.get_price(instruments=currency_pair)
                self.price_map[currency_pair] = prices
            logger.info(f"{self.price_map=}")

        def get_price(self, instruments: str):
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
            self.account_summary = self._get_account_summary()

        def _get_account_summary(self):
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

        def get_swap_points(self):
            # オープンポジションの情報を取得
            r = positions.OpenPositions(accountID=self.oanda.account_id)
            response = self.oanda.client.request(r)
            print(f"{response=}")

            # レスポンスからスワップポイントを抽出
            open_positions = r.response.get("positions", [])
            for position in open_positions:
                instrument = position["instrument"]
                long_swap = position["long"]["financing"]
                short_swap = position["short"]["financing"]
                print(
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
            print(params)
            print(f"{response=}")
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
                    print(transaction)


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


class Accumulation(Investment):
    """積立のための管理クラス
    1000万ペソ = 69万円/月 スワップ
    MXN/JPN が NY サーバに存在しないため
    USD/JPY Long | USD/MXN Short で代替する
    年間 1000万通貨の積立を目指す
    月間 100万通貨が必要となる（10ヶ月）
    日間 202409: 21日, 202410: 23, 202411: 21, 202412: 22, 202501: 23,
         202502: 20, 202503: 21, 202504: 22, 202505: 22, 202506: 21,
         202507: 23, 202508: 22, 202509: 22
        5万通貨 = 40万円/日
        レバレッジ 10倍だとして 4万円
        実質負担 = 80, 73,1, 66.2, 59.3, 52.4, 45.5, 38.6, 31.7, 24.8, 17.9, 11
        実質レバレッジ = 92%, 85.2%,
    [ 戦略 ]
        1000万円手元にあるとする。ペソ 8円だとして 125万ペソ。
        金利差が約 10%のため、年間で 100万円の利息がつく。
        ここでレバレッジを適用し、2倍であれば 500万円に対し、100万円。
        3倍であれば 333万円に対して 100万円。5倍であれば 200万円に対して 100万円という利率となる。
        基本はスワップを再度回して複利運用することで下記テーブルのようになる。
        1年目 - 3,264,188, 2年目 - 5,327,463, 3年目 - 8,694,920, 4年目 - 14,190,928, 5年目 - 23,160,931,
        円単位で年間 100万円の利率を目指し運用する
        概算によると usd/jpy+usd/mxn で年利 9%強
        TRY/JPY ポジションを含めることで年利 11%ほどのポートフォリオとする
    [ 戦術 ]
        積立分は枚数を固定する。円安となり上がってきた場合に買い支えできるため
            毎月 40360枚~30270枚 等の固定枚数を積み立てる
        複利分はレバレッジを固定する。複利単体で見て適正なバランスで維持するため
            80万円スワップがあった際には、レバレッジ x6 として 480万円分の通貨購入を行う
        => おそらく全てレバレッジベースで操作した方が良いのではないか？↓ロスカットコントローラにより全体倍率を 7.7倍等に定め逼迫したら削る処理を行う？
        USD/JPY: 7.7倍, USD/MXN: 7.7倍, TRY/JPY: 1/7.7倍 量の通貨購入を行う
    [ ロスカット戦略・戦術 ]
        USD/JPY と USD/MXN は分けて扱う
        その月毎に集計し、本来ロスカットであるラインで stoploss をまとめて設定する
        プレロスカットコントローラーを作成する
        そのポジションのレバレッジがたとえば 5倍を割るライン
            150 usd/jpy の long 1000unit を保有しているとすると証拠金は 3300yen
            有効証拠金が 10000yen の場合は、1pips 10円の値動きのため差異 6700yen-670pips-6.7yen でロスカット
            本来の 7倍を保つためのラインを求め、ポジション数を削ることで倍率を調整する
        毎月の積立は燃料と同じ。進めるだけ進むがレバレッジが 20倍を超えるとブレーキを踏む。
        その時は含み益があるポジションから整理し、17~15倍程度まで戻す
        本来のロスカット値にてストップロスが入った場合は、翌月の積立コントローラにて含めて買い付ける
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
            self.platform.trade.place_order(usd_order_data)
            # USD_MXN の Short
            # TODO: stoploss の設定
            mxn_amount = -1 * mxn_amount  # Short のため - 数量にする
            mxn_order_data = self.platform.trade._make_order_data(
                units=mxn_amount, instrument="USD_MXN"
            )
            self.platform.trade.place_order(mxn_order_data)
            # TRY_JPY の Long
            # TODO: stoploss の設定
            try_order_data = self.platform.trade._make_order_data(
                units=try_amount, instrument="TRY_JPY"
            )
            self.platform.trade.place_order(try_order_data)

    @classmethod
    def get_daily_amount(cls, monthly_amount: int, target_date: date = None):
        """日単位の購入 円 通貨量を求める関数
        四捨五入されて int で返る

        Args:
            monthly_amount (int): 月額の積立予算額（円）
            target_date (date, optional): 指定日時

        Returns:
            int: 四捨五入された 円 通貨量
        """
        weekday_count = super().count_weekdays_in_month(target_date)
        daily_amount = round(monthly_amount / weekday_count)
        return daily_amount

    def __change_account_mode(self):
        """アカウントモードによる調整を行う
        DEMO: デモ環境, PERS: 個人本番環境, CORP: 法人本番環境
        """
        if ACCOUNT_MODE == "DEMO":
            pass
        elif ACCOUNT_MODE == "PERS":
            # 個人環境の場合 1/10 で検証する
            self.daily_amount = int(self.daily_amount / 10)
            self.dairy_mxn_amount = int(self.dairy_mxn_amount / 10)
            self.dairy_usd_amount = int(self.dairy_usd_amount / 10)
        elif ACCOUNT_MODE == "CORP":
            pass
        else:
            raise Exception("***不正な ACCOUNT_MODE です***")

    # def calc_stop_loss_pips(self, margin_available: float, instrument: str):
    #     """ストップロスを設定するための関数
    #     証拠金の 2% を最大損失額として計算する
    #         */JPY : 100pips で +-1円

    #     Args:
    #         margin_available (float): 計算のベースとなる証拠金額
    #         instrument (str): 通貨ペア

    #     Returns:
    #         pips (int): pips数
    #     """
    #     cross_jpy = instrument.split("_")[1] == "JPY"
    #     pips = None
    #     if cross_jpy:
    #         pips = int(margin_available * 0.02 / 100)
    #     else:
    #         pips =


def lambda_handler(event, context):
    """毎日同じ通貨量を取引し積立を行う"""
    """[戦略] 1000万円分 = 約 125万ペソを 1ヶ月で買い切るため 約6万ペソ/日 購入し一月続ける"""
    """[戦略] レバレッジ 5倍をキープするとして、2年間複利運用すると 2年目での最終的な unit数は 41units になる見込み
        目標金額が 240Myen だとすると 5853658yen/month=unit となる。
        毎月 80万円入金し、5853658yen=40370$ 分購入を続ける"""
    # TODO: API 利用のための GOLD ステータス維持のため NY サーバでの取引量が 500,000$/月内 を超える必要がある
    #   したがって、25,000$（* 5回）の USD を両建てでオーダーしその後決済するメンテナンス用コントローラを追加する必要がある

    try:
        logger.info("Starting execute_accumulation ...")
        execute_accumulation()
        logger.info("Success placing orders")
        return {"statusCode": 200, "body": "Success placing orders"}
    except Exception as e:
        logger.error(str(e))
        logger.error(traceback.format_exc())
        logger.error("Error placing orders")
        return {"statusCode": 500, "body": "Error placing orders"}


def execute_accumulation():
    # インスタンスの実体化
    oanda = OANDA(
        account_id=OANDA_ACCOUNT_ID,
        api_key=OANDA_API_KEY,
        api_url=OANDA_API_URL,
        account_mode=ACCOUNT_MODE,
    )
    accumulation = Accumulation(platform=oanda, leverage=LEVERAGE)
    # 当日の投資額を計算
    daily_amount = accumulation.get_daily_amount(MONTHLY_AMOUNT)
    # 買付けの実施
    accumulation.execute_purchase(daily_amount)


# ローカルテスト
if __name__ == "__main__":
    lambda_handler(None, None)
