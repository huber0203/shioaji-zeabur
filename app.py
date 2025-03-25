from flask import Flask, request
import shioaji as sj
import json
import logging
import os
import socket
import sys

app = Flask(__name__)

# 設置日誌，寫入 /tmp/shioaji.log
logger = logging.getLogger('shioaji')
logger.setLevel(logging.INFO)
handler = logging.FileHandler('/tmp/shioaji.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.handlers = [handler]

# 記錄服務的 IP 位址
try:
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    logger.info(f"Service running on host: {hostname}, IP: {ip_address}")
except Exception as e:
    logger.error(f"Failed to get IP address: {str(e)}")

# 全局變數，用於儲存 Shioaji API 實例
api = None

@app.route('/login', methods=['POST'])
def login():
    global api
    try:
        data = request.get_json()
        if not data:
            error_msg = "Request body is empty"
            logger.error(error_msg)
            return {
                "statusCode": 400,
                "body": json.dumps({"error": error_msg})
            }

        # 從 body 中提取敏感資訊
        api_key = data.get("api_key")
        secret_key = data.get("secret_key")
        ca_path = data.get("ca_path", "/app/Sinopac.pfx")
        ca_password = data.get("ca_password")
        person_id = data.get("person_id")
        simulation_mode = data.get("simulation_mode", False)

        # 檢查必要參數
        missing_params = []
        if not api_key:
            missing_params.append("api_key")
        if not secret_key:
            missing_params.append("secret_key")
        if not simulation_mode:
            if not ca_password:
                missing_params.append("ca_password")
            if not person_id:
                missing_params.append("person_id")

        if missing_params:
            error_msg = f"Missing required parameters: {', '.join(missing_params)}"
            logger.error(error_msg)
            return {
                "statusCode": 400,
                "body": json.dumps({"error": error_msg})
            }

        # 檢查憑證檔案（僅在正式環境需要）
        if not simulation_mode:
            if not os.path.exists(ca_path):
                error_msg = f"CA file not found at {ca_path}"
                logger.error(error_msg)
                return {
                    "statusCode": 500,
                    "body": json.dumps({"error": error_msg})
                }
            logger.info(f"CA file found at {ca_path}")

        logger.info(f"Received login request: api_key={api_key[:4]}****, secret_key={secret_key[:4]}****")

        # 初始化 Shioaji
        logger.info(f"Initializing Shioaji with simulation={simulation_mode}")
        api = sj.Shioaji(simulation=simulation_mode)

        # 啟用憑證（僅在正式環境需要）
        if not simulation_mode:
            logger.info(f"Activating CA with ca_path={ca_path}, person_id={person_id}")
            result = api.activate_ca(
                ca_path=ca_path,
                ca_passwd=ca_password,
                person_id=person_id
            )
            if not result:
                error_msg = "Failed to activate CA"
                logger.error(error_msg)
                return {
                    "statusCode": 500,
                    "body": json.dumps({"error": error_msg})
                }
            logger.info("CA activated successfully")

        # 登入 Shioaji
        logger.info("Logging into Shioaji")
        accounts = api.login(api_key=api_key, secret_key=secret_key)
        logger.info(f"Login successful, accounts: {json.dumps(accounts, default=str)}")

        # 返回結果
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Login successful", "accounts": accounts}, default=str)
        }

    except Exception as e:
        error_msg = f"Error in login: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception traceback: {sys.exc_info()}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": error_msg})
        }

@app.route('/quote', methods=['POST'])
def quote():
    global api
    try:
        data = request.get_json()
        if not data:
            error_msg = "Request body is empty"
            logger.error(error_msg)
            return {
                "statusCode": 400,
                "body": json.dumps({"error": error_msg})
            }

        stock_code = data.get("stock_code", "2330")  # 從 body 中提取 stock_code

        # 檢查 API 是否已初始化
        if api is None:
            error_msg = "Shioaji API not initialized. Please login first."
            logger.error(error_msg)
            return {
                "statusCode": 500,
                "body": json.dumps({"error": error_msg})
            }

        logger.info(f"Received quote request: stock_code={stock_code}")

        # 查詢股票行情
        logger.info(f"Fetching quote for stock_code={stock_code}")
        contract = api.Contracts.Stocks.TSE[stock_code]
        quote = api.quote(contract)
        logger.info(f"Quote fetched successfully: {json.dumps(quote, default=str)}")

        # 返回結果
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Quote fetched", "quote": quote}, default=str)
        }

    except Exception as e:
        error_msg = f"Error in quote: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception traceback: {sys.exc_info()}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": error_msg})
        }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
