import streamlit as st
from google import genai
import os
import json
from PIL import Image
import io
import logging

@st.cache_resource
def get_gemini_client():
    try:
        client = genai.Client()
        return client
    except Exception as e:
        logging.error(f"Gemini 클라이언트 초기화 실패: {e}")
        st.error("AI 서비스를 초기화하는 데 실패했습니다. 관리자에게 문의하세요.")
        return None

# --- Gemini Vision OCR 함수 ---
def ocr_with_gemini(image_bytes):
    client = get_gemini_client()
    if not client:
        return None
    
    try:
        img = Image.open(io.BytesIO(image_bytes))
        prompt = "Extract all text from this image. Provide only the transcribed text, without any additional commentary or formatting."
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, img]
        )
        return response.text
    except Exception as e:
        logging.error(f"Gemini Vision API 호출 오류: {e}")
        st.error("이미지 분석 중 AI 서비스에 오류가 발생했습니다.")
        return None

# --- 역량 분석 함수 (한글 프롬프트 복구) ---
def analyze_competency_gemini(job_description, user_experience):    
    client = get_gemini_client()
    if not client:  
        return None

    prompt = f"""
    당신은 최고의 IT 채용 전문가 AI, 'JOJUN'입니다. [채용 공고]와 [지원자 경험]을 분석하여 다음 과업을 명확하고 객관적으로 수행해주세요.

    [과업]
    1. **핵심 역량 5가지 선정**: [채용 공고] 내용만을 바탕으로, 이 직무에서 가장 중요하게 요구되는 핵심 역량 5가지를 동적으로 선정합니다.
    2. **요구 역량 수준 평가**: 선정된 5개 역량에 대해, [채용 공고]가 요구하는 전문성의 수준을 1점에서 100점 사이로 평가합니다.
    3. **보유 역량 수준 평가**: 선정된 5개 역량에 대해, [지원자 경험]이 얼마나 부합하는지를 1점에서 100점 사이로 평가합니다.
    4. **종합 분석**: 모든 역량을 종합적으로 고려하여, 지원자의 직무 적합도를 1점에서 100점 사이의 '종합 합격률' 점수로 평가하고, 강점과 약점을 포함한 '종합 코멘트'를 2-3문장으로 작성합니다.

    [채용 공고]
    {job_description}

    [지원자 경험]
    {user_experience}

    [출력 형식]
    반드시 아래와 같은 JSON 형식으로만 응답해주세요. 다른 설명은 일체 포함하지 마세요.
    {{
        "categories": ["역량1", "역량2", "역량3", "역량4", "역량5"],
        "job_scores": [점수1, 점수2, 점수3, 점수4, 점수5],
        "user_scores": [점수1, 점수2, 점수3, 점수4, 점수5],
        "fit_score": "종합 합격률 점수",
        "overall_comment": "종합 코멘트 내용"
    }}
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,    
            config={
                "response_mime_type": "application/json"
            }
        )
        analysis_result = json.loads(response.text)
        
        # AI가 불완전한 JSON을 반환할 경우를 대비한 방어 코드
        required_keys = ["categories", "job_scores", "user_scores", "fit_score", "overall_comment"]
        if not all(key in analysis_result for key in required_keys):
            st.error("AI 응답이 불완전합니다. 잠시 후 다시 시도해주세요.")
            return None
            
        return analysis_result
    except Exception as e:
        logging.error(f"AI 역량 분석 오류: {e}")
        st.error(f"AI 역량 분석 중 오류가 발생했습니다: {e}")
        return None