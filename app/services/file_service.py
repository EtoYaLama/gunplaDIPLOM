import os
import uuid
from typing import List
from fastapi import UploadFile
from PIL import Image
import io



class FileService:
    """Инициализация класса"""
    def __init__(self):
        self.upload_dir = 'app/static/uploads/products'
        self.allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        self.max_file_size = 5 * 1024 * 1024  # 5MB
        self.image_sizes = {
            'thumbnail': (300, 300),
            'medium': (600, 600),
            'large': (1200, 1200)
        }

        ''' Создаем директории если их нет '''
        os.makedirs(self.upload_dir, exist_ok=True)
        for size in self.image_sizes.keys():
            os.makedirs(f"{self.upload_dir}/{size}", exist_ok=True)


    ''' Сохраняет изображения товара и возвращает пути к файлам '''
    async def save_product_images(self, files: List[UploadFile]) -> List[str]:
        if not files:
            return []

        saved_files = []

        for file in files:
            ''' Валидация файла '''
            if not self._validate_file(file):
                continue

            ''' Генерируем уникальное имя файла '''
            file_extension = os.path.splitext(file.filename)[1].lower()
            unique_filename = f"{str(uuid.uuid4())}{file_extension}"

            try:
                ''' Читаем файл '''
                content = await file.read()

                ''' Сохраняем оригинал и создаем разные размеры '''
                await self._save_with_resize(content, unique_filename)
                saved_files.append(unique_filename)

            except Exception as e:
                print(f"Ошибка при сохранении файла {file.filename}: {e}")
                continue
        return saved_files


    ''' Валидирует загружаемый файл '''
    def _validate_file(self, file: UploadFile) -> bool:
        if not file.filename:
            return False

        ''' Проверяем расширение '''
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in self.allowed_extensions:
            return False

        return True


    ''' Сохраняет файл в разных размерах '''
    async def _save_with_resize(self, content: bytes, filename: str) -> dict:
        file_paths = {}

        ''' Открываем изображение '''
        image = Image.open(io.BytesIO(content))

        ''' Конвертируем в RGB если нужно '''
        if image.mode != 'RGB':
            image = image.convert('RGB')

        ''' Сохраняем в разных размерах '''
        for size_name, (width, height) in self.image_sizes.items():
            ''' Ресайзим с сохранением пропорций '''
            resized_image = self._resize_image(image, width, height)

            ''' Путь к файлу '''
            file_path = f"{self.upload_dir}/{size_name}/{filename}"

            ''' Сохраняем '''
            resized_image.save(file_path, "JPEG", quality=85, optimize=True)
            file_paths[size_name] = f"/static/uploads/products/{size_name}/{filename}"

        return file_paths


    ''' Изменяет размер изображения с сохранением пропорций '''
    @staticmethod
    def _resize_image(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
        """ Вычисляем новые размеры """
        width, height = image.size
        ratio = min(max_width / width, max_height / height)

        if ratio < 1:
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        return image


    ''' Удаляет изображения товара '''
    def delete_product_images(self, filenames: List[str]):
        for filename in filenames:
            for size_name in self.image_sizes.keys():
                file_path = f"{self.upload_dir}/{size_name}/{filename}"
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"Ошибка при удалении файла {file_path}: {e}")


    ''' Возвращает URL изображения '''
    @staticmethod
    def get_image_url(filename: str, size: str = "medium") -> str:
        if not filename:
            return "/static/images/no-image.jpg"  # placeholder

        return f"/static/uploads/products/{size}/{filename}"



file_service = FileService()