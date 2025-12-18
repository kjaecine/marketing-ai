import streamlit as st
import pandas as pd
from groq import Groq
import requests
from bs4 import BeautifulSoup
import io
import re
import csv

# --- 🔒 [API 키 설정] ---
part1 = "gsk_lIDRWFZfRKNye7Il5egq"
part2 = "WGdyb3FY5WLFI3NtD9NB70RLy6uk4Mce"
FIXED_API_KEY = part1 + part2
FIXED_SHEET_ID = '1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw'
# -------------------------

st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="⚡", layout="wide")
st.title("⚡ AI 마케팅 카피 생성기 (Universal)")
st.markdown("주제 상관없이 작동하는 **범용 최적화 버전**입니다.")

# --- 👈 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정 확인")
    if FIXED_API_KEY.startswith("gsk_"):
        st.success("✅ Groq API Key 연결됨")
    
    sheet_id_input = st.text_input("구글 시트 ID", value=FIXED_SHEET_ID)
    sheet_gid_input = st.text_input("시트 GID (탭 번호)", value="0")

# --- 🔧 유틸리티: 텍스트 정제 (범용성 강화) ---
def clean_and_format_legal_text(text):
    """
    특정 주제(도파민 등)에 종속되지 않도록 
    하드코딩을 제거하고 깔끔하게 정제만 수행합니다.
    """
    if not isinstance(text, str): return str(text)
    
    # 1. 기존 법적 문구 제거 (중복 방지)
    text = text.replace("(광고)", "").replace("(광고 )", "")
    text = text.replace("*수신거부:설정>변경", "").replace("*수신거부 : 설정 > 변경", "")
    
    # 2. 외국어/특수문자 청소
    foreign_pattern = re.compile(r'[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF\u0600-\u06FF]+')
    text = foreign_pattern.sub('', text)
    
    # 3. 앞뒤 공백 제거
    text = text.strip()
    
    # 4. [수정됨] 내용이 너무 짧을 때(20자 미만) 붙는 문구를 '범용적'으로 변경
    # "도파민 충전" -> 삭제. 
    # 대신 너무 짧으면 가독성을 위해 점(...)만 찍거나, 아주 중립적인 문구 사용
    if len(text) < 15:
        text += "... 더 자세한 내용은 링크에서!"
        
    # 5. 법적 문구 부착 (필수)
    return f"(광고) {text}\n*수신거부:설정>변경"

# --- 🔧 핵심 함수: 시트 데이터 가져오기 ---
def get_raw_sheet_text(sheet_id, gid):
    try:
        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'
        response = requests.get(url)
        response.encoding = 'utf-8'
        
        f = io.StringIO(response.text)
        reader = csv.reader(f)
        all_rows = list(reader)
        
        if len(all_rows) < 2: return "데이터 없음"
        
        learned_data = []
        target_rows = all_rows[1:][-50:] 
        
        for row in target_rows:
            clean_row = [cell.strip() for cell in row if cell.strip()]
            if len(clean_row) >= 2:
                row_str = " | ".join(clean_row)
                learned_data.append(row_str)
        
        return "\n".join(learned_data)
    except Exception as e:
        return f"Error: {str(e)}"

# --- 🔧 핵심 함수: Groq 호출 ---
def generate_copy_groq(api_key, context_raw, keyword, info, user_config):
    client = Groq(api_key=api_key)
    
    custom_instruction = ""
    if user_config['target']: custom_instruction += f"- 타겟: {user_config['target']}\n"
    if user_config['note']: custom_instruction += f"- 요청사항: {user_config['note']}\n"

    prompt = f"""
    Role: You are a Viral Marketing Copywriter expert in Korean SNS trends.
    
    [YOUR MISSION]
    Create 10 marketing messages for '{keyword}'.
    
    [STYLE GUIDE]
    1. **Mimic User Data:** Analyze the [User's Past Data] below. Copy their tone and emoji style.
    2. **Clean Output:** **DO NOT** write "(광고)" or "*수신거부". I will add it via code.
    3. **No Header:** Do NOT output the header row. Just output data rows.
    
    [User's Past Data]
    {context_raw}
    
    [Trend Info]
    {info}

    [User Request]
    {custom_instruction}

    [Output Format]
    - CSV format with '|' separator.
    - Columns: Category | Campaign | Target | Contents | Title | Body
    - **Title:** 20~25 chars (Hooky & Creative)
    - **Body:** **Minimum 50 characters.** (Write a FULL sentence describing the benefit or curiosity. Do not be lazy.)
    - **Language:** Korean ONLY.

    **Output ONLY the data rows.**
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.75, 
            max_tokens=2500,
            top_p=1,
            stream=False,
            stop=None,
        )
        return completion.choices[0].message.content, "llama-3.3-70b"

    except Exception as e:
        raise Exception(f"Groq API 오류: {str(e)}")

# --- (정보 수집 함수) ---
def get_naver_search(keyword):
    try:
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sm=tab_opt&sort=1"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        news = []
        for item in soup.select(".news_area")[:3]:
            title = item.select_one('.news_tit').get_text()
            news.append(f"- {title}")
        return "\n".join(news) if news else ""
    except: return ""

# --- 실행부 ---
col1, col2 = st.columns([2, 1])
with col1:
    keyword = st.text_input("📢 홍보할 주제", placeholder="예: 환승연애4 (또는 로봇청소기, 영양제 등)")
with col2:
    campaign = st.text_input("🔖 캠페인명", placeholder="예: 런칭알림")
col3, col4 = st.columns([1, 1])
with col3:
    target = st.text_input("🎯 타겟 설정", placeholder="예: 2030 여성")
with col4:
    note = st.text_input("📝 요청사항", placeholder="예: 호기심 자극")

if st.button("🚀 기획안 생성 시작", type="primary"):
    if not keyword:
        st.warning("주제를 입력해주세요.")
    else:
        status_box = st.status("작업을 진행 중입니다...", expanded=True)
        
        status_box.write("🔍 데이터 수집 및 학습 중...")
        search_info = get_naver_search(keyword)
        context_raw = get_raw_sheet_text(sheet_id_input, sheet_gid_input)
        
        status_box.write("⚡ Groq 엔진 가동...")
        try:
            config = {"campaign": campaign, "target": target, "note": note}
            
            # AI 생성
            raw_text, used_model = generate_copy_groq(FIXED_API_KEY, context_raw, keyword, search_info, config)
            
            # CSV 파싱
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            lines = clean_csv.split('\n')
            
            data_rows = []
            for line in lines:
                if line.count('|') >= 4:
                    parts = line.split('|')
                    if '대분류' in parts[0] or 'Category' in parts[0] or '분류' in parts[0]:
                        continue
                    data_rows.append(parts)
            
            # 헤더 강제 주입
            fixed_columns = ["대분류", "캠페인", "타겟", "콘텐츠", "제목", "내용"]
            
            if data_rows:
                safe_data = []
                for row in data_rows:
                    if len(row) >= 6:
                        safe_data.append(row[:6])
                    else:
                        safe_data.append(row + [""] * (6 - len(row)))
                        
                df = pd.DataFrame(safe_data, columns=fixed_columns)
            else:
                raise Exception("생성된 데이터가 없습니다. 다시 시도해주세요.")
            
            # 후처리
            if '내용' in df.columns:
                df['내용'] = df['내용'].apply(clean_and_format_legal_text)
            
            if '제목' in df.columns:
                df['제목'] = df['제목'].apply(lambda x: str(x).strip()[:25])

            status_box.update(label=f"✅ 완료!", state="complete", expanded=False)
            st.subheader("📊 생성된 마케팅 기획안")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 엑셀 다운로드", csv, f"{keyword}_plan.csv", "text/csv")
            
        except Exception as e:
            status_box.update(label="❌ 오류 발생", state="error")
            st.error(f"에러 내용: {e}")
