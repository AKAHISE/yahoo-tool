import bcrypt

# 暗号化したいパスワード
password = "abc123"

# パスワードをバイト列に変換してハッシュ化
# streamlit-authenticatorと同じ暗号化方式(bcrypt)を使います
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

print("--- 以下の文字列をコピーして config.yaml に貼り付けてください ---")
print(hashed.decode('utf-8'))
print("-------------------------------------------------------")