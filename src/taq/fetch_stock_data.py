from logger import slog
import pandas_datareader.data as pdr
import talib as ta
import mplfinance as mpf
import json
import requests
import os
import numpy as np

TARGETS = [
    ("6176", "ブランジスタ"),
    ("7792", "コラントッテ"),
    ("4424", "Amazia"),
    ("4260", "ハイブリッドテクノロジーズ"),
    ("5253", "カバー"),
    ("5262", "ヒューム"),
]

def get_api_token():
    """tokenディレクトリからAPIトークンを取得"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    token_dir = os.path.join(script_dir, 'token')
    
    if not os.path.exists(token_dir):
        raise FileNotFoundError("tokenディレクトリが存在しません")
    
    token_files = [f for f in os.listdir(token_dir) if os.path.isfile(os.path.join(token_dir, f))]
    if not token_files:
        raise FileNotFoundError("トークンファイルが見つかりません")
    
    return token_files[0]  # 最初のファイル名をトークンとして返す

def get_stock_data(code):
	df = pdr.DataReader("{}.JP".format(code), "stooq").sort_index()
	return df

def analyze_stock_with_moving_averages(code, company_name):
	"""
	株価データを取得し、短期・長期移動平均線およびゴールデンクロス・デッドクロスを計算
	"""
	slog("INFO", f"{company_name}（{code}）の分析を開始します。")
	
	# 株価データ取得
	df = get_stock_data(code)
	close = df['Close']
	
	# 移動平均線の計算（5日線と25日線）
	ma5 = ta.SMA(close, timeperiod=5)
	ma25 = ta.SMA(close, timeperiod=25)
	df['ma5'], df['ma25'] = ma5, ma25
	
	# ゴールデンクロス・デッドクロスの検出
	# 5日移動平均と25日移動平均を比較（5日 > 25日ならTrue）
	cross = ma5 > ma25
	
	# 前日と比較して状態が変わった日を検出
	cross_shift = cross.shift(1)
	# ゴールデンクロス：FalseからTrueに変わった日
	gc_flag = (cross != cross_shift) & (cross == True)
	# デッドクロス：TrueからFalseに変わった日  
	dc_flag = (cross != cross_shift) & (cross == False)
	
	# ゴールデンクロスの日には5日移動平均の値、デッドクロスの日には25日移動平均の値を保存
	gc = [m if g == True else np.nan for g, m in zip(gc_flag, ma5)]
	dc = [m if d == True else np.nan for d, m in zip(dc_flag, ma25)]
	df['gc'], df['dc'] = gc, dc
	
	# 結果の表示
	slog("INFO", f"{company_name}（{code}）の最新データ:")
	slog("INFO", df[['Close', 'ma5', 'ma25']].tail().to_string())
	
	# ゴールデンクロス・デッドクロスの最新発生を確認
	recent_gc = df[df['gc'].notna()].tail(1)
	recent_dc = df[df['dc'].notna()].tail(1)
	
	if not recent_gc.empty:
		gc_date = recent_gc.index[0].strftime('%Y-%m-%d')
		gc_value = recent_gc['gc'].iloc[0]
		slog("INFO", f"最新のゴールデンクロス: {gc_date} (価格: {gc_value:.2f}円)")
	
	if not recent_dc.empty:
		dc_date = recent_dc.index[0].strftime('%Y-%m-%d')
		dc_value = recent_dc['dc'].iloc[0]
		slog("INFO", f"最新のデッドクロス: {dc_date} (価格: {dc_value:.2f}円)")
	
	return df

def analyze_all_targets():
	"""
	TARGETSリスト内のすべての銘柄を分析
	"""
	slog("INFO", "全銘柄の移動平均線分析を開始します。")
	
	results = {}
	for code, company_name in TARGETS:
		try:
			df = analyze_stock_with_moving_averages(code, company_name)
			results[code] = df
		except Exception as e:
			slog("ERROR", f"{company_name}（{code}）の分析でエラーが発生: {e}")
	
	return results

def analyze_stock_data():
	slog("INFO", "株価を取得します。")
	
	analyze_all_targets()

	# 入金処理はAPIでできない。

	# 現物余力 (ここで返ってきた額まで購入が可能)
	url = 'http://localhost:18080/kabusapi/wallet/cash'
	response = requests.get(url, headers={'X-API-KEY': get_api_token(),})
	buyable = json.loads(response.text)

	slog("INFO", "取引余力\t{}".format(buyable['StockAccountWallet']))

	if int(buyable['StockAccountWallet']) < 100 * 1000:  # 例: 100株×概算1,000円
		slog("ERROR", "資金がありません。入金してください。")
		return False

	return True
