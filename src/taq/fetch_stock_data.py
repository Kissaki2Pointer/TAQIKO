from logger import slog
import pandas_datareader.data as pdr
import pandas as pd
import talib as ta
import mplfinance as mpf
import json
import requests
import os
import numpy as np
import urllib.request
import urllib.error

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

def read_capital():
    """capital.txtから発注可能枠を読み込む"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    capital_file_path = os.path.join(project_root, 'db', 'capital.txt')
    
    try:
        with open(capital_file_path, 'r') as f:
            capital = int(f.read().strip())
        slog("INFO", f"発注可能枠を読み込み: {capital:,}円")
        return capital
    except FileNotFoundError:
        slog("ERROR", f"capital.txtが見つかりませ")
        return 0
    except ValueError:
        slog("ERROR", "capital.txtの内容が正しくありません")
        return 0

def write_capital(amount):
    """capital.txtに発注可能枠を書き込む"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    capital_file_path = os.path.join(project_root, 'db', 'capital.txt')
    
    try:
        with open(capital_file_path, 'w') as f:
            f.write(str(amount))
        slog("INFO", f"発注可能枠を更新: {amount:,}円")
        return True
    except Exception as e:
        slog("ERROR", f"capital.txtの書き込みでエラーが発生: {e}")
        return False

def calculate_commission(execution_amount):
    """
    約定金額に基づいて手数料を計算する
    
    Args:
        execution_amount: 約定金額（円）
    
    Returns:
        int: 手数料（円）
    """
    if execution_amount <= 50000:
        return 55
    elif execution_amount <= 100000:
        return 99
    elif execution_amount <= 200000:
        return 115
    elif execution_amount <= 500000:
        return 275
    elif execution_amount <= 1000000:
        return 535
    else:
        # 100万円超: 約定金額×0.099% + 99円（上限4,059円）
        commission = int(execution_amount * 0.00099) + 99
        return min(commission, 4059)

def update_capital_after_trading(buy_transactions, sell_transactions):
    """
    取引終了後にcapital.txtを更新する
    
    Args:
        buy_transactions: 買い注文のリスト [(symbol, qty, price), ...]
        sell_transactions: 売り注文のリスト [(symbol, qty, price), ...]
    
    Returns:
        bool: 更新成功かどうか
    """
    try:
        # 現在の残高を取得
        current_capital = read_capital()
        
        # 手数料合計を計算
        total_commission = 0
        
        # 買い注文の手数料を計算
        for symbol, qty, price in buy_transactions:
            execution_amount = qty * price
            commission = calculate_commission(execution_amount)
            total_commission += commission
            slog("INFO", f"買い手数料: {symbol} {execution_amount:,}円 → 手数料 {commission}円")
        
        # 売り注文の手数料を計算
        for symbol, qty, price in sell_transactions:
            execution_amount = qty * price
            commission = calculate_commission(execution_amount)
            total_commission += commission
            slog("INFO", f"売り手数料: {symbol} {execution_amount:,}円 → 手数料 {commission}円")
        
        # 実現損益を計算（売り注文の合計 - 買い注文の合計）
        buy_total = sum(qty * price for symbol, qty, price in buy_transactions)
        sell_total = sum(qty * price for symbol, qty, price in sell_transactions)
        realized_pnl = sell_total - buy_total
        
        # 新しい残高を計算
        # capital_new = capital_old + 実現損益合計 − 手数料合計
        new_capital = current_capital + realized_pnl - total_commission
        
        # ログ出力
        slog("INFO", f"=== 残高更新 ===")
        slog("INFO", f"前回残高: {current_capital:,}円")
        slog("INFO", f"買い合計: {buy_total:,}円")
        slog("INFO", f"売り合計: {sell_total:,}円")
        slog("INFO", f"実現損益: {realized_pnl:+,}円")
        slog("INFO", f"手数料合計: {total_commission:,}円")
        slog("INFO", f"新残高: {new_capital:,}円")
        
        # capital.txtに書き込み
        return write_capital(new_capital)
        
    except Exception as e:
        slog("ERROR", f"残高更新でエラーが発生: {e}")
        return False

def buy_stock_cash(symbol, qty=100, price=0, use_test_api=True):
    """
    現物買い注文を送信
    
    Args:
        symbol: 銘柄コード（文字列）
        qty: 数量（デフォルト100株）
        price: 指値価格（0の場合は成行）
        use_test_api: 検証用APIを使用するかどうか
    
    Returns:
        dict: 注文結果のレスポンス、エラーの場合はNone
    """
    # 検証用APIと本番APIのURL
    base_url = 'http://localhost:18081' if use_test_api else 'http://localhost:18080'
    url = f'{base_url}/kabusapi/sendorder'
    
    # 注文オブジェクトを作成
    order_obj = {
        'Symbol': symbol,
        'Exchange': 1,  # 東証
        'SecurityType': 1,  # 株式
        'Side': '2',  # 買い
        'CashMargin': 1,  # 現物
        'DelivType': 2,  # お預り金
        'FundType': 'AA',  # 現金
        'AccountType': 2,  # 特定口座
        'Qty': qty,
        'FrontOrderType': 10 if price == 0 else 20,  # 10: 成行, 20: 指値
        'Price': price,
        'ExpireDay': 0  # 当日
    }
    
    # 成行の場合はPriceを0にする
    if price == 0:
        order_obj['Price'] = 0
    
    json_data = json.dumps(order_obj).encode('utf-8')
    
    try:
        req = urllib.request.Request(url, json_data, method='POST')
        req.add_header('Content-Type', 'application/json')
        req.add_header('X-API-KEY', get_api_token())
        
        with urllib.request.urlopen(req) as res:
            if res.status == 200:
                content = json.loads(res.read())
                slog("INFO", f"注文送信成功: {symbol} {qty}株 {'成行' if price == 0 else f'{price}円'}")
                slog("INFO", f"注文結果: {content}")
                return content
            else:
                slog("ERROR", f"注文送信失敗: Status {res.status}")
                return None
                
    except urllib.error.HTTPError as e:
        try:
            error_content = json.loads(e.read())
            slog("ERROR", f"注文エラー: {symbol} - {error_content}")
        except:
            slog("ERROR", f"注文エラー: {symbol} - {e}")
        return None
    except Exception as e:
        slog("ERROR", f"注文送信でエラーが発生: {symbol} - {e}")
        return None

def sell_stock_cash(symbol, qty=100, price=0, use_test_api=True):
    """
    現物売り注文を送信
    
    Args:
        symbol: 銘柄コード（文字列）
        qty: 数量（デフォルト100株）
        price: 指値価格（0の場合は成行）
        use_test_api: 検証用APIを使用するかどうか
    
    Returns:
        dict: 注文結果のレスポンス、エラーの場合はNone
    """
    # 検証用APIと本番APIのURL
    base_url = 'http://localhost:18081' if use_test_api else 'http://localhost:18080'
    url = f'{base_url}/kabusapi/sendorder'
    
    # 注文オブジェクトを作成
    order_obj = {
        'Symbol': symbol,
        'Exchange': 1,  # 東証
        'SecurityType': 1,  # 株式
        'Side': '1',  # 売り
        'CashMargin': 1,  # 現物
        'DelivType': 0,  # 売建玉
        'FundType': '  ',  # 空白
        'AccountType': 2,  # 特定口座
        'Qty': qty,
        'FrontOrderType': 10 if price == 0 else 20,  # 10: 成行, 20: 指値
        'Price': price,
        'ExpireDay': 0  # 当日
    }
    
    # 成行の場合はPriceを0にする
    if price == 0:
        order_obj['Price'] = 0
    
    json_data = json.dumps(order_obj).encode('utf-8')
    
    try:
        req = urllib.request.Request(url, json_data, method='POST')
        req.add_header('Content-Type', 'application/json')
        req.add_header('X-API-KEY', get_api_token())
        
        with urllib.request.urlopen(req) as res:
            if res.status == 200:
                content = json.loads(res.read())
                slog("INFO", f"売り注文送信成功: {symbol} {qty}株 {'成行' if price == 0 else f'{price}円'}")
                slog("INFO", f"注文結果: {content}")
                return content
            else:
                slog("ERROR", f"売り注文送信失敗: Status {res.status}")
                return None
                
    except urllib.error.HTTPError as e:
        try:
            error_content = json.loads(e.read())
            slog("ERROR", f"売り注文エラー: {symbol} - {error_content}")
        except:
            slog("ERROR", f"売り注文エラー: {symbol} - {e}")
        return None
    except Exception as e:
        slog("ERROR", f"売り注文送信でエラーが発生: {symbol} - {e}")
        return None

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
	
	# 前日のゴールデンクロス・デッドクロスを確認
	yesterday_gc = False
	yesterday_dc = False
	
	if len(df) >= 2:
		# 最新から2番目（前日）のデータを取得
		yesterday_data = df.iloc[-2]
		yesterday_gc = not pd.isna(yesterday_data.get('gc', np.nan))
		yesterday_dc = not pd.isna(yesterday_data.get('dc', np.nan))
		
		if yesterday_gc:
			slog("INFO", f"前日にゴールデンクロス発生: {company_name}（{code}）")
		if yesterday_dc:
			slog("INFO", f"前日にデッドクロス発生: {company_name}（{code}）")
	
	return df, yesterday_gc, yesterday_dc

def analyze_all_targets():
	"""
	TARGETSリスト内のすべての銘柄を分析し、buy_listとsell_listを作成
	"""
	slog("INFO", "全銘柄の移動平均線分析を開始します。")
	
	results = {}
	buy_list = []
	sell_list = []
	
	for code, company_name in TARGETS:
		try:
			df, yesterday_gc, yesterday_dc = analyze_stock_with_moving_averages(code, company_name)
			results[code] = df
			
			# 前日にゴールデンクロスが発生した銘柄をbuy_listに追加
			if yesterday_gc:
				buy_list.append((code, company_name))
				slog("INFO", f"買いリストに追加: {company_name}（{code}）")
			
			# 前日にデッドクロスが発生した銘柄をsell_listに追加
			if yesterday_dc:
				sell_list.append((code, company_name))
				slog("INFO", f"売りリストに追加: {company_name}（{code}）")
				
		except Exception as e:
			slog("ERROR", f"{company_name}（{code}）の分析でエラーが発生: {e}")
	
	# 結果をログに出力
	slog("INFO", "=== 売買対象リスト ===")
	slog("INFO", f"買いリスト ({len(buy_list)}銘柄):")
	for code, name in buy_list:
		slog("INFO", f"  - {name}（{code}）")
	
	slog("INFO", f"売りリスト ({len(sell_list)}銘柄):")
	for code, name in sell_list:
		slog("INFO", f"  - {name}（{code}）")
	
	return results, buy_list, sell_list

def analyze_stock_data():
	slog("INFO", "売買リストを作成します。")
	
	results, buy_list, sell_list = analyze_all_targets()

	# capital.txtから今日の発注可能枠を取得
	daily_capital = read_capital()

	# 入金処理はAPIでできない。

	# 現物余力 (ここで返ってきた額まで購入が可能)
	# url = 'http://localhost:18080/kabusapi/wallet/cash'
	# response = requests.get(url, headers={'X-API-KEY': get_api_token(),})
	# buyable = json.loads(response.text)

	# slog("INFO", "取引余力\t{}".format(buyable['StockAccountWallet']))

	# if int(buyable['StockAccountWallet']) < 100 * 1000:  # 例: 100株×概算1,000円
	# 	slog("ERROR", "資金がありません。入金してください。")
	# 	return False

	# テスト用: 強制的に2番目の銘柄を買いリストに追加
	if not buy_list and len(TARGETS) > 1:
		test_stock = TARGETS[1]  # 2番目の銘柄
		buy_list.append(test_stock)
		slog("INFO", f"テスト用に買いリストに追加: {test_stock[1]}（{test_stock[0]}）")

	# 買いリストの銘柄を100株ずつ成行で購入（検証用API使用）
	slog("INFO", "=== 購入処理開始 ===")
	successful_orders = 0
	total_orders = len(buy_list)
	
	if daily_capital > 0 and total_orders > 0:
		for code, company_name in buy_list:
			try:
				slog("INFO", f"購入処理: {company_name}（{code}）100株 成行注文")
				result = buy_stock_cash(code, qty=100, price=0, use_test_api=True)
				
				if result:
					successful_orders += 1
					slog("INFO", f"購入成功: {company_name}（{code}）")
				else:
					slog("ERROR", f"購入失敗: {company_name}（{code}）")
					
			except Exception as e:
				slog("ERROR", f"購入処理でエラー: {company_name}（{code}） - {e}")
	
	else:
		if daily_capital <= 0:
			slog("WARNING", "発注可能枠が0円のため購入処理をスキップしました")
		if total_orders == 0:
			slog("INFO", "購入対象がないため購入処理をスキップしました")
	
	slog("INFO", f"購入処理完了: {successful_orders}/{total_orders}件成功")

	# テスト用: 強制的に最初の銘柄を売りリストに追加
	if not sell_list and TARGETS:
		test_stock = TARGETS[0]  # 最初の銘柄
		sell_list.append(test_stock)
		slog("INFO", f"テスト用に売りリストに追加: {test_stock[1]}（{test_stock[0]}）")

	# 売りリストの銘柄を100株ずつ成行で売却（検証用API使用）
	slog("INFO", "=== 売却処理開始 ===")
	sell_successful_orders = 0
	total_sell_orders = len(sell_list)
	
	for code, company_name in sell_list:
		try:
			slog("INFO", f"売却処理: {company_name}（{code}）100株 成行注文")
			result = sell_stock_cash(code, qty=100, price=0, use_test_api=True)
			
			if result:
				sell_successful_orders += 1
				slog("INFO", f"売却成功: {company_name}（{code}）")
			else:
				slog("ERROR", f"売却失敗: {company_name}（{code}）")
				
		except Exception as e:
			slog("ERROR", f"売却処理でエラー: {company_name}（{code}） - {e}")
	
	if total_sell_orders == 0:
		slog("INFO", "売却対象がないため売却処理をスキップしました")
	
	slog("INFO", f"売却処理完了: {sell_successful_orders}/{total_sell_orders}件成功")

	# 取引終了後にcapital.txtを更新
	# 注意: 実際の約定価格が必要ですが、ここでは仮の価格を使用
	# 実運用では注文結果から実際の約定価格を取得する必要があります
	slog("INFO", "=== 残高更新処理開始 ===")
	
	# 仮の約定価格（実際にはAPIレスポンスから取得）
	dummy_buy_price = 1000  # 仮の買い価格
	dummy_sell_price = 1100  # 仮の売り価格
	
	# 取引記録を作成（実際の実装では注文結果から作成）
	buy_transactions = []
	for code, company_name in buy_list:
		if code in [t[0] for t in TARGETS]:  # テスト用に追加された銘柄も含む
			buy_transactions.append((code, 100, dummy_buy_price))
	
	sell_transactions = []
	for code, company_name in sell_list:
		if code in [t[0] for t in TARGETS]:  # テスト用に追加された銘柄も含む
			sell_transactions.append((code, 100, dummy_sell_price))
	
	if buy_transactions or sell_transactions:
		slog("INFO", "取引記録に基づいて発注可能枠を更新します")
		slog("WARNING", "注意: 仮の価格を使用しています（実運用では実際の約定価格を使用してください）")
		update_success = update_capital_after_trading(buy_transactions, sell_transactions)
		
		if update_success:
			slog("INFO", "発注可能枠の更新が完了しました")
		else:
			slog("ERROR", "発注可能枠の更新に失敗しました")
	else:
		slog("INFO", "取引がないため発注可能枠の更新をスキップしました")

	return True
