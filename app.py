import streamlit as st

st.set_page_config(page_title="Yahoo Tool", layout="centered")

# ログイン機能
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    st.title("🔐 ログイン")
    user = st.text_input("Username")
    pw = st.text_input("Password", type="password")
    
    if st.button("Log in"):
        # Secretsからパスワードを読み込む
        if user == st.secrets["auth"]["username"] and pw == st.secrets["auth"]["password"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("パスワードが違います")
else:
    # ログイン成功後の画面
    st.title("✅ 起動成功！")
    st.success("GitHubの更新が正常に反映されました。")
    st.write("ここから機能を追加していきましょう。")
