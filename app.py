import streamlit as st
import pandas as pd
import time
import random
import re
import os
from urllib.parse import unquote

# --- Selenium関連 ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- ブラウザ設定（クラウド対応版） ---
def get_driver():
    options = Options()
    options.add_argument("--headless") # 画面なし
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,1080")
    # 人間に見せかける設定
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    # 自動操作と見破られないための呪文
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# --- 解析ロジック ---
def analyze_yahoo(keyword, driver):
    result = {"キーワード": keyword, "allintitle件数": "0"}
    try:
        # 100件表示モードで検索（精度向上のため）
        url = f"https://search.yahoo.co.jp/search?p=allintitle:\"{keyword}\"&n=100"
        driver.get(url)
        time.sleep(random.uniform(3.0, 5.0)) # 慎重に待機

        # 件数表示の部分を特定
        try:
            # ページ全体のテキストを取得
            body_text = driver.find_element(By.TAG_NAME, "body").text
            # 「約1,234件」や「1件〜10件」の数字を抽出
            match = re.search(r'([\d,]+)\s*件', body_text)
            
            if match:
                count = match.group(1).replace(',', '')
                # 実際に検索結果のタイトルが並んでいるか確認
                items = driver.find_elements(By.CSS_SELECTOR, "h3")
                real_count = len([i for i in items if i.is_displayed()])
                
                if real_count == 0 and int(count) > 0:
                    result["allintitle件数"] = "0 (不一致)"
                else:
                    result["allintitle件数"] = count
            elif "一致するウェブページは見つかりませんでした" in body_text:
                result["allintitle件数"] = "0"
        except:
            result["allintitle件数"] = "取得失敗"
            
    except Exception as e:
        result["allintitle件数"] = "エラー"
    return result

# --- メイン画面 ---
def main():
    st.set_page_config(page_title="Yahoo高精度分析", layout="wide")
    
    # 簡易ログイン（Secretsを利用）
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

    # メインコンテンツ
    st.title("🔍 Yahoo! allintitle高精度分析")
    st.write("Seleniumエンジンを使用して、実際の検索結果を1件ずつ確認します。")
    
    raw_text = st.text_area("キーワードを1行ずつ入力", height=200)
    target_list = [line.strip() for line in raw_text.split('\n') if line.strip()]

    if st.button("調査開始"):
        if not target_list:
            st.warning("キーワードを入力してください")
            return

        status = st.empty()
        status.info("🚀 ブラウザエンジンを起動中... (約10秒かかります)")
        
        try:
            driver = get_driver()
            results = []
            bar = st.progress(0)
            
            for i, kw in enumerate(target_list):
                status.info(f"🔎 調査中 ({i+1}/{len(target_list)}): {kw}")
                data = analyze_yahoo(kw, driver)
                results.append(data)
                bar.progress((i + 1) / len(target_list))
                # ブロック回避のために待機
                time.sleep(random.uniform(2.0, 4.0))
            
            status.success("✅ 全キーワードの調査が完了しました！")
            df = pd.DataFrame(results)
            st.table(df)
            
        except Exception as e:
            st.error(f"起動エラー: {e}")
        finally:
            if 'driver' in locals():
                driver.quit()

if __name__ == "__main__":
    main()
