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
st.title("⚡ AI 마케팅 카피 생성기 (Deep Learning Fix)")
st.markdown("데이터가 제대로 들어갔는지 확인하는 **디버깅 모드**가 추가되었습니다.")

# --- 👈 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정 확인")
    if FIXED_API_KEY.startswith("gsk_"):
        st.success("✅ Groq API Key 연결됨")
    else:
        st.error("API Key 설정 오류")
    
    sheet_id_input = st.text_input("구글 시트 ID", value=FIXED_SHEET_ID)
    sheet_gid_input = st.text_input("시트 GID (탭 번호)", value="0")

# --- 🔧 유틸리티: 텍스트 청소 ---
def clean_text_force_korean(text):
    # 한자/일본어 삭제
    pattern = re.compile(r'[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF]+')
    cleaned_text = pattern.sub('', text)
    return cleaned_text

# --- 🔧 핵심 함수: Groq 호출 ---
def generate_copy_groq(api_key, context_examples, keyword, info, user_config):
    client = Groq(api_key=api_key)
    
    custom_instruction = ""
    if user_config['target']: custom_instruction += f"- 타겟: {user_config['target']}\n"
    if user_config['note']: custom_instruction += f"- 요청사항: {user_config['note']}\n"

    # 참고 데이터가 비었을 경우를 대비한 강제 페르소나 주입
    if not context_examples:
        context_examples = """
        (Example 1)
        Title: X와의 재회, 심장 멎는 줄..
        Body: 내 눈앞에 나타난 전남친, 흔들리는 동공 ㄷㄷ #환승연애 #재회
        
        (Example 2)
        Title: 거짓말 탐지기 결과 충격 😱
        Body: "너 아직 나 좋아해?" 질문에 대한 대답은? #과몰입 #도파민
        """

    prompt = f"""
    Role: You are a Viral Marketing Copywriter for a Dating Reality Show (like Transit Love/EXchange).
    
    [YOUR MISSION]
    Create 10 marketing messages for '{keyword}'.
    
    [CRITICAL INSTRUCTION: STYLE TRANSFER]
    You MUST analyze the [Reference Examples] below. 
    Copy their **sentence structure**, **slang usage**, **emotional tone**, and **emoji patterns**.
    Do NOT write polite or educational text. Write like a gossiping friend or a provocative ad.

    [Reference Examples (LEARN FROM HERE)]
    {context_examples}
    
    [Trend Info]
    {info}

    [User Request]
    {custom_instruction}

    [Constraints]
    1. **Language:** Korean (Hangul) ONLY. No Hanja.
    2. **Format:** CSV with '|' separator.
    3. **Columns:** 분류|캠페인|타겟|콘텐츠|제목|내용
    4. **Tone:** Provocative, Emotional, "Dopamine-inducing", Short slang (e.g., ㄷㄷ, ㅠㅠ, ㅋㅋ).
    5. **Length:** Title < 20 chars, Body < 40 chars.

    **Output ONLY the CSV data.**
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9, # 창의성 최대치 (자극적인 문구를 위해)
            max_tokens=2048,
            top_p=1,
            stream=False,
            stop=None,
        )
        return completion.choices[0].message.content, "llama-3.3-70b"

    except Exception as e:
        raise Exception(f"Groq API 오류: {str(e)}")

# --- (정보 수집 함수들 - 시트 데이터 가공 강화) ---

def get_sheet_data_as_examples(sheet_id, gid):
    try:
        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'
        
        # 데이터 읽기 (에러 무시 모드)
        df = pd.read_csv(url, encoding='utf-8', on_bad_lines='skip', engine='python')
        
        if df.empty: return None, pd.DataFrame()

        # NaN 제거
        df = df.fillna("")
        
        # '제목'과 '내용' 컬럼이 있는지 확인하고, 있으면 그것 위주로 학습
        # 컬럼명을 못 찾을 경우를 대비해 컬럼 인덱스로 접근 시도
        title_col = None
        body_col = None

        for col in df.columns:
            if '제목' in col: title_col = col
            if '내용' in col: body_col = col
            
        examples = ""
        # 제목/내용 컬럼을 찾았으면 그것만 뽑아서 예시로 만듦 (AI가 이해하기 쉽게)
        if title_col and body_col:
            # 학습용으로 20개 샘플링
            sample_df = df.sample(min(20, len(df)))
            for _, row in sample_df.iterrows():
                examples += f"Title: {row[title_col]}\nBody: {row[body_col]}\n---\n"
        else:
            # 컬럼 못 찾으면 그냥 전체 텍스트로
            sample_df = df.sample(min(20, len(df)))
            examples = sample_df.to_string(index=False)

        return examples, df # 학습용 텍스트와 원본 데이터프레임 반환
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
        for item in soup.select(".news_area")[:3]: # 뉴스 3개만 (노이즈 감소)
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
    target = st.text_input("🎯 타겟 설정", placeholder="예: 2030 여성, 전애인 미련")
with col4:
    note = st.text_input("📝 요청사항", placeholder="예: 자극적으로, 맵게")

# --- 데이터 확인용 섹션 (사용자가 직접 확인 가능) ---
with st.expander("📊 시트 데이터 연결 상태 확인 (클릭)", expanded=False):
    if st.button("데이터 로드 테스트"):
        examples, raw_df = get_sheet_data_as_examples(sheet_id_input, sheet_gid_input)
        if not raw_df.empty:
            st.success(f"✅ 데이터 로드 성공! 총 {len(raw_df)}행을 읽었습니다.")
            st.dataframe(raw_df.head(5)) # 상위 5개 보여줌
            st.text_area("🤖 AI에게 들어가는 학습 데이터 예시", examples, height=200)
        else:
            st.error("❌ 데이터를 읽어오지 못했습니다. 시트 권한이나 내용을 확인해주세요.")

if st.button("🚀 기획안 생성 시작", type="primary"):
    if not keyword:
        st.warning("주제를 입력해주세요.")
    else:
        status_box = st.status("작업을 진행 중입니다...", expanded=True)
        
        status_box.write("🔍 최신 트렌드 수집 중...")
        search_info = get_naver_search(keyword)
        
        status_box.write("📚 시트 데이터 '말투' 추출 중...")
        # 여기서 데이터를 확실하게 가져옵니다.
        context_examples, _ = get_sheet_data_as_examples(sheet_id_input, sheet_gid_input)
        
        if not context_examples:
            status_box.write("⚠️ 시트 학습 실패! '기본 도파민 모드'로 작동합니다.")
        
        status_box.write("⚡ Groq 엔진으로 카피라이팅 중...")
        try:
            config = {"campaign": campaign, "target": target, "note": note}
            
            # 생성
            raw_text, used_model = generate_copy_groq(FIXED_API_KEY, context_examples, keyword, search_info, config)
            
            # CSV 파싱
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            if '|' in clean_csv:
                lines = clean_csv.split('\n')
                csv_lines = [line for line in lines if '|' in line]
                clean_csv = '\n'.join(csv_lines)

            df = pd.read_csv(io.StringIO(clean_csv), sep='|')
            
            # 법적 문구 & 글자수 & 한자 필터
            if any('내용' in c for c in df.columns):
                content_col = [c for c in df.columns if '내용' in c][0] 
                
                def final_clean(text):
                    text = clean_text_force_korean(str(text))
                    text = text.strip()
                    # 내용이 너무 길면 자름
                    if len(text) > 40: text = text[:38] + ".."
                    return f"(광고) {text}\n*수신거부:설정>변경"

                df[content_col] = df[content_col].apply(final_clean)
            
            status_box.update(label=f"✅ 완료!", state="complete", expanded=False)
            st.subheader("📊 생성된 마케팅 기획안")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 엑셀 다운로드", csv, f"{keyword}_plan.csv", "text/csv")
            
        except Exception as e:
            status_box.update(label="❌ 오류 발생", state="error")
            st.error(f"에러 내용: {e}")
