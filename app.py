import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
import requests
from bs4 import BeautifulSoup
import io

# --- 🔒 [사용자 고정 설정] ---
FIXED_API_KEY = 'AIzaSyCDtgjMmzUIbXGOIzZsYz-s0X1NTjqrUPo' 
FIXED_SHEET_ID = '1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw'
# -------------------------

# --- 🎨 페이지 설정 ---
st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="🧞‍♂️", layout="wide")
st.title("🧞‍♂️ AI 마케팅 카피 생성기 (Diagnosis Mode)")
st.markdown("서버와 통신 가능한 **최적의 모델 이름을 자동으로 찾아** 실행합니다.")

# --- 👈 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정 확인")
    sheet_id_input = st.text_input("구글 시트 ID", value=FIXED_SHEET_ID)
    sheet_gid_input = st.text_input("시트 GID (탭 번호)", value="0")

# --- 🔧 핵심 함수들 ---

def find_working_model(client):
    """
    404 에러를 방지하기 위해 사용 가능한 모델 이름을 직접 테스트하여 찾습니다.
    """
    # 테스트할 모델 이름 후보군 (우선순위 순)
    candidates = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-001",
        "gemini-1.5-flash-002",
        "gemini-1.5-pro",
        "gemini-1.5-pro-001",
        "gemini-2.0-flash-exp" # 최신 실험버전
    ]
    
    print("🔍 모델 연결 테스트 시작...")
    
    for model_name in candidates:
        try:
            # 아주 가벼운 테스트 요청을 보내봄
            client.models.generate_content(
                model=model_name,
                contents="Test",
                config=types.GenerateContentConfig(max_output_tokens=1)
            )
            print(f"✅ 연결 성공: {model_name}")
            return model_name # 성공하면 이 이름 반환
        except Exception as e:
            print(f"❌ 실패 ({model_name}): {e}")
            continue # 실패하면 다음 후보로

    # 다 실패하면 기본값 반환 (어차피 에러 나겠지만 로그 확인용)
    return "gemini-1.5-flash"

def get_sheet_data(sheet_id, gid):
    try:
        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'
        df = pd.read_csv(url, encoding='utf-8', on_bad_lines='skip')
        if df.empty: return None
        if len(df) > 30: df = df.tail(30)
        return df.to_markdown(index=False)
    except:
        return None

def get_naver_search(keyword):
    try:
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sm=tab_opt&sort=1"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        news = [f"[{item.select_one('.news_tit').get_text()}]: {item.select_one('.news_dsc').get_text()}" for item in soup.select(".news_area")[:5]]
        return "\n".join(news) if news else "검색 결과 없음"
    except:
        return "크롤링 차단됨 (기본 정보로 진행)"

def generate_plan(api_key, context, keyword, info, user_config, valid_model_name):
    client = genai.Client(api_key=api_key)
    
    custom_instruction = ""
    if user_config['target']: custom_instruction += f"- 타겟: {user_config['target']}\n"
    if user_config['campaign']: custom_instruction += f"- 캠페인: {user_config['campaign']}\n"
    if user_config['note']: custom_instruction += f"- 요청사항: {user_config['note']}\n"

    if not context: context = "데이터 없음."

    prompt = f"""
    Role: Viral Marketing Copywriter.
    
    [Mission]
    1. **STYLE CLONING:** Mimic the Emoji Usage and Tone from [Reference].
    2. Create 10 marketing messages for '{keyword}'.
    3. **STRICT LIMITS:**
       - **Title:** UNDER 22 Korean characters.
       - **Body:** UNDER 60 Korean characters.
    4. Apply [User Request].

    [Reference]
    {context}

    [News]
    {info}

    [User Request]
    {custom_instruction}

    [Output Format]
    대분류|캠페인|상세타겟_상세타깃_상세설명|추천 콘텐츠|제목|내용
    (CSV format with '|' separator, Header included)
    """

    # 검증된 모델 이름으로 호출
    response = client.models.generate_content(
        model=valid_model_name,
        contents=prompt
    )
    return response.text

# --- 🖥️ 메인 화면 UI ---

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
        
        # 1. 모델 진단 (가장 먼저 수행)
        status_box.write("🛰️ 사용 가능한 AI 모델을 스캔 중...")
        try:
            temp_client = genai.Client(api_key=FIXED_API_KEY)
            valid_model = find_working_model(temp_client)
            status_box.write(f"✅ 연결 성공! 사용 모델: **{valid_model}**")
        except Exception as e:
            status_box.update(label="❌ API 키 또는 네트워크 오류", state="error")
            st.error(f"초기 연결 실패: {e}")
            st.stop()
        
        # 2. 크롤링 및 시트 읽기
        status_box.write("🔍 네이버 뉴스 & 시트 데이터 수집 중...")
        search_info = get_naver_search(keyword)
        sheet_data = get_sheet_data(sheet_id_input, sheet_gid_input)
        
        # 3. 생성
        status_box.write(f"🤖 기획안 작성 중...")
        try:
            config = {"campaign": campaign, "target": target, "note": note}
            raw_text = generate_plan(FIXED_API_KEY, sheet_data, keyword, search_info, config, valid_model)
            
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            df = pd.read_csv(io.StringIO(clean_csv), sep='|')
            
            # 법적 문구 강제 삽입
            content_col = [c for c in df.columns if '내용' in c][0] 
            df[content_col] = df[content_col].apply(
                lambda x: f"(광고) {str(x).strip()}\n*수신거부:설정>변경"
            )
            
            status_box.update(label=f"✅ 완료! (모델: {valid_model})", state="complete", expanded=False)
            
            st.subheader("📊 생성된 마케팅 기획안")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 엑셀 다운로드", csv, f"{keyword}_plan.csv", "text/csv")
            
        except Exception as e:
            status_box.update(label="❌ 오류", state="error")
            st.error(f"에러: {e}")
