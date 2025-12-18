import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import io
import re

# --- 🔒 [사용자 고정 설정] ---
# 사용자님이 제공하신 새로운 API 키 (Gemini 2.0 Flash Lite 사용용)
FIXED_API_KEY = 'AIzaSyBKeWH-ztYroAmyTk7KX9OxKHGqyKkD48k'
FIXED_SHEET_ID = '1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw'
# -------------------------

# --- 🎨 페이지 설정 ---
st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="🧞‍♂️", layout="wide")
st.title("🧞‍♂️ AI 마케팅 카피 생성기 (Gemini 2.0 Flash Lite)")
st.markdown(f"**[(광고) 표기 강제 적용]** + **[수신거부 문구 자동 삽입]** + **[Flash Lite 모델]** 버전입니다.")

# --- 👈 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정 확인")
    st.success("✅ (광고) 및 수신거부 자동 적용됨")
    st.info("⚡ 모델: Gemini 2.0 Flash Lite")
    
    sheet_id_input = st.text_input("구글 시트 ID", value=FIXED_SHEET_ID)
    sheet_gid_input = st.text_input("시트 GID (탭 번호)", value="0")

# --- 🔧 핵심 함수들 ---

def get_naver_search(keyword):
    """
    네이버 뉴스 크롤링 (보안 우회 헤더 적용)
    - 기존 코드보다 헤더를 강화하여 차단을 방지합니다.
    """
    try:
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sm=tab_opt&sort=1"
        # 봇 차단 방지를 위한 리얼 브라우저 헤더
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.naver.com/'
        }
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        news_list = []
        for item in soup.select(".news_area")[:5]:
            title = item.select_one('.news_tit').get_text()
            desc = item.select_one('.news_dsc').get_text()
            news_list.append(f"[{title}]: {desc}")
            
        return "\n".join(news_list) if news_list else "검색 결과 없음"
    except Exception as e:
        return f"크롤링 에러: {str(e)}"

def get_sheet_data(sheet_id, gid):
    """구글 시트 데이터 가져오기"""
    try:
        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'
        df = pd.read_csv(url, encoding='utf-8', on_bad_lines='skip')
        if df.empty: return None
        # 최신 50개 정도 가져와서 스타일 학습
        if len(df) > 50: df = df.tail(50)
        return df.to_markdown(index=False)
    except:
        return None

def generate_plan(api_key, context, keyword, info, user_config):
    """Gemini 2.0 Flash Lite 모델 호출"""
    genai.configure(api_key=api_key)
    
    # 1. 모델 설정: 요청하신 Flash Lite 모델을 우선 지정
    # (정확한 모델 ID: gemini-2.0-flash-lite-preview-02-05)
    model_name = 'gemini-2.0-flash-lite-preview-02-05'
    
    try:
        model = genai.GenerativeModel(model_name)
    except:
        # 혹시 모델명이 다를 경우를 대비해 기본 Flash로 백업
        model_name = 'gemini-1.5-flash'
        model = genai.GenerativeModel(model_name)

    custom_instruction = ""
    if user_config['target']: custom_instruction += f"- 타겟: {user_config['target']}\n"
    if user_config['campaign']: custom_instruction += f"- 캠페인: {user_config['campaign']}\n"
    if user_config['note']: custom_instruction += f"- 요청사항: {user_config['note']}\n"

    if not context: context = "데이터 없음."

    # 프롬프트: 아까 만족하셨던 구조 유지 + 글자수/법적문구 가이드 강화
    prompt = f"""
    Role: Senior Viral Marketing Copywriter (Korea).
    
    [Mission]
    1. **STYLE CLONING:** Analyze the [Reference] data. Copy the tone, manner, and emoji usage exactly.
    2. Create 10 marketing messages for '{keyword}'.
    3. **STRICT LIMITS (CRITICAL):**
       - **Title:** UNDER 20 Korean characters. (Short & Impactful)
       - **Body:** **Exactly 40~50 characters (Excluding spaces).** (Note: Do NOT write '(광고)' or '*수신거부'. I will add them via code.)
    4. Apply [User Request].

    [Reference Data (Mimic this style)]
    {context}

    [News/Trends Info]
    {info}

    [User Request]
    {custom_instruction}

    [Output Format]
    대분류|캠페인|타겟|콘텐츠|제목|내용
    (CSV format with '|' separator. NO markdown code blocks.)
    """
    
    response = model.generate_content(prompt)
    return response.text, model_name

# --- 🖥️ 메인 화면 UI ---

col1, col2 = st.columns([2, 1])
with col1:
    keyword = st.text_input(":loudspeaker: 홍보할 주제", placeholder="예: 환승연애4")
with col2:
    campaign = st.text_input(":bookmark: 캠페인명", placeholder="예: 런칭알림")

col3, col4 = st.columns([1, 1])
with col3:
    target = st.text_input(":dart: 타겟 설정", placeholder="예: 2030 여성")
with col4:
    note = st.text_input(":memo: 요청사항", placeholder="예: 팩트 기반, 호기심 자극")

if st.button(":rocket: 기획안 생성 시작", type="primary"):
    if not keyword:
        st.warning("주제를 입력해주세요.")
    else:
        status_box = st.status("작업을 진행 중입니다...", expanded=True)
        
        status_box.write(":mag: 네이버 뉴스 검색 중 (보안 우회)...")
        search_info = get_naver_search(keyword)
        
        if "검색 결과 없음" in search_info or "에러" in search_info:
             status_box.write("⚠️ 뉴스 수집 실패 (일반 모드로 진행)")
        else:
             status_box.write("✅ 최신 뉴스 확보 완료!")
        
        status_box.write(":books: 구글 시트 학습 중...")
        sheet_data = get_sheet_data(sheet_id_input, sheet_gid_input)
        
        status_box.write(f":robot_face: Gemini 2.0 Flash Lite 가동...")
        try:
            config = {"campaign": campaign, "target": target, "note": note}
            raw_text, used_model = generate_plan(FIXED_API_KEY, sheet_data, keyword, search_info, config)
            
            # CSV 파싱
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            df = pd.read_csv(io.StringIO(clean_csv), sep='|')
            
            # ★ 법적 문구 및 글자수 제어 (파이썬 후처리) ★
            # 내용 컬럼 찾기
            content_cols = [c for c in df.columns if '내용' in c]
            if content_cols:
                content_col = content_cols[0]
                
                def final_formatter(text):
                    text = str(text).replace("(광고)", "").replace("*수신거부:설정>변경", "").strip()
                    # 본문이 너무 길면 자르기 (안전을 위해)
                    if len(text) > 60: text = text[:58] + ".."
                    return f"(광고) {text}\n*수신거부:설정>변경"

                df[content_col] = df[content_col].apply(final_formatter)
            
            status_box.update(label=f":white_check_mark: 완료! (모델: {used_model})", state="complete", expanded=False)
            
            st.subheader(":bar_chart: 생성된 마케팅 기획안")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(":inbox_tray: 엑셀 다운로드", csv, f"{keyword}_plan.csv", "text/csv")
            
        except Exception as e:
            status_box.update(label=":x: 오류", state="error")
            st.error(f"에러 내용: {e}")
