import streamlit as st
import pandas as pd
from groq import Groq
import requests
from bs4 import BeautifulSoup
import io

# --- 🔒 [보안 설정 변경] ---
# GitHub 에러 방지를 위해, 코드가 아닌 'Streamlit Secrets'에서 키를 가져옵니다.
try:
    FIXED_API_KEY = st.secrets["GROQ_API_KEY"]
except FileNotFoundError:
    # 로컬 테스트용 (혹시 secrets 파일이 없을 때 대비)
    st.error("⚠️ API 키를 찾을 수 없습니다. Streamlit 대시보드 > Settings > Secrets에 'GROQ_API_KEY'를 설정해주세요.")
    st.stop()

FIXED_SHEET_ID = '1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw'
# -------------------------

st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="⚡", layout="wide")
st.title("⚡ AI 마케팅 카피 생성기 (Groq Llama 3)")
st.markdown("세계에서 가장 빠른 **Groq(Llama 3)** 엔진으로 초고속 생성합니다.")

with st.sidebar:
    st.header("⚙️ 설정 확인")
    # 키가 로드되었는지 확인 (보안상 앞 4자리만 표시)
    if FIXED_API_KEY.startswith("gsk_"):
        masked_key = FIXED_API_KEY[:4] + "..."
        st.success(f"✅ Groq 키 연결됨 ({masked_key})")
    else:
        st.error("API 키 설정 오류")
    
    sheet_id_input = st.text_input("구글 시트 ID", value=FIXED_SHEET_ID)
    sheet_gid_input = st.text_input("시트 GID", value="0")

# --- 🔧 핵심 함수: Groq 호출 ---

def generate_copy_groq(api_key, context, keyword, info, user_config):
    # Groq 클라이언트 초기화
    client = Groq(api_key=api_key)
    
    custom_instruction = ""
    if user_config['target']: custom_instruction += f"- 타겟: {user_config['target']}\n"
    if user_config['campaign']: custom_instruction += f"- 캠페인: {user_config['campaign']}\n"
    if user_config['note']: custom_instruction += f"- 요청사항: {user_config['note']}\n"

    if not context: context = "데이터 없음."

    # 프롬프트 구성 (한국어 강제)
    prompt = f"""
    You are a professional Korean Viral Marketing Copywriter.
    
    [Mission]
    1. Analyze the tone and style from [Reference] and apply it.
    2. Create 10 marketing messages for '{keyword}'.
    3. **Important:** Output MUST be in Korean (한국어).
    4. **Output Format:** CSV format with '|' separator (Header: 대분류|캠페인|상세타겟_상세타깃_상세설명|추천 콘텐츠|제목|내용).
    5. Do not write any introduction or explanation, just the CSV data.

    [Reference Data]
    {context}

    [News/Trends]
    {info}

    [User Specific Request]
    {custom_instruction}
    """

    try:
        completion = client.chat.completions.create(
            model="llama3-70b-8192", # Llama 3 70B (성능/속도 최적)
            messages=[
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=2048,
            top_p=1,
            stream=False,
            stop=None,
        )
        
        return completion.choices[0].message.content, "llama3-70b (Groq)"

    except Exception as e:
        raise Exception(f"Groq API 오류: {str(e)}")

# --- (정보 수집 함수 동일) ---
def get_sheet_data(sheet_id, gid):
    try:
        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'
        df = pd.read_csv(url, encoding='utf-8', on_bad_lines='skip')
        if df.empty: return None
        if len(df) > 30: df = df.tail(30)
        return df.to_markdown(index=False)
    except: return None

def get_naver_search(keyword):
    try:
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sm=tab_opt&sort=1"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        news = [f"[{item.select_one('.news_tit').get_text()}]: {item.select_one('.news_dsc').get_text()}" for item in soup.select(".news_area")[:5]]
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
    target = st.text_input("🎯 타겟 설정", placeholder="예: 30대 직장인")
with col4:
    note = st.text_input("📝 요청사항", placeholder="예: 이모지 많이")

if st.button("🚀 기획안 생성 시작", type="primary"):
    if not keyword:
        st.warning("주제를 입력해주세요.")
    else:
        status_box = st.status("작업을 진행 중입니다...", expanded=True)
        
        status_box.write("🔍 데이터 수집 중...")
        search_info = get_naver_search(keyword)
        sheet_data = get_sheet_data(sheet_id_input, sheet_gid_input)
        
        status_box.write("⚡ Groq 엔진 가동 중 (Secret Key 사용)...")
        try:
            config = {"campaign": campaign, "target": target, "note": note}
            
            # Groq 호출
            raw_text, used_model = generate_copy_groq(FIXED_API_KEY, sheet_data, keyword, search_info, config)
            
            # CSV 파싱
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            if '|' in clean_csv:
                lines = clean_csv.split('\n')
                csv_lines = [line for line in lines if '|' in line]
                clean_csv = '\n'.join(csv_lines)

            df = pd.read_csv(io.StringIO(clean_csv), sep='|')
            
            # 법적 문구 추가
            if any('내용' in c for c in df.columns):
                content_col = [c for c in df.columns if '내용' in c][0] 
                df[content_col] = df[content_col].apply(lambda x: f"(광고) {str(x).strip()}\n*수신거부:설정>변경")
            
            status_box.update(label=f"✅ 성공! ({used_model})", state="complete", expanded=False)
            st.subheader("📊 생성된 마케팅 기획안")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 엑셀 다운로드", csv, f"{keyword}_plan.csv", "text/csv")
            
        except Exception as e:
            status_box.update(label="❌ 오류 발생", state="error")
            st.error(f"에러 내용: {e}")
