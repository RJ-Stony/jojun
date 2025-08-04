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

# --- 역량 분석 함수 (프롬프트 안정성 강화) ---
def analyze_competency_gemini(job_description, user_experience):    
    client = get_gemini_client()
    if not client:  
        return None

    prompt = f"""
    당신은 최고의 IT 채용 전문가 AI, 'JOJUN'입니다. [채용 공고]와 [지원자 경험]을 분석하여 다음 과업을 명확하고 객관적으로 수행해주세요.

    [과업]
    1. **핵심 역량 5가지 선정**: [채용 공고] 내용만을 바탕으로, 이 직무에서 가장 중요하게 요구되는 핵심 역량 5가지를 동적으로 선정합니다.
    2. **요구/보유 역량 수준 평가**: 선정된 5개 역량 각각에 대해, [채용 공고]가 요구하는 수준과 [지원자 경험]이 보유한 수준을 1점에서 100점 사이로 평가합니다.
    3. **종합 분석 (필수)**: 모든 분석을 종합하여, 지원자의 '종합 직무 적합도 점수(fit_score)'를 1점에서 100점 사이로 반드시 평가해야 합니다. 또한, 지원자의 강점과 개선점을 요약한 '종합 코멘트(overall_comment)'를 2~3 문장으로 반드시 작성해야 합니다.

    [채용 공고]
    {job_description}

    [지원자 경험]
    {user_experience}

    [출력 형식]
    **절대로 다른 설명 없이, 반드시 아래와 같은 JSON 형식으로만 응답해야 합니다. 'fit_score'와 'overall_comment' 필드는 필수 항목입니다.**
    {{
        "categories": ["역량1", "역량2", "역량3", "역량4", "역량5"],
        "job_scores": [점수1, 점수2, 점수3, 점수4, 점수5],
        "user_scores": [점수1, 점수2, 점수3, 점수4, 점수5],
        "fit_score": 88,
        "overall_comment": "지원자는 AI 개발 및 활용에 대한 깊은 이해와 실제 프로젝트 경험을 보유하고 있으며, 이는 채용 공고의 핵심 요구사항에 완벽하게 부합하는 강점입니다. 다만, 특정 기술 스택에 대한 경험이 명확히 드러나지 않는 점은 개선점으로 보입니다."
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
            st.error("AI 응답이 불완전합니다. 입력 내용 길이를 조절하거나 잠시 후 다시 시도해주세요.")
            logging.warning(f"Incomplete JSON response from AI: {analysis_result}")
            return None
            
        return analysis_result
    except Exception as e:
        logging.error(f"AI 역량 분석 오류: {e}")
        st.error(f"AI 역량 분석 중 오류가 발생했습니다: {e}")
        return None