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