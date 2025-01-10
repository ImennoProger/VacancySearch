import collections
if not hasattr(collections, "Mapping"):
    import collections.abc
    collections.Mapping = collections.abc.Mapping

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import requests
from typing import List
import logging
from experta import Fact, KnowledgeEngine, Rule, MATCH, TEST

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Создаем FastAPI приложение
app = FastAPI()

# Модели данных для входящих запросов
class JobSearchRequest(BaseModel):
    salary: int  # Ожидаем зарплату как число
    text: str  # Текстовый запрос для поиска по ключевым словам (например, должность)
    location: str  # Добавляем местоположение пользователя

# Модели данных для вакансий
class VacancyResponse(BaseModel):
    position: str
    company: str
    location: str
    from_salary: int
    to_salary: int
    currency: str
    link: str  # Добавляем ссылку на вакансию

# Определение фактов
class User(Fact):
    """Карточка пользователя."""
    salaryPrefer: int

class Vacancy(Fact):
    """Атрибуты вакансии."""
    position: str
    company: str
    location: str
    experience: str
    url: str
    from_salary: int
    to_salary: int

class InputLocation(Fact):
    """Ввод пользователя о местоположении."""
    inputLocation: str

class AnswerVacancies(Fact):
    """Ответ: вакансии, которые соответствуют зарплате и местоположению."""
    position: str
    company: str
    location: str
    experience: str
    url: str
    from_salary: int
    to_salary: int

# Движок правил
class VacancyEngine(KnowledgeEngine):
    @Rule(
        User(salaryPrefer=MATCH.salaryPrefer),
        InputLocation(inputLocation=MATCH.inputLocation),
        Vacancy(
            position=MATCH.position,
            company=MATCH.company,
            location=MATCH.location,
            experience=MATCH.experience,
            url=MATCH.url,
            from_salary=MATCH.from_salary,
            to_salary=MATCH.to_salary,
        ),
        TEST(lambda salaryPrefer, from_salary, to_salary, inputLocation, location:
             (from_salary or 0) <= salaryPrefer <= (to_salary or float('inf')) and location == inputLocation)
    )
    def job_matching_by_salary_and_location(self, salaryPrefer, inputLocation, position, company, location, experience, url, from_salary, to_salary):
        """Подбор вакансий по зарплате и местоположению одновременно."""
        self.declare(
            AnswerVacancies(
                position=position,
                company=company,
                location=location,
                experience=experience,
                url=url,
                from_salary=from_salary or 0,
                to_salary=to_salary or 0,
            )
        )

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

# Эндпоинт для поиска вакансий
@app.post("/find_jobs", response_model=List[VacancyResponse])
async def find_jobs(request: JobSearchRequest):
    """Обработчик поиска вакансий по зарплате, ключевому слову и местоположению."""
    salary = request.salary
    text = request.text
    location = request.location

    # Запрашиваем вакансии через API HH
    url = "https://api.hh.ru/vacancies"
    params = {
        "text": text,
        "salary": salary,
        "per_page": 25,
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при запросе к API HH: {e}")
    
    vacancies_data = response.json()
    if "items" not in vacancies_data or not vacancies_data["items"]:
        return []  # Если вакансий нет в ответе, возвращаем пустой список

    # Инициализируем движок правил
    engine = VacancyEngine()
    engine.reset()

    # Добавляем данные пользователя и местоположение
    engine.declare(User(salaryPrefer=salary))
    engine.declare(InputLocation(inputLocation=location))

    # Загружаем вакансии в движок
    for vacancy in vacancies_data["items"]:
        position = vacancy.get("name", "")
        company = vacancy.get("employer", {}).get("name", "")
        vacancy_location = vacancy.get("area", {}).get("name", "")
        experience = vacancy.get("snippet", {}).get("requirement", "Не указано")
        url = vacancy.get("alternate_url", "")
        salary_data = vacancy.get("salary", {})
        from_salary = salary_data.get("from")
        to_salary = salary_data.get("to")
        
        engine.declare(Vacancy(
            position=position,
            company=company,
            location=vacancy_location,
            experience=experience,
            url=url,
            from_salary=from_salary,
            to_salary=to_salary,
        ))

    # Запускаем движок правил
    engine.run()

    # Собираем подходящие вакансии
    results = []
    for fact in engine.facts.values():
        if isinstance(fact, AnswerVacancies):
            results.append({
                "position": fact["position"],
                "company": fact["company"],
                "location": fact["location"],
                "from_salary": fact["from_salary"],
                "to_salary": fact["to_salary"],
                "currency": "RUR",  # Можно заменить на фактическую валюту, если доступна
                "link": fact["url"],
            })

    return results
