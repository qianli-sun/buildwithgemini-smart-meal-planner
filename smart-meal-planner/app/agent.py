# ruff: noqa
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

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.tools import (
    check_daily_schedule,
    generate_dish_image,
    generate_grocery_list,
    get_recipe_details,
    save_recipe,
    search_online_recipes,
    search_recipes,
)


MODEL = "gemini-3.8-flash"


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


async def generate_memories_callback(callback_context: CallbackContext) -> None:
    """Extract and persist salient user facts and preferences to Memory Bank after each turn."""
    try:
        await callback_context.add_session_to_memory()
    except (ValueError, AttributeError):
        # Memory service is not configured in the current runner (e.g. lightweight tests)
        pass
    return None


root_agent = Agent(
    # Keep in sync with agents-cli-manifest.yaml: agents-cli derives this name
    # from the project `name:` recorded there, and telemetry reports it as
    # gen_ai.agent.name. Renaming the agent only here makes the two disagree,
    # and anything selecting traces by name stops finding this agent's.
    name="simple_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are SmartMeal Planner, a culinary and nutrition assistant designed for busy remote professionals.\n"
        "You help users plan healthy meals (breakfast, lunch, dinner), check daily schedule constraints, generate grocery lists, and create visual dish previews based on a Firestore database of recipes.\n\n"
        "Memory & Personalization:\n"
        "- PreloadMemoryTool automatically loads the user's cross-session facts and preferences into context.\n"
        "- Remember and actively apply the user's specific culinary profile across conversations:\n"
        "  1. Dietary restrictions & allergies (e.g. gluten-free, dairy-free, nut/shellfish allergies, vegetarian).\n"
        "  2. Food preferences & favorite cuisines (e.g. loves Mediterranean/Asian, high-protein focus, dislikes cilantro/spicy food).\n"
        "  3. Workday schedule patterns & cook time budgets (e.g. sprint days needing <=15 min express meals vs. relaxed cooking days).\n"
        "  4. Available kitchen appliances (e.g. air fryer, Instant Pot, blender, cast-iron skillet) and pantry staples.\n"
        "  5. Household size and meal prep habits (e.g. single-portion, lunch leftovers for dinner, shopping frequency).\n"
        "- When the user shares new dietary constraints, favorites, or schedule habits, acknowledge them naturally and use them in recommendations.\n\n"
        "Key capabilities:\n"
        "- When planning meals or when the user mentions their day/availability, use `check_daily_schedule` to evaluate their meeting load and recommend the best time tier: 'express' (<=15 min) for busy sprint days, 'standard' (<=30 min), or 'relaxed' (45+ min).\n"
        "- Use `search_recipes` to find matching meals from Firestore using filters like meal_type, time_tier, max_prep_time_minutes, or dietary_tag.\n"
        "- Use `search_online_recipes` when the user asks for new ideas, international recipes, or ingredients not covered in the local Firestore collection (fetches real recipes from TheMealDB).\n"
        "- Use `get_recipe_details` to retrieve complete ingredient lists, step-by-step instructions, and nutritional macros.\n"
        "- Use `save_recipe` when the user wants to add a new favorite dish or store a customized recipe in Firestore.\n"
        "- Use `generate_dish_image` to create an appetizing photo preview of a dish and get a public Cloud Storage image URL.\n"
        "- Use `generate_grocery_list` to consolidate ingredients across selected recipes into an organized supermarket shopping checklist grouped by aisle.\n"
        "- Be concise, practical, and helpful with nutrition, ingredients, and prep times."
    ),
    tools=[
        PreloadMemoryTool(),
        search_recipes,
        search_online_recipes,
        get_recipe_details,
        save_recipe,
        generate_dish_image,
        generate_grocery_list,
        check_daily_schedule,
        get_weather,
        get_current_time,
    ],
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
