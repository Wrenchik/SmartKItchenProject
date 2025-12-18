from pydantic import BaseModel
from pydantic import ConfigDict
from typing import Optional

class FridgeBase(BaseModel):
    owner: str

class FridgeCreate(FridgeBase):
    pass

class Fridge(FridgeBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class ProductBase(BaseModel):
    name: str
    perishability: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class InventoryBase(BaseModel):
    fridge_id: int
    product_id: int
    quantity: float
    unit: str

class InventoryCreate(InventoryBase):
    pass

class Inventory(InventoryBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class InventoryOut(BaseModel):
    id: int
    fridge_id: int
    product_id: int
    quantity: float
    unit: str
    model_config = ConfigDict(from_attributes=True)

class RecipeBase(BaseModel):
    name: str
    servings: int
    meal_type: str
    required_equipment: str


class RecipeCreate(RecipeBase):
    pass

class Recipe(RecipeBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class RecipeIngredientBase(BaseModel):
    recipe_id: int
    product: str
    quantity: float
    unit: str

class RecipeIngredientCreate(RecipeIngredientBase):
    pass

class RecipeIngredient(RecipeIngredientBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class OrderCreate(BaseModel):
    items: str

class Order(BaseModel):
    id: int
    items: str
    model_config = ConfigDict(from_attributes=True)

class RecommendRequest(BaseModel):
    fridge_ids: list[int]
    people: int
    meal_type: str

class TextRequest(BaseModel):
    text: str

class EquipmentBase(BaseModel):
    fridge_id: int
    name: str
    quantity: int

class EquipmentCreate(EquipmentBase):
    pass

class Equipment(EquipmentBase):
    id: int
    model_config = {"from_attributes": True}
