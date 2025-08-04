import streamlit as st
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from ai_analyzer import analyze_competency_gemini
import PyPDF2 # PDF 파싱
from pptx import Presentation # PPTX 파싱
import io

# --- 파일 파싱 함수 ---
def parse_files(uploaded_files):
    """
    업로드된 파일 리스트를 받아 각 파일의 텍스트를 추출하고 합칩니다.
    """
    all_text = ""
    for file in uploaded_files:
        try:
            # 파일 확장자를 소문자로 변환하여 확인
            file_extension = file.name.split('.')[-1].lower()

            if file_extension == "pdf":
                # PDF 파일 읽기
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.getvalue()))
                for page in pdf_reader.pages:
                    all_text += page.extract_text() + "\n"
                st.write(f"📄 '{file.name}' (PDF) 파일 분석 완료!")

            elif file_extension == "pptx":
                # PPTX 파일 읽기
                presentation = Presentation(io.BytesIO(file.getvalue()))
                for slide in presentation.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "text"):
                            all_text += shape.text + "\n"
                st.write(f"🖥️ '{file.name}' (PPTX) 파일 분석 완료!")
            
            else:
                # 기타 텍스트 파일 (txt, md 등)
                all_text += file.getvalue().decode("utf-8") + "\n"
                st.write(f"📝 '{file.name}' (텍스트) 파일 분석 완료!")

        except Exception as e:
            st.error(f"'{file.name}' 파일 처리 중 오류 발생: {e}")
    return all_text


# --- Streamlit UI 구성 ---
st.set_page_config(layout="wide", page_title="JOJUN")
st.title("🎯 JOJUN: AI 직무 역량 조준기 (파일 분석 ver.)")
st.write("채용 공고와 당신의 포트폴리오(PDF, PPTX)를 AI가 직접 분석하고 합격을 조준합니다.")

col1, col2 = st.columns(2)

with col1:
    st.header("📄 채용 공고 (Job Description)")
    url_input = st.text_input("채용 공고 URL을 붙여넣으세요.")
    # URL 입력 시 내용을 담을 변수
    job_description_from_url = ""
    if url_input:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url_input, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            job_description_from_url = soup.find('body').get_text(separator='\n', strip=True)
        except Exception as e:
            st.error(f"URL을 처리하는 중 오류가 발생했습니다: {e}")
            
    job_description_text = st.text_area("공고 내용", value=job_description_from_url, height=415)


with col2:
    st.header("🧑‍💻 나의 경험 (포트폴리오 파일 업로드)")
    # 파일 업로더로 변경! 여러 파일 업로드 허용
    uploaded_files = st.file_uploader(
        "PDF, PPTX 등 포트폴리오 파일을 업로드하세요.",
        type=["pdf", "pptx", "txt", "md"],
        accept_multiple_files=True
    )

# --- 분석 실행 ---
if st.button("✨ AI로 합격률 조준하기", type="primary", use_container_width=True):
    if not job_description_text:
        st.warning("채용 공고 내용을 입력하거나 URL을 통해 가져와주세요.")
    elif not uploaded_files:
        st.warning("분석할 포트폴리오 파일을 1개 이상 업로드해주세요.")
    else:
        # 파일 파싱
        with st.spinner("업로드된 파일을 분석하고 텍스트를 추출하는 중..."):
            my_experience_text = parse_files(uploaded_files)

        if my_experience_text:
            st.success("파일 분석 완료! 이제 Gemini AI가 역량을 분석합니다.")
            with st.spinner("AI 'JOJUN'이 당신의 역량을 분석 중입니다..."):
                analysis_data = analyze_competency_gemini(job_description_text, my_experience_text)

            if analysis_data:
                st.success("AI 분석 완료! 합격 포인트를 확인하세요.")
                categories = analysis_data['categories']
                job_scores = analysis_data['job_scores']
                user_scores = analysis_data['user_scores']

                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(r=job_scores, theta=categories, fill='toself', name='요구 역량 (JD)', line_color='royalblue'))
                fig.add_trace(go.Scatterpolar(r=user_scores, theta=categories, fill='toself', name='보유 역량 (나)', line_color='orange'))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True, title="직무 역량 적합도 분석 결과", font=dict(size=14))
                st.plotly_chart(fig, use_container_width=True)