import streamlit as st
from google import genai
import json

# genai.Client()는 자동으로 GOOGLE_API_KEY 환경 변수를 찾아 클라이언트를 설정합니다.
# Streamlit Secrets에 GOOGLE_API_KEY가 설정되어 있다면 그 값을 사용합니다.
try:
    client = genai.Client()
except Exception:
    st.warning("Google API 키가 설정되지 않았습니다. 로컬 테스트 시에는 환경 변수로, 배포 시에는 Streamlit Secrets에 추가해야 합니다.")
    client = None

def analyze_competency_gemini(job_description, user_experience):
    """
    최신 Gemini Client를 사용하여 JD와 사용자 경험을 분석하고,
    동적 역량 지표와 점수를 JSON 형태로 반환합니다.
    """
    if not client:
        st.error("Gemini API 클라이언트가 초기화되지 않았습니다. API 키 설정을 확인하세요.")
        return None

    # 제미나이에게 보낼 프롬프트
    prompt = f"""
    당신은 최고의 IT 채용 전문가 AI, 'JOJUN'입니다. [채용 공고]와 [지원자 경험]을 분석하여 다음 과업을 수행해주세요.

    [과업]
    1. [채용 공고] 내용만을 바탕으로, 이 직무에서 가장 중요하게 요구되는 핵심 역량 5가지를 동적으로 선정합니다.
    2. 선정된 5개 역량에 대해, [채용 공고]가 요구하는 수준을 1점에서 100점 사이로 평가합니다.
    3. 선정된 5개 역량에 대해, [지원자 경험]이 얼마나 부합하는지를 1점에서 100점 사이로 평가합니다.

    [채용 공고]
    {job_description}

    [지원자 경험]
    {user_experience}

    [출력 형식]
    반드시 아래와 같은 JSON 형식으로만 응답해주세요. 다른 설명은 일체 포함하지 마세요.
    {{
        "categories": ["역량1", "역량2", "역량3", "역량4", "역량5"],
        "job_scores": [점수1, 점수2, 점수3, 점수4, 점수5],
        "user_scores": [점수1, 점수2, 점수3, 점수4, 점수5]
    }}
    """
    try:
        # API 호출 (최신 방식)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            generation_config={
                "response_mime_type": "application/json"
            }
        )
        
        # JSON 응답을 파싱하여 반환
        analysis_result = json.loads(response.text)
        return analysis_result

    except Exception as e:
        st.error(f"AI 분석 중 오류 발생: {e}")
        return None