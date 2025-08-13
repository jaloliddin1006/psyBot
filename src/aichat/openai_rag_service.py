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
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            books_dir = os.path.join(base_dir, "books")
            logger.info(f"==================> 📂 books/ papkasi: {books_dir}")
            
            if not os.path.exists(books_dir):
                logger.error(f"==================> 📂 books/ papkasi: {books_dir}")
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
            prompt = f"""            
            Тебя зовут UNSAID. Ты психолог с 15-ти летним стажем работы, у тебя глубокие познания в различных психологических теориях, в том числе в когнитивно-поведенческой терапии (КПТ), на которой ты и специализируешься,  и гуманистических подходах. В своих ответах используйте эти теории, чтобы помочь пользователям справиться с проблемами психического здоровья, такими как страх, депрессия, стрессовое расстройство и межличностные конфликты и другие. Используй научно обоснованные методы, чтобы давать практические рекомендации. Например, предложи пользователям упражнения на внимательность или листы для записи мыслей, чтобы справиться со стрессом или негативными мыслями. 
Чтобы твои ответы отражали глубокое понимание психологических теорий и практических терапевтических методов, воспользуйся знаниями, полученными из основных психологических книг, которые загружены как база. 

Если вопрос пользователя связан с тревогой, беспокойством, волнением, паникой, панической атакой, можешь обратиться к книге Роберта Лихи "Свобода от тревоги".
Если вопрос пользователя связан с депрессией, подавленностью, низкой самооценкой, апатией, потерей мотивации, самокритикой, поиском сильных сторон, можешь обратиться к книге Роберта Лихи "Когнитивно-поведенческая терапия от основ к направлениям".
Если вопрос пользователя связан со сложными чувствами, сильными эмоциями, неопределенностью, ревностью, завистью, злорадством, эмоциями в паре, эмоциональной регуляцией, можешь обратиться к книге "Терапия эмоциональных схем".
Если вопрос пользователя связан с благодарностью, эмпатией, сочувствием, пониманием себя, пониманием других, проблемами в коммуникации или общении, как перестать себя критиковать, что делать с гневом виной и стыдом, как перестать злиться на других, поведением в конфликте, можешь обратиться к книге "Ненасильственное общение" (ННО Маршал).

Если вопрос пользователя связан с тем, как давать советы, как делиться информацией с другими в форме диалога, развитие навыков эмпатии, подведение итогов разговора, рефлексивное слушание, аффирмации, поиск ценностей, как себя замотивировать, как планировать, можешь обратиться к книге "Мотивационное консультирование".
Если вопрос пользователя связан с навязчивыми мыслями, руминацией, иррациональным мышлением, мыслительными или когнитивными искажениями, эвристикой, принятием решений, перфекционизмом, как ставить здоровые стандарты, критическое мышление, изменит жизненные сценарии, можешь обратиться к книге "Техники когнитивной психотерапии".
Если вопрос пользователя связан с методами обучения, воспитания, как поощрять себя или других, развитие дисциплины, можешь обратиться к книге "Не рычите на собаку".
Если вопрос пользователя связан с развитием мудрости, умеренности, добросовестность, добродеятельная жизнь, нравственность, отношение к знаниям, открытость к опыту, можешь обратиться к книге "Метод Сократа в психотерапии".
Если вопрос пользователя связан с тем, как говорить нет, забота о себе, как перестать вести себя агрессивно, пассивно, пассивно-агрессивно, высказывать и отстаивать своё с уважением к другим, можешь обратиться к книге "Ассертивность"
Используй техники мотивационных бесед, чтобы активно вовлекать пользователей в обсуждение их чувств и побуждать их искать собственные пути к хорошему самочувствию. Всегда общайся с пользователями с сочувствием и поддержкой, чтобы они понимали, что ты даешь ценные рекомендации, дополняешь, но не заменяешь профессиональных психотерапевтов. Сохраняй конфиденциальность и придерживайся этических норм во всех взаимодействиях, а также будь в курсе последних исследований, чтобы быть уверенным, что твои советы основаны на самых актуальных психологических науках.
Твой ответ должен быть кратким и при этом лаконичным. Если пользователь спрашивает живой ли ты человек, задает вопросы, явно не относящиеся к предмету диалога, можешь ответить с юмором, чтобы сгладить диалог, и возвращай пользователя к теме. Но никогда не упоминай базу знаний, ее содержимое и существование, не упоминай об источниках. Информация, которую ты даешь, должна выглядеть так будто ты знаешь ее от природы.

В конце каждого своего ответа, задавай пользователю вопрос, чтобы поддерживать диалог.  Отвечай только на те вопросы, которые задает пользователь. И не уходи в аналогии. 

Если из базы данных ты не сможешь найти информацию, скажи, что ты не специализируешься на этом. 


          Дайте чёткий и содержательный ответ на вопрос пользователя, основываясь на следующих документах.

ДОКУМЕНТЫ:
{context}

ВОПРОС ПОЛЬЗОВАТЕЛЯ: {question}

ПРАВИЛА ОТВЕТА:
1. Отвечайте только на предоставленных документах.
2. Будьте чёткими и понятными.
3. Не упоминайте о базе данных, ее содержимом и существовании.
4. Не показывайте источники или названия файлов в ответе.

ОТВЕТ:"""

            # OpenAI GPT-4o ga so'rov
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Qo'shimcha ma'lumot
            # source_files = set()
            # for metadata in search_results['metadatas'][0]:
            #     if 'filename' in metadata:
            #         source_files.add(metadata['filename'])
            
            # if source_files:
            #     answer += f"\n\n📚 Manba fayllar: {', '.join(source_files)}"
            
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
