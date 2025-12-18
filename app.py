import streamlit as st
import pandas as pd
from groq import Groq
import requests
from bs4 import BeautifulSoup
import io
import re
import csv
import random # 스마트 샘플링을 위해 추가

# --- 🔒 [API 키 설정] ---
part1 = "gsk_lIDRWFZfRKNye7Il5egq"
part2 = "WGdyb3FY5WLFI3NtD9NB70RLy6uk4Mce"
FIXED_API_KEY = part1 + part2
FIXED_SHEET_ID = '1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw'
# -------------------------

st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="⚡", layout="wide")
st.title("⚡ AI 마케팅 카피 생성기 (Smart Sampling)")
st.markdown("토큰 한도 최적화: 최신 300개 중 **핵심 60개 랜덤 학습** + 공백 제외 62자 타겟팅")

# --- 👈 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정 확인")
    if FIXED_API_KEY.startswith("gsk_"):
        st.success("✅ Groq API Key 연결됨")
    
    sheet_id_input = st.text_input("구글 시트 ID", value=FIXED_SHEET_ID)
    sheet_gid_input = st.text_input("시트 GID (탭 번호)", value="0")

# --- 🔧 유틸리티: 텍스트 정제 ---
def clean_and_format_legal_text(text):
    if not isinstance(text, str): return str(text)
    
    # 1. 중복 법적 문구 제거
    text = text.replace("(광고)", "").replace("*수신거부:설정>변경", "")
    text = text.replace('"', '').replace("'", "")
    
    # 2. 저품질 슬랭 삭제
    text = text.replace("ㅋㅋ", "").replace("ㅎㅎ", "").replace("ㅠㅠ", "").replace("ㄷㄷ", "")
    
    # 3. 외국어 제거
    foreign_pattern = re.compile(r'[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF\u0600-\u06FF]+')
    text = foreign_pattern.sub('', text)
    
    # 4. 공백 정리
    text = text.strip()
    
    # 5. 법적 문구 부착
    return f"(광고) {text}\n*수신거부:설정>변경"

# --- 🔧 핵심 함수: 시트 데이터 가져오기 (스마트 샘플링) ---
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
        
        # [핵심 수정] 토큰 폭발 방지 로직
        # 1. 일단 최신 300개를 가져옵니다. (트렌드 반영)
        recent_rows = all_rows[1:][-300:]
        
        # 2. 300개는 너무 많으니(2만 토큰), 여기서 '랜덤으로 60개'만 뽑습니다.
        # 60개면 약 4,000~5,000 토큰으로 안전권입니다.
        if len(recent_rows) > 60:
            target_rows = random.sample(recent_rows, 60)
        else:
            target_rows = recent_rows
        
        for row in target_rows:
            clean_row = [cell.strip() for cell in row if cell.strip()]
            if len(clean_row) >= 2:
                # 너무 짧은 건 학습 가치 없으니 제외
                if len("".join(clean_row)) > 15:
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

    # 공백 제외 45~48자 타겟팅
    
    prompt = f"""
    Role: You are a Professional Viral Marketing Copywriter (Target: Korea).
    
    [YOUR MISSION]
    Create 10 marketing messages for '{keyword}'.
    
    [STRICT TITLE FORMAT]
    **[Emoji] <{keyword}> [Trend Phrase]**
    - Include <{keyword}>.
    - Total length must be UNDER 22 characters (including spaces).
    
    [CONTENT TONE & STYLE]
    1. **Tone:** Casual (Banmal) or Noun-ending. 
    2. **PROHIBITED:** NO 'ㅋㅋ', 'ㅠㅠ', 'ㅎㅎ', 'ㄷㄷ'. NO foreign languages.
    3. **Emoji:** Use 1-2 appropriate emojis.
    4. **Mimic:** Learn patterns from [User's Past Data].
    
    [LENGTH CONSTRAINT - EXCLUDING SPACES]
    - **Body Text:** Write a message where the character count **(EXCLUDING SPACES)** is exactly **45 to 48 characters**.
    - This corresponds to roughly 60~65 characters including spaces.
    - **Do NOT be too short.** Make sure the "non-space character count" reaches at least 45.
    
    [User's Past Data (Sampled Patterns)]
    {context_raw}
    
    [Trend Info]
    {info}

    [User Request]
    {custom_instruction}

    [Output Format]
    - CSV format with '|' separator.
    - Columns: Category | Campaign | Target | Title | Body
    - **Language:** Korean ONLY.

    **Output ONLY the data rows.**
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.75, 
            max_tokens=3000,
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
            desc = item.select_one('.news_dsc').get_text()
            news.append(f"- {title}: {desc}")
        return "\n".join(news) if news else ""
    except: return ""

# --- 실행부 ---
col1, col2 = st.columns([2, 1])
with col1:
    keyword = st.text_input("📢 홍보할 주제", placeholder="예: 환승연애4")
with col2:
    campaign = st.text_input("🔖 캠페인명", placeholder="예: 런칭알림")
col3, col4 = st.columns([1, 1])
with col3:
    target = st.text_input("🎯 타겟 설정", placeholder="예: 2030 여성")
with col4:
    note = st.text_input("📝 요청사항", placeholder="예: 깔끔한 반말, 임팩트 있게")

if st.button("🚀 기획안 생성 시작", type="primary"):
    if not keyword:
        st.warning("주제를 입력해주세요.")
    else:
        status_box = st.status("작업을 진행 중입니다...", expanded=True)
        
        # [수정됨] 사용자에게 샘플링 사실 알림
        status_box.write(f"🔍 시트 데이터 최신 300개 중 60개 샘플링 학습...")
        search_info = get_naver_search(keyword)
        context_raw = get_raw_sheet_text(sheet_id_input, sheet_gid_input)
        
        status_box.write("⚡ Groq 엔진 가동 (토큰 최적화 모드)...")
        try:
            config = {"campaign": campaign, "target": target, "note": note}
            
            raw_text, used_model = generate_copy_groq(FIXED_API_KEY, context_raw, keyword, search_info, config)
            
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            lines = clean_csv.split('\n')
            
            data_rows = []
            for line in lines:
                if line.count('|') >= 3:
                    parts = line.split('|')
                    if '대분류' in parts[0] or 'Category' in parts[0] or '분류' in parts[0]:
                        continue
                    data_rows.append(parts)
            
            fixed_columns = ["대분류", "캠페인", "타겟", "제목", "내용"]
            
            if data_rows:
                safe_data = []
                for row in data_rows:
                    if len(row) >= 5:
                        safe_data.append(row[:5])
                    else:
                        safe_data.append(row + [""] * (5 - len(row)))
                        
                df = pd.DataFrame(safe_data, columns=fixed_columns)
            else:
                raise Exception("생성된 데이터가 없습니다.")
            
            # 후처리
            if '내용' in df.columns:
                df['내용'] = df['내용'].apply(clean_and_format_legal_text)
            
            if '제목' in df.columns:
                df['제목'] = df['제목'].apply(lambda x: str(x).strip()[:22])

            status_box.update(label=f"✅ 완료!", state="complete", expanded=False)
            st.subheader("📊 생성된 마케팅 기획안")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 엑셀 다운로드", csv, f"{keyword}_plan.csv", "text/csv")
            
        except Exception as e:
            status_box.update(label="❌ 오류 발생", state="error")
            st.error(f"에러 내용: {e}")
