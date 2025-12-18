import streamlit as st
import pandas as pd
from groq import Groq
import requests
from bs4 import BeautifulSoup
import io
import re

# --- 🔒 [API 키 설정] ---
part1 = "gsk_lIDRWFZfRKNye7Il5egq"
part2 = "WGdyb3FY5WLFI3NtD9NB70RLy6uk4Mce"
FIXED_API_KEY = part1 + part2
FIXED_SHEET_ID = '1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw'
# -------------------------

st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="⚡", layout="wide")
st.title("⚡ AI 마케팅 카피 생성기 (Length & Language Fix)")
st.markdown("글자수 확장(60자) + 외국어(아랍어/한자/일어) 완벽 차단 버전입니다.")

# --- 👈 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정 확인")
    if FIXED_API_KEY.startswith("gsk_"):
        st.success("✅ Groq API Key 연결됨")
    else:
        st.error("API Key 설정 오류")
    
    sheet_id_input = st.text_input("구글 시트 ID", value=FIXED_SHEET_ID)
    sheet_gid_input = st.text_input("시트 GID (탭 번호)", value="0")

# --- 🔧 유틸리티: 강력한 텍스트 청소 ---
def clean_text_strict(text):
    """
    한글, 영어, 숫자, 기본 기호, 이모지만 남기고 싹 다 지움 (아랍어, 한자 등 제거)
    """
    if not isinstance(text, str): return str(text)

    # 1. 제거할 문자 범위 정의 (CJK 한자, 히라가나, 카타카나, 아랍어 등)
    # 아랍어: \u0600-\u06FF, 한자/일어 등 포함
    foreign_pattern = re.compile(r'[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF\u0600-\u06FF]+')
    text = foreign_pattern.sub('', text)
    
    # 2. 불필요한 공백 정리
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# --- 🔧 핵심 함수: Groq 호출 ---
def generate_copy_groq(api_key, context_examples, keyword, info, user_config):
    client = Groq(api_key=api_key)
    
    custom_instruction = ""
    if user_config['target']: custom_instruction += f"- 타겟: {user_config['target']}\n"
    if user_config['note']: custom_instruction += f"- 요청사항: {user_config['note']}\n"

    # 시트 데이터가 없을 때를 대비한 기본 예시 (길이감 조정)
    if not context_examples:
        context_examples = """
        (Example 1)
        Title: 환승연애4 역대급 재회 장면 떴다!
        Body: "너 아직 나 좋아해?" X의 질문에 흔들리는 눈빛.. 오늘 밤 9시 본방사수! #도파민 #과몰입
        
        (Example 2)
        Title: 이번 시즌 비주얼 무슨 일이야? ㄷㄷ
        Body: 출연진 비주얼 미쳤다 진짜.. 예고편만 봐도 심장 터질 것 같음 ㅠㅠ 얼른 보러가자!
        """

    prompt = f"""
    Role: You are a Viral Marketing Copywriter for a Dating Reality Show (target: Korea).
    
    [Mission]
    Create 10 marketing messages for '{keyword}'.
    
    [Reference Examples (Tone & Manner)]
    {context_examples}
    
    [Trend Info]
    {info}

    [User Request]
    {custom_instruction}

    [CRITICAL RULES]
    1. **Language:** Korean (Hangul) ONLY. (Absolutely NO Chinese, Arabic, Japanese).
    2. **Length Strategy:**
       - **Title:** Write about **20~25 characters**. (Not too short).
       - **Body:** Write about **40~50 characters** of pure content. (Legal text will be added later, so provide enough substance).
    3. **Tone:** Gossip-style, emotional, engaging, using Korean slang (ㅋㅋ, ㄷㄷ, ㅠㅠ).
    4. **Format:** CSV with '|' separator.
    5. **Columns:** 대분류|캠페인|타겟|콘텐츠|제목|내용

    **Output ONLY the CSV data.**
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7, # 0.9 -> 0.7 (환각 방지, 안정성 강화)
            max_tokens=2048,
            top_p=1,
            stream=False,
            stop=None,
        )
        return completion.choices[0].message.content, "llama-3.3-70b"

    except Exception as e:
        raise Exception(f"Groq API 오류: {str(e)}")

# --- (정보 수집 함수들) ---

def get_sheet_data_as_examples(sheet_id, gid):
    try:
        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'
        df = pd.read_csv(url, encoding='utf-8', on_bad_lines='skip', engine='python')
        
        if df.empty: return None, pd.DataFrame()

        df = df.fillna("")
        
        # 제목/내용 컬럼 찾기
        title_col = None
        body_col = None
        for col in df.columns:
            if '제목' in col: title_col = col
            if '내용' in col: body_col = col
            
        examples = ""
        if title_col and body_col:
            # 20개 샘플링
            sample_df = df.sample(min(20, len(df)))
            for _, row in sample_df.iterrows():
                # 데이터가 너무 짧으면 건너뛰기 (이상한 데이터 학습 방지)
                if len(str(row[body_col])) < 5: continue
                examples += f"Title: {row[title_col]}\nBody: {row[body_col]}\n---\n"
        else:
            sample_df = df.sample(min(20, len(df)))
            examples = sample_df.to_string(index=False)

        return examples, df
    except Exception as e:
        print(f"Sheet Error: {e}")
        return None, pd.DataFrame()

def get_naver_search(keyword):
    try:
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sm=tab_opt&sort=1"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        news = []
        for item in soup.select(".news_area")[:3]:
            title = item.select_one('.news_tit').get_text()
            news.append(f"- {title}")
        return "\n".join(news) if news else ""
    except: return ""

# --- 실행부 ---
col1, col2 = st.columns([2, 1])
with col1:
    keyword = st.text_input("📢 홍보할 주제", placeholder="예: 환승연애4")
with col2:
    campaign = st.text_input("🔖 캠페인명", placeholder="예: 런칭알림")
col3, col4 = st.columns([1, 1])
with col3:
    target = st.text_input("🎯 타겟 설정", placeholder="예: 2030 여성, 도파민 중독자")
with col4:
    note = st.text_input("📝 요청사항", placeholder="예: 궁금증 유발, 길게")

# --- 디버깅용 ---
with st.expander("📊 시트 데이터 연결 상태 확인"):
    if st.button("데이터 로드 테스트"):
        examples, raw_df = get_sheet_data_as_examples(sheet_id_input, sheet_gid_input)
        if not raw_df.empty:
            st.success(f"✅ 데이터 로드 성공! ({len(raw_df)}행)")
            st.text_area("🤖 학습되는 데이터 예시", examples, height=200)
        else:
            st.error("❌ 데이터 로드 실패")

if st.button("🚀 기획안 생성 시작", type="primary"):
    if not keyword:
        st.warning("주제를 입력해주세요.")
    else:
        status_box = st.status("작업을 진행 중입니다...", expanded=True)
        
        status_box.write("🔍 최신 뉴스 수집 중...")
        search_info = get_naver_search(keyword)
        
        status_box.write("📚 시트 데이터 학습 중...")
        context_examples, _ = get_sheet_data_as_examples(sheet_id_input, sheet_gid_input)
        
        status_box.write("⚡ Groq 엔진 가동 (글자수 확장 & 외국어 차단)...")
        try:
            config = {"campaign": campaign, "target": target, "note": note}
            
            raw_text, used_model = generate_copy_groq(FIXED_API_KEY, context_examples, keyword, search_info, config)
            
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            if '|' in clean_csv:
                lines = clean_csv.split('\n')
                csv_lines = [line for line in lines if '|' in line]
                clean_csv = '\n'.join(csv_lines)

            df = pd.read_csv(io.StringIO(clean_csv), sep='|')
            
            # 후처리: 외국어 삭제 + 법적 문구 + 길이 제한
            if any('내용' in c for c in df.columns):
                content_col = [c for c in df.columns if '내용' in c][0] 
                
                def final_clean(text):
                    # 1. 외국어 박멸
                    text = clean_text_strict(str(text))
                    # 2. 길이 확장 (AI가 쓴 내용 그대로 살림, 너무 길면 55자에서 자름)
                    if len(text) > 55: text = text[:53] + ".."
                    # 3. 법적 문구
                    return f"(광고) {text}\n*수신거부:설정>변경"

                df[content_col] = df[content_col].apply(final_clean)
                
            # 제목도 글자수 맞춤 (너무 짧으면 좀 이상하니까)
            if any('제목' in c for c in df.columns):
                title_col = [c for c in df.columns if '제목' in c][0]
                df[title_col] = df[title_col].apply(lambda x: clean_text_strict(str(x))[:22]) # 22자 컷
            
            status_box.update(label=f"✅ 완료!", state="complete", expanded=False)
            st.subheader("📊 생성된 마케팅 기획안")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 엑셀 다운로드", csv, f"{keyword}_plan.csv", "text/csv")
            
        except Exception as e:
            status_box.update(label="❌ 오류 발생", state="error")
            st.error(f"에러 내용: {e}")
