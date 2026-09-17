#!/usr/bin/env python3
"""
Ведомость для HR Ак Барс — ежедневная онлайн-газета
Стиль: «Ежедневный пророк» (Гарри Поттер).
Собирает свежие HR-новости за неделю с автопереводом.
"""

import os
import re
import time
import datetime
import feedparser
from jinja2 import Template
# Импортируем оба переводчика
from deep_translator import GoogleTranslator, MyMemoryTranslator

# ============================================================
# 1. НАСТРОЙКИ
# ============================================================

# --- Источники новостей ---
RSS_FEEDS = [
    # --- Российские ---
    {"name": "HBR Россия", "url": "https://hbr-russia.ru/rss/news", "category": "Аналитика", "lang": "ru"},
    {"name": "HR-Portal", "url": "https://hr-portal.ru/rss.xml", "category": "Россия", "lang": "ru"},
    {"name": "HR-Director", "url": "https://www.hr-director.ru/rss", "category": "Россия", "lang": "ru"},
    {"name": "Cossa", "url": "https://www.cossa.ru/rss/", "category": "Технологии", "lang": "ru"},
    {"name": "E-xecutive", "url": "https://www.e-xecutive.ru/rss/all.xml", "category": "Россия", "lang": "ru"},
    {"name": "Forbes Россия", "url": "https://www.forbes.ru/newrss.xml", "category": "Мир", "lang": "ru"},

    # --- Международные (с автопереводом) ---
    {"name": "Josh Bersin", "url": "https://joshbersin.com/feed/", "category": "Аналитика", "lang": "en"},
    {"name": "HR Executive", "url": "https://hrexecutive.com/feed/", "category": "Мир", "lang": "en"},
    {"name": "SHRM", "url": "https://www.shrm.org/rss/news.xml", "category": "Мир", "lang": "en"},
    {"name": "HR Dive", "url": "https://www.hrdive.com/feeds/news/", "category": "Мир", "lang": "en"},
    {"name": "People Matters", "url": "https://www.peoplematters.in/rss/news", "category": "Мир", "lang": "en"},
    {"name": "HR Exchange Network", "url": "https://www.hrexchangenetwork.com/rss/news", "category": "Мир", "lang": "en"},
]

MAX_ARTICLES = 20
OUTPUT_DIR = "docs"
OUTPUT_FILE = "index.html"

# --- Свежесть: новости не старше N суток ---
DAYS_BACK = 7

# --- Фильтр релевантности ---
HR_KEYWORDS_RU = [
    "hr", "эйч-ар", "кадр", "персонал", "сотрудник", "работник",
    "найм", "нанимат", "рекрут", "подбор", "отбор",
    "онбординг", "адаптац", "мотивац", "вовлечён", "вовлечен",
    "обучени", "развити", "карьер", "талант", "компетенц",
    "руководител", "менеджер", "лидерств", "команд",
    "зарплат", "компенсац", "льгот", "бенефит",
    "удержан", "текучест", "увольн", "трудов", "employment",
    "корпоративн", "hr-бренд", "hr бренд", "кадров",
    "релокац", "гибридн", "удалёнк", "удаленк",
    "рекрутинг", "hiring", "talent", "employer",
]

HR_KEYWORDS_EN = [
    "hr ", "hr-", "human resource", "people ops", "people operation",
    "talent", "recruit", "hiring", "hire ", "onboard",
    "employee", "workforce", "workplace", "worker",
    "engagement", "retention", "attrition", "turnover",
    "payroll", "compensation", "benefit", "salary", "wage",
    "performance management", "learning", "development",
    "leadership", "manager", "management", "culture", "dei",
    "diversity", "inclusion", "wellbeing", "well-being",
]

# ============================================================
# 2. HTML-ШАБЛОН (без изменений)
# ============================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ведомость для HR Ак Барс</title>

    <!-- Старинные шрифты с поддержкой кириллицы -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Yeseva+One&family=Lora:ital,wght@0,400;0,600;0,700;1,400&family=Caveat:wght@500&family=PT+Sans:wght@400;700&display=swap" rel="stylesheet">

    <style>
        /* ============================================================
           ПАЛИТРА (пергамент и чернила)
           ============================================================ */

        * { margin: 0; padding: 0; box-sizing: border-box; }

        html, body {
            color: #2b1810;
            font-family: 'Lora', Georgia, serif;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }

        /* Многослойный пергамент: пятна, градиент, оттенки */
        body {
            background-color: #d9c9a3;
            background-image:
                radial-gradient(ellipse at 15% 20%, rgba(139, 90, 43, 0.15) 0%, transparent 40%),
                radial-gradient(ellipse at 85% 30%, rgba(139, 90, 43, 0.10) 0%, transparent 35%),
                radial-gradient(ellipse at 50% 85%, rgba(139, 90, 43, 0.12) 0%, transparent 40%),
                radial-gradient(ellipse at 25% 65%, rgba(139, 90, 43, 0.08) 0%, transparent 30%),
                radial-gradient(ellipse at 75% 75%, rgba(139, 90, 43, 0.06) 0%, transparent 25%),
                linear-gradient(135deg, #efe2c3 0%, #e5d5b3 50%, #d9c9a3 100%);
            background-attachment: fixed;
            padding: 40px 20px;
            min-height: 100vh;
        }

        /* «Газета» — центральный свиток */
        .newspaper {
            max-width: 1180px;
            margin: 0 auto;
            background-color: #ede0c4;
            background-image:
                radial-gradient(circle at 30% 15%, rgba(139, 90, 43, 0.06) 0%, transparent 30%),
                radial-gradient(circle at 70% 60%, rgba(139, 90, 43, 0.05) 0%, transparent 35%),
                radial-gradient(circle at 10% 90%, rgba(139, 90, 43, 0.04) 0%, transparent 25%);
            padding: 55px 60px 45px;
            box-shadow:
                inset 0 0 120px rgba(107, 68, 35, 0.20),
                inset 0 0 30px rgba(107, 68, 35, 0.12),
                0 15px 50px rgba(0, 0, 0, 0.35);
            position: relative;
            border: 1px solid #8b6f47;
        }

        .newspaper::before {
            content: "";
            position: absolute;
            top: 14px; left: 14px; right: 14px; bottom: 14px;
            border: 1px solid #6b4423;
            pointer-events: none;
        }
        .newspaper::after {
            content: "";
            position: absolute;
            top: 22px; left: 22px; right: 22px; bottom: 22px;
            border: 1px solid rgba(107, 68, 35, 0.4);
            pointer-events: none;
        }

        /* ============================================================
           ШАПКА (masthead)
           ============================================================ */

        .masthead {
            text-align: center;
            padding-bottom: 26px;
            margin-bottom: 32px;
            position: relative;
            border-bottom: 2px solid #2b1810;
            z-index: 1;
        }

        .masthead .top-line {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-family: 'PT Sans', Arial, sans-serif;
            font-size: 0.7rem;
            letter-spacing: 3px;
            text-transform: uppercase;
            color: #6b4423;
            padding-bottom: 16px;
            margin-bottom: 24px;
            border-bottom: 1px solid #6b4423;
        }

        .masthead .top-line span:first-child::before { content: "✦ "; }
        .masthead .top-line span:last-child::after  { content: " ✦"; }

        .masthead h1 {
            font-family: 'Yeseva One', Georgia, serif;
            font-weight: 400;
            font-size: 4.6rem;
            letter-spacing: -1px;
            line-height: 1;
            color: #2b1810;
            margin: 6px 0 14px;
            text-shadow:
                1px 1px 0 rgba(139, 111, 71, 0.4),
                2px 2px 4px rgba(43, 24, 16, 0.15);
        }

        .masthead h1 .accent {
            color: #2d5a3d;
            font-style: italic;
            display: inline-block;
            transform: rotate(-2deg);
            margin: 0 6px;
        }

        .masthead .tagline {
            font-family: 'Caveat', cursive;
            font-size: 1.5rem;
            color: #6b4423;
            margin-bottom: 22px;
            letter-spacing: 0.5px;
        }

        .masthead .tagline::before,
        .masthead .tagline::after {
            content: "  ~  ";
            color: #8b6f47;
            font-size: 1.1rem;
        }

        .masthead .bottom-line {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-family: 'PT Sans', Arial, sans-serif;
            font-size: 0.75rem;
            letter-spacing: 2.5px;
            text-transform: uppercase;
            color: #2b1810;
            padding-top: 16px;
            border-top: 1px solid #6b4423;
        }

        .masthead .bottom-line .issue {
            background: #2d5a3d;
            color: #efe2c3;
            padding: 5px 14px;
            letter-spacing: 3px;
            font-weight: 700;
            box-shadow: 1px 1px 0 rgba(43, 24, 16, 0.4);
        }

        /* ============================================================
           СЕТКА ГАЗЕТЫ
           ============================================================ */

        .news-grid {
            column-count: 3;
            column-gap: 36px;
            column-rule: 1px solid #a88b5d;
            position: relative;
            z-index: 1;
        }

        @media (max-width: 1000px) {
            .news-grid { column-count: 2; }
            .masthead h1 { font-size: 3.2rem; }
            .newspaper { padding: 40px 32px 30px; }
        }
        @media (max-width: 640px) {
            .news-grid { column-count: 1; }
            .masthead h1 { font-size: 2.2rem; }
            .newspaper { padding: 28px 22px; }
            .newspaper::before,
            .newspaper::after { display: none; }
            .masthead .top-line,
            .masthead .bottom-line { flex-direction: column; gap: 6px; }
        }

        /* ============================================================
           КАРТОЧКА СТАТЬИ
           ============================================================ */

        .article {
            break-inside: avoid;
            margin-bottom: 28px;
            padding-bottom: 24px;
            border-bottom: 1px dashed #8b6f47;
            animation: fadeIn 0.7s ease-out backwards;
        }
        .article:last-child { border-bottom: none; }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .article.lead h3 {
            font-size: 1.6rem;
            line-height: 1.22;
        }

        .article .category {
            display: inline-block;
            font-family: 'PT Sans', Arial, sans-serif;
            font-size: 0.62rem;
            font-weight: 700;
            letter-spacing: 2.5px;
            text-transform: uppercase;
            color: #2d5a3d;
            margin-bottom: 10px;
            padding: 2px 0 2px 0;
            border-bottom: 1px solid #2d5a3d;
        }
        .article .category::before { content: "❖ "; color: #8b6f47; }

        .article h3 {
            font-family: 'Lora', Georgia, serif;
            font-weight: 700;
            font-size: 1.25rem;
            line-height: 1.28;
            margin-bottom: 10px;
            color: #2b1810;
        }

        .article h3 a {
            color: inherit;
            text-decoration: none;
            transition: color 0.2s;
        }
        .article h3 a:hover { color: #2d5a3d; }

        .article .source {
            font-family: 'PT Sans', Arial, sans-serif;
            font-size: 0.68rem;
            letter-spacing: 1.8px;
            text-transform: uppercase;
            color: #6b4423;
            margin-bottom: 12px;
            font-style: italic;
        }
        .article .source::before { content: "— "; }

        .article .summary {
            font-size: 0.95rem;
            text-align: justify;
            hyphens: auto;
            color: #3a2418;
        }

        .article.lead .summary::first-letter {
            font-family: 'Yeseva One', serif;
            float: left;
            font-size: 3.5rem;
            line-height: 0.85;
            padding: 6px 10px 0 0;
            color: #2d5a3d;
            text-shadow: 1px 1px 0 rgba(139, 111, 71, 0.4);
        }

        .empty {
            text-align: center;
            padding: 70px 20px;
            font-family: 'Caveat', cursive;
            font-size: 1.6rem;
            color: #6b4423;
        }
        .empty::before {
            content: "✦";
            display: block;
            font-size: 2rem;
            margin-bottom: 16px;
            color: #8b6f47;
        }

        .footer {
            margin-top: 46px;
            padding-top: 24px;
            border-top: 2px solid #2b1810;
            text-align: center;
            font-family: 'PT Sans', Arial, sans-serif;
            font-size: 0.72rem;
            letter-spacing: 1.8px;
            text-transform: uppercase;
            color: #6b4423;
            line-height: 2;
            position: relative;
            z-index: 1;
        }

        .footer .ornament {
            color: #2d5a3d;
            font-size: 1.1rem;
            letter-spacing: 10px;
            margin-bottom: 10px;
        }

        .footer .wand {
            color: #8b6f47;
            font-size: 1rem;
        }
    </style>
</head>
<body>
    <div class="newspaper">

        <header class="masthead">
            <div class="top-line">
                <span>Корпоративное издание</span>
                <span>Для внутреннего пользования</span>
                <span>Выпуск №{{ issue_number }}</span>
            </div>

            <h1>Ведомость <span class="accent">для HR</span></h1>
            <div class="tagline">Новости, тренды и инновации в управлении персоналом</div>

            <div class="bottom-line">
                <span>{{ date }}</span>
                <span class="issue">АК БАРС</span>
                <span>Материалов в номере: {{ articles|length }}</span>
            </div>
        </header>

        {% if articles %}
        <div class="news-grid">
            {% for article in articles %}
            <article class="article {% if loop.first %}lead{% endif %}">
                <span class="category">{{ article.category }}</span>
                <h3><a href="{{ article.link }}" target="_blank" rel="noopener">{{ article.title }}</a></h3>
                <div class="source">{{ article.source }}</div>
                <p class="summary">{{ article.summary }}</p>
            </article>
            {% endfor %}
        </div>
        {% else %}
        <div class="empty">
            Сегодня свежих HR-новостей не нашлось.<br>
            Газета обновится завтра.
        </div>
        {% endif %}

        <footer class="footer">
            <div class="ornament">✦ ❦ ✦ ❦ ✦</div>
            <div>Ведомость для HR Ак Барс · Автоматический дайджест</div>
            <div class="wand">Все права на оригинальные публикации принадлежат их авторам</div>
        </footer>

    </div>
</body>
</html>
"""


# ============================================================
# 3. ЛОГИКА
# ============================================================

def clean_summary(text, max_length=450):
    if not text:
        return "Читать полностью на сайте источника."
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    if len(clean) > max_length:
        clean = clean[:max_length].rsplit(' ', 1)[0] + '…'
    return clean


def get_entry_date(entry):
    for field in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = entry.get(field)
        if parsed:
            try:
                return datetime.datetime.fromtimestamp(time.mktime(parsed))
            except (ValueError, OverflowError):
                continue
    return None


def is_fresh(entry, days_back=DAYS_BACK):
    published = get_entry_date(entry)
    if published is None:
        return False
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days_back)
    return published >= cutoff


def is_hr_relevant(title, summary):
    text = (title + " " + summary).lower()
    for kw in HR_KEYWORDS_RU:
        if kw in text:
            return True
    for kw in HR_KEYWORDS_EN:
        if re.search(r'\b' + re.escape(kw), text):
            return True
    return False


def translate_text(text, source_lang='en', target_lang='ru'):
    """Переводит текст. Пытается использовать Google, затем MyMemory."""
    if not text:
        return text

    # --- Попытка 1: Google Translate (с 3 попытками) ---
    for attempt in range(3):
        try:
            translated = GoogleTranslator(source=source_lang, target=target_lang).translate(text)
            if translated and translated.lower() != text.lower():
                print(f"  → Перевод (Google): OK")
                return translated
        except Exception as e:
            print(f"  ⚠ Google попытка {attempt+1} не удалась: {e}")
            time.sleep(1) # Небольшая пауза перед следующей попыткой

    # --- Попытка 2: MyMemory Translator ---
    try:
        translated = MyMemoryTranslator(source=source_lang, target=target_lang).translate(text)
        if translated and translated.lower() != text.lower():
            print(f"  → Перевод (MyMemory): OK")
            return translated
    except Exception as e:
        print(f"  ⚠ MyMemory не удался: {e}")

    # --- Если все попытки не удались, возвращаем оригинал ---
    print(f"  ⚠ Не удалось перевести: {text[:50]}...")
    return text


def fetch_news():
    all_articles = []
    skipped_old = 0
    skipped_irrelevant = 0

    for feed_info in RSS_FEEDS:
        try:
            print(f"Читаю: {feed_info['name']}...")
            feed = feedparser.parse(feed_info['url'])
            print(f"  → получено записей: {len(feed.entries)}")

            for entry in feed.entries[:20]: # Увеличим лимит для более широкого охвата
                title = entry.get('title', 'Без заголовка')
                summary = clean_summary(entry.get('summary', ''))

                if not is_fresh(entry):
                    skipped_old += 1
                    continue

                if not is_hr_relevant(title, summary):
                    skipped_irrelevant += 1
                    continue

                # Перевод для английских источников
                if feed_info.get('lang') == 'en':
                    print(f"  → Перевод: {title[:50]}...")
                    title = translate_text(title)
                    summary = translate_text(summary)

                published = get_entry_date(entry)
                all_articles.append({
                    'title': title,
                    'link': entry.get('link', '#'),
                    'summary': summary,
                    'source': feed_info['name'],
                    'category': feed_info['category'],
                    'published_dt': published or datetime.datetime.min,
                })

        except Exception as e:
            print(f"  ⚠ Ошибка при чтении {feed_info['name']}: {e}")

    print(f"Пропущено старых новостей: {skipped_old}")
    print(f"Пропущено нерелевантных: {skipped_irrelevant}")

    all_articles.sort(key=lambda x: x['published_dt'], reverse=True)
    return all_articles[:MAX_ARTICLES]


def generate_newspaper(articles):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    template = Template(HTML_TEMPLATE)
    today = datetime.date.today()

    months = {
        1:"января",2:"февраля",3:"марта",4:"апреля",5:"мая",6:"июня",
        7:"июля",8:"августа",9:"сентября",10:"октября",11:"ноября",12:"декабря"
    }
    date_str = f"{today.day} {months[today.month]} {today.year}"
    issue_number = today.timetuple().tm_yday

    html = template.render(
        articles=articles,
        date=date_str,
        issue_number=issue_number,
    )

    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Газета сохранена: {output_path}")


def main():
    print("=== Ведомость для HR Ак Барс ===")
    articles = fetch_news()
    print(f"Собрано HR-новостей: {len(articles)}")
    generate_newspaper(articles)
    print("Готово!")


if __name__ == "__main__":
    main()
