from logger import slog
import pandas_datareader.data as pdr

def get_stock_data(code):
	df = pdr.DataReader("{}.JP".format(code), "stooq").sort_index()
	return df

def analyze_stock_data():
	slog("INFO", "株価を取得します。")
	code = 5262 # ヒューム
	df = get_stock_data(code)
	slog("INFO", df.tail())
