import shioaji as sj
import json
import logging
import os

# 設置 Shioaji 日誌路徑為 /tmp/shioaji.log
sj.set_logging_config(
    log_path="/tmp/shioaji.log"
)

def lambda_handler(event, context):
    api = sj.Shioaji(simulation=True)
    api_key = event.get("api_key", "你的API Key")
    secret_key = event.get("secret_key", "你的Secret Key")
    stock_code = event.get("stock_code", "2330")
    api.login(api_key=api_key, secret_key=secret_key)
    contract = api.Contracts.Stocks.TSE[stock_code]
    quote = api.quote(contract)
    return {
        "statusCode": 200,
        "body": json.dumps(quote, default=str)
    }