import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import io

# --- 🔒 [사용자 고정 설정] ---
FIXED_API_KEY = 'AIzaSyCDtgjMmzUIbXGOIzZsYz-s0X1NTjqrUPo' 
FIXED_SHEET_ID = '1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw'
# -------------------------

# --- 🎨 페이지 설정 ---
st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="🧞‍♂️", layout="wide")
st.title("🧞‍♂️ AI 마케팅 카피 생성기(User Growth)")
st.markdown(f"📢User Growth를 위한 AI 문구생성기입니다. 좋은 카피가 안나온다면 요청사항에 추가해주세요.")

# --- 👈 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정 확인")
    st.success("✅ (광고) 및 수신거부 자동 적용됨")
    
    sheet_id_input = st.text_input("구글 시트 ID", value=FIXED_SHEET_ID)
    sheet_gid_input = st.text_input("시트 GID (탭 번호)", value="0")

# --- 🔧 핵심 함수들 ---

def get_available_model(api_key):
    """모델 자동 탐색"""
    genai.configure(api_key=api_key)
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'flash' in m.name: return m.name
                if 'pro' in m.name: return m.name
        return 'models/gemini-pro'
    except:
        return 'models/gemini-pro'

def get_sheet_data(sheet_id, gid):
    """구글 시트 데이터 가져오기 (인코딩 강화)"""
    try:
        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'
        df = pd.read_csv(url, encoding='utf-8', on_bad_lines='skip')
        if df.empty: return None
        if len(df) > 30: df = df.tail(30)
        return df.to_markdown(index=False)
    except:
        return None

def get_naver_search(keyword):
    """네이버 뉴스 크롤링"""
    try:
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sm=tab_opt&sort=1"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        news = [f"[{item.select_one('.news_tit').get_text()}]: {item.select_one('.news_dsc').get_text()}" for item in soup.select(".news_area")[:5]]
        return "\n".join(news) if news else "검색 결과 없음"
    except:
        return "크롤링 차단됨 (기본 정보로 진행)"

def generate_plan(api_key, context, keyword, info, user_config):
    """기획안 생성"""
    model_name = get_available_model(api_key)
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    custom_instruction = ""
    if user_config['target']: custom_instruction += f"- 타겟: {user_config['target']}\n"
    if user_config['campaign']: custom_instruction += f"- 캠페인: {user_config['campaign']}\n"
    if user_config['note']: custom_instruction += f"- 요청사항: {user_config['note']}\n"

    if not context: context = "데이터 없음."

    # ★ 글자수 제한: (광고)랑 수신거부 문구 들어갈 자리 빼고 40자로 줄임
    prompt = f"""
    Role: Viral Marketing Copywriter.
    
    [Mission]
    1. **STYLE CLONING:** Mimic the Emoji Usage and Tone from [Reference].
    2. Create 10 marketing messages for '{keyword}'.
    3. **STRICT LIMITS (CRITICAL):**
       - **Title:** UNDER 20 Korean characters.
       - **Body:** UNDER 40 Korean characters (Short & Punchy).
    4. Apply [User Request].

    [Reference]
    {context}

    [News]
    {info}

    [User Request]
    {custom_instruction}

    [Output Format]
    대분류|캠페인|상세타겟_상세타깃_상세설명|추천 콘텐츠|제목|내용
    (CSV format with '|' separator, Header included)
    """
    
    response = model.generate_content(prompt)
    return response.text, model_name

# --- 🖥️ 메인 화면 UI ---

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
        status_box.write("🔍 네이버 뉴스 검색 중...")
        search_info = get_naver_search(keyword)
        
        status_box.write("📚 구글 시트 학습 중...")
        sheet_data = get_sheet_data(sheet_id_input, sheet_gid_input)
        
        status_box.write("🤖 AI 생성 및 법적 문구 적용 중...")
        try:
            config = {"campaign": campaign, "target": target, "note": note}
            raw_text, used_model = generate_plan(FIXED_API_KEY, sheet_data, keyword, search_info, config)
            
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            df = pd.read_csv(io.StringIO(clean_csv), sep='|')
            
            # ★ 핵심 수정: 법적 문구 강제 삽입 구간 ★
            # 데이터프레임의 '내용' 컬럼을 찾아서 앞뒤에 문구 붙이기
            content_col = [c for c in df.columns if '내용' in c][0] # '내용'이 포함된 컬럼 찾기
            
            # (광고) + 본문 + 수신거부 결합
            df[content_col] = df[content_col].apply(
                lambda x: f"(광고) {str(x).strip()}\n*수신거부:설정>변경"
            )
            
            status_box.update(label=f"✅ 완료! (모델: {used_model})", state="complete", expanded=False)
            
            st.subheader("📊 생성된 마케팅 기획안")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 엑셀 다운로드", csv, f"{keyword}_plan.csv", "text/csv")
            
        except Exception as e:
            status_box.update(label="❌ 오류", state="error")
            st.error(f"에러: {e}")
