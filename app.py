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
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- 設定: 監視ターゲット ---
BLOG_DOMAINS = [
    "ameblo.jp", 
    "hatenablog.com", "hatenablog.jp", "hatena.blog",
    "note.com", "note.mu"
]

# --- ブラウザ設定 ---
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,1080")
    # Mac偽装
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(executable_path="/usr/bin/chromedriver")
    options.binary_location = "/usr/bin/chromium"
    
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# --- 解析ロジック ---
def analyze_yahoo(keyword, driver):
    result = {
        "keyword": keyword, 
        "allintitle": "0", 
        "qa_flag": False, 
        "blog_flag": False,
        "debug_titles": []
    }
    
    try:
        # 1. allintitle検索
        parts = keyword.replace("　", " ").split()
        intitle_query = " ".join([f"intitle:{p}" for p in parts if p.strip()])
        
        driver.get(f"https://search.yahoo.co.jp/search?p={intitle_query}&n=10")
        time.sleep(random.uniform(2.5, 4.0))
        
        body_text = driver.find_element(By.TAG_NAME, "body").text
        
        if "一致する情報は" in body_text and "見つかりませんでした" in body_text:
            result["allintitle"] = "0"
        else:
            match = re.search(r'約\s*([\d,]+)\s*件', body_text)
            if match:
                result["allintitle"] = match.group(1).replace(',', '')
            else:
                match_strict = re.search(r'([\d,]+)\s*件', body_text)
                if match_strict:
                    result["allintitle"] = match_strict.group(1).replace(',', '')
                else:
                    result["allintitle"] = "取得失敗"

        # 2. 通常検索（知恵袋・ブログ判定）
        driver.get(f"https://search.yahoo.co.jp/search?p={keyword}&ei=UTF-8")
        time.sleep(random.uniform(2.5, 4.0))
        
        try: main_area = driver.find_element(By.ID, "main")
        except: main_area = driver
        
        cards = main_area.find_elements(By.CSS_SELECTOR, "div.sw-CardBase")
        if len(cards) == 0: cards = main_area.find_elements(By.CSS_SELECTOR, "div.algo")
        
        valid_count = 0
        for card in cards:
            try:
                if not card.is_displayed(): continue
                
                title_links = card.find_elements(By.CSS_SELECTOR, "a")
                if not title_links: continue
                
                target_link = title_links[0]
                h3_link = card.find_elements(By.CSS_SELECTOR, "h3 a")
                if h3_link: target_link = h3_link[0]

                url = unquote(target_link.get_attribute("href"))
                text = card.text
                
                # ---------------------------------------------------
                # ★鉄壁の除外リスト（ここに追加すれば絶対無視します）
                # ---------------------------------------------------
                if "search.yahoo.co.jp" in url: continue
                if "help.yahoo.co.jp" in url: continue
                if "shopping.yahoo.co.jp" in url: continue # ショッピングを完全無視
                if "paypaymall" in url: continue

                if "http" in url:
                    valid_count += 1
                    
                    # ---------------------------------------------------
                    # ★知恵袋判定：detail.chiebukuro だけを許可
                    # ---------------------------------------------------
                    if "detail.chiebukuro.yahoo.co.jp" in url:
                        result["qa_flag"] = True
                        # 証拠ログ：なぜ判定したのかURLを記録
                        result["debug_titles"].append(f"★知恵袋検知: {url}")
                    
                    # ブログチェック
                    for blog in BLOG_DOMAINS:
                        if blog in url: 
                            result["blog_flag"] = True
                            result["debug_titles"].append(f"★ブログ検知: {url}")
                    
            except: continue
            if valid_count >= 10: break

    except Exception as e:
        result["allintitle"] = "エラー"
        
    return result

# --- メイン画面 ---
def main():
    st.set_page_config(page_title="Yahoo分析ツール", layout="wide")
    
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        st.title("🔐 ログイン")
        u = st.text_input("User")
        p = st.text_input("Pass", type="password")
        if st.button("Login"):
            if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]:
                st.session_state.auth = True
                st.rerun()
        return

    st.title("🔍 Yahoo! 徹底攻略ツール (誤検知防止版)")
    
    raw_text = st.text_area("キーワード入力", height=200)
    target_list = [line.strip() for line in raw_text.split('\n') if line.strip()]

    if st.button("調査開始"):
        if not target_list: return
        
        status = st.empty()
        status.info("🚀 起動中...")
        
        try:
            driver = get_driver()
            results = []
            bar = st.progress(0)
            
            for i, kw in enumerate(target_list):
                status.info(f"🔎 調査中 ({i+1}/{len(target_list)}): {kw}")
                data = analyze_yahoo(kw, driver)
                results.append(data)
                bar.progress((i + 1) / len(target_list))
                time.sleep(2)
            
            status.success("完了！")
            df = pd.DataFrame(results)
            
            df['知恵袋'] = df['qa_flag'].apply(lambda x: 'あり' if x else '-')
            df['無料ブログ'] = df['blog_flag'].apply(lambda x: 'あり' if x else '-')
            
            st.dataframe(
                df[['keyword', 'allintitle', '知恵袋', '無料ブログ']],
                use_container_width=True
            )
            
            # ★判定の証拠を表示するエリア（重要）
            with st.expander("🕵️‍♀️ なぜ「あり」になったの？（証拠URLを見る）"):
                st.write("「あり」と判定された場合、ここにそのURLが表示されます。")
                st.write(df[['keyword', 'debug_titles']])
            
        finally:
            if 'driver' in locals(): driver.quit()

if __name__ == "__main__":
    main()
