import streamlit as st

# 1. ページ設定（一番最初に書く必要があります）
st.set_page_config(page_title="Yahoo Tool", layout="centered")

# 2. ログインチェック機能
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.title("🔐 ログイン")
    user = st.text_input("Username")
    pw = st.text_input("Password", type="password")
    
    if st.button("Log in"):
        if user == st.secrets["auth"]["username"] and pw == st.secrets["auth"]["password"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("😕 ユーザー名またはパスワードが違います")
    return False

# 3. メイン画面
if check_password():
    st.title("🛍️ Yahooツール（準備完了）")
    st.success("ログインに成功しました！")
    st.info("ここから以前の『allintitle』や『知恵袋』の機能を1つずつ戻していきます。")
    
    # 動作確認用のテストボタン
    if st.button("現在の状態をテスト"):
        st.write("システムは正常に反応しています。")