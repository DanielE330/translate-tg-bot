import telebot
from telebot import types
from deep_translator import GoogleTranslator
import pyperclip
import logging
from datetime import datetime
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('translator_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot("YOUR_TELEGRAM_BOT_TOKEN")

def log_event(user_id, action, details=""):
    logger.info(f"User {user_id}: {action}. {details}")

def safe_send(chat_id, text, markup=None):
    try:
        sent_message = bot.send_message(
            chat_id,
            text,
            reply_markup=markup,
            parse_mode='HTML'
        )
        log_event(chat_id, "Message sent", f"Content: {text[:100]}...")
        return sent_message
    except Exception as e:
        logger.error(f"Error sending message to {chat_id}: {str(e)}")
        return None

def create_translate_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        'Английский -> Русский',
        'Русский -> Английский',
        'Другие языки'
    ]
    return markup.add(*[types.KeyboardButton(btn) for btn in buttons])

@bot.message_handler(commands=['start'])
def send_welcome(message):
    log_event(message.chat.id, "Started conversation")
    welcome_text = "Привет! Я бот-переводчик.\nОтправь мне текст, и я переведу его на нужный язык."
    safe_send(message.chat.id, welcome_text)

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    try:
        user_text = message.text.strip()
        if not user_text:
            log_event(message.chat.id, "Empty message received")
            safe_send(message.chat.id, "Пожалуйста, отправьте текст для перевода")
            return

        log_event(message.chat.id, "Text received for translation", f"Length: {len(user_text)} chars")
        safe_send(message.chat.id, "Выберите направление перевода:", create_translate_keyboard())
        bot.register_next_step_handler(message, process_choice, user_text)

    except Exception as e:
        logger.error(f"Error in handle_text: {str(e)}", exc_info=True)
        safe_send(message.chat.id, "Ошибка. Попробуйте снова.")

def process_choice(message, user_text):
    try:
        choice = message.text
        log_event(message.chat.id, "Translation direction selected", f"Choice: {choice}")
        
        if choice == 'Английский -> Русский':
            result = GoogleTranslator(source='en', target='ru').translate(user_text)
            log_event(message.chat.id, "Translation completed", "EN->RU")
            safe_send(
                message.chat.id, 
                f"<b>Перевод:</b>\n\n<code>{result}</code>"
                                        )
            safe_send(message.chat.id, "Готово!", types.ReplyKeyboardRemove())

        elif choice == 'Русский -> Английский':
            result = GoogleTranslator(source='ru', target='en').translate(user_text)
            log_event(message.chat.id, "Translation completed", "RU->EN")
            safe_send(
                message.chat.id, 
                f"<b>Translation:</b>\n\n<code>{result}</code>"
                                        )
            safe_send(message.chat.id, "Done!", types.ReplyKeyboardRemove())

        elif choice == 'Другие языки':
            log_event(message.chat.id, "Custom language selected")
            safe_send(message.chat.id, "Введите код исходного языка (например: en, ru):")
            bot.register_next_step_handler(message, get_source_lang, user_text)

        else:
            log_event(message.chat.id, "Invalid choice", f"Received: {choice}")
            safe_send(message.chat.id, "Неверный выбор. Попробуйте еще раз.", types.ReplyKeyboardRemove())

    except Exception as e:
        logger.error(f"Error in process_choice: {str(e)}", exc_info=True)
        safe_send(message.chat.id, "Ошибка обработки. Начните заново.")

def get_source_lang(message, user_text):
    try:
        src = message.text.strip().lower()[:2]
        if not src.isalpha():
            raise ValueError("Некорректный код языка")
            
        log_event(message.chat.id, "Source language provided", f"Language: {src}")
        safe_send(message.chat.id, "Введите код целевого языка (например: en, ru):")
        bot.register_next_step_handler(message, get_target_lang, user_text, src)
        
    except Exception as e:
        logger.error(f"Invalid source language: {str(e)}")
        safe_send(message.chat.id, "Недопустимый код языка. Начните заново.")

def get_target_lang(message, user_text, src):
    try:
        dest = message.text.strip().lower()[:2]
        if not dest.isalpha():
            raise ValueError("Некорректный код языка")
            
        log_event(message.chat.id, "Target language provided", f"Translation: {src}->{dest}")
        result = GoogleTranslator(source=src, target=dest).translate(user_text)
        safe_send(
            message.chat.id, 
            f"<b>Перевод ({src.upper()}->{dest.upper()}):</b>\n\n<code>{result}</code>", 
        )
        safe_send(message.chat.id, "Готово!", types.ReplyKeyboardRemove())
        
    except Exception as e:
        logger.error(f"Translation error: {str(e)}", exc_info=True)
        safe_send(message.chat.id, "Ошибка перевода. Проверьте коды языков.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('copy_'))
def handle_copy(call):
    try:
        text_to_copy = call.data[5:]  
        try:
            import pyperclip
            pyperclip.copy(text_to_copy)
        except:
            import subprocess
            try:
                subprocess.run(['xclip', '-selection', 'clipboard'], input=text_to_copy.encode('utf-8'), check=True)
            except:
                try:
                    subprocess.run(['xsel', '-b', '-i'], input=text_to_copy.encode('utf-8'), check=True)
                except:
                    bot.answer_callback_query(
                        call.id, 
                        "Не удалось скопировать автоматически. Текст готов для ручного копирования.",
                        show_alert=True
                    )
                    return
        
        log_event(call.from_user.id, "Text copied to clipboard", f"Length: {len(text_to_copy)} chars")
        bot.answer_callback_query(call.id, "✅ Текст скопирован в буфер обмена!")
        
    except Exception as e:
        logger.error(f"Copy error: {str(e)}", exc_info=True)
        bot.answer_callback_query(
            call.id, 
            "⚠️ Не удалось скопировать автоматически. Скопируйте текст вручную.",
            show_alert=True
        )
if __name__ == '__main__':
    logger.info("Starting bot...")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logger.critical(f"Bot crashed: {str(e)}", exc_info=True)
    finally:
        logger.info("Bot stopped")