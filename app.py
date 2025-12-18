import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import io

# --- 🎨 페이지 설정 ---
st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="🧞‍♂️", layout="wide")

st.title("🧞‍♂️ AI 마케팅 카피 생성기 (Auto-Detect Model)")
st.markdown("구글 시트의 **톤앤매너**를 학습하고, **네이버 최신 뉴스**를 반영하여 기획안을 작성합니다.")

# --- 👈 사이드바: 설정 구간 ---
with st.sidebar:
    st.header("⚙️ 기본 설정")
    GEMINI_API_KEY = st.text_input("Gemini API Key", type="password", help="Google AI Studio에서 발급받은 키를 입력하세요.")
    SPREADSHEET_ID = st.text_input("구글 시트 ID", value="1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw")
    SHEET_GID = st.text_input("시트 GID (보통 0)", value="0")
    
    st.divider()
    st.info("💡 API 키는 저장되지 않으며 새로고침 시 초기화됩니다.")

# --- 🔧 핵심 함수들 ---

def get_available_model(api_key):
    """
    내 API 키로 사용 가능한 모델을 자동으로 찾아냅니다. (404 에러 방지)
    """
    genai.configure(api_key=api_key)
    try:
        # 사용 가능한 모델 목록을 조회
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # 1순위: Flash 모델 (빠름)
                if 'flash' in m.name: return m.name
                # 2순위: Pro 모델 (성능 좋음)
                if 'pro' in m.name: return m.name
        # 목록 조회는 됐는데 딱히 못 찾았으면 기본값
        return 'models/gemini-pro'
    except:
        # 목록 조회조차 실패하면 가장 기본 모델 반환
        return 'models/gemini-pro'

def get_sheet_data(sheet_id, gid):
    """구글 시트 데이터 가져오기 (최신 30개)"""
    try:
        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'
        df = pd.read_csv(url, on_bad_lines='skip')
        if df.empty: return None
        if len(df) > 30: df = df.tail(30)
        return df.to_markdown(index=False)
    except Exception as e:
        return None

def get_naver_search(keyword):
    """네이버 뉴스 크롤링"""
    try:
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sm=tab_opt&sort=1"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        news_list = []
        for item in soup.select(".news_area")[:5]:
            title = item.select_one(".news_tit").get_text()
            desc = item.select_one(".news_dsc").get_text()
            news_list.append(f"[{title}]: {desc}")
            
        return "\n".join(news_list) if news_list else "검색 결과 없음"
    except:
        return "크롤링 차단됨 (기본 정보로 진행)"

def generate_plan(api_key, context, keyword, info, user_config):
    """기획안 생성"""
    # 1. 모델 자동 탐색 (여기가 핵심!)
    model_name = get_available_model(api_key)
    
    # 2. 모델 설정
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    custom_instruction = ""
    if user_config['target']: custom_instruction += f"- 타겟: {user_config['target']}\n"
    if user_config['campaign']: custom_instruction += f"- 캠페인: {user_config['campaign']}\n"
    if user_config['note']: custom_instruction += f"- 요청사항: {user_config['note']}\n"

    if not context: context = "데이터 없음. 일반적인 마케팅 톤 사용."

    prompt = f"""
    Role: Marketing Expert.
    
    [Mission]
    1. Learn style from [Reference].
    2. Create 10 marketing messages for '{keyword}' based on [News].
    3. Apply [User Request] strictly.
    4. Output MUST be a CSV format with '|' separator.

    [Reference]
    {context}

    [News]
    {info}

    [User Request]
    {custom_instruction}

    [Output Format]
    대분류|캠페인|상세타겟_상세타깃_상세설명|추천 콘텐츠|제목|내용
    (Include header, Use '|' separator)
    """
    
    response = model.generate_content(prompt)
    return response.text, model_name

# --- 🖥️ 메인 화면 UI ---

col1, col2 = st.columns([2, 1])

with col1:
    keyword = st.text_input("📢 홍보할 주제 (키워드)", placeholder="예: 환승연애4, 갤럭시S24")

with col2:
    campaign = st.text_input("🔖 캠페인명 (선택)", placeholder="예: 런칭알림")

col3, col4 = st.columns([1, 1])
with col3:
    target = st.text_input("🎯 타겟 설정 (선택)", placeholder="예: 30대 직장인")
with col4:
    note = st.text_input("📝 특이사항/요청 (선택)", placeholder="예: 도파민 강조해줘")

if st.button("🚀 기획안 생성 시작", type="primary"):
    if not GEMINI_API_KEY:
        st.error("좌측 사이드바에 API 키를 입력해주세요!")
    elif not keyword:
        st.warning("홍보할 주제를 입력해주세요.")
    else:
        status_box = st.status("작업을 진행 중입니다...", expanded=True)
        
        # 1. 정보 수집
        status_box.write("🔍 네이버 뉴스 검색 중...")
        search_info = get_naver_search(keyword)
        
        # 2. 시트 읽기
        status_box.write("📚 구글 시트 학습 중...")
        sheet_data = get_sheet_data(SPREADSHEET_ID, SHEET_GID)
        
        # 3. 생성
        status_box.write("🤖 모델을 찾고 기획안을 작성 중...")
        try:
            user_config = {"campaign": campaign, "target": target, "note": note}
            
            # 생성 함수 호출
            raw_text, used_model = generate_plan(GEMINI_API_KEY, sheet_data, keyword, search_info, user_config)
            
            # 4. 결과 변환
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            df = pd.read_csv(io.StringIO(clean_csv), sep='|')
            
            status_box.update(label=f"✅ 생성 완료! (사용 모델: {used_model})", state="complete", expanded=False)
            
            st.subheader("📊 생성된 마케팅 기획안")
            st.data_editor(df, num_rows="dynamic", use_container_width=True)
            
            # CSV 다운로드 버튼
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 엑셀(CSV)로 다운로드",
                data=csv,
                file_name=f"{keyword}_marketing_plan.csv",
                mime="text/csv",
            )
            
        except Exception as e:
            status_box.update(label="❌ 오류 발생", state="error")
            st.error(f"에러 내용: {e}")
