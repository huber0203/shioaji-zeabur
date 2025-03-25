from flask import Flask, request
import json

app = Flask(__name__)

@app.route('/login', methods=['POST'])
def login():
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Login endpoint"})
    }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
