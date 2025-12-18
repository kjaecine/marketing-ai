import streamlit as st
import pandas as pd
from groq import Groq
import requests
from bs4 import BeautifulSoup
import io

# --- 🎨 페이지 설정 ---
st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="⚡", layout="wide")
st.title("⚡ AI 마케팅 카피 생성기 (Groq Llama 3)")
st.markdown("세계에서 가장 빠른 **Groq(Llama 3)** 엔진으로 초고속 생성합니다.")

# --- 🔒 [API 키 처리 로직] (핵심 수정) ---
# 1. 비밀 금고(Secrets)를 먼저 뒤져봅니다.
# 2. 없으면(에러나면) 사이드바에서 입력받습니다.

api_key = None

try:
    # Streamlit Secrets에서 조회 시도
    if "GROQ_API_KEY" in st.secrets:
        api_key = st.secrets["GROQ_API_KEY"]
except FileNotFoundError:
    pass # 로컬 환경 등에서 secrets 파일 자체가 없을 때 무시

# --- 👈 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정")
    
    # Secrets에 키가 없으면 입력창을 띄움
    if not api_key:
        api_key = st.text_input("🔑 Groq API Key 입력", type="password", placeholder="gsk_로 시작하는 키")
        if not api_key:
            st.warning("API 키를 입력하거나 Secrets에 설정해주세요.")
    else:
        # Secrets에서 잘 가져왔으면 성공 표시
        st.success("✅ API Key 연동됨 (Secrets)")
    
    sheet_id_input = st.text_input("구글 시트 ID", value='1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw')
    sheet_gid_input = st.text_input("시트 GID (탭 번호)", value="0")

# --- 🔧 핵심 함수 ---

def generate_copy_groq(key, context, keyword, info, user_config):
    client = Groq(api_key=key)
    
    custom_instruction = ""
    if user_config['target']: custom_instruction += f"- 타겟: {user_config['target']}\n"
    if user_config['campaign']: custom_instruction += f"- 캠페인: {user_config['campaign']}\n"
    if user_config['note']: custom_instruction += f"- 요청사항: {user_config['note']}\n"

    if not context: context = "데이터 없음."

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
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2048,
            top_p=1,
            stream=False,
            stop=None,
        )
        return completion.choices[0].message.content, "llama3-70b (Groq)"

    except Exception as e:
        raise Exception(f"Groq API 오류: {str(e)}")

# --- (정보 수집 함수들) ---
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
    if not api_key:
        st.error("🚫 API 키가 없습니다. 사이드바에 Groq API 키를 입력해주세요.")
    elif not keyword:
        st.warning("주제를 입력해주세요.")
    else:
        status_box = st.status("작업을 진행 중입니다...", expanded=True)
        
        status_box.write("🔍 데이터 수집 중...")
        search_info = get_naver_search(keyword)
        sheet_data = get_sheet_data(sheet_id_input, sheet_gid_input)
        
        status_box.write("⚡ Groq 엔진 가동 중...")
        try:
            config = {"campaign": campaign, "target": target, "note": note}
            
            # API 키 전달
            raw_text, used_model = generate_copy_groq(api_key, sheet_data, keyword, search_info, config)
            
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            if '|' in clean_csv:
                lines = clean_csv.split('\n')
                csv_lines = [line for line in lines if '|' in line]
                clean_csv = '\n'.join(csv_lines)

            df = pd.read_csv(io.StringIO(clean_csv), sep='|')
            
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
