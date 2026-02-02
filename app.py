import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import utils
from datetime import datetime
import re

# 页面配置
st.set_page_config(
    page_title="港股智能分析系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 侧边栏
with st.sidebar:
    st.title("📊 港股分析设置")
    
    # Session state initialization
    if 'ticker_input' not in st.session_state:
        # Load from JSON if exists
        saved_tickers = utils.load_tickers_from_json()
        if saved_tickers:
            st.session_state.ticker_input = " ".join(saved_tickers)
        else:
            st.session_state.ticker_input = "0700 9988 3690"

    # Clean up new_ticker state if it was used to set default index
    # We do this at start of script so after the render where it was used, next rerun it is gone?
    # Actually, st.selectbox index is only used on initial render or when key changes.
    # To force update, we might need a unique key or rely on index change.
    # If we rely on index change, Streamlit updates the value.
    # Let's try clearing it if it's not the first run after add.
    # But how to track?
    # Simple way: just keep it. User changes manually, selectbox updates. 
    # If user adds another, new_ticker updates, index updates.
    # This seems fine.

    def add_ticker(code):
        current = st.session_state.ticker_input
        # Simple check to avoid duplicates (not perfect but works for simple case)
        if code not in current:
            new_input = current + f" {code}"
            st.session_state.ticker_input = new_input
            st.session_state.new_ticker = code # Mark for default selection
            # Save to JSON
            raw_tickers = re.split(r'[,\s\n]+', new_input)
            tickers = [t.strip() for t in raw_tickers if t.strip()]
            utils.save_tickers_to_json(tickers)

    # Search feature
    st.subheader("🔍 搜索添加股票")
    search_query = st.text_input("输入中文名称搜索 (如: 腾讯)", key="search_box")
    if search_query:
        with st.spinner("搜索中..."):
            results = utils.search_stock_sina(search_query)
            if results:
                st.write(f"找到 {len(results)} 个结果:")
                for name, code in results[:5]: # Show top 5
                    col_res1, col_res2 = st.columns([3, 1])
                    with col_res1:
                        st.write(f"{name} ({code})")
                    with col_res2:
                        if st.button("➕", key=f"add_{code}"):
                            add_ticker(code)
                            st.rerun()
            else:
                st.info("未找到相关股票")
    
    st.markdown("---")

    # Currency selection
    currency = st.radio("显示货币", ("HKD (港币)", "CNY (人民币)"), horizontal=True)
    currency_code = "HKD" if "HKD" in currency else "CNY"
    
    # Translation Toggle
    enable_translation = st.checkbox("🔤 开启AI中文翻译 (实验性)", value=False, help="使用翻译引擎将英文内容自动翻译为中文，可能会增加加载时间。")
    
    exchange_rate = 1.0
    if currency_code == "CNY":
        with st.spinner("获取汇率中..."):
            exchange_rate = utils.get_exchange_rate("HKD", "CNY")
        st.caption(f"当前汇率 HKD/CNY: {exchange_rate:.4f}")

    user_tickers = st.text_area("输入股票代码 (空格或逗号分隔)", key="ticker_input", help="例如: 0700 9988 1810")
    
    # 处理输入的股票代码 (支持空格、逗号、换行)
    raw_tickers = re.split(r'[,\s\n]+', user_tickers)
    tickers = [t.strip() for t in raw_tickers if t.strip()]
    
    # Save to JSON whenever tickers change (simple approach: save on every rerun if different from file)
    # Or just save current tickers
    if tickers:
        utils.save_tickers_to_json(tickers)
    
    # 股票列表展示
    if tickers:
        with st.expander("📋 已选股票列表", expanded=False):
            # Use cached sina name fetching
            @st.cache_data(ttl=3600)
            def fetch_names_batch(ticker_list):
                return utils.get_stock_names_sina(ticker_list)
                
            name_map = fetch_names_batch(tickers)
            
            stock_info_list = []
            for t in tickers:
                name = name_map.get(t, t)
                # If Sina failed (English name only), fallback to yfinance logic later or just use code
                stock_info_list.append({"代码": t, "名称": name})
            
            if stock_info_list:
                st.dataframe(pd.DataFrame(stock_info_list), hide_index=True, use_container_width=True)
                
                # Save detailed info to JSON as well (as requested)
                # We do this here because we already have the info loaded
                try:
                    import json
                    with open('stock_details.json', 'w', encoding='utf-8') as f:
                        json.dump({'stocks': stock_info_list}, f, indent=4, ensure_ascii=False)
                except:
                    pass

    col_period, col_interval = st.columns(2)
    with col_period:
        period = st.selectbox(
            "分析周期",
            ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"),
            index=5
        )
    with col_interval:
        interval = st.selectbox(
            "时间粒度 (Interval)",
            ("1m", "5m", "15m", "30m", "60m", "1d", "1wk", "1mo"),
            index=5
        )
    
    # 简单的有效性检查提示
    if interval in ['1m', '5m', '15m', '30m', '60m'] and period not in ['1d', '5d', '7d']:
        st.warning("⚠️ 注意: 分钟级数据通常只支持短期周期 (如 1d, 5d)。如果图表加载失败，请缩短分析周期。")
    
    st.markdown("---")
    st.markdown("### 关于系统")
    st.info(
        "本系统基于 yfinance 和 ta 库构建。\n"
        "提供港股实时行情、技术指标分析及投资组合概览。"
    )

# 处理输入的股票代码 (moved to sidebar)
# tickers = [t.strip() for t in user_tickers.split(',') if t.strip()]

# 主界面
st.title("📈 港股智能分析与趋势预测系统")
st.markdown(f"**当前日期:** {datetime.now().strftime('%Y-%m-%d')}")

if not tickers:
    st.warning("请在侧边栏输入股票代码以开始分析。")
    st.stop()

# 创建Tabs
tab1, tab2, tab3, tab4 = st.tabs(["🔍 个股深度分析", "💼 投资组合概览", "📰 市场动态", "👥 股东与大户"])

# --- Tab 1: 个股深度分析 ---
with tab1:
    # Prepare ticker options with names
    ticker_options = tickers
    ticker_display_map = {}
    
    # Try to reuse the name_map from sidebar if available, otherwise fetch again (cached)
    if 'name_map' in locals():
        current_name_map = name_map
    else:
        current_name_map = utils.get_stock_names_sina(tickers)
        
    ticker_options_display = []
    for t in tickers:
        n = current_name_map.get(t, t)
        display = f"{t} - {n}"
        ticker_options_display.append(display)
        ticker_display_map[display] = t

    # Determine default index
    default_index = 0
    if 'new_ticker' in st.session_state and st.session_state.new_ticker in tickers:
        try:
            default_index = tickers.index(st.session_state.new_ticker)
            # clear it so it doesn't stick
            # del st.session_state.new_ticker # Don't delete immediately if we want it to persist across one rerun
        except:
            pass
            
    selected_display = st.selectbox("选择要分析的股票", ticker_options_display, index=default_index)
    selected_ticker = ticker_display_map.get(selected_display)
    
    if selected_ticker:
        # Force refresh button
        col_title, col_refresh = st.columns([4, 1])
        with col_title:
            st.write(f"正在分析: **{selected_ticker}**")
        with col_refresh:
            if st.button("🔄 刷新数据", key="refresh_individual"):
                st.rerun()

        with st.spinner(f"正在加载 {selected_ticker} 数据..."):
            # 获取数据 (尝试获取最新实时数据)
            df = utils.get_stock_data(selected_ticker, period, interval)
            info = utils.get_stock_info(selected_ticker)
            
            # 获取实时价格 (额外请求一次 1d/1m 数据以确保实时性)
            # 如果主数据已经是 1d 或更短，且是最近的，其实可以复用
            realtime_price_data = utils.get_stock_data(selected_ticker, period="1d", interval="1m")
            
            if df is not None and not df.empty:
                # Use realtime data for current price if available and newer
                current_price = df['Close'].iloc[-1]
                prev_price = df['Close'].iloc[-2] if len(df) > 1 else df['Open'].iloc[0]
                
                if realtime_price_data is not None and not realtime_price_data.empty:
                    rt_price = realtime_price_data['Close'].iloc[-1]
                    # If the date is newer or same day but different time (hard to check without timezone align), assume rt is better
                    # But for simplicity, let's just use the realtime query result for the price metric
                    current_price = rt_price
                    # Re-calculate change based on previous close from daily data
                    # Or use realtime data's open? No, change is usually vs Prev Close.
                    # info['previousClose'] is reliable
                    prev_close = info.get('previousClose', prev_price)
                
                change = current_price - prev_close
                pct_change = (change / prev_close) * 100
                
                # Currency conversion
                display_price = current_price * exchange_rate
                display_change = change * exchange_rate
                
                # 计算指标
                df = utils.calculate_technical_indicators(df)

                # 显示基本信息
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(f"当前价格 ({currency_code})", f"{display_price:.2f}", f"{display_change:.2f} ({pct_change:.2f}%)")
                with col2:
                    st.metric("行业", info.get('industry', 'N/A'))
                with col3:
                    mkt_cap = info.get('marketCap', 0) * exchange_rate
                    st.metric(f"市值 ({currency_code})", f"{mkt_cap/1e9:.2f} B")
                with col4:
                    pe = info.get('trailingPE', 'N/A')
                    st.metric("市盈率 (PE)", f"{pe:.2f}" if isinstance(pe, (int, float)) else pe)
                
                # 绘制K线图和技术指标
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                    vertical_spacing=0.03, subplot_titles=(f'{selected_ticker} K线图 & 布林带 & 均线', 'RSI & MACD'), 
                                    row_width=[0.2, 0.7])

                # Candlestick
                fig.add_trace(go.Candlestick(x=df.index,
                                open=df['Open'],
                                high=df['High'],
                                low=df['Low'],
                                close=df['Close'],
                                name='K线'), row=1, col=1)
                
                # Bollinger Bands
                fig.add_trace(go.Scatter(x=df.index, y=df['BB_High'], line=dict(color='gray', width=1, dash='dash'), name='布林带上轨'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], line=dict(color='gray', width=1, dash='dash'), name='布林带下轨', fill='tonexty'), row=1, col=1)
                
                # MA Lines
                fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='orange', width=1), name='20日均线'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], line=dict(color='blue', width=1), name='50日均线'), row=1, col=1)

                # RSI (Optional, putting MACD here instead or separate)
                # Let's put MACD in the second row
                fig.add_trace(go.Bar(x=df.index, y=df['MACD_Diff'], name='MACD柱', marker_color='grey'), row=2, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='MACD线', line=dict(color='purple')), row=2, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], name='信号线', line=dict(color='orange')), row=2, col=1)

                fig.update_layout(xaxis_rangeslider_visible=False, height=700)
                st.plotly_chart(fig, use_container_width=True, key="technical_chart")
                
                # 增强版智能趋势分析
                st.subheader("🤖 AI 智能趋势深度解析")
                
                last_close = df['Close'].iloc[-1]
                prev_close = df['Close'].iloc[-2]
                sma20 = df['SMA_20'].iloc[-1]
                sma50 = df['SMA_50'].iloc[-1]
                rsi = df['RSI'].iloc[-1]
                macd = df['MACD'].iloc[-1]
                macd_signal = df['MACD_Signal'].iloc[-1]
                bb_high = df['BB_High'].iloc[-1]
                bb_low = df['BB_Low'].iloc[-1]
                
                analysis_points = []
                
                # 1. 均线系统分析
                if last_close > sma20 and last_close > sma50:
                    ma_status = "多头排列"
                    ma_desc = "股价稳居20日和50日均线上方，短期与中期趋势均表现强势，属于典型的上升通道。"
                elif last_close < sma20 and last_close < sma50:
                    ma_status = "空头排列"
                    ma_desc = "股价受制于20日和50日均线压制，市场情绪偏弱，处于下跌趋势中。"
                elif last_close > sma20:
                    ma_status = "短期反弹"
                    ma_desc = "股价站上20日均线，显示短期有反弹迹象，但需关注上方50日均线压力。"
                else:
                    ma_status = "短期回调"
                    ma_desc = "股价跌破20日均线，短期可能面临调整，下方关注50日均线支撑。"
                
                analysis_points.append(f"**📈 均线趋势 ({ma_status}):** {ma_desc}")
                
                # 2. 布林带分析
                if last_close > bb_high:
                    bb_desc = "股价突破布林带上轨，表明短期上涨动能极强，但也需警惕乖离率过大带来的回调风险。"
                elif last_close < bb_low:
                    bb_desc = "股价跌破布林带下轨，处于极端弱势区域，可能存在超跌反弹机会。"
                else:
                    bb_pos = (last_close - bb_low) / (bb_high - bb_low) * 100
                    bb_desc = f"股价处于布林带通道内部 (位置: {bb_pos:.1f}%)，波动相对正常。"
                    if bb_high - bb_low < last_close * 0.05:
                        bb_desc += " 通道收窄，预示着变盘在即。"
                
                analysis_points.append(f"**📉 布林带形态:** {bb_desc}")

                # 3. 动能与摆动指标 (RSI & MACD)
                rsi_status = "中性"
                if rsi > 70: rsi_status = "超买 🔥"
                elif rsi < 30: rsi_status = "超卖 ❄️"
                
                macd_status = "金叉 🟢" if macd > macd_signal else "死叉 🔴"
                macd_desc = "MACD线上穿信号线，发出买入信号。" if macd > macd_signal else "MACD线下穿信号线，发出卖出信号。"
                if macd > 0 and macd_signal > 0:
                    macd_desc += " 且MACD处于零轴上方，多头主导。"
                elif macd < 0 and macd_signal < 0:
                    macd_desc += " 且MACD处于零轴下方，空头主导。"
                
                analysis_points.append(f"**📊 动能指标:** RSI为 {rsi:.1f} ({rsi_status})。MACD呈现 {macd_status}，{macd_desc}")

                # 4. 综合建议
                score = 0
                if last_close > sma20: score += 1
                if last_close > sma50: score += 1
                if rsi < 70 and rsi > 40: score += 1
                if macd > macd_signal: score += 1
                if last_close > prev_close: score += 0.5
                
                recommendation = ""
                if score >= 4:
                    recommendation = "🌟 **综合评级: 积极看多** - 各项指标配合良好，可考虑逢低介入或持有。"
                elif score <= 1:
                    recommendation = "⚠️ **综合评级: 谨慎观望** - 技术面偏弱，建议等待趋势明朗。"
                else:
                    recommendation = "👀 **综合评级: 中性持有** - 多空力量胶着，建议关注关键支撑/压力位的得失。"
                
                st.markdown("\n\n".join(analysis_points))
                st.success(recommendation)

                # --- 🏢 公司简介 (Company Profile) ---
                st.subheader("🏢 公司简介")
                if 'longBusinessSummary' in info:
                    summary = info['longBusinessSummary']
                    if enable_translation:
                        with st.spinner("正在翻译公司简介..."):
                            summary = utils.translate_text(summary)
                    
                    with st.expander("查看详细简介", expanded=True):
                        st.write(summary)
                else:
                    st.info("暂无公司简介信息")

                # --- 🔮 机构观点与未来展望 ---
                st.subheader("🔮 机构观点与未来展望")
                
                # 提取分析师数据
                target_mean = info.get('targetMeanPrice')
                current_price_raw = df['Close'].iloc[-1]
                
                rec_key_raw = info.get('recommendationKey', 'N/A').replace('_', ' ').upper()
                rec_map = {
                    'STRONG BUY': '强力买入',
                    'BUY': '买入',
                    'HOLD': '持有',
                    'UNDERPERFORM': '跑输大盘',
                    'SELL': '卖出',
                    'STRONG SELL': '强力卖出',
                    'N/A': '暂无数据'
                }
                rec_key = rec_map.get(rec_key_raw, rec_key_raw)
                
                rec_mean = info.get('recommendationMean')
                num_analysts = info.get('numberOfAnalystOpinions', 0)
                
                # 提取基本面增长数据
                rev_growth = info.get('revenueGrowth')
                earnings_growth = info.get('earningsGrowth')
                fwd_pe = info.get('forwardPE')
                trail_pe = info.get('trailingPE')
                roe = info.get('returnOnEquity')
                gross_margin = info.get('grossMargins')

                col_outlook1, col_outlook2 = st.columns(2)
                
                with col_outlook1:
                    st.markdown("#### 📢 机构评级")
                    if rec_key != 'N/A':
                        st.metric("分析师共识", rec_key, f"基于 {num_analysts} 位分析师" if num_analysts else None)
                        
                        # 目标价潜力
                        if target_mean and current_price_raw:
                            upside = ((target_mean - current_price_raw) / current_price_raw) * 100
                            st.metric("平均目标价", f"{target_mean:.2f} HKD", f"潜力: {upside:+.2f}%")
                            if upside > 20:
                                st.success("🚀 目标价显示有显著上涨空间")
                            elif upside < 0:
                                st.error("⚠️ 当前价格已高于平均目标价")
                    else:
                        st.info("暂无机构评级数据")

                with col_outlook2:
                    st.markdown("#### 🔭 未来增长与估值")
                    fund_points = []
                    
                    # 增长性
                    if rev_growth:
                        fund_points.append(f"**营收增长:** {rev_growth*100:.1f}% (同比)")
                    if earnings_growth:
                        fund_points.append(f"**盈利增长:** {earnings_growth*100:.1f}% (同比)")
                    
                    # 估值趋势
                    if fwd_pe and trail_pe:
                        if fwd_pe < trail_pe:
                            fund_points.append(f"**估值展望:** 预期市盈率 ({fwd_pe:.1f}) 低于当前 ({trail_pe:.1f})，暗示未来盈利预期向好。")
                        else:
                            fund_points.append(f"**估值展望:** 预期市盈率 ({fwd_pe:.1f}) 高于当前，需关注增长能否支撑高估值。")
                    
                    # 盈利能力
                    if roe:
                        fund_points.append(f"**ROE (净资产收益率):** {roe*100:.1f}%")
                    if gross_margin:
                        fund_points.append(f"**毛利率:** {gross_margin*100:.1f}%")
                        
                    if fund_points:
                        for p in fund_points:
                            st.markdown(f"- {p}")
                    else:
                        st.info("暂无详细基本面预测数据")

            else:
                st.error("无法获取数据，请检查股票代码是否正确。")

# --- Tab 2: 投资组合概览 ---
with tab2:
    st.subheader(f"📊 实时行情与组合对比 ({currency_code})")
    
    # Auto-refresh or manual refresh
    if st.button("🔄 刷新行情"):
        st.rerun()

    quotes_data = []
    # Use progress bar for better UX
    progress_bar = st.progress(0)
    
    for i, t in enumerate(tickers):
        # Fetch 1 month data to calculate change
        d = utils.get_stock_data(t, period="1mo") 
        info = utils.get_stock_info(t)
        
        if d is not None and not d.empty:
            last_price = d['Close'].iloc[-1]
            start_price = d['Close'].iloc[0] # 1mo ago price approx
            prev_close = d['Close'].iloc[-2] # Yesterday close
            
            day_change = last_price - prev_close
            day_pct = (day_change / prev_close) * 100
            
            month_pct = (last_price - start_price) / start_price * 100
            
            name = info.get('shortName', t)
            
            quotes_data.append({
                "代码": t,
                "名称": name,
                "最新价": last_price * exchange_rate,
                "日涨跌": day_change * exchange_rate,
                "日涨跌幅%": day_pct,
                "月涨跌幅%": month_pct,
                "成交量": d['Volume'].iloc[-1]
            })
        progress_bar.progress((i + 1) / len(tickers))
    
    progress_bar.empty()
    
    if quotes_data:
        quotes_df = pd.DataFrame(quotes_data)
        
        # Style the dataframe
        def color_change(val):
            color = 'green' if val > 0 else 'red' if val < 0 else 'black'
            return f'color: {color}'

        st.dataframe(
            quotes_df.style.format({
                "最新价": "{:.2f}", 
                "日涨跌": "{:.2f}",
                "日涨跌幅%": "{:.2f}%", 
                "月涨跌幅%": "{:.2f}%",
                "成交量": "{:,.0f}"
            }).map(color_change, subset=['日涨跌', '日涨跌幅%', '月涨跌幅%']),
            use_container_width=True
        )
        
        # Bar chart for comparison
        st.subheader("📈 涨跌幅对比")
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            fig_day = go.Figure(go.Bar(
                x=quotes_df['代码'],
                y=quotes_df['日涨跌幅%'],
                text=quotes_df['日涨跌幅%'].apply(lambda x: f"{x:.2f}%"),
                textposition='auto',
                marker_color=['green' if x > 0 else 'red' for x in quotes_df['日涨跌幅%']]
            ))
            fig_day.update_layout(title="今日涨跌幅 (%)", yaxis_title="涨跌幅 (%)")
            st.plotly_chart(fig_day, use_container_width=True, key="chart_day")
            
        with col_chart2:
            fig_month = go.Figure(go.Bar(
                x=quotes_df['代码'],
                y=quotes_df['月涨跌幅%'],
                text=quotes_df['月涨跌幅%'].apply(lambda x: f"{x:.2f}%"),
                textposition='auto',
                marker_color=['green' if x > 0 else 'red' for x in quotes_df['月涨跌幅%']]
            ))
            fig_month.update_layout(title="本月涨跌幅 (%)", yaxis_title="涨跌幅 (%)")
            st.plotly_chart(fig_month, use_container_width=True, key="chart_month")

    else:
        st.warning("暂无有效数据")

# --- Tab 4: 股东与大户 ---
with tab4:
    st.subheader("👥 股东结构与大户交易")
    if selected_ticker:
        holders_data = utils.get_holders_data(selected_ticker)
        
        # 1. 主要股东概况 (Major Holders)
        st.markdown("#### 🏢 主要股东持股概况 (Major Holders)")
        major = holders_data.get('major_holders')
        if major is not None and not major.empty:
            # Major holders usually returns a DF with 0, 1 columns. 0 is value, 1 is text description
            try:
                # Rename columns for clarity
                # The raw data index is 0,1,2... and columns are [0, 1] usually
                # 0 is the percentage/number, 1 is the description
                major.columns = ["数值 (Value)", "描述 (Description)"]
                
                # Translate common descriptions
                desc_map = {
                    "% of Shares Held by All Insider": "内部人士持股比例 (Insider %)",
                    "% of Shares Held by Institutions": "机构持股比例 (Inst. %)",
                    "% of Float Held by Institutions": "机构持股占流通盘比例 (Inst. Float %)",
                    "Number of Institutions Holding Shares": "持股机构数量 (Inst. Count)"
                }
                major["描述 (Description)"] = major["描述 (Description)"].map(lambda x: desc_map.get(x, x))
                
                st.table(major)
            except:
                st.dataframe(major, use_container_width=True)
        else:
            st.info("暂无主要股东数据")
            
        st.markdown("---")

        # 2. 机构持股 (Institutional Holders)
        st.markdown("#### 🏦 前10大机构持股 (Top Institutional Holders)")
        inst = holders_data.get('institutional_holders')
        if inst is not None and not inst.empty:
            # Translate column names
            col_map_inst = {
                "Holder": "持有机构 (Holder)",
                "Shares": "持股数 (Shares)",
                "Date Reported": "报告日期 (Date)",
                "% Out": "持股比例 (%)",
                "Value": "市值 (Value)"
            }
            inst = inst.rename(columns=col_map_inst)
            
            # Translate Holder Names if enabled (slow but requested)
            if enable_translation and "持有机构 (Holder)" in inst.columns:
                 inst["持有机构 (Holder)"] = inst["持有机构 (Holder)"].apply(lambda x: utils.translate_text(x) if isinstance(x, str) else x)

            st.dataframe(inst, use_container_width=True)
        else:
            st.info("暂无机构持股数据")
            
        st.markdown("---")

        # 3. 内部人士交易 (Insider Transactions)
        st.markdown("#### 👔 内部人士交易 (Insider Transactions)")
        insider = holders_data.get('insider_transactions')
        if insider is not None and not insider.empty:
            try:
                # Translate column names
                col_map_insider = {
                    "Insider": "内部人士 (Insider)",
                    "Position": "职位 (Position)",
                    "URL": "链接 (URL)",
                    "Text": "描述 (Text)",
                    "Start Date": "开始日期 (Start)",
                    "Ownership": "所有权 (Ownership)",
                    "Value": "市值 (Value)",
                    "Shares": "股数 (Shares)"
                }
                # Filter/Rename columns if they exist
                cols_to_keep = [c for c in insider.columns if c in col_map_insider or c in ['Insider', 'Relation', 'Date', 'Transaction', 'Value', 'Shares']]
                insider_display = insider[cols_to_keep].copy()
                
                # Standardize some column names if they differ
                insider_display = insider_display.rename(columns={
                    "Relation": "职位 (Position)",
                    "Date": "日期 (Date)",
                    "Transaction": "交易类型 (Transaction)",
                    **col_map_insider
                })
                
                # --- Content Translation ---
                
                # 1. Position / Relation
                if "职位 (Position)" in insider_display.columns:
                    def translate_position(val):
                        if not isinstance(val, str): return val
                        val_lower = val.lower()
                        # Use dict for common ones first
                        if 'chief executive officer' in val_lower: return '首席执行官 (CEO)'
                        if 'chief financial officer' in val_lower: return '首席财务官 (CFO)'
                        if 'chief operating officer' in val_lower: return '首席运营官 (COO)'
                        if 'chief technology officer' in val_lower: return '首席技术官 (CTO)'
                        if 'vice president' in val_lower: return '副总裁'
                        if 'president' in val_lower: return '总裁'
                        if 'director' in val_lower: return '董事'
                        if 'chairman' in val_lower: return '董事长'
                        if 'secretary' in val_lower: return '秘书'
                        if 'officer' in val_lower: return '高管'
                        if '10% owner' in val_lower: return '持股10%以上大股东'
                        
                        # Fallback to AI translation if enabled
                        if enable_translation:
                            return utils.translate_text(val)
                        return val
                    
                    insider_display["职位 (Position)"] = insider_display["职位 (Position)"].apply(translate_position)

                # 2. Transaction Type
                if "交易类型 (Transaction)" in insider_display.columns:
                    trans_map = {
                        'Buy': '买入',
                        'Sell': '卖出',
                        'Sale': '出售',
                        'Purchase': '购买',
                        'Option Exercise': '期权行权',
                        'Grant': '授予',
                        'Award': '奖励',
                        'Gift': '赠与',
                        'Automatic Sell': '自动卖出'
                    }
                    # Partial match or exact match? usually exact words in yfinance
                    insider_display["交易类型 (Transaction)"] = insider_display["交易类型 (Transaction)"].map(lambda x: trans_map.get(x, x))

                # 3. Ownership Type
                if "所有权 (Ownership)" in insider_display.columns:
                    own_map = {
                        'Direct': '直接持有',
                        'Indirect': '间接持有',
                        'D': '直接',
                        'I': '间接'
                    }
                    insider_display["所有权 (Ownership)"] = insider_display["所有权 (Ownership)"].map(lambda x: own_map.get(x, x))
                
                st.dataframe(insider_display, use_container_width=True)
            except:
                st.dataframe(insider, use_container_width=True)
        else:
            st.info("暂无内部人士近期交易数据")
    else:
        st.warning("请先选择股票")
with tab3:
    st.subheader("📰 最新相关新闻")
    if selected_ticker:
        news = utils.get_news(selected_ticker)
        if news:
            # Translation warning/hint
            if enable_translation:
                 st.info("💡 已开启自动翻译，新闻标题将尝试显示为中文。")
                 
            for n in news[:5]:
                title = n.get('title', 'No Title')
                if enable_translation:
                    # Translate title
                    title = utils.translate_text(title)
                    
                link = n.get('link', '#')
                st.markdown(f"**[{title}]({link})**")
                
                publisher = n.get('publisher', 'Unknown')
                # Handle time (timestamp or ISO string)
                pub_time = n.get('pubDate') or n.get('providerPublishTime')
                time_str = "Unknown"
                
                if pub_time:
                    if isinstance(pub_time, int):
                        time_str = datetime.fromtimestamp(pub_time).strftime('%Y-%m-%d %H:%M')
                    else:
                        # Simple cleanup for ISO string
                        time_str = str(pub_time).replace('T', ' ').replace('Z', '')
                
                st.caption(f"来源: {publisher} | 发布时间: {time_str}")
                st.markdown("---")
        else:
            st.write("暂无新闻数据。")
