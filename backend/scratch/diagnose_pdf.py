import fitz
import sys

file_path = "uploads/rag_test_document.pdf"
try:
    doc = fitz.open(file_path)
    print(f"PDF open successful! Pages: {len(doc)}")
    for i in range(len(doc)):
        page = doc[i]
        image_list = page.get_images(full=True)
        print(f"Page {i+1} has {len(image_list)} images: {image_list}")
        for img_idx, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            print(f"Image {img_idx+1} extracted: size={len(base_image['image'])} bytes, ext={base_image['ext']}")
except Exception as e:
    print(f"Error: {e}")
