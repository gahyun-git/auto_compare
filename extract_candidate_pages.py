import pdfplumber
from PyPDF2 import PdfReader, PdfWriter
import os

# 1. 경로/파일명 설정 (원본 PDF 파일)
pdf_path = "input_pdfs/2026_동국대.pdf"

# 2. 후보 키워드/페이지 threshold (자유롭게 조정 가능)
keywords = ['모집', '정원', '전형', '변경', '학과', '증원', '감원']
threshold = 2

# 3. 후보 페이지 자동 탐색
def find_candidate_pages(pdf_path, keywords, threshold=2):
    candidate_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            score = sum(text.count(kw) for kw in keywords)
            if score >= threshold:
                candidate_pages.append(i)
    return candidate_pages

# 4. 후보 페이지만 PDF로 저장
def save_pages(pdf_path, page_numbers, out_pdf):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    for num in page_numbers:
        writer.add_page(reader.pages[num])
    os.makedirs(os.path.dirname(out_pdf), exist_ok=True)
    with open(out_pdf, "wb") as f:
        writer.write(f)
    print(f"후보 페이지만 저장: {out_pdf}")

if __name__ == "__main__":
    candidate_pages = find_candidate_pages(pdf_path, keywords, threshold)
    print(f"\n[INFO] 후보 페이지: {candidate_pages}")

    # 경로/파일명 지정
    out_pdf = "input_pdfs/2026_동국대_candidate.pdf"

    if candidate_pages:
        save_pages(pdf_path, candidate_pages, out_pdf)
        print(f"\n[INFO] 후보 PDF가 생성되었습니다: {out_pdf}")
        print("[INFO] 이제 main.py에서 이 파일만 API로 돌리세요!")
    else:
        print("\n[INFO] 후보 페이지가 없습니다. threshold/keywords를 조정하세요.")
