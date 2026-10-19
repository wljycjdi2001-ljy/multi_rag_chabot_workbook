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