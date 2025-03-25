from flask import Flask, request
import shioaji as sj
import json
import logging
import os

app = Flask(__name__)

# 設置日誌，寫入 /tmp/shioaji.log
logger = logging.getLogger('shioaji')
logger.setLevel(logging.INFO)
handler = logging.FileHandler('/tmp/shioaji.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.handlers = [handler]

# 從環境變數中讀取敏感資訊
API_KEY = os.getenv("SHIOAJI_API_KEY")
SECRET_KEY = os.getenv("SHIOAJI_SECRET_KEY")
CA_PATH = os.getenv("SHIOAJI_CA_PATH", "/tmp/Sinopac.pfx")
CA_PASSWORD = os.getenv("SHIOAJI_CA_PASSWORD")
PERSON_ID = os.getenv("SHIOAJI_PERSON_ID")

# 檢查環境變數是否存在
missing_vars = []
if not API_KEY:
    missing_vars.append("SHIOAJI_API_KEY")
if not SECRET_KEY:
    missing_vars.append("SHIOAJI_SECRET_KEY")
if not CA_PASSWORD:
    missing_vars.append("SHIOAJI_CA_PASSWORD")
if not PERSON_ID:
    missing_vars.append("SHIOAJI_PERSON_ID")

if missing_vars:
    error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
    logger.error(error_msg)
else:
    # 檢查憑證檔案是否存在
    if not os.path.exists(CA_PATH):
        error_msg = f"CA file not found at {CA_PATH}"
        logger.error(error_msg)
    else:
        logger.info(f"CA file found at {CA_PATH}")

@app.route('/quote', methods=['POST'])
def get_quote():
    try:
        # 檢查環境變數
        if missing_vars:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": f"Missing required environment variables: {', '.join(missing_vars)}"})
            }

        # 檢查憑證檔案
        if not os.path.exists(CA_PATH):
            return {
                "statusCode": 500,
                "body": json.dumps({"error": f"CA file not found at {CA_PATH}"})
            }

        data = request.get_json()
        api_key = data.get("api_key", API_KEY)
        secret_key = data.get("secret_key", SECRET_KEY)
        stock_code = data.get("stock_code", "2330")

        # 初始化 Shioaji（正式環境）
        api = sj.Shioaji(simulation=False)

        # 啟用憑證
        result = api.activate_ca(
            ca_path=CA_PATH,
            ca_passwd=CA_PASSWORD,
            person_id=PERSON_ID
        )
        if not result:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Failed to activate CA"})
            }

        # 登入 Shioaji
        api.login(api_key=api_key, secret_key=secret_key)

        # 查詢股票行情
        contract = api.Contracts.Stocks.TSE[stock_code]
        quote = api.quote(contract)

        # 返回結果
        return {
            "statusCode": 200,
            "body": json.dumps(quote, default=str)
        }

    except Exception as e:
        # 錯誤處理
        logger.error(f"Error in get_quote: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
