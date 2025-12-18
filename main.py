from fastapi import FastAPI, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session
import models
from database import SessionLocal, engine
import schemas
import re
from fastapi.templating import Jinja2Templates
from fastapi import Request
import random

# ensure models are imported so metadata exists (if not already created)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Kitchen")
templates = Jinja2Templates(directory="templates")

@app.get("/ui")
def ui(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
@app.get("/products_ui")
def products_ui(request: Request):
    return templates.TemplateResponse("products.html", {"request": request})

@app.get("/orders_ui")
def orders_ui(request: Request):
    return templates.TemplateResponse("orders.html", {"request": request})

@app.get("/fridges_ui")
def fridges_ui(request: Request):
    return templates.TemplateResponse("fridges.html", {"request": request})

@app.get("/equipment_ui")
def equipment_ui(request: Request):
    return templates.TemplateResponse("equipment.html", {"request": request})

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# --- Fridges ---
@app.post("/fridges", response_model=schemas.Fridge)
def create_fridge(fridge: schemas.FridgeCreate, db: Session = Depends(get_db)):
    db_fridge = models.Fridge(owner=fridge.owner)
    db.add(db_fridge)
    db.commit()
    db.refresh(db_fridge)
    return db_fridge

@app.get("/fridges", response_model=List[schemas.Fridge])
def list_fridges(db: Session = Depends(get_db)):
    return db.query(models.Fridge).all()

# --- Products ---
@app.post("/products", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    db_product = models.Product(name=product.name, perishability=product.perishability)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/products", response_model=List[schemas.Product])
def list_products(db: Session = Depends(get_db)):
    return db.query(models.Product).all()

# --- Inventory ---
@app.post("/inventory", response_model=schemas.Inventory)
def add_inventory(item: schemas.InventoryCreate, db: Session = Depends(get_db)):
    # Simple check: fridge and product exist
    if db.query(models.Fridge).filter(models.Fridge.id == item.fridge_id).first() is None:
        raise HTTPException(status_code=400, detail="Fridge not found")
    if db.query(models.Product).filter(models.Product.id == item.product_id).first() is None:
        raise HTTPException(status_code=400, detail="Product not found")
    db_item = models.Inventory(fridge_id=item.fridge_id, product_id=item.product_id, quantity=item.quantity, unit=item.unit)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/inventory", response_model=List[schemas.InventoryOut])
def list_inventory(fridge_ids: Optional[str] = Query(None, description="Comma separated fridge ids, e.g. 1,2"), db: Session = Depends(get_db)):
    q = db.query(models.Inventory)
    if fridge_ids:
        ids = [int(x.strip()) for x in fridge_ids.split(",") if x.strip().isdigit()]
        q = q.filter(models.Inventory.fridge_id.in_(ids))
    return q.all()

# Consolidated inventory for fridge_ids
@app.get("/inventory/consolidated")
def consolidated_inventory(fridge_ids: str = Query(..., description="Comma separated fridge ids, e.g. 1,2"), db: Session = Depends(get_db)):
    ids = [int(x.strip()) for x in fridge_ids.split(",") if x.strip().isdigit()]
    if not ids:
        raise HTTPException(status_code=400, detail="fridge_ids required")
    # join inventory -> product and sum quantities grouped by product.name and unit
    from sqlalchemy import func
    rows = (
        db.query(models.Product.name, models.Inventory.unit, func.sum(models.Inventory.quantity).label("total"))
        .join(models.Inventory, models.Product.id == models.Inventory.product_id)
        .filter(models.Inventory.fridge_id.in_(ids))
        .group_by(models.Product.name, models.Inventory.unit)
        .all()
    )
    result = [{"product": r[0], "unit": r[1], "total_quantity": float(r[2])} for r in rows]
    return {"fridge_ids": ids, "consolidated": result}

# --- Recipes & Ingredients ---
@app.post("/recipes", response_model=schemas.Recipe)
def create_recipe(r: schemas.RecipeCreate, db: Session = Depends(get_db)):
    db_r = models.Recipe(name=r.name, servings=r.servings, meal_type=r.meal_type)
    db.add(db_r)
    db.commit()
    db.refresh(db_r)
    return db_r

@app.get("/recipes", response_model=List[schemas.Recipe])
def list_recipes(db: Session = Depends(get_db)):
    return db.query(models.Recipe).all()

@app.post("/recipe_ingredients", response_model=schemas.RecipeIngredient)
def add_recipe_ingredient(item: schemas.RecipeIngredientCreate, db: Session = Depends(get_db)):
    # check recipe exists
    if db.query(models.Recipe).filter(models.Recipe.id == item.recipe_id).first() is None:
        raise HTTPException(status_code=400, detail="Recipe not found")
    db_item = models.RecipeIngredient(recipe_id=item.recipe_id, product=item.product, quantity=item.quantity, unit=item.unit)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/recipe_ingredients")
def get_recipe_ingredients(recipe_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(models.RecipeIngredient)
    if recipe_id:
        q = q.filter(models.RecipeIngredient.recipe_id == recipe_id)
    return q.all()

# --- Orders ---
@app.get("/orders")
def list_orders(db: Session = Depends(get_db)):
    return db.query(models.Order).all()

@app.post("/orders")
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    db_order = models.Order(items=order.items)
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

from sqlalchemy import func

@app.post("/recommend")
def recommend(req: schemas.RecommendRequest, db: Session = Depends(get_db)):

    # 1. Берём ВСЕ рецепты нужного типа
    recipes = db.query(models.Recipe).filter(
        models.Recipe.meal_type == req.meal_type
    ).all()

    if not recipes:
        raise HTTPException(status_code=404, detail="Рецепты не найдены")

    # 2. Доступная посуда (агрегация)
    eq_rows = (
        db.query(models.Equipment.name, func.sum(models.Equipment.quantity))
        .filter(models.Equipment.fridge_id.in_(req.fridge_ids))
        .group_by(models.Equipment.name)
        .all()
    )
    available_eq = {r[0]: r[1] for r in eq_rows}

    # 3. Консолидированный инвентарь + perishability
    inv_rows = (
        db.query(
            models.Product.name,
            models.Product.perishability,
            func.sum(models.Inventory.quantity)
        )
        .join(models.Inventory, models.Product.id == models.Inventory.product_id)
        .filter(models.Inventory.fridge_id.in_(req.fridge_ids))
        .group_by(models.Product.name, models.Product.perishability)
        .all()
    )

    inventory = {}
    perishability = {}

    for name, p, qty in inv_rows:
        inventory[name] = qty
        perishability[name] = p

    suitable_recipes = []

    # 4. Проверяем КАЖДЫЙ рецепт
    for recipe in recipes:

        # ---- проверка посуды ----
        needed_eq = []
        if recipe.required_equipment:
            needed_eq = recipe.required_equipment.split(",")

        if any(available_eq.get(e, 0) < 1 for e in needed_eq):
            continue  # этот рецепт нельзя приготовить

        # ---- проверка продуктов ----
        scale = req.people / recipe.servings
        ingredients = db.query(models.RecipeIngredient).filter(
            models.RecipeIngredient.recipe_id == recipe.id
        ).all()

        missing = {}
        fast_used = 0

        for ing in ingredients:
            needed = ing.quantity * scale
            available = inventory.get(ing.product, 0)

            if available < needed:
                missing[ing.product] = round(needed - available, 2)

            # считаем скоропортящиеся продукты
            if perishability.get(ing.product) == "fast":
                fast_used += 1

        suitable_recipes.append({
            "recipe": recipe,
            "missing": missing,
            "fast_used": fast_used
        })

    if not suitable_recipes:
        return {
            "can_cook": False,
            "reason": "Нет подходящих рецептов под текущие условия"
        }

    # 5. Приоритет рецептам с МАКСИМУМОМ fast-продуктов
    max_fast = max(r["fast_used"] for r in suitable_recipes)
    best_recipes = [r for r in suitable_recipes if r["fast_used"] == max_fast]

    # 6. СЛУЧАЙНЫЙ выбор из лучших
    chosen = random.choice(best_recipes)

    recipe = chosen["recipe"]
    missing = chosen["missing"]

    # 7. Если не хватает продуктов — заказ
    order_id = None
    if missing:
        order = models.Order(items=str(missing))
        db.add(order)
        db.commit()
        order_id = order.id

    return {
        "recipe": recipe.name,
        "people": req.people,
        "can_cook": len(missing) == 0,
        "missing": missing,
        "order_id": order_id,
        "used_fast_products": max_fast
    }



@app.post("/text_request")
def text_request(req: schemas.TextRequest, db: Session = Depends(get_db)):
    text = req.text.lower()

    # 1. Извлечение количества человек
    people = 1
    m = re.search(r"(\d+)\s*(человек|человека|людей)", text)
    if m:
        people = int(m.group(1))

    # 2. Тип приёма пищи
    if "вечеринк" in text:
        meal_type = "party"
    elif "завтрак" in text:
        meal_type = "breakfast"
    elif "обед" in text:
        meal_type = "lunch"
    elif "ужин" in text:
        meal_type = "dinner"
    else:
        meal_type = "breakfast"  # по умолчанию

    # 3. Кухня / холодильник
    fridge_ids = [1]
    m = re.search(r"(\d+)\s*кухн", text)
    if m:
        fridge_ids = [int(m.group(1))]

    # 4. Используем уже реализованную логику рекомендации
    recommend_request = schemas.RecommendRequest(
        fridge_ids=fridge_ids,
        people=people,
        meal_type=meal_type
    )

    result = recommend(recommend_request, db)

    return {
        "parsed_request": {
            "people": people,
            "meal_type": meal_type,
            "fridge_ids": fridge_ids
        },
        "recommendation": result
    }

@app.post("/equipment", response_model=schemas.Equipment)
def add_equipment(item: schemas.EquipmentCreate, db: Session = Depends(get_db)):
    eq = models.Equipment(
        fridge_id=item.fridge_id,
        name=item.name,
        quantity=item.quantity
    )
    db.add(eq)
    db.commit()
    db.refresh(eq)
    return eq

@app.delete("/orders/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    db.delete(order)
    db.commit()
    return {"status": "deleted"}


@app.get("/equipment")
def list_equipment(fridge_ids: Optional[str] = Query(None), db: Session = Depends(get_db)):
    q = db.query(models.Equipment)
    if fridge_ids:
        ids = [int(x) for x in fridge_ids.split(",")]
        q = q.filter(models.Equipment.fridge_id.in_(ids))
    return q.all()

@app.put("/inventory/{item_id}")
def update_inventory(item_id: int, quantity: float, db: Session = Depends(get_db)):
    item = db.query(models.Inventory).filter(models.Inventory.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    item.quantity = quantity
    db.commit()
    return {"status": "updated"}

@app.delete("/inventory/{item_id}")
def delete_inventory(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Inventory).filter(models.Inventory.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()
    return {"status": "deleted"}
