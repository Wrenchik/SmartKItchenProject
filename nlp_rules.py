import spacy
from database import SessionLocal
import models

nlp = spacy.load("ru_core_news_sm")

TEXTS = [
    "Взбейте 2 яйца до пены.",
    "Яйца нельзя взбивать слишком долго.",
    "Выпекать при температуре 180 градусов 25 минут."
]

db = SessionLocal()

rules = []

for text in TEXTS:
    doc = nlp(text)
    text_lower = text.lower()

    # 1. Отбрасывание несущественного (просто пример)
    if len(text) < 5:
        continue

    # 2. Выявление сущностей и намерений
    if "взбей" in text_lower:
        rules.append(("IF есть яйца THEN взбить яйца", 0.9))
    if "нельзя" in text_lower and "взб" in text_lower:
        rules.append(("IF есть яйца THEN НЕ взбивать яйца", 0.8))
    if "градус" in text_lower:
        rules.append(("IF тесто готово THEN выпекать при 180C 25 минут", 0.95))

# 3. Сохранение в БЗ
for r in rules:
    db_rule = models.KnowledgeRule(rule=r[0], confidence=r[1])
    db.add(db_rule)

db.commit()

# 4. Обнаружение противоречий
print("ПРОВЕРКА ПРОТИВОРЕЧИЙ:")
has_positive = any("взбить" in r[0] and "НЕ" not in r[0] for r in rules)
has_negative = any("НЕ взбивать" in r[0] for r in rules)

if has_positive and has_negative:
    print("⚠ Найдено противоречие: взбивать / не взбивать яйца")

db.close()
