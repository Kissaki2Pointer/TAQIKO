import urllib.request
import json
import pprint
import os
from utils import get_env_value
from logger import slog

def get_token(use_test_api):
    """
    トークンを取得し、tokenディレクトリに保存する
    
    Args:
        use_test_api: 検証用APIを使用するかどうか
    """
    if use_test_api:
        api_password = get_env_value('APIPASS_KSHO')
        if api_password is None:
            slog("ERROR", "APIPASS_KSHOが取得できませんでした。")
            return False
        url = 'http://localhost:18081/kabusapi/token'
    else:
        api_password = get_env_value('APIPASS')
        if api_password is None:
            slog("ERROR", "APIPASSが取得できませんでした。")
            return False
        url = 'http://localhost:18080/kabusapi/token'

    obj = { 'APIPassword': api_password }
    json_data = json.dumps(obj).encode('utf8')
    req = urllib.request.Request(url, json_data, method='POST')
    req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(req) as res:
            slog("INFO", f"{res.status} {res.reason}")
            for header in res.getheaders():
                slog("INFO", str(header))
            slog("INFO","")
            content = json.loads(res.read())
            pprint.pprint(content)
            
            # トークン発行成功時にファイルを保存
            if res.status == 200 and 'Token' in content:
                token = content['Token']
                # tokenディレクトリを作成
                script_dir = os.path.dirname(os.path.abspath(__file__))
                token_dir = os.path.join(script_dir, 'token')
                if not os.path.exists(token_dir):
                    os.makedirs(token_dir)
                
                # 古いtokenファイルを削除
                for old_token_file in os.listdir(token_dir):
                    old_file_path = os.path.join(token_dir, old_token_file)
                    if os.path.isfile(old_file_path):
                        os.remove(old_file_path)
                
                # トークンファイルを作成
                token_file_path = os.path.join(token_dir, token)
                with open(token_file_path, 'w', encoding='utf-8') as token_file:
                    pass
                slog("INFO", f"トークン : {token}")
                return True
            else:
                return False
    except urllib.error.HTTPError as e:
        slog("ERROR", str(e))
        try:
            content = json.loads(e.read())
            pprint.pprint(content)
        except:
            pass
        return False
    except Exception as e:
        slog("ERROR", str(e))
        return False
