import pdfplumber

try:
    pdf = pdfplumber.open("C:/Users/UMERz/Downloads/rag_test_document.pdf")
    text = ""
    t_cnt = 0
    img_cnt = 0
    for p in pdf.pages:
        text += (p.extract_text() or "") + "\n"
        t = p.find_tables()
        if t:
            t_cnt += len(t)
        if p.images:
            img_cnt += len(p.images)
            
    lines = [l for l in text.split("\n") if l.strip()]
    paras = [p for p in text.split("\n\n") if p.strip()]
    print(f"SUCCESS: Lines: {len(lines)}, Paras: {len(paras)}, Tables: {t_cnt}, Images: {img_cnt}")
except Exception as e:
    print("ERROR:", e)
