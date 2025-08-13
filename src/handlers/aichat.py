import logging
from aiogram import types
from aiogram.fsm.context import FSMContext
from src.database.session import get_session, close_session
from src.database.models import User
from src.constants import MAIN_MENU
from aiogram import Router, F
from aiogram.filters import Command
from .emotion_diary import start_emotion_diary
from src.aichat.openai_rag_service import OpenAIRAGService
import os 


logger = logging.getLogger(__name__)
router = Router(name=__name__)

rag_service = OpenAIRAGService(openai_api_key=os.environ.get("OPENAI_API_KEY"))




@router.message(F.text == '/reset_books')
async def handle_reset_books(message: types.Message, state: FSMContext):
    logger.info(f"Handling 'Reset Books' command. message.from_user.id: {message.from_user.id}")

    if not rag_service.test_connection():
        await message.answer("❌ OpenAI connection muvaffaqiyatsiz! API key va internetni tekshiring.")
        return

    if rag_service.clear_database():
        print("✅ Baza tozalandi!")
        await message.answer("✅ Baza tozalandi!")
    else:
        await message.answer("❌ Bazani tozalashda xatolik!")

    if rag_service.process_books_pdfs():
        await message.answer("🎉 Barcha PDF fayllar muvaffaqiyatli ChromaDB ga qo'shildi!")
    else:
        await message.answer("❌ PDF fayllarni processing qilishda xatolik!")


    stats = rag_service.get_database_stats()
    await message.answer("\n📊 PDF BAZA STATISTIKASI:\n"
    f"📄 Jami PDF chunks: {stats['total_pdf_chunks']}\n"
    f"🔋 Holat: {stats['status']}"
    )




@router.message(F.text)
async def handle_emotion_diary_button(message: types.Message, state: FSMContext):
    logger.info(f"Handling 'Дневник эмоций' button press. message.from_user.id: {message.from_user.id}")
    
    if not rag_service.test_connection():
        await message.answer("❌ OpenAI connection muvaffaqiyatsiz! API key va internetni tekshiring.")
        return
    
    # Show typing status
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    question = message.text.strip()
    
    answer = rag_service.chat(question)

    if answer:
        await message.answer(answer)
    else:
        await message.answer("❌ OpenAI answer NOT FOUND! :(")

