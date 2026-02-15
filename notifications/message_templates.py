"""Bilingual message templates for notification tasks."""

# ─── Weekly Report ────────────────────────────────────────────────────

WEEKLY_REPORT_AR = (
    "📊 *التقرير الأسبوعي للاستهلاك*\n\n"
    "المعدل اليومي: {avg_daily_kwh} كيلوواط\n"
    "إجمالي الأسبوع: {total_kwh} كيلوواط\n"
    "{change_line}"
)

WEEKLY_REPORT_EN = (
    "📊 *Weekly Consumption Report*\n\n"
    "Daily average: {avg_daily_kwh} kWh\n"
    "Weekly total: {total_kwh} kWh\n"
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

# ─── Plan Created Confirmation ───────────────────────────────────────

PLAN_CREATED_AR = (
    "✅ *تم حفظ خطة التوفير*\n\n"
    "الخطة: {plan_summary}\n"
    "سنتابع استهلاكك ونرسل لك النتائج بتاريخ {verify_date}.\n\n"
    "💡 طبّق الخطة وراقب استهلاكك اليومي."
)

PLAN_CREATED_EN = (
    "✅ *Optimization Plan Saved*\n\n"
    "Plan: {plan_summary}\n"
    "We'll monitor your usage and send results on {verify_date}.\n\n"
    "💡 Follow the plan and watch your daily consumption."
)

# ─── Plan Verification Results ────────────────────────────────────────

PLAN_RESULT_IMPROVED_AR = (
    "🎉 *نتائج خطة التوفير*\n\n"
    "الخطة: {plan_summary}\n"
    "النتيجة: تحسن بنسبة {change_percent}%\n"
    "التوفير اليومي المتوقع: {savings_kwh} كيلوواط\n\n"
    "أحسنت! استمر على هذا النهج."
)

PLAN_RESULT_IMPROVED_EN = (
    "🎉 *Plan Verification Results*\n\n"
    "Plan: {plan_summary}\n"
    "Result: Improved by {change_percent}%\n"
    "Estimated daily savings: {savings_kwh} kWh\n\n"
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

# ─── Plan Abandoned ─────────────────────────────────────────────────

PLAN_ABANDONED_AR = (
    "🗑️ *تم إلغاء الخطة*\n\n"
    "الخطة: {plan_summary}\n\n"
    "يمكنك إنشاء خطة جديدة في أي وقت."
)

PLAN_ABANDONED_EN = (
    "🗑️ *Plan Cancelled*\n\n"
    "Plan: {plan_summary}\n\n"
    "You can create a new plan anytime."
)
