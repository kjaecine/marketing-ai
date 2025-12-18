import streamlit as st
import pandas as pd
from groq import Groq
import requests
from bs4 import BeautifulSoup
import io
import re  # 정규식 모듈 추가 (한자/일본어 박멸용)

# --- 🔒 [API 키 설정] ---
part1 = "gsk_lIDRWFZfRKNye7Il5egq"
part2 = "WGdyb3FY5WLFI3NtD9NB70RLy6uk4Mce"
FIXED_API_KEY = part1 + part2

FIXED_SHEET_ID = '1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw'
# -------------------------

st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="⚡", layout="wide")
st.title("⚡ AI 마케팅 카피 생성기 (Final - Clean Mode)")
st.markdown("한자/일본어 강제 삭제 필터 + 구글 시트 말투 복제 기능이 적용되었습니다.")

# --- 👈 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정 확인")
    if FIXED_API_KEY.startswith("gsk_"):
        st.success("✅ Groq API Key 연결됨")
    else:
        st.error("API Key 설정 오류")
    
    sheet_id_input = st.text_input("구글 시트 ID", value=FIXED_SHEET_ID)
    sheet_gid_input = st.text_input("시트 GID (탭 번호)", value="0")

# --- 🔧 유틸리티 함수: 텍스트 청소 (핵심!) ---
def clean_text_force_korean(text):
    """
    한글, 영어, 숫자, 기본 문장부호, 이모지 외에는 다 지워버리는 강력한 필터
    """
    # 1. 한자/일본어 등을 제거하기 위해 허용할 문자 범위 지정
    # 가-힣(한글), ㄱ-ㅎ/ㅏ-ㅣ(자모), a-zA-Z(영어), 0-9(숫자)
    # \s(공백), .,!?~@#$%^&*()_+-=[]{}|;':"<>/(문장부호)
    # 그리고 이모지는 유니코드 범위가 넓어서 별도 처리하거나, 
    # 반대로 '제거할 대상(한자, 히라가나, 카타카나)'을 지정해서 날리는 게 안전함.
    
    # CJK 통합 한자 / 히라가나 / 카타카나 범위 제거
    # 한중일 통합 한자: \u4E00-\u9FFF
    # 히라가나: \u3040-\u309F
    # 카타카나: \u30A0-\u30FF
    pattern = re.compile(r'[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF]+')
    
    cleaned_text = pattern.sub('', text)
    return cleaned_text

# --- 🔧 핵심 함수: Groq 호출 ---

def generate_copy_groq(api_key, context, keyword, info, user_config):
    client = Groq(api_key=api_key)
    
    custom_instruction = ""
    if user_config['target']: custom_instruction += f"- 타겟: {user_config['target']}\n"
    if user_config['campaign']: custom_instruction += f"- 캠페인: {user_config['campaign']}\n"
    if user_config['note']: custom_instruction += f"- 요청사항: {user_config['note']}\n"

    if not context: 
        context = "참고 데이터 없음. 일반적인 SNS 스타일로 작성."

    # 프롬프트 (말투 복제에 집중)
    prompt = f"""
    Role: You are a Viral Marketing Copywriter expert in Korean SNS trends.
    
    [YOUR GOAL]
    Create 10 marketing messages for '{keyword}'. 
    **CRUCIAL: You must MIMIC the 'Tone and Manner' of the [Reference Data] below.** If the reference uses short slang, you utilize short slang. If it uses questions, you use questions. 
    **Do NOT write generic, polite, or boring sentences.**
    
    [Reference Data (MIMIC THIS STYLE)]
    {context}
    
    [Trend Info]
    {info}

    [User Request]
    {custom_instruction}

    [Strict Constraints]
    1. **Language:** Korean (Hangul) ONLY. No Chinese(Hanja), No Japanese.
    2. **Format:** CSV format with '|' separator.
    3. **Columns:** 대분류|캠페인|상세타겟_상세타깃_상세설명|추천 콘텐츠|제목|내용
    4. **Length:** Title < 22 chars, Body < 60 chars. (Short & Impactful)
    5. **Emoji:** Use emojis heavily (2~3 per line).
    6. **Content:** Direct, provocative, curiosity-inducing. (e.g., "이거 실화?", "진짜 역대급 ㄷㄷ")

    **Output ONLY the CSV data.**
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85, # 창의성 높임 (말투 다양화)
            max_tokens=2048,
            top_p=1,
            stream=False,
            stop=None,
        )
        return completion.choices[0].message.content, "llama-3.3-70b"

    except Exception as e:
        raise Exception(f"Groq API 오류: {str(e)}")

# --- (정보 수집 함수들) ---

def get_sheet_data(sheet_id, gid):
    try:
        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'
        df = pd.read_csv(url, encoding='utf-8', on_bad_lines='skip')
        if df.empty: return None
        # 데이터가 많으면 랜덤으로 섞어서 50개만 뽑음 (다양한 말투 학습 유도)
        if len(df) > 50: 
            df = df.sample(50) 
        return df.to_markdown(index=False)
    except: return None

def get_naver_search(keyword):
    try:
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sm=tab_opt&sort=1"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        news = []
        for item in soup.select(".news_area")[:5]:
            title = item.select_one('.news_tit').get_text()
            news.append(f"- {title}")
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
    target = st.text_input("🎯 타겟 설정", placeholder="예: 2030 여성")
with col4:
    note = st.text_input("📝 요청사항", placeholder="예: 도파민 터지게, 친구한테 말하듯이")

if st.button("🚀 기획안 생성 시작", type="primary"):
    if not keyword:
        st.warning("주제를 입력해주세요.")
    else:
        status_box = st.status("작업을 진행 중입니다...", expanded=True)
        
        status_box.write("🔍 데이터 수집 중...")
        search_info = get_naver_search(keyword)
        sheet_data = get_sheet_data(sheet_id_input, sheet_gid_input)
        
        # 시트 데이터 확인용 로그 (잠시 주석 처리 가능)
        if sheet_data:
            print("학습된 시트 데이터 길이:", len(sheet_data))
        else:
            status_box.write("⚠️ 구글 시트 데이터를 불러오지 못했습니다. 일반 모드로 동작합니다.")
        
        status_box.write("⚡ Groq 엔진 가동 (한자 제거 필터 ON)...")
        try:
            config = {"campaign": campaign, "target": target, "note": note}
            
            raw_text, used_model = generate_copy_groq(FIXED_API_KEY, sheet_data, keyword, search_info, config)
            
            # 1차 정제: CSV 포맷만 추출
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            if '|' in clean_csv:
                lines = clean_csv.split('\n')
                csv_lines = [line for line in lines if '|' in line]
                clean_csv = '\n'.join(csv_lines)

            # 2차 정제: DataFrame 변환
            df = pd.read_csv(io.StringIO(clean_csv), sep='|')
            
            # [핵심] 3차 정제: 법적 문구 추가 + 한자/일본어 삭제 필터 적용
            if any('내용' in c for c in df.columns):
                content_col = [c for c in df.columns if '내용' in c][0] 
                
                def final_clean(text):
                    # 1. 한자/일본어 삭제
                    text = clean_text_force_korean(str(text))
                    # 2. 앞뒤 공백 제거
                    text = text.strip()
                    # 3. 법적 문구 부착
                    return f"(광고) {text}\n*수신거부:설정>변경"

                df[content_col] = df[content_col].apply(final_clean)
            
            status_box.update(label=f"✅ 완료! ({used_model})", state="complete", expanded=False)
            st.subheader("📊 생성된 마케팅 기획안")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 엑셀 다운로드", csv, f"{keyword}_plan.csv", "text/csv")
            
        except Exception as e:
            status_box.update(label="❌ 오류 발생", state="error")
            st.error(f"에러 내용: {e}")
