import streamlit as st
import pandas as pd
from groq import Groq
import requests
from bs4 import BeautifulSoup
import io
import re
import csv
import random

# --- 🔒 [API 키 설정] ---
part1 = "gsk_lIDRWFZfRKNye7Il5egq"
part2 = "WGdyb3FY5WLFI3NtD9NB70RLy6uk4Mce"
FIXED_API_KEY = part1 + part2
FIXED_SHEET_ID = '1rZ4T2aiIU0OsKjMh-gX85Y2OrNoX8YzZI2AVE7CJOMw'
# -------------------------

st.set_page_config(page_title="AI 마케팅 카피 생성기", page_icon="⚡", layout="wide")
st.title("⚡ AI 마케팅 카피 생성기 (News Crawler Fix)")
st.markdown("네이버 보안 우회(Stealth Mode) + 뉴스 팩트체크 기능 적용")

# --- 👈 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정 확인")
    if FIXED_API_KEY.startswith("gsk_"):
        st.success("✅ Groq API Key 연결됨")
    
    sheet_id_input = st.text_input("구글 시트 ID", value=FIXED_SHEET_ID)
    sheet_gid_input = st.text_input("시트 GID (탭 번호)", value="0")

# --- 🔧 유틸리티: 텍스트 정제 ---
def clean_and_format_legal_text(text):
    if not isinstance(text, str): return str(text)
    
    # 1. 중복 법적 문구 제거
    text = text.replace("(광고)", "").replace("*수신거부:설정>변경", "")
    text = text.replace('"', '').replace("'", "")
    
    # 2. 외국어 제거 (이모지, 한글, 숫자, 영어, 기본 문장부호 유지)
    # 베트남어, 한자 등 제거
    foreign_pattern = re.compile(r'[\u4E00-\u9FFF\u00C0-\u024F\u1E00-\u1EFF\u0600-\u06FF\u0400-\u04FF]+')
    text = foreign_pattern.sub('', text)
    
    # 3. 공백 정리
    text = text.strip()
    
    # 4. 법적 문구 부착
    return f"(광고) {text}\n*수신거부:설정>변경"

# --- 🔧 핵심 함수: 시트 데이터 가져오기 ---
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
        recent_rows = all_rows[1:][-300:] # 최신 300개
        
        if len(recent_rows) > 60:
            target_rows = random.sample(recent_rows, 60)
        else:
            target_rows = recent_rows
        
        for row in target_rows:
            clean_row = [cell.strip() for cell in row if cell.strip()]
            if len(clean_row) >= 2:
                if len("".join(clean_row)) > 20:
                    row_str = " | ".join(clean_row)
                    learned_data.append(row_str)
        
        return "\n".join(learned_data)
    except Exception as e:
        return f"Error: {str(e)}"

# --- 🔧 핵심 함수: 네이버 뉴스 수집 (보안 우회 강화) ---
def get_naver_search(keyword):
    try:
        url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sm=tab_opt&sort=1"
        
        # [핵심] 진짜 브라우저처럼 보이는 헤더 정보 (User-Agent, Referer 등)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.naver.com/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        # 접속 실패 시 에러 메시지 반환
        if response.status_code != 200:
            return f"네이버 접속 차단됨 (Status: {response.status_code})"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        news_list = []
        # 뉴스 5개 긁어옴 (제목 + 요약문)
        # 클래스명이 바뀔 경우를 대비해 예외처리
        items = soup.select(".news_area")
        if not items:
            return "뉴스 검색 결과 없음 (HTML 구조 변경 또는 검색어 문제)"
            
        for item in items[:5]:
            title_tag = item.select_one('.news_tit')
            desc_tag = item.select_one('.news_dsc')
            
            if title_tag and desc_tag:
                title = title_tag.get_text()
                desc = desc_tag.get_text()
                news_list.append(f"Title: {title}\nSummary: {desc}")
            
        result = "\n---\n".join(news_list)
        return result if result else "뉴스 검색 결과 없음"
        
    except Exception as e:
        return f"크롤링 시스템 에러: {str(e)}"

# --- 🔧 핵심 함수: Groq 호출 ---
def generate_copy_groq(api_key, context_raw, keyword, info, user_config):
    client = Groq(api_key=api_key)
    
    custom_instruction = ""
    if user_config['target']: custom_instruction += f"- 타겟: {user_config['target']}\n"
    if user_config['note']: custom_instruction += f"- 요청사항: {user_config['note']}\n"

    prompt = f"""
    Role: Professional Viral Marketing Copywriter (Korea).
    
    [YOUR MISSION]
    Create 10 marketing messages for '{keyword}'.
    
    [SOURCE OF TRUTH - NEWS DATA]
    **You MUST use the information below.** If this data contains specific details (names, dates, plot), USE THEM.
    **Do NOT invent facts.**
    
    [News Data]
    {info}
    
    [STRICT TITLE FORMAT]
    **[Emoji] <{keyword}> [Trend/News Hook]**
    - Example: 💘 <나는솔로> 23기 결혼 커플 탄생?
    - Keep under 22 chars.
    
    [CONTENT RULES]
    1. **Language:** Korean ONLY. No Chinese, No Vietnamese.
    2. **Tone:** Trendy, Banmal. No cheap slang (ㅋㅋ, ㅠㅠ).
    3. **Length (Excluding Spaces):** Exactly **45~48 characters**.
    4. **Content:** Don't just say "Watch it". Mention a specific conflict, romance, or event from the [News Data].
    
    [User's Past Data (Style Ref)]
    {context_raw}
    
    [User Request]
    {custom_instruction}

    [Output Format]
    - CSV format with '|' separator.
    - Columns: Category | Campaign | Target | Title | Body
    - **Language:** Korean ONLY.

    **Output ONLY the data rows.**
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7, 
            max_tokens=3000,
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
    keyword = st.text_input("📢 홍보할 주제", placeholder="예: 나는SOLO (또는 환승연애4)")
with col2:
    campaign = st.text_input("🔖 캠페인명", placeholder="예: 런칭알림")
col3, col4 = st.columns([1, 1])
with col3:
    target = st.text_input("🎯 타겟 설정", placeholder="예: 2030 여성")
with col4:
    note = st.text_input("📝 요청사항", placeholder="예: 팩트 기반으로 호기심 자극")

if st.button("🚀 기획안 생성 시작", type="primary"):
    if not keyword:
        st.warning("주제를 입력해주세요.")
    else:
        status_box = st.status("작업을 진행 중입니다...", expanded=True)
        
        status_box.write("🔍 네이버 최신 뉴스 검색 중 (보안 우회 시도)...")
        search_info = get_naver_search(keyword)
        
        # 뉴스 상태 확인 창 (디버깅용)
        if "차단됨" in search_info or "에러" in search_info:
            status_box.write("⚠️ 뉴스 수집 실패. 다시 시도하거나 잠시 후 이용해주세요.")
            st.error(search_info)
        elif "결과 없음" in search_info:
             status_box.write("⚠️ 검색 결과가 없습니다.")
        else:
            status_box.write("✅ 최신 뉴스 확보 완료!")
            with st.expander("📰 수집된 뉴스 데이터 보기"):
                st.text(search_info)
        
        status_box.write("📚 시트 스타일 학습 중...")
        context_raw = get_raw_sheet_text(sheet_id_input, sheet_gid_input)
        
        status_box.write("⚡ Groq 엔진 가동 (팩트체크 & 외국어 필터)...")
        try:
            config = {"campaign": campaign, "target": target, "note": note}
            
            raw_text, used_model = generate_copy_groq(FIXED_API_KEY, context_raw, keyword, search_info, config)
            
            clean_csv = raw_text.replace('```csv', '').replace('```', '').strip()
            lines = clean_csv.split('\n')
            
            data_rows = []
            for line in lines:
                if line.count('|') >= 3:
                    parts = line.split('|')
                    if '대분류' in parts[0] or 'Category' in parts[0] or '분류' in parts[0]:
                        continue
                    data_rows.append(parts)
            
            fixed_columns = ["대분류", "캠페인", "타겟", "제목", "내용"]
            
            if data_rows:
                safe_data = []
                for row in data_rows:
                    if len(row) >= 5:
                        safe_data.append(row[:5])
                    else:
                        safe_data.append(row + [""] * (5 - len(row)))
                        
                df = pd.DataFrame(safe_data, columns=fixed_columns)
            else:
                raise Exception("생성된 데이터가 없습니다.")
            
            # 후처리
            if '내용' in df.columns:
                df['내용'] = df['내용'].apply(clean_and_format_legal_text)
            
            if '제목' in df.columns:
                df['제목'] = df['제목'].apply(lambda x: str(x).strip()[:22])

            status_box.update(label=f"✅ 완료!", state="complete", expanded=False)
            st.subheader("📊 생성된 마케팅 기획안")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 엑셀 다운로드", csv, f"{keyword}_plan.csv", "text/csv")
            
        except Exception as e:
            status_box.update(label="❌ 오류 발생", state="error")
            st.error(f"에러 내용: {e}")
