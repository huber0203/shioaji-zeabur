from flask import Flask, request
import shioaji as sj
import json
import logging
import os
import socket
import sys
import base64
from datetime import datetime, timedelta

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

# 測試網路連線
def test_network():
    try:
        socket.create_connection(("www.sinopac.com", 80), timeout=5)
        logger.info("Network connection to Sinopac server is OK")
    except Exception as e:
        logger.error(f"Network connection failed: {str(e)}")

test_network()

# 從環境變數讀取憑證檔案（如果以 base64 形式提供）
ca_path = "/app/Sinopac.pfx"
ca_file_base64 = os.getenv("CA_FILE_BASE64")
if ca_file_base64:
    try:
        with open(ca_path, "wb") as f:
            f.write(base64.b64decode(ca_file_base64))
        logger.info(f"CA file written to {ca_path} from environment variable")
    except Exception as e:
        logger.error(f"Failed to write CA file from base64: {str(e)}")

# 全局變數，用於儲存 Shioaji API 實例
api = None

# 健康檢查端點
@app.route('/health', methods=['GET'])
def health():
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Service is healthy"})
    }

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
            file_size = os.path.getsize(ca_path)
            logger.info(f"CA file found at {ca_path}, size: {file_size} bytes")

        logger.info(f"Received login request: api_key={api_key[:4]}****, secret_key={secret_key[:4]}****")

        # 初始化 Shioaji
        logger.info(f"Initializing Shioaji with simulation={simulation_mode}")
        api = sj.Shioaji(simulation=simulation_mode)

        # 啟用憑證（僅在正式環境需要）
        if not simulation_mode:
            logger.info(f"Activating CA with ca_path={ca_path}, person_id={person_id}")
            try:
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
            except Exception as e:
                error_msg = f"Error in activate_ca: {str(e)}"
                logger.error(error_msg)
                return {
                    "statusCode": 500,
                    "body": json.dumps({"error": error_msg})
                }

        # 登入 Shioaji
        logger.info("Logging into Shioaji")
        accounts = api.login(api_key=api_key, secret_key=secret_key)
        logger.info(f"Login successful, accounts: {json.dumps(accounts, default=str)}")

        # 強制下載商品檔
        logger.info("Fetching contracts")
        api.fetch_contracts(contract_download=True)
        logger.info("Contracts fetched successfully")

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
        market = data.get("market", "TSE")  # 從 body 中提取市場（預設 TSE）

        # 檢查 API 是否已初始化
        if api is None:
            error_msg = "Shioaji API not initialized. Please login first."
            logger.error(error_msg)
            return {
                "statusCode": 500,
                "body": json.dumps({"error": error_msg})
            }

        logger.info(f"Received quote request: stock_code={stock_code}, market={market}")

        # 查詢股票行情（根據市場選擇 TSE 或 OTC）
        logger.info(f"Fetching contract for stock_code={stock_code}, market={market}")
        if market == "TSE":
            contract = api.Contracts.Stocks.TSE[stock_code]
        elif market == "OTC":
            contract = api.Contracts.Stocks.OTC[stock_code]
        else:
            error_msg = f"Unsupported market: {market}"
            logger.error(error_msg)
            return {
                "statusCode": 400,
                "body": json.dumps({"error": error_msg})
            }

        # 檢查契約是否有效
        if contract is None:
            error_msg = f"Invalid stock code: {stock_code} in market {market}"
            logger.error(error_msg)
            return {
                "statusCode": 400,
                "body": json.dumps({"error": error_msg})
            }

        # 查詢即時行情快照
        logger.info(f"Fetching snapshot for stock_code={stock_code}")
        snapshots = api.snapshots([contract])  # 即時快照資料
        if not snapshots:  # 檢查是否為空列表
            error_msg = f"No snapshot data available for stock_code={stock_code}. The stock may be suspended or have no recent trades."
            logger.error(error_msg)
            return {
                "statusCode": 404,
                "body": json.dumps({"error": error_msg})
            }

        snapshot = snapshots[0]  # 取第一個元素
        logger.info(f"Snapshot fetched: {json.dumps(snapshot, default=str)}")

        # 返回結果
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Quote fetched", "quote": snapshot}, default=str)
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

@app.route('/kbars', methods=['POST'])
def kbars():
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
        market = data.get("market", "TSE")  # 從 body 中提取市場（預設 TSE）
        timeframe = data.get("timeframe", "1Min")  # K 棒時間框架（預設 1 分鐘）
        minutes = data.get("minutes", 2)  # 查詢前幾分鐘的 K 棒（預設 2 分鐘）

        # 檢查 API 是否已初始化
        if api is None:
            error_msg = "Shioaji API not initialized. Please login first."
            logger.error(error_msg)
            return {
                "statusCode": 500,
                "body": json.dumps({"error": error_msg})
            }

        logger.info(f"Received kbars request: stock_code={stock_code}, market={market}, timeframe={timeframe}, minutes={minutes}")

        # 查詢歷史 K 棒（根據市場選擇 TSE 或 OTC）
        logger.info(f"Fetching contract for stock_code={stock_code}, market={market}")
        if market == "TSE":
            contract = api.Contracts.Stocks.TSE[stock_code]
        elif market == "OTC":
            contract = api.Contracts.Stocks.OTC[stock_code]
        else:
            error_msg = f"Unsupported market: {market}"
            logger.error(error_msg)
            return {
                "statusCode": 400,
                "body": json.dumps({"error": error_msg})
            }

        # 檢查契約是否有效
        if contract is None:
            error_msg = f"Invalid stock code: {stock_code} in market {market}"
            logger.error(error_msg)
            return {
                "statusCode": 400,
                "body": json.dumps({"error": error_msg})
            }

        # 查詢歷史 K 棒
        logger.info(f"Fetching kbars for stock_code={stock_code}")
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=minutes)
        kbars = api.kbars(
            contract=contract,
            start=start_time.strftime("%Y-%m-%d %H:%M:%S"),
            end=end_time.strftime("%Y-%m-%d %H:%M:%S"),
            timeframe=timeframe
        )
        logger.info(f"Kbars fetched: {json.dumps(kbars, default=str)}")

        # 返回結果
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Kbars fetched", "kbars": kbars}, default=str)
        }

    except Exception as e:
        error_msg = f"Error in kbars: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception traceback: {sys.exc_info()}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": error_msg})
        }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
