"""
PDF processor for extracting and chunking PDF files
"""
import PyPDF2
from typing import List, Dict, Any
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFProcessor:
    def __init__(self, chunk_size: int = 700, chunk_overlap: int = 100):
        """PDF processoeri"""
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """PDF fayldan matn chiqarish"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                
                logger.info(f"PDF matn chiqarildi: {pdf_path}")
                return text.strip()
                
        except Exception as e:
            logger.error(f"PDF o'qishda xatolik {pdf_path}: {e}")
            return ""
    
    def chunk_text(self, text: str) -> List[str]:
        """PDF matnni chunklarga bo'lish"""
        if not text:
            return []
        
        chunks = []
        words = text.split()
        
        if len(words) <= self.chunk_size:
            return [text]
        
        i = 0
        while i < len(words):
            # Chunk olish
            end_idx = min(i + self.chunk_size, len(words))
            chunk_words = words[i:end_idx]
            chunk = " ".join(chunk_words)
            chunks.append(chunk)
            
            # Overlap bilan keyingi chunk boshlanishi
            i += self.chunk_size - self.chunk_overlap
        
        logger.info(f"PDF matn {len(chunks)} ta chunkga bo'lingan")
        return chunks
    
    def process_pdf_file(self, pdf_path: str) -> List[Dict[str, Any]]:
        """PDF fayl ni process qilish va chunk qilish"""
        try:
            pdf_path = Path(pdf_path)
            
            if pdf_path.suffix.lower() != '.pdf':
                logger.error(f"Fayl PDF emas: {pdf_path}")
                return []
            
            # PDF dan matn chiqarish
            text = self.extract_text_from_pdf(str(pdf_path))
            
            if not text:
                logger.warning(f"PDF dan matn chiqarilmadi: {pdf_path}")
                return []
            
            # Chunklarga bo'lish
            chunks = self.chunk_text(text)
            
            # Metadata bilan qaytarish
            results = []
            for i, chunk in enumerate(chunks):
                results.append({
                    'text': chunk,
                    'metadata': {
                        'file_path': str(pdf_path),
                        'file_name': pdf_path.name,
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                        'file_type': 'pdf'
                    }
                })
            
            logger.info(f"PDF muvaffaqiyatli process qilindi: {pdf_path} ({len(results)} chunks)")
            return results
            
        except Exception as e:
            logger.error(f"PDF faylni process qilishda xatolik {pdf_path}: {e}")
            return []
    
    def process_pdf_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """Papkadagi barcha PDF fayllarni process qilish"""
        try:
            directory_path = Path(directory_path)
            if not directory_path.exists():
                logger.error(f"Papka mavjud emas: {directory_path}")
                return []
            
            all_chunks = []
            
            # PDF fayllarni topish
            for pdf_file in directory_path.rglob('*.pdf'):
                chunks = self.process_pdf_file(str(pdf_file))
                all_chunks.extend(chunks)
            
            logger.info(f"PDF papka process qilindi: {directory_path} ({len(all_chunks)} chunks)")
            return all_chunks
            
        except Exception as e:
            logger.error(f"PDF papkani process qilishda xatolik {directory_path}: {e}")
            return []