import collections
if not hasattr(collections, "Mapping"):
    import collections.abc
    collections.Mapping = collections.abc.Mapping

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import requests
from typing import List, Optional
import logging
from experta import Fact, KnowledgeEngine, Rule, MATCH, TEST

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Создаем FastAPI приложение
app = FastAPI()

# Модели данных для входящих запросов
class JobSearchRequest(BaseModel):
    salary: Optional[int] = None  # Делаем параметр зарплаты опциональным
    text: str  # Текстовый запрос для поиска по ключевым словам (например, должность)

# Модели данных для вакансий
class VacancyResponse(BaseModel):
    position: str
    company: str
    location: str
    from_salary: int
    to_salary: int
    currency: str
    link: str  # Добавляем ссылку на вакансию

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

# Факты и движок знаний
class User(Fact):
    salaryPrefer: Optional[int]

class Vacancy(Fact):
    position: str
    company: str
    location: str
    from_salary: int
    to_salary: int

class InputLocation(Fact):
    inputLocation: str

class AnswerVacancies(Fact):
    position: str
    company: str
    location: str
    from_salary: int
    to_salary: int

class VacancyEngine(KnowledgeEngine):
    @Rule(
        User(salaryPrefer=MATCH.salaryPrefer),
        InputLocation(inputLocation=MATCH.inputLocation),
        Vacancy(
            position=MATCH.position,
            company=MATCH.company,
            location=MATCH.location,
            from_salary=MATCH.from_salary,
            to_salary=MATCH.to_salary,
        ),
        TEST(lambda salaryPrefer, from_salary, to_salary, inputLocation, location:
             (salaryPrefer is None or (salaryPrefer >= from_salary and salaryPrefer <= to_salary)) and location == inputLocation)
    )
    def job_matching_by_salary_and_location(self, salaryPrefer, inputLocation, position, company, location, from_salary, to_salary):
        """Подбор вакансий по зарплате и местоположению одновременно."""
        self.declare(
            AnswerVacancies(
                position=position,
                company=company,
                location=location,
                from_salary=from_salary,
                to_salary=to_salary,
            )
        )

# Эндпоинт для поиска вакансий
@app.post("/find_jobs", response_model=List[VacancyResponse])
async def find_jobs(request: JobSearchRequest):
    logging.info(f"Получен запрос find_jobs с данными: {request.dict()}")
    
    salary = request.salary  # Используем зарплату из запроса, если она указана
    text = request.text  # Используем текстовый запрос для поиска
    
    url = "https://api.hh.ru/vacancies"
    params = {
        "text": text,  # Передаем текст для поиска по вакансиям
        "salary": salary if salary is not None else None,  # Указываем зарплату, если передана
        "per_page": 25,  # Количество вакансий на странице
    }
    
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
    engine = VacancyEngine()
    engine.reset()

    for vacancy in vacancies_data.get("items", []):
        position = vacancy.get("name")
        company = vacancy.get("employer", {}).get("name")
        location = vacancy.get("area", {}).get("name")
        salary_data = vacancy.get("salary", {})
        salary_from = salary_data.get("from") if salary_data else None
        salary_to = salary_data.get("to") if salary_data else None
        
        engine.declare(Vacancy(
            position=position,
            company=company,
            location=location,
            from_salary=salary_from if salary_from is not None else 0,
            to_salary=salary_to if salary_to is not None else 0,
        ))

    engine.declare(User(salaryPrefer=salary))
    engine.declare(InputLocation(inputLocation="Москва"))  # Для примера: фиксированное значение

    engine.run()

    for fact in engine.facts.values():
        if isinstance(fact, AnswerVacancies):
            vacancies.append(VacancyResponse(
                position=fact["position"],
                company=fact["company"],
                location=fact["location"],
                from_salary=fact["from_salary"],
                to_salary=fact["to_salary"],
                currency="RUR",
                link=""  # Нет данных о ссылке в данном примере
            ))
    
    return vacancies
