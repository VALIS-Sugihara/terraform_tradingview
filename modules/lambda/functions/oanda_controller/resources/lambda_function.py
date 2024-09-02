import json
import os
import oandapyV20
import oandapyV20.endpoints
from oandapyV20.endpoints import orders, positions, accounts, pricing


# OANDAのAPI設定
OANDA_ACCOUNT_ID = os.environ["OANDA_ACCOUNT_ID"]
OANDA_API_KEY = os.environ["OANDA_RESTAPI_TOKEN"]
OANDA_API_URL = 'https://api-fxpractice.oanda.com'  # デモアカウントの場合。ライブアカウントの場合は'https://api-fxtrade.oanda.com'

# OANDAのAPIクライアントを設定
client = oandapyV20.API(access_token=OANDA_API_KEY)

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
    """
    event={
        'version': '2.0', 
        'routeKey': '$default', 
        'rawPath': '/', 
        'rawQueryString': '', 
        'headers': {'x-amzn-tls-cipher-suite': 'TLS_AES_128_GCM_SHA256', 
        'content-length': '165', 
        'x-amzn-tls-version': 'TLSv1.3', 
        'x-amzn-trace-id': 'Root=1-66b05b28-1a95b645045801cb142b376f', 
        'x-forwarded-proto': 'https', 
        'host': 'v5ba2svhrvpljegyacgramay6a0sgpqe.lambda-url.ap-northeast-1.on.aws', 
        'x-forwarded-port': '443', 
        'content-type': 'text/plain; charset=utf-8', 
        'x-forwarded-for': '34.212.75.30', 
        'accept-encoding': 'gzip', 
        'user-agent': 'Go-http-client/1.1'}, 
        'requestContext': {'accountId': 'anonymous', 
        'apiId': 'v5ba2svhrvpljegyacgramay6a0sgpqe', 
        'domainName': 'v5ba2svhrvpljegyacgramay6a0sgpqe.lambda-url.ap-northeast-1.on.aws', 
        'domainPrefix': 'v5ba2svhrvpljegyacgramay6a0sgpqe', 
        'http': {
            'method': 'POST', 
            'path': '/', 
            'protocol': 'HTTP/1.1', 
            'sourceIp': '34.212.75.30', 
            'userAgent': 'Go-http-client/1.1'
        }, 
        'requestId': 'a7e64efd-ec07-4737-a2a6-2ca90581002f', 
        'routeKey': '$default', 
        'stage': '$default', 
        'time': '05/Aug/2024:04:55:04 +0000', 
        'timeEpoch': 1722833704578}, 
        'body': 'Squeeze Momentum Strategy [vls] (,100,20,2,20, 1.5): USDJPY で buy @ 100 の注文が約定しました。新しいストラテジーポジションは 0 です', 
        'isBase64Encoded': False
    }
    """
    print(f"{event=}")
    # print(f"{context=}")
    try:
        body = json.loads(event["body"]) if type(event["body"]) is str else event["body"]
        """
        body: {
            "title": "Chandelier Exit Strategy",
            "ticker": {{ticker}},
            "orderAction": {{strategy.order.action}} : sell | buy,
            "orderContracts": {{strategy.order.contracts}},
            "positionSize": {{strategy.position_size}},
            "comment": {{strategy.order.comment}},
            "__origin__": "__trading_view__"
        }
        """
        print(f"{body=}")

        # TODO: AuthCheck
        if body["__origin__"] != "__trading_view__":
            raise Exception("*** 不正なアクセスの可能性があります ***")

        stop_loss_pips = 10  # 未使用
        take_profit_pips = 20  # 未使用
        if body["orderAction"] == "buy":
            # 例: 1000ユニットを買い
            # buy_units = 1000
            # TODO: unit を計算（複利対応）
            buy_units = 10000
            response_buy = place_order(buy_units, stop_loss_pips=stop_loss_pips, take_profit_pips=take_profit_pips)
            print("Buy order response:", response_buy)

        elif body["orderAction"] == "sell":
            # 例: 1000ユニットを売り
            # sell_units = -1000
            # TODO: unit を計算（複利対応）
            sell_units = -10000
            response_sell = place_order(sell_units, stop_loss_pips=stop_loss_pips, take_profit_pips=take_profit_pips)
            print("Sell order response:", response_sell)

        else:
            raise Exception("orderAction が指定されていません")
        
        # TODO: 決済条件の整理
        if body["orderAction"] == "buy" and body["orderContracts"] == "200"\
              or "決済" in body["comment"]:
            position_close("short", 100)
        elif body["orderAction"] == "sell" and body["orderContracts"] == "200"\
              or "決済" in body["comment"]:
            position_close("long", 100)

        return {
            'statusCode': 200,
            'body': f'{body["orderAction"]} Orders placed successfully'
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