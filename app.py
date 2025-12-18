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
