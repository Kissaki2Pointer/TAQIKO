import requests
from bs4 import BeautifulSoup
import time
from logger import slog


def fetch_yahoo_finance_data(retries: int = 3) -> list:
    """
    東証グロースの出来高上位銘柄データをスクレイピングする

    Args:
        retries: リトライ回数

    Returns:
        list: 銘柄データのリスト（順位、銘柄コード、銘柄名、現在値、前日比、出来高など）
    """

    url = "https://finance.yahoo.co.jp/stocks/ranking/tradingValueHigh?market=tokyoM&term=daily"  # 東証グロース
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for attempt in range(retries):
        try:
            slog("INFO", f"東証グロース出来高上位データを取得中... - 試行 {attempt + 1}/{retries}")

            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # ランキングテーブルを取得
            ranking_data = []

            # RankingTable__row__1Gwpクラスの行を取得
            rows = soup.find_all('tr', class_='RankingTable__row__1Gwp')

            for i, row in enumerate(rows[:50]):  # 上位50位まで取得
                try:
                    # 順位を取得
                    rank_cell = row.find('th', class_='RankingTable__rank__2fAZ')
                    rank = int(rank_cell.text.strip()) if rank_cell else i + 1

                    # 銘柄情報を取得
                    detail_cell = row.find('td', class_='RankingTable__detail__P452')
                    if not detail_cell:
                        continue

                    # 銘柄名
                    name_link = detail_cell.find('a')
                    company_name = name_link.text.strip() if name_link else '不明'

                    # 銘柄コード
                    symbol_code = '不明'
                    supplements = detail_cell.find_all('li', class_='RankingTable__supplement__vv_m')
                    if supplements and len(supplements) > 0:
                        symbol_code = supplements[0].text.strip()

                    # 現在値を取得
                    price_elements = row.find_all('td', class_='RankingTable__detail--value__i9gr')

                    current_price = '0'
                    change = '0'
                    change_rate = '0%'
                    volume = '0'

                    if len(price_elements) >= 3:
                        # 現在値（1番目の要素）
                        price_span = price_elements[0].find('span', class_='StyledNumber__value__3rXW')
                        if price_span:
                            current_price = price_span.text.strip().replace(',', '')

                        # 前日比と前日比率（2番目の要素）
                        change_element = price_elements[1]
                        change_spans = change_element.find_all('span', class_='StyledNumber__value__3rXW')
                        if len(change_spans) >= 2:
                            change = change_spans[0].text.strip()
                            change_rate = change_spans[1].text.strip()
                            # %記号を取得
                            suffix_span = change_element.find('span', class_='StyledNumber__suffix__2SD5')
                            if suffix_span:
                                change_rate += suffix_span.text.strip()

                        # 出来高（3番目の要素）
                        volume_span = price_elements[2].find('span', class_='StyledNumber__value__3rXW')
                        if volume_span:
                            volume = volume_span.text.strip().replace(',', '')

                    stock_data = {
                        'rank': rank,
                        'symbol': symbol_code,
                        'name': company_name,
                        'current_price': current_price,
                        'change': change,
                        'change_rate': change_rate,
                        'volume': volume
                    }

                    ranking_data.append(stock_data)

                except Exception as e:
                    slog("WARNING", f"行データの解析に失敗: {e}")
                    continue

            if ranking_data:
                slog("INFO", f"東証グロース出来高上位データ取得成功: {len(ranking_data)}銘柄")
                return ranking_data
            else:
                slog("WARNING", "出来高上位データが見つかりませんでした。ページ構造が変更された可能性があります。")

        except requests.exceptions.RequestException as e:
            slog("ERROR", f"リクエストエラー: {e}")
        except Exception as e:
            slog("ERROR", f"予期しないエラー: {e}")

        if attempt < retries - 1:
            slog("INFO", f"5秒後に再試行します...")
            time.sleep(5)

    slog("ERROR", "東証グロース出来高上位データの取得に失敗しました。")
    return []
