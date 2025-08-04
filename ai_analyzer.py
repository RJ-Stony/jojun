import streamlit as st
from google import genai
import os
import json
from PIL import Image
import io

# --- 클라이언트 초기화 ---
# 라이브러리가 자동으로 GOOGLE_API_KEY 환경 변수를 찾아 사용합니다.
try:
    client = genai.Client()
except Exception as e:
    st.error("Google API 키를 사용하여 Gemini 클라이언트를 초기화하는 데 실패했습니다.")
    st.error(f"오류 상세: {e}")
    client = None

# --- Gemini Vision OCR 함수 ---
def ocr_with_gemini(image_bytes):
    if not client:
        return None
    
    try:
        img = Image.open(io.BytesIO(image_bytes))
        prompt = "Extract all text from this image. Provide only the transcribed text, without any additional commentary or formatting."
        
        # client.models.generate_content 사용
        response = client.models.generate_content(
            model="gemini-2.5-flash", # Vision 기능에 flash 모델 사용
            contents=[prompt, img]
        )
        return response.text
    except Exception as e:
        st.error(f"Gemini Vision API 호출 중 오류 발생: {e}")
        return None

# --- 역량 분석 함수 ---
def analyze_competency_gemini(job_description, user_experience):
    if not client:
        return None

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
        # client.models.generate_content 사용
        response = client.models.generate_content(
            model="gemini-2.5-pro", # 역량 분석에 pro 모델 사용
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )
        analysis_result = json.loads(response.text)
        return analysis_result
    except Exception as e:
        st.error(f"AI 분석 중 오류 발생: {e}")
        return None