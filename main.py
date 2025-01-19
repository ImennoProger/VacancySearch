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


# Логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Инициализация FastAPI
app = FastAPI()

# Модели запросов и ответов
class FlightSearchRequest(BaseModel):
    origin: str
    destination: str
    departure_at: str
    return_at: str = None  # Опционально
    one_way: bool = True
    currency: str = "rub"
    limit: int = 30
    sorting: str = "price"

class FlightResponse(BaseModel):
    price: float
    link: str

# Факты и движок знаний
class Flight(Fact):
    origin: str
    destination: str
    price: float
    link: str

class FlightCriteria(Fact):
    origin: str
    destination: str

class MatchedFlight(Fact):
    origin: str
    destination: str
    price: float
    link: str

class FlightEngine(KnowledgeEngine):
    @Rule(
        Flight(origin=MATCH.origin, destination=MATCH.destination, price=MATCH.price, link=MATCH.link),
        FlightCriteria(origin=MATCH.origin, destination=MATCH.destination)
    )
    def match_flight(self, origin, destination, price, link):
        self.declare(MatchedFlight(origin=origin, destination=destination, price=price, link=link))

# Логирование всех запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logging.info(f"Получен запрос: {request.method} {request.url}")
    try:
        body = await request.json()
        logging.info(f"Тело запроса: {body}")
    except Exception:
        logging.info("Тело запроса отсутствует или недоступно")
    response = await call_next(request)
    return response

# Эндпоинт поиска авиабилетов
@app.post("/search_flights", response_model=List[FlightResponse])
async def search_flights(request: FlightSearchRequest):
    token = "74d50d2720af4296189110fe2639ae75"
    api_url = (
        f"https://api.travelpayouts.com/aviasales/v3/prices_for_dates?"
        f"origin={request.origin}&destination={request.destination}&currency={request.currency}&limit={request.limit}"
        f"&sorting={request.sorting}&one_way={str(request.one_way).lower()}"
        f"{'&departure_at=' + request.departure_at if request.departure_at else ''}"
        f"{'&return_at=' + request.return_at if request.return_at else ''}"
        f"&token={token}"
    )

    try:
        logging.info(f"Запрос к API Travelpayouts: {api_url}")
        response = requests.get(api_url)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Ошибка при вызове API: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при вызове API")

    flights_data = response.json()
    if "data" not in flights_data or not flights_data["data"]:
        logging.warning("Нет доступных билетов.")
        return []

    # Инициализация движка знаний
    engine = FlightEngine()
    engine.reset()

    # Добавление данных в движок знаний
    for flight in flights_data["data"]:
        engine.declare(Flight(
            origin=request.origin,
            destination=request.destination,
            price=flight["price"],
            link=f"https://www.aviasales.ru/{flight['link']}"
        ))

    # Задание критериев поиска
    engine.declare(FlightCriteria(origin=request.origin, destination=request.destination))
    engine.run()

    # Сбор данных из движка знаний
    matched_flights = []
    for fact in engine.facts.values():
        if isinstance(fact, MatchedFlight):
            matched_flights.append(FlightResponse(price=fact["price"], link=fact["link"]))

    return matched_flights
