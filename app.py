
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

# ✍️ [빈칸 채우기] 가장 단순한 RAG — 검색 → 생성
def simple_rag(question):
    # (1) 질문으로 관련 조문 검색 — 힌트: retriever.invoke(question)
    docs = retriever.invoke(question)
    context = "\n\n".join(
        f"[{d.metadata['조']}({d.metadata['제목']})] {d.page_content}"
        for d in docs)
    # (2) 검색 결과 근거로 답변 — 힌트: llm.invoke(...).content
    answer = llm.invoke(
        f"소득세법 안내입니다. 아래 [자료]만 근거로 답하고, "
        f"없으면 '자료에서 확인되지 않습니다'라고 하세요.\n\n"
        f"[자료]\n{context}\n\n질문: {question}"
    ).content
    return answer

print("🙋 소득세법의 목적은?")
print("🤖", simple_rag("소득세법의 목적은 무엇인가요?"))

print("① 잡담:")
print("🙋 안녕하세요")
print("🤖", simple_rag("안녕하세요"), "\n")

print("② 계산:")
print("🙋 과세표준 2000만원이면 6% 세율로 세금은?")
print("🤖", simple_rag("과세표준 2000만원이면 6% 세율로 세금은 얼마야?"), "\n")

print("③ 법령:")
print("🙋 기본공제 금액은?")
print("🤖", simple_rag("기본공제는 1인당 얼마인가요?"))