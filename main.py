import collections
if not hasattr(collections, "Mapping"):
    import collections.abc
    collections.Mapping = collections.abc.Mapping
    
import logging
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
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
    # Добавьте другие растения здесь
]

class PlantQuery(BaseModel):
    color: str
    size: str
    type: str

class PlantFact(Fact):
    """Факт, описывающий растение."""
    color = ""
    size = ""
    type = ""
    name = ""
    link = ""

class PlantEngine(KnowledgeEngine):
    def __init__(self, query):
        super().__init__()
        self.query = query
        self.results = []

    def add_facts(self):
        """Добавляем факты о растениях."""
        for plant in plants:
            # Передаем все данные, включая name и link
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
            # Добавляем все параметры в результат
            self.results.append({
                "color": color,
                "size": size,
                "type": type,
                "name": name,
                "link": link
            })

@app.post("/find_plants")
async def find_plants(query: PlantQuery, request: Request):
    """Эндпоинт для поиска растений по параметрам с использованием experta."""
    # Логирование входящего запроса (полное тело запроса)
    request_body = await request.body()
    logger.info(f"Получен запрос от {request.client.host}: {request_body.decode()}")

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
