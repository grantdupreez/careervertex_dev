from PyPDF2 import PdfReader
import docx
import io

def extract_text_from_file(file):
    """Extract text from uploaded file (PDF, DOCX, or TXT)."""
    file_name = file.name.lower()
    
    try:
        if file_name.endswith('.pdf'):
            return extract_from_pdf(file)
        elif file_name.endswith('.docx'):
            return extract_from_docx(file)
        elif file_name.endswith('.txt'):
            return file.read().decode('utf-8')
        else:
            return None
    except Exception as e:
        print(f"Text extraction error: {e}")
        return None

def extract_from_pdf(file):
    """Extract text from PDF file."""
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return None

def extract_from_docx(file):
    """Extract text from DOCX file."""
    try:
        doc = docx.Document(io.BytesIO(file.read()))
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        print(f"DOCX extraction error: {e}")
        return None
