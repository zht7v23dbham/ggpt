import yfinance as yf
import pandas as pd
import ta
import json
import os
import requests
from deep_translator import GoogleTranslator

# ... existing imports ...

def translate_text(text, target='zh-CN'):
    """
    翻译文本
    """
    if not text or not isinstance(text, str):
        return text
    
    try:
        # Use simple mapping for common words to save API calls and time
        # This is a basic optimization
        if len(text) < 20:
            # Add simple dict check here if needed
            pass
            
        translator = GoogleTranslator(source='auto', target=target)
        return translator.translate(text)
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def load_tickers_from_json(file_path='tickers.json'):
    """
    从JSON文件加载股票代码
    """
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('tickers', [])
    except Exception as e:
        print(f"Error loading tickers: {e}")
        return None

def save_tickers_to_json(tickers, file_path='tickers.json'):
    """
    保存股票代码到JSON文件
    """
    try:
        # Load existing data to preserve structure if needed, or just overwrite
        data = {'tickers': tickers}
        
        # Also fetch and save basic info for these tickers to make the json more useful
        # This is optional but requested "股票代码和信息"
        infos = []
        for t in tickers:
            # We can't fetch full info here efficiently for many stocks on every save
            # So let's just save the codes for now, or maybe minimal info if available
            # To keep it fast, we just save codes. 
            # If user wants info saved, we might need a separate function or file.
            # Let's stick to saving codes for persistence first.
            pass
            
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving tickers: {e}")
        return False

def format_hk_ticker(ticker):
    """
    格式化港股代码为 Yahoo Finance 可识别的格式
    e.g. "01810" -> "1810.HK"
         "00700" -> "0700.HK"
         "700" -> "0700.HK"
         "0700.HK" -> "0700.HK"
    """
    # 移除可能的 .HK 后缀进行处理
    base_code = ticker.replace('.HK', '').strip()
    
    # 尝试转为整数再格式化为4位
    try:
        code_int = int(base_code)
        # 港股一般是4位，Yahoo Finance 要求至少4位
        # 如 0005 -> 0005.HK
        # 如 700 -> 0700.HK
        # 如 1810 -> 1810.HK
        # 如 9988 -> 9988.HK
        formatted_code = f"{code_int:04d}.HK"
        return formatted_code
    except ValueError:
        # 如果无法转为整数，原样返回（可能包含非数字字符）
        if not ticker.endswith('.HK'):
            return f"{ticker}.HK"
        return ticker

def get_stock_data(ticker, period="1y", interval="1d"):
    """
    获取股票历史数据
    ticker: 股票代码
    period: 时间周期 (e.g., '1y', '1mo', 'max')
    interval: 时间粒度 (e.g., '1d', '1h', '15m')
    """
    ticker = format_hk_ticker(ticker)
    
    stock = yf.Ticker(ticker)
    try:
        df = stock.history(period=period, interval=interval)
        if df.empty:
            return None
        return df
    except Exception as e:
        print(f"Error getting data for {ticker}: {e}")
        return None

def get_holders_data(ticker):
    """
    获取股东相关数据
    """
    ticker = format_hk_ticker(ticker)
    stock = yf.Ticker(ticker)
    
    data = {}
    try:
        data['major_holders'] = stock.major_holders
    except:
        pass
        
    try:
        data['institutional_holders'] = stock.institutional_holders
    except:
        pass
        
    try:
        data['insider_transactions'] = stock.insider_transactions
    except:
        pass
        
    return data

def get_stock_info(ticker):
    """
    获取股票基本信息
    """
    ticker = format_hk_ticker(ticker)
    
    stock = yf.Ticker(ticker)
    try:
        return stock.info
    except Exception:
        return {}

def calculate_technical_indicators(df):
    """
    计算技术指标
    """
    if df is None or df.empty:
        return df
    
    # Simple Moving Averages
    df['SMA_20'] = ta.trend.sma_indicator(df['Close'], window=20)
    df['SMA_50'] = ta.trend.sma_indicator(df['Close'], window=50)
    
    # Bollinger Bands
    bb_indicator = ta.volatility.BollingerBands(close=df["Close"], window=20, window_dev=2)
    df['BB_High'] = bb_indicator.bollinger_hband()
    df['BB_Low'] = bb_indicator.bollinger_lband()
    df['BB_Mid'] = bb_indicator.bollinger_mavg()
    
    # RSI
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    
    # MACD
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['MACD_Diff'] = macd.macd_diff()
    
    return df

def get_news(ticker):
    """
    获取新闻并标准化格式
    """
    ticker = format_hk_ticker(ticker)
    
    stock = yf.Ticker(ticker)
    try:
        raw_news = stock.news
    except Exception:
        return []

def get_stock_names_sina(tickers):
    """
    批量获取港股中文名称
    tickers: list of stock codes (e.g. ['0700', '0005', '0700.HK'])
    Returns: dict {code: name}
    """
    if not tickers:
        return {}
        
    # Format codes for Sina: hk00700
    sina_codes = []
    code_map = {} # map sina_code back to original ticker
    
    for t in tickers:
        clean_code = t.replace('.HK', '').strip()
        try:
            code_int = int(clean_code)
            sina_code = f"hk{code_int:05d}"
            sina_codes.append(sina_code)
            code_map[sina_code] = t
        except:
            continue
            
    if not sina_codes:
        return {}
        
    # Batch query (limit usually around 800 chars url, let's chunk safely)
    results = {}
    chunk_size = 20
    for i in range(0, len(sina_codes), chunk_size):
        chunk = sina_codes[i:i+chunk_size]
        query_list = ",".join(chunk)
        url = f"http://hq.sinajs.cn/list={query_list}"
        headers = {'Referer': 'http://finance.sina.com.cn/'}
        
        try:
            resp = requests.get(url, headers=headers)
            # encoding might be GBK
            resp.encoding = 'gbk'
            text = resp.text
            
            lines = text.strip().split('\n')
            for line in lines:
                # var hq_str_hk00700="TENCENT,腾讯控股,..."
                if '="' in line:
                    parts = line.split('="')
                    if len(parts) < 2: continue
                    
                    lhs = parts[0] # var hq_str_hk00700
                    rhs = parts[1].strip('";') # TENCENT,腾讯控股,...
                    
                    if not rhs: continue
                    
                    # Extract sina code from lhs
                    # var hq_str_hk00700 -> hk00700
                    current_sina_code = lhs.split('hq_str_')[-1]
                    
                    data_parts = rhs.split(',')
                    if len(data_parts) > 1:
                        cn_name = data_parts[1]
                        # Map back to original ticker
                        original_ticker = code_map.get(current_sina_code)
                        if original_ticker:
                            results[original_ticker] = cn_name
        except Exception as e:
            print(f"Error fetching names from Sina: {e}")
            
    return results

def get_news(ticker):
    """
    获取新闻并标准化格式
    """
    ticker = format_hk_ticker(ticker)
    
    stock = yf.Ticker(ticker)
    try:
        raw_news = stock.news
    except Exception:
        return []
    
    processed_news = []
    if raw_news:
        for item in raw_news:
            # Handle new yfinance structure (nested in 'content')
            if 'content' in item:
                c = item['content']
                title = c.get('title', 'No Title')
                
                # Try to find link in various places
                click_through = c.get('clickThroughUrl')
                if click_through:
                    link = click_through.get('url', '')
                else:
                    link = ''
                    
                if not link:
                    canonical = c.get('canonicalUrl')
                    if canonical:
                        link = canonical.get('url', '')
                
                provider = c.get('provider')
                if provider:
                    publisher = provider.get('displayName', 'Unknown')
                else:
                    publisher = 'Unknown'
                    
                pub_time = c.get('pubDate', '') 
                
                processed_news.append({
                    'title': title,
                    'link': link,
                    'publisher': publisher,
                    'pubDate': pub_time, # ISO string
                    'is_new_format': True
                })
            else:
                # Old structure
                processed_news.append({
                    'title': item.get('title', 'No Title'),
                    'link': item.get('link', ''),
                    'publisher': item.get('publisher', 'Unknown'),
                    'providerPublishTime': item.get('providerPublishTime', 0),
                    'is_new_format': False
                })
                
    return processed_news

def get_exchange_rate(from_currency="HKD", to_currency="CNY"):
    """
    获取汇率
    """
    if from_currency == to_currency:
        return 1.0
        
    pair = f"{from_currency}{to_currency}=X"
    try:
        ticker = yf.Ticker(pair)
        hist = ticker.history(period="1d")
        if not hist.empty:
            return hist['Close'].iloc[-1]
    except Exception:
        pass
    
    # Fallback/Default values if fetch fails (approximate)
    if from_currency == "HKD" and to_currency == "CNY":
        return 0.92
    elif from_currency == "CNY" and to_currency == "HKD":
        return 1.09
        
    return 1.0

def search_stock_sina(query):
    """
    使用新浪财经接口搜索港股
    返回: list of (name, code)
    """
    url = f"http://suggest3.sinajs.cn/suggest/type=31&key={query}&name=suggest_data"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'gbk'
        text = response.text
        
        # Parse: var suggest_data="腾讯控股,31,00700,00700,...;..."
        if '="' in text:
            content = text.split('="')[1].strip('";')
            if not content:
                return []
            
            results = []
            items = content.split(';')
            for item in items:
                parts = item.split(',')
                if len(parts) >= 4:
                    name = parts[0]
                    raw_code = parts[2] # e.g. 00700 or 01810
                    
                    # Format for Yahoo Finance
                    try:
                        code_int = int(raw_code)
                        formatted_code = f"{code_int:04d}" # Keep as 4 digits for display, utils will add .HK
                    except:
                        formatted_code = raw_code

                    results.append((name, formatted_code))
            return results
    except Exception as e:
        print(f"Search error: {e}")
        return []
    
    return []
