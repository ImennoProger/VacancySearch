import collections
if not hasattr(collections, "Mapping"):
    import collections.abc
    collections.Mapping = collections.abc.Mapping

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List
import logging
from experta import KnowledgeEngine, Fact, Rule, MATCH

# Инициализация приложения FastAPI
app = FastAPI()

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

# Данные о растениях
plants = [
    {"name": "Роза", "color": "красный", "size": "маленький", "type": "цветок", "link": "-"},
    {"name": "Либерти", "color": "зеленый", "size": "средний", "type": "кустарник", "link": "https://elovpark.ru/product/%d1%85%d0%be%d1%81%d1%82%d0%b0-%d0%bb%d0%b8%d0%b1%d0%b5%d1%80%d1%82%d0%b8/"},
    {"name": "Вербейник", "color": "желтый", "size": "средний", "type": "цветок", "link": "https://elovpark.ru/product/%d0%b2%d0%b5%d1%80%d0%b1%d0%b5%d0%b9%d0%bd%d0%b8%d0%ba-%d1%82%d0%be%d1%87%d0%b5%d1%87%d0%bd%d1%8b%d0%b9/"},
    {"name": "Тюльпан", "color": "желтый", "size": "средний", "type": "цветок", "link": "-"},
    {"name": "Барбарис", "color": "красный", "size": "большой", "type": "кустарник", "link": "https://elovpark.ru/product/%d0%b1%d0%b0%d1%80%d0%b1%d0%b0%d1%80%d0%b8%d1%81-%d1%82%d1%83%d0%bd%d0%b1%d0%b5%d1%80%d0%b3%d0%b0-%d0%b0%d1%82%d1%80%d0%be%d0%bf%d1%83%d1%80%d0%bf%d1%83%d1%80%d0%b5%d0%b0/"},
    {"name": "Бадан", "color": "розовый", "size": "маленький", "type": "цветок", "link": "https://elovpark.ru/product/%d0%b1%d0%b0%d0%b4%d0%b0%d0%bd-%d1%82%d0%be%d0%bb%d1%81%d1%82%d0%be%d0%bb%d0%b8%d%d0%b8%d1%81%d1%82%d0%bd%d1%8b%d0%b9/"},
    {"name": "Кактус", "color": "зеленый", "size": "маленький", "type": "цветок", "link": "-"},
    {"name": "Орхидея", "color": "белый", "size": "маленький", "type": "цветок", "link": "-"},
    {"name": "Медуница", "color": "синий", "size": "маленький", "type": "цветок", "link": "https://elovpark.ru/product/%d0%bc%d0%b5%d0%b4%d1%83%d0%bd%d0%b8%d1%86%d0%b0-%d1%81%d0%b0%d1%85%d0%b0%d1%80%d0%bd%d0%b0%d1%8f-%d0%bc%d0%b8%d1%81%d1%81%d0%b8%d1%81-%d0%bc%d1%83%d0%bd/"},
    {"name": "Пион", "color": "красный", "size": "маленький", "type": "цветок", "link": "https://elovpark.ru/product/%d0%bf%d0%b8%d0%be%d0%bd-%d1%82%d0%be%d0%bd%d0%ba%d0%be%d0%bb%d0%b8%d1%81%d1%82%d0%bd%d1%8b%d0%b9/"},
    {"name": "Ирис Вайт Ледис", "color": "белый", "size": "средний", "type": "цветок", "link": "https://elovpark.ru/product/%d0%b8%d1%80%d0%b8%d1%81-%d0%b2%d0%b0%d0%b9%d1%82-%d0%bb%d0%b5%d0%b4%d0%b8%d1%81/"},
    {"name": "Астра", "color": "красный", "size": "средний", "type": "цветок", "link": "-"},
    {"name": "Бегония", "color": "розовый", "size": "маленький", "type": "цветок", "link": "-"},
    {"name": "Каллы", "color": "белый", "size": "средний", "type": "цветок", "link": "-"},
    {"name": "Пальма", "color": "зеленый", "size": "большой", "type": "дерево", "link": "-"},
    {"name": "Нарцисс", "color": "желтый", "size": "маленький", "type": "цветок", "link": "-"},
    {"name": "Фиалка", "color": "синий", "size": "маленький", "type": "цветок", "link": "-"},
    {"name": "Гладиолус", "color": "красный", "size": "большой", "type": "цветок", "link": "-"},
    {"name": "Мирт", "color": "зеленый", "size": "маленький", "type": "цветок", "link": "-"},
    {"name": "Цинерария", "color": "синий", "size": "средний", "type": "цветок", "link": "-"},
    {"name": "Клематис", "color": "белый", "size": "большой", "type": "цветок", "link": "-"},
    {"name": "Лаванда", "color": "синий", "size": "средний", "type": "цветок", "link": "-"}
]

class PlantQuery(BaseModel):
    color: str
    size: str
    type: str

class PlantFact(Fact):
    """Факт, описывающий растение."""
    name = ""
    color = ""
    size = ""
    type = ""
    link = ""

class PlantEngine(KnowledgeEngine):
    def __init__(self, query):
        super().__init__()
        self.query = query
        self.results = []

    def add_facts(self):
        """Добавляем факты о растениях."""
        for plant in plants:
            self.declare(PlantFact(
                name=plant["name"],
                color=plant["color"],
                size=plant["size"],
                type=plant["type"],
                link=plant["link"]
            ))

    @Rule(PlantFact(color=MATCH.color, size=MATCH.size, type=MATCH.type),
          salience=1)
    def match_plant(self, color, size, type, name, link):
        """Правило для нахождения подходящего растения."""
        if (color == self.query.color and
                size == self.query.size and
                type == self.query.type):
            self.results.append({"name": name, "link": link})

@app.post("/find_plants")
async def find_plants(query: PlantQuery, request: Request):
    """Эндпоинт для поиска растений по параметрам с использованием experta."""
    # Логирование входящего запроса
    logger.info(f"Получен запрос от {request.client.host}: {query}")

    # Инициализация экспертной системы
    plant_engine = PlantEngine(query)

    # Добавление фактов и запуск правил
    plant_engine.reset()
    plant_engine.add_facts()
    plant_engine.run()

    # Формирование ответа
    if not plant_engine.results:
        raise HTTPException(status_code=404, detail="Растения не найдены")

    return {"results": plant_engine.results}
