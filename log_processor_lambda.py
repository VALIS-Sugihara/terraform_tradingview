import json
import boto3
import os
import base64
import gzip

sns = boto3.client("sns")

INFO_FILTER_NAME = os.environ["INFO_FILTER_NAME"]
ERROR_FILTER_NAME = os.environ["ERROR_FILTER_NAME"]
INFO_SNS_TOPIC_ARN = os.environ["INFO_SNS_TOPIC_ARN"]
ERROR_SNS_TOPIC_ARN = os.environ["ERROR_SNS_TOPIC_ARN"]


def lambda_handler(event, context):
    # base64 デコード
    decoded_data = base64.b64decode(event["awslogs"]["data"])
    # gzip 解凍
    decompressed_data = gzip.decompress(decoded_data)
    json_data = json.loads(decompressed_data)
    """
    json_data={
        'messageType': 'DATA_MESSAGE',
        'owner': '291357645530',
        'logGroup': '/aws/lambda/vls-trdvw-demo-accumulation-controller-function',
        'logStream': '2024/10/01/[$LATEST]ec63d56d0b0c459781c8d83975617df6',
        'subscriptionFilters': ['test'],
        'logEvents': [
            {
                'id': '38530823446187000737950677317228421677701013436713467905',
                'timestamp': 1727781879178,
                'message': '[INFO]\t2024-10-01T11:24:39.178Z\t1a595bbd-4b24-44d5-91a5-d75b677b7def\tStarting ...\n'
            }
        ]
    }
    """
    for log_event in json_data["logEvents"]:
        message = log_event["message"]

        if INFO_FILTER_NAME in json_data["subscriptionFilters"]:
            sns.publish(
                TopicArn=INFO_SNS_TOPIC_ARN, Message=message, Subject=INFO_FILTER_NAME
            )
        elif ERROR_FILTER_NAME in json_data["subscriptionFilters"]:
            sns.publish(
                TopicArn=ERROR_SNS_TOPIC_ARN, Message=message, Subject=ERROR_FILTER_NAME
            )

    return {"statusCode": 200, "body": json.dumps("Log processed successfully")}
