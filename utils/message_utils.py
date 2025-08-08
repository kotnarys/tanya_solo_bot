def split_text_message(text: str, max_length: int = 4096) -> list[str]:
    """
    Разбивает длинный текст на части, не превышающие лимит Telegram.
    
    Args:
        text: Текст для разбивки
        max_length: Максимальная длина одного сообщения (по умолчанию 4096 символов)
    
    Returns:
        Список строк, каждая не длиннее max_length символов
    """
    if len(text) <= max_length:
        return [text]
    
    parts = []
    current_part = ""
    
    # Разбиваем по абзацам
    paragraphs = text.split('\n\n')
    
    for paragraph in paragraphs:
        # Если абзац сам по себе длинный
        if len(paragraph) > max_length:
            # Разбиваем по предложениям
            sentences = paragraph.split('. ')
            for i, sentence in enumerate(sentences):
                if i < len(sentences) - 1:
                    sentence += '. '
                
                if len(current_part + sentence) > max_length:
                    if current_part:
                        parts.append(current_part.strip())
                        current_part = ""
                    
                    # Если предложение само слишком длинное, разбиваем по словам
                    if len(sentence) > max_length:
                        words = sentence.split(' ')
                        for word in words:
                            if len(current_part + word + ' ') > max_length:
                                if current_part:
                                    parts.append(current_part.strip())
                                    current_part = ""
                            current_part += word + ' '
                    else:
                        current_part = sentence
                else:
                    current_part += sentence
        else:
            # Проверяем, поместится ли абзац в текущую часть
            if len(current_part + '\n\n' + paragraph) > max_length:
                if current_part:
                    parts.append(current_part.strip())
                    current_part = paragraph
                else:
                    current_part = paragraph
            else:
                if current_part:
                    current_part += '\n\n' + paragraph
                else:
                    current_part = paragraph
    
    if current_part:
        parts.append(current_part.strip())
    
    return parts


async def send_split_message(bot_or_message, text: str, chat_id: int = None, **kwargs):
    """
    Отправляет сообщение, автоматически разбивая его на части если оно слишком длинное.
    
    Args:
        bot_or_message: Bot instance или Message instance
        text: Текст для отправки
        chat_id: ID чата (нужен если передан bot)
        **kwargs: Дополнительные параметры для send_message
    """
    parts = split_text_message(text)
    
    for part in parts:
        if hasattr(bot_or_message, 'send_message'):
            # Это bot instance
            await bot_or_message.send_message(chat_id, part, **kwargs)
        else:
            # Это message instance
            await bot_or_message.answer(part, **kwargs)


async def answer_split_text(message, text: str, **kwargs):
    """
    Удобная функция для ответа на сообщение с автоматической разбивкой длинного текста.
    
    Args:
        message: Message instance
        text: Текст для отправки
        **kwargs: Дополнительные параметры для answer
    """
    parts = split_text_message(text)
    
    for part in parts:
        await message.answer(part, **kwargs)