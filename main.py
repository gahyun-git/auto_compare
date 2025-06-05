import glob
import os
from google.cloud import documentai_v1 as documentai
import pandas as pd

# ========== 환경 세팅 ==========
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service-account.json"

# [여기 직접 입력!] --------------------------------------
project_id = "lean-ai-faq"                # 본인 GCP 프로젝트 ID
location = "us"                               # ex) us, asia-northeast1
form_parser_id = "531ed2ea56b22562"          # Form Parser 프로세서 ID
ocr_processor_id = "d6772c2611759117"   # Document OCR 프로세서 ID
# -----------------------------------------------------
def parse_pdf_tables(file_path, processor_id):
    client = documentai.DocumentProcessorServiceClient()
    resource_name = client.processor_path(project_id, location, processor_id)

    with open(file_path, "rb") as pdf_file:
        content = pdf_file.read()

    raw_document = documentai.RawDocument(content=content, mime_type="application/pdf")
    request = documentai.ProcessRequest(
        name=resource_name,
        raw_document=raw_document
    )
    result = client.process_document(request=request)
    document = result.document

    tables = []
    for page in document.pages:
        for table in page.tables:
            table_data = []
            for row in table.header_rows + table.body_rows:
                cells = []
                for cell in row.cells:
                    text = ""
                    for segment in cell.layout.text_anchor.text_segments:
                        text += document.text[segment.start_index:segment.end_index]
                    cells.append(text.strip())
                table_data.append(cells)
            tables.append(table_data)
    if not tables:
        texts = []
        for page in document.pages:
            text = ""
            if hasattr(page.layout, "text_anchor") and page.layout.text_anchor.text_segments:
                for segment in page.layout.text_anchor.text_segments:
                    text += document.text[segment.start_index:segment.end_index]
            texts.append(text)
        return None, texts
    return tables, None

def tables_to_dataframes(tables):
    dataframes = []
    for table in tables:
        if len(table) > 1:
            columns = table[0]
            rows = table[1:]
            clean_rows = [row + ['']*(len(columns)-len(row)) if len(row)<len(columns) else row for row in rows]
            df = pd.DataFrame(clean_rows, columns=columns)
            dataframes.append(df)
    return dataframes

def save_ocr_texts(texts, filename):
    with open(filename, "w", encoding="utf-8") as f:
        for i, text in enumerate(texts):
            f.write(f"--- Page {i+1} ---\n{text}\n\n")

if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)

    # 후보 PDF 자동 인식: 모든 *_candidate.pdf 처리
    candidate_pdf_list = sorted(glob.glob("input_pdfs/*_candidate.pdf"))

    if not candidate_pdf_list:
        print("[오류] 분석할 후보 PDF가 없습니다. extract_candidate_pages.py를 먼저 실행하세요.")
        exit()

    for pdf_path in candidate_pdf_list:
        base = os.path.basename(pdf_path).replace('.pdf', '')

        print(f"\n===== {base} 분석 시작 =====")

        # 1. Form Parser 처리
        print("[Form Parser] 표 추출 시도...")
        tables, texts = parse_pdf_tables(pdf_path, form_parser_id)
        if tables:
            dfs = tables_to_dataframes(tables)
            print(f"[Form Parser] 추출된 표 개수: {len(dfs)}")
            for i, df in enumerate(dfs):
                outname = f"output/{base}_formparser_table{i+1}.xlsx"
                df.to_excel(outname, index=False)
                print(f"[Form Parser] 엑셀 저장: {outname}")
        else:
            print("[Form Parser] 표 추출 실패. OCR 텍스트만 추출.")

        # 2. Document OCR도 병행(비교용, 선택)
        print("[OCR] 표/텍스트 추출 시도...")
        tables_ocr, texts_ocr = parse_pdf_tables(pdf_path, ocr_processor_id)
        if tables_ocr:
            dfs_ocr = tables_to_dataframes(tables_ocr)
            print(f"[OCR] 추출된 표 개수: {len(dfs_ocr)}")
            for i, df in enumerate(dfs_ocr):
                outname = f"output/{base}_ocr_table{i+1}.xlsx"
                df.to_excel(outname, index=False)
                print(f"[OCR] 엑셀 저장: {outname}")
        elif texts_ocr:
            txtname = f"output/{base}_ocr_text.txt"
            save_ocr_texts(texts_ocr, txtname)
            print(f"[OCR] 표 추출 실패, 텍스트만 저장: {txtname}")
        else:
            print("[OCR] 결과 없음.")

    print("\n✅ 모든 후보 PDF 분석 완료! output 폴더에서 결과를 확인하세요.")
