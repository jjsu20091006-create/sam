# -*- coding: utf-8 -*-
"""
app.py
Streamlit 기반 CSV 데이터 분석 앱
- CSV 업로드 또는 기본 경로 불러오기
- 기본 통계, 결측치, 범주형 빈도, 숫자형 요약 자동 표시
- 시각화(히스토그램, 막대그래프) 포함

실행 방법:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import re
import matplotlib.font_manager as fm
from matplotlib import rc
import platform

# 한글 폰트 설정 (예: 맑은 고딕)
plt.rcParams['font.family'] = 'Malgun Gothic'  # Windows 기준
plt.rcParams['axes.unicode_minus'] = False     # 마이너스 기호 깨짐 방지

# 깃허브 리눅스 기준
if platform.system() == 'Linux':
    fontname = './NanumGothic.ttf'
    font_files = fm.findSystemFonts(fontpaths=fontname)
    fm.fontManager.addfont(fontname)
    fm._load_fontmanager(try_read_cache=False)
    rc('font', family='NanumGothic')


# ------------------------------------------------------------
# 헬퍼 함수들
# ------------------------------------------------------------

def smart_read_csv(path: Path):
    """인코딩을 자동으로 감지하며 CSV 읽기"""
    for enc in ["utf-8", "cp949", "euc-kr"]:
        try:
            df = pd.read_csv(path, encoding=enc)
            st.info(f"✅ CSV loaded with encoding='{enc}'")
            return df
        except Exception:
            continue
    st.error("❌ CSV 파일을 읽을 수 없습니다. 인코딩을 확인하세요.")
    return None

def clean_column_names(df):
    """컬럼 이름 정리"""
    cols = [str(c).replace("\n", " ").replace("\r", " ").strip() for c in df.columns]
    seen = {}
    new_cols = []
    for c in cols:
        if c not in seen:
            seen[c] = 0
            new_cols.append(c)
        else:
            seen[c] += 1
            new_cols.append(f"{c}_{seen[c]}")
    df.columns = new_cols
    return df

def coerce_datetimes(df, max_try=30, success_threshold=0.8):
    """날짜 형태로 보이는 컬럼 자동 변환"""
    common_formats = [
        "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d",
        "%d/%m/%Y", "%m/%d/%Y", "%Y-%m", "%Y/%m",
    ]

    def looks_date_like(s):
        if s.dtype != object:
            return False
        sample = s.dropna().astype(str).head(200)
        if sample.empty:
            return False
        pattern_hits = sum(
            bool(re.search(r"\d{4}[-/.]\d{1,2}([-/\.]\d{1,2})?", val)) or
            bool(re.fullmatch(r"\d{8}", val)) or
            bool(re.search(r"(년|월|일)", val))
            for val in sample
        )
        return pattern_hits / len(sample) >= 0.3

    for col in df.columns[:max_try]:
        s = df[col]
        if not looks_date_like(s):
            continue
        series_str = s.astype(str)
        converted = None
        for fmt in common_formats:
            try:
                parsed = pd.to_datetime(series_str, format=fmt, errors="raise")
                if (parsed.notna() & s.notna()).mean() >= success_threshold:
                    converted = pd.to_datetime(series_str, format=fmt, errors="coerce")
                    break
            except Exception:
                continue
        if converted is None:
            parsed = pd.to_datetime(series_str, errors="coerce")
            if (parsed.notna() & s.notna()).mean() >= success_threshold:
                converted = parsed
        if converted is not None:
            df[col] = converted
    return df

# ------------------------------------------------------------
# Streamlit UI
# ------------------------------------------------------------

st.set_page_config(page_title="CSV 데이터 분석 도구", layout="wide")

st.title("📊 CSV 데이터 분석 앱")
st.caption("Python + Streamlit 기반 | 자동 인코딩 감지 + 기본 통계 + 시각화")

# 파일 업로드
uploaded_file = st.file_uploader("분석할 CSV 파일을 업로드하세요", type=["csv"])

if uploaded_file:
    temp_path = Path("uploaded.csv")
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.read())
    df = smart_read_csv(temp_path)
else:
    default_path = Path(r"C:\Users\admin\Desktop\ㅇㅇㅇㅇ\2023년 정보화통계조사_마이크로데이터.csv")
    if default_path.exists():
        df = smart_read_csv(default_path)
        st.info("📁 기본 파일을 불러왔습니다.")
    else:
        st.warning("⚠️ CSV 파일을 업로드하거나, 기본 경로에 파일을 두세요.")
        df = None

# ------------------------------------------------------------
# 데이터 분석
# ------------------------------------------------------------
if df is not None:
    df = clean_column_names(df)
    df = coerce_datetimes(df)

    st.subheader("📋 데이터 미리보기")
    st.dataframe(df.head())

    st.subheader("📈 기본 정보")
    c1, c2, c3 = st.columns(3)
    c1.metric("행 개수", len(df))
    c2.metric("열 개수", len(df.columns))
    c3.metric("결측치 있는 열 수", df.isnull().any(axis=0).sum())

    with st.expander("🔎 컬럼별 프로필 보기"):
        profile = pd.DataFrame({
            "dtype": df.dtypes.astype(str),
            "missing_count": df.isnull().sum(),
            "missing_%": (df.isnull().mean() * 100).round(2),
            "nunique": df.nunique()
        })
        st.dataframe(profile)

    num_df = df.select_dtypes(include=["number"])
    cat_df = df.select_dtypes(exclude=["number", "datetime"])

    if not num_df.empty:
        st.subheader("📊 숫자형 요약 통계")
        st.dataframe(num_df.describe().T)

        st.subheader("📉 숫자형 히스토그램")
        selected_num = st.selectbox("히스토그램으로 볼 컬럼 선택", num_df.columns)
        fig, ax = plt.subplots()
        num_df[selected_num].dropna().hist(bins=30, ax=ax)
        ax.set_title(f"Histogram - {selected_num}")
        st.pyplot(fig)

    if not cat_df.empty:
        st.subheader("🧾 범주형 데이터 분석")
        selected_cat = st.selectbox("막대그래프로 볼 컬럼 선택", cat_df.columns)
        fig, ax = plt.subplots()
        cat_df[selected_cat].astype(str).value_counts().head(20).plot(kind="bar", ax=ax)
        ax.set_title(f"Top 20 categories - {selected_cat}")
        st.pyplot(fig)

    st.success("✅ 데이터 분석 완료!")

