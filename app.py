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

# --- 設定: 監視ターゲット（ローカル版と同じ構成） ---
QA_DOMAINS = ["detail.chiebukuro.yahoo.co.jp"]
BLOG_DOMAINS = [
    "ameblo.jp", 
    "hatenablog.com", "hatenablog.jp", "hatena.blog",
    "note.com", "note.mu"
]

# --- ブラウザ設定（Mac偽装・クラウド対応版） ---
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,1080")
    
    # ★ローカル版と同じ「Mac」のUser-Agentを使用！
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # クラウド環境のパス指定
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
        # --- 1. allintitle検索 ---
        # 100件表示モード(n=100)で取得
        driver.get(f"https://search.yahoo.co.jp/search?p=allintitle:\"{keyword}\"&n=100")
        time.sleep(random.uniform(2.0, 3.5))
        
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            
            # 「約◯件」の抽出（カンマ区切り対応）
            match = re.search(r'([\d,]+)\s*件', body_text)
            
            # 「一致するウェブページは見つかりませんでした」のチェック
            if "一致するウェブページは見つかりませんでした" in body_text:
                result["allintitle"] = "0"
            elif match:
                # 数字を正規化
                count_str = match.group(1).replace(',', '')
                result["allintitle"] = count_str
            else:
                result["allintitle"] = "0"
        except:
            result["allintitle"] = "取得失敗"

        # --- 2. 通常検索（順位チェック） ---
        driver.get(f"https://search.yahoo.co.jp/search?p={keyword}&ei=UTF-8")
        time.sleep(random.uniform(2.0, 3.5))
        
        # ローカル版と同じロジック（カード取得 -> タイトル抽出）
        # まずメインエリア
        try: main_area = driver.find_element(By.ID, "main")
        except: main_area = driver
        
        # 記事カードの取得（複数のクラスに対応）
        cards = main_area.find_elements(By.CSS_SELECTOR, "div.sw-CardBase")
        if len(cards) == 0: cards = main_area.find_elements(By.CSS_SELECTOR, "div.algo")
        if len(cards) == 0: cards = main_area.find_elements(By.XPATH, "//h3/ancestor::div[contains(@class, 'sw-CardBase') or position()=1]")

        valid_count = 0
        
        for card in cards:
            try:
                if not card.is_displayed(): continue
                
                # タイトルリンクの取得（ローカル版のロジックを踏襲）
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
                    card_text = card.text
                    
                    if raw_url:
                        url = unquote(raw_url)
                        
                        # ゴミ除外
                        if "search.yahoo.co.jp" in url: continue
                        if "help.yahoo.co.jp" in url: continue

                        if "http" in url:
                            valid_count += 1
                            
                            # 判定ロジック
                            detected_qa = False
                            detected_blog = False
                            
                            # 知恵袋チェック（URL + テキスト）
                            for qa_domain in QA_DOMAINS:
                                if qa_domain in url: detected_qa = True
                            if "Yahoo!知恵袋" in card_text: detected_qa = True
                            
                            if detected_qa: result["qa_flag"] = True
                            
                            # ブログチェック
                            for blog in BLOG_DOMAINS:
                                if blog in url: detected_blog = True
                            
                            if detected_blog: result["blog_flag"] = True
                            
                            # 診断ログ
                            result["debug_titles"].append(f"【{valid_count}位】{title_text[:10]}... ({url[:20]}...)")
            except: continue
            
            if valid_count >= 10: break

    except Exception as e:
        result["allintitle"] = "エラー"
        
    return result

# --- メイン画面 ---
def main():
    st.set_page_config(page_title="Yahoo高精度分析", layout="wide")
    
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
                st.error("認証失敗")
        return

    st.title("🔍 Yahoo! 徹底攻略ツール (Mac偽装版)")
    
    raw_text = st.text_area("キーワードを1行ずつ入力", height=200)
    target_list = [line.strip() for line in raw_text.split('\n') if line.strip()]

    if st.button("調査開始"):
        if not target_list: return

        status = st.empty()
        status.info("🚀 エンジン起動中...")
        
        try:
            driver = get_driver()
            results = []
            bar = st.progress(0)
            
            for i, kw in enumerate(target_list):
                status.info(f"🔎 調査中 ({i+1}/{len(target_list)}): {kw}")
                data = analyze_yahoo(kw, driver)
                results.append(data)
                bar.progress((i + 1) / len(target_list))
                time.sleep(random.uniform(2.0, 4.0))
            
            status.success("✅ 完了！")
            df = pd.DataFrame(results)
            
            # 結果表示の整形
            df['知恵袋'] = df['qa_flag'].apply(lambda x: 'あり' if x else '')
            df['無料ブログ'] = df['blog_flag'].apply(lambda x: 'あり' if x else '')
            
            st.dataframe(
                df[['keyword', 'allintitle', '知恵袋', '無料ブログ']],
                use_container_width=True
            )
            
            with st.expander("【答え合わせ】検出タイトル"):
                st.dataframe(df[['keyword', 'debug_titles']])
            
        except Exception as e:
            st.error(f"エラー: {e}")
        finally:
            if 'driver' in locals():
                driver.quit()

if __name__ == "__main__":
    main()
