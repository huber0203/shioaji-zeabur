from flask import Flask, request
import shioaji as sj
import json
import logging
import os

app = Flask(__name__)

# 手動配置 Shioaji 的日誌，寫入 /tmp/shioaji.log
logger = logging.getLogger('shioaji')
logger.setLevel(logging.INFO)
handler = logging.FileHandler('/tmp/shioaji.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.handlers = [handler]

# 從環境變數中讀取敏感資訊
API_KEY = os.getenv("SHIOAJI_API_KEY")
SECRET_KEY = os.getenv("SHIOAJI_SECRET_KEY")

# 檢查環境變數是否存在
missing_vars = []
if not API_KEY:
    missing_vars.append("SHIOAJI_API_KEY")
if not SECRET_KEY:
    missing_vars.append("SHIOAJI_SECRET_KEY")

if missing_vars:
    error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
    logger.error(error_msg)

@app.route('/quote', methods=['POST'])
def get_quote():
    try:
        # 檢查環境變數
        if
