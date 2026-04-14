"""
Синхронизация файлов с диска и базой данных.
Добавляет в БД файлы, которые есть на диске, но нет в базе.
Удаляет из БД записи о файлах, которых нет на диске.
"""

import os
import config
from database import db


def sync_directory(directory, file_type):
    """Синхронизировать папку с базой данных"""
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        return 0

    # Получить файлы из БД
    db_files = db.get_files_by_type(file_type)
    db_filenames = {f[1] for f in db_files}  # set из filename

    # Получить файлы с диска
    disk_files = set()
    for f in os.listdir(directory):
        filepath = os.path.join(directory, f)
        if os.path.isfile(filepath):
            disk_files.add(f)

    added = 0

    # Добавить в БД файлы, которые есть на диске, но нет в базе
    for filename in disk_files:
        filepath = os.path.join(directory, filename)

        # Проверить расширение
        _, ext = os.path.splitext(filename)
        ext = ext.lower()

        allowed = config.ALLOWED_EXTENSIONS.get(file_type, [])
        if ext not in allowed:
            continue

        if filename not in db_filenames:
            file_size = os.path.getsize(filepath)
            db.add_file(filename, filename, file_type, filepath, file_size, None)
            print(f"  ✅ Добавлен в БД: {filename}")
            added += 1

    # Удалить из БД записи, файлы которых удалены с диска
    for db_file in db_files:
        file_id = db_file[0]
        filename = db_file[1]
        if filename not in disk_files:
            db.delete_file(file_id)
            print(f"  🗑️ Удалён из БД (нет на диске): {filename}")

    return added


def main():
    print("🔄 Синхронизация файлов с базой данных...\n")

    total = 0

    print("🎵 Музыка:")
    total += sync_directory(config.MUSIC_DIR, 'music')

    print("\n🎬 Видео:")
    total += sync_directory(config.VIDEO_DIR, 'video')

    print("\n📷 Фото:")
    total += sync_directory(config.PHOTO_DIR, 'photo')

    print(f"\n✅ Синхронизация завершена! Добавлено файлов: {total}")


if __name__ == '__main__':
    main()