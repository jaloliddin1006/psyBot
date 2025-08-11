import os
import logging
from typing import List, Dict
import openai
    
from .pdf_processor import PDFProcessor
from .chroma_manager import ChromaManager

logger = logging.getLogger(__name__)


class OpenAIRAGService:
    """OpenAI RAG Service class"""
    
    def __init__(self, openai_api_key: str):
        """Initialize OpenAI RAG Service"""
        self.openai_api_key = openai_api_key
        self.client = openai.OpenAI(api_key=openai_api_key)
        
        # Komponenlarni yaratish
        self.pdf_processor = PDFProcessor()
        self.chroma_manager = ChromaManager(
            collection_name="books_pdfs",
            embedding_model="openai"
        )
        
        # OpenAI embedding model
        self.embedding_model = "text-embedding-ada-002"
        self.llm_model = "gpt-4o"
        
        logger.info("OpenAI RAG Service yaratildi")
    
    def test_connection(self) -> bool:
        """OpenAI connection ni tekshirish"""
        try:
            # Test embedding
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input="test"
            )
            logger.info("OpenAI connection muvaffaqiyatli!")
            return True
        except Exception as e:
            logger.error(f"OpenAI connection xatolik: {e}")
            return False
    
    def _get_openai_embedding(self, text: str) -> List[float]:
        """OpenAI embedding olish"""
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text.replace("\n", " ")
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding xatolik: {e}")
            raise
    
    def process_books_pdfs(self) -> bool:
        """books/ papkasidagi PDF fayllarni processing qilish"""
        try:
            books_dir = os.path.join(os.getcwd(), "books")
            
            if not os.path.exists(books_dir):
                logger.error("books/ papkasi topilmadi!")
                print("❌ books/ papkasi topilmadi!")
                return False
            
            # PDF fayllarni topish
            pdf_files = []
            for file in os.listdir(books_dir):
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(books_dir, file))
            
            if not pdf_files:
                logger.warning("books/ da PDF fayllar topilmadi!")
                print("⚠️ books/ papkasida PDF fayllar topilmadi!")
                return False
            
            logger.info(f"{len(pdf_files)} ta PDF fayl topildi")
            print(f"📄 {len(pdf_files)} ta PDF fayl topildi:")
            
            # Har bir PDF ni processing qilish
            total_processed = 0
            
            for pdf_path in pdf_files:
                filename = os.path.basename(pdf_path)
                print(f"⏳ Processing: {filename}...")
                
                try:
                    # PDF dan text ajratish
                    text = self.pdf_processor.extract_text_from_pdf(pdf_path)
                    
                    if not text or len(text.strip()) < 50:
                        print(f"⚠️ {filename} - kam text yoki bo'sh fayl")
                        continue
                    
                    # Text ni chunklarga bo'lish
                    chunks = self.pdf_processor.chunk_text(text)
                    
                    if not chunks:
                        print(f"⚠️ {filename} - chunking muvaffaqiyatsiz")
                        continue
                    
                    # Har bir chunk uchun embedding va ChromaDB ga qo'shish
                    for i, chunk in enumerate(chunks):
                        if len(chunk.strip()) < 20:  # Juda kichik chunkni tashlab yuborish
                            continue
                        
                        try:
                            # OpenAI embedding
                            embedding = self._get_openai_embedding(chunk)
                            
                            # ChromaDB ga qo'shish
                            chunk_id = f"{filename}_chunk_{i}"
                            metadata = {
                                "filename": filename,
                                "chunk_index": i,
                                "total_chunks": len(chunks),
                                "file_path": pdf_path
                            }
                            
                            self.chroma_manager.add_document(
                                doc_id=chunk_id,
                                text=chunk,
                                embedding=embedding,
                                metadata=metadata
                            )
                            
                        except Exception as e:
                            logger.error(f"Chunk embedding xatolik ({filename}): {e}")
                            continue
                    
                    total_processed += 1
                    print(f"✅ {filename} - {len(chunks)} chunks qo'shildi")
                    
                except Exception as e:
                    logger.error(f"PDF processing xatolik ({filename}): {e}")
                    print(f"❌ {filename} - processing xatolik: {str(e)[:100]}")
                    continue
            
            if total_processed > 0:
                logger.info(f"{total_processed} ta PDF muvaffaqiyatli processing qilindi")
                print(f"\n🎉 {total_processed}/{len(pdf_files)} ta PDF muvaffaqiyatli qo'shildi!")
                return True
            else:
                logger.warning("Hech qanday PDF processing qilinmadi")
                return False
                
        except Exception as e:
            logger.error(f"books PDF processing xatolik: {e}")
            print(f"❌ PDF processing xatolik: {e}")
            return False
    
    def chat(self, question: str) -> str:
        """Chat funksiyasi - hybrid qidiruv bilan"""
        try:
            # Question ni embedding qilish
            question_embedding = self._get_openai_embedding(question)
            
            # ChromaDB dan relevant chunklar qidirish (hybrid search)
            search_results = self.chroma_manager.hybrid_search(
                query_text=question,
                query_embedding=question_embedding,
                n_results=5
            )
            
            if not search_results or not search_results.get('documents'):
                return "❌ Savolingizga mos hujjatlar topilmadi. Iltimos, boshqa savol bering yoki avval PDF fayllarni yuklashni tekshiring."
            
            # Context tayyorlash
            contexts = []
            for i, doc in enumerate(search_results['documents'][0]):
                metadata = search_results['metadatas'][0][i]
                contexts.append(f"[{metadata.get('filename', 'Unknown')}]: {doc}")
            
            context = "\n\n".join(contexts)
            
            # GPT-4o ga prompt
            prompt = f"""Siz yordamchi AI assistantsiz. Quyidagi hujjatlar asosida foydalanuvchi savoliga aniq va foydali javob bering.

HUJJATLAR:
{context}

FOYDALANUVCHI SAVOLI: {question}

JAVOB QOIDALARI:
1. Faqat berilgan hujjatlar asosida javob bering
2. Javobni o'zbek tilida yozing
3. Aniq va tushunarli bo'lsin
4. Agar javob hujjatlarda yo'q bo'lsa, "Berilgan hujjatlarda bu haqda ma'lumot yo'q" deb ayting
5. Qaysi fayldan ma'lumot olgansangiz, uni ham aytib o'ting

JAVOB:"""

            # OpenAI GPT-4o ga so'rov
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Qo'shimcha ma'lumot
            source_files = set()
            for metadata in search_results['metadatas'][0]:
                if 'filename' in metadata:
                    source_files.add(metadata['filename'])
            
            if source_files:
                answer += f"\n\n📚 Manba fayllar: {', '.join(source_files)}"
            
            return answer
            
        except Exception as e:
            logger.error(f"Chat xatolik: {e}")
            return f"❌ Javob olishda xatolik: {str(e)[:200]}..."
    
    def get_database_stats(self) -> Dict:
        """ChromaDB statistikasi"""
        try:
            count = self.chroma_manager.get_count()
            return {
                "total_pdf_chunks": count,
                "status": "Faol" if count > 0 else "Bo'sh"
            }
        except Exception as e:
            logger.error(f"Database stats xatolik: {e}")
            return {"total_pdf_chunks": 0, "status": "Xatolik"}
    
    def clear_database(self) -> bool:
        """ChromaDB ni tozalash"""
        try:
            return self.chroma_manager.clear_collection()
        except Exception as e:
            logger.error(f"Database clear xatolik: {e}")
            return False
