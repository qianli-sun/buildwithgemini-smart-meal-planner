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

"""Seed script to populate Firestore with initial healthy recipes.

Important: FIRESTORE_PROJECT_ID is hardcoded as a string because Agent Platform
runtime returns the numeric project number from google.auth.default() and
GOOGLE_CLOUD_PROJECT, which breaks Firestore (default) database lookups.
"""

from google.cloud import firestore

# Hardcoded project ID as string - DO NOT change to env var or google.auth.default()
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-04-5805be9550d8"
COLLECTION_NAME = "recipes"

SEED_RECIPES = [
    {
        "id": "express-chickpea-bowl",
        "name": "Mediterranean Chickpea Salad Bowl",
        "meal_type": "lunch",
        "time_tier": "express",
        "prep_time_minutes": 10,
        "cook_time_minutes": 0,
        "total_time_minutes": 10,
        "servings": 1,
        "cuisine": "Mediterranean",
        "dietary_tags": ["vegetarian", "vegan", "gluten-free", "healthy", "high-fiber"],
        "calories": 420,
        "macros": {"protein_g": 18, "carbs_g": 54, "fat_g": 14},
        "description": "A crisp, refreshing no-cook lunch bowl with chickpeas, diced cucumber, tomatoes, and kalamata olives tossed in lemon-herb dressing.",
        "ingredients": [
            {"item": "Canned chickpeas", "amount": "1 can (rinsed & drained)", "category": "pantry"},
            {"item": "English cucumber", "amount": "1/2 cup diced", "category": "produce"},
            {"item": "Cherry tomatoes", "amount": "1/2 cup halved", "category": "produce"},
            {"item": "Kalamata olives", "amount": "2 tbsp sliced", "category": "pantry"},
            {"item": "Olive oil & lemon dressing", "amount": "2 tbsp", "category": "condiments"},
        ],
        "instructions": [
            "Rinse and drain the canned chickpeas.",
            "Dice cucumber and halve cherry tomatoes.",
            "Combine chickpeas, vegetables, and olives in a bowl.",
            "Drizzle with olive oil and fresh lemon juice; toss and serve immediately.",
        ],
    },
    {
        "id": "express-berry-overnight-oats",
        "name": "Berry Chia Overnight Oats",
        "meal_type": "breakfast",
        "time_tier": "express",
        "prep_time_minutes": 5,
        "cook_time_minutes": 0,
        "total_time_minutes": 5,
        "servings": 1,
        "cuisine": "American",
        "dietary_tags": ["vegetarian", "gluten-free", "healthy", "meal-prep"],
        "calories": 350,
        "macros": {"protein_g": 14, "carbs_g": 48, "fat_g": 10},
        "description": "Creamy rolled oats soaked in almond milk with chia seeds, topped with fresh mixed blueberries and strawberries.",
        "ingredients": [
            {"item": "Rolled oats", "amount": "1/2 cup", "category": "pantry"},
            {"item": "Unsweetened almond milk", "amount": "3/4 cup", "category": "dairy-alternative"},
            {"item": "Chia seeds", "amount": "1 tbsp", "category": "pantry"},
            {"item": "Fresh berries", "amount": "1/2 cup", "category": "produce"},
            {"item": "Maple syrup", "amount": "1 tsp", "category": "pantry"},
        ],
        "instructions": [
            "Stir oats, almond milk, and chia seeds together in a mason jar.",
            "Refrigerate overnight or for at least 4 hours.",
            "Top with fresh berries and maple syrup before eating.",
        ],
    },
    {
        "id": "express-avocado-egg-toast",
        "name": "Smashed Avocado & Fried Egg Toast",
        "meal_type": "breakfast",
        "time_tier": "express",
        "prep_time_minutes": 5,
        "cook_time_minutes": 5,
        "total_time_minutes": 10,
        "servings": 1,
        "cuisine": "Modern",
        "dietary_tags": ["vegetarian", "healthy", "high-protein"],
        "calories": 380,
        "macros": {"protein_g": 16, "carbs_g": 28, "fat_g": 22},
        "description": "Crispy whole-grain sourdough toast topped with creamy smashed avocado, chili flakes, and a sunny-side-up pasture-raised egg.",
        "ingredients": [
            {"item": "Whole grain sourdough bread", "amount": "2 slices", "category": "bakery"},
            {"item": "Ripe avocado", "amount": "1/2 avocado", "category": "produce"},
            {"item": "Egg", "amount": "1 large", "category": "dairy"},
            {"item": "Red pepper flakes & sea salt", "amount": "to taste", "category": "spices"},
        ],
        "instructions": [
            "Toast the sourdough slices until golden and crisp.",
            "Fry the egg in a lightly oiled skillet to desired doneness.",
            "Mash the avocado with salt and spread across toast.",
            "Top with the fried egg and red pepper flakes.",
        ],
    },
    {
        "id": "standard-turkey-skillet",
        "name": "20-Minute Lean Turkey & Zucchini Skillet",
        "meal_type": "lunch",
        "time_tier": "standard",
        "prep_time_minutes": 5,
        "cook_time_minutes": 15,
        "total_time_minutes": 20,
        "servings": 2,
        "cuisine": "American",
        "dietary_tags": ["healthy", "high-protein", "low-carb", "gluten-free"],
        "calories": 410,
        "macros": {"protein_g": 36, "carbs_g": 14, "fat_g": 18},
        "description": "Ground lean turkey browned with diced zucchini, bell pepper, and garlic herb seasoning for a fast, macro-friendly lunch.",
        "ingredients": [
            {"item": "Lean ground turkey (93/7)", "amount": "0.75 lb", "category": "meat"},
            {"item": "Zucchini", "amount": "1 medium (chopped)", "category": "produce"},
            {"item": "Red bell pepper", "amount": "1 medium (chopped)", "category": "produce"},
            {"item": "Garlic powder & oregano", "amount": "1 tsp each", "category": "spices"},
            {"item": "Olive oil", "amount": "1 tbsp", "category": "pantry"},
        ],
        "instructions": [
            "Heat olive oil in a large skillet over medium-high heat.",
            "Add ground turkey, break apart, and cook until browned (6-8 mins).",
            "Toss in chopped zucchini and bell pepper; sauté for 5 minutes until tender-crisp.",
            "Season with garlic powder, oregano, salt, and black pepper.",
        ],
    },
    {
        "id": "standard-sesame-salmon",
        "name": "25-Minute Sesame Ginger Glazed Salmon",
        "meal_type": "dinner",
        "time_tier": "standard",
        "prep_time_minutes": 10,
        "cook_time_minutes": 15,
        "total_time_minutes": 25,
        "servings": 2,
        "cuisine": "Asian",
        "dietary_tags": ["pescatarian", "healthy", "high-protein", "omega-3"],
        "calories": 480,
        "macros": {"protein_g": 38, "carbs_g": 16, "fat_g": 26},
        "description": "Pan-seared wild salmon fillets glazed with tamari, ginger, and sesame, served alongside tender steamed broccoli.",
        "ingredients": [
            {"item": "Salmon fillets", "amount": "2 (6 oz each)", "category": "seafood"},
            {"item": "Broccoli florets", "amount": "2 cups", "category": "produce"},
            {"item": "Low-sodium tamari or soy sauce", "amount": "2 tbsp", "category": "condiments"},
            {"item": "Grated fresh ginger", "amount": "1 tsp", "category": "produce"},
            {"item": "Sesame oil & seeds", "amount": "1 tsp each", "category": "pantry"},
        ],
        "instructions": [
            "Whisk tamari, ginger, and sesame oil in a small bowl.",
            "Sear salmon skin-side down in a hot skillet for 4-5 minutes, flip and cook 3-4 minutes.",
            "Brush glaze over the salmon during the last minute of cooking.",
            "Steam broccoli florets until bright green and serve with salmon.",
        ],
    },
    {
        "id": "standard-coconut-lentil-curry",
        "name": "30-Minute Coconut Red Lentil Dahl",
        "meal_type": "dinner",
        "time_tier": "standard",
        "prep_time_minutes": 10,
        "cook_time_minutes": 20,
        "total_time_minutes": 30,
        "servings": 3,
        "cuisine": "Indian",
        "dietary_tags": ["vegan", "vegetarian", "gluten-free", "healthy", "high-fiber"],
        "calories": 390,
        "macros": {"protein_g": 17, "carbs_g": 52, "fat_g": 12},
        "description": "Warming red lentils simmered in coconut milk, diced tomatoes, turmeric, and cumin, finished with fresh baby spinach.",
        "ingredients": [
            {"item": "Dry red lentils", "amount": "1 cup", "category": "pantry"},
            {"item": "Light coconut milk", "amount": "1 can (13.5 oz)", "category": "pantry"},
            {"item": "Canned diced tomatoes", "amount": "1 can (14.5 oz)", "category": "pantry"},
            {"item": "Baby spinach", "amount": "2 cups", "category": "produce"},
            {"item": "Curry powder, cumin, turmeric", "amount": "1 tsp each", "category": "spices"},
        ],
        "instructions": [
            "Rinse red lentils until water runs clear.",
            "In a pot, bring coconut milk, tomatoes, lentils, and spices to a gentle boil.",
            "Reduce heat and simmer for 15-18 minutes until lentils are soft and creamy.",
            "Stir in fresh spinach until wilted; season with salt and lime juice.",
        ],
    },
    {
        "id": "relaxed-sheet-pan-roast-chicken",
        "name": "Herb-Roasted Chicken & Root Vegetables",
        "meal_type": "dinner",
        "time_tier": "relaxed",
        "prep_time_minutes": 15,
        "cook_time_minutes": 45,
        "total_time_minutes": 60,
        "servings": 4,
        "cuisine": "Mediterranean",
        "dietary_tags": ["healthy", "gluten-free", "high-protein", "batch-cooking"],
        "calories": 520,
        "macros": {"protein_g": 42, "carbs_g": 34, "fat_g": 22},
        "description": "Juicy bone-in chicken thighs roasted on a sheet pan with sweet potatoes, red onion wedges, rosemary, and whole garlic cloves.",
        "ingredients": [
            {"item": "Chicken thighs (bone-in)", "amount": "4 pieces (~1.5 lbs)", "category": "meat"},
            {"item": "Sweet potatoes", "amount": "2 medium (cubed)", "category": "produce"},
            {"item": "Red onion", "amount": "1 large (wedges)", "category": "produce"},
            {"item": "Fresh rosemary", "amount": "2 sprigs", "category": "produce"},
            {"item": "Olive oil", "amount": "2 tbsp", "category": "pantry"},
        ],
        "instructions": [
            "Preheat oven to 400°F (200°C).",
            "Toss sweet potatoes and red onions with 1 tbsp olive oil, salt, and pepper on a baking sheet.",
            "Season chicken thighs with remaining olive oil, salt, pepper, and chopped fresh rosemary; arrange between vegetables.",
            "Roast for 40-45 minutes until chicken reaches 165°F and sweet potatoes are caramelized.",
        ],
    },
    {
        "id": "relaxed-spinach-feta-frittata",
        "name": "Weekend Spinach, Mushroom & Feta Frittata",
        "meal_type": "breakfast",
        "time_tier": "relaxed",
        "prep_time_minutes": 15,
        "cook_time_minutes": 25,
        "total_time_minutes": 40,
        "servings": 4,
        "cuisine": "Mediterranean",
        "dietary_tags": ["vegetarian", "gluten-free", "healthy", "high-protein"],
        "calories": 290,
        "macros": {"protein_g": 19, "carbs_g": 6, "fat_g": 21},
        "description": "Fluffy oven-baked frittata loaded with sautéed crimini mushrooms, wilted spinach, and crumbled Greek feta cheese.",
        "ingredients": [
            {"item": "Eggs", "amount": "8 large", "category": "dairy"},
            {"item": "Baby spinach", "amount": "3 cups", "category": "produce"},
            {"item": "Crimini mushrooms", "amount": "1 cup sliced", "category": "produce"},
            {"item": "Feta cheese", "amount": "1/2 cup crumbled", "category": "dairy"},
            {"item": "Olive oil", "amount": "1 tbsp", "category": "pantry"},
        ],
        "instructions": [
            "Preheat oven to 375°F (190°C).",
            "Sauté mushrooms in an oven-safe skillet until browned; add spinach until wilted.",
            "Whisk eggs with a pinch of salt and pepper; pour into skillet over vegetables.",
            "Scatter crumbled feta over the top and bake for 20-25 minutes until set.",
        ],
    },
]


def seed_database() -> None:
    """Writes all seed recipes into Firestore."""
    print(f"Connecting to Firestore using project ID: '{FIRESTORE_PROJECT_ID}'...")
    db = firestore.Client(project=FIRESTORE_PROJECT_ID)
    collection = db.collection(COLLECTION_NAME)

    print(f"Seeding {len(SEED_RECIPES)} recipes into collection '{COLLECTION_NAME}'...")
    batch = db.batch()
    for recipe in SEED_RECIPES:
        doc_ref = collection.document(recipe["id"])
        batch.set(doc_ref, recipe)

    batch.commit()
    print(f"Successfully seeded {len(SEED_RECIPES)} recipes into Firestore '{COLLECTION_NAME}'!")


if __name__ == "__main__":
    seed_database()
