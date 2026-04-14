import os
import re
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton,
    InlineKeyboardMarkup, FSInputFile
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import config
from database import db
from sync_files import sync_directory

# Создаём роутер
router = Router()



# ========== FSM состояния ==========
class FileUpload(StatesGroup):
    waiting_for_name = State()
    waiting_for_file = State()

class FileRename(StatesGroup):
    waiting_for_new_name = State()

# ========== Клавиатуры ==========
def main_keyboard():
    buttons = [
        [InlineKeyboardButton(text="📂 Просмотреть файлы", callback_data="view_files")],
        [InlineKeyboardButton(text="⬆️ Отправить файл", callback_data="upload_file")],
        [InlineKeyboardButton(text="🔄 Синхронизация", callback_data="sync_files")],
        [InlineKeyboardButton(text="👥 Статистика", callback_data="stats")],
        [InlineKeyboardButton(text="⚙️ Управление", callback_data="admin")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def file_type_keyboard(action="view"):
    buttons = [
        [InlineKeyboardButton(text="🎵 Музыка", callback_data=f"{action}_music")],
        [InlineKeyboardButton(text="🎬 Видео", callback_data=f"{action}_video")],
        [InlineKeyboardButton(text="📷 Фото", callback_data=f"{action}_photo")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])

def get_emoji(file_type: str) -> str:
    return {'music': '🎵', 'video': '🎬', 'photo': '📷'}.get(file_type, '📁')

# ========== Вспомогательные функции ==========
async def show_files_list(callback: CallbackQuery, file_type: str):
    # Синхронизация перед показом
    directories = {
        'music': config.MUSIC_DIR,
        'video': config.VIDEO_DIR,
        'photo': config.PHOTO_DIR
    }
    sync_directory(directories[file_type], file_type)

    files = db.get_files_by_type(file_type)
    if not files:
        await callback.message.edit_text(
            f"📭 Файлов типа {get_emoji(file_type)} пока нет",
            reply_markup=back_keyboard()
        )
        return

    keyboard = []
    for file in files[:20]:
        file_id, filename, original_name, file_size, _ = file
        size_mb = file_size / (1024 * 1024) if file_size else 0
        btn_text = f"{filename} ({size_mb:.1f} MB)"
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"send_{file_id}")])
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="view_files")])

    await callback.message.edit_text(
        f"📂 {get_emoji(file_type)} ({len(files)} файлов):\n\nНажмите на файл для получения:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

# ========== Хендлеры команд ==========
@router.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    db.add_user(user.id, user.username, user.first_name, user.last_name)

    text = f"""
👋 Привет, {user.first_name}!

🎬 Добро пожаловать в Media Server Bot!

Здесь вы можете:
📂 Просматривать медиа-файлы
⬆️ Загружать свои файлы
📊 Смотреть статистику

Выберите действие:
"""
    await message.answer(text, reply_markup=main_keyboard())

@router.message(Command("help"))
async def cmd_help(message: Message):
    text = """
📖 <b>Справка по Media Server Bot</b>

<b>Команды:</b>
/start - Главное меню
/help - Справка
/cancel - Отменить действие
/stats - Статистика

<b>Просмотр файлов:</b>
📂 Просмотреть → выберите тип → нажмите на файл

<b>Загрузка файлов:</b>
⬆️ Отправить → выберите тип → введите имя → отправьте файл

<b>Разрешенные форматы:</b>
🎬 Видео: .mp4, .mkv
📷 Фото: .raw, .jpeg, .jpg, .png
🎵 Музыка: .ogg, .wav, .mp3

<b>Управление:</b>
✏️ Переименование файлов
🗑️ Удаление файлов (с подтверждением)
"""
    await message.answer(text, reply_markup=back_keyboard())

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer("❌ Действие отменено", reply_markup=back_keyboard())
    else:
        await message.answer("Нет активных действий", reply_markup=back_keyboard())

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    user_count = db.get_user_count()
    music_count = len(db.get_files_by_type('music'))
    video_count = len(db.get_files_by_type('video'))
    photo_count = len(db.get_files_by_type('photo'))

    text = f"""
📊 <b>Статистика сервера</b>

👥 Пользователей: {user_count}

📁 Файлов в базе:
🎵 Музыка: {music_count}
🎬 Видео: {video_count}
📷 Фото: {photo_count}

📦 Всего: {music_count + video_count + photo_count}
"""
    await message.answer(text, reply_markup=back_keyboard())

# ========== Обработка CallbackQuery ==========
@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    await callback.message.edit_text("📱 Главное меню:", reply_markup=main_keyboard())
    await callback.answer()

@router.callback_query(F.data == "view_files")
async def callback_view_files(callback: CallbackQuery):
    await callback.message.edit_text(
        "📂 Выберите категорию для просмотра:",
        reply_markup=file_type_keyboard("view")
    )
    await callback.answer()

@router.callback_query(F.data.startswith("view_"))
async def callback_view_type(callback: CallbackQuery):
    file_type = callback.data.replace("view_", "")
    await show_files_list(callback, file_type)
    await callback.answer()

@router.callback_query(F.data == "upload_file")
async def callback_upload_file(callback: CallbackQuery):
    await callback.message.edit_text(
        "⬆️ Что хотите загрузить?",
        reply_markup=file_type_keyboard("upload")
    )
    await callback.answer()

@router.callback_query(F.data.startswith("upload_"))
async def callback_upload_type(callback: CallbackQuery, state: FSMContext):
    file_type = callback.data.replace("upload_", "")
    await state.update_data(file_type=file_type)
    await state.set_state(FileUpload.waiting_for_name)
    await callback.message.edit_text(
        f"📝 Введите имя файла для {get_emoji(file_type)}:\n\n"
        "(Без расширения, оно добавится автоматически)"
    )
    await callback.answer()

@router.callback_query(F.data == "sync_files")
async def callback_sync_files(callback: CallbackQuery):
    await callback.message.edit_text("🔄 Синхронизация...")
    total = 0
    total += sync_directory(config.MUSIC_DIR, 'music')
    total += sync_directory(config.VIDEO_DIR, 'video')
    total += sync_directory(config.PHOTO_DIR, 'photo')

    music_count = len(db.get_files_by_type('music'))
    video_count = len(db.get_files_by_type('video'))
    photo_count = len(db.get_files_by_type('photo'))

    text = f"""
✅ Синхронизация завершена!

🆕 Новых файлов добавлено: {total}

📁 Всего в базе:
🎵 Музыка: {music_count}
🎬 Видео: {video_count}
📷 Фото: {photo_count}
"""
    await callback.message.edit_text(text, reply_markup=back_keyboard())
    await callback.answer()

@router.callback_query(F.data == "stats")
async def callback_stats(callback: CallbackQuery):
    user_count = db.get_user_count()
    music_count = len(db.get_files_by_type('music'))
    video_count = len(db.get_files_by_type('video'))
    photo_count = len(db.get_files_by_type('photo'))

    text = f"""
📊 <b>Статистика сервера</b>

👥 Пользователей: {user_count}

📁 Файлов в базе:
🎵 Музыка: {music_count}
🎬 Видео: {video_count}
📷 Фото: {photo_count}

📦 Всего: {music_count + video_count + photo_count}
"""
    await callback.message.edit_text(text, reply_markup=back_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin")
async def callback_admin(callback: CallbackQuery):
    buttons = [
        [InlineKeyboardButton(text="✏️ Переименовать файл", callback_data="admin_rename")],
        [InlineKeyboardButton(text="🗑️ Удалить файл", callback_data="admin_delete")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ]
    await callback.message.edit_text(
        "⚙️ Панель управления:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

@router.callback_query(F.data == "admin_rename")
async def callback_admin_rename(callback: CallbackQuery):
    await callback.message.edit_text(
        "✏️ Выберите тип файла для переименования:",
        reply_markup=file_type_keyboard("rename")
    )
    await callback.answer()

@router.callback_query(F.data.startswith("rename_"))
async def callback_rename_type(callback: CallbackQuery):
    file_type = callback.data.replace("rename_", "")
    files = db.get_files_by_type(file_type)
    if not files:
        await callback.message.edit_text(
            f"📭 Файлов типа {get_emoji(file_type)} нет",
            reply_markup=back_keyboard()
        )
        await callback.answer()
        return

    keyboard = []
    for file in files[:20]:
        file_id, filename, _, _, _ = file
        keyboard.append([InlineKeyboardButton(text=filename, callback_data=f"ren_{file_id}")])
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_rename")])

    await callback.message.edit_text(
        "✏️ Выберите файл для переименования:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data == "admin_delete")
async def callback_admin_delete(callback: CallbackQuery):
    await callback.message.edit_text(
        "🗑️ Выберите тип файла для удаления:",
        reply_markup=file_type_keyboard("delete")
    )
    await callback.answer()

@router.callback_query(F.data.startswith("delete_"))
async def callback_delete_type(callback: CallbackQuery):
    file_type = callback.data.replace("delete_", "")
    files = db.get_files_by_type(file_type)
    if not files:
        await callback.message.edit_text(
            f"📭 Файлов типа {get_emoji(file_type)} нет",
            reply_markup=back_keyboard()
        )
        await callback.answer()
        return

    keyboard = []
    for file in files[:20]:
        file_id, filename, _, _, _ = file
        keyboard.append([InlineKeyboardButton(text=f"🗑 {filename}", callback_data=f"del_{file_id}")])
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_delete")])

    await callback.message.edit_text(
        "🗑️ Выберите файл для удаления:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("ren_"))
async def callback_rename_file(callback: CallbackQuery, state: FSMContext):
    file_id = int(callback.data.replace("ren_", ""))
    file_data = db.get_file_by_id(file_id)
    if not file_data:
        await callback.message.edit_text("❌ Файл не найден", reply_markup=back_keyboard())
        await callback.answer()
        return

    await state.update_data(file_id=file_id, file_data=file_data)
    await state.set_state(FileRename.waiting_for_new_name)
    await callback.message.edit_text(
        f"✏️ Переименование файла:\n\n"
        f"📄 Текущее имя: <b>{file_data[1]}</b>\n\n"
        f"Введите новое имя файла (без расширения):",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("del_"))
async def callback_delete_file(callback: CallbackQuery):
    file_id = int(callback.data.replace("del_", ""))
    file_data = db.get_file_by_id(file_id)
    if not file_data:
        await callback.message.edit_text("❌ Файл не найден", reply_markup=back_keyboard())
        await callback.answer()
        return

    keyboard = [
        [
            InlineKeyboardButton(text="✅ Да, удалить!", callback_data=f"confirm_delete_{file_id}"),
            InlineKeyboardButton(text="❌ Нет, отмена", callback_data="cancel_delete")
        ]
    ]
    await callback.message.edit_text(
        f"⚠️ <b>ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ</b>\n\n"
        f"📄 Файл: <b>{file_data[1]}</b>\n"
        f"📂 Тип: {get_emoji(file_data[3])}\n\n"
        f"❗ Это действие <b>НЕЛЬЗЯ</b> отменить!\n"
        f"Вы уверены?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_delete_"))
async def callback_confirm_delete(callback: CallbackQuery):
    file_id = int(callback.data.replace("confirm_delete_", ""))
    file_data = db.get_file_by_id(file_id)
    if not file_data:
        await callback.message.edit_text("❌ Файл не найден", reply_markup=back_keyboard())
        await callback.answer()
        return

    file_path = file_data[4]
    filename = file_data[1]

    physical_deleted = False
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            physical_deleted = True
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка удаления с диска: {e}", reply_markup=back_keyboard())
            await callback.answer()
            return

    db.delete_file(file_id)
    db.log_operation(callback.from_user.id, 'delete', file_id, f"Deleted {filename}")

    status = "с диска и из базы" if physical_deleted else "из базы (файл на диске не найден)"
    await callback.message.edit_text(
        f"✅ Файл <b>{filename}</b> успешно удален {status}!",
        parse_mode="HTML",
        reply_markup=back_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_delete")
async def callback_cancel_delete(callback: CallbackQuery):
    await callback.message.edit_text("❌ Удаление отменено", reply_markup=back_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("send_"))
async def callback_send_file(callback: CallbackQuery, bot: Bot):
    file_id = int(callback.data.replace("send_", ""))
    file_data = db.get_file_by_id(file_id)
    if not file_data:
        await callback.answer("❌ Файл не найден", show_alert=True)
        return

    file_path = file_data[4]
    file_type = file_data[3]

    if not os.path.exists(file_path):
        await callback.answer("❌ Файл не существует на сервере", show_alert=True)
        return

    await callback.answer("⏳ Отправляю файл...")
    try:
        input_file = FSInputFile(file_path)
        if file_type == 'photo':
            await callback.message.answer_photo(photo=input_file, caption=file_data[1])
        elif file_type == 'video':
            await callback.message.answer_video(video=input_file, caption=file_data[1])
        elif file_type == 'music':
            await callback.message.answer_audio(audio=input_file, caption=file_data[1])
        db.log_operation(callback.from_user.id, 'download', file_id, f"Downloaded {file_data[1]}")
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка отправки файла: {e}")

# ========== Обработка текстовых сообщений (FSM) ==========
@router.message(FileUpload.waiting_for_name)
async def process_filename(message: Message, state: FSMContext):
    text = message.text.strip()
    # Проверка на запрещённые символы
    if re.search(r'[\\/:*?"<>|]', text):
        await message.answer("❌ Имя содержит недопустимые символы! Запрещены: \\ / : * ? \" < > |\nВведите другое имя:")
        return
    if len(text) > 200:
        await message.answer("❌ Имя слишком длинное (макс. 200 символов)\nВведите другое имя:")
        return

    data = await state.get_data()
    file_type = data['file_type']
    await state.update_data(file_name=text)
    await state.set_state(FileUpload.waiting_for_file)

    allowed = config.ALLOWED_EXTENSIONS[file_type]
    await message.answer(
        f"✅ Имя файла: <b>{text}</b>\n\n"
        f"📎 Теперь отправьте сам файл!\n\n"
        f"📋 Разрешенные форматы для {get_emoji(file_type)}:\n"
        f"<b>{', '.join(allowed)}</b>\n\n"
        f"❗ Отправьте файл как документ (скрепка → файл)",
        parse_mode="HTML"
    )

@router.message(FileUpload.waiting_for_file, F.document)
async def process_document(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    file_type = data['file_type']
    custom_name = data['file_name']
    document = message.document

    original_name = document.file_name or "unknown"
    _, ext = os.path.splitext(original_name)
    ext = ext.lower()
    allowed = config.ALLOWED_EXTENSIONS.get(file_type, [])
    if ext not in allowed:
        await message.answer(
            f"❌ <b>Недопустимое расширение!</b>\n\n"
            f"📄 Ваш файл: <b>{ext}</b>\n"
            f"📋 Для {get_emoji(file_type)} разрешены:\n"
            f"<b>{', '.join(allowed)}</b>",
            parse_mode="HTML"
        )
        return

    if document.file_size > 50 * 1024 * 1024:
        await message.answer("❌ Файл слишком большой! Лимит Telegram: 50 МБ.")
        return

    directories = {
        'music': config.MUSIC_DIR,
        'video': config.VIDEO_DIR,
        'photo': config.PHOTO_DIR
    }
    directory = directories[file_type]
    final_filename = custom_name + ext
    file_path = os.path.join(directory, final_filename)

    counter = 1
    while os.path.exists(file_path):
        final_filename = f"{custom_name}_{counter}{ext}"
        file_path = os.path.join(directory, final_filename)
        counter += 1

    await message.answer("⏳ Загружаю файл на сервер...")
    try:
        file = await bot.get_file(document.file_id)
        await bot.download_file(file.file_path, destination=file_path)

        file_size = os.path.getsize(file_path)
        db_id = db.add_file(final_filename, original_name, file_type, file_path, file_size, message.from_user.id)
        db.log_operation(message.from_user.id, 'upload', db_id, f"Uploaded {final_filename}")

        await state.clear()
        size_mb = file_size / (1024 * 1024)
        await message.answer(
            f"✅ <b>Файл успешно загружен!</b>\n\n"
            f"📄 Имя: <b>{final_filename}</b>\n"
            f"📂 Тип: {get_emoji(file_type)}\n"
            f"📦 Размер: <b>{size_mb:.2f} MB</b>\n"
            f"💾 Путь: <code>{file_path}</code>",
            parse_mode="HTML",
            reply_markup=back_keyboard()
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка загрузки: {e}")
        await state.clear()

@router.message(FileUpload.waiting_for_file, F.photo)
async def process_photo(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    file_type = data['file_type']
    if file_type != 'photo':
        await message.answer(
            f"❌ Вы выбрали категорию <b>{get_emoji(file_type)}</b>, а отправляете фото!\n"
            f"Отправьте файл как документ (📎 скрепка)",
            parse_mode="HTML"
        )
        return

    custom_name = data['file_name']
    photo = message.photo[-1]
    final_filename = custom_name + ".jpg"
    file_path = os.path.join(config.PHOTO_DIR, final_filename)

    counter = 1
    while os.path.exists(file_path):
        final_filename = f"{custom_name}_{counter}.jpg"
        file_path = os.path.join(config.PHOTO_DIR, final_filename)
        counter += 1

    await message.answer("⏳ Сохраняю фото...")
    try:
        file = await bot.get_file(photo.file_id)
        await bot.download_file(file.file_path, destination=file_path)

        file_size = os.path.getsize(file_path)
        db_id = db.add_file(final_filename, final_filename, 'photo', file_path, file_size, message.from_user.id)
        db.log_operation(message.from_user.id, 'upload', db_id, f"Uploaded photo {final_filename}")

        await state.clear()
        await message.answer(
            f"✅ <b>Фото сохранено!</b>\n\n"
            f"📄 Имя: <b>{final_filename}</b>\n"
            f"📦 Размер: <b>{file_size / 1024:.1f} KB</b>",
            parse_mode="HTML",
            reply_markup=back_keyboard()
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        await state.clear()

@router.message(FileUpload.waiting_for_file, F.audio)
async def process_audio(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    file_type = data['file_type']
    if file_type != 'music':
        await message.answer(
            f"❌ Вы выбрали <b>{get_emoji(file_type)}</b>, а отправляете аудио!\n"
            f"Отправьте как документ (📎 скрепка)",
            parse_mode="HTML"
        )
        return

    audio = message.audio
    custom_name = data['file_name']
    original_name = audio.file_name or "audio.mp3"
    _, ext = os.path.splitext(original_name)
    ext = ext.lower() if ext else ".mp3"

    allowed = config.ALLOWED_EXTENSIONS['music']
    if ext not in allowed:
        await message.answer(
            f"❌ Расширение <b>{ext}</b> не разрешено!\nРазрешены: {', '.join(allowed)}",
            parse_mode="HTML"
        )
        return

    final_filename = custom_name + ext
    file_path = os.path.join(config.MUSIC_DIR, final_filename)
    counter = 1
    while os.path.exists(file_path):
        final_filename = f"{custom_name}_{counter}{ext}"
        file_path = os.path.join(config.MUSIC_DIR, final_filename)
        counter += 1

    await message.answer("⏳ Сохраняю музыку...")
    try:
        file = await bot.get_file(audio.file_id)
        await bot.download_file(file.file_path, destination=file_path)

        file_size = os.path.getsize(file_path)
        db_id = db.add_file(final_filename, original_name, 'music', file_path, file_size, message.from_user.id)
        db.log_operation(message.from_user.id, 'upload', db_id, f"Uploaded audio {final_filename}")

        await state.clear()
        await message.answer(
            f"✅ <b>Музыка сохранена!</b>\n\n"
            f"📄 Имя: <b>{final_filename}</b>\n"
            f"📦 Размер: <b>{file_size / (1024*1024):.2f} MB</b>",
            parse_mode="HTML",
            reply_markup=back_keyboard()
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        await state.clear()

@router.message(FileRename.waiting_for_new_name)
async def process_rename(message: Message, state: FSMContext):
    text = message.text.strip()
    if re.search(r'[\\/:*?"<>|]', text):
        await message.answer("❌ Имя содержит недопустимые символы! Введите другое:")
        return

    data = await state.get_data()
    file_id = data['file_id']
    file_data = data['file_data']
    old_name = file_data[1]
    file_path = file_data[4]
    file_type = file_data[3]

    _, ext = os.path.splitext(old_name)
    new_filename = text + ext
    directories = {
        'music': config.MUSIC_DIR,
        'video': config.VIDEO_DIR,
        'photo': config.PHOTO_DIR
    }
    directory = directories[file_type]
    new_path = os.path.join(directory, new_filename)

    try:
        if os.path.exists(file_path):
            os.rename(file_path, new_path)

        db.rename_file(file_id, new_filename)
        db.cursor.execute('UPDATE server SET file_path = ? WHERE id = ?', (new_path, file_id))
        db.conn.commit()
        db.log_operation(message.from_user.id, 'rename', file_id, f"Renamed: {old_name} → {new_filename}")

        await state.clear()
        await message.answer(
            f"✅ Файл переименован!\n\n"
            f"📄 Было: <b>{old_name}</b>\n"
            f"📄 Стало: <b>{new_filename}</b>",
            parse_mode="HTML",
            reply_markup=back_keyboard()
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка переименования: {e}", reply_markup=back_keyboard())
        await state.clear()

# ========== Обработка прочих сообщений ==========
@router.message(F.text)
async def handle_text(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        # Если не в состоянии FSM, предлагаем начать
        await message.answer("📱 Используйте /start для начала работы", reply_markup=back_keyboard())
    # Иначе сообщение обработается соответствующим хендлером состояния