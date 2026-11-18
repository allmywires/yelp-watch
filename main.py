import os
import glob
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from contextlib import asynccontextmanager

from models import RestaurantCreate, RestaurantResponse, ScreenshotResponse, DashboardView
from database import init_db, get_db
from scraper import take_screenshot

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "screenshots")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Yelp Watch", lifespan=lifespan)

# Serve static files
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
app.mount("/screenshots", StaticFiles(directory=SCREENSHOTS_DIR), name="screenshots")


# ─── Restaurant CRUD ───────────────────────────────────────────────────────

@app.get("/api/restaurants", response_model=list[RestaurantResponse])
async def list_restaurants():
    async with get_db() as db:
        async with db.execute(
            "SELECT id, name, url, created_at FROM restaurants ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                RestaurantResponse(
                    id=row["id"],
                    name=row["name"],
                    url=row["url"],
                    created_at=row["created_at"]
                )
                for row in rows
            ]


@app.post("/api/restaurants", response_model=RestaurantResponse, status_code=201)
async def add_restaurant(restaurant: RestaurantCreate):
    async with get_db() as db:
        try:
            await db.execute(
                "INSERT INTO restaurants (name, url) VALUES (?, ?)",
                (restaurant.name, str(restaurant.url))
            )
            await db.commit()
        except Exception as e:
            if "UNIQUE constraint" in str(e):
                raise HTTPException(status_code=409, detail="Restaurant URL already exists")
            raise HTTPException(status_code=500, detail=str(e))
        
        # Return the created record
        async with db.execute(
            "SELECT id, name, url, created_at FROM restaurants WHERE url = ?",
            (str(restaurant.url),)
        ) as cursor:
            row = await cursor.fetchone()
            return RestaurantResponse(
                id=row["id"],
                name=row["name"],
                url=row["url"],
                created_at=row["created_at"]
            )


@app.delete("/api/restaurants/{restaurant_id}")
async def delete_restaurant(restaurant_id: int):
    async with get_db() as db:
        # Delete associated screenshots first
        await db.execute("DELETE FROM screenshots WHERE restaurant_id = ?", (restaurant_id,))
        # Delete the restaurant
        result = await db.execute(
            "DELETE FROM restaurants WHERE id = ?", (restaurant_id,)
        )
        await db.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Restaurant not found")
    
    # Clean up screenshot files
    # Find and delete any screenshot files for this restaurant by searching screenshots table first
    async with get_db() as db:
        async with db.execute(
            "SELECT screenshot_path FROM screenshots WHERE restaurant_id = ?",
            (restaurant_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                if row["screenshot_path"] and os.path.exists(row["screenshot_path"]):
                    os.remove(row["screenshot_path"])
    
    return {"detail": "Restaurant deleted"}


# ─── Screenshots ───────────────────────────────────────────────────────────

@app.get("/api/restaurants/{restaurant_id}/screenshots", response_model=list[ScreenshotResponse])
async def list_screenshots(restaurant_id: int):
    async with get_db() as db:
        # Verify restaurant exists
        async with db.execute(
            "SELECT id FROM restaurants WHERE id = ?", (restaurant_id,)
        ) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(status_code=404, detail="Restaurant not found")
        
        async with db.execute(
            "SELECT id, restaurant_id, screenshot_path, timestamp, status "
            "FROM screenshots WHERE restaurant_id = ? ORDER BY timestamp DESC",
            (restaurant_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                ScreenshotResponse(
                    restaurant_id=row["restaurant_id"],
                    restaurant_name="",  # Filled by caller
                    screenshot_path=row["screenshot_path"] or "",
                    timestamp=row["timestamp"],
                    status=row["status"]
                )
                for row in rows
            ]


@app.post("/api/restaurants/{restaurant_id}/check", response_model=ScreenshotResponse)
async def check_waitlist(restaurant_id: int):
    async with get_db() as db:
        async with db.execute(
            "SELECT id, name, url FROM restaurants WHERE id = ?", (restaurant_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Restaurant not found")
    
    # Take screenshot outside DB context
    result = await take_screenshot(row["url"], row["name"])
    
    # Record in DB
    async with get_db() as db:
        await db.execute(
            "INSERT INTO screenshots (restaurant_id, screenshot_path, status) VALUES (?, ?, ?)",
            (restaurant_id, result["screenshot_path"] or "", result["status"])
        )
        await db.commit()
        
        async with db.execute(
            "SELECT id, restaurant_id, screenshot_path, timestamp, status "
            "FROM screenshots WHERE restaurant_id = ? ORDER BY timestamp DESC LIMIT 1",
            (restaurant_id,)
        ) as cursor:
            new_row = await cursor.fetchone()
            return ScreenshotResponse(
                restaurant_id=new_row["restaurant_id"],
                restaurant_name=row["name"],
                screenshot_path=new_row["screenshot_path"] or "",
                timestamp=new_row["timestamp"],
                status=new_row["status"]
            )


@app.post("/api/check-all")
async def check_all_restaurants():
    """Check waitlist for all restaurants, return list of results."""
    async with get_db() as db:
        async with db.execute("SELECT id, name, url FROM restaurants ORDER BY created_at") as cursor:
            restaurants = await cursor.fetchall()
    
    results = []
    for row in restaurants:
        result = await take_screenshot(row["url"], row["name"])
        
        async with get_db() as db:
            await db.execute(
                "INSERT INTO screenshots (restaurant_id, screenshot_path, status) VALUES (?, ?, ?)",
                (row["id"], result["screenshot_path"] or "", result["status"])
            )
            await db.commit()
            
            async with db.execute(
                "SELECT id, restaurant_id, screenshot_path, timestamp, status "
                "FROM screenshots WHERE restaurant_id = ? ORDER BY timestamp DESC LIMIT 1",
                (row["id"],)
            ) as cursor:
                new_row = await cursor.fetchone()
                results.append(ScreenshotResponse(
                    restaurant_id=new_row["restaurant_id"],
                    restaurant_name=row["name"],
                    screenshot_path=new_row["screenshot_path"] or "",
                    timestamp=new_row["timestamp"],
                    status=new_row["status"]
                ))
    
    return results


# ─── Dashboard ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    with open(os.path.join(os.path.dirname(__file__), "static", "index.html"), "r") as f:
        return f.read()
