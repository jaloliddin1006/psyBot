"""
OpenAI PDF RAG Chatbot - Main application
"""
import logging
import os
from openai_rag_service import OpenAIRAGService

# Logging sozlash
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Main OpenAI PDF RAG chatbot"""
    print("🤖 OpenAI PDF RAG Chatbot ishga tushirilmoqda...")
    print("📋 GPT-4o + text-embedding-ada-002 + ChromaDB")
    
    try:
        # OpenAI API key ni olish
        api_key = input("\n🔑 OpenAI API key kiriting: ").strip()
        
        if not api_key:
            print("❌ OpenAI API key talab qilinadi!")
            return
        
        # RAG Service yaratish
        print("🔧 OpenAI RAG Service yaratilmoqda...")
        rag_service = OpenAIRAGService(openai_api_key=api_key)
        
        # Connection tekshirish
        print("🔍 OpenAI connection tekshirilmoqda...")
        if not rag_service.test_connection():
            print("❌ OpenAI connection muvaffaqiyatsiz!")
            print("API key va internetni tekshiring.")
            return
        
        print("✅ OpenAI connection muvaffaqiyatli!")
        
        # Menu
        while True:
            print("\n" + "="*60)
            print("📚 OPENAI PDF RAG CHATBOT MENU")
            print("="*60)
            print("1. books/ PDF fayllarini embedding qilish")
            print("2. Chat (Savol-Javob)")
            print("3. Baza statistikasi")
            print("4. Bazani tozalash")
            print("5. Chiqish")
            print("="*60)
            
            choice = input("Tanlovingizni kiriting (1-5): ").strip()
            
            if choice == '1':
                # books PDF fayllarini processing
                print("\n📁 books/ papkasidagi PDF fayllar processing qilinmoqda...")
                print("⏳ Bu bir necha daqiqa davom etishi mumkin...")
                
                if rag_service.process_books_pdfs():
                    print("🎉 Barcha PDF fayllar muvaffaqiyatli ChromaDB ga qo'shildi!")
                else:
                    print("❌ PDF fayllarni processing qilishda xatolik!")
            
            elif choice == '2':
                # Chat rejimi
                stats = rag_service.get_database_stats()
                
                if stats['total_pdf_chunks'] == 0:
                    print("❌ Avval PDF fayllarni embedding qiling! (1-tanlov)")
                    continue
                
                print(f"\n💬 Chat rejimi (ChromaDB: {stats['total_pdf_chunks']} chunks)")
                print("📝 'exit' yozib chiqing")
                print("-" * 50)
                
                while True:
                    question = input("\n❓ Savolingiz: ").strip()
                    
                    if question.lower() in ['exit', 'chiqish', 'quit']:
                        break
                    
                    if not question:
                        continue
                    
                    print("🤔 Javob tayyorlanmoqda (GPT-4o)...")
                    answer = rag_service.chat(question)
                    print(f"\n🤖 Javob:\n{answer}")
            
            elif choice == '3':
                # Baza statistikasi
                stats = rag_service.get_database_stats()
                print("\n📊 PDF BAZA STATISTIKASI:")
                print(f"📄 Jami PDF chunks: {stats['total_pdf_chunks']}")
                print(f"🔋 Holat: {stats['status']}")
            
            elif choice == '4':
                # Bazani tozalash
                confirm = input("\n❗ Bazani tozalashni xohlaysizmi? [y/N]: ").strip().lower()
                if confirm in ['y', 'yes', 'ha']:
                    if rag_service.clear_database():
                        print("✅ Baza tozalandi!")
                    else:
                        print("❌ Bazani tozalashda xatolik!")
            
            elif choice == '5':
                # Chiqish
                print("👋 Xayr! OpenAI PDF RAG Chatbot yopilmoqda...")
                break
            
            else:
                print("❌ Noto'g'ri tanlov! Iltimos 1-5 orasida raqam kiriting.")
    
    except KeyboardInterrupt:
        print("\n\n👋 Dastur to'xtatildi!")
    except Exception as e:
        logger.error(f"Main da xatolik: {e}")
        print(f"❌ Kutilmagan xatolik: {e}")


if __name__ == "__main__":
    main()
"""
OpenAI PDF RAG Chatbot - Main application
"""
import logging
import os
from openai_rag_service import OpenAIRAGService

# Logging sozlash
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Main OpenAI PDF RAG chatbot"""
    print("🤖 OpenAI PDF RAG Chatbot ishga tushirilmoqda...")
    print("📋 GPT-4o + text-embedding-ada-002 + ChromaDB")
    
    try:
        # OpenAI API key ni olish
        api_key = input("\n🔑 OpenAI API key kiriting: ").strip()
        
        if not api_key:
            print("❌ OpenAI API key talab qilinadi!")
            return
        
        # RAG Service yaratish
        print("🔧 OpenAI RAG Service yaratilmoqda...")
        rag_service = OpenAIRAGService(openai_api_key=api_key)
        
        # Connection tekshirish
        print("🔍 OpenAI connection tekshirilmoqda...")
        if not rag_service.test_connection():
            print("❌ OpenAI connection muvaffaqiyatsiz!")
            print("API key va internetni tekshiring.")
            return
        
        print("✅ OpenAI connection muvaffaqiyatli!")
        
        # Menu
        while True:
            print("\n" + "="*60)
            print("📚 OPENAI PDF RAG CHATBOT MENU")
            print("="*60)
            print("1. books/ PDF fayllarini embedding qilish")
            print("2. Chat (Savol-Javob)")
            print("3. Baza statistikasi")
            print("4. Bazani tozalash")
            print("5. Chiqish")
            print("="*60)
            
            choice = input("Tanlovingizni kiriting (1-5): ").strip()
            
            if choice == '1':
                # books PDF fayllarini processing
                print("\n📁 books/ papkasidagi PDF fayllar processing qilinmoqda...")
                print("⏳ Bu bir necha daqiqa davom etishi mumkin...")
                
                if rag_service.process_books_pdfs():
                    print("🎉 Barcha PDF fayllar muvaffaqiyatli ChromaDB ga qo'shildi!")
                else:
                    print("❌ PDF fayllarni processing qilishda xatolik!")
            
            elif choice == '2':
                # Chat rejimi
                stats = rag_service.get_database_stats()
                
                if stats['total_pdf_chunks'] == 0:
                    print("❌ Avval PDF fayllarni embedding qiling! (1-tanlov)")
                    continue
                
                print(f"\n💬 Chat rejimi (ChromaDB: {stats['total_pdf_chunks']} chunks)")
                print("📝 'exit' yozib chiqing")
                print("-" * 50)
                
                while True:
                    question = input("\n❓ Savolingiz: ").strip()
                    
                    if question.lower() in ['exit', 'chiqish', 'quit']:
                        break
                    
                    if not question:
                        continue
                    
                    print("🤔 Javob tayyorlanmoqda (GPT-4o)...")
                    answer = rag_service.chat(question)
                    print(f"\n🤖 Javob:\n{answer}")
            
            elif choice == '3':
                # Baza statistikasi
                stats = rag_service.get_database_stats()
                print("\n📊 PDF BAZA STATISTIKASI:")
                print(f"📄 Jami PDF chunks: {stats['total_pdf_chunks']}")
                print(f"🔋 Holat: {stats['status']}")
            
            elif choice == '4':
                # Bazani tozalash
                confirm = input("\n❗ Bazani tozalashni xohlaysizmi? [y/N]: ").strip().lower()
                if confirm in ['y', 'yes', 'ha']:
                    if rag_service.clear_database():
                        print("✅ Baza tozalandi!")
                    else:
                        print("❌ Bazani tozalashda xatolik!")
            
            elif choice == '5':
                # Chiqish
                print("👋 Xayr! OpenAI PDF RAG Chatbot yopilmoqda...")
                break
            
            else:
                print("❌ Noto'g'ri tanlov! Iltimos 1-5 orasida raqam kiriting.")
    
    except KeyboardInterrupt:
        print("\n\n👋 Dastur to'xtatildi!")
    except Exception as e:
        logger.error(f"Main da xatolik: {e}")
        print(f"❌ Kutilmagan xatolik: {e}")


if __name__ == "__main__":
    main()
