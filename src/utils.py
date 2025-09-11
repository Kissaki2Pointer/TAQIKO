from logger import slog
from datetime import datetime, timezone, timedelta

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

def is_target_time(target_time):
	"""
	現在時刻が指定された時刻かどうかを判定する
	JST（日本標準時）で判定
	Args:
		target_time (str): 判定したい時刻（例: "8:55", "15:30"）
	Returns:
		bool: 指定時刻の場合True、それ以外はFalse
	"""
	try:
		target_hour, target_minute = map(int, target_time.split(':'))
		jst = timezone(timedelta(hours=9))
		current_time = datetime.now(jst)
		return current_time.hour == target_hour and current_time.minute == target_minute
	except (ValueError, AttributeError):
		slog("ERROR", f"時刻の形式が正しくありません: {target_time}")
		return False
