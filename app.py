from flask import Flask, render_template, request, jsonify
import subprocess
import os
import webbrowser
from threading import Timer

app = Flask(__name__)

@app.route('/')
def index():
    scripts_info = [
        {
            "name": "src/main.py",
            "display_name": "メインシステム",
            "desc": "いろいろセットのメインです。起動に時間がかかります。"
        },
        {
            "name": "src/toDNG.py",
            "display_name": "DNG変換ツール",
            "desc": "pngまたはjpgを無理やりdngに変換します。"
        }, 
        {
            "name": "src/color.py",
            "display_name": "グラデーション表示",
            "desc": "可視光スペクトルをStreamlitで表示・調整します。"
        },
        {
            "name": "src/approximator.py",
            "display_name": "透過率近似パラメータ算出",
            "desc": "透過率のファイルから簡易・精密法でパラメータを近似、メインシステムのプリセットとして登録します。"
        },
        {
            "name": "src/koujo.py",
            "display_name": "恒常性実験",
            "desc": "環境光と2つの反射スペクトルから色の見え方を計算・比較"
        },
        {
            "name": "src/doga.py",
            "display_name": "動画",
            "desc": "環境光と2つの反射スペクトルから色の見え方を計算・比較"
        }
    ]
    return render_template('index.html', scripts=scripts_info)

@app.route('/run', methods=['POST'])
def run_script():
    script_name = request.form.get('script_name')
    
    if not script_name:
        return jsonify({'exit_code': 1, 'stdout': '', 'stderr': 'ファイル名が送信されていません。'}), 400

    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_path = os.path.normpath(os.path.join(base_dir, script_name))

    if not os.path.exists(target_path):
        error_msg = "スクリプトが見つかりません。名称を更新してください。\n探したパス: " + target_path
        return jsonify({'exit_code': 1, 'stdout': '', 'stderr': error_msg}), 400

    try:
        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'import streamlit' in content:
            subprocess.Popen(['streamlit', 'run', target_path])
            return jsonify({
                'exit_code': 0, 
                'stdout': '別タブで起動します...。他スクリプトの同時起動も可能です。', 
                'stderr': ''
            })
        else:
            result = subprocess.run(['python', target_path], capture_output=True, text=True)
            return jsonify({
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            })
    except Exception as e:
        return jsonify({'exit_code': 1, 'stdout': '', 'stderr': str(e)}), 500

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")

if __name__ == '__main__':
    app.run(port=5000, debug=False)