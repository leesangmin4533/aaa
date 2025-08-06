# app.py
from flask import Flask, request, jsonify
import subprocess
import os
import sys

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def run_automation():
    print("Received request to run automation.")
    # Cloud Run은 PORT 환경 변수를 통해 포트를 지정합니다.
    # Flask 앱이 이 포트에서 리스닝해야 합니다.
    port = int(os.environ.get('PORT', 8080))

    try:
        # main.py를 서브프로세스로 실행합니다.
        # PYTHONPATH를 설정하여 main.py가 다른 모듈을 올바르게 임포트할 수 있도록 합니다.
        env = os.environ.copy()
        env['PYTHONPATH'] = os.getcwd() # 현재 작업 디렉토리를 PYTHONPATH에 추가

        result = subprocess.run(
            [sys.executable, "main.py"], # sys.executable을 사용하여 현재 파이썬 인터프리터 사용
            capture_output=True,
            text=True,
            check=True,
            env=env
        )
        print("Automation script finished.")
        print("Stdout:", result.stdout)
        print("Stderr:", result.stderr)
        return jsonify({"status": "success", "message": "Automation script executed.", "stdout": result.stdout, "stderr": result.stderr}), 200
    except subprocess.CalledProcessError as e:
        print(f"Automation script failed with error: {e}")
        print("Stdout:", e.stdout)
        print("Stderr:", e.stderr)
        return jsonify({"status": "error", "message": "Automation script failed.", "stdout": e.stdout, "stderr": e.stderr}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"status": "error", "message": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    # 로컬 테스트용. Cloud Run은 Gunicorn과 같은 WSGI 서버를 사용합니다.
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
