import collections
if not hasattr(collections, "Mapping"):
    import collections.abc
    collections.Mapping = collections.abc.Mapping

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import requests
from typing import List, Optional
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Создаем FastAPI приложение
app = FastAPI()

# Модели данных для входящих запросов
class JobSearchRequest(BaseModel):
    salary: Optional[int] = None  # Сделано опциональным с значением по умолчанию None
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
    logging.info(f"Получен запрос: {request.method} {request.url}")
    try:
        body = await request.json()
        logging.info(f"Тело запроса: {body}")
    except Exception:
        logging.info("Тело запроса: отсутствует или недоступно")
    
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
    logging.info(f"Получен запрос find_jobs с данными: {request.dict()}")
    
    salary = request.salary  # Используем зарплату из запроса, если передана
    text = request.text.strip()  # Удаляем лишние пробелы из текста
    
    if request.location:
        text = f"{text} {request.location.strip()}"
    
    url = "https://api.hh.ru/vacancies"
    params = {
        "text": text,
        "per_page": 25,  # Количество вакансий на странице
    }
    
    # Если зарплата передана, добавляем ее в параметры
    if salary is not None:
        params["salary"] = salary
    
    try:
        logging.info(f"Запрос к API HH с параметрами: {params}")
        response = requests.get(url, params=params)
        response.raise_for_status()
        logging.info(f"Ответ от API HH: {response.status_code}")
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при запросе к API HH: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при получении данных с HH")
    
    vacancies_data = response.json()
    
    logging.info(f"Ответ от HH: {vacancies_data}")
    
    if "items" not in vacancies_data or not vacancies_data["items"]:
        logging.warning("Нет вакансий в ответе.")
        return []
    
    vacancies = []
    for vacancy in vacancies_data.get("items", []):
        position = vacancy.get("name")
        company = vacancy.get("employer", {}).get("name")
        location = vacancy.get("area", {}).get("name")
        
        salary = vacancy.get("salary", {})
        salary_from = salary.get("from") if salary else None
        salary_to = salary.get("to") if salary else None
        salary_currency = salary.get("currency", "RUR") if salary else "RUR"
        
        link = vacancy.get("alternate_url", "")
        
        logging.info(f"Вакансия: {position}, Компания: {company}, Город: {location}, Зарплата: {salary_from} - {salary_to} {salary_currency}, Ссылка: {link}")
        
        vacancies.append(VacancyResponse(
            position=position,
            company=company,
            location=location,
            from_salary=salary_from if salary_from is not None else 0,
            to_salary=salary_to if salary_to is not None else 0,
            currency=salary_currency,
            link=link
        ))
    
    return vacancies
