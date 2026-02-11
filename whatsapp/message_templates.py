"""WhatsApp message templates for KahrabaAI — Arabic and English."""

ONBOARDING_AR = (
    "مرحباً بك في كهرباءAI ⚡🔍\n"
    "محقق الطاقة الذكي — بساعدك تفهم استهلاكك وتوفر بفاتورة الكهرباء.\n\n"
    "عشان أبدأ، أرسلي رقم اشتراكك من فاتورة الكهرباء.\n"
    "الرقم بكون بهالشكل: 01-123456-01\n\n"
    "بتلاقيه على أول صفحة من الفاتورة."
)

ONBOARDING_EN = (
    "Welcome to KahrabaAI ⚡🔍\n"
    "Your Smart Energy Detective — I help you understand your consumption "
    "and reduce your electricity bill.\n\n"
    "To get started, send me your subscription number from your JEPCO bill.\n"
    "It looks like this: 01-123456-01\n\n"
    "You'll find it on the first page of your bill."
)

REGISTRATION_SUCCESS_AR = (
    "تم تسجيلك بنجاح! ✅\n"
    "رقم الاشتراك: {subscription_number}\n\n"
    "جهزت بيانات العداد الذكي. جرب تسألني:\n"
    '- "ليش فاتورتي غالية؟"\n'
    '- "كيف أوفر؟"\n'
    '- "شو وضع استهلاكي؟"'
)

REGISTRATION_SUCCESS_EN = (
    "Registration successful! ✅\n"
    "Subscription: {subscription_number}\n\n"
    "Smart meter data is ready. Try asking:\n"
    '- "Why is my bill so high?"\n'
    '- "How can I save?"\n'
    '- "What does my consumption look like?"'
)

REGISTRATION_CONFLICT_AR = (
    "رقم الاشتراك {subscription_number} مسجل على رقم ثاني.\n"
    "إذا هذا رقمك، تواصل مع الدعم."
)

REGISTRATION_CONFLICT_EN = (
    "Subscription {subscription_number} is already registered "
    "to another number.\n"
    "If this is yours, please contact support."
)

WELCOME_BACK_AR = "مرحباً مجدداً! حسابك مسجل. كيف أقدر أساعدك اليوم؟"

WELCOME_BACK_EN = "Welcome back! Your account is active. How can I help you today?"

FALLBACK_AR = "عذراً، في مشكلة تقنية حالياً. حاول مرة ثانية بعد شوي. 🔧"

FALLBACK_EN = (
    "Sorry, there's a technical issue right now. "
    "Please try again shortly. 🔧"
)

RATE_LIMIT_AR = "عذراً، أرسلت رسائل كثيرة بوقت قصير. حاول مرة ثانية بعد شوي. 🕐"

RATE_LIMIT_EN = (
    "Sorry, you've sent too many messages in a short time. "
    "Please try again shortly. 🕐"
)
