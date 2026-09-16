#!/usr/bin/env python3
"""
Ведомость для HR Ак Барс — ежедневная онлайн-газета
Собирает только HR-новости из RSS-источников и генерирует HTML-газету.
"""

import os
import re
import datetime
import feedparser
from jinja2 import Template

# ============================================================
# 1. НАСТРОЙКИ
# ============================================================

# --- Источники новостей ---
# Отбирайте только HR-профильные сайты. Если добавляете общий
# новостной портал — фильтр по ключевым словам (ниже) отсечёт лишнее.
RSS_FEEDS = [
    # --- Российские HR-источники ---
    {"name": "HR-Portal", "url": "https://hr-portal.ru/rss.xml", "category": "Россия"},
    {"name": "HR-Director", "url": "https://www.hr-director.ru/rss", "category": "Россия"},
    {"name": "E-xecutive", "url": "https://www.e-xecutive.ru/rss/all.xml", "category": "Россия"},

    # --- Международные HR-источники ---
    {"name": "HR Exchange Network", "url": "https://www.hrexchangenetwork.com/rss/news-trends", "category": "Мир"},
    {"name": "ETHRWorld — HR Tech", "url": "https://hr.economictimes.indiatimes.com/rss/trends/ai-in-hr", "category": "Мир"},
    {"name": "ETHRWorld — Recruitment", "url": "https://hr.economictimes.indiatimes.com/rss/workplace-4-0/recruitment", "category": "Мир"},
]

MAX_ARTICLES = 12
OUTPUT_DIR = "docs"
OUTPUT_FILE = "index.html"

# --- Фильтр релевантности ---
# Новость остаётся в газете, только если хотя бы одно из этих слов
# встречается в её заголовке или описании (без учёта регистра).
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
# 2. ГАЗЕТНЫЙ HTML-ШАБЛОН
# ============================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ведомость для HR Ак Барс</title>

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400&family=PT+Serif:ital,wght@0,400;0,700;1,400&family=PT+Sans:wght@400;700&display=swap" rel="stylesheet">

    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        html, body {
            background: #e8e2d4;
            color: #1a1a1a;
            font-family: 'PT Serif', Georgia, serif;
            line-height: 1.55;
            -webkit-font-smoothing: antialiased;
        }

        body {
            background-image:
                radial-gradient(circle at 20% 30%, rgba(0,0,0,0.02) 0%, transparent 50%),
                radial-gradient(circle at 80% 70%, rgba(0,0,0,0.02) 0%, transparent 50%);
            padding: 30px 15px;
        }

        .newspaper {
            max-width: 1180px;
            margin: 0 auto;
            background: #f4efe4;
            padding: 50px 55px 40px;
            box-shadow:
                0 1px 3px rgba(0,0,0,0.08),
                0 15px 40px rgba(0,0,0,0.12);
            position: relative;
        }

        .newspaper::before {
            content: "";
            position: absolute;
            top: 18px; left: 18px; right: 18px; bottom: 18px;
            border: 1px solid #1a1a1a;
            pointer-events: none;
        }

        .masthead {
            text-align: center;
            padding-bottom: 22px;
            margin-bottom: 28px;
            border-bottom: 3px double #1a1a1a;
            position: relative;
        }

        .masthead .top-line {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-family: 'PT Sans', Arial, sans-serif;
            font-size: 0.7rem;
            letter-spacing: 3px;
            text-transform: uppercase;
            color: #6b6256;
            padding-bottom: 14px;
            border-bottom: 1px solid #1a1a1a;
            margin-bottom: 22px;
        }

        .masthead h1 {
            font-family: 'Playfair Display', Georgia, serif;
            font-weight: 900;
            font-size: 4.8rem;
            letter-spacing: -2px;
            line-height: 0.95;
            color: #1a1a1a;
            margin: 6px 0 10px;
        }

        .masthead h1 .accent {
            color: #0d4d3c;
            font-style: italic;
        }

        .masthead .tagline {
            font-family: 'PT Serif', Georgia, serif;
            font-style: italic;
            font-size: 1.05rem;
            color: #6b6256;
            margin-bottom: 18px;
        }

        .masthead .bottom-line {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-family: 'PT Sans', Arial, sans-serif;
            font-size: 0.75rem;
            letter-spacing: 2px;
            text-transform: uppercase;
            color: #1a1a1a;
            padding-top: 14px;
            border-top: 1px solid #1a1a1a;
        }

        .masthead .bottom-line .issue {
            background: #0d4d3c;
            color: #f4efe4;
            padding: 4px 12px;
            letter-spacing: 3px;
        }

        .news-grid {
            column-count: 3;
            column-gap: 34px;
            column-rule: 1px solid #c9c0ad;
        }

        @media (max-width: 1000px) {
            .news-grid { column-count: 2; }
            .masthead h1 { font-size: 3.2rem; }
            .newspaper { padding: 35px 30px 30px; }
        }
        @media (max-width: 640px) {
            .news-grid { column-count: 1; }
            .masthead h1 { font-size: 2.2rem; }
            .newspaper { padding: 25px 20px; }
            .newspaper::before { display: none; }
            .masthead .top-line,
            .masthead .bottom-line { flex-direction: column; gap: 6px; }
        }

        .article {
            break-inside: avoid;
            margin-bottom: 26px;
            padding-bottom: 22px;
            border-bottom: 1px solid #d8cfb9;
        }
        .article:last-child { border-bottom: none; }

        .article.lead h3 {
            font-size: 1.55rem;
            line-height: 1.2;
        }

        .article .category {
            display: inline-block;
            font-family: 'PT Sans', Arial, sans-serif;
            font-size: 0.65rem;
            font-weight: 700;
            letter-spacing: 2.5px;
            text-transform: uppercase;
            color: #0d4d3c;
            margin-bottom: 8px;
            padding-bottom: 2px;
            border-bottom: 1px solid #0d4d3c;
        }

        .article h3 {
            font-family: 'Playfair Display', Georgia, serif;
            font-weight: 700;
            font-size: 1.25rem;
            line-height: 1.25;
            margin-bottom: 10px;
            color: #1a1a1a;
        }

        .article h3 a {
            color: inherit;
            text-decoration: none;
            transition: color 0.15s;
        }
        .article h3 a:hover { color: #0d4d3c; }

        .article .source {
            font-family: 'PT Sans', Arial, sans-serif;
            font-size: 0.7rem;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            color: #6b6256;
            margin-bottom: 10px;
        }
        .article .source::before { content: "— "; }

        .article .summary {
            font-size: 0.95rem;
            text-align: justify;
            hyphens: auto;
            color: #2a2a2a;
        }

        .article.lead .summary::first-letter {
            font-family: 'Playfair Display', serif;
            font-weight: 900;
            float: left;
            font-size: 3.2rem;
            line-height: 0.85;
            padding: 4px 8px 0 0;
            color: #0d4d3c;
        }

        .empty {
            text-align: center;
            padding: 60px 20px;
            font-style: italic;
            color: #6b6256;
            font-size: 1.1rem;
        }

        .footer {
            margin-top: 42px;
            padding-top: 22px;
            border-top: 3px double #1a1a1a;
            text-align: center;
            font-family: 'PT Sans', Arial, sans-serif;
            font-size: 0.72rem;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            color: #6b6256;
            line-height: 1.9;
        }

        .footer .ornament {
            color: #0d4d3c;
            font-size: 1.1rem;
            letter-spacing: 8px;
            margin-bottom: 8px;
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
            <div class="ornament">❦ ❦ ❦</div>
            <div>Ведомость для HR Ак Барс · Автоматический дайджест</div>
            <div>Все права на оригинальные публикации принадлежат их авторам</div>
        </footer>

    </div>
</body>
</html>
"""


# ============================================================
# 3. ЛОГИКА
# ============================================================

def clean_summary(text, max_length=420):
    if not text:
        return "Читать полностью на сайте источника."
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    if len(clean) > max_length:
        clean = clean[:max_length].rsplit(' ', 1)[0] + '…'
    return clean


def is_hr_relevant(title, summary):
    """Проверяет, относится ли новость к HR-тематике."""
    text = (title + " " + summary).lower()

    for kw in HR_KEYWORDS_RU:
        if kw in text:
            return True

    # Английские ключи ищем с границей слова, чтобы не ловить случайные совпадения
    for kw in HR_KEYWORDS_EN:
        if re.search(r'\b' + re.escape(kw), text):
            return True

    return False


def fetch_news():
    all_articles = []
    skipped = 0

    for feed_info in RSS_FEEDS:
        try:
            print(f"Читаю: {feed_info['name']}...")
            feed = feedparser.parse(feed_info['url'])

            for entry in feed.entries[:10]:
                title = entry.get('title', 'Без заголовка')
                summary = clean_summary(entry.get('summary', ''))

                # Пропускаем новости, не относящиеся к HR
                if not is_hr_relevant(title, summary):
                    skipped += 1
                    continue

                all_articles.append({
                    'title': title,
                    'link': entry.get('link', '#'),
                    'summary': summary,
                    'source': feed_info['name'],
                    'category': feed_info['category'],
                    'published': entry.get('published', ''),
                })

        except Exception as e:
            print(f"Ошибка при чтении {feed_info['name']}: {e}")

    print(f"Отфильтровано нерелевантных новостей: {skipped}")

    all_articles.sort(key=lambda x: x.get('published', ''), reverse=True)
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
