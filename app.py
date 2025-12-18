import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
import json

# --- 🔒 [사용자 고정 설정] ---
FIXED_API_KEY = 'AIzaSyAuZqhGnynPLvbpjjbJC7CDR24LZtzVQO4'.strip() 
FIXED_SHEET_ID = '1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw'
# -------------------------

st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="🧞‍♂️", layout="wide")
st.title("🧞‍♂️ AI 마케팅 카피 생성기 (Gemini 1.5 Fixed)")
st.markdown("안정적인 **Gemini 1.5 Flash** 모델만 골라서 연결합니다.")

with st.sidebar:
    st.header("⚙️ 설정 확인")
    if FIXED_API_KEY:
        st.success(f"🔑 API Key 적용됨")
    else:
        st.error("API Key가 없습니다.")
        
    sheet_id_input = st.text_input("구글 시트 ID", value=FIXED_SHEET_ID)
    sheet_gid_input = st.text_input("시트 GID", value="0")

# --- 🔧 핵심 함수: 1.5 모델만 콕 집어내기 ---

def get_stable_1_5_model(api_key):
    """
    RPD 이슈가 있는 2.5 버전은 거르고,
    안정적인 1.5 Flash 버전을 목록에서 찾아냅니다.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    try:
        response = requests.get(url)
        if response.status_code != 200:
            st.error(f"모델 목록 조회 실패: {response.text}")
            return "gemini-1.5-flash" # 실패 시 기본값 강제

        data = response.json()
        if 'models' not in data:
            return "gemini-1.5-flash"
            
        candidates = [m['name'].replace('models/', '') for m in data['models']]
        
        # ★ 핵심 수정: 우선순위 지정 (2.5 절대 배제) ★
        
        # 1순위: 1.5 Flash 최신 버전 찾기
        for name in candidates:
            if 'gemini-1.5-flash' in name and 'latest' in name: return name
            
        # 2순위: 1.5 Flash 특정 버전 (001, 002 등)
        for name in candidates:
            if 'gemini-1.5-flash' in name and '00' in name: return name
            
        # 3순위: 그냥 1.5 Flash
        for name in candidates:
            if 'gemini-1.5-flash' in name: return name
            
        # 1.5 Flash가 정 없으면 1.5 Pro라도 사용
        for name in candidates:
            if 'gemini-1.5-pro' in name: return name
            
        # 목록에 아무것도 없으면 강제 지정
        return "gemini-1.5-flash"
        
    except Exception as e:
        print(f"탐색 에러: {e}")
        return "gemini-1.5-flash"

def call_gemini_direct(api_key, prompt, model_name):
    """
    찾아낸 모델로 요청을 보냅니다. (빈 응답 에러 처리 포함)
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        # 상태 코드 확인
        if response.status_code != 200:
            raise Exception(f"API 오류 ({response.status_code}): {response.text}")
            
        result = response.json()
        
        # ★ 핵심 수정: list index out of range 방지 ★
        if 'candidates' in result and len(result['candidates']) > 0:
            content = result['candidates'][0].get('content')
            if content and 'parts' in content:
                return content['parts'][0]['text']
            else:
                raise Exception("생성된 텍스트가 비어있습니다. (Safety 필터 등)")
        else:
            # candidates가 비어서 오면 보통 Safety 이슈거나 내부 오류
            raise Exception(f"응답은 왔으나 내용이 없습니다. 결과: {result}")
            
    except Exception as e:
        raise e

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
        
        # 1. 모델 확정 (1.5 우선)
        status_box.write("🛰️ 안정적인 Gemini 1.5 모델을 찾는 중...")
        best_model = get_stable_1_5_model(FIXED_API_KEY)
        
        # 혹시라도 2.5가 잡혔는지 재확인 (안전장치)
        if '2.5' in best_model:
             best_model = 'gemini-1.5-flash' # 강제 변경
             
        status_box.write(f"✅ 사용 모델 확정: **{best_model}**")
        
        # 2. 정보 수집
        status_box.write("🔍 데이터 수집 중...")
        search_info = get_naver_search(keyword)
        sheet_data = get_sheet_data(sheet_id_input, sheet_gid_input)
        
        # 3. 생성
        status_box.write(f"🤖 기획안 작성 중...")
        try:
            prompt = f"Role: Copywriter.\nRef: {sheet_data}\nNews: {search_info}\nRequest: {note}\nCreate 5 copies for {keyword}. Output Format: CSV with '|' separator."
            
            raw_text = call_gemini_direct(FIXED_API_KEY, prompt, best_model)
            
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
