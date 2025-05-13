import io
from PyPDF2 import PdfReader
import docx
from utils.error_tracker import error_tracker

def extract_text_from_pdf(file):
    """Extract text from a PDF file."""
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                 text += page_text + "\n"
        return text
    except Exception as e:
        error_tracker.add_error("parse_error", f"Error reading PDF {file.name}", True, str(e))
        return ""

def extract_text_from_docx(file):
    """Extract text from a DOCX file."""
    try:
        doc = docx.Document(file)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    except Exception as e:
        error_tracker.add_error("parse_error", f"Error reading DOCX {file.name}", True, str(e))
        return ""

def extract_text_from_file(file):
    """Extract text from a supported file format (PDF, DOCX, TXT)."""
    file_name = file.name.lower()
    # Read content once
    try:
        file_content = file.read()
        # Reset file pointer AFTER reading
        file.seek(0)
    except Exception as e:
        error_tracker.add_error("parse_error", f"Error reading file {file.name}", True, str(e))
        return None

    if file_name.endswith('.pdf'):
        return extract_text_from_pdf(file)
    elif file_name.endswith('.docx'):
        # Use BytesIO for docx
        return extract_text_from_docx(io.BytesIO(file_content))
    elif file_name.endswith('.txt'):
        # Decode bytes to string with error handling
        try:
            return file_content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                # Try another common encoding
                return file_content.decode('latin-1')
            except Exception as e:
                error_tracker.add_error("parse_error", f"Error decoding text file {file.name}", True, str(e))
                return None
    else:
        error_tracker.add_error("parse_error", f"Unsupported file type: {file_name}", False)
        return None
