import os
from time import sleep

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

def get_driver():
	global driver
	options = webdriver.ChromeOptions()
	# Webドライバ－の警告を出さないようにする。
	options.add_experimental_option('excludeSwitches', ['enable-logging'])
	# DOM読み込みまで
	options.set_capability('pageLoadStrategy', 'eager')
	# User Agentを設定
	options.add_argument("user-agent=Desired User Agent String")
	#headlessの指定をする場合、以下が必要。
	# options.add_argument('--headless')
	driver = webdriver.Chrome(options) #Chrome起動
	return None

def web_login():
	slog("INFO", f"WEBログインを実行します。")
	
	if not os.path.exists("../.env"):
		slog("ERROR", ".envファイルが存在しません。作成してください。")
		return False
	
	get_driver()
	driver.get('https://www.ipat.jra.go.jp/') #中央競馬
	# ログイン可能か判定
	try:
		number_inet = driver.find_element(By.NAME, 'inetid')
	except Exception as e:
		slog("WEBログインができませんでした。")
		driver.close()
		return False

	number_inet.send_keys(get_env_value("INETID")) #INET-ID
	sleep(1)
	#ログインボタン
	driver.find_element(By.CLASS_NAME, 'button').click()
	number_kanyu = driver.find_element(By.NAME, 'i')
	number_kanyu.send_keys(get_env_value("SUBNUM"))
	number_ansho = driver.find_element(By.NAME, 'p')
	number_ansho.send_keys(get_env_value("KPASS"))
	number_pars = driver.find_element(By.NAME, 'r')
	number_pars.send_keys(get_env_value("PARS"))

	driver.find_element(By.CLASS_NAME, 'buttonModern').click()
	sleep(5)
	slog("INFO", f"WEBログイン完了しました。")
	return True

def payment():
	slog("INFO", f"JRA 入金処理を実行します。")


