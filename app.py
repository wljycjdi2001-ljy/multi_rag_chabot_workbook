# 현재 노트북 커널에 설치합니다. Windows에서도 한 줄로 실행됩니다.
%pip install -q langchain langchain-openai langchain-community langchain-text-splitters langgraph pypdf pdfplumber faiss-cpu grandalf
print("✅ 설치 완료")


# 📌 [그대로 실행] OpenAI 키 등록 — VS Code / Jupyter
# 기존 환경 변수의 키를 사용하고, 없으면 화면에 표시되지 않게 입력받습니다.
import os
from getpass import getpass

api_key = os.environ.get("OPENAI_API_KEY", "").strip()
if not api_key or api_key == "sk-여기에-키-입력":
    api_key = getpass("OpenAI API 키 입력 (화면에 표시되지 않음): ").strip()
if not api_key:
    raise ValueError("OpenAI API 키가 비어 있습니다. 이 셀을 다시 실행해 입력하세요.")

os.environ["OPENAI_API_KEY"] = api_key
del api_key
print("✅ 키 준비됨")

