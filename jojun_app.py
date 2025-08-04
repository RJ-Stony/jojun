import streamlit as st
from dotenv import load_dotenv

load_dotenv()

import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from ai_analyzer import analyze_competency_gemini, ocr_with_gemini
import PyPDF2
from pptx import Presentation
import io
from PIL import Image
import json
import os
from streamlit.errors import StreamlitSecretNotFoundError
from streamlit_paste_button import paste_image_button

# --- 함수 정의 ---
def parse_input_files(uploaded_files):
    all_text = ""
    if not uploaded_files:
        return all_text
    for file in uploaded_files:
        try:
            file_extension = file.name.split('.')[-1].lower()
            file_bytes = file.getvalue()
            if file_extension == "pdf":
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
                for page in pdf_reader.pages:
                    all_text += page.extract_text() + "\n"
                st.write(f"✓ '{file.name}' (PDF) 분석 완료!")
            elif file_extension == "pptx":
                presentation = Presentation(io.BytesIO(file_bytes))
                for slide in presentation.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "text"):
                            all_text += shape.text + "\n"
                st.write(f"✓ '{file.name}' (PPTX) 분석 완료!")
            elif file_extension in ["jpg", "jpeg", "png"]:
                with st.spinner(f"'{file.name}' 이미지 텍스트 분석 중..."):
                    ocr_text = ocr_with_gemini(file_bytes)
                if ocr_text:
                    all_text += ocr_text + "\n"
                    st.write(f"✓ '{file.name}' (이미지) 분석 완료!")
                else:
                    st.warning(f"'{file.name}'에서 텍스트를 찾지 못했습니다.")
            else: # txt, md 등
                all_text += file_bytes.decode("utf-8", errors='ignore') + "\n"
                st.write(f"✓ '{file.name}' (텍스트) 파일 분석 완료!")
        except Exception as e:
            st.error(f"'{file.name}' 파일 처리 중 오류 발생: {e}")
    return all_text

# --- Streamlit UI 구성 ---
st.set_page_config(layout="wide", page_title="JOJUN")
st.title("🎯 JOJUN: AI 직무 역량 조준기")
st.write("채용 공고와 당신의 경험을 모든 방식으로 분석하여 합격을 조준합니다.")

try:
    _ = st.secrets["GOOGLE_API_KEY"]
    google_api_key_exists = True
except (StreamlitSecretNotFoundError, KeyError):
    # 로컬 환경: .env에서 로드된 환경 변수에 키가 있는지 확인
    google_api_key_exists = "GOOGLE_API_KEY" in os.environ

# session_state 초기화
if 'jd_text' not in st.session_state:
    st.session_state.jd_text = ""
if 'my_exp_text' not in st.session_state:
    st.session_state.my_exp_text = ""
if 'last_pasted_image_data' not in st.session_state:
    st.session_state.last_pasted_image_data = None

col1, col2 = st.columns(2)

with col1:
    st.header("📄 채용 공고")
    url_input = st.text_input("채용 공고 URL을 붙여넣어주세요.")
    if url_input:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url_input, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            st.session_state.jd_text = soup.find('body').get_text(separator='\n', strip=True)
            st.info("URL 내용을 가져왔습니다. 아래 텍스트 박스를 확인하세요.")
        except Exception as e:
            st.error(f"URL 처리 중 오류가 발생했습니다: {e}")

    st.write("혹은 클립보드의 이미지를 바로 붙여넣어주세요.")
    paste_result = paste_image_button("📋 클릭해서 이미지 붙여넣기", key="paste_button")
    
    if paste_result.image_data is not None and paste_result.image_data != st.session_state.last_pasted_image_data:
        st.session_state.last_pasted_image_data = paste_result.image_data
        img_bytes_io = io.BytesIO()
        paste_result.image_data.save(img_bytes_io, format="PNG")
        image_bytes_for_api = img_bytes_io.getvalue()
        with st.spinner("붙여넣은 이미지의 텍스트를 분석 중..."):
            ocr_text_from_paste = ocr_with_gemini(image_bytes_for_api)
        if ocr_text_from_paste:
            st.session_state.jd_text += "\n" + ocr_text_from_paste
            st.info("이미지 텍스트가 아래 텍스트 박스에 추가되었습니다.")
        st.rerun()

    st.text_area("공고 내용 확인 및 직접 수정", key="jd_text", height=250)
    jd_files = st.file_uploader(
        "혹은 공고 파일을 직접 업로드해주세요.",
        type=["pdf", "pptx", "txt", "md", "jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="jd_uploader"
    )

with col2:
    st.header("🧑‍💻 나의 경험")
    st.text_area("경험/이력 내용을 직접 붙여넣어주세요.", key="my_exp_text", height=415)
    my_files = st.file_uploader(
        "혹은 포트폴리오 파일을 직접 업로드해주세요.",
        type=["pdf", "pptx", "txt", "md"],
        accept_multiple_files=True,
        key="my_files_uploader"
    )

if st.button("✨ AI로 합격률 조준하기", type="primary", use_container_width=True):
    if not google_api_key_exists:
        st.error("Google API 키가 설정되지 않았습니다. .env 파일 또는 Streamlit Secrets에 추가해주세요.")
    else:
        # 각 영역의 최종 텍스트 조합
        final_jd_text = st.session_state.jd_text
        if st.session_state.jd_uploader:
            final_jd_text += "\n" + parse_input_files(st.session_state.jd_uploader)

        final_my_experience_text = st.session_state.my_exp_text
        if st.session_state.my_files_uploader:
            final_my_experience_text += "\n" + parse_input_files(st.session_state.my_files_uploader)

        if not final_jd_text.strip() or not final_my_experience_text.strip():
            st.warning("채용 공고와 나의 경험을 모두 입력(또는 업로드)해주세요.")
        else:
            with st.spinner("AI 'JOJUN'이 당신의 역량을 분석 중입니다..."):
                analysis_data = analyze_competency_gemini(final_jd_text, final_my_experience_text)

            if analysis_data:
                st.success("분석 완료! 합격 포인트를 확인하세요.")
                categories = analysis_data['categories']
                job_scores = analysis_data['job_scores']
                user_scores = analysis_data['user_scores']
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(r=job_scores, theta=categories, fill='toself', name='요구 역량 (JD)', line_color='royalblue'))
                fig.add_trace(go.Scatterpolar(r=user_scores, theta=categories, fill='toself', name='보유 역량 (나)', line_color='orange'))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True, title="직무 역량 적합도 분석 결과", font=dict(size=14))
                st.plotly_chart(fig, use_container_width=True)