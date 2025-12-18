import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import io
from duckduckgo_search import DDGS

# --- 🎨 페이지 설정 ---
st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="🔓", layout="wide")
st.title("🔓 AI 마케팅 카피 생성기 (Open Model Select)")
st.markdown("⚠️ **AI가 모델을 추천하지 않습니다. 사용 가능한 모델을 직접 선택하세요.**")

# --- 🔧 유틸리티 함수 ---

def get_all_models(api_key):
    """
    필터링 없이 계정에서 접근 가능한 '모든' 모델을 가져옵니다.
    """
    genai.configure(api_key=api_key)
    try:
        model_list = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # 모델 이름에서 'models/' 접두사 제거하고 저장
                name = m.name.replace('models/', '')
                model_list.append(name)
        return model_list
    except Exception as e:
        return []

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

def generate_plan_custom(api_key, model_name, context, keyword, info, user_config):
    genai.configure(api_key=api_key)
    
    # 사용자가 선택/입력한 모델명으로 생성 모델 초기화
    target_model = model_name
    # 만약 'models/'가 안 붙어있으면 붙여줌 (안전장치)
    if not target_model.startswith('models/') and not target_model.startswith('tunedModels/'):
         model_name_api = f'models/{target_model}'
    else:
         model_name_api = target_model

    model = genai.GenerativeModel(model_name_api)

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
    
    # 안전 필터 해제
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
    
    final_model_choice = None

    if user_api_key:
        # 1. 사용 가능 모델 목록 가져오기
        available = get_all_models(user_api_key)
        
        # 탭을 나눠서 제공 (목록 선택 vs 직접 입력)
        tab1, tab2 = st.tabs(["📋 목록에서 선택", "⌨️ 직접 입력"])
        
        with tab1:
            if available:
                selected_from_list = st.selectbox("사용 가능한 모델 목록", available)
                st.caption(f"감지된 모델 개수: {len(available)}개")
            else:
                st.error("API 키로 조회된 모델이 없습니다. (직접 입력을 시도해보세요)")
                selected_from_list = None
        
        with tab2:
            manual_input = st.text_input("모델명 직접 입력", placeholder="예: gemini-2.0-flash-lite-preview-02-05")
            st.caption("목록에 없어도 구글이 출시한 신규 모델명을 알면 입력하세요.")
        
        # 최종 모델 결정 로직
        if manual_input:
            final_model_choice = manual_input
            st.info(f"👉 **직접 입력한 모델**을 사용합니다: `{final_model_choice}`")
        elif selected_from_list:
            final_model_choice = selected_from_list
            st.info(f"👉 **선택한 모델**을 사용합니다: `{final_model_choice}`")
            
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
    elif not final_model_choice:
        st.error("🚨 사용할 모델을 선택하거나 입력해주세요.")
    elif not keyword:
        st.warning("주제를 입력해주세요.")
    else:
        status_box = st.status("작업을 진행 중입니다...", expanded=True)
        
        # 1. 검색
        status_box.write(":mag: 최신 뉴스 검색 중 (DuckDuckGo)...")
        search_info = get_news_search_ddg(keyword)
        
        if "에러" in search_info or "없음" in search_info:
             status_box.write(f"⚠️ 검색 이슈: {search_info}")
        else:
             status_box.write("✅ 최신 정보 확보 완료!")
        
        # 2. 시트
        status_box.write(":books: 구글 시트 학습 중...")
        sheet_data = get_sheet_data(sheet_id_input, sheet_gid_input)
        
        # 3. 생성
        status_box.write(f":robot_face: `{final_model_choice}` 엔진 가동...")
        try:
            config = {"campaign": campaign, "target": target, "note": note}
            
            raw_text = generate_plan_custom(user_api_key, final_model_choice, sheet_data, keyword, search_info, config)
            
            # 파싱 & 후처리
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
            
            status_box.update(label=f":white_check_mark: 완료! ({final_model_choice})", state="complete", expanded=False)
            st.subheader(":bar_chart: 생성된 마케팅 기획안")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(":inbox_tray: 엑셀 다운로드", csv, f"{keyword}_plan.csv", "text/csv")
            
        except Exception as e:
            status_box.update(label=":x: 오류", state="error")
            st.error(f"에러 내용: {e}")
            if "404" in str(e):
                st.warning("해당 모델명을 찾을 수 없습니다. 이름이 정확한지 확인하거나 목록에 있는 다른 모델을 써보세요.")
            elif "429" in str(e):
                st.warning(f"선택하신 모델 `{final_model_choice}`의 사용량이 초과되었습니다.")
