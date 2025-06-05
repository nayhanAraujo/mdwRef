import PyPDF2
import logging

logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path):

    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text += page.extract_text()
        if not text.strip():
            logger.warning(f"Nenhum texto extraído de {pdf_path}. O PDF pode ser baseado em imagem.")
            # Poderia tentar OCR aqui como fallback, mas é mais complexo.
            return None
        logger.info(f"Texto extraído com sucesso de {pdf_path} (Primeiros 500 chars: {text[:500]})")
        return text
    except FileNotFoundError:
        logger.error(f"Arquivo PDF não encontrado: {pdf_path}")
        return None
    except Exception as e:
        logger.error(f"Erro ao processar PDF {pdf_path}: {e}")
        return None