import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
import json

# --- 🔒 [사용자 고정 설정] ---
# 방금 보내주신 따끈따끈한 새 키를 적용했습니다.
FIXED_API_KEY = 'AIzaSyBKeWH-ztYroAmyTk7KX9OxKHGqyKkD48k'.strip() 
FIXED_SHEET_ID = '1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw'
# -------------------------

st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="🧞‍♂️", layout="wide")
st.title("🧞‍♂️ AI 마케팅 카피 생성기 (Final Success)")
st.markdown("새 API 키를 통해 **Gemini 1.5 Flash**를 정상적으로 호출합니다.")

with st.sidebar:
    st.header("⚙️ 설정 확인")
    # 키가 잘 들어갔는지 확인 (보안상 일부만 표시)
    if len(FIXED_API_KEY) > 10:
        masked_key = FIXED_API_KEY[:5] + "..." + FIXED_API_KEY[-4:]
        st.success(f"🔑 Key 적용됨 ({masked_key})")
    else:
        st.error("키가 없습니다.")
    
    sheet_id_input = st.text_input("구글 시트 ID", value=FIXED_SHEET_ID)
    sheet_gid_input = st.text_input("시트 GID", value="0")

# --- 🔧 핵심 함수: 1.5 Flash 직접 호출 ---

def call_gemini_final(api_key, prompt):
    """
    새 프로젝트 키는 1.5 모델 권한이 있으므로,
    가장 표준적인 주소로 바로 접속합니다.
    """
    # 호출할 모델 후보 (1순위: 1.5 Flash)
    models = [
        "gemini-1.5-flash", 
        "gemini-1.5-flash-latest", 
        "gemini-1.5-pro",
        "gemini-pro"
    ]
    
    logs = []

    for model in models:
        # v1beta 주소 사용
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.75, # 창의력 약간 높임
                "maxOutputTokens": 2000
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=20)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and result['candidates']:
                    # ★ 성공 시 텍스트 반환 ★
                    return result['candidates'][0]['content']['parts'][0]['text'], model
            
            # 실패 시 로그 기록
            logs.append(f"⚠️ {model} 실패 ({response.status_code})")
            
        except Exception as e:
            logs.append(f"❌ {model} 에러: {e}")
            continue

    # 모든 시도 실패 시
    raise Exception(f"모든 모델 연결 실패. (로그: {', '.join(logs)})")

# --- (정보 수집 함수들) ---
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

# --- 메인 실행 화면 ---
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
        
        status_box.write("🔍 네이버 뉴스 & 시트 데이터 수집 중...")
        search_info = get_naver_search(keyword)
        sheet_data = get_sheet_data(sheet_id_input, sheet_gid_input)
        
        status_box.write("🤖 Gemini 1.5 Flash 가동 중 (New Key)...")
        try:
            prompt = f"Role: Copywriter.\nRef: {sheet_data}\nNews: {search_info}\nRequest: {note}\nCreate 5 copies for {keyword}. Output Format: CSV with '|' separator."
            
            # 새 키로 실행
            raw_text, used_model = call_gemini_final(FIXED_API_KEY, prompt)
            
            # 후처리
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            df = pd.read_csv(io.StringIO(clean_csv), sep='|')
            
            # 법적 문구 추가
            content_col = [c for c in df.columns if '내용' in c][0] 
            df[content_col] = df[content_col].apply(lambda x: f"(광고) {str(x).strip()}\n*수신거부:설정>변경")
            
            status_box.update(label=f"✅ 성공! (모델: {used_model})", state="complete", expanded=False)
            st.subheader("📊 생성된 마케팅 기획안")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 엑셀 다운로드", csv, f"{keyword}_plan.csv", "text/csv")
            
        except Exception as e:
            status_box.update(label="❌ 오류 발생", state="error")
            st.error(f"에러 내용: {e}")
