import streamlit as st
import pandas as pd
import time
import random
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- ブラウザ設定（クラウド環境・安定版） ---
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    # 人間に見せかけるためのUser-Agent設定
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # クラウド上のChromiumとDriverを直接指定
    service = Service(executable_path="/usr/bin/chromedriver")
    options.binary_location = "/usr/bin/chromium"
    
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# --- 解析ロジック (超高精度・実数カウント版) ---
def analyze_yahoo(keyword, driver):
    result = {"キーワード": keyword, "allintitle件数": "0"}
    try:
        # 確実に100件表示させて、1ページ内で完結させる
        url = f"https://search.yahoo.co.jp/search?p=allintitle:\"{keyword}\"&n=100"
        driver.get(url)
        time.sleep(random.uniform(3.5, 5.5)) # じっくり待つ

        # 1. ページ内の「検索結果のタイトル(h3)」をすべて取得
        # Yahooの検索結果タイトルは通常 h3 タグの中にあります
        titles = driver.find_elements(By.CSS_SELECTOR, "h3")
        
        real_count = 0
        for t in titles:
            # 広告や「関連キーワード」を除外するため、リンクを持っているものだけカウント
            try:
                if t.find_element(By.TAG_NAME, "a"):
                    real_count += 1
            except:
                continue

        # 2. もし実数が0なら、念のため「一致する結果はありません」の文字を確認
        body_text = driver.find_element(By.TAG_NAME, "body").text
        
        if real_count > 0:
            result["allintitle件数"] = str(real_count)
        elif "一致するウェブページは見つかりませんでした" in body_text:
            result["allintitle件数"] = "0"
        else:
            # ページ上部の「約◯件」という文字も予備で探す
            match = re.search(r'約\s*([\d,]+)\s*件', body_text)
            if match:
                result["allintitle件数"] = match.group(1).replace(',', '')
            else:
                result["allintitle件数"] = "0"
            
    except Exception as e:
        result["allintitle件数"] = "再試行が必要"
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

    st.title("🔍 Yahoo! allintitle分析 (高精度Selenium版)")
    
    raw_text = st.text_area("キーワードを1行ずつ入力", height=200)
    target_list = [line.strip() for line in raw_text.split('\n') if line.strip()]

    if st.button("調査開始"):
        if not target_list:
            st.warning("キーワードを入力してください")
            return

        status = st.empty()
        status.info("🚀 高精度エンジンを起動中...")
        
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
            
            status.success("✅ 調査完了！")
            df = pd.DataFrame(results)
            st.table(df)
            
        except Exception as e:
            st.error(f"起動エラー: {e}")
        finally:
            if 'driver' in locals():
                driver.quit()

if __name__ == "__main__":
    main()
