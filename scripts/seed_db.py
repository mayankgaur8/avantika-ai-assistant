"""
Database seed script — inserts initial plans, languages, and countries.
Run once after first migration: python scripts/seed_db.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import AsyncSessionLocal, engine
from backend.app.models.models import Base, Country, Language, Plan, PlanName
from backend.app.services.billing_service import PLAN_CONFIGS


LANGUAGES = [
    {"code": "en", "name": "English", "native_name": "English"},
    {"code": "hi", "name": "Hindi", "native_name": "हिन्दी"},
    {"code": "de", "name": "German", "native_name": "Deutsch"},
    {"code": "fr", "name": "French", "native_name": "Français"},
    {"code": "es", "name": "Spanish", "native_name": "Español"},
    {"code": "ja", "name": "Japanese", "native_name": "日本語"},
    {"code": "zh", "name": "Mandarin Chinese", "native_name": "普通话"},
    {"code": "ar", "name": "Arabic", "native_name": "العربية"},
    {"code": "pt", "name": "Portuguese", "native_name": "Português"},
    {"code": "ru", "name": "Russian", "native_name": "Русский"},
    {"code": "it", "name": "Italian", "native_name": "Italiano"},
    {"code": "ko", "name": "Korean", "native_name": "한국어"},
    {"code": "nl", "name": "Dutch", "native_name": "Nederlands"},
    {"code": "tr", "name": "Turkish", "native_name": "Türkçe"},
]

COUNTRIES = [
    {"code": "IN", "name": "India", "primary_language_code": "hi"},
    {"code": "US", "name": "United States", "primary_language_code": "en"},
    {"code": "GB", "name": "United Kingdom", "primary_language_code": "en"},
    {"code": "DE", "name": "Germany", "primary_language_code": "de"},
    {"code": "FR", "name": "France", "primary_language_code": "fr"},
    {"code": "JP", "name": "Japan", "primary_language_code": "ja"},
    {"code": "CN", "name": "China", "primary_language_code": "zh"},
    {"code": "AE", "name": "UAE", "primary_language_code": "ar"},
    {"code": "AU", "name": "Australia", "primary_language_code": "en"},
    {"code": "CA", "name": "Canada", "primary_language_code": "en"},
    {"code": "SG", "name": "Singapore", "primary_language_code": "en"},
    {"code": "ES", "name": "Spain", "primary_language_code": "es"},
    {"code": "IT", "name": "Italy", "primary_language_code": "it"},
    {"code": "KR", "name": "South Korea", "primary_language_code": "ko"},
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        await _seed_languages(db)
        await _seed_countries(db)
        await _seed_plans(db)
        await db.commit()
        print("Seed complete.")


async def _seed_languages(db: AsyncSession):
    for lang_data in LANGUAGES:
        result = await db.execute(select(Language).where(Language.code == lang_data["code"]))
        if not result.scalar_one_or_none():
            db.add(Language(**lang_data))
            print(f"  Added language: {lang_data['name']}")


async def _seed_countries(db: AsyncSession):
    for country_data in COUNTRIES:
        result = await db.execute(select(Country).where(Country.code == country_data["code"]))
        if not result.scalar_one_or_none():
            db.add(Country(**country_data))
            print(f"  Added country: {country_data['name']}")


async def _seed_plans(db: AsyncSession):
    for plan_name, config in PLAN_CONFIGS.items():
        result = await db.execute(select(Plan).where(Plan.name == plan_name))
        if not result.scalar_one_or_none():
            plan = Plan(
                name=plan_name,
                display_name=config["display_name"],
                monthly_price_inr=config["monthly_price_inr"],
                yearly_price_inr=config["yearly_price_inr"],
                monthly_requests=config["monthly_requests"],
                allow_premium_model=config["allow_premium_model"],
                allow_whatsapp=config["allow_whatsapp"],
                allow_voice=config["allow_voice"],
                allow_travel_packs=config["allow_travel_packs"],
                allow_job_coaching=config["allow_job_coaching"],
                translation_limit_per_day=config["translation_limit_per_day"],
                features=config["features"],
            )
            db.add(plan)
            print(f"  Added plan: {config['display_name']}")


if __name__ == "__main__":
    asyncio.run(seed())
