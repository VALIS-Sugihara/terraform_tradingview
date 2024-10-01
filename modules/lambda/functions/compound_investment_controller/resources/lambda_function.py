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

JST = ZoneInfo("Asia/Tokyo")

# OANDAのAPI設定
OANDA_ACCOUNT_ID = os.environ["OANDA_ACCOUNT_ID"]
OANDA_API_KEY = os.environ["OANDA_RESTAPI_TOKEN"]
OANDA_API_URL = os.environ["OANDA_API_URL"]

try:
    ACCOUNT_MODE = os.environ["ACCOUNT_MODE"]
except Exception:
    raise Exception("ACCOUNT_MODE が設定されていません")

# OANDAのAPIクライアントを設定
# client = oandapyV20.API(access_token=OANDA_API_KEY)


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

    def __init__(
        self, account_id: str, api_key: str, api_url: str, account_mode: str
    ) -> None:
        self.account_id = account_id
        self.api_key = api_key
        self.api_url = api_url
        self.account_mode = account_mode
        print(self.account_id, self.api_key, self.api_url, account_mode)
        self.client = self._create_client()
        self.trade = self.Trade(self)  # trade_manager
        self.price = self.Price(self)  # price_manager
        self.account = self.Account(self)  # account_manager

    def _create_client(self):
        # Create and return an oandapyV20 API client instance using api_key and api_url
        environment = "practice" if ACCOUNT_MODE == "DEMO" else "live"
        return oandapyV20.API(access_token=self.api_key, environment=environment)

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
                print("Error:", str(e))
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
                print("Error:", str(e))
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
            self.price_map = {}
            self.oanda = oanda

        def generate_price_map(self):
            self.price_map = {}
            print("price_map を生成します")
            for currency_pair in self.main_currency_pairs:
                prices = self.get_price(instruments=currency_pair)
                self.price_map[currency_pair] = prices
            print(f"{self.price_map=}")

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
                print(f"Error: {e}")
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

        def __init__(self, oanda) -> None:
            self.oanda = oanda

        # 証拠金を取得する関数
        def get_margin_available(self):
            """証拠金を取得する関数

            Returns:
                margin_available (float): 証拠金残高
            """
            endpoint = accounts.AccountSummary(self.oanda.account_id)
            response = self.oanda.client.request(endpoint)
            margin_available = float(response["account"]["marginAvailable"])
            return margin_available

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
        Exception: _description_

    Returns:
        _type_: _description_
    """

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
        print(f"{usd_rate=}")
        usd_amount = int(self.dairy_amount / usd_rate)
        print(f"{usd_amount=}")
        return usd_amount


class Accumulation:
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

    dairy_amount: int  # 毎日購入する通貨量（円単位）
    dairy_mxn_amount: int  # 毎日購入する通貨量（ペソ単位）
    dairy_usd_amount: int  # 毎日購入する通貨量（ドル単位）

    def __init__(self, dairy_amount: int, price_map: dict) -> None:
        self.dairy_amount = dairy_amount
        self.dairy_mxn_amount = self.convert_jpy_to_mxn(price_map)
        self.dairy_usd_amount = self.convert_mxn_to_usd(price_map)
        self.__change_account_mode()

    def __change_account_mode(self):
        """アカウントモードによる調整を行う
        DEMO: デモ環境, PERS: 個人本番環境, CORP: 法人本番環境
        """
        if ACCOUNT_MODE == "DEMO":
            pass
        elif ACCOUNT_MODE == "PERS":
            # 個人環境の場合 1/10 で検証する
            self.dairy_amount = int(self.dairy_amount / 10)
            self.dairy_mxn_amount = int(self.dairy_mxn_amount / 10)
            self.dairy_usd_amount = int(self.dairy_usd_amount / 10)
        elif ACCOUNT_MODE == "CORP":
            pass
        else:
            raise Exception("***不正な ACCOUNT_MODE です***")

    @classmethod
    def count_weekdays_in_current_month(cls):
        # 現在の日付を取得
        today = date.today()

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

    def convert_jpy_to_mxn(self, price_map: dict):
        """JPY の通貨量を MXN 単位へ変換する関数
        サーバに MXN/JPY がないため USD/JPY / USD/MXN の中値で MXN/JPY レートを計算する

        Args:
            price_map (dict): プライスマップ

        Raises:
            Exception: 全ての例外

        Returns:
            mxn_amount (int): MXN の通貨量
        """
        mxn_rate = price_map["USD_JPY"].mid / price_map["USD_MXN"].mid
        print(f"{mxn_rate=}")
        mxn_amount = int(self.dairy_amount / mxn_rate)
        print(f"{mxn_amount=}")
        return mxn_amount

    def convert_mxn_to_usd(self, price_map: dict):
        """MXN の通貨量を USD 単位へ変換する関数

        Args:
            rate (float): USD/MXN の計算レート

        Raises:
            Exception: 全ての例外

        Returns:
            usd_amount (int): USD の通貨量
        """
        usd_amount = int(self.dairy_mxn_amount / price_map["USD_MXN"].bid)
        return usd_amount

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


class CompoundInvestment:

    def __init__(self) -> None:
        pass

    def get_daily_swap_points():
        # トランザクション履歴から最新の DAILY_INTEREST を取得する
        """トランザクション履歴から最新の DAILY_INTEREST を取得する
        {
            "id" : 175739363,
            "accountId" : 1491998,
            "time" : "2014-04-15T15:21:21Z",
            "type" : "DAILY_INTEREST",
            "instrument" : "EUR_USD",
            "interest" : 10.0414,
            "accountBalance" : 99999.9992
        }
        """
        # Define the date range for today's transactions
        start_date = (
            datetime.now(JST)
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .isoformat("T")
            + "Z"
        )
        end_date = (datetime.now(JST) + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat("T") + "Z"

        # Pagination setup
        params = {
            "from": start_date,
            "to": end_date,
            "type": "DAILY_INTEREST",  # Filter for DAILY_INTEREST transaction types
            "pageSize": 100,  # Adjust page size as needed
        }

        # Initialize an empty list to store DAILY_INTEREST transactions
        daily_interest_transactions = []

        # Start pagination loop
        while True:
            try:
                # Get the transactions
                request = transactions.TransactionIDRange(accountID, params=params)
                response = client.request(request)

                # Filter out DAILY_INTEREST transactions
                daily_interest_transactions.extend(
                    [
                        tx
                        for tx in response.get("transactions", [])
                        if tx["type"] == "DAILY_INTEREST"
                    ]
                )

                # Pagination: check if there are more pages
                if "nextPage" in response:
                    params["beforeID"] = response["nextPage"]
                else:
                    break
            except Exception as e:
                print(f"Error fetching transactions: {e}")
                break

        # Output the DAILY_INTEREST transactions for today
        for tx in daily_interest_transactions:
            print(tx)
        # 必要ならページャー処理
        # 必要なら instrument 毎の swap を合計して返す
        # swap を円換算？
        pass


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
    print(f"購入するユニット数: {int(units)}")
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
    execute_compound_investment()
    exit()

    # 関数を実行して平日の日数を計算
    WEEKDAYS_THIS_MONTH = Accumulation.count_weekdays_in_current_month()
    print("当月の平日の日数:", WEEKDAYS_THIS_MONTH)

    MONTHLY_AMOUNT = 5853658  # 円単位
    if ACCOUNT_MODE == "DEMO":
        MONTHLY_AMOUNT = 10000000  # 円単位（デモ）
    DAILY_AMOUNT = MONTHLY_AMOUNT / WEEKDAYS_THIS_MONTH  # 22日計算
    try:
        # インスタンスを作成
        oanda = OANDA(
            account_id=OANDA_ACCOUNT_ID,
            api_key=OANDA_API_KEY,
            api_url=OANDA_API_URL,
            account_mode=ACCOUNT_MODE,
        )
        trade_manager = OANDA.Trade(oanda)
        price_manager = OANDA.Price(oanda)
        account_manager = OANDA.Account(oanda)
        margin = account_manager.get_account_margin()
        account_manager.get_transactions_last_month()
        account_manager.get_swap_points()
        exit()
        print(f"{margin=}")

        # 現在価格のプライスマップを取得する
        price_manager.generate_price_map()

        # プライスマップから購入する USD 通貨量を計算する
        accumulation = Accumulation(DAILY_AMOUNT, price_manager.price_map)
        usd_amount = accumulation.dairy_usd_amount
        print(f"{usd_amount=}")

        # 求めた通貨量で USD/JPY と MXN/USD を取引する
        # TODO: 証拠金残高の 2% でストップロスを設定する
        trade_manager.place_order(units=usd_amount, instrument="USD_JPY")
        trade_manager.place_order(units=(-1 * usd_amount), instrument="USD_MXN")

        return {
            "statusCode": 200,
            "body": f"{usd_amount}units Orders placed successfully",
        }

    except Exception as e:
        print("Error:", str(e))
        return {"statusCode": 500, "body": "Error placing orders"}


def execute_compound_investment():
    # CompoundInvestment クラスの実体化
    # 当日スワップポイントの取得
    oanda = OANDA(
        account_id=OANDA_ACCOUNT_ID,
        api_key=OANDA_API_KEY,
        api_url=OANDA_API_URL,
        account_mode=ACCOUNT_MODE,
    )

    swap_points = get_daily_swap_points(oanda)

    # 買付け実施
    execute_purchase(swap_points)


def get_daily_swap_points(oanda: OANDA):
    # トランザクション履歴から最新の DAILY_INTEREST を取得する
    """_summary_
    {
        "id" : 175739363,
        "accountId" : 1491998,
        "time" : "2014-04-15T15:21:21Z",
        "type" : "DAILY_INTEREST",
        "instrument" : "EUR_USD",
        "interest" : 10.0414,
        "accountBalance" : 99999.9992
    }
    """
    # Define the date range for today's transactions
    start_date = (
        datetime.now(timezone.utc)
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .isoformat(timespec="seconds")
    )

    end_date = (
        datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        + timedelta(days=1)
    ).isoformat(timespec="seconds")

    print(f"{start_date=}")
    print(f"{end_date=}")

    # Pagination setup
    params = {
        "from": "2024-10-01",
        "to": "2024-10-02",
        "type": "DAILY_FINANCING",  # Filter for DAILY_INTEREST transaction types
        "pageSize": 100,  # Adjust page size as needed
    }

    # Initialize an empty list to store DAILY_INTEREST transactions
    daily_interest_transactions = []

    # Start pagination loop
    while True:
        try:
            # Get the transactions
            request = transactions.TransactionList(oanda.account_id, params=params)
            response = oanda.client.request(request)
            print(f"{response=}")

            # Filter out DAILY_INTEREST transactions
            daily_interest_transactions.extend(
                [
                    tx
                    for tx in response.get("transactions", [])
                    if tx["type"] == "DAILY_INTEREST"
                ]
            )

            # Pagination: check if there are more pages
            if "nextPage" in response:
                params["beforeID"] = response["nextPage"]
            else:
                break
        except Exception as e:
            print(f"Error fetching transactions: {e}")
            break
    exit()
    # Output the DAILY_INTEREST transactions for today
    for tx in daily_interest_transactions:
        print(tx)
    # 必要ならページャー処理
    # 必要なら instrument 毎の swap を合計して返す
    # swap を円換算？
    pass


def execute_purchase(swap_points):
    # swap を円換算？
    # 与信処理
    # usdjpy の買付け
    # usdmxn の買付け
    # tryjpy の買付け
    pass


# ローカルテスト
if __name__ == "__main__":
    lambda_handler(None, None)
