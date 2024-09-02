def lambda_handler(event, 
context):
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
    print(f"{context=}")
    return "Hello from Lambda"
