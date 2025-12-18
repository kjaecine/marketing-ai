import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import io
import re
import xml.etree.ElementTree as ET # RSS 파싱용

# --- 🔒 [사용자 고정 설정] ---
FIXED_API_KEY = 'AIzaSyA1HhzAK2y_TCKjb1tG3M7GHnmC5uKh4WM'
FIXED_SHEET_ID = '1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw'
# -------------------------

# --- 🎨 페이지 설정 ---
st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="💎", layout="wide")
st.title("💎 AI 마케팅 카피 생성기 (Google News RSS)")
st.markdown("🚀 **Gemma 3 27B** + **구글 뉴스 RSS(무중단 검색)** + **정밀 패턴 학습**")

# --- 🔧 유틸리티 함수 ---

def get_google_news_rss(keyword):
    """
    구글 뉴스 RSS 피드를 사용하여 최신 뉴스를 가져옵니다.
    이 방식은 크롤링 차단이 없으며 가장 안정적입니다.
    """
    try:
        # 구글 뉴스 한국 서버 RSS URL
        url = f"https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            news_list = []
            
            # 상위 5개 뉴스 아이템 파싱
            count = 0
            for item in root.findall('./channel/item'):
                if count >= 5: break
                title = item.find('title').text
                # RSS description은 HTML 태그가 섞여있어 지저분하므로 제목 위주로 가져옵니다.
                # 마케팅 카피용으로는 제목의 키워드만으로도 충분합니다.
                news_list.append(f"- {title}")
                count += 1
            
            if not news_list:
                return "검색 결과 없음 (최신 뉴스가 없거나 키워드 확인 필요)"
                
            return "\n".join(news_list)
        else:
            return f"뉴스 서버 연결 실패 (Code: {response.status_code})"
            
    except Exception as e:
        return f"뉴스 검색 에러: {str(e)}"

def get_sheet_data(sheet_id, gid):
    try:
        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'
        df = pd.read_csv(url, encoding='utf-8', on_bad_lines='skip')
        if df.empty: return None
        # 데이터가 너무 많으면 최신 50개만
        if len(df) > 50: df = df.tail(50)
        return df.to_markdown(index=False)
    except:
        return None

def generate_plan_gemma_fixed(api_key, context, keyword, purpose, info, user_config):
    genai.configure(api_key=api_key)
    
    # [고정] 사용자 지정 모델
    target_model = 'gemma-3-27b-it'
    
    try:
        model = genai.GenerativeModel(target_model)
        
        custom_instruction = ""
        if user_config['target']: custom_instruction += f"- 타겟: {user_config['target']}\n"
        # 캠페인 목적 반영
        if purpose: custom_instruction += f"- 캠페인 목적(대분류): {purpose}\n"
        if user_config['note']: custom_instruction += f"- 요청사항: {user_config['note']}\n"

        if not context: context = "학습 데이터 없음."

        # 프롬프트: 사용자의 구체적 요구사항(대분류 매핑, 글자수) 완벽 반영
        prompt = f"""
        Role: Senior Viral Marketing Copywriter (Korea).
        
        [Mission]
        1. **PATTERN LEARNING (CRITICAL):** - Reference Data Source: Google Sheet provided below.
           - **Pattern Logic:**
             - '대분류' column = **Campaign Objective** (e.g., 시청유도, 재시청).
             - '추천 콘텐츠' column = **Content Topic** (e.g., {keyword}).
             - '제목/내용' columns = The output style you must mimic.
           - **Task:** Analyze how the tone and angle change based on the 'Campaign Objective' ({purpose}). Apply that specific pattern to the current request.
        
        2. **TASK:** Create 10 marketing messages for '{keyword}' with the objective '{purpose}'.
        
        3. **STRICT LENGTH CONSTRAINTS (CALCULATE CAREFULLY):**
           - **Title:** **20~25 characters (EXCLUDING SPACES).** - Make it catchy and complete. Not too short.
           - **Body:** **40~45 characters (EXCLUDING SPACES).**
             - **IMPORTANT:** Do NOT include `(광고)` or `*수신거부` in your output text.
             - I will add `(광고)`(4 chars) and `*수신거부...`(11 chars) programmatically.
             - So, your generated body text must be around 40-45 chars to keep the TOTAL length under 60 chars.

        4. **CONTENT SOURCE:** Use the [News/Trends Info] below to include real facts (names, dates, events).

        [Reference Data (Sheet)]
        {context}

        [News/Trends Info (Real-time)]
        {info}

        [User Request]
        {custom_instruction}

        [Output Format]
        대분류|캠페인목적|타겟|콘텐츠명|제목|내용
        (CSV format with '|' separator. NO markdown.)
        """
        
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text, target_model

    except Exception as e:
        raise Exception(f"모델 호출 실패 ({target_model}): {str(e)}")

# --- 👈 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정")
    st.success("✅ API Key 적용됨")
    st.info("⚡ 모델: **gemma-3-27b-it** (고정)")

    st.divider()
    sheet_id_input = st.text_input("구글 시트 ID", value=FIXED_SHEET_ID)
    sheet_gid_input = st.text_input("시트 GID (탭 번호)", value="0")

# --- 🖥️ 메인 화면 ---

col1, col2 = st.columns([2, 1])
with col1:
    keyword = st.text_input("📢 홍보할 주제 (콘텐츠명)", placeholder="예: 환승연애4")
with col2:
    purpose = st.text_input("🎯 캠페인 목적 (대분류)", placeholder="예: 시청유도, 재시청, 런칭알림")

col3, col4 = st.columns([1, 1])
with col3:
    target = st.text_input("👥 타겟 설정", placeholder="예: 2030 여성")
with col4:
    note = st.text_input("📝 요청사항", placeholder="예: 호기심 자극, 팩트 강조")

if st.button("🚀 기획안 생성 시작", type="primary"):
    if not keyword:
        st.warning("홍보할 주제(콘텐츠명)를 입력해주세요.")
    elif not purpose:
        st.warning("캠페인 목적을 입력해주세요.")
    else:
        status_box = st.status("작업을 진행 중입니다...", expanded=True)
        
        # 1. 검색 (Google News RSS)
        status_box.write(f":mag: '{keyword}' 구글 뉴스 검색 중 (RSS)...")
        search_info = get_google_news_rss(keyword)
        
        if "없음" in search_info or "에러" in search_info:
             status_box.write(f"⚠️ 검색 상태: {search_info}")
        else:
             status_box.write("✅ 최신 트렌드 정보 확보!")
             with st.expander("뉴스 내용 미리보기"):
                 st.text(search_info)
        
        # 2. 시트
        status_box.write(":books: 구글 시트 학습 중 (패턴 분석)...")
        sheet_data = get_sheet_data(sheet_id_input, sheet_gid_input)
        
        # 3. 생성
        status_box.write(f":robot_face: Gemma 3 (27B) 엔진 가동...")
        try:
            config = {"target": target, "note": note}
            
            raw_text, used_model = generate_plan_gemma_fixed(FIXED_API_KEY, sheet_data, keyword, purpose, search_info, config)
            
            # 파싱
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            df = pd.read_csv(io.StringIO(clean_csv), sep='|')
            
            # 후처리: 법적 문구 추가
            content_cols = [c for c in df.columns if '내용' in c]
            if content_cols:
                content_col = content_cols[0]
                def final_formatter(text):
                    text = str(text).replace("(광고)", "").replace("*수신거부:설정>변경", "").strip()
                    # 법적 문구 결합
                    return f"(광고) {text}\n*수신거부:설정>변경"
                
                df[content_col] = df[content_col].apply(final_formatter)
            
            status_box.update(label=f":white_check_mark: 완료!", state="complete", expanded=False)
            
            st.subheader("📊 생성된 마케팅 기획안")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(":inbox_tray: 엑셀 다운로드", csv, f"{keyword}_plan.csv", "text/csv")
            
        except Exception as e:
            status_box.update(label=":x: 오류", state="error")
            st.error(f"에러 내용: {e}")
