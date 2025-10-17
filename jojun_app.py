import streamlit as st
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from ai_analyzer import run_full_analysis, ocr_with_gemini
import PyPDF2
from pptx import Presentation
import io
import os
import re
from streamlit.errors import StreamlitSecretNotFoundError
from streamlit_paste_button import paste_image_button

# --- 페이지 설정 및 환경 구성 ---
st.set_page_config(layout="wide", page_title="JOJUN - AI 직무 역량 조준기", initial_sidebar_state="expanded")

# .env 파일 로드 (로컬 개발 환경용)
load_dotenv()

# API 키 확인 (앱 시작 시)
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except (StreamlitSecretNotFoundError, KeyError):
    api_key = os.environ.get("GOOGLE_API_KEY")

if not api_key:
    st.error("🚨 Google API 키가 설정되지 않았습니다!")
    st.info("로컬에서 실행하는 경우, .env 파일에 `GOOGLE_API_KEY=여러분의API키` 형식으로 키를 추가해주세요.")
    st.info("Streamlit Cloud에 배포하는 경우, Secrets에 `GOOGLE_API_KEY`를 설정해야 합니다.")
    st.stop()

# --- 스타일링 ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700&display=swap');
    .stApp { font-family: 'Pretendard', sans-serif; }
    div[data-testid="stAppViewContainer"] > .main .block-container { max-width: 100%; }
    .stButton>button { font-family: 'Pretendard', sans-serif; font-weight: 700; font-size: 16px; color: white; background-color: #4A4A4A; border: none; border-radius: 10px; padding: 12px 0; transition: all 0.2s ease-in-out; }
    .stButton>button:hover { background-color: #2a2a2a; transform: scale(1.02); }
    .stButton>button:active { background-color: #1a1a1a !important; transform: scale(0.98) !important; color: white !important; }
    .kpi-card { background-color: #FFFFFF; border-left: 5px solid #4A4A4A; color: #333; border-radius: 10px; padding: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 10px; height: 180px; display: flex; flex-direction: column; justify-content: space-between; }
    .kpi-title { font-size: 1.1rem; font-weight: 700; margin-bottom: 15px; }
    .kpi-scores { display: flex; justify-content: space-between; align-items: center; }
    .kpi-score-box { text-align: center; }
    .kpi-score-label { font-size: 0.8rem; }
    .kpi-score-value { font-size: 1.8rem; font-weight: 700; }
    .kpi-delta { text-align: center; font-size: 1.2rem; font-weight: 700; }
    .delta-positive { color: #28a745 !important; }
    .delta-negative { color: #dc3545 !important; }
    .delta-zero { color: #6c757d !important; }
    .ai-comment-card { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 10px; padding: 25px; margin-top: 5px; }
    .ai-comment-title { font-size: 1.2rem; font-weight: 700; margin-bottom: 10px; color: #4A4A4A; }
    .ai-comment-body { font-size: 1rem; line-height: 1.6; color: #343a40; }
    [data-theme="dark"] .kpi-card, [data-theme="dark"] .ai-comment-card { background-color: #262730; border-color: #444; }
    [data-theme="dark"] .kpi-title, [data-theme="dark"] .kpi-score-value, [data-theme="dark"] .ai-comment-title, [data-theme="dark"] .ai-comment-body { color: #FAFAFA; }
    [data-theme="dark"] .kpi-score-label { color: #A0A0A0; }
</style>
""", unsafe_allow_html=True)

# --- 유틸리티 함수 ---
def parse_and_display_suggestions(text):
    # ###로 시작하는 각 제안 블록을 찾습니다.
    for match in re.finditer(r"###\s*(.*?)(?=###|$)", text, re.DOTALL):
        suggestion = match.group(1).strip()
        if not suggestion: continue
        try:
            title_match = re.search(r"타겟 역량:\s*(.*)", suggestion)
            title = title_match.group(1).strip() if title_match else "AI 제안"
            
            guidance_match = re.search(r"\*\*개선 방안:\*\*\s*([\s\S]*?)(?=\n\*\*예시 문구:|$)", suggestion)
            guidance = guidance_match.group(1).strip() if guidance_match else "내용 없음"

            example_match = re.search(r"\*\*예시 문구:\*\*\s*(.*)", suggestion, re.DOTALL)
            example = example_match.group(1).strip().replace('"', '') if example_match else "내용 없음"

            with st.expander(f"🎯 **{title}** 역량 강화하기"):
                st.markdown("##### 💡 개선 방안")
                st.info(guidance)
                st.markdown("##### ✍️ 추천 예시 문구")
                st.code(example, language='text')
        except (IndexError, AttributeError) as e:
            st.warning(f"AI 제안을 표시하는 중 일부 내용에 오류가 있었습니다: {e}")
            st.text(suggestion)

def parse_and_display_questions(text):
    # ###로 시작하는 각 질문 블록을 찾습니다.
    for i, match in enumerate(re.finditer(r"###\s*(.*?)(?=###|$)", text, re.DOTALL)):
        question_block = match.group(1).strip()
        if not question_block: continue
        try:
            # 질문과 의도를 분리합니다.
            parts = question_block.split("**질문 의도:**")
            question = parts[0].strip()
            intent = parts[1].strip() if len(parts) > 1 else "의도 파악 불가"

            with st.expander(f"**질문 {i+1}:** {question}"):
                st.markdown(f"**🔍 질문 의도:** {intent}")
        except (IndexError, AttributeError) as e:
            st.warning(f"AI 예상 질문을 표시하는 중 일부 내용에 오류가 있었습니다: {e}")
            st.text(question_block)

# --- 파일 처리 및 상태 관리 함수 ---
def _handle_pdf(file_bytes): return "\n".join(page.extract_text() for page in PyPDF2.PdfReader(io.BytesIO(file_bytes)).pages)
def _handle_pptx(file_bytes): 
    text = []
    for slide in Presentation(io.BytesIO(file_bytes)).slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"): text.append(shape.text)
    return "\n".join(text)
def _handle_image(file_bytes, file_name): 
    with st.spinner(f"'{file_name}' 이미지 분석 중..."): return ocr_with_gemini(file_bytes) or ""
def _handle_text(file_bytes): return file_bytes.decode("utf-8", errors='ignore')

def parse_input_files(uploaded_files):
    if not uploaded_files: return ""
    file_handlers = {'pdf': _handle_pdf, 'pptx': _handle_pptx, 'jpg': _handle_image, 'jpeg': _handle_image, 'png': _handle_image, 'txt': _handle_text, 'md': _handle_text}
    all_text = []
    progress_bar = st.sidebar.progress(0)
    for i, file in enumerate(uploaded_files):
        try:
            ext = file.name.split('.')[-1].lower()
            handler = file_handlers.get(ext, _handle_text)
            content = handler(file.getvalue(), file.name) if ext in ['jpg', 'jpeg', 'png'] else handler(file.getvalue())
            all_text.append(content)
        except Exception as e: st.sidebar.error(f"'{file.name}' 처리 오류: {e}")
        finally: progress_bar.progress((i + 1) / len(uploaded_files), f"'{file.name}' 처리 완료!")
    progress_bar.empty()
    st.sidebar.success(f"{len(uploaded_files)}개 파일 분석 완료!")
    return "\n".join(all_text)

def initialize_state():
    if 'app_initialized' not in st.session_state:
        st.session_state.app_initialized = True
        st.session_state.last_pasted_image = None
        st.session_state.jd_text = ""
        st.session_state.my_exp_text = ""
        st.session_state.analysis_data = None
        st.session_state.history = []

initialize_state()

# --- UI --- 
with st.sidebar:
    st.title("🎯 JOJUN")
    st.markdown("AI 직무 역량 조준기")
    st.divider()

    with st.expander("📜 분석 히스토리", expanded=True):
        if not st.session_state.history:
            st.caption("아직 분석 기록이 없습니다.")
        for i, record in enumerate(st.session_state.history):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.info(f"**{record['title']}** (적합도: {record['fit_score']}점)")
            with col2:
                if st.button("👀", key=f"view_{i}", use_container_width=True):
                    st.session_state.analysis_data = record['data']
                    st.rerun()
            with col3:
                if st.button("🗑️", key=f"del_{i}", use_container_width=True):
                    st.session_state.history.pop(i)
                    st.rerun()
    st.divider()

    st.header("1. 채용 공고 입력")
    with st.expander("🔗 URL에서 가져오기", expanded=False):
        url_input = st.text_input("채용 공고 URL", key="url_input")
        if url_input:
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url_input, headers=headers, timeout=5)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                st.session_state.jd_text = soup.find('body').get_text(separator='\n', strip=True)
                st.success("URL 내용을 성공적으로 가져왔습니다.")
            except Exception as e: st.error(f"URL 처리 오류: {e}")

    with st.expander("✍️ 붙여넣기 & 직접 수정", expanded=True):
        paste_result = paste_image_button("📋 클립보드 이미지 붙여넣기", key="paste_button")
        if paste_result.image_data and paste_result.image_data != st.session_state.last_pasted_image:
            st.session_state.last_pasted_image = paste_result.image_data
            with st.spinner("이미지 분석 중..."):
                img_bytes_io = io.BytesIO()
                paste_result.image_data.save(img_bytes_io, format="PNG")
                ocr_text = ocr_with_gemini(img_bytes_io.getvalue())
            if ocr_text:
                st.session_state.jd_text += "\n" + ocr_text
                st.info("이미지 텍스트를 공고 내용에 추가했습니다.")
                st.rerun()
        st.text_area("공고 내용", key="jd_text", height=200)

    with st.expander("📁 파일 업로드", expanded=False):
        jd_files = st.file_uploader("PDF, PPTX, TXT, MD, JPG, PNG", type=["pdf", "pptx", "txt", "md", "jpg", "jpeg", "png"], accept_multiple_files=True, key="jd_uploader")
    
    st.divider()

    st.header("2. 나의 경험 입력")
    with st.expander("✍️ 직접 입력", expanded=True):
        st.text_area("이력서, 포트폴리오 내용", key="my_exp_text", height=200)
    with st.expander("📁 파일 업로드", expanded=False):
        my_files = st.file_uploader("PDF, PPTX, TXT, MD", type=["pdf", "pptx", "txt", "md"], accept_multiple_files=True, key="my_files_uploader")

    st.divider()
    if st.button("✨ AI로 합격률 조준하기", use_container_width=True):
        final_jd_text = st.session_state.jd_text
        if 'jd_files' in locals() and jd_files: final_jd_text += "\n" + parse_input_files(jd_files)
        final_my_exp_text = st.session_state.my_exp_text
        if 'my_files' in locals() and my_files: final_my_exp_text += "\n" + parse_input_files(my_files)

        if not final_jd_text.strip() or not final_my_exp_text.strip():
            st.warning("채용 공고와 나의 경험을 모두 입력(또는 업로드)해주세요.")
            st.session_state.analysis_data = None
        else:
            with st.spinner("AI 'JOJUN'이 당신의 역량을 정밀 분석 중입니다..."):
                analysis_result = run_full_analysis(final_jd_text, final_my_exp_text)
                if analysis_result:
                    st.session_state.analysis_data = analysis_result
                    # 히스토리 저장 (IndexError 방지)
                    title = "새로운 분석" # 기본값
                    if analysis_result.get('categories'):
                        title = f"{analysis_result['categories'][0]} 직무"
                    history_entry = {
                        'title': title,
                        'fit_score': analysis_result.get('fit_score', 0),
                        'data': analysis_result
                    }
                    st.session_state.history.insert(0, history_entry)

st.title("🎯 JOJUN: AI 직무 역량 분석")

if st.session_state.analysis_data:
    analysis_data = st.session_state.analysis_data
    st.success("🎉 분석 완료!") # 타임스탬프 제거

    tab1, tab2, tab3 = st.tabs(["📊 종합 분석", "💡 이력서 코칭", "💬 예상 면접 질문"])

    with tab1:
        st.subheader("🎯 종합 분석")
        col1, col2 = st.columns([1, 2])
        with col1: st.metric(label="직무 적합도", value=f"{analysis_data.get('fit_score', 0)}점"); st.progress(analysis_data.get('fit_score', 0))
        with col2: st.markdown(f"<div class='ai-comment-card'><div class='ai-comment-title'>💡 AI 총평</div><div class='ai-comment-body'>{analysis_data.get('overall_comment', '')}</div></div>", unsafe_allow_html=True)
        st.divider()
        st.subheader("📈 역량 비교 분석")
        categories = analysis_data.get('categories', []); job_scores = analysis_data.get('job_scores', []); user_scores = analysis_data.get('user_scores', [])
        if categories and job_scores and user_scores:
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=job_scores, theta=categories, fill='toself', name='요구 역량 (JD)', line_color='rgba(74, 74, 74, 0.8)', fillcolor='rgba(74, 74, 74, 0.2)'))
            fig.add_trace(go.Scatterpolar(r=user_scores, theta=categories, fill='toself', name='보유 역량 (나)', line_color='rgba(255, 140, 0, 0.8)', fillcolor='rgba(255, 140, 0, 0.2)'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100], showline=False, showticklabels=False, ticks='')), showlegend=True, title=dict(text="<b>역량 적합도 레이더 차트</b>", font=dict(size=20), x=0.5), font=dict(family="Pretendard, sans-serif", size=14), legend=dict(yanchor="top", y=1.1, xanchor="center", x=0.5, orientation="h"), template="plotly_white", margin=dict(t=80, b=20))
            st.plotly_chart(fig, use_container_width=True)
            st.subheader("🔍 역량별 상세 점수")
            cols = st.columns(min(len(categories), 3))
            for i, category in enumerate(categories):
                job_score = job_scores[i]; user_score = user_scores[i]; delta = user_score - job_score
                delta_color, delta_sign = ("positive", "+") if delta > 0 else (("negative", "") if delta < 0 else ("zero", ""))
                with cols[i % min(len(categories), 3)]: st.markdown(f"<div class='kpi-card'><div class='kpi-title'>{category}</div><div class='kpi-scores'><div class='kpi-score-box'><div class='kpi-score-label'>요구 역량</div><div class='kpi-score-value'>{job_score}</div></div><div class='kpi-score-box'><div class='kpi-score-label'>보유 역량</div><div class='kpi-score-value'>{user_score}</div></div><div class='kpi-delta'><div class='kpi-score-label'>차이</div><div class='{delta_color}'>{delta_sign}{delta}</div></div></div></div>", unsafe_allow_html=True)

    with tab2:
        st.subheader("✨ AI 기반 이력서 맞춤 제안")
        suggestions = analysis_data.get('suggestions', "")
        if suggestions: parse_and_display_suggestions(suggestions)
        else: st.info("생성된 이력서 제안이 없습니다.")

    with tab3:
        st.subheader("💬 AI 예상 면접 질문")
        questions = analysis_data.get('interview_questions', "")
        if questions: parse_and_display_questions(questions)
        else: st.info("생성된 예상 면접 질문이 없습니다.")
else:
    st.markdown("### 👋 JOJUN에 오신 것을 환영합니다!")
    st.markdown("JOJUN은 AI를 통해 채용 공고와 당신의 경험을 비교 분석하여, 직무 적합도를 알려주는 스마트한 비서입니다.")
    st.info("**시작하려면, 왼쪽 사이드바에 채용 공고와 자신의 이력서/경험을 입력하고 'AI로 합격률 조준하기' 버튼을 눌러주세요.**")

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 0.8em; color: #888;'>Made with ❤️ by JOJUN</p>", unsafe_allow_html=True)
