from aiogram import types
from aiogram.fsm.context import FSMContext
import logging
import asyncio

logger = logging.getLogger(__name__)

async def delete_previous_messages(message: types.Message, state: FSMContext, keep_current: bool = False):
    data = await state.get_data()
    messages_to_delete = data.get('messages_to_delete', [])
    new_messages_to_delete_list = [] # To rebuild the list if keep_current is true

    for msg_id in messages_to_delete:
        if keep_current and msg_id == message.message_id:
            new_messages_to_delete_list.append(msg_id) # Keep it in the list for next time if needed
            continue # Skip deleting this one
        try:
            await message.bot.delete_message(message.chat.id, msg_id)
        except Exception as e:
            # Log error or handle specific exceptions if necessary
            logger.debug(f"Failed to delete message {msg_id} in chat {message.chat.id}: {e}")
            pass # Continue trying to delete other messages
    
    if keep_current:
        # If we kept the current message, the list should reflect that for future deletions.
        # For now, if keep_current, we put only the current message back if it was targeted, or empty the list.
        if message.message_id in messages_to_delete and message.message_id in new_messages_to_delete_list:
             await state.update_data(messages_to_delete=new_messages_to_delete_list)
        else:
             await state.update_data(messages_to_delete=[])
    else:
        await state.update_data(messages_to_delete=[])

async def show_pin_recommendation_and_main_menu(callback: types.CallbackQuery, state: FSMContext, clear_state: bool = True):
    """Show pin chat recommendation and then main menu"""
    await callback.answer()  # Acknowledge the callback
    await delete_previous_messages(callback.message, state)  # Clean up the capabilities message
    if clear_state:
        await state.clear()  # Clear the registration FSM state
    
    # Show pin chat recommendation
    pin_msg = await callback.message.answer(
        "Для удобства пользования рекомендую закрепить чат. Так мы точно не потеряемся среди множества сообщений 💚"
    )
    
    # Add short delay and then show main menu
    await asyncio.sleep(2)  # 2 second delay
    
    # Import and call main menu
    from .main_menu import main_menu
    await main_menu(callback, state)
