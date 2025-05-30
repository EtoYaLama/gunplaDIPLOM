from fastapi import FastAPI
from app.database import create_tables

from app.api import auth
from app.api import product
from app.api import order


''' Создание приложения FastAPI '''
app = FastAPI(
    docs_url='/',
    title='Gunpla Store API',
    description='Api для интернет магазина моделей Gunpla'
)



''' Подключение роутеров '''
app.include_router(auth.router, prefix='/auth')
app.include_router(product.router, prefix='/product')
app.include_router(order.router, prefix='/order')

# try:
#     create_tables()
#     print('yes')
# except Exception:
#     print('no')