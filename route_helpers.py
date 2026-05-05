from datetime import datetime, timedelta
import math

import pytz
from werkzeug.security import generate_password_hash

from app import TASHKENT_TZ


PLAN_DEFINITIONS = {
    "basic": {
        "plan": "basic",
        "label": "Basic",
        "max_products": 25,
        "max_categories": 5,
        "ai_enabled": False,
        "description": "Kichik inventar va asosiy boshqaruv uchun qulay reja.",
    },
    "standard": {
        "plan": "standard",
        "label": "Standard",
        "max_products": 75,
        "max_categories": 12,
        "ai_enabled": True,
        "description": "AI insightlar, kengroq hisobotlar va o'sayotgan biznes uchun mos reja.",
    },
    "premium": {
        "plan": "premium",
        "label": "Premium",
        "max_products": None,
        "max_categories": None,
        "ai_enabled": True,
        "description": "Cheksiz inventar, chuqur tahlil va to'liq nazorat uchun maksimal reja.",
    },
}


def set_user_password(user, raw_password, *, is_temp_password=False):
    password = (raw_password or "").strip()
    if not password:
        return
    user.password_hash = generate_password_hash(password)
    user.password_plain = password
    user.is_temp_password = is_temp_password


def subscription_days_left(user):
    expires_at = getattr(user, "subscription_expires_at", None)
    if not expires_at:
        return None
    now_utc = datetime.utcnow()
    seconds_left = (expires_at - now_utc).total_seconds()
    return int(math.ceil(seconds_left / 86400.0))


def _enrich_plan(definition):
    enriched = dict(definition)
    max_products = enriched.get("max_products")
    max_categories = enriched.get("max_categories")
    enriched["max_products_label"] = "Cheksiz" if max_products is None else str(max_products)
    enriched["max_categories_label"] = "Cheksiz" if max_categories is None else str(max_categories)
    enriched["ai_label"] = "Mavjud" if enriched.get("ai_enabled") else "Mavjud emas"
    enriched["feature_points"] = [
        f"Mahsulotlar: {enriched['max_products_label']}",
        f"Kategoriyalar: {enriched['max_categories_label']}",
        f"AI tahlil: {enriched['ai_label']}",
    ]
    return enriched


def get_plan_catalog():
    return [_enrich_plan(PLAN_DEFINITIONS[key]) for key in ("basic", "standard", "premium")]


def get_plan_config(user):
    plan = (getattr(user, "subscription_plan", None) or "basic").lower()
    return _enrich_plan(PLAN_DEFINITIONS.get(plan, PLAN_DEFINITIONS["basic"]))


def build_plan_usage(plan_details, total_products, total_categories):
    def make_usage(current, limit):
        if limit is None:
            return {
                "current": current,
                "limit": None,
                "remaining": None,
                "percent": None,
                "label": f"{current} / Cheksiz",
                "is_near_limit": False,
                "is_full": False,
            }

        percent = 0 if limit <= 0 else min(int(round((current / limit) * 100)), 100)
        remaining = max(limit - current, 0)
        return {
            "current": current,
            "limit": limit,
            "remaining": remaining,
            "percent": percent,
            "label": f"{current} / {limit}",
            "is_near_limit": percent >= 80,
            "is_full": current >= limit,
        }

    products_usage = make_usage(total_products, plan_details.get("max_products"))
    categories_usage = make_usage(total_categories, plan_details.get("max_categories"))

    warnings = []
    if products_usage["is_full"]:
        warnings.append("Mahsulot limiti to'lgan, yangi mahsulot qo'shish uchun tarifni yangilash kerak.")
    elif products_usage["is_near_limit"]:
        warnings.append("Mahsulot limitiga yaqinlashyapsiz, zaxira joyni oldindan rejalashtiring.")

    if categories_usage["is_full"]:
        warnings.append("Kategoriya limiti to'lgan, yangi kategoriya qo'shish uchun tarifni yangilash kerak.")
    elif categories_usage["is_near_limit"]:
        warnings.append("Kategoriya limitiga yaqinlashyapsiz, tuzilmani soddalashtirish foydali bo'ladi.")

    return {
        "products": products_usage,
        "categories": categories_usage,
        "warnings": warnings,
    }


def generate_ai_report_insights(
    *,
    plan_details,
    report_sessions,
    total_revenue,
    session_revenue,
    products_revenue,
    top_products,
    top_rooms,
    inventory_products,
    plan_usage,
    period_label,
):
    if not plan_details.get("ai_enabled"):
        return []

    insights = []
    total_sessions = len(report_sessions)
    products_with_sales = sum(1 for session in report_sessions if (session.products_total or 0) > 0)
    product_attach_rate = (products_with_sales / total_sessions * 100) if total_sessions else 0
    products_share = (products_revenue / total_revenue * 100) if total_revenue else 0
    avg_session_value = (total_revenue / total_sessions) if total_sessions else 0

    low_stock_products = [
        product for product in inventory_products
        if product.stock_quantity is not None and product.stock_quantity <= product.min_stock_alert
    ]
    out_of_stock_products = [
        product for product in inventory_products
        if product.stock_quantity is None or product.stock_quantity <= 0
    ]
    top_product_names = {name for name, _ in top_products[:5]}
    urgent_restock = [product.name for product in low_stock_products if product.name in top_product_names]

    if total_sessions == 0:
        insights.append({
            "tone": "warning",
            "icon": "bi-activity",
            "title": "Faollik past",
            "message": f"{period_label} davomida yopilgan seanslar topilmadi. Reklama, aksiya yoki mijozni qayta jalb qilish takliflarini ishga tushirish kerak.",
        })
    else:
        insights.append({
            "tone": "info",
            "icon": "bi-cpu",
            "title": "Asosiy signal",
            "message": f"{period_label} bo'yicha o'rtacha tushum {avg_session_value:,.0f} so'm va mahsulot biriktirish darajasi {product_attach_rate:.0f}% ni tashkil qildi.",
        })

    if products_share < 15 and total_sessions >= 3:
        insights.append({
            "tone": "primary",
            "icon": "bi-cup-hot",
            "title": "Qo'shimcha savdo imkoniyati",
            "message": f"Mahsulot savdosi tushumning atigi {products_share:.0f}% ini berdi. Ichimlik yoki snack kombo takliflari seansga qo'shimcha daromad olib kelishi mumkin.",
        })
    elif products_share >= 30:
        insights.append({
            "tone": "success",
            "icon": "bi-graph-up-arrow",
            "title": "Mahsulot savdosi kuchli",
            "message": f"Mahsulotlar {products_share:.0f}% ulush bilan yaxshi ishlayapti. Eng ko'p sotilgan pozitsiyalarni aksiyada ushlab turish foydali bo'ladi.",
        })

    if top_rooms:
        top_room_name, top_room_stats = top_rooms[0]
        room_share = (top_room_stats["revenue"] / total_revenue * 100) if total_revenue else 0
        if room_share >= 45:
            insights.append({
                "tone": "info",
                "icon": "bi-house-door",
                "title": "Xona bo'yicha yetakchi nuqta",
                "message": f'"{top_room_name}" xonasi tushumning {room_share:.0f}% ini olib keldi. Shu xona uchun premium slotlar yoki narx testi foyda berishi mumkin.',
            })

    if out_of_stock_products:
        insights.append({
            "tone": "danger",
            "icon": "bi-exclamation-triangle",
            "title": "Zudlik bilan to'ldirish kerak",
            "message": f"{len(out_of_stock_products)} ta mahsulot tugagan. Savdo yo'qotilishini oldini olish uchun zaxirani yangilang.",
        })
    elif urgent_restock:
        insights.append({
            "tone": "warning",
            "icon": "bi-box-seam",
            "title": "Tez sotilayotgan mahsulot kamaygan",
            "message": f"{', '.join(urgent_restock[:3])} tez sotilyapti va minimal zaxiraga yaqinlashgan. Oldindan buyurtma berish tavsiya etiladi.",
        })

    if plan_usage["products"]["is_near_limit"] or plan_usage["categories"]["is_near_limit"]:
        insights.append({
            "tone": "secondary",
            "icon": "bi-layers",
            "title": "Tarif yuklamasi oshmoqda",
            "message": "Hozirgi tarif limitlariga yaqinlashyapsiz. Inventar va kategoriyalar o'sishda davom etsa, Standard yoki Premium reja ishni silliqroq qiladi.",
        })

    return insights[:5]


def utc_range_for_tashkent_date(local_date):
    start_local = TASHKENT_TZ.localize(datetime(local_date.year, local_date.month, local_date.day, 0, 0, 0))
    end_local = start_local + timedelta(days=1)
    start_utc = start_local.astimezone(pytz.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(pytz.utc).replace(tzinfo=None)
    return start_utc, end_utc


def utc_range_for_tashkent_dates(start_date_inclusive, end_date_inclusive):
    start_utc, _ = utc_range_for_tashkent_date(start_date_inclusive)
    end_utc, _ = utc_range_for_tashkent_date(end_date_inclusive + timedelta(days=1))
    return start_utc, end_utc


def utc_range_for_tashkent_month(year, month):
    start_local = TASHKENT_TZ.localize(datetime(year, month, 1, 0, 0, 0))
    if month == 12:
        end_local = TASHKENT_TZ.localize(datetime(year + 1, 1, 1, 0, 0, 0))
    else:
        end_local = TASHKENT_TZ.localize(datetime(year, month + 1, 1, 0, 0, 0))
    start_utc = start_local.astimezone(pytz.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(pytz.utc).replace(tzinfo=None)
    return start_utc, end_utc
