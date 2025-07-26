import streamlit as st
import pandas as pd
import os
from datetime import datetime

# データ保存用CSVのパス
DATA_PATH = "data/records.csv"
os.makedirs("data", exist_ok=True)

# CSVが存在しない場合はヘッダー付きで作成
if not os.path.exists(DATA_PATH):
    df_init = pd.DataFrame(columns=["日付", "金額", "種別", "カテゴリ", "タグ", "メモ"])
    df_init.to_csv(DATA_PATH, index=False)

# Streamlit アプリ
st.title("📒 家計簿アプリ（ベータ版）")

st.subheader("収入・支出の記録")

# 入力フォーム
with st.form("entry_form"):
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("日付", datetime.today())
        amount = st.number_input("金額（円）", min_value=0)
        kind = st.radio("種別", ["支出", "収入"])
    with col2:
        category = st.selectbox("カテゴリ", ["食費", "交通費", "交際費", "給与", "その他"])
        tag = st.text_input("タグ（例：プライベート、仕事）")
        note = st.text_input("メモ")

    submitted = st.form_submit_button("保存")
    if submitted:
        new_record = pd.DataFrame([{
            "日付": date.strftime("%Y-%m-%d"),
            "金額": int(amount),
            "種別": kind,
            "カテゴリ": category,
            "タグ": tag,
            "メモ": note
        }])
        new_record.to_csv(DATA_PATH, mode="a", header=False, index=False)
        st.success("保存しました！")

st.subheader("📊 入力履歴")

# 履歴表示
df = pd.read_csv(DATA_PATH)
st.dataframe(df[::-1])  # 新しい順に表示

st.subheader("💰 支出・収入の合計")

if not df.empty:
    total_expense = df[df["種別"] == "支出"]["金額"].sum()
    total_income = df[df["種別"] == "収入"]["金額"].sum()
    st.write(f"🔴 総支出：{total_expense:,} 円")
    st.write(f"🟢 総収入：{total_income:,} 円")

    st.subheader("🏷️ タグ別の支出合計")
    tag_expense = df[df["種別"] == "支出"].groupby("タグ")["金額"].sum()
    st.bar_chart(tag_expense)

    # タグ絞り込み
    unique_tags = df["タグ"].dropna().unique().tolist()
    selected_tag = st.selectbox("タグで履歴を絞り込み", ["（全て）"] + unique_tags)
    if selected_tag != "（全て）":
        filtered_df = df[df["タグ"] == selected_tag]
        st.dataframe(filtered_df[::-1])

st.subheader("📈 プライベート支出の進捗")

# 上限金額を設定
private_limit = st.number_input("プライベート支出の上限（円）", min_value=1000, value=50000, step=1000)

# プライベート支出の抽出（種別=支出 かつ タグ=プライベート）
private_df = df[(df["種別"] == "支出") & (df["タグ"].str.contains("プライベート", na=False))]

# 合計金額
private_total = private_df["金額"].sum()

# 割合計算
progress = min(private_total / private_limit, 1.0)

# 表示
st.write(f"現在のプライベート支出：{private_total:,} 円 / {private_limit:,} 円")
st.progress(progress)

import plotly.express as px

if private_limit > 0:
    fig = px.pie(
        names=["使った分", "残り"],
        values=[private_total, max(private_limit - private_total, 0)],
        title="プライベート支出の割合",
        hole=0.4
    )
    st.plotly_chart(fig)
