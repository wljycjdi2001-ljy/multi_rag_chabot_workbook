
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


# 임베딩

# 조문 벡터 저장 + 검색기
from langchain_community.vectorstores import FAISS

# (1) docs를 임베딩해 FAISS에
vectordb = FAISS.from_documents(docs, embeddings)

# (2) 검색기, 질문당 3개
retriever = vectordb.as_retriever(search_kwargs={"k": 3})

print("✅ 검색 준비 완료")
print("질문 '기본공제' 검색 결과:")
for d in retriever.invoke("기본공제는 얼마인가요?"):
    print(f"  [{d.metadata['조']} {d.metadata['제목']}]")


import base64
from langchain_core.messages import HumanMessage

# 1) 제55조 세율표가 있는 페이지 자동 탐색
import pdfplumber
rate_page = None
with pdfplumber.open(PDF) as pdf:
    for i, p in enumerate(pdf.pages):
        t = p.extract_text() or ""
        if "제55조(세율)" in t and "종합소득과세표준" in t:
            # 본문 다음 페이지에 표 이미지가 있음
            for cand in (i, i + 1):
                big = [im for im in pdf.pages[cand].images
                       if im["width"] > 200 and im["height"] > 100]
                if big:
                    rate_page = cand
                    break
        if rate_page is not None:
            break

print(f"✅ 세율표 이미지 페이지 발견: p{rate_page}")

# 2) 그 페이지를 고해상도 이미지로 저장
with pdfplumber.open(PDF) as pdf:
    pdf.pages[rate_page].to_image(resolution=300).save("rate_table.png")
print("✅ 세율표 페이지 캡처 완료 (rate_table.png)")


# 비전 모델로 세율표 이미지 → 텍스트(OCR)
# 프롬프트를 "OCR 작업"으로! 세무 단어 많으면 거부됨
with open("rate_table.png", "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode()

# (1) 비전 모델 — "gpt-4o" (mini 아님, 표 정확도)
vision = ChatOpenAI(model="gpt-4o", temperature=0)

vision_msg = HumanMessage(content=[
    {"type": "text", "text":
     "다음 이미지에 표가 하나 있습니다. OCR 작업입니다: "
     "표의 각 행과 열에 적힌 글자·숫자를 보이는 그대로 "
     "마크다운 표로 옮겨 적으세요. 내용을 해석하거나 "
     "조언하지 말고, 표를 그대로 전사(transcribe)만 하세요."},
    # (2) 이미지 전달 — 힌트: f"data:image/png;base64,{img_b64}"
    {"type": "image_url",
     "image_url": {"url": f"data:image/png;base64,{img_b64}",
                   "detail": "high"}},
])
resp = vision.invoke([vision_msg]).content

# 거부 응답 시 영어로 1회 재시도
if "can't assist" in resp.lower() or "sorry" in resp.lower():
    retry_msg = HumanMessage(content=[
        {"type": "text", "text":
         "Transcribe the table in this image into a markdown "
         "table. Copy text and numbers exactly. Plain OCR task."},
        {"type": "image_url",
         "image_url": {"url": f"data:image/png;base64,{img_b64}",
                       "detail": "high"}},
    ])
    resp = vision.invoke([retry_msg]).content

rate_table_text = resp
print("─── 비전 복원: 세율표 ───")
print(rate_table_text)

if "sorry" in rate_table_text.lower() or "can't" in rate_table_text.lower():
    print("\n⚠️ 비전 복원 실패. 셀 재실행 또는 키 권한 확인.")
else:
    print("\n✅ 세율표 복원 성공")


# 복원한 세율표를 벡터DB에 추가
from langchain_core.documents import Document

rate_doc = Document(
    page_content=(f"[소득세법 제55조 종합소득세 세율표 "
                  f"- 이미지에서 비전 복원]\n{rate_table_text}"),
    metadata={"조": "제55조", "제목": "세율"})

# 기존 DB에 '추가'
vectordb.add_documents([rate_doc])
print("✅ 세율표를 벡터DB에 추가 (검색·계산에 활용 가능)")

hit = retriever.invoke("종합소득세 과세표준 세율은 어떻게 되나요?")
print("\n'과세표준 세율' 검색 결과:")
for d in hit[:2]:
    print(f"  [{d.metadata['조']} {d.metadata['제목']}] "
          f"{d.page_content[:50].strip()}...")

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





########################## STEP 5 ###########################

###### 5-1. 계산봇 ######
# ✍️ [빈칸 채우기] 계산봇 — 하드코딩 X, 복원 세율표 근거
#   핵심: 3단계의 rate_table_text 를 프롬프트에 넣기
def calc_bot(question):
    answer = llm.invoke(
        f"당신은 세무 계산기입니다. 아래는 소득세법 제55조 "
        f"실제 세율표입니다 (이미지에서 복원한 정확한 표).\n\n"
        # (1) 복원 세율표 변수 — 힌트: {rate_table_text}
        f"[종합소득세 세율표]\n{rate_table_text}\n\n"
        f"이 세율표의 누진 구조(구간별 세율 + 누진공제)를 "
        f"정확히 적용해 계산하세요. 단순히 과세표준 전체에 "
        f"한 세율을 곱하지 마세요. 계산 과정을 단계별로 보이고 "
        f"최종 산출세액을 굵게 표시하세요.\n\n"
        f"질문: {question}"
    ).content
    return answer + "\n(소득세법 제55조 세율표 근거 · 참고용)"

print("🧮", calc_bot("과세표준 2000만원이면 세금 얼마야?"))
print()
print("🧮", calc_bot("과세표준 6천만원 세금 계산해줘"))


###### 5-2. 법령봇 ######
# ✍️ [빈칸 채우기] 법령봇 — 4단계 simple_rag 재사용
def law_bot(question):
    # 힌트: 이미 만든 simple_rag(question) 호출
    return simple_rag(question)

print("📖", law_bot("과세기간은 어떻게 되나요?"))


###### 5-3. 상담봇 ######
# ✍️ [빈칸 채우기] 상담봇 — 검색 없이 친절 응대
def chat_bot(question):
    # 힌트: llm.invoke(프롬프트).content
    return llm.invoke(
        f"당신은 위니브 세무 상담 챗봇입니다. 1~2문장으로 "
        f"친절히 답하되, 세금 계산·법령 질문이면 '계산/법령 "
        f"기능을 이용해 주세요'라고 안내하세요.\n손님: {question}"
    ).content

print("💬", chat_bot("안녕하세요, 뭘 도와주나요?"))

print("🤖", simple_rag("기본공제는 1인당 얼마인가요?"))



############## STEP 5 종료 ##############

