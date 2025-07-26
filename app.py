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

# CSV読み込み
df = pd.read_csv(DATA_PATH)

st.subheader("📊 入力履歴")

if not df.empty:
    df_display = df.reset_index(drop=True)
    st.dataframe(df_display[::-1])  # 新しい順に表示

st.subheader("🗑️ データ削除（内容を選んで削除）")

if not df.empty:
    df_reset = df.reset_index(drop=True)

    # 表示用にプレビュー列を追加
    df_reset["プレビュー"] = df_reset.apply(
        lambda row: f"{row['日付']} | {row['種別']} | {row['金額']}円 | {row['カテゴリ']} | {row['タグ']} | {row['メモ']}",
        axis=1
    )

    selected_preview = st.selectbox("削除したい記録を選んでください", df_reset["プレビュー"].tolist())
    delete_index = df_reset[df_reset["プレビュー"] == selected_preview].index[0]

    if st.button("この記録を削除する"):
        df_new = df_reset.drop(delete_index).drop(columns=["プレビュー"]).reset_index(drop=True)
        df_new.to_csv(DATA_PATH, index=False)
        st.success("✅ 指定された記録を削除しました。")
        st.rerun()  # ✅ 再読み込みで最新状態に


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

""" import pytesseract
from PIL import Image

def preprocess_image(image):
    # グレースケール化のみ（最低限の前処理）
    gray = image.convert("L")

    # 解像度アップ：文字を拡大（1.5倍）
    width, height = gray.size
    resized = gray.resize((int(width * 1.5), int(height * 1.5)))

    # コントラスト強調は任意（つぶれるようならコメントアウト）
    # resized = ImageOps.autocontrast(resized)

    return resized


st.subheader("📷 レシート画像から読み取り（OCR）")

uploaded_file = st.file_uploader("画像をアップロード（JPEG/PNG）", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    from PIL import Image
    import re

    image = Image.open(uploaded_file)
    st.image(image, caption="元画像", use_container_width=True)

    # 前処理
    processed = preprocess_image(image)
    st.image(processed, caption="前処理後（グレースケール＋二値化）", use_container_width=True)

    # OCR処理
    ocr_text = pytesseract.image_to_string(processed, lang='jpn+eng')



    # OCRテキストの正規化
    clean_text = ocr_text
    clean_text = clean_text.replace("　", " ")  # 全角スペース → 半角
    clean_text = clean_text.replace("￥", "¥").replace("\\", "¥").replace("¥¥", "¥")
    clean_text = re.sub(r"\s+", " ", clean_text)  # 連続空白 → 1個に
    clean_text = clean_text.replace(",", "").replace(".", "")  # カンマ・ピリオド削除

    # 柔軟な「合計」＋空白＋任意の記号＋金額
    # キーワード：合計 / TOTAL / 支払金額 / 計 / 計（税込） など
    keywords = r"(合計|TOTAL|支払金額|支払い|計)"
    sum_match = re.search(
        rf"{keywords}[ ：:¥¥¥￥\\]*\s*([1-9]\d{{2,6}})",
        clean_text,
        re.IGNORECASE
    )

    if sum_match:
        extracted_amount = int(sum_match.group(2))
        st.success(f"💡 合計金額として検出: {extracted_amount:,} 円")
    else:
        # バックアップ：最大の金額を使う
        all_matches = re.findall(r"(?:¥)?([1-9]\d{2,6})", clean_text)
        if all_matches:
            extracted_amount = max(map(int, all_matches))
            st.info(f"🔍 合計が見つからなかったため、最大金額を候補として使用: {extracted_amount:,} 円")
        else:
            extracted_amount = None

    # 登録処理
    if extracted_amount is not None:
        if st.button("↑ この金額で支出登録する"):
            new_record = pd.DataFrame([{
                "日付": datetime.today().strftime("%Y-%m-%d"),
                "金額": extracted_amount,
                "種別": "支出",
                "カテゴリ": "未分類",
                "タグ": "OCR",
                "メモ": "OCR自動入力"
            }])
            new_record.to_csv(DATA_PATH, mode="a", header=False, index=False)
            st.success("✅ OCR結果を家計簿に登録しました！")
    else:
        st.warning("⚠️ 金額が見つかりませんでした。OCR結果を確認してください。")
        st.text_area("OCR結果（全文）", value=ocr_text, height=200) """