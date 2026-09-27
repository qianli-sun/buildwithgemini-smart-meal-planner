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

"""Firestore tools for reading and writing recipes in SmartMeal Planner.

Important: FIRESTORE_PROJECT_ID is hardcoded as a string because Agent Platform
runtime returns the numeric project number from google.auth.default() and
GOOGLE_CLOUD_PROJECT, which breaks Firestore (default) database lookups.
"""

import base64
import datetime
import os
import re
from typing import Any
from google import genai
from google.adk.tools import ToolContext
from google.cloud import firestore, storage
from google.genai import types
import httpx

# Hardcoded project ID and GCS bucket as string literals
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-04-5805be9550d8"
COLLECTION_NAME = "recipes"
IMAGE_BUCKET_NAME = "smart-meal-planner-images-5805be95"

_firestore_client: firestore.Client | None = None
_genai_client: genai.Client | None = None
_storage_client: storage.Client | None = None


def get_firestore_client() -> firestore.Client:
    """Returns the Firestore client initialized with the hardcoded project ID."""
    global _firestore_client
    if _firestore_client is None:
        _firestore_client = firestore.Client(project=FIRESTORE_PROJECT_ID)
    return _firestore_client


def get_genai_client() -> genai.Client:
    """Returns the GenAI client initialized for the global region."""
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(
            vertexai=True,
            project=FIRESTORE_PROJECT_ID,
            location="global",
        )
    return _genai_client


def get_storage_client() -> storage.Client:
    """Returns the Google Cloud Storage client."""
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
    return _storage_client


def search_recipes(
    meal_type: str = "",
    time_tier: str = "",
    max_prep_time_minutes: int = 0,
    dietary_tag: str = "",
    cuisine: str = "",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Search and filter recipes from the Firestore database.

    Args:
        meal_type: Optional meal type filter ('breakfast', 'lunch', 'dinner', or 'snack').
        time_tier: Optional prep tier ('express' for <=15m, 'standard' for <=30m, 'relaxed' for 45m+).
        max_prep_time_minutes: Maximum total preparation time in minutes (0 means no limit).
        dietary_tag: Optional dietary tag filter (e.g. 'vegetarian', 'vegan', 'gluten-free', 'high-protein').
        cuisine: Optional cuisine filter (e.g. 'Mediterranean', 'Asian', 'American').
        limit: Maximum number of recipes to return (default 5).

    Returns:
        A list of matching recipe summaries containing ID, name, meal type, time tier, prep time, calories, and description.
    """
    db = get_firestore_client()
    recipes_ref = db.collection(COLLECTION_NAME)

    docs = recipes_ref.stream()
    results: list[dict[str, Any]] = []

    clean_meal = meal_type.strip().lower()
    clean_tier = time_tier.strip().lower()
    clean_tag = dietary_tag.strip().lower()
    clean_cuisine = cuisine.strip().lower()

    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id

        # Filter by meal_type if provided
        if clean_meal and data.get("meal_type", "").lower() != clean_meal:
            continue

        # Filter by time_tier if provided
        if clean_tier and data.get("time_tier", "").lower() != clean_tier:
            continue

        # Filter by max prep/total time if provided
        if max_prep_time_minutes > 0:
            total_time = data.get("total_time_minutes") or (
                data.get("prep_time_minutes", 0) + data.get("cook_time_minutes", 0)
            )
            if total_time > max_prep_time_minutes:
                continue

        # Filter by dietary tag if provided
        if clean_tag:
            tags = [t.lower() for t in data.get("dietary_tags", [])]
            if clean_tag not in tags and not any(clean_tag in t for t in tags):
                continue

        # Filter by cuisine if provided
        if clean_cuisine and clean_cuisine not in data.get("cuisine", "").lower():
            continue

        # Return a clean summary of the recipe
        summary = {
            "id": data.get("id"),
            "name": data.get("name"),
            "meal_type": data.get("meal_type"),
            "time_tier": data.get("time_tier"),
            "prep_time_minutes": data.get("prep_time_minutes"),
            "cook_time_minutes": data.get("cook_time_minutes", 0),
            "total_time_minutes": data.get("total_time_minutes"),
            "calories": data.get("calories"),
            "cuisine": data.get("cuisine"),
            "dietary_tags": data.get("dietary_tags", []),
            "description": data.get("description"),
        }
        results.append(summary)

        if len(results) >= limit:
            break

    return results


def get_recipe_details(recipe_id: str) -> dict[str, Any]:
    """Get the full details of a specific recipe from Firestore.

    Args:
        recipe_id: The unique identifier of the recipe (e.g. 'express-chickpea-bowl').

    Returns:
        A dictionary containing complete recipe information, ingredients, instructions, and macros.
    """
    db = get_firestore_client()
    doc_ref = db.collection(COLLECTION_NAME).document(recipe_id.strip())
    doc = doc_ref.get()

    if not doc.exists:
        # Fallback search by name if exact ID is not found
        clean_id = recipe_id.strip().lower()
        for d in db.collection(COLLECTION_NAME).stream():
            data = d.to_dict()
            if data.get("name", "").lower() == clean_id:
                data["id"] = d.id
                return data

        return {"error": f"Recipe with ID '{recipe_id}' not found in Firestore."}

    data = doc.to_dict()
    data["id"] = doc.id
    return data


def save_recipe(
    name: str,
    meal_type: str,
    time_tier: str,
    prep_time_minutes: int,
    cook_time_minutes: int = 0,
    servings: int = 1,
    cuisine: str = "General",
    dietary_tags: list[str] | None = None,
    calories: int = 0,
    protein_g: int = 0,
    carbs_g: int = 0,
    fat_g: int = 0,
    ingredients: list[Any] | None = None,
    instructions: list[str] | None = None,
    description: str = "",
) -> dict[str, Any]:
    """Save a new recipe or update an existing recipe in Firestore.

    Args:
        name: Name of the dish (e.g. 'Greek Yogurt Parfait').
        meal_type: Meal type ('breakfast', 'lunch', 'dinner', or 'snack').
        time_tier: Time category ('express', 'standard', or 'relaxed').
        prep_time_minutes: Preparation time in minutes.
        cook_time_minutes: Cooking time in minutes (default 0).
        servings: Number of servings (default 1).
        cuisine: Cuisine style (e.g. 'Mediterranean', 'American').
        dietary_tags: List of dietary tags (e.g. ['vegetarian', 'healthy']).
        calories: Estimated calories per serving.
        protein_g: Protein in grams per serving.
        carbs_g: Carbohydrates in grams per serving.
        fat_g: Fat in grams per serving.
        ingredients: List of ingredient strings or ingredient objects with item/amount/category.
        instructions: List of step-by-step preparation steps.
        description: Brief appetizing description of the recipe.

    Returns:
        A dictionary containing the status of the operation and the assigned recipe_id.
    """
    db = get_firestore_client()

    # Generate a slug ID from name
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    recipe_id = f"{time_tier.lower()}-{slug}" if time_tier else slug

    # Normalize ingredients format
    formatted_ingredients = []
    if ingredients:
        for item in ingredients:
            if isinstance(item, dict):
                formatted_ingredients.append(item)
            else:
                formatted_ingredients.append({"item": str(item), "amount": "", "category": "pantry"})

    doc_data = {
        "id": recipe_id,
        "name": name,
        "meal_type": meal_type.lower(),
        "time_tier": time_tier.lower(),
        "prep_time_minutes": prep_time_minutes,
        "cook_time_minutes": cook_time_minutes,
        "total_time_minutes": prep_time_minutes + cook_time_minutes,
        "servings": servings,
        "cuisine": cuisine,
        "dietary_tags": dietary_tags or [],
        "calories": calories,
        "macros": {
            "protein_g": protein_g,
            "carbs_g": carbs_g,
            "fat_g": fat_g,
        },
        "ingredients": formatted_ingredients,
        "instructions": instructions or [],
        "description": description,
    }

    doc_ref = db.collection(COLLECTION_NAME).document(recipe_id)
    doc_ref.set(doc_data)

    return {
        "status": "success",
        "message": f"Recipe '{name}' saved successfully to Firestore collection '{COLLECTION_NAME}'.",
        "recipe_id": recipe_id,
        "total_time_minutes": doc_data["total_time_minutes"],
    }


async def generate_dish_image(
    dish_name: str,
    visual_description: str = "",
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Generate an appetizing food photography preview for a dish, save as an artifact, and upload to Cloud Storage.

    Args:
        dish_name: Name of the dish (e.g. 'Mediterranean Chickpea Salad Bowl').
        visual_description: Optional extra details to guide photo generation (e.g. 'with fresh herbs in a white ceramic bowl').
        tool_context: Optional ADK ToolContext injected by the runtime to save artifacts to the Playground's Artifacts panel.

    Returns:
        A dictionary with status and public HTTPS URL (https://storage.googleapis.com/<bucket>/<object>) of the generated image.
    """
    client = get_genai_client()
    storage_client = get_storage_client()
    bucket = storage_client.bucket(IMAGE_BUCKET_NAME)

    prompt = f"Professional appetizing food photography of {dish_name}"
    if visual_description:
        prompt += f", {visual_description}"
    prompt += ", high resolution, culinary magazine style, natural lighting."

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
        )
        image_part = next(
            (p for p in response.candidates[0].content.parts if p.inline_data),
            None,
        )
        if not image_part or not image_part.inline_data:
            return {"error": "No image data returned from image generation model."}

        image_bytes = image_part.inline_data.data
        mime_type = image_part.inline_data.mime_type or "image/jpeg"
        ext = "jpg" if "jpeg" in mime_type else "png"

        slug = re.sub(r"[^a-z0-9]+", "-", dish_name.lower()).strip("-")
        filename = f"{slug}.{ext}"

        # 1. Save with tool_context.save_artifact so it shows up in Playground's Artifacts panel
        artifact_version = None
        if tool_context is not None:
            try:
                part_artifact = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                artifact_version = await tool_context.save_artifact(
                    filename=filename,
                    artifact=part_artifact,
                )
            except Exception:
                # Fallback if artifact service is not initialized in the current environment
                pass

        # 2. Upload the same image bytes to the public Cloud Storage bucket (no local file written)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)
        public_url = f"https://storage.googleapis.com/{IMAGE_BUCKET_NAME}/{filename}"

        return {
            "status": "success",
            "dish_name": dish_name,
            "filename": filename,
            "image_url": public_url,
            "artifact_version": artifact_version,
        }
    except Exception as e:
        return {"error": f"Failed to generate dish image: {e}"}


def _process_video_audio_and_duration(video_bytes: bytes) -> bytes:
    """Enhance raw Omni video with smooth retiming (>=6s) and Google Lyria acoustic soundtrack."""
    import shutil
    import subprocess
    import tempfile

    if not shutil.which("ffmpeg"):
        return video_bytes

    audio_path = os.path.join(os.path.dirname(__file__), "assets", "lyria_cozy_soundtrack.aac")
    if not os.path.exists(audio_path):
        try:
            storage_client = get_storage_client()
            bucket = storage_client.bucket(IMAGE_BUCKET_NAME)
            blob = bucket.blob("lyria_cozy_soundtrack.aac")
            if blob.exists():
                os.makedirs(os.path.dirname(audio_path), exist_ok=True)
                blob.download_to_filename(audio_path)
        except Exception:
            pass

    if not os.path.exists(audio_path):
        return video_bytes

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            in_path = os.path.join(tmpdir, "raw.mp4")
            out_path = os.path.join(tmpdir, "muxed.mp4")
            with open(in_path, "wb") as f:
                f.write(video_bytes)

            raw_dur = 3.0
            try:
                probe = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", in_path],
                    capture_output=True, text=True, timeout=5
                )
                val = float(probe.stdout.strip())
                if val > 0:
                    raw_dur = val
            except Exception:
                pass

            target_dur = 6.0 if raw_dur <= 4.0 else raw_dur
            pts_factor = target_dur / raw_dur

            cmd = [
                "ffmpeg", "-y",
                "-i", in_path,
                "-stream_loop", "-1",
                "-i", audio_path,
                "-filter:v", f"setpts={pts_factor:.2f}*PTS",
                "-filter:a", f"afade=t=in:st=0:d=0.8,afade=t=out:st={max(0.0, target_dur - 1.5):.2f}:d=1.5,volume=0.7",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-t", f"{target_dur:.2f}",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "20",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                out_path
            ]
            res = subprocess.run(cmd, capture_output=True, timeout=15)
            if res.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                with open(out_path, "rb") as f:
                    return f.read()
    except Exception:
        pass

    return video_bytes


async def generate_dish_video(
    dish_name: str,
    visual_style: str = "vibrant Studio Ghibli anime style, warm cozy lighting, appetizing food aesthetic",
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """Generate a short video preview for a dish using Google's Omni model (gemini-omni-flash-preview) in the global region.

    Args:
        dish_name: Name of the dish (e.g. 'Steaming Ramen Bowl', 'Crispy Golden Salmon', 'Berry Yogurt Parfait').
        visual_style: Visual art style or animation aesthetic (default: vibrant Studio Ghibli anime style with cozy lighting).
        tool_context: Optional ADK ToolContext injected by the runtime to save artifacts to the Playground's Artifacts panel.

    Returns:
        A dictionary with status and public HTTPS URL (https://storage.googleapis.com/<bucket>/<object>) of the generated video.
    """
    client = get_genai_client()
    storage_client = get_storage_client()
    bucket = storage_client.bucket(IMAGE_BUCKET_NAME)

    prompt = f"A smooth 10-second appetizing culinary animation of {dish_name}, {visual_style}."

    try:
        interaction = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt,
            response_format={"type": "video"},
        )

        video_bytes = None
        mime_type = "video/mp4"

        if (
            hasattr(interaction, "output_video")
            and interaction.output_video
            and getattr(interaction.output_video, "data", None)
        ):
            video_bytes = base64.b64decode(interaction.output_video.data)
            if getattr(interaction.output_video, "mime_type", None):
                mime_type = interaction.output_video.mime_type
        elif hasattr(interaction, "steps") and interaction.steps:
            for step in interaction.steps:
                content_list = getattr(step, "content", []) or []
                for item in content_list:
                    if getattr(item, "type", "") == "video" and getattr(item, "data", None):
                        video_bytes = base64.b64decode(item.data)
                        mime_type = getattr(item, "mime_type", "video/mp4")
                        break

        if not video_bytes:
            return {"error": "No video data returned from Omni video model."}

        # Enhance with Lyria soundtrack and smooth >=6s playback
        video_bytes = _process_video_audio_and_duration(video_bytes)

        slug = re.sub(r"[^a-z0-9]+", "-", dish_name.lower()).strip("-")
        filename = f"{slug}-omni.mp4"

        # 1. Save with tool_context.save_artifact so it shows up in Playground's Artifacts panel
        artifact_version = None
        if tool_context is not None:
            try:
                part_artifact = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
                artifact_version = await tool_context.save_artifact(
                    filename=filename,
                    artifact=part_artifact,
                )
            except Exception:
                # Fallback if artifact service is not initialized in the current environment
                pass

        # 2. Upload the same video bytes to the public Cloud Storage bucket (no local file written)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)
        public_url = f"https://storage.googleapis.com/{IMAGE_BUCKET_NAME}/{filename}"

        return {
            "status": "success",
            "dish_name": dish_name,
            "filename": filename,
            "video_url": public_url,
            "artifact_version": artifact_version,
            "prompt": prompt,
        }
    except Exception as e:
        return {"error": f"Failed to generate dish video: {e}"}


def generate_grocery_list(recipe_ids: list[str]) -> dict[str, Any]:
    """Consolidate ingredients from multiple recipes into an organized shopping checklist grouped by aisle.

    Args:
        recipe_ids: A list of recipe IDs (e.g. ['express-chickpea-bowl', 'standard-sesame-salmon']) to shop for.

    Returns:
        A dictionary containing categorized grocery items and a formatted markdown checklist.
    """
    db = get_firestore_client()
    categorized: dict[str, list[str]] = {
        "Produce": [],
        "Pantry & Grains": [],
        "Meat & Seafood": [],
        "Dairy & Eggs": [],
        "Spices & Condiments": [],
        "Other": [],
    }
    found_recipes: list[str] = []

    for r_id in recipe_ids:
        doc = db.collection(COLLECTION_NAME).document(r_id.strip()).get()
        if not doc.exists:
            continue
        data = doc.to_dict()
        found_recipes.append(data.get("name", r_id))
        ingredients = data.get("ingredients", [])

        for ing in ingredients:
            if isinstance(ing, dict):
                item_name = ing.get("item", "")
                amount = ing.get("amount", "")
                cat = ing.get("category", "").lower()
                entry = f"{item_name} ({amount})" if amount else item_name
            else:
                entry = str(ing)
                cat = "other"

            if any(k in cat for k in ["produce", "veg", "fruit"]):
                categorized["Produce"].append(entry)
            elif any(k in cat for k in ["meat", "seafood", "fish", "poultry"]):
                categorized["Meat & Seafood"].append(entry)
            elif any(k in cat for k in ["dairy", "egg", "cheese"]):
                categorized["Dairy & Eggs"].append(entry)
            elif any(k in cat for k in ["spice", "condiment", "herb", "seasoning"]):
                categorized["Spices & Condiments"].append(entry)
            elif any(k in cat for k in ["pantry", "grain", "canned", "oil"]):
                categorized["Pantry & Grains"].append(entry)
            else:
                categorized["Other"].append(entry)

    cleaned_categorized = {}
    lines = [f"# Grocery Shopping List ({len(found_recipes)} Recipes Included)\n"]
    lines.append(f"**Planned Meals:** {', '.join(found_recipes)}\n")

    for cat_name, items in categorized.items():
        if items:
            deduped = sorted(list(set(items)))
            cleaned_categorized[cat_name] = deduped
            lines.append(f"### {cat_name}")
            for item in deduped:
                lines.append(f"- [ ] {item}")
            lines.append("")

    checklist_text = "\n".join(lines)
    return {
        "status": "success",
        "recipes_included": found_recipes,
        "categorized_items": cleaned_categorized,
        "checklist_markdown": checklist_text,
    }


def check_daily_schedule(day_of_week: str = "") -> dict[str, Any]:
    """Check workday schedule and meeting density to recommend the ideal cooking time tier.

    Args:
        day_of_week: Optional day of week (e.g. 'Monday', 'Tuesday', 'today'). Defaults to today.

    Returns:
        A dictionary with meeting schedule summary, available prep time window (minutes), and recommended time_tier ('express', 'standard', or 'relaxed').
    """
    if not day_of_week or day_of_week.lower() in ["today", "now"]:
        target_day = datetime.datetime.now().strftime("%A")
    else:
        target_day = day_of_week.capitalize()

    schedules = {
        "Monday": {
            "meeting_load": "Heavy sprint planning and team syncs (11:30 AM - 1:30 PM)",
            "available_prep_minutes": 15,
            "recommended_time_tier": "express",
            "reasoning": "Back-to-back morning meetings leave only a 15-minute gap for lunch. Fast no-cook or pre-prepped options recommended.",
        },
        "Tuesday": {
            "meeting_load": "Moderate meetings with 12:00 PM - 1:00 PM open slot",
            "available_prep_minutes": 30,
            "recommended_time_tier": "standard",
            "reasoning": "A solid 1-hour lunch block allows a standard 20-30 minute stovetop or skillet prep.",
        },
        "Wednesday": {
            "meeting_load": "High meeting density (midday client reviews & design syncs)",
            "available_prep_minutes": 15,
            "recommended_time_tier": "express",
            "reasoning": "Dense afternoon schedule demands a quick <15 min express meal.",
        },
        "Thursday": {
            "meeting_load": "Moderate focus day with isolated 30m standups",
            "available_prep_minutes": 30,
            "recommended_time_tier": "standard",
            "reasoning": "Comfortable schedule for a standard 25-30 minute cook session.",
        },
        "Friday": {
            "meeting_load": "No-meeting afternoon / Wrap-up focus time",
            "available_prep_minutes": 60,
            "recommended_time_tier": "relaxed",
            "reasoning": "Open afternoon schedule enables a leisurely or relaxed 45+ min batch cook or roasted meal.",
        },
        "Saturday": {
            "meeting_load": "Weekend / Free day",
            "available_prep_minutes": 90,
            "recommended_time_tier": "relaxed",
            "reasoning": "Weekend allows ample time for relaxed cooking and batch prep.",
        },
        "Sunday": {
            "meeting_load": "Weekend / Weekly meal prep & grocery planning",
            "available_prep_minutes": 90,
            "recommended_time_tier": "relaxed",
            "reasoning": "Ideal day for relaxed cooking, grocery consolidation, and batch-prepping weekday meals.",
        },
    }

    info = schedules.get(
        target_day,
        {
            "meeting_load": "Standard workday",
            "available_prep_minutes": 30,
            "recommended_time_tier": "standard",
            "reasoning": "Standard daily schedule allows a 20-30 minute meal.",
        },
    )

    return {
        "day": target_day,
        "meeting_load": info["meeting_load"],
        "available_prep_minutes": info["available_prep_minutes"],
        "recommended_time_tier": info["recommended_time_tier"],
        "reasoning": info["reasoning"],
    }


def search_online_recipes(query: str, limit: int = 3) -> list[dict[str, Any]]:
    """Search for global meal ideas and recipes from TheMealDB public culinary database.

    Args:
        query: Ingredient or dish keyword to search for (e.g. 'salmon', 'chicken', 'pasta', 'curry').
        limit: Maximum number of recipes to return (default 3).

    Returns:
        A list of recipes with name, cuisine, category, ingredients, instructions, and image URL.
    """
    api_key = os.getenv("THEMEALDB_API_KEY", "1")
    url = f"https://www.themealdb.com/api/json/v1/{api_key}/search.php"

    try:
        response = httpx.get(url, params={"s": query.strip()}, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        meals = data.get("meals") or []

        results = []
        for meal in meals[:limit]:
            ingredients = []
            for i in range(1, 21):
                ing = meal.get(f"strIngredient{i}")
                measure = meal.get(f"strMeasure{i}")
                if ing and ing.strip():
                    amt = measure.strip() if measure else ""
                    ingredients.append(f"{amt} {ing.strip()}".strip())

            results.append({
                "name": meal.get("strMeal"),
                "cuisine": meal.get("strArea"),
                "category": meal.get("strCategory"),
                "instructions": meal.get("strInstructions"),
                "image_url": meal.get("strMealThumb"),
                "ingredients": ingredients,
                "source_url": meal.get("strSource") or meal.get("strYoutube"),
            })

        return results
    except Exception as e:
        return [{"error": f"Failed to fetch online recipes: {e}"}]


