import json
import os
import oandapyV20
from oandapyV20.endpoints import orders, positions, accounts, pricing
from typing import NamedTuple, Dict, List, Tuple
import collections

# OANDAのAPI設定
OANDA_ACCOUNT_ID = os.environ["OANDA_ACCOUNT_ID"]
OANDA_API_KEY = os.environ["OANDA_RESTAPI_TOKEN"]
OANDA_API_URL = "https://api-fxpractice.oanda.com"  # デモアカウントの場合。ライブアカウントの場合は'https://api-fxtrade.oanda.com'

# OANDAのAPIクライアントを設定
client = oandapyV20.API(access_token=OANDA_API_KEY)


class Price:
    """価格に関する情報を扱うクラス"""

    class Prices(NamedTuple):
        bid: float  # 売値
        ask: float  # 買値
        mid: float  # 中値

    PriceMap = Dict[str, Prices]
    # PriceMap = Dict[str, float]
    price_map: PriceMap
    main_currency_pairs = (
        "USD_JPY",
        "EUR_JPY",
        "AUD_JPY",
        "GBP_JPY",
        "NZD_JPY",
        "CAD_JPY",
        "CHF_JPY",
        "ZAR_JPY",
        "EUR_USD",
        "GBP_USD",
        "NZD_USD",
        "AUD_USD",
        "USD_CHF",
        "EUR_CHF",
        "GBP_CHF",
        "EUR_GBP",
        "AUD_NZD",
        "AUD_CAD",
        "AUD_CHF",
        "CAD_CHF",
        "EUR_AUD",
        "EUR_CAD",
        "EUR_DKK",
        "EUR_NOK",
        "EUR_NZD",
        "EUR_SEK",
        "GBP_AUD",
        "GBP_CAD",
        "GBP_NZD",
        "NZD_CAD",
        "NZD_CHF",
        "USD_CAD",
        "USD_DKK",
        "USD_NOK",
        "USD_SEK",
        "AUD_HKD",
        "AUD_SGD",
        "CAD_HKD",
        "CAD_SGD",
        "CHF_HKD",
        "CHF_ZAR",
        "EUR_CZK",
        "EUR_HKD",
        "EUR_HUF",
        "EUR_PLN",
        "EUR_SGD",
        "EUR_TRY",
        "EUR_ZAR",
        "GBP_HKD",
        "GBP_PLN",
        "GBP_SGD",
        "GBP_ZAR",
        "HKD_JPY",
        "NZD_HKD",
        "NZD_SGD",
        "SGD_CHF",
        "SGD_JPY",
        "TRY_JPY",
        "USD_CNH",
        "USD_CZK",
        "USD_HKD",
        "USD_HUF",
        "USD_MXN",
        "USD_PLN",
        "USD_SGD",
        "USD_THB",
        "USD_TRY",
        "USD_ZAR",
    )
    main_currencies = (
        "USD",
        "JPY",
        "GBP",
        "AUD",
        "NZD",
        "EUR",
        "CAD",
        "CNH",
        "CHF",
        "CZK",
        "DKK",
        "NOK",
        "SEK",
        "HUF",
        "PLN",
        "HKD",
        "SGD",
        "ZAR",
        "MXN",
        "THB",
    )

    def __init__(self):
        self.price_map = {}

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
            str: A greeting message.
        """
        # 価格情報を取得するエンドポイントの設定
        params = {"instruments": instruments}
        pricing_info = pricing.PricingInfo(
            accountID=OANDA_ACCOUNT_ID, params=params
        )

        # リクエストを送信して現在価格を取得
        try:
            response = client.request(pricing_info)
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


class Esperanto:
    """各通貨を統一的に扱うためのクラス
    世界共通語として発明された ESPERANTO をモチーフとして命名
    """

    class EsperantoResult(NamedTuple):
        combination_name: str = ""  # 組み合わせ名  ex)USD_JPY_EUR
        esperanto_ratio: float = (
            1  # 相場の何割安か. 0.5 であれば 50%Off と同じ扱い
        )
        long_positions: list = (
            []
        )  # Long するべき通貨ペア. 2つ出るはずなので list で ["USD_JPY", "EUR_JPY"] のような形
        short_positions: list = (
            []
        )  # short するべき通貨ぺあ. 1つのはずなので "EUR_USD" の形
        # Name: str = "Alice"  # デフォルト値をつける時はないものの定義のあとであれば OK

    # vehicle_currencies = ["USD", "JPY", "GBP", "AUD", "NZD", "EUR"]  # 単一媒介通貨名リスト
    vehicle_currencies = [
        "USD",
        "JPY",
        "GBP",
        "AUD",
        "NZD",
        "EUR",
        "CAD",
        "CNH",
        "CHF",
        "CZK",
        "DKK",
        "NOK",
        "SEK",
        "HUF",
        "PLN",
        "HKD",
        "SGD",
        "ZAR",
        "MXN",
        "THB",
    ]
    result: EsperantoResult = EsperantoResult()
    highest_result: EsperantoResult = (
        EsperantoResult()
    )  # 最も割高な組み合わせ 1以上の比率を持つ
    lowest_result: EsperantoResult = (
        EsperantoResult()
    )  # 最も割安な組み合わせ 1以下の比率を持つ
    # esperanto_ratio: float = None  # 相場の何割安か. 0.5 であれば 50%Off と同じ扱い
    long_positions: list = []  # Long するべき通貨ペア
    short_positions: list = []  # Short するべき通貨ペア
    price: Price = None  # Price インスタンス

    def __init__(self, price: Price) -> None:
        # 初期化を行う
        self.result = self.EsperantoResult()
        self.highest_result = self.EsperantoResult()
        self.lowest_result = self.EsperantoResult()
        # self.esperanto_ratio = 0
        self.long_positions = []
        self.short_positions = []
        self.price = price

    def calc_esperanto_ratio(
        self,
        price_map: dict,
        first_currency: str,
        second_currency: str,
        vehicle_currency: str,
    ):
        """３通貨間で割安な通貨ペアを計算し、long/short をそれぞれ取るべき通貨ペアを導き出す関数
            世界共通語として発明された ESPERANTO をモチーフとして命名
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
            Ptn.3: 媒介通貨 240812
                orange_apple = 5
                melon_apple = 100
                melon_orange = 10  # 本来は melon_orange = 20
                melon_orange が割安であると感じるのは、orange > melon > apple > orange と一巡した際に orange が２倍になっているからである.
                これを apple という媒介通貨を経たルートだからだと考える.
                仮に orange_banana = 10, melon_banana = 100 で orange > melon > banana > orange というルートの際には、
                100 banana = 10 orange となり、変わらないため手数料を考えるとすべきでない取引となる.
                まとめると、媒介通貨によって変わるため、first_currency と second_currency をターゲットに、どの vehicle_currency のルートをとるべきかという設計に変更する.
            考察） 240815
                strtg1:
                orange > melon > apple > orange と一巡した際に orange が２倍になっていることからの上記の戦略.
                しかし、実際に検証してみるとあまり有益でない結果となった.
                Orange高/Melon安 には melon_orange が下降トレンドなのに long を取っているのではないかと仮定する
                strtg2:
                melon_orange が割安である時に、orange > melon > apple > orange と動かすとあまり有益でない結果であることが検証により分かった.
                melon_orange = 10 の時は、Orange高/Melon安であるため、Orange を集中的に買う戦略へ変更してみる.
                つまり、melon_orange and apple が EsperantoLongの時には、
                melon_orange-short, orange_apple-long この時に、Melon安Orange高から誘発される連携相場は、Melon安/Apple高 or Orange高/Apple安 だと仮定し、
                melon_apple 間は melon_apple-short を取ることにする
                strtg3:
                chatgpt によると strtgy1 の考え方で概ね正しいようなので一旦戻すこととする
        Args:
            price_map (dict): 通過ペアごとの価格の map. ex)
            first_currency (str): 検査したい通貨,ペアの 1つ目 ex) orange, JPY
            second_currency (str): 検査したい通貨,ペアの 2つ目 ex) melon, USD
            vehicle_currency (str): 経由することで差益を期待する通貨名 ex) apple, banana, EUR
        Returns:
            EsperantoResult (NamedTuple):
                相場の何割安か. 0.50 であれば 50%Off と同じ扱い
        """

        # target_pair_price = price_map.get(f"{second_currency}_{first_currency}", 1 / float(price_map.get(f"{first_currency}_{second_currency}", 1)))  # ない時は逆数を返す
        # v_first_pair_price = price_map.get(f"{second_currency}_{vehicle_currency}", 1 / float(price_map.get(f"{vehicle_currency}_{second_currency}", 1)))  # ない時は逆数を返す
        # v_second_pair_price = price_map.get(f"{first_currency}_{vehicle_currency}", 1 / float(price_map.get(f"{vehicle_currency}_{first_currency}", 1)))  # ない時は逆数を返す
        target_pair_price = self.price.get_price_from_pricemap(
            instruments=f"{second_currency}_{first_currency}"
        )
        v_first_pair_price = self.price.get_price_from_pricemap(
            instruments=f"{second_currency}_{vehicle_currency}"
        )
        v_second_pair_price = self.price.get_price_from_pricemap(
            instruments=f"{first_currency}_{vehicle_currency}"
        )

        mid_esperanto_ratio: float = target_pair_price / (
            v_first_pair_price / v_second_pair_price
        )

        # flag = third_pair_price < (second_pair_price / first_pair_price)

        # 中値で計算した後 bid/ask を考慮しそれでも LONG/SHORT か篩にかける
        if mid_esperanto_ratio < 1:
            print(
                "組み合わせ",
                f"{first_currency}_{second_currency}_{vehicle_currency} MAYBE LONG",
            )
            print(
                "実効レート: ",
                target_pair_price,
                v_first_pair_price / v_second_pair_price,
            )
            # LONG であることが分かったため再計算
            target_pair_price = self.price.get_price_from_pricemap(
                instruments=f"{second_currency}_{first_currency}",
                bid_ask_mid="ask",
            )
            v_first_pair_price = self.price.get_price_from_pricemap(
                instruments=f"{second_currency}_{vehicle_currency}",
                bid_ask_mid="bid",
            )
            v_second_pair_price = self.price.get_price_from_pricemap(
                instruments=f"{first_currency}_{vehicle_currency}",
                bid_ask_mid="ask",
            )
            esperanto_ratio: float = target_pair_price / (
                v_first_pair_price / v_second_pair_price
            )
            # TODO: 閾値判定, 中値判断をやめる
            if (
                esperanto_ratio < 1
            ):  # 本来相場より割安であるため Long が 2つに Short が 1つ
                print(
                    "組み合わせ",
                    f"{first_currency}_{second_currency}_{vehicle_currency} Esperanto LONG",
                )
                print(
                    "実効レート: ",
                    target_pair_price,
                    v_first_pair_price / v_second_pair_price,
                )
                # strtgy1. melon_orange - long, melon_apple - short, orange_apple - long
                # result = self.EsperantoResult(esperanto_ratio, [f"{second_currency}_{first_currency}", f"{first_currency}_{vehicle_currency}"], [f"{second_currency}_{vehicle_currency}"])
                # strtgy2. melon_orange-short, orange_apple-long, melon_apple-short
                # result = self.EsperantoResult(f"{first_currency}_{second_currency}_{vehicle_currency}", esperanto_ratio, [f"{first_currency}_{vehicle_currency}"], [f"{second_currency}_{first_currency}", f"{second_currency}_{vehicle_currency}"])
                # strtgy3. == strtgy1 に戻す & bid/ask レートを考慮してみる
                result = self.EsperantoResult(
                    f"{first_currency}_{second_currency}_{vehicle_currency}",
                    esperanto_ratio,
                    [
                        f"{second_currency}_{first_currency}",
                        f"{first_currency}_{vehicle_currency}",
                    ],
                    [f"{second_currency}_{vehicle_currency}"],
                )
                # ひとまず self.result に格納する
                self.result = result
                # self.change_pair()
                # return self.EsperantoResult(esperanto_ratio, self.long_positions, self.short_positions)
            else:
                print(
                    "組み合わせ",
                    f"{first_currency}_{second_currency}_{vehicle_currency} NOT FLAGGED",
                )
                print(
                    "実効レート: ",
                    target_pair_price,
                    v_first_pair_price / v_second_pair_price,
                )
                result = self.EsperantoResult(
                    f"{first_currency}_{second_currency}_{vehicle_currency}",
                    esperanto_ratio,
                )
                # ひとまず self.result に格納する
                self.result = result
                # return result
        elif (
            mid_esperanto_ratio > 1
        ):  # 本来相場より割高であるため Short が 2つに Long が 1つ？
            print(
                "組み合わせ",
                f"{first_currency}_{second_currency}_{vehicle_currency} MAYBE SHORT",
            )
            print(
                "実効レート: ",
                target_pair_price,
                v_first_pair_price / v_second_pair_price,
            )
            target_pair_price = self.price.get_price_from_pricemap(
                instruments=f"{second_currency}_{first_currency}",
                bid_ask_mid="bid",
            )
            v_first_pair_price = self.price.get_price_from_pricemap(
                instruments=f"{second_currency}_{vehicle_currency}",
                bid_ask_mid="ask",
            )
            v_second_pair_price = self.price.get_price_from_pricemap(
                instruments=f"{first_currency}_{vehicle_currency}",
                bid_ask_mid="bid",
            )
            esperanto_ratio: float = target_pair_price / (
                v_first_pair_price / v_second_pair_price
            )
            if esperanto_ratio > 1:
                print(
                    "組み合わせ",
                    f"{first_currency}_{second_currency}_{vehicle_currency} Esperanto SHORT",
                )
                print(
                    "実効レート: ",
                    target_pair_price,
                    v_first_pair_price / v_second_pair_price,
                )
                # strtgy1. melon_orange - short, melon_apple - long, orange_apple - short
                # result = self.EsperantoResult(esperanto_ratio, [f"{second_currency}_{vehicle_currency}"], [f"{second_currency}_{first_currency}", f"{first_currency}_{vehicle_currency}"])
                # strtgy2. melon_orange-long, orange_apple-short, melon_apple-long
                # result = self.EsperantoResult(f"{first_currency}_{second_currency}_{vehicle_currency}", esperanto_ratio, [f"{second_currency}_{first_currency}", f"{second_currency}_{vehicle_currency}"], [f"{first_currency}_{vehicle_currency}"])
                # strtgy3. == strtgy1 に戻す & bid/ask レートを考慮してみる
                # SHORT であることが分かったため再計算
                result = self.EsperantoResult(
                    f"{first_currency}_{second_currency}_{vehicle_currency}",
                    esperanto_ratio,
                    [f"{second_currency}_{vehicle_currency}"],
                    [
                        f"{second_currency}_{first_currency}",
                        f"{first_currency}_{vehicle_currency}",
                    ],
                )
                # ひとまず self.result に格納する
                self.result = result
                # self.change_pair()
                # return self.EsperantoResult(esperanto_ratio, self.long_positions, self.short_positions)
            else:
                print(
                    "組み合わせ",
                    f"{first_currency}_{second_currency}_{vehicle_currency} NOT FLAGGED",
                )
                print(
                    "実効レート: ",
                    target_pair_price,
                    v_first_pair_price / v_second_pair_price,
                )
                result = self.EsperantoResult(
                    f"{first_currency}_{second_currency}_{vehicle_currency}",
                    esperanto_ratio,
                )
                # ひとまず self.result に格納する
                self.result = result
                # return result
        else:
            print(
                "組み合わせ",
                f"{first_currency}_{second_currency}_{vehicle_currency} NOT FLAGGED",
            )
            print(
                "実効レート: ",
                target_pair_price,
                v_first_pair_price / v_second_pair_price,
            )
            result = self.EsperantoResult(
                f"{first_currency}_{second_currency}_{vehicle_currency}",
                esperanto_ratio,
            )
            # ひとまず self.result に格納する
            self.result = result
            # return result

    def evaluate_esperanto_result(self):
        """結果を評価する関数
        閾値の判定や、最も高い/安い組み合わせを更新する
        """
        # 基準値の設定  fiveNine 以下以上で仮に設定
        baseline = 0.00001
        # 現結果の long/short の判定
        flag = (
            "LONG"
            if self.result.esperanto_ratio < 1
            else "SHORT" if self.result.esperanto_ratio > 1 else None
        )
        if flag == "LONG" and self.result.esperanto_ratio + baseline < 1:
            # if self.lowest_result is None or \
            #     self.result.esperanto_ratio < self.lowest_result.esperanto_ratio:  # 下回ったら更新
            #     self.lowest_result = self.result
            # sim1: 基準値以下のものは全て格納してみる
            self.long_positions += self.result.long_positions
            self.short_positions += self.result.short_positions
        elif flag == "SHORT" and self.result.esperanto_ratio - baseline > 1:
            # if self.highest_result is None or \
            #     self.result.esperanto_ratio > self.highest_result.esperanto_ratio:  # 上回ったら更新
            #     self.highest_result = self.result
            # sim1: 基準値以上のものは全て格納してみる
            self.long_positions += self.result.long_positions
            self.short_positions += self.result.short_positions

    def set_position(self):
        """最終的な結果を long/short positions へ格納する関数"""
        # sim1: 既に格納済みのため CO
        self.long_positions = (
            self.highest_result.long_positions
            + self.lowest_result.long_positions
        )
        self.short_positions = (
            self.highest_result.short_positions
            + self.lowest_result.short_positions
        )
        self.change_pair()  # 組み合わせの是正
        # sim2: highest と lowest で ２つ同じポジションが入ることが多い. 試しにその２つのもののみ購入することとする
        # c = collections.Counter(self.long_positions)
        # if c.most_common()[0][1] >= 2:  # 2回以上なら
        #     self.long_positions = [c.most_common()[0][0]]
        # else:
        #     self.long_positions = []
        # c = collections.Counter(self.short_positions)
        # if c.most_common()[0][1] >= 2:  # 2回以上なら
        #     self.short_positions = [c.most_common()[0][0]]
        # else:
        #     self.short_positions = []

    def change_pair(self):
        """通貨ペアとポジションを是正するための関数
        self.long_positions = ["JPY_USD"] となっていた場合、
        self.short_positions = ["USD_JPY"] へと訂正する
        """
        # JPY_USD が格納されていた場合 long<->short へ正しいペアを入れ直し元を削除する
        for position_name in self.long_positions[:]:
            flag = position_name in Price.main_currency_pairs
            if flag is False:
                l, r = position_name.split("_")[0], position_name.split("_")[1]
                correct_position_name = f"{r}_{l}"
                self.short_positions.append(correct_position_name)
                self.long_positions.remove(position_name)

        for position_name in self.short_positions[:]:
            flag = position_name in Price.main_currency_pairs
            if flag is False:
                l, r = position_name.split("_")[0], position_name.split("_")[1]
                correct_position_name = f"{r}_{l}"
                self.long_positions.append(correct_position_name)
                self.short_positions.remove(position_name)


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


# 証拠金を取得する関数
def get_account_margin():
    endpoint = accounts.AccountSummary(OANDA_ACCOUNT_ID)
    response = client.request(endpoint)
    margin_available = float(response["account"]["marginAvailable"])
    return margin_available


# マーケットオーダーを送信する関数
def place_order(
    units, instrument="USD_JPY", stop_loss_pips=10, take_profit_pips=20
):
    # 現在の価格を取得
    endpoint = pricing.PricingInfo(
        accountID=OANDA_ACCOUNT_ID, params={"instruments": instrument}
    )
    response = client.request(endpoint)
    current_price = float(response["prices"][0]["closeoutAsk"])

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
def position_close(
    close_action,
    units,
    instrument="USD_JPY",
    stop_loss_pips=10,
    take_profit_pips=20,
):
    try:
        # Long ポジションの決済
        if close_action == "long":
            data = {"longUnits": "ALL"}
            request = positions.PositionClose(
                accountID=OANDA_ACCOUNT_ID, instrument=instrument, data=data
            )
            response = client.request(request)

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
                accountID=OANDA_ACCOUNT_ID, instrument=instrument, data=data
            )
            response = client.request(request)

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
    """通貨の強弱を判断し定時実行する"""
    try:
        # プライスマップを取得
        price = Price()
        price.generate_price_map()

        esperanto = Esperanto(price=price)
        # main_currencies = ["USD_JPY", "EUR_JPY", "GBP_JPY", "AUD_JPY", "NZD_JPY", "EUR_GBP", "EUR_USD",
        # "EUR_AUD", "EUR_NZD", "GBP_USD", "GBP_AUD", "GBP_NZD", "AUD_USD", "AUD_NZD", "NZD_USD"]

        # 通貨の組み合わせを決めてループ
        # esperanto比率を計算する
        for i in range(len(esperanto.vehicle_currencies)):
            for j in range(i + 1, len(esperanto.vehicle_currencies)):
                for k in range(j + 1, len(esperanto.vehicle_currencies)):
                    try:
                        A, B, C = (
                            esperanto.vehicle_currencies[i],
                            esperanto.vehicle_currencies[j],
                            esperanto.vehicle_currencies[k],
                        )
                        # A_B = get_rate(f"{A}_{B}")
                        # B_C = get_rate(f"{B}_{C}")
                        # C_A = get_rate(f"{C}_{A}")

                        # if A_B and B_C and C_A:
                        #     ratio = calculate_esperanto_ratio(A_B, B_C, C_A)
                        #     key = f"{A}_{B}_{C} EsperantoRatio"
                        #     ratios[key] = ratio
                        esperanto.calc_esperanto_ratio(
                            price.price_map, A, B, C
                        )
                        esperanto.evaluate_esperanto_result()
                        print(f"{esperanto.result=}")
                    except Exception:
                        # print(f"{A}, {B}, {C} の組み合わせはありません")
                        continue
        print(f"{esperanto.lowest_result=}")
        print(f"{esperanto.highest_result=}")
        esperanto.set_position()
        print(f"{esperanto.long_positions=}")
        print(f"{esperanto.short_positions=}")

        # 一番高い比率のものをそれぞれ選択
        # 結果に基づき long を発注
        LEVERAGE = 30  # 30倍固定
        # TODO: 証拠金の特定パーセントにて運用など. 一旦 30,000円で固定してみる
        # 証拠金計算) margin_baseline = price_map[long_position_pair] * buy_units / LEVERAGE
        for long_position_pair in esperanto.long_positions:
            # ptn1: 証拠金額を同一に設定するパターン
            # margin_baseline = 30000  # 変数再セット
            # right = long_position_pair.split("_")[1]  # _で分離した右側を取得
            # if right != "JPY":  # JPY 以外の場合は証拠金を右側の通貨へ換算する
            #     margin_baseline /= price.price_map[f"{right}_JPY"]
            # # TODO: 発注 unit 数の平準化（証拠金ベースで計算）
            # buy_units = int((margin_baseline * LEVERAGE) / price.price_map[long_position_pair])
            # # buy_units = 10000

            # ptn2: 同一 pips で同一の損益額となるよう units 数を調整するパターン（最大 2% の 30,000円と仮にしたいので margin=1,500,000 で固定してみる）
            buy_units = calculate_units(
                entry_price=price.price_map[long_position_pair],
                margin=1500000,
                risk_percentage=0.001,
                stop_loss_pips=30,
            )
            print(f"{buy_units=}")
            response_buy = place_order(
                buy_units, instrument=long_position_pair
            )
            print("Buy order response:", response_buy)

        for short_position_pair in esperanto.short_positions:
            # ptn1: 証拠金額を同一に設定するパターン
            # margin_baseline = 30000  # 変数再セット
            # right = short_position_pair.split("_")[1]  # _で分離した右側を取得
            # if right != "JPY":  # JPY 以外の場合は証拠金を右側の通貨へ換算する
            #     margin_baseline /= price.price_map[f"{right}_JPY"]
            # # TODO: 発注 unit 数の平準化（証拠金ベースで計算）
            # short_units = int(-1 * ((margin_baseline * LEVERAGE) / price.price_map[short_position_pair]))
            # # short_units = -10000

            # ptn2: 同一 pips で同一の損益額となるよう units 数を調整するパターン（最大 2% の 30,000円と仮にしたいので margin=1,500,000 で固定してみる）
            short_units = calculate_units(
                entry_price=price.price_map[short_position_pair],
                margin=1500000,
                risk_percentage=0.001,
                stop_loss_pips=30,
            )
            print(f"{short_units=}")
            response_sell = place_order(
                short_units, instrument=short_position_pair
            )
            print("Sell order response:", response_sell)

        # # TODO: 決済条件の整理
        # if body["orderAction"] == "buy" and body["orderContracts"] == "200"\
        #       or "決済" in body["comment"]:
        #     position_close("short", 100)
        # elif body["orderAction"] == "sell" and body["orderContracts"] == "200"\
        #       or "決済" in body["comment"]:
        #     position_close("long", 100)

        return {"statusCode": 200, "body": f"Orders placed successfully"}

    except Exception as e:
        print("Error:", str(e))
        return {"statusCode": 500, "body": "Error placing orders"}


# ローカルテスト
if __name__ == "__main__":
    lambda_handler(None, None)
