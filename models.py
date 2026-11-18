from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime


class RestaurantCreate(BaseModel):
    name: str
    url: HttpUrl


class RestaurantResponse(BaseModel):
    id: int
    name: str
    url: str
    created_at: str


class ScreenshotResponse(BaseModel):
    restaurant_id: int
    restaurant_name: str
    screenshot_path: str
    timestamp: str
    status: str  # "success" or "error"


class DashboardView(BaseModel):
    restaurants: list[RestaurantResponse]
    screenshots: list[ScreenshotResponse]
