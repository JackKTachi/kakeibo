import streamlit as st
import pandas as pd
import os
from datetime import datetime
from PIL import Image, ImageOps, ImageFilter
import numpy as np
import pytesseract
import plotly.express as px

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
        category = st.text_input("カテゴリ（自由入力）")
        tag = st.selectbox("タグ", ["プライベート", "生活費", "研究費", "仕事", "出張"])
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


# CSV読み込み
df = pd.read_csv(DATA_PATH)

st.subheader("📊 入力履歴")

if not df.empty:
    df_display = df.reset_index(drop=True)
    st.dataframe(df_display[::-1])  # 新しい順に表示

BACKUP_PATH = "data/records_backup.csv"

st.subheader("🗑️ データ削除（内容を選んで削除）")

if not df.empty:
    df_reset = df.reset_index(drop=True)
    df_reset["プレビュー"] = df_reset.apply(
        lambda row: f"{row['日付']} | {row['種別']} | {row['金額']}円 | {row['カテゴリ']} | {row['タグ']} | {row['メモ']}",
        axis=1
    )

    selected_preview = st.selectbox("削除したい記録を選んでください", df_reset["プレビュー"].tolist())
    delete_index = df_reset[df_reset["プレビュー"] == selected_preview].index[0]

    if st.button("この記録を削除する"):
        df_reset.drop(columns=["プレビュー"]).to_csv(BACKUP_PATH, index=False)  # バックアップ
        df_new = df_reset.drop(delete_index).drop(columns=["プレビュー"]).reset_index(drop=True)
        df_new.to_csv(DATA_PATH, index=False)
        st.success("✅ 指定された記録を削除しました。")
        st.rerun()

# 削除の取り消し機能
if os.path.exists(BACKUP_PATH):
    if st.button("↩️ 直前の削除を元に戻す"):
        backup_df = pd.read_csv(BACKUP_PATH)
        backup_df.to_csv(DATA_PATH, index=False)
        os.remove(BACKUP_PATH)
        st.success("✅ データを元に戻しました。")
        st.rerun()

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

private_limit = st.number_input("プライベート支出の上限（円）", min_value=1000, value=50000, step=1000)

private_df = df[(df["種別"] == "支出") & (df["タグ"].str.contains("プライベート", na=False))]
private_total = private_df["金額"].sum()
progress = min(private_total / private_limit, 1.0)

st.write(f"現在のプライベート支出：{private_total:,} 円 / {private_limit:,} 円")
st.progress(progress)

if private_limit > 0:
    fig = px.pie(
        names=["使った分", "残り"],
        values=[private_total, max(private_limit - private_total, 0)],
        title="プライベート支出の割合",
        hole=0.4
    )
    st.plotly_chart(fig)

st.subheader("📅 月ごとの集計")

if not df.empty:
    df["月"] = pd.to_datetime(df["日付"]).dt.to_period("M").astype(str)
    monthly_summary = df.groupby(["月", "種別"])["金額"].sum().reset_index()
    monthly_pivot = monthly_summary.pivot(index="月", columns="種別", values="金額").fillna(0)

    st.dataframe(monthly_pivot.style.format("{:,.0f} 円"))

    # グラフ表示
    st.bar_chart(monthly_pivot)
