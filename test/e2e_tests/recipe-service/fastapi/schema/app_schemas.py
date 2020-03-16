from typing import List

from pydantic import BaseModel


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
