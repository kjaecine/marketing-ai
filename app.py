import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import io
from duckduckgo_search import DDGS

# --- 🎨 페이지 설정 ---
st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="⚡", layout="wide")
st.title("⚡ AI 마케팅 카피 생성기 (High RPD Enforcer)")
st.markdown("🚀 **일일 1,500회 제공되는 'Flash' 모델만 강제로 사용합니다.** (Pro 모델 사용 안 함)")

# --- 🔧 유틸리티 함수 ---

def get_high_rpd_model(api_key):
    """
    [핵심] 사용자 계정에서 'Flash'가 포함된 고용량 모델만 찾아냅니다.
    Pro 모델(RPD 50회)이 잡히면 과감히 버립니다.
    """
    genai.configure(api_key=api_key)
    try:
        all_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                all_models.append(m.name)
        
        # 필터링 1: 2.0 Flash 계열 (최신, 빠름)
        for m in all_models:
            if 'gemini-2.0-flash' in m: return m
            
        # 필터링 2: 1.5 Flash 계열 (가장 안정적, 1500회 보장)
        for m in all_models:
            if 'gemini-1.5-flash' in m and '8b' not in m: return m
            
        # 필터링 3: 1.5 Flash-8b (초경량)
        for m in all_models:
            if 'gemini-1.5-flash' in m: return m
            
        return None # Flash 모델이 하나도 없으면 None 반환 (Pro는 안 씀)
        
    except Exception as e:
        return None

def get_news_search_ddg(keyword):
    """DuckDuckGo 뉴스 검색"""
    try:
        results = DDGS().text(f"{keyword} 뉴스", region='kr-kr', max_results=5)
        if not results: return "검색 결과 없음"
        
        news_summary = []
        for r in results:
            news_summary.append(f"[{r.get('title','')}]: {r.get('body','')}")
        return "\n\n".join(news_summary)
    except Exception as e:
        return f"검색 에러: {str(e)}"

def get_sheet_data(sheet_id, gid):
    try:
        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'
        df = pd.read_csv(url, encoding='utf-8', on_bad_lines='skip')
        if df.empty: return None
        if len(df) > 50: df = df.tail(50)
        return df.to_markdown(index=False)
    except:
        return None

def generate_plan(api_key, model_name, context, keyword, info, user_config):
    genai.configure(api_key=api_key)
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
       - **Body:** **Exactly 40~50 characters (Excluding spaces).** - Do NOT write '(광고)' or '*수신거부'. I will add them via code.
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
    
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    response = model.generate_content(prompt, safety_settings=safety_settings)
    return response.text

# --- 👈 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정")
    user_api_key = st.text_input("Google API Key", type="password")
    
    selected_model = None
    if user_api_key:
        # [핵심] Flash 모델만 찾음
        found_model = get_high_rpd_model(user_api_key)
        
        if found_model:
            st.success(f"✅ 고속 모델 연결됨:\n{found_model}")
            st.caption("하루 1,500회 무료 제공 모델입니다.")
            selected_model = found_model
        else:
            st.error("❌ 이 API 키로는 'Flash(고속)' 모델을 쓸 수 없습니다.")
            st.warning("Google AI Studio에서 새 프로젝트를 만들고 키를 다시 받아보세요. (Pro 모델은 RPD가 너무 낮아 제외했습니다.)")

    st.divider()
    sheet_id_input = st.text_input("구글 시트 ID", value='1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw')
    sheet_gid_input = st.text_input("시트 GID (탭 번호)", value="0")

# --- 🖥️ 메인 화면 ---

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
        st.error("🚨 API 키를 입력해주세요.")
    elif not selected_model:
        st.error("🚨 RPD가 높은 Flash 모델을 찾지 못해 작업을 중단합니다.")
    elif not keyword:
        st.warning("주제를 입력해주세요.")
    else:
        status_box = st.status("작업을 진행 중입니다...", expanded=True)
        
        status_box.write(":mag: 최신 뉴스 검색 중 (DuckDuckGo)...")
        search_info = get_news_search_ddg(keyword)
        
        if "에러" in search_info or "없음" in search_info:
             status_box.write(f"⚠️ 검색 이슈: {search_info}")
        else:
             status_box.write("✅ 최신 정보 확보 완료!")
        
        status_box.write(":books: 구글 시트 학습 중...")
        sheet_data = get_sheet_data(sheet_id_input, sheet_gid_input)
        
        status_box.write(f":robot_face: {selected_model} 엔진 가동...")
        try:
            config = {"campaign": campaign, "target": target, "note": note}
            raw_text = generate_plan(user_api_key, selected_model, sheet_data, keyword, search_info, config)
            
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            df = pd.read_csv(io.StringIO(clean_csv), sep='|')
            
            content_cols = [c for c in df.columns if '내용' in c]
            if content_cols:
                content_col = content_cols[0]
                def final_formatter(text):
                    text = str(text).replace("(광고)", "").replace("*수신거부:설정>변경", "").strip()
                    if len(text) > 60: text = text[:58] + ".."
                    return f"(광고) {text}\n*수신거부:설정>변경"
                df[content_col] = df[content_col].apply(final_formatter)
            
            status_box.update(label=f":white_check_mark: 완료! ({selected_model})", state="complete", expanded=False)
            st.subheader(":bar_chart: 생성된 마케팅 기획안")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(":inbox_tray: 엑셀 다운로드", csv, f"{keyword}_plan.csv", "text/csv")
            
        except Exception as e:
            status_box.update(label=":x: 오류", state="error")
            st.error(f"에러 내용: {e}")
            if "429" in str(e) or "Quota" in str(e):
                st.error("이 키는 'Flash' 모델조차 할당량이 초과되었거나 막혀있습니다. 새 구글 계정으로 키를 생성해보세요.")
