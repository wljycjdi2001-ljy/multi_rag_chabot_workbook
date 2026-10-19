
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



PDF = r"c:\workspaces\RAG\소득세법_실습데이터.pdf"

print(f"✅ 업로드: {PDF}")

# ✍️ [빈칸 채우기] PDF 텍스트 추출 + 본문 시작점 찾기
import pypdf, re

reader = pypdf.PdfReader(PDF)
# (1) 모든 페이지 텍스트 추출 — 힌트: 페이지의 .extract_text()

pages = [(p.extract_text() or "") for p in reader.pages]
full = "\n".join(pages)

print(len(pages))
print(len(full))

# (2) 본문 시작 = "제1조(목적)" 위치 (앞 목차 건너뛰기)
#     힌트: 정규식 패턴 "제1\\s?조\\(목적\\)"
m = re.search(r"제1조(목적)", full)
body = full[m.start():] if m else full

print(f"✅ {len(reader.pages)}페이지에서 {len(body):,}자 추출")
print(body[:150])

# ✍️ [빈칸 채우기] 본문을 "제○조" 단위 분할 + 메타데이터
from langchain_core.documents import Document

pat = re.compile(r"(제\s?\d+\s?조(?:\s?의\s?\d+)?)\s*\(\s*([^)]+?)\s*\)")
matches = list(pat.finditer(body))

docs = []
for i, mt in enumerate(matches):
    jo = re.sub(r"\s+", "", mt.group(1))      # 제50조
    title = re.sub(r"\s+", "", mt.group(2))   # 기본공제
    start = mt.start()
    end = matches[i+1].start() if i+1 < len(matches) else len(body)
    content = body[start:end].strip()
    if len(content) < 15:       # 짧으면 목차 → 제외
        continue
    # Document 만들기 — 힌트: page_content=본문[:1500],
    #   metadata={"조": jo, "제목": title}
    docs.append(Document(
        page_content=content[:1500],
        metadata={"조": jo, "제목": title}))

print(f"✅ 조문 {len(docs)}개로 분할")
print(f"예시: {docs[0].metadata}")


###### 