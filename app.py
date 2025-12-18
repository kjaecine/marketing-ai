import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
import json

# --- 🔒 [사용자 고정 설정] ---
# 주신 키 그대로 사용
FIXED_API_KEY = 'AIzaSyAuZqhGnynPLvbpjjbJC7CDR24LZtzVQO4'.strip() 
FIXED_SHEET_ID = '1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw'
# -------------------------

st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="🧞‍♂️", layout="wide")
st.title("🧞‍♂️ AI 마케팅 카피 생성기 (Super Fix)")
st.markdown("가능한 모든 **서버 주소(v1/v1beta)**와 **모델**을 교차 검증하여 연결합니다.")

with st.sidebar:
    st.header("⚙️ 설정 확인")
    st.success("🔑 API Key 적용됨")
    sheet_id_input = st.text_input("구글 시트 ID", value=FIXED_SHEET_ID)
    sheet_gid_input = st.text_input("시트 GID", value="0")

# --- 🔧 핵심 함수: 주소 & 모델 교차 폭격 ---

def call_gemini_super_brute(api_key, prompt):
    """
    1. 모델 이름만 바꾸는 게 아니라
    2. 서버 주소(endpoint)도 v1(정식)과 v1beta(베타)를 모두 시도합니다.
    총 12가지 조합을 테스트합니다.
    """
    # 1. 서버 주소 후보
    versions = ["v1beta", "v1"]
    
    # 2. 모델 이름 후보 (안정적인 것 우선)
    models = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash-001",
        "gemini-1.5-pro",
        "gemini-pro"
    ]
    
    logs = []

    print("🚀 Super Brute Force 시작...")

    # 이중 반복문으로 모든 조합 시도
    for version in versions:
        for model in models:
            # 주소 조합: https://.../v1beta/models/... 또는 /v1/models/...
            url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent?key={api_key}"
            headers = {'Content-Type': 'application/json'}
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.7}
            }
            
            try:
                # 2초 정도 짧게 치고 빠지기
                response = requests.post(url, headers=headers, json=data, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    if 'candidates' in result and result['candidates']:
                        # ★ 성공! ★
                        text = result['candidates'][0]['content']['parts'][0]['text']
                        return text, f"{model} ({version})"
                
                # 실패 시 로그만 남기고 조용히 다음으로
                logs.append(f"⚠️ [{version}/{model}] 실패: {response.status_code}")
                
            except Exception as e:
                logs.append(f"❌ [{version}/{model}] 에러: {e}")
                continue

    # 여기까지 왔다면 10번 넘는 시도가 다 실패한 것
    error_summary = "\n".join(logs)
    raise Exception(f"모든 서버/모델 조합 연결 실패.\n[원인분석]\nAPI 키가 'Google AI Studio'에서 발급된 게 맞는지 확인해주세요.\n(Google Cloud Console 키는 권한 설정이 없으면 작동 안 함)\n\n[상세로그]\n{error_summary}")


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
        
        status_box.write("🔍 데이터 수집 중...")
        search_info = get_naver_search(keyword)
        sheet_data = get_sheet_data(sheet_id_input, sheet_gid_input)
        
        status_box.write("🤖 최적의 서버 경로 탐색 중...")
        try:
            prompt = f"Role: Copywriter.\nRef: {sheet_data}\nNews: {search_info}\nRequest: {note}\nCreate 5 copies for {keyword}. Output Format: CSV with '|' separator."
            
            # 교차 폭격 함수 실행
            raw_text, used_path = call_gemini_super_brute(FIXED_API_KEY, prompt)
            
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            df = pd.read_csv(io.StringIO(clean_csv), sep='|')
            
            content_col = [c for c in df.columns if '내용' in c][0] 
            df[content_col] = df[content_col].apply(lambda x: f"(광고) {str(x).strip()}\n*수신거부:설정>변경")
            
            status_box.update(label=f"✅ 성공! (경로: {used_path})", state="complete", expanded=False)
            st.subheader("📊 결과")
            st.dataframe(df)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 엑셀 다운로드", csv, f"{keyword}_plan.csv", "text/csv")
            
        except Exception as e:
            status_box.update(label="❌ 모든 경로 실패", state="error")
            st.error(f"{e}")
            # 진짜 안 되면 키 발급처 링크 제공
            st.markdown("---")
            st.warning("🚨 **그래도 안 되나요?**\nAPI 키가 'Google Cloud'가 아닌 **'Google AI Studio'**에서 발급된 것인지 확인해주세요.\n[👉 여기서 키 발급받기 (Get API key)](https://aistudio.google.com/app/apikey)")
