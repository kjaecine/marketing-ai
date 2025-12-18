import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
import json

# --- 🔒 [사용자 고정 설정] ---
# 아까 주신 키 그대로 사용 (정상 키임이 확인됨)
FIXED_API_KEY = 'AIzaSyAuZqhGnynPLvbpjjbJC7CDR24LZtzVQO4'.strip() 
FIXED_SHEET_ID = '1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw'
# -------------------------

st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="🧞‍♂️", layout="wide")
st.title("🧞‍♂️ AI 마케팅 카피 생성기 (Auto-Discovery)")
st.markdown("구글 서버의 **모델 목록(ListModels)**을 직접 조회하여 404 오류를 해결합니다.")

with st.sidebar:
    st.header("⚙️ 설정 확인")
    # API 키 상태 표시
    if FIXED_API_KEY:
        st.success(f"🔑 API Key 적용됨 ({FIXED_API_KEY[:5]}...)")
    else:
        st.error("API Key가 없습니다.")
        
    sheet_id_input = st.text_input("구글 시트 ID", value=FIXED_SHEET_ID)
    sheet_gid_input = st.text_input("시트 GID", value="0")

# --- 🔧 핵심 함수: 모델 메뉴판 조회 (ListModels) ---

def get_available_model_name(api_key):
    """
    구글 서버에 '사용 가능한 모델 목록'을 요청해서
    가장 적합한 모델의 '정확한 이름'을 가져옵니다.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    try:
        response = requests.get(url)
        if response.status_code != 200:
            st.error(f"모델 목록 조회 실패: {response.text}")
            return None
            
        data = response.json()
        if 'models' not in data:
            st.error("모델 목록이 비어있습니다.")
            return None
            
        # 사용 가능한 모델들 중에서 'generateContent' 기능이 있는 것만 추림
        candidates = []
        for m in data['models']:
            if 'generateContent' in m.get('supportedGenerationMethods', []):
                candidates.append(m['name']) # 예: models/gemini-1.5-flash-001
        
        # 우선순위에 따라 모델 선택 (Flash -> Pro -> 구형 Pro)
        # 이름에 'flash'가 포함된 최신 모델 찾기
        for name in candidates:
            if '1.5-flash' in name: return name.replace('models/', '')
            
        for name in candidates:
            if 'flash' in name: return name.replace('models/', '')
            
        for name in candidates:
            if '1.5-pro' in name: return name.replace('models/', '')
            
        # 정 없으면 목록의 첫 번째 거라도 씀
        if candidates:
            return candidates[0].replace('models/', '')
            
        return "gemini-1.5-flash" # 최후의 수단 (기본값)
        
    except Exception as e:
        st.error(f"모델 탐색 중 에러: {e}")
        return "gemini-1.5-flash"

def call_gemini_dynamic(api_key, prompt, model_name):
    """
    위에서 찾은 '정확한 모델 이름'으로 API를 호출합니다.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7}
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=20)
    
    if response.status_code == 200:
        result = response.json()
        if 'candidates' in result:
            return result['candidates'][0]['content']['parts'][0]['text']
    
    # 실패 시 에러 내용 반환
    raise Exception(f"모델({model_name}) 호출 실패: {response.text}")

# --- (나머지 크롤링/시트 함수는 동일) ---
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
        
        # 1. 모델 메뉴판 조회 (핵심!)
        status_box.write("🛰️ 구글 서버에서 사용 가능한 모델 목록을 조회 중...")
        best_model = get_available_model_name(FIXED_API_KEY)
        
        if not best_model:
            status_box.update(label="❌ 모델 목록 조회 실패", state="error")
            st.stop()
            
        status_box.write(f"✅ 모델 확정: **{best_model}**")
        
        # 2. 정보 수집
        status_box.write("🔍 데이터 수집 중...")
        search_info = get_naver_search(keyword)
        sheet_data = get_sheet_data(sheet_id_input, sheet_gid_input)
        
        # 3. 생성
        status_box.write(f"🤖 기획안 작성 중 ({best_model})...")
        try:
            prompt = f"Role: Copywriter.\nRef: {sheet_data}\nNews: {search_info}\nRequest: {note}\nCreate 5 copies for {keyword}. Output Format: CSV with '|' separator."
            
            raw_text = call_gemini_dynamic(FIXED_API_KEY, prompt, best_model)
            
            # 후처리
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            df = pd.read_csv(io.StringIO(clean_csv), sep='|')
            
            # 법적 문구 추가
            content_col = [c for c in df.columns if '내용' in c][0] 
            df[content_col] = df[content_col].apply(lambda x: f"(광고) {str(x).strip()}\n*수신거부:설정>변경")
            
            status_box.update(label=f"✅ 성공! ({best_model})", state="complete", expanded=False)
            st.subheader("📊 결과")
            st.dataframe(df)
            
        except Exception as e:
            status_box.update(label="❌ 생성 실패", state="error")
            st.error(f"에러 내용: {e}")
