import yaml
import streamlit as st
import pandas as pd
import time
import random
import re
from urllib.parse import unquote, urlparse, parse_qs

# --- Selenium関連 ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ========= config.yaml 読み込み =========
def load_cfg(path="config.yaml"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

CFG = load_cfg()
RULES = (CFG.get("rules") or {})
SEARCH = ((CFG.get("search") or {}).get("yahoo") or {})

QA_DOMAINS = RULES.get("qa_domains", ["detail.chiebukuro.yahoo.co.jp"])
BLOG_DOMAINS = RULES.get("blog_domains", ["ameblo.jp", "hatenablog.com", "hatenablog.jp", "hatena.blog", "note.com", "note.mu"])
EXCLUDE_DOMAINS = RULES.get("exclude_domains", ["search.yahoo.co.jp", "help.yahoo.co.jp"])

TOP_N = int(SEARCH.get("top_n", 10))
SLEEP_MIN = float(SEARCH.get("sleep_min", 0.6))
SLEEP_MAX = float(SEARCH.get("sleep_max", 1.2))
ALLINTITLE_N = int(SEARCH.get("allintitle_n", 100))
# ======================================


# --- ブラウザ設定（Mac偽装・クラウド対応版） ---
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    service = Service(executable_path="/usr/bin/chromedriver")
    options.binary_location = "/usr/bin/chromium"
    return webdriver.Chrome(service=service, options=options)


# ===== 精度改善用ユーティリティ =====
def _normalize_host(url: str) -> str:
    try:
        p = urlparse(url)
        host = (p.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except:
        return ""

def _extract_real_url(href: str) -> str:
    if not href:
        return href
    href = unquote(href)

    if "search.yahoo.co.jp/r/" not in href:
        return href

    m = re.search(r"RU=([^/]+)", href)
    if m:
        cand = unquote(m.group(1))
        if cand.startswith("http"):
            return cand

    try:
        qs = parse_qs(urlparse(href).query)
        for k in ("RU", "ru", "u", "url"):
            if k in qs and qs[k]:
                cand = unquote(qs[k][0])
                if cand.startswith("http"):
                    return cand
    except:
        pass

    return href

def _host_matches(host: str, domain_list: list[str]) -> bool:
    for d in domain_list:
        d = d.lower().lstrip(".")
        if host == d or host.endswith("." + d):
            return True
    return False

def _get_allintitle_count(driver) -> str:
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    candidates = []
    for sel in ["#main", "div#main", "div.contents"]:
        try:
            candidates.append(driver.find_element(By.CSS_SELECTOR, sel).text)
        except:
            pass

    try:
        candidates.append(driver.find_element(By.TAG_NAME, "body").text)
    except:
        pass

    joined = "\n".join([c for c in candidates if c])

    if "一致するウェブページは見つかりませんでした" in joined:
        return "0"

    m = re.search(r"約?\s*([\d,]+)\s*件", joined)
    if m:
        return m.group(1).replace(",", "")

    m2 = re.search(r"([\d,]+)\s*件", joined)
    if m2:
        return m2.group(1).replace(",", "")

    return "0"
# ==============================


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
        wait = WebDriverWait(driver, 12)

        # --- 1) allintitle検索（★ALLINTITLE_Nを使う） ---
        driver.get(f'https://search.yahoo.co.jp/search?p=allintitle:"{keyword}"&n={ALLINTITLE_N}')
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))

        try:
            result["allintitle"] = _get_allintitle_count(driver)
        except:
            result["allintitle"] = "取得失敗"

        # --- 2) 通常検索（TopN） ---
        driver.get(f"https://search.yahoo.co.jp/search?p={keyword}&ei=UTF-8")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))

        try:
            main_area = driver.find_element(By.ID, "main")
        except:
            main_area = driver

        cards = main_area.find_elements(By.CSS_SELECTOR, "div.sw-CardBase")
        if not cards:
            cards = main_area.find_elements(By.CSS_SELECTOR, "div.algo")

        valid_count = 0

        for card in cards:
            if valid_count >= TOP_N:   # ★TOP_Nを使う
                break

            try:
                if not card.is_displayed():
                    continue

                card_text = (card.text or "")

                # 広告系除外
                if "広告" in card_text or "スポンサー" in card_text or "Sponsored" in card_text:
                    continue

                try:
                    title_link = card.find_element(By.CSS_SELECTOR, "h3 a")
                except:
                    try:
                        title_link = card.find_element(By.CSS_SELECTOR, "a")
                    except:
                        continue

                raw_href = title_link.get_attribute("href")
                title_text = (title_link.text or "").strip().replace("\n", "")
                if not raw_href:
                    continue

                url = _extract_real_url(raw_href)
                if not url.startswith("http"):
                    continue

                host = _normalize_host(url)

                # ★除外は host ベース＋configのEXCLUDE_DOMAINSを使う
                if _host_matches(host, EXCLUDE_DOMAINS):
                    continue

                valid_count += 1

                detected_qa =_
