from flask import Flask, request
import shioaji as sj
import json
import logging
import os

app = Flask(__name__)

# 手動配置 Shioaji 的日誌
logger = logging.getLogger('shioaji')
logger.setLevel(logging.INFO)
handler = logging.FileHandler('/tmp/shioaji.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.handlers = [handler]

@app.route('/quote', methods=['POST'])
def get_quote():
    data = request.get_json()
    api = sj.Shioaji(simulation=False)
    api_key = data.get("api_key", "你的API Key")
    secret_key = data.get("secret_key", "你的Secret Key")
    stock_code = data.get("stock_code", "2330")
    api.login(api_key=api_key, secret_key=secret_key)
    contract = api.Contracts.Stocks.TSE[stock_code]
    quote = api.quote(contract)
    return {
        "statusCode": 200,
        "body": json.dumps(quote, default=str)
    }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
