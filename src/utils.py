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
