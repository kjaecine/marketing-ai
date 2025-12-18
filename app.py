import streamlit as st
import pandas as pd
from groq import Groq
import requests
from bs4 import BeautifulSoup
import io
import re
import csv # CSV 정밀 파싱을 위해 추가

# --- 🔒 [API 키 설정] ---
part1 = "gsk_lIDRWFZfRKNye7Il5egq"
part2 = "WGdyb3FY5WLFI3NtD9NB70RLy6uk4Mce"
FIXED_API_KEY = part1 + part2
FIXED_SHEET_ID = '1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw'
# -------------------------

st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="⚡", layout="wide")
st.title("⚡ AI 마케팅 카피 생성기 (Real Sheet Learning)")
st.markdown("특정 예시 없이 **사용자의 구글 시트 데이터를 있는 그대로** 학습합니다.")

# --- 👈 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정 확인")
    if FIXED_API_KEY.startswith("gsk_"):
        st.success("✅ Groq API Key 연결됨")
    
    sheet_id_input = st.text_input("구글 시트 ID", value=FIXED_SHEET_ID)
    sheet_gid_input = st.text_input("시트 GID (탭 번호)", value="0")

# --- 🔧 유틸리티: 텍스트 청소 ---
def clean_text_strict(text):
    # 외국어 제거
    pattern = re.compile(r'[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF\u0600-\u06FF]+')
    text = pattern.sub('', str(text))
    return re.sub(r'\s+', ' ', text).strip()

# --- 🔧 핵심 함수: 시트 데이터 '날것'으로 가져오기 ---
def get_raw_sheet_text(sheet_id, gid):
    """
    Pandas로 표를 만들려다가 에러가 나니, 
    그냥 텍스트 덩어리로 가져와서 AI에게 던져줍니다.
    """
    try:
        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'
        response = requests.get(url)
        response.encoding = 'utf-8'
        
        # 1. 텍스트로 받아옴
        raw_text = response.text
        
        # 2. CSV 리더로 한 줄씩 파싱 (에러 없이 읽기 위해)
        # 쉼표가 포함된 문장도 csv 모듈은 잘 처리함
        f = io.StringIO(raw_text)
        reader = csv.reader(f)
        
        learned_data = []
        
        # 3. 데이터 추출 (헤더 제외하고 최근 50개 행만)
        all_rows = list(reader)
        if len(all_rows) < 2: return "데이터 없음"
        
        # 최신 트렌드 반영을 위해 뒤에서부터 50개
        target_rows = all_rows[1:][-50:] 
        
        for row in target_rows:
            # 빈 칸 제거하고 하나의 문장으로 합침
            # 예: ["엔터", "환승연애", "제목..", "내용.."] -> "엔터 | 환승연애 | 제목.. | 내용.."
            clean_row = [cell.strip() for cell in row if cell.strip()]
            if len(clean_row) >= 2: # 최소한 데이터가 2칸 이상은 있어야 학습
                row_str = " | ".join(clean_row)
                learned_data.append(row_str)
        
        # AI에게 줄 최종 텍스트
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
    
    [CRITICAL: STYLE CLONING]
    Below is the **Raw Data** from the user's past performance.
    Analyze the **structure, length, tone, and emoji usage** from this data and generate NEW copies that look exactly like them.
    
    [User's Past Data (Raw Text)]
    {context_raw}
    
    [Trend Info]
    {info}

    [User Request]
    {custom_instruction}

    [Constraints]
    1. **Language:** Korean (Hangul) ONLY. No Foreign languages.
    2. **Format:** CSV with '|' separator.
    3. **Columns:** 대분류|캠페인|타겟|콘텐츠|제목|내용
    4. **Volume:**
       - **Title:** 20~30 characters.
       - **Body:** 50~80 characters. (Write fully and emotionally. Do not cut it short.)
    5. **Tone:** Use the same tone found in [User's Past Data].

    **Output ONLY the CSV data.**
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
    keyword = st.text_input("📢 홍보할 주제", placeholder="예: 환승연애4")
with col2:
    campaign = st.text_input("🔖 캠페인명", placeholder="예: 런칭알림")
col3, col4 = st.columns([1, 1])
with col3:
    target = st.text_input("🎯 타겟 설정", placeholder="예: 2030 여성")
with col4:
    note = st.text_input("📝 요청사항", placeholder="예: 자극적으로")

# --- 데이터 확인용 ---
with st.expander("📊 학습 데이터 미리보기 (Raw Text)"):
    if st.button("데이터 로드 확인"):
        raw_text = get_raw_sheet_text(sheet_id_input, sheet_gid_input)
        if len(raw_text) > 50:
            st.success("✅ 시트 데이터 로드 성공!")
            st.text_area("AI가 학습할 실제 데이터", raw_text, height=300)
        else:
            st.error("❌ 데이터 로드 실패 혹은 내용 부족.")

if st.button("🚀 기획안 생성 시작", type="primary"):
    if not keyword:
        st.warning("주제를 입력해주세요.")
    else:
        status_box = st.status("작업을 진행 중입니다...", expanded=True)
        
        status_box.write("🔍 트렌드 & 시트 학습 중...")
        search_info = get_naver_search(keyword)
        
        # 시트 데이터 가져오기 (Raw Text 방식)
        context_raw = get_raw_sheet_text(sheet_id_input, sheet_gid_input)
        
        if len(context_raw) < 50:
             status_box.write("⚠️ 시트 내용을 불러오지 못했습니다. 일반 모드로 진행합니다.")
        
        status_box.write("⚡ Groq 엔진 가동 (사용자 스타일 복제)...")
        try:
            config = {"campaign": campaign, "target": target, "note": note}
            
            raw_text, used_model = generate_copy_groq(FIXED_API_KEY, context_raw, keyword, search_info, config)
            
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            if '|' in clean_csv:
                lines = clean_csv.split('\n')
                csv_lines = [line for line in lines if line.count('|') >= 4] 
                clean_csv = '\n'.join(csv_lines)

            df = pd.read_csv(io.StringIO(clean_csv), sep='|')
            
            # 후처리
            if any('내용' in c for c in df.columns):
                content_col = [c for c in df.columns if '내용' in c][0] 
                
                def final_clean(text):
                    text = clean_text_strict(str(text))
                    # 50자 미만이면 AI가 성의없게 쓴 거니 뒤에 문구 추가
                    if len(text) < 40: 
                        text += " 지금 바로 확인하고 도파민 충전하세요! ⚡"
                    return f"(광고) {text}\n*수신거부:설정>변경"

                df[content_col] = df[content_col].apply(final_clean)
            
            # 제목 길이 정리
            if any('제목' in c for c in df.columns):
                title_col = [c for c in df.columns if '제목' in c][0]
                df[title_col] = df[title_col].apply(lambda x: clean_text_strict(str(x))[:30]) 

            status_box.update(label=f"✅ 완료!", state="complete", expanded=False)
            st.subheader("📊 생성된 마케팅 기획안")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 엑셀 다운로드", csv, f"{keyword}_plan.csv", "text/csv")
            
        except Exception as e:
            status_box.update(label="❌ 오류 발생", state="error")
            st.error(f"에러 내용: {e}")
