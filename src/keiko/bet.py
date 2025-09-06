import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from logger import slog

def get_env_value(key):
	"""
	.envファイルから指定されたキーの値を取得する
	フォーマット: key:value
	"""
	try:
		with open('../.env', 'r', encoding='utf-8') as f:
			for line in f:
				line = line.strip()
				if ':' in line:
					env_key, env_value = line.split(':', 1)
					if env_key.strip() == key:
						return env_value.strip()
		return None
	except FileNotFoundError:
		slog("ERROR", ".envファイルが見つかりません。")
		return None
	except Exception as e:
		slog("ERROR", f".envファイルの読み込み中にエラーが発生しました: {e}")
		return None

def web_login(): 
	slog("INFO", f"WEBログインを実行します。")
	
	if not os.path.exists("../.env"):
		slog("ERROR", ".envファイルが存在しません。作成してください。")
		return False
	
	# print(get_env_value("inet_id"))