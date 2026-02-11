"""Bilingual message templates for notification tasks."""

# ─── Weekly Report ────────────────────────────────────────────────────

WEEKLY_REPORT_AR = (
    "📊 *التقرير الأسبوعي للاستهلاك*\n\n"
    "المعدل اليومي: {avg_daily_kwh} كيلوواط\n"
    "إجمالي الأسبوع: {total_kwh} كيلوواط\n"
    "التكلفة اليومية: {avg_daily_cost_fils} فلس\n"
    "{change_line}"
)

WEEKLY_REPORT_EN = (
    "📊 *Weekly Consumption Report*\n\n"
    "Daily average: {avg_daily_kwh} kWh\n"
    "Weekly total: {total_kwh} kWh\n"
    "Daily cost: {avg_daily_cost_fils} fils\n"
    "{change_line}"
)

WEEKLY_IMPROVED_AR = "✅ تحسن {change_percent}% مقارنة بالأسبوع السابق"
WEEKLY_IMPROVED_EN = "✅ Improved {change_percent}% vs last week"

WEEKLY_INCREASED_AR = "⚠️ ارتفاع {change_percent}% مقارنة بالأسبوع السابق"
WEEKLY_INCREASED_EN = "⚠️ Increased {change_percent}% vs last week"

WEEKLY_STABLE_AR = "➖ مستقر مقارنة بالأسبوع السابق"
WEEKLY_STABLE_EN = "➖ Stable vs last week"

# ─── Spike Alert ──────────────────────────────────────────────────────

SPIKE_ALERT_AR = (
    "⚡ *تنبيه ارتفاع مفاجئ*\n\n"
    "تم رصد ارتفاع في الاستهلاك:\n"
    "القدرة: {power_kw} كيلوواط\n"
    "الوقت: {time}\n"
    "أعلى من المعتاد بـ {factor}x\n\n"
    "💡 تحقق من الأجهزة التي كانت تعمل في ذلك الوقت."
)

SPIKE_ALERT_EN = (
    "⚡ *Spike Alert*\n\n"
    "Unusual consumption detected:\n"
    "Power: {power_kw} kW\n"
    "Time: {time}\n"
    "{factor}x above normal\n\n"
    "💡 Check which appliances were running at that time."
)

# ─── Plan Verification Results ────────────────────────────────────────

PLAN_RESULT_IMPROVED_AR = (
    "🎉 *نتائج خطة التوفير*\n\n"
    "الخطة: {plan_summary}\n"
    "النتيجة: تحسن بنسبة {change_percent}%\n"
    "التوفير الشهري المتوقع: {savings_jod} دينار\n\n"
    "أحسنت! استمر على هذا النهج."
)

PLAN_RESULT_IMPROVED_EN = (
    "🎉 *Plan Verification Results*\n\n"
    "Plan: {plan_summary}\n"
    "Result: Improved by {change_percent}%\n"
    "Estimated monthly savings: {savings_jod} JOD\n\n"
    "Great job! Keep it up."
)

PLAN_RESULT_NOT_IMPROVED_AR = (
    "📋 *نتائج خطة التوفير*\n\n"
    "الخطة: {plan_summary}\n"
    "النتيجة: تغير بنسبة {change_percent}%\n"
    "لم يتحقق التوفير المطلوب بعد.\n\n"
    "💡 هل تحتاج مساعدة في تعديل الخطة؟ أرسل \"تعديل الخطة\"."
)

PLAN_RESULT_NOT_IMPROVED_EN = (
    "📋 *Plan Verification Results*\n\n"
    "Plan: {plan_summary}\n"
    "Result: Changed by {change_percent}%\n"
    "Target savings not yet achieved.\n\n"
    "💡 Need help adjusting the plan? Send \"adjust plan\"."
)
