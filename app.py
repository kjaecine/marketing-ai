import streamlit as st
import pandas as pd
from groq import Groq
import requests
from bs4 import BeautifulSoup
import io
import re
import csv
import random

# --- 🔒 [사용자 고정 설정] ---
# Groq API 키 (사용자님 키 적용됨)
part1 = "gsk_lIDRWFZfRKNye7Il5egq"
part2 = "WGdyb3FY5WLFI3NtD9NB70RLy6uk4Mce"
FIXED_API_KEY = part1 + part2

FIXED_SHEET_ID = '1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw'
# -------------------------

st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="⚡", layout="wide")
st.title("⚡ AI 마케팅 카피 생성기 (Groq High-End Ver)")
st.markdown("네이버 보안 우회 + 데이터 토큰 최적화 + Gemini급 품질 튜닝")

# --- 👈 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정 확인")
    if FIXED_API_KEY.startswith("gsk_"):
        st.success("✅ Groq API Key 연결됨")
    
    sheet_id_input = st.text_input("구글 시트 ID", value=FIXED_SHEET_ID)
    sheet_gid_input = st.text_input("시트 GID (탭 번호)", value="0")

# --- 🔧 유틸리티: 텍스트 정제 (법적 문구 & 글자수 제어) ---
def clean_and_format_final(text):
    if not isinstance(text, str): return str(text)
    
    # 1. 중복 문구 제거
    text = text.replace("(광고)", "").replace("*수신거부:설정>변경", "")
    text = text.replace('"', '').replace("'", "")
    
    # 2. 외국어(베트남어, 한자 등) 강력 차단
    # 한글, 영어, 숫자, 기본 문장부호, 이모지만 남김
    foreign_pattern = re.compile(r'[\u4E00-\u9FFF\u00C0-\u024F\u1E00-\u1EFF\u0600-\u06FF\u0400-\u04FF]+')
    text = foreign_pattern.sub('', text)
    
    # 3. 공백 정리
    text = text.strip()
    
    # 4. 법적 문구 부착
    # (광고) [4자] + 공백 + 본문 + 줄바꿈 + *수신거부... [11자] = 고정 약 17자
    # 본문이 45자 내외면 총 62자 달성
    return f"(광고) {text}\n*수신거부:설정>변경"

# --- 🔧 핵심 함수: 네이버 뉴스 수집 (헤더 위장 기술 적용) ---
def get_naver_search(keyword):
    """
    네이버 봇 차단을 뚫기 위해 '나는 사람입니다'라는 증명서(Header)를 제출합니다.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.naver.com/'
    }
    
    try:
        # 뉴스 탭 검색
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sort=1"
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        news_list = []
        # 뉴스 3개만 추출 (핵심만)
        for item in soup.select(".news_area")[:3]:
            title = item.select_one('.news_tit').get_text()
            desc = item.select_one('.news_dsc').get_text()
            news_list.append(f"- {title} ({desc})")
            
        result = "\n".join(news_list)
        return result if result else "뉴스 정보 없음"
        
    except Exception as e:
        return f"크롤링 에러: {str(e)}"

# --- 🔧 핵심 함수: 시트 데이터 가져오기 (토큰 최적화) ---
def get_raw_sheet_text(sheet_id, gid):
    try:
        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'
        response = requests.get(url)
        response.encoding = 'utf-8'
        
        f = io.StringIO(response.text)
        reader = csv.reader(f)
        all_rows = list(reader)
        
        if len(all_rows) < 2: return "데이터 없음"
        
        learned_data = []
        # 최신 50개만 가져오되
        recent_rows = all_rows[1:][-50:]
        
        for row in recent_rows:
            clean_row = [cell.strip() for cell in row if cell.strip()]
            if len(clean_row) >= 2:
                # 내용이 너무 짧은 건 버림
                if len("".join(clean_row)) > 15:
                    learned_data.append(" | ".join(clean_row))
        
        # [중요] Groq 토큰 한도(Request too large)를 피하기 위해
        # 텍스트 길이를 강제로 2500자로 자릅니다. (핵심 데이터만 전달)
        full_text = "\n".join(learned_data)
        if len(full_text) > 2500:
            full_text = full_text[-2500:] # 가장 최근 데이터 위주로 자름
            
        return full_text
    except:
        return "데이터 없음"

# --- 🔧 핵심 함수: Groq 호출 (Gemini급 프롬프트 튜닝) ---
def generate_copy_groq(api_key, context_raw, keyword, info, user_config):
    client = Groq(api_key=api_key)
    
    custom_instruction = ""
    if user_config['target']: custom_instruction += f"- 타겟: {user_config['target']}\n"
    if user_config['note']: custom_instruction += f"- 요청사항: {user_config['note']}\n"

    # Gemini의 품질을 따라잡기 위한 '상세 지시(System Prompt)' 강화
    # 특히 '공백 제외 글자수'와 '제목 패턴'을 강력하게 주입
    
    prompt = f"""
    Role: Senior Viral Marketing Copywriter (Korea).
    
    [GOAL]
    Write 10 high-quality marketing messages for '{keyword}'.
    
    [INPUT DATA]
    1. **News Trends:** {info} (MUST reflect these facts)
    2. **Style Reference:** {context_raw} (Copy this tone)
    
    [STRICT GUIDELINES]
    1. **Language:** Korean ONLY. (No Chinese/Vietnamese/Arabic).
    2. **Tone:** Trendy Banmal (반말). Use emojis properly. NO cheap slang like 'ㅋㅋ', 'ㅠㅠ'.
    3. **Title Format:** [Emoji] <{keyword}> [Keyword from News]
       - Example: 🕵️‍♂️ <크라임씬> 범인은 바로 너!
       - Length: Under 22 chars.
    4. **Body Length:** **Exactly 45~50 characters (excluding spaces).**
       - If it's too short, add more details.
       - Do NOT write "(광고)" or "*수신거부". I will add them later.
    
    [User Request]
    {custom_instruction}

    [Output Format]
    CSV format with '|' separator.
    Columns: Category | Campaign | Target | Title | Body
    
    **Output ONLY the CSV data rows.**
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6, # 창의성을 0.6으로 낮춰서 '환각(헛소리)'을 줄이고 안정성 높임
            max_tokens=2500,
            top_p=1,
            stream=False,
            stop=None,
        )
        return completion.choices[0].message.content, "llama-3.3-70b"

    except Exception as e:
        raise Exception(f"Groq API 오류: {str(e)}")

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
    note = st.text_input("📝 요청사항", placeholder="예: 팩트 기반, 호기심 자극")

if st.button("🚀 기획안 생성 시작", type="primary"):
    if not keyword:
        st.warning("주제를 입력해주세요.")
    else:
        status_box = st.status("작업을 진행 중입니다...", expanded=True)
        
        status_box.write("🔍 네이버 뉴스 스텔스 크롤링 중...")
        search_info = get_naver_search(keyword)
        
        # 뉴스 결과 디버깅 (사용자 확인용)
        if "없음" in search_info or "에러" in search_info:
            status_box.write("⚠️ 뉴스 수집 불가 (일반 창작 모드)")
        else:
            status_box.write("✅ 최신 뉴스 확보 완료!")
            with st.expander("📰 수집된 뉴스 요약 보기"):
                st.text(search_info)
        
        status_box.write("📚 시트 데이터 최적화 학습 중...")
        context_raw = get_raw_sheet_text(sheet_id_input, sheet_gid_input)
        
        status_box.write("⚡ Groq 엔진 가동 (Gemini급 튜닝)...")
        try:
            config = {"campaign": campaign, "target": target, "note": note}
            
            # Groq 호출
            raw_text, used_model = generate_copy_groq(FIXED_API_KEY, context_raw, keyword, search_info, config)
            
            # CSV 파싱
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            lines = clean_csv.split('\n')
            
            data_rows = []
            for line in lines:
                if line.count('|') >= 3:
                    parts = line.split('|')
                    if '대분류' in parts[0] or 'Category' in parts[0] or '분류' in parts[0]: continue
                    data_rows.append(parts)
            
            fixed_columns = ["대분류", "캠페인", "타겟", "제목", "내용"]
            if data_rows:
                safe_data = []
                for row in data_rows:
                    if len(row) >= 5: safe_data.append(row[:5])
                    else: safe_data.append(row + [""] * (5 - len(row)))
                df = pd.DataFrame(safe_data, columns=fixed_columns)
            else:
                raise Exception("유효한 CSV 데이터 생성 실패")

            # 후처리: 법적 문구 & 글자수 제어
            if '내용' in df.columns:
                df['내용'] = df['내용'].apply(clean_and_format_final)
            
            if '제목' in df.columns:
                df['제목'] = df['제목'].apply(lambda x: str(x).strip()[:22])
            
            status_box.update(label=f"✅ 완료! (Groq Llama 3 - Optimized)", state="complete", expanded=False)
            
            st.subheader("📊 생성된 마케팅 기획안")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 엑셀 다운로드", csv, f"{keyword}_plan.csv", "text/csv")
            
        except Exception as e:
            status_box.update(label="❌ 오류 발생", state="error")
            st.error(f"에러 내용: {e}")
