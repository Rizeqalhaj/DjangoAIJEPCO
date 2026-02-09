"""
RAG retriever stub.

Returns hardcoded energy tips and tariff info until Phase 5 adds ChromaDB.
"""

_KNOWLEDGE_BASE = [
    {
        "title": "JEPCO Residential Tariff Tiers",
        "title_ar": "شرائح التعرفة السكنية",
        "content": (
            "JEPCO residential tariff has 7 tiers: "
            "0-160 kWh @ 33 fils/kWh, "
            "161-320 kWh @ 72 fils/kWh, "
            "321-480 kWh @ 86 fils/kWh, "
            "481-640 kWh @ 114 fils/kWh, "
            "641-800 kWh @ 158 fils/kWh, "
            "801-1000 kWh @ 200 fils/kWh, "
            "1000+ kWh @ 265 fils/kWh. "
            "Fixed charge: 500 fils/month (single phase), 1500 fils/month (three phase)."
        ),
        "source": "JEPCO Tariff Schedule 2025",
        "keywords": ["tariff", "tier", "rate", "price", "fils", "kwh", "شريحة", "تعرفة", "سعر"],
    },
    {
        "title": "Time-of-Use (TOU) Periods",
        "title_ar": "فترات التعرفة حسب الوقت",
        "content": (
            "TOU periods in Jordan: "
            "Off-Peak (خارج الذروة): 05:00-14:00, "
            "Partial Peak (ذروة جزئية): 14:00-17:00 and 23:00-05:00, "
            "Peak (وقت الذروة): 17:00-23:00. "
            "Electricity is cheapest during off-peak hours."
        ),
        "source": "EMRC TOU Schedule",
        "keywords": ["tou", "peak", "off-peak", "hours", "time", "ذروة", "وقت", "ساعات"],
    },
    {
        "title": "EV Charging TOU Rates",
        "title_ar": "تعرفة شحن السيارات الكهربائية",
        "content": (
            "EV home charging TOU rates: "
            "Off-peak: 108 fils/kWh, Partial peak: 118 fils/kWh, Peak: 160 fils/kWh. "
            "EV public charging: Off-peak: 103 fils/kWh, Partial peak: 113 fils/kWh, Peak: 133 fils/kWh. "
            "Charging during off-peak (5AM-2PM) saves up to 32% compared to peak."
        ),
        "source": "EMRC EV Tariff 2025",
        "keywords": ["ev", "charging", "car", "electric", "vehicle", "سيارة", "شحن", "كهربائية"],
    },
    {
        "title": "Water Heater Energy Saving Tips",
        "title_ar": "نصائح لتوفير طاقة سخان الماء",
        "content": (
            "A typical water heater uses 2-3 kW. Running it during peak hours (5PM-11PM) "
            "costs significantly more. Tips: "
            "1. Use a timer to heat water during off-peak (5AM-2PM). "
            "2. Lower thermostat to 55°C. "
            "3. Insulate the tank and pipes. "
            "4. A 2.5kW heater running 2 hours daily at peak costs ~640 fils vs ~432 fils at off-peak."
        ),
        "source": "KahrabaAI Energy Tips",
        "keywords": ["water", "heater", "سخان", "ماء", "timer", "مؤقت", "hot"],
    },
    {
        "title": "Air Conditioning Optimization",
        "title_ar": "تحسين استخدام المكيف",
        "content": (
            "AC units consume 1.5-3.5 kW. Tips to reduce AC costs: "
            "1. Set temperature to 24°C (not 18°C) — each degree lower adds ~8% consumption. "
            "2. Use a programmable thermostat. "
            "3. Close curtains during afternoon sun (2PM-5PM). "
            "4. Clean filters monthly — dirty filters increase consumption 15-25%. "
            "5. Pre-cool the house during off-peak morning hours."
        ),
        "source": "KahrabaAI Energy Tips",
        "keywords": ["ac", "air", "conditioning", "cooling", "مكيف", "تبريد", "حرارة", "temperature"],
    },
    {
        "title": "EV Charging Best Practices",
        "title_ar": "أفضل ممارسات شحن السيارة الكهربائية",
        "content": (
            "EV charging at home typically draws 3-7 kW. "
            "Best practices: "
            "1. Schedule charging for off-peak hours (5AM-2PM) or late night. "
            "2. A 7kW charger running 4 hours at peak costs 4,480 fils vs 3,024 fils at off-peak. "
            "3. Daily savings of ~1,456 fils (1.46 JOD), monthly savings of ~43.7 JOD. "
            "4. Most EVs have built-in charging schedules — use them!"
        ),
        "source": "KahrabaAI Energy Tips",
        "keywords": ["ev", "charging", "schedule", "night", "شحن", "سيارة", "ليل", "جدول"],
    },
    {
        "title": "Understanding Your Electricity Bill",
        "title_ar": "فهم فاتورة الكهرباء",
        "content": (
            "Your JEPCO bill includes: "
            "1. Fixed charge (500 fils single-phase, 1500 fils three-phase). "
            "2. Energy charge based on tiered rates (consumption in kWh). "
            "3. The more you consume, the higher the per-kWh rate. "
            "4. Reducing from 800 kWh to 500 kWh doesn't just save 300 kWh — "
            "it saves the EXPENSIVE kWh (tiers 4-5 at 114-158 fils vs tier 1-3 at 33-86 fils)."
        ),
        "source": "KahrabaAI Energy Tips",
        "keywords": ["bill", "فاتورة", "understand", "فهم", "high", "غالي", "expensive", "charge"],
    },
    {
        "title": "Solar Net Metering in Jordan",
        "title_ar": "صافي القياس للطاقة الشمسية",
        "content": (
            "Jordan allows net metering for residential solar installations. "
            "Key facts: "
            "1. Excess generation is credited at the retail tariff rate. "
            "2. System size is limited to match your average consumption. "
            "3. Average payback period is 4-6 years. "
            "4. JEPCO handles meter replacement for bidirectional metering."
        ),
        "source": "EMRC Solar Regulations",
        "keywords": ["solar", "شمسي", "net metering", "panel", "طاقة", "لوح", "generation"],
    },
    {
        "title": "Common Appliance Power Consumption",
        "title_ar": "استهلاك الأجهزة المنزلية",
        "content": (
            "Typical appliance consumption in Jordan: "
            "AC unit: 1.5-3.5 kW, Water heater: 2-3 kW, "
            "Washing machine: 0.5-2 kW, Refrigerator: 0.1-0.4 kW, "
            "TV: 0.05-0.2 kW, LED bulb: 0.01 kW, Iron: 1-2.5 kW, "
            "Oven: 2-5 kW, EV charger: 3-7 kW. "
            "Water heater is like running 25 LED bulbs at once!"
        ),
        "source": "KahrabaAI Energy Tips",
        "keywords": ["appliance", "consumption", "جهاز", "استهلاك", "power", "kw", "watt"],
    },
    {
        "title": "Spike Detection and Investigation",
        "title_ar": "كشف والتحقيق في الارتفاعات المفاجئة",
        "content": (
            "A consumption spike is when power draw exceeds 2x the normal level for that hour. "
            "Common causes: "
            "1. Water heater turning on during peak. "
            "2. EV charging at peak hours. "
            "3. Multiple AC units running simultaneously. "
            "4. Electric oven usage during peak. "
            "The smart meter records data every 15 minutes — "
            "we can pinpoint exactly when spikes happen."
        ),
        "source": "KahrabaAI Energy Tips",
        "keywords": ["spike", "ارتفاع", "high", "sudden", "مفاجئ", "unusual", "غير طبيعي"],
    },
]


def search(query: str, n_results: int = 3) -> list[dict]:
    """
    Search the knowledge base for relevant information.

    Stub implementation: keyword matching against hardcoded knowledge base.
    Phase 5 will replace this with ChromaDB vector search.
    """
    query_lower = query.lower()
    query_words = set(query_lower.split())

    scored = []
    for entry in _KNOWLEDGE_BASE:
        score = 0
        for keyword in entry["keywords"]:
            if keyword in query_lower:
                score += 2
            elif keyword in query_words:
                score += 1
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for _, entry in scored[:n_results]:
        results.append({
            "title": entry["title"],
            "content": entry["content"],
            "source": entry["source"],
        })

    if not results:
        # Return the most general tips if no keyword match
        for entry in _KNOWLEDGE_BASE[:n_results]:
            results.append({
                "title": entry["title"],
                "content": entry["content"],
                "source": entry["source"],
            })

    return results
