#!/usr/bin/env python3
"""
Ведомость для HR Ак Барс — ежедневная онлайн-газета
Стиль: «Ежедневный пророк» (Гарри Поттер).
Перевод через DeepL. Рандомные картинки. Избранное в браузере.
"""

import os
import re
import time
import random
import datetime
import requests
import feedparser
from jinja2 import Template

# ============================================================
# 1. НАСТРОЙКИ
# ============================================================

RSS_FEEDS = [
    # --- Российские ---
    {"name": "HBR Россия", "url": "https://hbr-russia.ru/rss/news", "category": "Аналитика", "lang": "ru"},
    {"name": "HR-Portal", "url": "https://hr-portal.ru/rss.xml", "category": "Россия", "lang": "ru"},
    {"name": "HR-Director", "url": "https://www.hr-director.ru/rss", "category": "Россия", "lang": "ru"},
    {"name": "Cossa", "url": "https://www.cossa.ru/rss/", "category": "Технологии", "lang": "ru"},
    {"name": "E-xecutive", "url": "https://www.e-xecutive.ru/rss/all.xml", "category": "Россия", "lang": "ru"},
    {"name": "Forbes Россия", "url": "https://www.forbes.ru/newrss.xml", "category": "Мир", "lang": "ru"},

    # --- Международные (с автопереводом через DeepL) ---
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
DAYS_BACK = 7

# --- Картинки ---
IMAGES_SRC_DIR = "images"        # откуда брать (в корне репозитория)
IMAGES_DEST_DIR = "docs/images"  # куда положить (рядом с index.html)
IMAGES_IN_ISSUE_MIN = 2          # минимум картинок в номере
IMAGES_IN_ISSUE_MAX = 4          # максимум картинок в номере

HR_KEYWORDS_RU = [
    "hr", "эйч-ар", "кадр", "персонал", "сотрудник", "работник",
    "найм", "нанимат", "рекрут", "подбор", "отбор",
    "онбординг", "адаптац", "мотивац", "вовлечён", "вовлечен",
    "обучени", "развити", "карьер", "талант", "компетенц",
    "руководител", "менеджер", "лидерств", "команд",
    "зарплат", "компенсац", "льгот", "бенефит",
    "удержан", "текучест", "увольн", "трудов",
    "корпоративн", "hr-бренд", "кадров",
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
# 2. HTML-ШАБЛОН
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
    <link href="https://fonts.googleapis.com/css2?family=Yeseva+One&family=Lora:ital,wght@0,400;0,600;0,700;1,400&family=Caveat:wght@500&family=PT+Sans:wght@400;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { color: #2b1810; font-family: 'Lora', Georgia, serif; line-height: 1.6; -webkit-font-smoothing: antialiased; }
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
        .newspaper {
            max-width: 1180px; margin: 0 auto;
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
            position: relative; border: 1px solid #8b6f47;
        }
        .newspaper::before {
            content: ""; position: absolute;
            top: 14px; left: 14px; right: 14px; bottom: 14px;
            border: 1px solid #6b4423; pointer-events: none;
        }
        .newspaper::after {
            content: ""; position: absolute;
            top: 22px; left: 22px; right: 22px; bottom: 22px;
            border: 1px solid rgba(107, 68, 35, 0.4); pointer-events: none;
        }
        .masthead { text-align: center; padding-bottom: 26px; margin-bottom: 32px; position: relative; border-bottom: 2px solid #2b1810; z-index: 1; }
        .masthead .top-line {
            display: flex; justify-content: space-between; align-items: center;
            font-family: 'PT Sans', Arial, sans-serif; font-size: 0.7rem;
            letter-spacing: 3px; text-transform: uppercase; color: #6b4423;
            padding-bottom: 16px; margin-bottom: 24px; border-bottom: 1px solid #6b4423;
        }
        .masthead .top-line span:first-child::before { content: "✦ "; }
        .masthead .top-line span:last-child::after { content: " ✦"; }
        .masthead h1 {
            font-family: 'Yeseva One', Georgia, serif; font-weight: 400;
            font-size: 4.6rem; letter-spacing: -1px; line-height: 1;
            color: #2b1810; margin: 6px 0 14px;
            text-shadow: 1px 1px 0 rgba(139, 111, 71, 0.4), 2px 2px 4px rgba(43, 24, 16, 0.15);
        }
        .masthead h1 .accent { color: #2d5a3d; font-style: italic; display: inline-block; transform: rotate(-2deg); margin: 0 6px; }
        .masthead .tagline { font-family: 'Caveat', cursive; font-size: 1.5rem; color: #6b4423; margin-bottom: 22px; letter-spacing: 0.5px; }
        .masthead .tagline::before, .masthead .tagline::after { content: "  ~  "; color: #8b6f47; font-size: 1.1rem; }
        .masthead .bottom-line {
            display: flex; justify-content: space-between; align-items: center;
            font-family: 'PT Sans', Arial, sans-serif; font-size: 0.75rem;
            letter-spacing: 2.5px; text-transform: uppercase; color: #2b1810;
            padding-top: 16px; border-top: 1px solid #6b4423;
        }
        .masthead .bottom-line .issue {
            background: #2d5a3d; color: #efe2c3; padding: 5px 14px;
            letter-spacing: 3px; font-weight: 700;
            box-shadow: 1px 1px 0 rgba(43, 24, 16, 0.4);
        }
        .news-grid { column-count: 3; column-gap: 36px; column-rule: 1px solid #a88b5d; position: relative; z-index: 1; }
        @media (max-width: 1000px) { .news-grid { column-count: 2; } .masthead h1 { font-size: 3.2rem; } .newspaper { padding: 40px 32px 30px; } }
        @media (max-width: 640px) {
            .news-grid { column-count: 1; } .masthead h1 { font-size: 2.2rem; }
            .newspaper { padding: 28px 22px; }
            .newspaper::before, .newspaper::after { display: none; }
            .masthead .top-line, .masthead .bottom-line { flex-direction: column; gap: 6px; }
        }
        .article { break-inside: avoid; margin-bottom: 28px; padding-bottom: 24px; border-bottom: 1px dashed #8b6f47; animation: fadeIn 0.7s ease-out backwards; position: relative; }
        .article:last-child { border-bottom: none; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
        .article.lead h3 { font-size: 1.6rem; line-height: 1.22; }
        .article .category {
            display: inline-block; font-family: 'PT Sans', Arial, sans-serif;
            font-size: 0.62rem; font-weight: 700; letter-spacing: 2.5px;
            text-transform: uppercase; color: #2d5a3d;
            margin-bottom: 10px; padding: 2px 0; border-bottom: 1px solid #2d5a3d;
        }
        .article .category::before { content: "❖ "; color: #8b6f47; }
        .article h3 { font-family: 'Lora', Georgia, serif; font-weight: 700; font-size: 1.25rem; line-height: 1.28; margin-bottom: 10px; color: #2b1810; padding-right: 30px; }
        .article h3 a { color: inherit; text-decoration: none; transition: color 0.2s; }
        .article h3 a:hover { color: #2d5a3d; }
        .article .source {
            font-family: 'PT Sans', Arial, sans-serif; font-size: 0.68rem;
            letter-spacing: 1.8px; text-transform: uppercase; color: #6b4423;
            margin-bottom: 12px; font-style: italic;
        }
        .article .source::before { content: "— "; }
        .article .summary { font-size: 0.95rem; text-align: justify; hyphens: auto; color: #3a2418; }
        .article.lead .summary::first-letter {
            font-family: 'Yeseva One', serif; float: left; font-size: 3.5rem;
            line-height: 0.85; padding: 6px 10px 0 0; color: #2d5a3d;
            text-shadow: 1px 1px 0 rgba(139, 111, 71, 0.4);
        }
        /* Кнопка "В избранное" */
        .fav-btn {
            position: absolute; top: 0; right: 0;
            background: transparent; border: none; cursor: pointer;
            font-size: 1.4rem; color: #8b6f47;
            padding: 2px 6px; transition: transform 0.15s, color 0.15s;
            line-height: 1; z-index: 2;
        }
        .fav-btn:hover { transform: scale(1.25); color: #2d5a3d; }
        .fav-btn.active { color: #c9a227; }
        /* Картинка между статьями */
        .inline-image {
            break-inside: avoid;
            margin: 0 0 28px 0;
            padding: 8px;
            background: #e0d1ad;
            border: 1px solid #8b6f47;
            box-shadow: 3px 3px 0 rgba(43, 24, 16, 0.15);
            position: relative;
        }
        .inline-image img {
            display: block; width: 100%; height: auto;
            filter: sepia(0.35) contrast(0.95) brightness(0.98);
            border: 1px solid #6b4423;
        }
        .inline-image::after {
            content: "✦ ✦ ✦"; display: block;
            text-align: center; margin-top: 6px;
            color: #8b6f47; font-size: 0.7rem; letter-spacing: 4px;
        }
        /* Блок "Избранное" */
        .favorites-section {
            margin-top: 50px; padding-top: 30px;
            border-top: 3px double #2b1810;
            position: relative; z-index: 1;
        }
        .favorites-section h2 {
            font-family: 'Yeseva One', serif; font-weight: 400;
            font-size: 2rem; color: #2d5a3d;
            text-align: center; margin-bottom: 24px;
            letter-spacing: 1px;
        }
        .favorites-section h2::before, .favorites-section h2::after {
            content: " ✦ "; color: #8b6f47; font-size: 1rem;
        }
        .favorites-empty {
            text-align: center; font-family: 'Caveat', cursive;
            font-size: 1.3rem; color: #6b4423; padding: 20px;
        }
        .favorites-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 18px;
        }
        .fav-item {
            background: #e8d9b5;
            border: 1px solid #8b6f47;
            padding: 16px 18px;
            position: relative;
            box-shadow: 2px 2px 0 rgba(43, 24, 16, 0.12);
        }
        .fav-item h4 {
            font-family: 'Lora', serif; font-weight: 700;
            font-size: 1rem; line-height: 1.3;
            margin-bottom: 8px; padding-right: 24px;
        }
        .fav-item h4 a { color: #2b1810; text-decoration: none; }
        .fav-item h4 a:hover { color: #2d5a3d; }
        .fav-item .fav-source {
            font-family: 'PT Sans', sans-serif; font-size: 0.65rem;
            letter-spacing: 1.5px; text-transform: uppercase;
            color: #6b4423; font-style: italic;
        }
        .fav-item .fav-remove {
            position: absolute; top: 8px; right: 10px;
            background: transparent; border: none; cursor: pointer;
            color: #8b6f47; font-size: 1.1rem;
            padding: 2px 6px; line-height: 1;
            transition: color 0.15s, transform 0.15s;
        }
        .fav-item .fav-remove:hover { color: #a02929; transform: scale(1.2); }
        .empty { text-align: center; padding: 70px 20px; font-family: 'Caveat', cursive; font-size: 1.6rem; color: #6b4423; }
        .empty::before { content: "✦"; display: block; font-size: 2rem; margin-bottom: 16px; color: #8b6f47; }
        .footer {
            margin-top: 46px; padding-top: 24px;
            border-top: 2px solid #2b1810; text-align: center;
            font-family: 'PT Sans', Arial, sans-serif; font-size: 0.72rem;
            letter-spacing: 1.8px; text-transform: uppercase; color: #6b4423;
            line-height: 2; position: relative; z-index: 1;
        }
        .footer .ornament { color: #2d5a3d; font-size: 1.1rem; letter-spacing: 10px; margin-bottom: 10px; }
        .footer .wand { color: #8b6f47; font-size: 1rem; }
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
                <span>Материалов в номере: {{ article_count }}</span>
            </div>
        </header>

        {% if items %}
        <div class="news-grid">
            {% for item in items %}
                {% if item.type == 'article' %}
                <article class="article {% if item.is_lead %}lead{% endif %}"
                         data-id="{{ item.article.link }}"
                         data-title="{{ item.article.title }}"
                         data-source="{{ item.article.source }}"
                         data-link="{{ item.article.link }}">
                    <button class="fav-btn" type="button" title="Добавить в избранное" aria-label="Добавить в избранное">☆</button>
                    <span class="category">{{ item.article.category }}</span>
                    <h3><a href="{{ item.article.link }}" target="_blank" rel="noopener">{{ item.article.title }}</a></h3>
                    <div class="source">{{ item.article.source }}</div>
                    <p class="summary">{{ item.article.summary }}</p>
                </article>
                {% elif item.type == 'image' %}
                <figure class="inline-image">
                    <img src="{{ item.src }}" alt="Иллюстрация" loading="lazy">
                </figure>
                {% endif %}
            {% endfor %}
        </div>
        {% else %}
        <div class="empty">Сегодня свежих HR-новостей не нашлось.<br>Газета обновится завтра.</div>
        {% endif %}

        <section class="favorites-section" id="favorites-section">
            <h2>Моё избранное</h2>
            <div class="favorites-empty" id="favorites-empty">
                Пока ничего не отложено. Нажмите ☆ у статьи, чтобы сохранить её здесь.
            </div>
            <div class="favorites-list" id="favorites-list"></div>
        </section>

        <footer class="footer">
            <div class="ornament">✦ ❦ ✦ ❦ ✦</div>
            <div>Ведомость для HR Ак Барс · Автоматический дайджест</div>
            <div class="wand">Все права на оригинальные публикации принадлежат их авторам</div>
        </footer>
    </div>

<script>
(function() {
    var STORAGE_KEY = 'hr-favorites-v1';

    function getFavs() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
        } catch (e) { return []; }
    }
    function saveFavs(favs) {
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(favs)); } catch (e) {}
    }
    function escapeHtml(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function renderFavorites() {
        var favs = getFavs();
        var list = document.getElementById('favorites-list');
        var empty = document.getElementById('favorites-empty');
        if (!list || !empty) return;

        if (favs.length === 0) {
            empty.style.display = 'block';
            list.innerHTML = '';
            return;
        }
        empty.style.display = 'none';
        list.innerHTML = favs.map(function(f) {
            return '<div class="fav-item">' +
                '<button class="fav-remove" type="button" data-id="' + encodeURIComponent(f.id) + '" title="Убрать из избранного">✕</button>' +
                '<h4><a href="' + f.link + '" target="_blank" rel="noopener">' + escapeHtml(f.title) + '</a></h4>' +
                '<div class="fav-source">— ' + escapeHtml(f.source) + '</div>' +
                '</div>';
        }).join('');
    }

    function updateButtons() {
        var favs = getFavs();
        var ids = favs.map(function(f) { return f.id; });
        document.querySelectorAll('.fav-btn').forEach(function(btn) {
            var article = btn.closest('.article');
            if (!article) return;
            var id = article.getAttribute('data-id');
            if (ids.indexOf(id) !== -1) {
                btn.classList.add('active');
                btn.textContent = '★';
                btn.title = 'Убрать из избранного';
            } else {
                btn.classList.remove('active');
                btn.textContent = '☆';
                btn.title = 'Добавить в избранное';
            }
        });
    }

    function toggleFavorite(article) {
        var id = article.getAttribute('data-id');
        var title = article.getAttribute('data-title');
        var source = article.getAttribute('data-source');
        var link = article.getAttribute('data-link');
        var favs = getFavs();
        var idx = -1;
        for (var i = 0; i < favs.length; i++) {
            if (favs[i].id === id) { idx = i; break; }
        }
        if (idx >= 0) {
            favs.splice(idx, 1);
        } else {
            favs.unshift({ id: id, title: title, source: source, link: link });
        }
        saveFavs(favs);
        renderFavorites();
        updateButtons();
    }

    document.addEventListener('click', function(e) {
        var btn = e.target.closest('.fav-btn');
        if (btn) {
            var article = btn.closest('.article');
            if (article) { toggleFavorite(article); }
            return;
        }
        var remove = e.target.closest('.fav-remove');
        if (remove) {
            var id = decodeURIComponent(remove.getAttribute('data-id'));
            var favs = getFavs().filter(function(f) { return f.id !== id; });
            saveFavs(favs);
            renderFavorites();
            updateButtons();
        }
    });

    renderFavorites();
    updateButtons();
})();
</script>
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


def translate_text(text, source_lang='EN', target_lang='RU'):
    """Перевод через DeepL API. Ключ передаётся в заголовке Authorization."""
    if not text:
        return text
    api_key = os.getenv("DEEPL_API_KEY")
    if not api_key:
        print("  ⚠ DEEPL_API_KEY не задан — пропускаю перевод")
        return text
    try:
        url = "https://api-free.deepl.com/v2/translate"
        response = requests.post(
            url,
            headers={
                "Authorization": f"DeepL-Auth-Key {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "text": [text],
                "source_lang": source_lang,
                "target_lang": target_lang,
            },
            timeout=20,
        )
        if response.status_code == 200:
            result = response.json()
            translated = result["translations"][0]["text"]
            print(f"  ✓ Перевод OK ({len(text)} симв.)")
            return translated
        else:
            print(f"  ⚠ DeepL ответил: {response.status_code} — {response.text[:200]}")
            return text
    except Exception as e:
        print(f"  ⚠ Ошибка DeepL: {e}")
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
            for entry in feed.entries[:20]:
                title = entry.get('title', 'Без заголовка')
                summary = clean_summary(entry.get('summary', ''))
                if not is_fresh(entry):
                    skipped_old += 1
                    continue
                if not is_hr_relevant(title, summary):
                    skipped_irrelevant += 1
                    continue
                if feed_info.get('lang') == 'en':
                    print(f"  → Перевожу: {title[:60]}...")
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
    print(f"Пропущено старых: {skipped_old}")
    print(f"Пропущено нерелевантных: {skipped_irrelevant}")
    all_articles.sort(key=lambda x: x['published_dt'], reverse=True)
    return all_articles[:MAX_ARTICLES]


def get_random_images():
    """Возвращает список файлов-картинок из IMAGES_SRC_DIR (папка в корне)."""
    if not os.path.isdir(IMAGES_SRC_DIR):
        print(f"  ℹ Папка с картинками не найдена: {IMAGES_SRC_DIR}")
        return []
    exts = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
    images = [f for f in os.listdir(IMAGES_SRC_DIR)
              if f.lower().endswith(exts)]
    return images


def build_issue_items(articles, images):
    """Собирает список: статьи + случайные картинки между ними."""
    if not articles:
        return []

    if not images or len(articles) < 3:
        chosen_images = []
    else:
        max_possible = min(len(images), IMAGES_IN_ISSUE_MAX, len(articles) - 1)
        min_possible = min(IMAGES_IN_ISSUE_MIN, max_possible)
        if max_possible >= min_possible and max_possible > 0:
            num = random.randint(min_possible, max_possible)
            chosen_images = random.sample(images, num)
        else:
            chosen_images = []

    if chosen_images:
        positions = sorted(random.sample(range(1, len(articles)), len(chosen_images)))
    else:
        positions = []

    items = []
    img_iter = iter(chosen_images)
    for i, article in enumerate(articles):
        items.append({
            'type': 'article',
            'article': article,
            'is_lead': (i == 0),
        })
        if i in positions:
            try:
                img = next(img_iter)
                items.append({'type': 'image', 'src': f'images/{img}'})
            except StopIteration:
                pass
    return items


def generate_newspaper(articles, images):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    items = build_issue_items(articles, images)
    image_count = sum(1 for i in items if i['type'] == 'image')
    print(f"Вставлено картинок в номер: {image_count}")

    template = Template(HTML_TEMPLATE)
    today = datetime.date.today()
    months = {1:"января",2:"февраля",3:"марта",4:"апреля",5:"мая",6:"июня",7:"июля",8:"августа",9:"сентября",10:"октября",11:"ноября",12:"декабря"}
    date_str = f"{today.day} {months[today.month]} {today.year}"
    issue_number = today.timetuple().tm_yday

    html = template.render(
        items=items,
        article_count=len(articles),
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
    images = get_random_images()
    print(f"Найдено картинок в пуле: {len(images)}")
    generate_newspaper(articles, images)
    print("Готово!")


if __name__ == "__main__":
    main()
