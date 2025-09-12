from logger import slog
import json
import os
import urllib.request
import urllib.error
import datetime
import hashlib
import time

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

def get_order_status(order_id=None, symbol=None, use_test_api=True):
    """
    注文状況を取得
    
    Args:
        order_id: 注文ID（指定した場合は特定の注文のみ）
        symbol: 銘柄コード（指定した場合は特定銘柄のみ）
        use_test_api: 検証用APIを使用するかどうか
    
    Returns:
        list: 注文情報のリスト、エラーの場合はNone
    """
    # 検証用APIと本番APIのURL
    base_url = 'http://localhost:18081' if use_test_api else 'http://localhost:18080'
    url = f'{base_url}/kabusapi/orders'
    
    # パラメータ設定
    params = {'product': 0}  # 0:すべて、1:現物、2:信用、3:先物、4:OP
    
    if order_id:
        params['id'] = order_id
    if symbol:
        params['symbol'] = symbol
    
    try:
        # URLにパラメータを追加
        import urllib.parse
        url_with_params = f"{url}?{urllib.parse.urlencode(params)}"
        
        req = urllib.request.Request(url_with_params, method='GET')
        req.add_header('Content-Type', 'application/json')
        req.add_header('X-API-KEY', get_api_token())
        
        with urllib.request.urlopen(req) as res:
            if res.status == 200:
                content = json.loads(res.read())
                slog("INFO", f"注文状況取得成功: {len(content) if isinstance(content, list) else 1}件")
                return content
            else:
                slog("ERROR", f"注文状況取得失敗: Status {res.status}")
                return None
                
    except urllib.error.HTTPError as e:
        try:
            error_content = json.loads(e.read())
            slog("ERROR", f"注文状況取得エラー: {error_content}")
        except:
            slog("ERROR", f"注文状況取得エラー: {e}")
        return None
    except Exception as e:
        slog("ERROR", f"注文状況取得でエラーが発生: {e}")
        return None


def get_execution_price_from_order(order_id, use_test_api=True):
    """
    注文IDから約定価格を取得
    
    Args:
        order_id: 注文ID
        use_test_api: 検証用APIを使用するかどうか
    
    Returns:
        float: 約定価格、約定していない場合やエラーの場合はNone
    """
    orders = get_order_status(order_id=order_id, use_test_api=use_test_api)
    
    if not orders:
        return None
    
    # 注文情報から約定価格を取得
    if isinstance(orders, list) and len(orders) > 0:
        order = orders[0]
    else:
        order = orders
    
    try:
        # State=5（終了）かつ全約定の場合のみ約定価格を返す
        if order.get('State') == 5:  # 終了状態
            execution_qty = order.get('CumQty', 0)  # 約定数量
            if execution_qty > 0:
                execution_price = order.get('Price', 0)  # 約定価格
                if execution_price > 0:
                    slog("INFO", f"約定価格取得: {order_id} → {execution_price}円 ({execution_qty}株)")
                    return execution_price
        
        slog("INFO", f"未約定または約定価格なし: {order_id}")
        return None
        
    except Exception as e:
        slog("ERROR", f"約定価格取得でエラー: {order_id} - {e}")
        return None



def wait_for_execution_and_get_price(order_result, symbol, max_wait_seconds=30, use_test_api=True):
    """
    注文の約定を待機し、約定価格を取得
    
    Args:
        order_result: 注文送信結果（注文IDを含む）
        symbol: 銘柄コード
        max_wait_seconds: 最大待機時間（秒）
        use_test_api: 検証用APIを使用するかどうか
    
    Returns:
        float: 約定価格、約定しなかった場合やエラーの場合はNone
    """
    if not order_result:
        return None
    
    # 検証用APIの場合は仮のIDとテスト価格を使用
    if use_test_api:
        order_id = order_result.get('OrderId')
        if not order_id:
            # 検証用APIでは注文IDが返らないため、仮のIDを生成
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y%m%dA02N%H%M%S%f')[:-2]  # マイクロ秒の下2桁を削除
            order_id = timestamp
            slog("INFO", f"検証用API: 仮の注文ID={order_id}を生成 {symbol}")
        
        # テスト用の仮の約定価格を生成（銘柄コードに基づいて）
        import hashlib
        hash_val = int(hashlib.md5(symbol.encode()).hexdigest()[:8], 16)
        test_price = 500 + (hash_val % 1500)  # 500-2000円の範囲でテスト価格を生成
        
        slog("INFO", f"検証用API: テスト約定価格={test_price}円 {symbol} (注文ID={order_id})")
        return float(test_price)
    
    # 本番API用の処理
    order_id = order_result.get('Result')
    if not order_id:
        slog("ERROR", f"注文結果に注文IDがありません: {symbol}")
        return None
    
    import time
    
    slog("INFO", f"約定待機開始: {symbol} 注文ID={order_id}")
    
    for i in range(max_wait_seconds):
        execution_price = get_execution_price_from_order(order_id, use_test_api)
        
        if execution_price is not None:
            slog("INFO", f"約定確認: {symbol} 約定価格={execution_price}円")
            return execution_price
        
        if i < max_wait_seconds - 1:  # 最後の試行でない場合のみ待機
            time.sleep(1)
    
    slog("WARNING", f"約定待機タイムアウト: {symbol} 注文ID={order_id}")
    return None



