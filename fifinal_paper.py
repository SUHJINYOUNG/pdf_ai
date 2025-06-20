import streamlit as st
import zipfile
import os
import tempfile
from PyPDF2 import PdfReader
import google.generativeai as genai

# Gemini API 설정
genai.configure(api_key="AIzaSyCN9aElRlN1VoATgzoo6Spx2RPsp67nEbc")
model = genai.GenerativeModel("gemini-1.5-flash")

st.set_page_config(page_title="PDF Chat 분석기", layout="wide")

st.title("📦 ZIP 기반 PDF Chat 분석 시스템")

# 세션 스테이트에 chat_history 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list of dicts: {"role": "user"/"assistant", "text": ...}

uploaded_zip = st.file_uploader("PDF 파일들이 들어있는 ZIP 파일을 업로드하세요", type=["zip"])
question = st.text_input("AI에게 물어볼 질문을 입력하세요:")

def extract_text_from_pdf(path):
    reader = PdfReader(path)
    texts = []
    for page in reader.pages:
        try:
            texts.append(page.extract_text() or "")
        except:
            continue
    return "\n".join(texts)

# 메인 버튼
if st.button("질문하기"):
    if not uploaded_zip:
        st.warning("ZIP 파일을 업로드해주세요.")
    elif not question:
        st.warning("질문을 입력해주세요.")
    else:
        with st.spinner("AI가 답변을 생성 중입니다…"):
            try:
                # 1) ZIP에서 PDF 텍스트 추출
                context_list = []
                with tempfile.TemporaryDirectory() as tmpdir:
                    with zipfile.ZipFile(uploaded_zip, "r") as zf:
                        zf.extractall(tmpdir)

                    for fname in sorted(os.listdir(tmpdir)):
                        if not fname.lower().endswith(".pdf"):
                            continue
                        path = os.path.join(tmpdir, fname)
                        text = extract_text_from_pdf(path).strip()
                        if not text:
                            snippet = f"📄 {fname}: (텍스트 추출 실패 또는 빈 문서)"
                        else:
                            # 너무 길면 앞/뒤 1,000자만
                            if len(text) > 2000:
                                snippet = (
                                    f"📄 {fname}\n"
                                    + text[:1000]
                                    + "\n\n...[중략]...\n\n"
                                    + text[-1000:]
                                )
                            else:
                                snippet = f"📄 {fname}\n{text}"
                        context_list.append(snippet)

                full_context = "\n\n---\n\n".join(context_list)

                # 2) Gemini 호출
                prompt = f"""
아래는 ZIP에 포함된 여러 PDF 문서에서 추출한 텍스트입니다. 이 내용을 바탕으로 아래 질문에 답해주세요.

{full_context}

[질문]
{question}
"""
                response = model.generate_content(prompt)

                # 3) 세션에 기록
                st.session_state.chat_history.append({"role": "user", "text": question})
                st.session_state.chat_history.append({"role": "assistant", "text": response.text})

            except Exception as e:
                st.error(f"❗ 오류 발생: {e}")

# 4) 채팅 히스토리 렌더링
for msg in st.session_state.chat_history:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["text"])
    else:
        st.chat_message("assistant").write(msg["text"])
