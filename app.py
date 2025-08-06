# app.py
from flask import Flask, jsonify
import os
import sys
import io
import contextlib

# main.py에서 main 함수를 직접 임포트합니다.
# 프로젝트의 루트 디렉토리가 PYTHONPATH에 추가되어 있어야 합니다.
# Dockerfile에서 ENV PYTHONPATH=/app 로 설정되어 있으므로 가능합니다.
from main import main as run_main_automation

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def trigger_automation():
    print("Received request to trigger automation.")

    # main.py의 출력을 캡처하기 위한 설정 (선택 사항, Cloud Logging으로도 충분)
    # Cloud Run에서는 stdout/stderr이 자동으로 Cloud Logging으로 전송됩니다。
    # 여기서는 Flask 응답에 포함하기 위해 캡처합니다.
    f = io.StringIO()
    with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
        try:
            run_main_automation() # main.py의 main 함수를 직접 호출
            output = f.getvalue()
            print("Automation script finished successfully.")
            return jsonify({"status": "success", "message": "Automation script executed.", "output": output}), 200
        except Exception as e:
            output = f.getvalue()
            print(f"Automation script failed with error: {e}")
            return jsonify({"status": "error", "message": f"Automation script failed: {str(e)}", "output": output}), 500

if __name__ == '__main__':
    # Cloud Run은 PORT 환경 변수를 통해 포트를 지정합니다.
    # Gunicorn이 이 부분을 처리하므로, 로컬 테스트용으로만 사용됩니다.
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))