import collections
if not hasattr(collections, "Mapping"):
    import collections.abc
    collections.Mapping = collections.abc.Mapping

from fastapi import FastAPI
from pydantic import BaseModel
from experta import Fact, KnowledgeEngine, Rule, MATCH, TEST
from typing import List

# Создаем FastAPI приложение
app = FastAPI()

# Модели данных для входящих запросов
class JobSearchRequest(BaseModel):
    salary: int
    location: str

# Модели данных для вакансий
class VacancyResponse(BaseModel):
    position: str
    company: str
    location: str
    experience: str
    url: str
    from_salary: int
    to_salary: int

# Определение фактов (шаблоны из templates.CLP)
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

# Определение движка знаний
class VacancyEngine(KnowledgeEngine):

    def load_vacancies(self):
        """Загрузка данных о вакансиях"""
        self.declare(Vacancy(
            position="Веб-программист",
            company="Центр Веб-решений",
            location="Иркутск",
            experience="Нет опыта",
            url="https://hh.ru/vacancy/91451214",
            from_salary=60000,
            to_salary=120000
        ))
        self.declare(Vacancy(
            position="PHP-разработчик / Веб-разработчик",
            company="Верный Код",
            location="Иркутск",
            experience="От 1 года до 3 лет",
            url="https://hh.ru/vacancy/91724935",
            from_salary=80000,
            to_salary=110000
        ))
        self.declare(Vacancy(
            position="PHP программист в веб-студию (1C-Битрикс, OpenCart)",
            company="Jobers",
            location="Иркутск",
            experience="От 1 года до 3 лет",
            url="https://hh.ru/vacancy/91197688",
            from_salary=30000,
            to_salary=80000
        ))
        self.declare(Vacancy(
            position="Junior Golang developer",
            company="Lamoda Tech",
            location="Москва",
            experience="От 1 года до 3 лет",
            url="https://hh.ru/vacancy/91659394",
            from_salary=40000,
            to_salary=160000
        ))
        self.declare(Vacancy(
            position="Программист 1C",
            company="Саппорт Ю",
            location="Иркутск",
            experience="От 1 года до 3 лет",
            url="https://hh.ru/vacancy/91595629",
            from_salary=40000,
            to_salary=160000
        ))
        self.declare(Vacancy(
            position="Официант Рестобар 'Kiss'",
            company="Семья",
            location="Иркутск",
            experience="Нет опыта",
            url="https://hh.ru/vacancy/91075809",
            from_salary=50000,
            to_salary=80000
        ))
        self.declare(Vacancy(
            position="Fullstack-разработчик",
            company="Бондаренко Анна Евгеньевна",
            location="Иркутск",
            experience="От 1 года до 3 лет",
            url="https://hh.ru/vacancy/91894240",
            from_salary=90000,
            to_salary=200000
        ))

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
             salaryPrefer >= from_salary and salaryPrefer <= to_salary and location == inputLocation)
    )
    def job_matching_by_salary_and_location(self, salaryPrefer, inputLocation, position, company, location, experience, url, from_salary, to_salary):
        """Подбор вакансий по зарплате и местоположению одновременно."""
        print(f"Зарплата пользователя: {salaryPrefer}, диапазон вакансии: {from_salary} - {to_salary}")
        print(f"Сработало правило: job_matching_by_salary_and_location для вакансии {position} ({company})")
        self.declare(
            AnswerVacancies(
                position=position,
                company=company,
                location=location,
                experience=experience,
                url=url,
                from_salary=from_salary,
                to_salary=to_salary,
            )
        )


# Эндпоинт для поиска вакансий
@app.post("/find_jobs", response_model=List[VacancyResponse])
async def find_jobs(request: JobSearchRequest):
    """Обработчик поиска вакансий по зарплате и местоположению."""
    salary = request.salary
    location = request.location
    
    engine = VacancyEngine()
    engine.reset()

    # Добавляем данные пользователя и местоположение
    engine.declare(User(salaryPrefer=salary))
    engine.declare(InputLocation(inputLocation=location))
    
    engine.load_vacancies()  # Загрузка вакансий
    engine.run()  # Запуск движка знаний

    results = []
    for fact in engine.facts.values():
        if isinstance(fact, AnswerVacancies):
            results.append(VacancyResponse(
                position=fact['position'],
                company=fact['company'],
                location=fact['location'],
                experience=fact['experience'],
                url=fact['url'],
                from_salary=fact['from_salary'],
                to_salary=fact['to_salary']
            ))
    
    return results


# Запуск FastAPI приложения через Uvicorn
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
