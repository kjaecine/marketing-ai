import streamlit as st
import pandas as pd
from groq import Groq
import requests
from bs4 import BeautifulSoup
import io

# --- 🔒 [API 키 설정] ---
part1 = "gsk_lIDRWFZfRKNye7Il5egq"
part2 = "WGdyb3FY5WLFI3NtD9NB70RLy6uk4Mce"
FIXED_API_KEY = part1 + part2

FIXED_SHEET_ID = '1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw'
# -------------------------

st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="⚡", layout="wide")
st.title("⚡ AI 마케팅 카피 생성기 (High Quality)")
st.markdown("한자 제거, 자연스러운 한국어 톤앤매너, 법적 문구 자동화가 적용된 **최종 완성 버전**입니다.")

# --- 👈 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정 확인")
    
    if FIXED_API_KEY.startswith("gsk_"):
        st.success("✅ Groq API Key 연결됨")
    else:
        st.error("API Key 설정 오류")
    
    sheet_id_input = st.text_input("구글 시트 ID", value=FIXED_SHEET_ID)
    sheet_gid_input = st.text_input("시트 GID (탭 번호)", value="0")

# --- 🔧 핵심 함수: Groq 호출 ---

def generate_copy_groq(api_key, context, keyword, info, user_config):
    client = Groq(api_key=api_key)
    
    custom_instruction = ""
    if user_config['target']: custom_instruction += f"- 타겟: {user_config['target']}\n"
    if user_config['campaign']: custom_instruction += f"- 캠페인: {user_config['campaign']}\n"
    if user_config['note']: custom_instruction += f"- 요청사항: {user_config['note']}\n"

    if not context: context = "데이터 없음."

    # 프롬프트 (품질 대폭 강화)
    prompt = f"""
    Role: You are a professional Korean SNS Viral Marketing Copywriter (expert in Instagram/YouTube Shorts trends).
    
    [Task]
    Create 10 marketing messages for '{keyword}'.
    
    [Reference Style - Learn Only Tone & Emoji]
    {context}
    
    [Trend Info]
    {info}

    [User Request]
    {custom_instruction}

    [CRITICAL RULES - DO NOT IGNORE]
    1. **NO HANJA (Chinese Characters):** NEVER use characters like '必見', '紹介', '登場'. Use ONLY Korean Hangul. (e.g., instead of '必見', use '필독' or '놓치지 마세요').
    2. **Natural Korean Tone:** Do NOT use translation-like sentences (e.g., avoid repetitive "If you like X, you must see Y"). Use natural, trendy, emotional, and catchy spoken Korean (SNS style).
    3. **Diverse Patterns:** Vary the sentence structures. Use questions, exclamations, and emotional hooks.
    4. **Context Awareness:** If the keyword is '{keyword}', understand its genre (e.g., if it's a romance show, talk about love/breakup/dopamine, NOT action scenes).

    [Output Constraints]
    1. **Format:** CSV format with '|' separator.
    2. **Header:** 대분류|캠페인|상세타겟_상세타깃_상세설명|추천 콘텐츠|제목|내용
    3. **Title Length:** UNDER 22 characters.
    4. **Body Length:** UNDER 40 characters (Short & Punchy). *Legal text will be added automatically, so keep the core message short.*
    5. **Emoji:** Use emojis naturally and abundantly.
    
    **Output ONLY the CSV data. No extra text.**
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8, # 창의성 약간 더 높임 (0.75 -> 0.8)
            max_tokens=2048,
            top_p=1,
            stream=False,
            stop=None,
        )
        return completion.choices[0].message.content, "llama-3.3-70b (Groq)"

    except Exception as e:
        raise Exception(f"Groq API 오류: {str(e)}")

# --- (정보 수집 함수들) ---

def get_sheet_data(sheet_id, gid):
    try:
        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'
        df = pd.read_csv(url, encoding='utf-8', on_bad_lines='skip')
        if df.empty: return None
        # 문맥 파악을 위해 최근 100개 학습
        if len(df) > 100: df = df.tail(100)
        return df.to_markdown(index=False)
    except: return None

def get_naver_search(keyword):
    try:
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sm=tab_opt&sort=1"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        news = []
        items = soup.select(".news_area")[:5]
        for item in items:
            title = item.select_one('.news_tit').get_text()
            desc = item.select_one('.news_dsc').get_text()
            news.append(f"- {title}: {desc}")
        return "\n".join(news) if news else "검색 결과 없음"
    except: return "크롤링 차단됨"

# --- 실행부 ---
col1, col2 = st.columns([2, 1])
with col1:
    keyword = st.text_input("📢 홍보할 주제", placeholder="예: 환승연애4")
with col2:
    campaign = st.text_input("🔖 캠페인명", placeholder="예: 런칭알림")
col3, col4 = st.columns([1, 1])
with col3:
    target = st.text_input("🎯 타겟 설정", placeholder="예: 2030 여성, 도파민 중독자")
with col4:
    note = st.text_input("📝 요청사항", placeholder="예: 자극적이고 궁금하게")

if st.button("🚀 기획안 생성 시작", type="primary"):
    if not keyword:
        st.warning("주제를 입력해주세요.")
    else:
        status_box = st.status("작업을 진행 중입니다...", expanded=True)
        
        status_box.write("🔍 네이버 트렌드 & 시트 톤앤매너 분석 중...")
        search_info = get_naver_search(keyword)
        sheet_data = get_sheet_data(sheet_id_input, sheet_gid_input)
        
        status_box.write("⚡ Groq AI 카피라이팅 (한자 제거 & 감성 입히기)...")
        try:
            config = {"campaign": campaign, "target": target, "note": note}
            
            # 생성
            raw_text, used_model = generate_copy_groq(FIXED_API_KEY, sheet_data, keyword, search_info, config)
            
            # CSV 파싱
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            if '|' in clean_csv:
                lines = clean_csv.split('\n')
                csv_lines = [line for line in lines if '|' in line]
                clean_csv = '\n'.join(csv_lines)

            df = pd.read_csv(io.StringIO(clean_csv), sep='|')
            
            # 법적 문구 & 글자수 제어 (파이썬 후처리)
            if any('내용' in c for c in df.columns):
                content_col = [c for c in df.columns if '내용' in c][0] 
                df[content_col] = df[content_col].apply(
                    lambda x: f"(광고) {str(x).strip()}\n*수신거부:설정>변경"
                )
            
            status_box.update(label=f"✅ 완료! ({used_model})", state="complete", expanded=False)
            st.subheader("📊 생성된 마케팅 기획안")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 엑셀 다운로드", csv, f"{keyword}_plan.csv", "text/csv")
            
        except Exception as e:
            status_box.update(label="❌ 오류 발생", state="error")
            st.error(f"에러 내용: {e}")
