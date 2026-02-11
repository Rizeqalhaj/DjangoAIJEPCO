"""
Demo conversation walkthroughs for KahrabaAI.

Usage:
    python manage.py run_demo              # Print scripted demo conversations
    python manage.py run_demo --live       # Actually call the agent (needs Groq key)
    python manage.py run_demo --scenario 1 # Run specific demo (1, 2, or 3)
"""

from django.core.management.base import BaseCommand
from accounts.models import Subscriber


DEMO_SCENARIOS = [
    {
        "title": "Demo 1: The EV Peak Charger (Ahmed / أحمد)",
        "phone": "+962791000001",
        "messages": [
            ("user", "مرحبا"),
            ("agent",
             "مرحبا أحمد! أنا محقق الطاقة الذكي ⚡🔍\n"
             "كيف بقدر أساعدك اليوم؟"),
            ("user", "ليش فاتورتي غالية؟"),
            ("agent",
             "خليني أحلل بياناتك...\n\n"
             "📊 ملخص آخر 30 يوم:\n"
             "- المعدل اليومي: ~35 كيلوواط\n"
             "- التكلفة اليومية: ~1,200 فلس\n"
             "- حصة الذروة: ~45%\n\n"
             "بشوف ارتفاع كبير كل يوم من الساعة 7-11 بالليل (~7 كيلوواط).\n"
             "هذا بأوقات الذروة وبكلفك كثير.\n\n"
             "شو بتعمل عادة هالوقت؟"),
            ("user", "بشحن سيارتي لما بوصل عالبيت"),
            ("agent",
             "أكيد! شحن السيارة 7 كيلوواط × 4 ساعات = 28 كيلوواط/يوم بوقت الذروة (160 فلس/كيلوواط).\n"
             "لو شحنتها الساعة 1 بالليل (خارج الذروة - 108 فلس/كيلوواط):\n"
             "💰 توفير تقريبي: ~1.46 دينار/يوم = ~43.7 دينار/شهر\n\n"
             "خليني أسوي خطة توفير؟"),
            ("user", "تمام"),
            ("agent",
             "✅ تم إنشاء خطة التوفير!\n"
             "📋 الخطة: شحن السيارة بأوقات خارج الذروة (1AM-5AM)\n"
             "📅 فترة المراقبة: 7 أيام\n"
             "💰 التوفير المتوقع: ~43.7 دينار/شهر\n\n"
             "رح أتابع معك وأخبرك بالنتائج بعد أسبوع!"),
            ("user", "كيف ماشية الخطة؟"),
            ("agent",
             "📋 تقدم خطتك:\n"
             "✅ استهلاكك نزل ~20%\n"
             "💰 توفير شهري تقريبي: ~40 دينار\n\n"
             "ممتاز! كمّل على هالنظام 💪"),
        ],
    },
    {
        "title": "Demo 2: The Bill Shocked AC User (Sara / سارة)",
        "phone": "+962791000002",
        "messages": [
            ("user", "مرحبا، فاتورتي تضاعفت بالصيف"),
            ("agent",
             "مرحبا سارة! خليني أتحقق من بياناتك...\n\n"
             "📊 ملخص آخر 30 يوم:\n"
             "- المعدل اليومي: ~30 كيلوواط\n"
             "- ارتفاع عن الشهر الماضي: +35%\n\n"
             "بشوف نمط واضح: ارتفاع ~3.5 كيلوواط من الساعة 2-11 بالليل.\n"
             "هذا بالصيف بالذات. شو رأيك السبب؟"),
            ("user", "المكيف بشغله على 20 درجة من الساعة 2"),
            ("agent",
             "مظبوط! المكيف على 20 درجة بوكل كهربا كثير.\n"
             "خليني أسوي خطة:\n\n"
             "1️⃣ ارفع الحرارة على 24°C (توفير ~8% لكل درجة)\n"
             "2️⃣ برّد البيت الصبح من 10-12 (خارج الذروة)\n"
             "3️⃣ نظف فلتر المكيف (فلتر مسكر بزيد الاستهلاك 15-25%)\n"
             "4️⃣ سكر الستاير وقت الشمس (2-5 العصر)\n\n"
             "💰 توفير متوقع: ~25-35 دينار/شهر"),
        ],
    },
    {
        "title": "Demo 3: English User (Omar / عمر)",
        "phone": "+962791000005",
        "messages": [
            ("user", "Hi, how much am I spending?"),
            ("agent",
             "Hi Omar! Let me check your consumption data...\n\n"
             "📊 Last 30 days summary:\n"
             "- Daily average: ~15 kWh\n"
             "- Monthly projected: ~450 kWh\n"
             "- Estimated bill: ~28 JOD\n"
             "- Peak share: only 20%\n\n"
             "Good news: you're mostly consuming during off-peak hours! 🌟"),
            ("user", "How can I save money?"),
            ("agent",
             "Your consumption is already quite efficient! 👍\n\n"
             "Based on your data:\n"
             "1. Your EV charges at night (off-peak) — great!\n"
             "2. Small morning spike 6-8 AM — normal\n"
             "3. Consider running laundry before 2 PM (off-peak)\n\n"
             "💡 You're in tier 3 (~86 fils/kWh). Reducing by 10% "
             "would drop you to tier 2 (~72 fils/kWh) and save ~3 JOD/month."),
        ],
    },
]


class Command(BaseCommand):
    help = "Run demo conversation walkthroughs for KahrabaAI."

    def add_arguments(self, parser):
        parser.add_argument(
            '--live', action='store_true',
            help='Actually call the agent (requires Groq API key and seeded data)',
        )
        parser.add_argument(
            '--scenario', type=int, default=0,
            help='Run specific scenario (1, 2, or 3). 0 = all.',
        )

    def handle(self, *args, **options):
        scenarios = DEMO_SCENARIOS
        if options['scenario']:
            idx = options['scenario'] - 1
            if 0 <= idx < len(DEMO_SCENARIOS):
                scenarios = [DEMO_SCENARIOS[idx]]
            else:
                self.stderr.write(self.style.ERROR(
                    f"Invalid scenario: {options['scenario']}. Use 1-{len(DEMO_SCENARIOS)}."
                ))
                return

        if options['live']:
            self._run_live(scenarios)
        else:
            self._run_scripted(scenarios)

    def _run_scripted(self, scenarios):
        """Print scripted demo conversations."""
        for scenario in scenarios:
            self.stdout.write(self.style.SUCCESS(f"\n{'=' * 60}"))
            self.stdout.write(self.style.SUCCESS(scenario["title"]))
            self.stdout.write(self.style.SUCCESS(f"Phone: {scenario['phone']}"))
            self.stdout.write(self.style.SUCCESS(f"{'=' * 60}\n"))

            for role, text in scenario["messages"]:
                if role == "user":
                    self.stdout.write(self.style.WARNING(f"  User: {text}"))
                else:
                    for line in text.split("\n"):
                        self.stdout.write(f"  Agent: {line}")
                self.stdout.write("")

    def _run_live(self, scenarios):
        """Actually call the agent for each message."""
        from agent.coach import EnergyDetective

        for scenario in scenarios:
            phone = scenario["phone"]
            if not Subscriber.objects.filter(phone_number=phone).exists():
                self.stderr.write(self.style.ERROR(
                    f"Subscriber {phone} not found. Run 'manage.py seed_demo' first."
                ))
                continue

            self.stdout.write(self.style.SUCCESS(f"\n{'=' * 60}"))
            self.stdout.write(self.style.SUCCESS(f"{scenario['title']} (LIVE)"))
            self.stdout.write(self.style.SUCCESS(f"{'=' * 60}\n"))

            agent = EnergyDetective()
            for role, text in scenario["messages"]:
                if role == "user":
                    self.stdout.write(self.style.WARNING(f"  User: {text}"))
                    try:
                        reply = agent.handle_message(phone, text)
                        for line in reply.split("\n"):
                            self.stdout.write(f"  Agent: {line}")
                    except Exception as exc:
                        self.stderr.write(self.style.ERROR(f"  Error: {exc}"))
                    self.stdout.write("")
