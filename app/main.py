from fastapi import FastAPI

from app.api import auth


''' Создание приложения FastAPI '''
app = FastAPI(
    docs_url='/',
    title='Gunpla Store API',
    description='Api для интернет магазина моделей Gunpla'
)



''' Подключение роутеров '''
app.include_router(auth.router, prefix="/auth")

