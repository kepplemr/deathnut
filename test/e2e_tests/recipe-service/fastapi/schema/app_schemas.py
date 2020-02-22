from pydantic import BaseModel
from typing import List
class Recipe(BaseModel):
    title: str
    ingredients: List[str]

class RecipeWithId(Recipe):
    id: str
    title: str
    ingredients: List[str]

class PartialRecipe(BaseModel):
    title: str = None
    ingredients: List[str] = None