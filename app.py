import streamlit as st
import requests
import json
import pandas as pd

# --- 🔒 [사용자 고정 설정] ---
FIXED_API_KEY = 'AIzaSyDRM_1h6IEoSnf06auPiqk2nj-Cx2lVmKM'.strip() 
# -------------------------

st.set_page_config(page_title="API 정밀 진단기", page_icon="🩺", layout="wide")
st.title("🩺 Google API 정밀 진단")
st.markdown("현재 API 키로 접근 가능한 **모든 모델 목록**을 조회합니다.")

def diagnose_key(api_key):
    # 1. 모델 리스트 조회 (v1beta)
    url_list = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    st.write("---")
    st.subheader("📡 1. 모델 목록 조회 결과")
    
    try:
        response = requests.get(url_list, timeout=10)
        
        # 상태 코드 확인
        st.write(f"**상태 코드:** `{response.status_code}`")
        
        if response.status_code == 200:
            data = response.json()
            if 'models' in data:
                models = data['models']
                st.success(f"✅ 조회 성공! 총 {len(models)}개의 모델이 발견되었습니다.")
                
                # 표로 보여주기
                df = pd.DataFrame(models)
                # 보기 좋게 컬럼 정리
                if 'name' in df.columns:
                    df['name'] = df['name'].apply(lambda x: x.replace('models/', ''))
                st.dataframe(df[['name', 'supportedGenerationMethods', 'version']], use_container_width=True)
                
                # 1.5 Flash 존재 여부 확인
                flash_exists = any('1.5-flash' in m['name'] for m in models)
                if flash_exists:
                    st.info("✨ **희소식:** 목록에 '1.5-flash'가 있습니다! 이름만 정확히 맞추면 됩니다.")
                else:
                    st.error("😱 **충격:** 목록 조회가 됐는데 '1.5-flash'가 없습니다. 계정/지역 문제입니다.")
            else:
                st.warning("⚠️ 조회는 됐으나 'models' 목록이 비어있습니다. (텅 빈 프로젝트)")
                st.json(data)
        else:
            st.error("❌ 조회 실패. 구글이 보낸 에러 메시지:")
            st.json(response.json())
            
    except Exception as e:
        st.error(f"통신 에러: {e}")

    # 2. 강제 호출 테스트 (1.5 Flash)
    st.write("---")
    st.subheader("🧪 2. 'gemini-1.5-flash' 강제 호출 테스트")
    
    url_generate = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": "Hello"}]}]}
    
    try:
        resp = requests.post(url_generate, headers=headers, json=data, timeout=10)
        st.write(f"**호출 결과 (Status {resp.status_code}):**")
        if resp.status_code == 200:
            st.success("🎉 **성공!** 모델이 정상 작동합니다.")
            st.write(resp.json()['candidates'][0]['content']['parts'][0]['text'])
        else:
            st.error("🔥 **실패.** 상세 원인:")
            st.json(resp.json()) # 에러의 속살을 낱낱이 보여줌
            
    except Exception as e:
        st.error(f"호출 중 에러: {e}")

if st.button("🚀 진단 시작", type="primary"):
    diagnose_key(FIXED_API_KEY)
