import os
import oandapyV20
from oandapyV20.endpoints import orders, positions, accounts, pricing
from typing import NamedTuple, Dict, List, Tuple


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
    client: oandapyV20.API  # API クライアント

    def __init__(self, account_id, api_key, api_url) -> None:
        self.account_id = account_id
        self.api_key = api_key
        self.api_url = api_url
        environment = "practice" if ACCOUNT_MODE == "DEMO" else "live"
        print(self.account_id, self.api_key, self.api_url)
        print(f"{environment=}")
        self.client = oandapyV20.API(
            access_token=api_key, environment=environment
        )

    class Trade:
        """OANDA でのトレードをまとめたクラス

        Raises:
            Exception: 全ての例外
        """

        def __init__(self, oanda_instance) -> None:
            self.oanda = oanda_instance

        # マーケットオーダーを送信する関数
        def place_order(
            self,
            units: int,
            instrument: str = "USD_JPY",
            stop_loss_pips=0,
            take_profit_pips=0,
        ):
            """マーケットオーダーを送信する関数

            Args:
                units (_type_): 購入数
                instrument (str, optional): 通貨ペア. Defaults to "USD_JPY".
                stop_loss_pips (int, optional): ストップロスの pips. Defaults to 0.
                take_profit_pips (int, optional): 利確のpips. Defaults to 0.

            Returns:
                _type_: _description_
            """
            # 現在の価格を取得
            # endpoint = pricing.PricingInfo(
            #     accountID=OANDA_ACCOUNT_ID, params={"instruments": instrument}
            # )
            # response = client.request(endpoint)
            # current_price = float(response["prices"][0]["closeoutAsk"])

            # 証拠金の2%をリスクとして計算
            # margin_available = get_account_margin()
            # print(f"{margin_available=}")
            # risk_amount = margin_available * 0.02
            # stop_loss_price = current_price - (stop_loss_pips * 0.0001)
            # take_profit_price = current_price + (take_profit_pips * 0.0001)

            order_data = {
                "order": {
                    "units": str(units),  # 正の値は買い、負の値は売り
                    "instrument": instrument,
                    "timeInForce": "FOK",
                    "type": "MARKET",
                    "positionFill": "DEFAULT",
                    # "stopLossOnFill": {
                    #     "price": f"{stop_loss_price:.5f}"
                    # },
                    # "takeProfitOnFill": {
                    #     "price": f"{take_profit_price:.5f}"
                    # }
                }
            }
            r = orders.OrderCreate(self.oanda.account_id, data=order_data)
            response = self.oanda.client.request(r)
            return response

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
                            response.get("longOrderFillTransaction").get(
                                "units"
                            ),
                            response.get("longOrderFillTransaction").get(
                                "price"
                            ),
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
                            response.get("shortOrderFillTransaction").get(
                                "units"
                            ),
                            response.get("shortOrderFillTransaction").get(
                                "price"
                            ),
                            response.get("shortOrderFillTransaction").get(
                                "pl"
                            ),
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
        # PriceMap = Dict[str, float]
        price_map: PriceMap
        main_currency_pairs = (
            "USD_JPY",
            "USD_MXN",
        )
        main_currencies = (
            "USD",
            "JPY",
            "MXN",
        )

        def __init__(self, oanda_instance):
            self.price_map = {}
            self.oanda = oanda_instance

        def generate_price_map(self):
            print(f"{self.main_currency_pairs} の price_map を生成します")
            for currency_pair in self.main_currency_pairs:
                bid, ask, mid = self.get_price(instruments=currency_pair)
                self.price_map[currency_pair] = self.Prices(bid, ask, mid)
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
                middle_price = (float(bid) + float(ask)) / 2
                return bid, ask, middle_price
            except Exception as e:
                print(f"Error: {e}")

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

        def __init__(self, oanda_instance) -> None:
            self.oanda = oanda_instance

        # 証拠金を取得する関数
        def get_account_margin(self):
            """証拠金を取得する関数

            Returns:
                margin_available (float): 証拠金残高
            """
            endpoint = accounts.AccountSummary(self.oanda.account_id)
            print(self.oanda.account_id, endpoint)
            response = self.oanda.client.request(endpoint)
            margin_available = float(response["account"]["marginAvailable"])
            return margin_available


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


class FundManagement:
    """資金管理用クラス
    利益の 50%: 消費, 40%: 投資, 10%: 消費
    GOLDEN RULES:
        ・トレンドの判断は直近高値、安値を更新したか
        ・資金管理は２％
        ・複利が適用できる運用方針とする
        ・通貨の強弱  GBP/USD↑ GBP/JPY↑ USD/JPY↑ の時 GBP>USD>JPY となり GBP/JPY で強いトレンドとなりやすい
        ・利益の毎月 20% は出金する（税金）
    Attributes:
        name (str): The name of the person.
        age (int): The age of the person.
    """

    def rule_of_2percent():
        """2%ルールを適用する
        クロス円: ロット（通貨量） = 損失額 / 損失幅(pips) * 100
        ドルストレート: ロット（通貨量） = 損失額 / 損失幅(pips) / ドル円レート * 10000
            ☆バルサラ破産確率表も利用する

        """
        pass

    def kelly_criterion():
        """ケリー基準を求める関数
        単利でプラスの期待値があるシステムが複利効果を得ると最終的なリターンは大きくなりますが、
        リスクを過剰に取るとドローダウンを回復できなくなるため逆に最終的なリターンは小さくなっていくことを、ここまでで解説しました。
            https://www.oanda.jp/lab-education/ea_trading/beginner/optimal_f_fund_management/
        ケリー基準(Kelly criterion)は、最終的なリターンを最大化するための複利運用比率を求めます。
        f = p - (1-p)/b
            f: 掛け金の比率
            p: 勝率。勝率 55% なら p=0.55 となる。
            b: 利益と損失の比率。利益 150、損失 100なら b=1.5 となる
        """


class TradingEnvironmentAnalysis:
    """環境認識クラス
    取引手法や分析に関するメソッドを扱う
        ・トレンド判断
        ・通過強弱判断
    シグナル毎に Severity をつける
        Severity: HIGH
            月足のゴールデンクロス
            週足のゴールデンクロス
        Severity: MEDIUM
            日足のゴールデンクロス
            下位足の複数同時のゴールデンクロス？
            複数のダイバージェンス？
    """

    def elliot_diagonal():
        """エリオット波動を分析する関数
        エリオット波動定義：
            高さ：
                2 < 1 < 3 < 4 < 5
                2波は1波の始まりより低くならない（ヒゲさえも）
                4波は1波の終点=2波の始点よりも低くならない
                2波は深く戻すことが多く、4波は浅く戻す
                2波は簡単なチャートパターン、4波は複雑になることが多い=オルタネーション（2と4が逆のパターンもある）
                5波の高さは3波を超える=>3波超えたら利確の準備
                イレギュラーパターン:
                    フェイラー: 5波が3波を超えない => 勢いが不足している場合に表れる
                    エンディングダイアゴナル: 5波において 12345 がフラッグのような形で重なり表れる
                    エクステンション: 3波で12345波の形となっている => 強力なトレンドで現れやすい
                    ランニングコレクション: 2波が落ちず3波に繋がる => 相場に大きな勢いがある時に表れる

            長さ：
                2-3
                3波より1波の方が長い場合、1波 < 3波 < 5波

        """


# 購入 units 数を計算する関数
def calculate_units(
    entry_price, margin, risk_percentage=0.02, stop_loss_pips=50
):
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
    """毎日同じ通貨量を取引し積立を行う"""
    """[戦略] 1000万円分 = 約 125万ペソを 1ヶ月で買い切るため 約6万ペソ/日 購入し一月続ける"""
    """[戦略] レバレッジ 5倍をキープするとして、2年間複利運用すると 2年目での最終的な unit数は 41units になる見込み
        目標金額が 240Myen だとすると 5853658yen/month=unit となる。
        毎月 80万円入金し、5853658yen=40370$ 分購入を続ける"""
    MONTHLY_AMOUNT = 5853658  # 円単位
    if ACCOUNT_MODE == "DEMO":
        MONTHLY_AMOUNT = 10000000  # 円単位（デモ）
    DAILY_AMOUNT = MONTHLY_AMOUNT / 22  # 22日計算
    try:
        # インスタンスを作成
        oanda = OANDA(
            account_id=OANDA_ACCOUNT_ID,
            api_key=OANDA_API_KEY,
            api_url=OANDA_API_URL,
        )
        trade_manager = OANDA.Trade(oanda)
        price_manager = OANDA.Price(oanda)
        account_manager = OANDA.Account(oanda)
        margin = account_manager.get_account_margin()
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
        trade_manager.place_order(
            units=(-1 * usd_amount), instrument="USD_MXN"
        )

        return {
            "statusCode": 200,
            "body": f"{usd_amount}units Orders placed successfully",
        }

    except Exception as e:
        print("Error:", str(e))
        return {"statusCode": 500, "body": "Error placing orders"}


# ローカルテスト
if __name__ == "__main__":
    lambda_handler(None, None)
