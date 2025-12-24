import streamlit as st
import pandas as pd
import time
import random
import re
from urllib.parse import unquote
import os

# --- Selenium関連 ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- 設定: 監視ターゲット（ご提示のリストをそのまま採用） ---
QA_DOMAINS = ["detail.chiebukuro.yahoo.co.jp"]

BLOG_DOMAINS = [
    "ameblo.jp",          # アメブロ
    "hatenablog.com",     # はてなブログ
    "hatenablog.jp",      # はてなブログ
    "hatena.blog",        # はてなブログ(独自)
    "note.com",           # note
    "note.mu"             # note旧
]

# --- ブラウザ設定（クラウド対応） ---
def get_driver():
    options = Options()
    options.add_argument("--headless") # クラウドでは必須
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # クラウド環境に合わせたドライバ設定
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# --- 解析ロジック（あなたのPCで成功したロジックを移植） ---
def analyze_yahoo_selenium(keyword, driver):
    result = {
        "keyword": keyword,
        "allintitle": None,
        "qa_flag": False,
        "blog_flag": False,
        "debug_titles": [] 
    }

    try:
        # 1. allintitle検索
        driver.get(f"https://search.yahoo.co.jp/search?p=allintitle:{keyword}&ei=UTF-8")
        time.sleep(random.uniform(2.0, 3.5))
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            match = re.search(r'([\d,]+)\s*件', body_text)
            if match:
                result["allintitle"] = int(match.group(1).replace(',', ''))
            elif "一致する情報は" in body_text:
                result["allintitle"] = 0
        except:
            pass

        # 2. 通常検索（順位チェック）
        driver.get(f"https://search.yahoo.co.jp/search?p={keyword}&ei=UTF-8")
        time.sleep(random.uniform(2.5, 4.0))
        
        # カード取得（ご提示のロジックを使用）
        try: main_area = driver.find_element(By.ID, "main")
        except: main_area = driver
        
        cards = main_area.find_elements(By.CSS_SELECTOR, "div.sw-CardBase")
        if len(cards) == 0: cards = main_area.find_elements(By.CSS_SELECTOR, "div.algo")
        # 予備のh3検索
        if len(cards) == 0: cards = main_area.find_elements(By.XPATH, "//h3/ancestor::div[contains(@class, 'sw-CardBase') or position()=1]")

        valid_count = 0
        
        for card in cards:
            try:
                if not card.is_displayed(): continue

                # タイトルリンクを探す（ご提示のロジック）
                title_link = None
                try: title_link = card.find_element(By.CSS_SELECTOR, "h3 a")
                except: pass
                
                if not title_link:
                    try: title_link = card.find_element(By.CSS_SELECTOR, "div[class*='Title'] a")
                    except: pass
                
                if not title_link:
                    try: 
                        links = card.find_elements(By.TAG_NAME, "a")
                        if links: title_link = links[0]
                    except: pass

                if title_link:
                    raw_url = title_link.get_attribute("href")
                    title_text = title_link.text.strip().replace("\n", "")
                    card_text = card.text # カード内の文字（Yahoo!知恵袋などの表記）
                    
                    if raw_url:
                        url = unquote(raw_url)
                        
                        # ゴミ除外
                        if "search.yahoo.co.jp" in url: continue
                        if "help.yahoo.co.jp" in url: continue

                        if "http" in url:
                            valid_count += 1
                            
                            # 判定開始
                            is_qa = False
                            is_blog = False
                            detected_name = ""

                            # 知恵袋判定
                            for qa_domain in QA_DOMAINS:
                                if qa_domain in url: is_qa = True
                            if "Yahoo!知恵袋" in card_text: is_qa = True
                            
                            if is_qa: result["qa_flag"] = True

                            # ブログ判定
                            for blog in BLOG_DOMAINS:
                                if blog in url:
                                    is_blog = True
                                    detected_name = blog
                            
                            if is_blog: result["blog_flag"] = True
                            
                            # 診断ログ
                            log_msg = f"【{valid_count}位】{title_text[:15]}..."
                            if is_qa: log_msg += " [知恵袋]"
                            elif is_blog: log_msg += f" [{detected_name}]"
                            else: log_msg += f" ({url[:20]}...)"
                            
                            result["debug_titles"].append(log_msg)
            
            except:
                continue
            
            if valid_count >= 10: break

    except Exception as e:
        st.error(f"エラー: {e}")
        
    return result

# --- メイン画面 ---
def main():
    st.set_page_config(page_title="Yahoo! KW分析ツール", layout="wide")
    
    # 簡易ログイン機能（安定版）
    if "auth" not in st.session_state:
        st.session_state.auth = False

    if not st.session_state.auth:
        st.title("🔐 ログイン")
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.button("Log in"):
            if user == st.secrets["auth"]["username"] and pw == st.secrets["auth"]["password"]:
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("パスワードが違います")
        return

    # メインコンテンツ
    st.title("Yahoo! KW分析ツール (完全移植版)")
    st.info("あなたのPCで成功したロジックをクラウド上で再現しています。")
    
    raw_text = st.text_area("キーワード貼り付け", height=200)
    target_list = [line.strip() for line in raw_text.split('\n') if line.strip()]

    if st.button("調査開始"):
        if not target_list: return
        
        st.success("ブラウザ起動中...")
        try:
            driver = get_driver()
            results = []
            bar = st.progress(0)
            
            for i, kw in enumerate(target_list):
                data = analyze_yahoo_selenium(kw, driver)
                results.append(data)
                bar.progress((i + 1) / len(target_list))
                time.sleep(1.0)
            
            st.success("完了！")
            df = pd.DataFrame(results)
            
            if not df.empty:
                df['allintitle'] = df['allintitle'].astype('Int64')
                df['知恵袋'] = df['qa_flag'].apply(lambda x: 'あり' if x else '')
                df['無料ブログ'] = df['blog_flag'].apply(lambda x: 'あり' if x else '')
                
                st.dataframe(
                    df[['keyword', 'allintitle', '知恵袋', '無料ブログ']], 
                    use_container_width=True,
                    column_config={"allintitle": st.column_config.NumberColumn(format="%d")}
                )
                
                with st.expander("【答え合わせ】検出詳細"):
                    st.dataframe(df[['keyword', 'debug_titles']])
        finally:
            driver.quit()

if __name__ == "__main__":
    main()
