
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




########################## STEP 5 ###########################

###### 5-1. 한계측정 ######
print("① 잡담:")
print("🙋 안녕하세요")
print("🤖", simple_rag("안녕하세요"), "\n")

print("② 계산:")
print("🙋 과세표준 2000만원이면 6% 세율로 세금은?")
print("🤖", simple_rag("과세표준 2000만원이면 6% 세율로 세금은 얼마야?"), "\n")

print("③ 법령:")
print("🙋 기본공제 금액은?")
print("🤖", simple_rag("기본공제는 1인당 얼마인가요?"))





###### 5-2. 봇 ㅡ 1) 계산봇 ######
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


###### 5-2. 봇 ㅡ 2) 법령봇 ######
# ✍️ [빈칸 채우기] 법령봇 — 4단계 simple_rag 재사용
def law_bot(question):
    # 힌트: 이미 만든 simple_rag(question) 호출
    return simple_rag(question)

print("📖", law_bot("과세기간은 어떻게 되나요?"))


###### 5-2. 봇 ㅡ 3) 상담봇 ######
# ✍️ [빈칸 채우기] 상담봇 — 검색 없이 친절 응대
def chat_bot(question):
    # 힌트: llm.invoke(프롬프트).content
    return llm.invoke(
        f"당신은 위니브 세무 상담 챗봇입니다. 1~2문장으로 "
        f"친절히 답하되, 세금 계산·법령 질문이면 '계산/법령 "
        f"기능을 이용해 주세요'라고 안내하세요.\n손님: {question}"
    ).content

print("💬", chat_bot("안녕하세요, 뭘 도와주나요?"))