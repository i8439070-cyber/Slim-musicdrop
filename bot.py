from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
from pathlib import Path

# --- Конфігурація ---
TELEGRAM_TOKEN = "7349204352:AAH_Xsu07bSXx3Kzy1le39xDgmEM2whWoCw"
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# --- Команди бота ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Надсилання локальної картинки
    with open("images/background.jpg", "rb") as photo:
        await update.message.reply_photo(
            photo=photo,
            caption="🎵 Привіт! Напиши назву треку або посилання з YouTube Music, щоб отримати аудіо."
        )

# --- Основна логіка пошуку та завантаження ---
async def search_youtube_music(update: Update, context: ContextTypes.DEFAULT_TYPE, dlp=None):
    query = update.message.text.strip()
    if not query:
        await update.message.reply_text("❌ Вкажи запит або посилання.")
        return

    await update.message.reply_text("⏳ Шукаю і завантажую аудіо з YouTube Music...")

    # --- Налаштування yt_dlp ---
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(DOWNLOAD_DIR / "%(id)s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "keepvideo": False,
        "quiet": True,
        "max_filesize": 1000 * 1024 * 1024,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    try:
        # --- Формування запиту для пошуку ---
        if not query.startswith("http"):
            query = f"ytsearch3:{query}"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(query, download=True)

            # --- Якщо знайдено декілька треків ---
            if 'entries' in info_dict and info_dict['entries']:
                entries = info_dict['entries']
                for entry in entries:
                    file_path = None
                    if 'requested_downloads' in entry:
                        file_path = entry['requested_downloads'][0]['filepath']
                    elif 'filepath' in entry:
                        file_path = entry['filepath']
                    elif '_filename' in entry:
                        file_path = str(Path(entry['_filename']).with_suffix('.mp3'))

                    # --- Перевірка та надсилання аудіо ---
                    if file_path and Path(file_path).exists():
                        if Path(file_path).stat().st_size > 50 * 1024 * 1024:
                            await update.message.reply_text(
                                "❌ Файл занадто великий для Telegram (>50 МБ).\n"
                                "🔗 Спробуйте скачати напряму: [Відкрити файл]({url})",
                                parse_mode="Markdown",
                                disable_web_page_preview=True
                            )
                            Path(file_path).unlink(missing_ok=True)
                            continue

                        # --- Надсилання обкладинки ---
                        thumbnail_url = entry.get('thumbnail')
                        if thumbnail_url:
                            try:
                                await update.message.reply_photo(
                                    photo=thumbnail_url,
                                    caption=f"{entry.get('title', 'Audio')}\nВиконавець: {entry.get('uploader', '')}"
                                )
                            except Exception:
                                pass

                        # --- Надсилання аудіо ---
                        with open(file_path, "rb") as audio_file:
                            await update.message.reply_audio(
                                audio=audio_file,
                                title=entry.get('title', 'Audio'),
                                performer=entry.get('uploader', None)
                            )
                        Path(file_path).unlink(missing_ok=True)
                    else:
                        await update.message.reply_text("❌ Не вдалося знайти аудіофайл.")

                    # --- Додаткова інформація ---
                    info_text = (
                        f"🎵 <b>{entry.get('title', 'Audio')}</b>\n"
                        f"👤 Виконавець: {entry.get('uploader', '')}\n"
                        f"⏱️ Тривалість: {entry.get('duration', '')} сек\n"
                        f"👁️ Переглядів: {entry.get('view_count', '')}\n"
                        f"👍 Лайків: {entry.get('like_count', '')}\n"
                        f"🎶 Жанр: {entry.get('genre', '')}\n"
                        f"📀 Альбом: {entry.get('album', '')}\n"
                        f"📅 Рік випуску: {entry.get('release_year', '')}\n"
                        f"📝 Опис: {entry.get('description', '')[:200]}..."
                    )
                    await update.message.reply_text(info_text, parse_mode="HTML")

                    yt_url = entry.get('webpage_url', '')
                    if yt_url:
                        keyboard = [[InlineKeyboardButton("Відкрити на YouTube ▶️", url=yt_url)]]
                        await update.message.reply_text("🔗 Перейти до відео:", reply_markup=InlineKeyboardMarkup(keyboard))

            # --- Якщо це одиночний трек ---
            elif 'filepath' in info_dict:
                file_path = info_dict['filepath']
            elif '_filename' in info_dict:
                file_path = str(Path(info_dict['_filename']).with_suffix('.mp3'))

            if file_path and Path(file_path).exists():
                if Path(file_path).stat().st_size > 50 * 1024 * 1024:
                    await update.message.reply_text(
                        "❌ Файл занадто великий для Telegram (>50 МБ).\n"
                        "🔗 Спробуйте скачати напряму: [Відкрити файл]({url})",
                        parse_mode="Markdown",
                        disable_web_page_preview=True
                    )
                    Path(file_path).unlink(missing_ok=True)
                    return

                # --- Надсилання обкладинки ---
                thumbnail_url = info_dict.get('thumbnail')
                if not thumbnail_url and 'entries' in info_dict and info_dict['entries']:
                    entry = info_dict['entries'][0]
                    thumbnail_url = entry.get('thumbnail')

                if thumbnail_url:
                    try:
                        await update.message.reply_photo(
                            photo=thumbnail_url,
                            caption=f"{info_dict.get('title', 'Audio')}\nВиконавець: {info_dict.get('uploader', '')}"
                        )
                    except Exception:
                        pass

                # --- Надсилання аудіо ---
                with open(file_path, "rb") as audio_file:
                    await update.message.reply_audio(
                        audio=audio_file,
                        title=info_dict.get('title', 'Audio'),
                        performer=info_dict.get('uploader', None)
                    )
                Path(file_path).unlink(missing_ok=True)
            else:
                await update.message.reply_text("❌ Не вдалося знайти аудіофайл.")
            
            # --- Додаткова інформація про трек ---
            info_text = (
                f"🎵 <b>{info_dict.get('title', 'Audio')}</b>\n"
                f"👤 Виконавець: {info_dict.get('uploader', '')}\n"
                f"⏱️ Тривалість: {info_dict.get('duration', '')} сек\n"
                f"👁️ Переглядів: {info_dict.get('view_count', '')}\n"
                f"👍 Лайків: {info_dict.get('like_count', '')}\n"
                f"🎶 Жанр: {info_dict.get('genre', '')}\n"
                f"📀 Альбом: {info_dict.get('album', '')}\n"
                f"📅 Рік випуску: {info_dict.get('release_year', '')}\n"
                f"📝 Опис: {info_dict.get('description', '')[:200]}..."
            )
            await update.message.reply_text(info_text, parse_mode="HTML")

            yt_url = info_dict.get('webpage_url', '')
            if yt_url:
                keyboard = [[InlineKeyboardButton("Відкрити на YouTube ▶️", url=yt_url)]]
                await update.message.reply_text("🔗 Перейти до відео:", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        # --- Обробка помилок ---
        pass

# --- Запуск бота ---
app = Application.builder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_youtube_music))
app.run_polling()
