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

# --- AI 이력서 제안 함수 ---
def get_resume_suggestions(job_description, user_experience):
    client = get_gemini_client()
    if not client:
        return None

    prompt = f"""
    당신은 최고의 커리어 코치 AI 'JOJUN'입니다. [채용 공고]와 [지원자 경험]을 바탕으로, 지원자가 자신의 강점을 더 잘 어필하고 부족한 점을 보완할 수 있도록 이력서 문구를 3가지 구체적으로 제안해주세요.
    각 제안은 '###'로 시작해야 합니다. 각 제안은 (1) 어떤 역량을 타겟하는지 '타겟 역량', (2) 기존 경험을 어떻게 개선할지 '개선 방안', (3) 실제 이력서에 쓸 수 있는 '예시 문구'를 포함해야 합니다.
    
    [채용 공고]
    {job_description}

    [지원자 경험]
    {user_experience}

    [출력 형식]
    ### 타겟 역량: [분석된 역량]
    **개선 방안:** [기존 경험을 어떻게 구체화하고, 어떤 성과를 강조해야 하는지에 대한 설명]
    **예시 문구:** "[실제 이력서에 추가할 수 있는, 수치화된 성과가 포함된 문장]"
    
    ### 타겟 역량: [분석된 역량]
    **개선 방안:** [설명]
    **예시 문구:** "[예시]"
    
    ### 타겟 역량: [분석된 역량]
    **개선 방안:** [설명]
    **예시 문구:** "[예시]"
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        logging.error(f"AI 이력서 제안 생성 오류: {e}")
        st.error(f"AI 이력서 제안 생성 중 오류가 발생했습니다: {e}")
        return "이력서 제안을 생성하는 데 실패했습니다."

# --- AI 예상 면접 질문 생성 함수 ---
def get_interview_questions(job_description, user_experience):
    client = get_gemini_client()
    if not client:
        return None

    prompt = f"""
    당신은 최고의 IT 전문 면접관 AI 'JOJUN'입니다. [채용 공고]와 [지원자 경험]을 종합적으로 분석하여, 면접에서 나올 법한 예상 질문 5개를 생성해주세요.
    - 3개는 지원자의 핵심 강점과 경험을 깊이 있게 확인하는 질문이어야 합니다.
    - 2개는 채용 공고의 요구사항에 비해 지원자의 경험이 다소 부족해 보이는 부분을 검증하는 압박 질문이어야 합니다.
    각 질문은 '###'로 시작하고, 질문 뒤에는 어떤 의도로 질문했는지 1문장으로 '질문 의도'를 포함해야 합니다.

    [채용 공고]
    {job_description}

    [지원자 경험]
    {user_experience}

    [출력 형식]
    ### [1. 강점 확인 질문]
    **질문 의도:** [이 질문을 통해 무엇을 확인하고 싶은지에 대한 설명]

    ### [2. 강점 확인 질문]
    **질문 의도:** [설명]

    ### [3. 강점 확인 질문]
    **질문 의도:** [설명]

    ### [4. 약점/경험 검증 질문]
    **질문 의도:** [설명]

    ### [5. 약점/경험 검증 질문]
    **질문 의도:** [설명]
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        logging.error(f"AI 면접 질문 생성 오류: {e}")
        st.error(f"AI 면접 질문 생성 중 오류가 발생했습니다: {e}")
        return "면접 질문을 생성하는 데 실패했습니다."

# --- 전체 분석 실행 함수 ---
def run_full_analysis(job_description, user_experience):
    client = get_gemini_client()
    if not client:
        return None

    # 1. 역량 분석
    competency_prompt = f"""
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
    **절대로 다른 설명 없이, 반드시 아래와 같은 JSON 형식으로만 응답해야 합니다.**
    {{
        "categories": ["역량1", "역량2", "역량3", "역량4", "역량5"],
        "job_scores": [점수1, 점수2, 점수3, 점수4, 점수5],
        "user_scores": [점수1, 점수2, 점수3, 점수4, 점수5],
        "fit_score": 88,
        "overall_comment": "지원자는 AI 개발 및 활용에 대한 깊은 이해와 실제 프로젝트 경험을 보유하고 있으며, 이는 채용 공고의 핵심 요구사항에 완벽하게 부합하는 강점입니다. 다만, 특정 기술 스택에 대한 경험이 명확히 드러나지 않는 점은 개선점으로 보입니다."
    }}
    """
    try:
        competency_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=competency_prompt,
            config={"response_mime_type": "application/json"}
        )
        analysis_result = json.loads(competency_response.text)
        
        required_keys = ["categories", "job_scores", "user_scores", "fit_score", "overall_comment"]
        if not all(key in analysis_result for key in required_keys):
            st.error("AI 역량 분석 응답이 불완전합니다. 다시 시도해주세요.")
            logging.warning(f"Incomplete JSON from competency analysis: {analysis_result}")
            return None

        # 2. 이력서 제안 생성
        suggestions = get_resume_suggestions(job_description, user_experience)
        analysis_result['suggestions'] = suggestions

        # 3. 예상 면접 질문 생성
        interview_questions = get_interview_questions(job_description, user_experience)
        analysis_result['interview_questions'] = interview_questions
            
        return analysis_result

    except Exception as e:
        logging.error(f"AI 전체 분석 오류: {e}")
        st.error(f"AI 분석 중 오류가 발생했습니다: {e}")
        return None
