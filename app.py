import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io

# --- 🔒 [사용자 고정 설정] ---
# 아까 주신 키를 그대로 넣었습니다. (공백 제거 로직 추가함)
FIXED_API_KEY = 'AIzaSyAuZqhGnynPLvbpjjbJC7CDR24LZtzVQO4'.strip() 
FIXED_SHEET_ID = '1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw'
# -------------------------

st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="🧞‍♂️", layout="wide")
st.title("🧞‍♂️ AI 마케팅 카피 생성기 (X-Ray Mode)")
st.markdown("에러가 나면 **구글이 보낸 상세 메시지**를 그대로 화면에 출력합니다.")

with st.sidebar:
    st.header("⚙️ 설정 확인")
    # 키가 제대로 들어갔는지 확인
    st.text_input("현재 적용된 API Key", value=FIXED_API_KEY, type="password")
    sheet_id_input = st.text_input("구글 시트 ID", value=FIXED_SHEET_ID)
    sheet_gid_input = st.text_input("시트 GID", value="0")

def call_gemini_xray(api_key, prompt):
    """
    모든 모델을 찔러보고, 실패하면 '왜 실패했는지' 상세 사유를 모아서 반환합니다.
    """
    models_to_try = [
        "gemini-1.5-flash", 
        "gemini-1.5-pro",
        "gemini-pro"
    ]

    error_report = [] # 에러 로그 수집

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            # 성공(200)하면 바로 결과 리턴
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result:
                    return result['candidates'][0]['content']['parts'][0]['text'], model, None
            
            # 실패하면 구글이 보낸 메시지를 기록
            error_json = response.json()
            error_msg = error_json.get('error', {}).get('message', response.text)
            log = f"❌ [{model}] 상태코드: {response.status_code} / 사유: {error_msg}"
            print(log)
            error_report.append(log)
                
        except Exception as e:
            error_report.append(f"❌ [{model}] 통신 오류: {str(e)}")

    # 여기까지 왔다는 건 전멸했다는 뜻
    return None, None, "\n".join(error_report)

# ... (나머지 함수 동일) ...
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
        status_box = st.status("진단 모드 실행 중...", expanded=True)
        
        status_box.write("🔍 정보 수집 중...")
        search_info = get_naver_search(keyword)
        sheet_data = get_sheet_data(sheet_id_input, sheet_gid_input)
        
        status_box.write("📡 구글 서버 접속 시도 (X-Ray)...")
        
        prompt = f"Role: Copywriter.\nRef: {sheet_data}\nNews: {search_info}\nCreate 5 copies for {keyword}."
        
        # X-Ray 함수 호출
        raw_text, used_model, error_details = call_gemini_xray(FIXED_API_KEY, prompt)
        
        if raw_text:
            # 성공 시
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            df = pd.read_csv(io.StringIO(clean_csv), sep='|')
            status_box.update(label=f"✅ 성공! ({used_model})", state="complete", expanded=False)
            st.subheader("📊 결과")
            st.dataframe(df)
        else:
            # 실패 시: 상세 에러 출력
            status_box.update(label="❌ 연결 실패 (상세 내용 확인)", state="error")
            st.error("▼ 구글 서버에서 거절한 진짜 이유입니다:")
            st.code(error_details)
            
            st.info("💡 힌트:\n- 400 'API key not valid': 키가 틀렸습니다.\n- 403 'Permission denied': 키가 활성화되지 않았습니다.\n- 429 'Quota exceeded': 무료 사용량 초과입니다.")
