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
            return {"statusCode": 400, "body": json.dumps({"error": error_msg})}

        api_key = data.get("api_key")
        secret_key = data.get("secret_key")
        ca_path = data.get("ca_path", "/app/Sinopac.pfx")
        ca_password = data.get("ca_password")
        person_id = data.get("person_id")
        simulation_mode = data.get("simulation_mode", False)

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
            return {"statusCode": 400, "body": json.dumps({"error": error_msg})}

        if not simulation_mode:
            if not os.path.exists(ca_path):
                error_msg = f"CA file not found at {ca_path}"
                logger.error(error_msg)
                return {"statusCode": 500, "body": json.dumps({"error": error_msg})}
            logger.info(f"CA file found at {ca_path}")

        logger.info(f"Received login request: api_key={api_key[:4]}****, secret_key={secret_key[:4]}****")
        logger.info(f"Initializing Shioaji with simulation={simulation_mode}")
        api = sj.Shioaji(simulation=simulation_mode)

        if not simulation_mode:
            logger.info(f"Activating CA with ca_path={ca_path}, person_id={person_id}")
            result = api.activate_ca(ca_path=ca_path, ca_passwd=ca_password, person_id=person_id)
            if not result:
                error_msg = "Failed to activate CA"
                logger.error(error_msg)
                return {"statusCode": 500, "body": json.dumps({"error": error_msg})}
            logger.info("CA activated successfully")

        logger.info("Logging into Shioaji")
        accounts = api.login(api_key=api_key, secret_key=secret_key)
        logger.info(f"Login successful, accounts: {json.dumps(accounts, default=str)}")

        logger.info("Fetching contracts data")
        api.fetch_contracts()
        logger.info("Contracts data fetched successfully")

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Login successful", "accounts": accounts}, default=str)
        }

    except Exception as e:
        error_msg = f"Error in login: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception traceback: {sys.exc_info()}")
        return {"statusCode": 500, "body": json.dumps({"error": error_msg})}

@app.route('/quote', methods=['POST'])
def quote():
    global api
    try:
        data = request.get_json()
        if not data:
            error_msg = "Request body is empty"
            logger.error(error_msg)
            return {"statusCode": 400, "body": json.dumps({"error": error_msg})}

        stock_code = data.get("stock_code", "2330")

        if api is None:
            error_msg = "Shioaji API not initialized. Please login first."
            logger.error(error_msg)
            return {"statusCode": 500, "body": json.dumps({"error": error_msg})}

        logger.info(f"Received quote request: stock_code={stock_code}")

        # 嘗試從 TSE 查詢合約，若失敗則記錄詳細錯誤
        logger.info(f"Fetching contract for stock_code={stock_code}")
        contract = api.Contracts.Stocks.TSE[stock_code]

        # 檢查 contract 是否為 None
        if contract is None:
            error_msg = f"Contract not found for stock_code={stock_code} in TSE (returned None)"
            logger.error(error_msg)
            return {"statusCode": 500, "body": json.dumps({"error": error_msg})}

        # 記錄合約資料
        logger.info(f"Contract found: {json.dumps(contract.__dict__, default=str)}")

        # 查詢快照資料
        logger.info(f"Fetching quote for stock_code={stock_code}")
        quote = api.snapshots([contract])[0]
        logger.info(f"Quote fetched successfully: {json.dumps(quote, default=str)}")

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Quote fetched", "quote": quote}, default=str)
        }

    except KeyError as ke:
        error_msg = f"Contract not found for stock_code={stock_code} in TSE (KeyError: {str(ke)})"
        logger.error(error_msg)
        return {"statusCode": 500, "body": json.dumps({"error": error_msg})}
    except Exception as e:
        error_msg = f"Error in quote: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception traceback: {sys.exc_info()}")
        return {"statusCode": 500, "body": json.dumps({"error": error_msg})}

@app.route('/contracts', methods=['GET'])
def get_contracts():
    global api
    try:
        if api is None:
            error_msg = "Shioaji API not initialized. Please login first."
            logger.error(error_msg)
            return {"statusCode": 500, "body": json.dumps({"error": error_msg})}

        # 獲取 TSE 股票合約資料並轉為可序列化的格式
        logger.info("Fetching TSE contracts")
        tse_contracts = {k: v.__dict__ if v is not None else None for k, v in api.Contracts.Stocks.TSE.items()}
        logger.info("TSE contracts fetched successfully")

        # 額外記錄 OTC 合約資料
        logger.info("Fetching OTC contracts")
        otc_contracts = {k: v.__dict__ if v is not None else None for k, v in api.Contracts.Stocks.OTC.items()}
        logger.info("OTC contracts fetched successfully")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Contracts fetched",
                "tse_contracts": tse_contracts,
                "otc_contracts": otc_contracts
            }, default=str)
        }

    except Exception as e:
        error_msg = f"Error in contracts: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception traceback: {sys.exc_info()}")
        return {"statusCode": 500, "body": json.dumps({"error": error_msg})}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
