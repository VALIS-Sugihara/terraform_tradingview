import json
import os
import oandapyV20
from oandapyV20.endpoints import orders, positions, accounts, pricing
from typing import NamedTuple


# OANDAのAPI設定
OANDA_ACCOUNT_ID = os.environ["OANDA_ACCOUNT_ID"]
OANDA_API_KEY = os.environ["OANDA_RESTAPI_TOKEN"]
OANDA_API_URL = 'https://api-fxpractice.oanda.com'  # デモアカウントの場合。ライブアカウントの場合は'https://api-fxtrade.oanda.com'

# OANDAのAPIクライアントを設定
client = oandapyV20.API(access_token=OANDA_API_KEY)


def get_price(instruments: str):
    """ 価格取得関数
        中値を計算し返す
    Args:
        instruments (str): 取得したい通過ペア. ex) USD_JPY
    Returns:
        str: A greeting message.
    """
    # 価格情報を取得するエンドポイントの設定
    params = {
        "instruments": instruments
    }
    pricing_info = pricing.PricingInfo(accountID=OANDA_ACCOUNT_ID, params=params)
    
    # リクエストを送信して現在価格を取得
    try:
        response = client.request(pricing_info)
        prices = response["prices"][0]
        # print(f"{prices=}")
        bid = prices["bids"][0]["price"]
        ask = prices["asks"][0]["price"]
        print(f"{instruments} Bid Price: {bid}")
        print(f"{instruments} Ask Price: {ask}")
        middle_price = (float(bid) + float(ask)) / 2
        return middle_price
    except Exception as e:
        print(f"Error: {e}")

class Esperanto():
    """ 各通貨を統一ために扱うためのクラス
    世界共通語として発明された ESPERANTO をモチーフとして命名
    """
    class EsperantoResult(NamedTuple):
        esperanto_ratio: float  # 相場の何割安か. 0.5 であれば 50%Off と同じ扱い
        long_position: list = []  # Long するべき通貨ペア. 2つ出るはずなので list で ["USD_JPY", "EUR_JPY"] のような形
        short_position: list = []  # short するべき通貨ぺあ. 1つのはずなので "EUR_USD" の形
        # Name: str = "Alice"  # デフォルト値をつける時はないものの定義のあとであれば OK

    main_currencies = ["USD_JPY", "EUR_JPY", "GBP_JPY", "AUD_JPY", "NZD_JPY", "EUR_GBP", "EUR_USD", 
        "EUR_AUD", "EUR_NZD", "GBP_USD", "GBP_AUD", "GBP_NZD", "AUD_USD", "AUD_NZD", "NZD_USD"]
    result: EsperantoResult = None
    esperanto_ratio: float = None  # 相場の何割安か. 0.5 であれば 50%Off と同じ扱い
    long_position: list = []  # Long するべき通貨ペア. 2つ出るはずなので list で ["USD_JPY", "EUR_JPY"] のような形
    short_position: list = []  # short するべき通貨ぺあ. 1つのはずなので "EUR_USD" の形


    def __init__(self) -> None:
        pass

    def calc_esperanto_ratio(self, price_map: dict, first_currency: str, second_currency: str, third_currency: str):
        """ ３通貨間で割安な通貨ペアを計算し、long/short をそれぞれ取るべき通貨ペアを導き出す関数
            世界共通語として発明された ESPERANTo をモチーフとして命名
            考え方例）
                Apple が 5個で Orange を 1つ買える (orange_apple = 5)
                Apple が 100個で Melon を 1つ買える (melon_apple = 100) 時
                Melon が Orange 10個で買える場合は、 (melon_orange = 10)
                Orange で Melon を買い、Orange を売り Apple を買うべきである
            数式例）
            Ptn.1: 割安の場合
                orange_apple = 5
                melon_apple = 100
                melon_orange = 10  # 本来は melon_orange = 20            
                melon_apple / orange_apple
                # melon_orange < (melon_apple / orange_apple) の時に orange で melon で買, melon を売り apple を買, 追加で？apple で orange を買
                # つまり、melon_orange - long, melon_apple - short, orange_apple - long ??  Orange:10 -> Melon:1 -> Apple: 100 -> Orange:20
            Ptn.2: 割高の場合
                orange_apple = 5
                melon_apple = 100
                melon_orange = 25  # 本来は melon_orange = 20            
                melon_apple / orange_apple
                # melon_orange > (melon_apple / orange_apple) の時に melon を売り orange を買, orange を売り apple を買, 追加で？apple で melon を買
                # つまり、melon_orange - short, orange_apple - short, melon_apple - long, ??  Melon:1 -> Orange:25 -> Apple:125 -> Melon:1.25
        Args:
            instruments (str): 取得したい通過ペア. ex) USD_JPY
        Returns:
            EsperantoResult (NamedTuple):
                相場の何割安か. 0.50 であれば 50%Off と同じ扱い
        """

        first_pair_price = price_map.get(f"{second_currency}_{first_currency}", 1 / float(price_map.get(f"{first_currency}_{second_currency}", 1)))  # ない時は逆数を返す
        second_pair_price = price_map.get(f"{third_currency}_{first_currency}", 1 / float(price_map.get(f"{first_currency}_{third_currency}", 1)))  # ない時は逆数を返す
        third_pair_price = price_map.get(f"{third_currency}_{second_currency}", 1 / float(price_map.get(f"{second_currency}_{third_currency}", 1)))  # ない時は逆数を返す

        esperanto_ratio: float = third_pair_price / (second_pair_price / first_pair_price)
        
        # flag = third_pair_price < (second_pair_price / first_pair_price)

        # TODO: 閾値判定
        if esperanto_ratio < 1:  # 本来相場より割安であるため Long が 2つに Short が 1つ
            print("組み合わせ", f"{third_currency}_{second_currency}_{first_currency} Esperanto LONG")
            print("実効レート: ", third_pair_price, second_pair_price / first_pair_price)
            result = self.EsperantoResult(esperanto_ratio, [f"{third_currency}_{second_currency}", f"{second_currency}_{first_currency}"], [f"{third_currency}_{first_currency}"])
            self.result = result
            self.change_pair()
            return result
        if esperanto_ratio > 1:  # 本来相場より割高であるため Short が 2つに Long が 1つ？
            print("組み合わせ", f"{third_currency}_{second_currency}_{first_currency} Esperanto SHORT")
            print("実効レート: ", third_pair_price, second_pair_price / first_pair_price)
            result = self.EsperantoResult(esperanto_ratio, [f"{third_currency}_{first_currency}"], [f"{third_currency}_{second_currency}", f"{second_currency}_{first_currency}"])
            self.result = result
            self.change_pair()
            return result
        else:
            print("組み合わせ", f"{third_currency}_{second_currency}_{first_currency} NOT FLAGGED")
            print("実効レート: ", third_pair_price, second_pair_price / first_pair_price)
            result = self.EsperantoResult(esperanto_ratio)
            self.result = result
            return result

    def change_pair(self):
        """ 通貨ペアとポジションを是正するための関数
        self.long_position = ["JPY_USD"] となっていた場合、
        self.short_position = ["USD_JPY"] へと訂正する
        """
        # TODO: main_currencies に基づき判断
        for long_position in self.result.long_position:
            if long_position == "JPY_USD":
                self.short_position.append("USD_JPY")
            if long_position == "JPY_EUR":
                self.short_position.append("EUR_JPY")
            if long_position == "USD_EUR":
                self.short_position.append("EUR_USD")
            else:
                self.long_position.append(long_position)

        for short_position in self.result.short_position:
            if short_position == "JPY_USD":
                self.long_position.append("USD_JPY")
            if short_position == "JPY_EUR":
                self.long_position.append("EUR_JPY")
            if short_position == "USD_EUR":
                self.long_position.append("EUR_USD")
            else:
                self.short_position.append(short_position)


class FundManagement():
    """ 資金管理用クラス
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
        """ 2%ルールを適用する
        クロス円: ロット（通貨量） = 損失額 / 損失幅(pips) * 100
        ドルストレート: ロット（通貨量） = 損失額 / 損失幅(pips) / ドル円レート * 10000
            ☆バルサラ破産確率表も利用する
        
        """
        pass

    def kelly_criterion():
        """ ケリー基準を求める関数
        単利でプラスの期待値があるシステムが複利効果を得ると最終的なリターンは大きくなりますが、
        リスクを過剰に取るとドローダウンを回復できなくなるため逆に最終的なリターンは小さくなっていくことを、ここまでで解説しました。
            https://www.oanda.jp/lab-education/ea_trading/beginner/optimal_f_fund_management/
        ケリー基準(Kelly criterion)は、最終的なリターンを最大化するための複利運用比率を求めます。
        f = p - (1-p)/b
            f: 掛け金の比率
            p: 勝率。勝率 55% なら p=0.55 となる。
            b: 利益と損失の比率。利益 150、損失 100なら b=1.5 となる
        """

class TradingEnvironmentAnalysis():
    """ 環境認識クラス
    取引手法や分析に関するメソッドを扱う
        ・トレンド判断
        ・通過強弱判断
    """

# 証拠金を取得する関数
def get_account_margin():
    endpoint = accounts.AccountSummary(OANDA_ACCOUNT_ID)
    response = client.request(endpoint)
    margin_available = float(response['account']['marginAvailable'])
    return margin_available

# マーケットオーダーを送信する関数
def place_order(units, instrument='USD_JPY', stop_loss_pips=10, take_profit_pips=20):
    # 現在の価格を取得
    endpoint = pricing.PricingInfo(accountID=OANDA_ACCOUNT_ID, params={"instruments": instrument})
    response = client.request(endpoint)
    current_price = float(response['prices'][0]['closeoutAsk'])

    # 証拠金の2%をリスクとして計算
    margin_available = get_account_margin()
    print(f"{margin_available=}")
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
    r = orders.OrderCreate(OANDA_ACCOUNT_ID, data=order_data)
    response = client.request(r)
    return response

# ポジション決済を送信する関数
def position_close(close_action, units, instrument='USD_JPY', stop_loss_pips=10, take_profit_pips=20):
    try:
        # Long ポジションの決済
        if close_action == "long":
            data = {"longUnits": "ALL"}
            request = positions.PositionClose(accountID=OANDA_ACCOUNT_ID, instrument=instrument, data=data)
            response = client.request(request)

            print("position close: {} at {}. pl: {}".format(
                response.get("longOrderFillTransaction").get("units"),
                response.get("longOrderFillTransaction").get("price"),
                response.get("longOrderFillTransaction").get("pl"),
            ))

            return response

        # Short ポジションの決済
        elif close_action == "short":
            data = {"shortUnits": "ALL"}
            request = positions.PositionClose(accountID=OANDA_ACCOUNT_ID, instrument=instrument, data=data)
            response = client.request(request)

            print("position close: {} at {}. pl: {}".format(
                response.get("shortOrderFillTransaction").get("units"),
                response.get("shortOrderFillTransaction").get("price"),
                response.get("shortOrderFillTransaction").get("pl"),
            ))

            return response
        
        else:
            raise Exception("ポジションを決済できませんでした")
        
    except Exception as e:
        print("Error:", str(e))
        return {
            'statusCode': 500,
            'body': 'Error Position Closing'
        }

# Lambdaハンドラー関数
def lambda_handler(event, context):
    """ 通貨の強弱を判断し定時実行する
    """
    try:
        esperanto = Esperanto()
        # main_currencies = ["USD_JPY", "EUR_JPY", "GBP_JPY", "AUD_JPY", "NZD_JPY", "EUR_GBP", "EUR_USD", 
        # "EUR_AUD", "EUR_NZD", "GBP_USD", "GBP_AUD", "GBP_NZD", "AUD_USD", "AUD_NZD", "NZD_USD"]

        price_map = {}
        for currency in esperanto.main_currencies:
            price_map[currency] = get_price(currency)

        esperanto_result = esperanto.calc_esperanto_ratio(price_map, "JPY", "USD", "EUR")
        print(f"{esperanto_result=}")

        # 結果に基づき long を発注
        for long_position_pair in esperanto.long_position:
            # TODO: 発注 unit 数の平準化（証拠金ベースで計算）
            buy_units = 10000
            response_buy = place_order(buy_units, instrument=long_position_pair)
            print("Buy order response:", response_buy)

        for short_position_pair in esperanto.short_position:
            # TODO: 発注 unit 数の平準化（証拠金ベースで計算）
            short_units = -10000
            response_sell = place_order(short_units, instrument=short_position_pair)
            print("Sell order response:", response_sell)

        # # TODO: 決済条件の整理
        # if body["orderAction"] == "buy" and body["orderContracts"] == "200"\
        #       or "決済" in body["comment"]:
        #     position_close("short", 100)
        # elif body["orderAction"] == "sell" and body["orderContracts"] == "200"\
        #       or "決済" in body["comment"]:
        #     position_close("long", 100)

        return {
            'statusCode': 200,
            'body': f'Orders placed successfully'
        }

    except Exception as e:
        print("Error:", str(e))
        return {
            'statusCode': 500,
            'body': 'Error placing orders'
        }

# ローカルテスト
if __name__ == "__main__":
    lambda_handler(None, None)