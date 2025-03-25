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

# 從環境變數中讀取敏感資訊
API_KEY = os.getenv("SHIOAJI_API_KEY")
SECRET_KEY = os.getenv("SHIOAJI_SECRET_KEY")
CA_PATH = os.getenv("SHIOAJI_CA_PATH", "/app/Sinopac.pfx")
CA_PASSWORD = os.getenv("SHIOAJI_CA_PASSWORD")
PERSON_ID = os.getenv("SHIOAJI_PERSON_ID")
SIMULATION_MODE = os.getenv("SHIOAJI_SIMULATION", "False").lower() == "true"

# 檢查環境變數是否存在
missing_vars = []
if not API_KEY:
    missing_vars.append("SHIOAJI_API_KEY")
if not SECRET_KEY:
    missing_vars.append("SHIOAJI_SECRET_KEY")
if not SIMULATION_MODE:  # 正式環境需要額外變數
    if not CA_PASSWORD:
        missing_vars.append("SHIOAJI_CA_PASSWORD")
    if not PERSON_ID:
        missing_vars.append("SHIOAJI_PERSON_ID")

if missing_vars:
    error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
    logger.error(error_msg)

# 檢查憑證檔案是否存在（僅在正式環境需要）
if not SIMULATION_MODE:
    if os.path.exists(CA_PATH):
        logger.info(f"CA file found at {CA_PATH}")
    else:
        logger.error(f"CA file not found at {CA_PATH}")

# 記錄服務的 IP 位址
try:
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    logger.info(f"Service running on host: {hostname}, IP: {ip_address}")
except Exception as e:
    logger.error(f"Failed to get IP address: {str(e)}")

# 全局變數，用於儲存 Shioaji API 實例
api = None

# 啟動時初始化 Shioaji
try:
    logger.info(f"Initializing Shioaji with simulation={SIMULATION_MODE}")
    api = sj.Shioaji(simulation=SIMULATION_MODE)

    # 啟用憑證（僅在正式環境需要）
    if not SIMULATION_MODE:
        logger.info(f"Activating CA with ca_path={CA_PATH}, person_id={PERSON_ID}")
        result = api.activate_ca(
            ca_path=CA_PATH,
            ca_passwd=CA_PASSWORD,
            person_id=PERSON_ID
        )
        if not result:
            error_msg = "Failed to activate CA during startup"
            logger.error(error_msg)
            raise Exception(error_msg)
        logger.info("CA activated successfully during startup")

    # 登入 Shioaji
    logger.info("Logging into Shioaji during startup")
    accounts = api.login(api_key=API_KEY, secret_key=SECRET_KEY)
    logger.info(f"Login successful during startup, accounts: {json.dumps(accounts, default=str)}")

except Exception as e:
    error_msg = f"Failed to initialize Shioaji during startup: {str(e)}"
    logger.error(error_msg)
    logger.error(f"Exception type: {type(e).__name__}")
    logger.error(f"Exception traceback: {sys.exc_info()}")

@app.route('/login', methods=['POST'])
def login():
    try:
        # 檢查環境變數
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logger.error(error_msg)
            return {
                "statusCode": 500,
                "body": json.dumps({"error": error_msg})
            }

        # 檢查 API 是否已初始化
        if api is None:
            error_msg = "Shioaji API not initialized"
            logger.error(error_msg)
            return {
                "statusCode": 500,
                "body": json.dumps({"error": error_msg})
            }

        data = request.get_json()
        api_key = data.get("api_key", API_KEY)
        secret_key = data.get("secret_key", SECRET_KEY)

        logger.info(f"Received login request: api_key={api_key[:4]}****, secret_key={secret_key[:4]}****")

        # 返回已登入的帳戶資訊
        accounts = api.list_accounts()
        logger.info(f"Login successful, accounts: {json.dumps(accounts, default=str)}")

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
    try:
        # 檢查環境變數
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logger.error(error_msg)
            return {
                "statusCode": 500,
                "body": json.dumps({"error": error_msg})
            }

        # 檢查 API 是否已初始化
        if api is None:
            error_msg = "Shioaji API not initialized"
            logger.error(error_msg)
            return {
                "statusCode": 500,
                "body": json.dumps({"error": error_msg})
            }

        data = request.get_json()
        stock_code = data.get("stock_code", "2330")  # 從 body 中提取 stock_code

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
