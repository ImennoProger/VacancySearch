import collections
if not hasattr(collections, "Mapping"):
    import collections.abc
    collections.Mapping = collections.abc.Mapping

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import requests
from typing import List
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Создаем FastAPI приложение
app = FastAPI()

# Модели данных для входящих запросов
class JobSearchRequest(BaseModel):
    salary: int  # Ожидаем зарплату как число
    text: str  # Текстовый запрос для поиска по ключевым словам (например, должность)
    location: str = None  # Локация как необязательное поле

# Модели данных для вакансий
class VacancyResponse(BaseModel):
    position: str
    company: str
    location: str
    from_salary: int
    to_salary: int
    currency: str
    link: str  # Ссылка на вакансию

# Логирование всех запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Миддлвэр для логирования всех входящих запросов."""
    # Логируем метод и URL запроса
    logging.info(f"Получен запрос: {request.method} {request.url}")
    try:
        # Логируем тело запроса, если оно доступно
        body = await request.json()
        logging.info(f"Тело запроса: {body}")
    except Exception:
        logging.info("Тело запроса: отсутствует или недоступно")
    
    # Передаем запрос дальше
    response = await call_next(request)
    return response

# Логирование ошибок валидации
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обработчик ошибок валидации для логирования полного запроса."""
    logging.error(f"Ошибка валидации запроса: {exc}")
    try:
        body = await request.json()
        logging.error(f"Тело запроса: {body}")
    except Exception:
        logging.error("Тело запроса отсутствует или не может быть прочитано.")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(exc.body)},
    )

# Эндпоинт для поиска вакансий
@app.post("/find_jobs", response_model=List[VacancyResponse])
async def find_jobs(request: JobSearchRequest):
    """Обработчик поиска вакансий по зарплате и ключевому слову (text)."""
    # Логируем структуру запроса
    logging.info(f"Получен запрос find_jobs с данными: {request.dict()}")
    
    salary = request.salary  # Используем зарплату из запроса
    text = request.text.strip()  # Удаляем лишние пробелы из текста
    
    # Добавляем location к text, если оно передано
    if request.location:
        text = f"{text} {request.location.strip()}"
    
    url = "https://api.hh.ru/vacancies"
    params = {
        "text": text,  # Передаем текст для поиска по вакансиям
        "salary": salary,  # Указываем желаемую зарплату
        "per_page": 25,  # Количество вакансий на странице
    }
    
    try:
        logging.info(f"Запрос к API HH с параметрами: {params}")
        response = requests.get(url, params=params)
        
        # Проверка на успешный статус ответа
        response.raise_for_status()
        logging.info(f"Ответ от API HH: {response.status_code}")
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при запросе к API HH: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при получении данных с HH")
    
    vacancies_data = response.json()  # Получаем данные из ответа API
    
    # Логируем, что пришло в ответе
    logging.info(f"Ответ от HH: {vacancies_data}")
    
    if "items" not in vacancies_data or not vacancies_data["items"]:
        logging.warning("Нет вакансий в ответе.")
        return []  # Если вакансий нет в ответе, возвращаем пустой список
    
    # Обрабатываем данные, чтобы вернуть только нужные поля
    vacancies = []
    for vacancy in vacancies_data.get("items", []):
        position = vacancy.get("name")
        company = vacancy.get("employer", {}).get("name")
        location = vacancy.get("area", {}).get("name")
        
        # Проверка на наличие поля salary
        salary = vacancy.get("salary", {})
        salary_from = salary.get("from") if salary else None
        salary_to = salary.get("to") if salary else None
        salary_currency = salary.get("currency", "RUR") if salary else "RUR"
        
        # Получаем ссылку на вакансию
        link = vacancy.get("alternate_url", "")
        
        # Логируем данные о вакансии
        logging.info(f"Вакансия: {position}, Компания: {company}, Город: {location}, Зарплата: {salary_from} - {salary_to} {salary_currency}, Ссылка: {link}")
        
        # Формируем объект вакансии для ответа
        vacancies.append(VacancyResponse(
            position=position,
            company=company,
            location=location,
            from_salary=salary_from if salary_from is not None else 0,  # Если не указана, ставим 0
            to_salary=salary_to if salary_to is not None else 0,  # Если не указана, ставим 0
            currency=salary_currency,
            link=link  # Добавляем ссылку на вакансию
        ))
    
    return vacancies
