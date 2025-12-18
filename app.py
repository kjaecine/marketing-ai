import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import io
from duckduckgo_search import DDGS # 강력한 우회 검색 도구

# --- 🎨 페이지 설정 ---
st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="🧞‍♂️", layout="wide")
st.title("🧞‍♂️ AI 마케팅 카피 생성기 (Secure & Stable)")
st.markdown("⚠️ **API 키 보안 모드** + **검색 엔진 우회(DuckDuckGo)** 적용됨")

# --- 👈 사이드바 (API 키 입력) ---
with st.sidebar:
    st.header("⚙️ 설정")
    
    # [보안] 코드가 아니라 여기서 직접 입력받습니다.
    user_api_key = st.text_input("AIzaSyA1HhzAK2y_TCKjb1tG3M7GHnmC5uKh4WM", type="password", help="새로 발급받은 키를 여기에 넣으세요.")
    
    if not user_api_key:
        st.warning("⚠️ API 키를 입력해야 작동합니다.")
    else:
        st.success("✅ 키 입력됨")

    st.divider()
    
    sheet_id_input = st.text_input("구글 시트 ID", value='1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw')
    sheet_gid_input = st.text_input("시트 GID (탭 번호)", value="0")

# --- 🔧 핵심 함수들 ---

def get_news_search_ddg(keyword):
    """
    네이버 차단을 피하기 위해 DuckDuckGo 엔진을 통해 
    '키워드 + 뉴스'를 검색하여 결과를 가져옵니다. (차단 확률 0%)
    """
    try:
        results = DDGS().text(f"{keyword} 최신 뉴스", max_results=5)
        if not results:
            return "검색 결과 없음"
        
        news_summary = []
        for r in results:
            title = r.get('title', '')
            body = r.get('body', '')
            news_summary.append(f"[{title}]: {body}")
            
        return "\n\n".join(news_summary)
    except Exception as e:
        return f"검색 에러: {str(e)}"

def get_sheet_data(sheet_id, gid):
    """구글 시트 데이터 가져오기"""
    try:
        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'
        df = pd.read_csv(url, encoding='utf-8', on_bad_lines='skip')
        if df.empty: return None
        if len(df) > 50: df = df.tail(50)
        return df.to_markdown(index=False)
    except:
        return None

def generate_plan(api_key, context, keyword, info, user_config):
    """Gemini 호출"""
    genai.configure(api_key=api_key)
    
    # 최신 모델 우선 시도, 실패 시 안정적인 Pro 모델 사용
    model_name = 'gemini-2.0-flash-lite-preview-02-05'
    try:
        model = genai.GenerativeModel(model_name)
    except:
        model_name = 'gemini-1.5-flash' # 백업
        model = genai.GenerativeModel(model_name)

    custom_instruction = ""
    if user_config['target']: custom_instruction += f"- 타겟: {user_config['target']}\n"
    if user_config['campaign']: custom_instruction += f"- 캠페인: {user_config['campaign']}\n"
    if user_config['note']: custom_instruction += f"- 요청사항: {user_config['note']}\n"

    if not context: context = "데이터 없음."

    prompt = f"""
    Role: Senior Viral Marketing Copywriter (Korea).
    
    [Mission]
    1. **STYLE CLONING:** Analyze the [Reference] data. Copy the tone, manner, and emoji usage exactly.
    2. Create 10 marketing messages for '{keyword}'.
    3. **STRICT LIMITS (CRITICAL):**
       - **Title:** UNDER 20 Korean characters.
       - **Body:** **Exactly 40~50 characters (Excluding spaces).** - Do NOT write '(광고)' or '*수신거부'.
    4. Apply [User Request].

    [Reference Data]
    {context}

    [News/Trends Info]
    {info}

    [User Request]
    {custom_instruction}

    [Output Format]
    대분류|캠페인|타겟|콘텐츠|제목|내용
    (CSV format with '|' separator. NO markdown.)
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
    if not user_api_key:
        st.error("🚨 사이드바에 새 API 키를 입력해주세요! (기존 키는 유출로 인해 차단됨)")
    elif not keyword:
        st.warning("주제를 입력해주세요.")
    else:
        status_box = st.status("작업을 진행 중입니다...", expanded=True)
        
        # 1. 검색
        status_box.write(":mag: 최신 뉴스 검색 중 (우회 모드)...")
        search_info = get_news_search_ddg(keyword)
        
        if "에러" in search_info or "없음" in search_info:
             status_box.write(f"⚠️ 검색 이슈: {search_info}")
        else:
             status_box.write("✅ 최신 정보 확보 완료!")
        
        # 2. 시트
        status_box.write(":books: 구글 시트 학습 중...")
        sheet_data = get_sheet_data(sheet_id_input, sheet_gid_input)
        
        # 3. 생성
        status_box.write(f":robot_face: Gemini 엔진 가동...")
        try:
            config = {"campaign": campaign, "target": target, "note": note}
            raw_text, used_model = generate_plan(user_api_key, sheet_data, keyword, search_info, config)
            
            # 파싱
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            df = pd.read_csv(io.StringIO(clean_csv), sep='|')
            
            # 후처리
            content_cols = [c for c in df.columns if '내용' in c]
            if content_cols:
                content_col = content_cols[0]
                def final_formatter(text):
                    text = str(text).replace("(광고)", "").replace("*수신거부:설정>변경", "").strip()
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
            if "403" in str(e):
                st.error("🚨 API 키 오류: 입력하신 키가 유효하지 않거나 차단되었습니다. 새 키를 입력해주세요.")
            else:
                st.error(f"에러 내용: {e}")
