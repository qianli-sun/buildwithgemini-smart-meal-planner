# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for SmartMeal Planner Firestore recipe tools."""

from app.tools import (
    check_daily_schedule,
    generate_dish_image,
    generate_dish_video,
    generate_grocery_list,
    get_recipe_details,
    save_recipe,
    search_online_recipes,
    search_recipes,
)


def test_search_recipes() -> None:
    """Test searching recipes with different filters."""
    # Test meal type filter
    lunches = search_recipes(meal_type="lunch")
    assert len(lunches) > 0
    for r in lunches:
        assert r["meal_type"] == "lunch"

    # Test time tier filter
    express_meals = search_recipes(time_tier="express")
    assert len(express_meals) > 0
    for r in express_meals:
        assert r["time_tier"] == "express"


def test_get_recipe_details() -> None:
    """Test fetching details for a seeded recipe."""
    details = get_recipe_details("express-chickpea-bowl")
    assert "error" not in details
    assert details["name"] == "Mediterranean Chickpea Salad Bowl"
    assert "macros" in details
    assert "ingredients" in details
    assert len(details["ingredients"]) > 0


def test_save_and_retrieve_recipe() -> None:
    """Test creating a new recipe and reading it back."""
    result = save_recipe(
        name="Unit Test Quinoa Power Salad",
        meal_type="lunch",
        time_tier="express",
        prep_time_minutes=12,
        cook_time_minutes=0,
        servings=1,
        cuisine="Mediterranean",
        dietary_tags=["vegan", "gluten-free", "healthy"],
        calories=360,
        protein_g=14,
        carbs_g=48,
        fat_g=12,
        ingredients=["Cooked quinoa", "Kale", "Lemon vinaigrette"],
        instructions=["Toss all ingredients together."],
        description="A nutrient-dense quick lunch salad.",
    )
    assert result["status"] == "success"
    recipe_id = result["recipe_id"]

    fetched = get_recipe_details(recipe_id)
    assert fetched["name"] == "Unit Test Quinoa Power Salad"
    assert fetched["time_tier"] == "express"
    assert fetched["macros"]["protein_g"] == 14


def test_generate_grocery_list() -> None:
    """Test generating a consolidated grocery checklist from recipe IDs."""
    result = generate_grocery_list(["express-chickpea-bowl", "standard-turkey-skillet"])
    assert result["status"] == "success"
    assert len(result["recipes_included"]) == 2
    assert "Produce" in result["categorized_items"]
    assert len(result["categorized_items"]["Produce"]) > 0
    assert "[ ]" in result["checklist_markdown"]


def test_check_daily_schedule() -> None:
    """Test schedule checker returns appropriate time tiers."""
    monday = check_daily_schedule("Monday")
    assert monday["recommended_time_tier"] == "express"
    assert monday["available_prep_minutes"] <= 15

    friday = check_daily_schedule("Friday")
    assert friday["recommended_time_tier"] == "relaxed"
    assert friday["available_prep_minutes"] >= 45


def test_search_online_recipes() -> None:
    """Test searching real online recipes from TheMealDB API."""
    results = search_online_recipes("salmon", limit=2)
    assert len(results) > 0
    first = results[0]
    assert "error" not in first
    assert "name" in first
    assert "ingredients" in first
    assert "instructions" in first
    assert len(first["ingredients"]) > 0


import pytest

@pytest.mark.asyncio
async def test_generate_dish_image() -> None:
    """Test generating a dish image with gemini-3.1-flash-lite-image in global region and GCS upload."""
    res = await generate_dish_image("Avocado Berry Toast")
    assert "error" not in res
    assert res["status"] == "success"
    assert res["image_url"].startswith("https://storage.googleapis.com/smart-meal-planner-images-5805be95/")


@pytest.mark.asyncio
async def test_generate_dish_video_mocked(monkeypatch) -> None:
    """Test generating a dish video with mocked Omni interactions API."""
    import base64

    class DummyVideo:
        data = base64.b64encode(b"fake_mp4_video_data").decode("utf-8")
        mime_type = "video/mp4"

    class DummyInteraction:
        output_video = DummyVideo()

    class DummyInteractionsClient:
        def create(self, **kwargs):
            return DummyInteraction()

    class DummyGenAIClient:
        interactions = DummyInteractionsClient()

    monkeypatch.setattr("app.tools.get_genai_client", lambda: DummyGenAIClient())

    res = await generate_dish_video("Matcha Green Tea Parfait")
    assert "error" not in res
    assert res["status"] == "success"
    assert res["dish_name"] == "Matcha Green Tea Parfait"
    assert res["video_url"].endswith(".mp4")
    assert res["video_url"].startswith("https://storage.googleapis.com/smart-meal-planner-images-5805be95/")



