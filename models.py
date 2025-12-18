from sqlalchemy import Column, Integer, String, Float, ForeignKey
from database import Base

class Fridge(Base):
    __tablename__ = "fridges"
    id = Column(Integer, primary_key=True)
    owner = Column(String)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    perishability = Column(String)  # fast / long

class Inventory(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True)
    fridge_id = Column(Integer, ForeignKey("fridges.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Float)
    unit = Column(String)

class Recipe(Base):
    __tablename__ = "recipes"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    servings = Column(Integer)
    meal_type = Column(String)
    required_equipment = Column(String)

class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"
    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"))
    product = Column(String)
    quantity = Column(Float)
    unit = Column(String)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    items = Column(String)

class KnowledgeRule(Base):
    __tablename__ = "knowledge_rules"
    id = Column(Integer, primary_key=True)
    rule = Column(String)
    confidence = Column(Float)

class Equipment(Base):
    __tablename__ = "equipment"
    id = Column(Integer, primary_key=True)
    fridge_id = Column(Integer, ForeignKey("fridges.id"))
    name = Column(String)
    quantity = Column(Integer)

