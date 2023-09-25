from flask import Flask, jsonify, request

from api_utils import *

app = Flask(__name__)


# 定义一个路由，指定请求方法为POST
@app.route("/api/v1/simulation/score/simulationScoreAnalysis", methods=["POST"])
def score_analysis_api():
    if request.is_json:
        try:
            data = request.get_json()
            url = data["url"]
            save_dir = "download_files/"
            file_path = download_file(save_dir, url)
            res = score_analysis(file_path)
            return jsonify(res), 200
        except Exception as _:
            return jsonify({"success": False, "msg": "An error occurred during scoring.", "code": 400, "data": {}}), 400

    else:
        return jsonify({"success": False, "msg": "Request data is not in JSON format.", "code": 400, "data": {}}), 400


@app.route("/api/v1/biddingDocumentParse", methods=["POST"])
def bidding_document_parse_api():
    if request.is_json:
        try:
            data = request.get_json()
            id = data["id"]
            url = data["url"]
            save_dir = "download_files/"
            file_path = download_file(save_dir, url)
            bidding_document_parse_result = bidding_document_parse(file_path)
            bidding_document_parse_result["id"] = id
            response = {"success": True, "msg": "请求成功", "code": 200, "data": bidding_document_parse_result}
            return jsonify(response), 200
        except Exception as _:
            return jsonify({"success": False, "msg": "An error occurred during parsing.", "code": 400, "data": {}}), 400
    else:
        return jsonify({"success": False, "msg": "Request data is not in JSON format.", "code": 400, "data": {}}), 400


if __name__ == '__main__':
    app.run("192.168.60.138", 8001)
