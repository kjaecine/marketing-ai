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
st.title("🧞‍♂️ AI 마케팅 카피 생성기 (Safe Mode)")
st.markdown("오류가 발생하면 **다른 버전의 1.5 모델**로 즉시 전환하여 실행합니다.")

with st.sidebar:
    st.header("⚙️ 설정 확인")
    if FIXED_API_KEY:
        st.success("🔑 API Key 적용됨")
    sheet_id_input = st.text_input("구글 시트 ID", value=FIXED_SHEET_ID)
    sheet_gid_input = st.text_input("시트 GID", value="0")

# --- 🔧 핵심 함수: 될 때까지 두드리기 ---

def call_gemini_brute_force(api_key, prompt):
    """
    하나의 모델 이름에 의존하지 않고, 
    성공할 때까지 준비된 안전한 모델 리스트를 순회합니다.
    (2.5 버전 제외, 1.5 위주 구성)
    """
    # 시도할 모델 목록 (순서대로 시도)
    safe_models = [
        "gemini-1.5-flash",          # 1순위: 기본 별명
        "gemini-1.5-flash-001",      # 2순위: 구버전 명시
        "gemini-1.5-flash-002",      # 3순위: 신버전 명시
        "gemini-1.5-flash-latest",   # 4순위: 최신 별명
        "gemini-1.5-pro",            # 5순위: 플래시 안되면 프로
        "gemini-pro"                 # 6순위: 구형 프로 (최후의 수단)
    ]
    
    logs = [] # 실패 로그 기록용

    print("🚀 생성 시작...")

    for model_name in safe_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7}
        }
        
        try:
            # 요청 전송
            response = requests.post(url, headers=headers, json=data, timeout=20)
            
            # 200 OK가 아니면 다음으로
            if response.status_code != 200:
                fail_msg = f"⚠️ [{model_name}] 실패 (Status {response.status_code})"
                print(fail_msg)
                logs.append(fail_msg)
                continue 
            
            # 응답 파싱
            result = response.json()
            if 'candidates' in result and result['candidates']:
                content = result['candidates'][0].get('content')
                if content and 'parts' in content:
                    # ★ 성공 시 바로 리턴 (루프 종료) ★
                    return content['parts'][0]['text'], model_name
            
            # 응답은 왔는데 내용이 비어있는 경우
            logs.append(f"⚠️ [{model_name}] 빈 응답 수신")
            continue

        except Exception as e:
            logs.append(f"❌ [{model_name}] 연결 에러: {e}")
            continue

    # 모든 모델이 실패했을 경우
    error_summary = "\n".join(logs)
    raise Exception(f"모든 모델 연결 실패. (상세 로그 아래)\n{error_summary}")


# --- (나머지 함수 동일) ---
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
        
        # 1. 정보 수집
        status_box.write("🔍 데이터 수집 중...")
        search_info = get_naver_search(keyword)
        sheet_data = get_sheet_data(sheet_id_input, sheet_gid_input)
        
        # 2. 생성 (무한 재시도)
        status_box.write("🤖 1.5 모델 연결 시도 중 (순차 접속)...")
        try:
            prompt = f"Role: Copywriter.\nRef: {sheet_data}\nNews: {search_info}\nRequest: {note}\nCreate 5 copies for {keyword}. Output Format: CSV with '|' separator."
            
            # 여기서 6개 모델을 순서대로 다 찔러봅니다
            raw_text, used_model = call_gemini_brute_force(FIXED_API_KEY, prompt)
            
            # 후처리
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            df = pd.read_csv(io.StringIO(clean_csv), sep='|')
            
            # 법적 문구 추가
            content_col = [c for c in df.columns if '내용' in c][0] 
            df[content_col] = df[content_col].apply(lambda x: f"(광고) {str(x).strip()}\n*수신거부:설정>변경")
            
            status_box.update(label=f"✅ 성공! (연결된 모델: {used_model})", state="complete", expanded=False)
            st.subheader("📊 결과")
            st.dataframe(df)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 엑셀 다운로드", csv, f"{keyword}_plan.csv", "text/csv")
            
        except Exception as e:
            status_box.update(label="❌ 모든 시도 실패", state="error")
            st.error(f"최종 에러 내용:\n{e}")
