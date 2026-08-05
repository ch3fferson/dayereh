import json
import re
from pathlib import Path
from urllib.parse import urlparse
from utils.string_utils import StringUtils
from utils.time_utils import TimeUtils
from utils.id_generator import IDGenerator
from converters.media_type import MediaType
from converters.markdown_to_html import MarkdownToHTML
from converters.media_compressor import MediaCompressor


class HTMLBuilder:

    MEDIA_PLACEHOLDER_SVG = (
        '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="5" width="18" height="14" rx="2"></rect>'
        '<circle cx="8.5" cy="10" r="1.5"></circle>'
        '<path d="M21 15l-5-5L5 21"></path>'
        '</svg>'
    )

    RELATED_PLACEHOLDER_SVG = (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>'
        '<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>'
        '</svg>'
    )

    def __init__(self, storage=None):
        self.storage = storage
        self.compressor = MediaCompressor(image_quality=70, video_crf=30)
        self._thumb_cache = {}

    def video_thumb_url(self, video_url):
        parsed = urlparse(str(video_url))
        name = Path(parsed.path).name
        stem = Path(name).stem
        thumb_name = f"{stem}_thumb.jpg"
        base = str(video_url).rsplit("/", 1)[0]
        return f"{base}/{thumb_name}"

    def ensure_video_thumbnail(self, video_url):
        if not video_url:
            return ""

        if video_url in self._thumb_cache:
            return self._thumb_cache[video_url]

        thumb_url = self.video_thumb_url(video_url)

        if not self.storage:
            self._thumb_cache[video_url] = thumb_url
            return thumb_url

        filename = Path(urlparse(str(video_url)).path).name
        video_path = self.storage.media / filename
        thumb_path = self.storage.media / f"{Path(filename).stem}_thumb.jpg"

        if thumb_path.exists():
            self._thumb_cache[video_url] = thumb_url
            return thumb_url

        if not video_path.exists():
            self._thumb_cache[video_url] = ""
            return ""

        try:
            self.compressor.extract_video_thumbnail(
                str(video_path),
                str(thumb_path),
            )
            self._thumb_cache[video_url] = thumb_url
            return thumb_url
        except Exception as e:
            print(f"error generating video thumbnail: {e}")
            self._thumb_cache[video_url] = ""
            return ""

    def resolve_card_thumbnail(self, media_url):
        if not media_url:
            return ""

        media_type = MediaType.detect_media_type_url(media_url)

        if media_type == "video":
            return self.ensure_video_thumbnail(media_url)

        return media_url

    def build_media_list(self, raw_media):
        media_list = []

        for url in raw_media or []:
            if not url:
                continue

            media_type = MediaType.detect_media_type_url(url)
            entry = {"url": url, "type": media_type}

            if media_type == "video":
                poster = self.ensure_video_thumbnail(url)
                if poster:
                    entry["poster"] = poster

            media_list.append(entry)

        return media_list

    def build_summary_content(self, summery):
        return MarkdownToHTML.convert(summery)

    def build_summary_trigger(self, summary_html):
        if not summary_html:
            return ""

        return """
<button
    class="ai-summary-trigger"
    type="button"
    onclick="openSummaryModal()"
    aria-haspopup="dialog"
    aria-controls="aiSummaryModal"
>
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v3M12 18v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M3 12h3M18 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"></path><circle cx="12" cy="12" r="3.2"></circle></svg>
    <span>خلاصه هوشمند</span>
</button>
"""

    def build_summary_modal(self, summary_html, update_time=""):
        if not summary_html:
            return ""

        safe_time = StringUtils.safe(update_time) if update_time else ""
        time_html = (
            f'<span class="ai-summary-time" data-live-time="{safe_time}"></span>'
            if safe_time else ""
        )

        return f"""
<div
    class="modal-overlay ai-summary-overlay"
    id="aiSummaryModal"
    role="dialog"
    aria-modal="true"
    aria-labelledby="aiSummaryModalTitle"
>

    <div class="news-modal ai-summary-modal">

        <button
            class="modal-close"
            onclick="closeSummaryModal()"
            aria-label="بستن"
        >
            ✕
        </button>

        <div class="modal-header ai-summary-modal-header">

            <div class="ai-summary-badge">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v3M12 18v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M3 12h3M18 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"></path><circle cx="12" cy="12" r="3.2"></circle></svg>
                <span id="aiSummaryModalTitle">خلاصه هوشمند</span>
            </div>

            <div class="ai-summary-meta">
                <span class="ai-summary-tag">تولید شده توسط Gemini</span>
                {time_html}
            </div>

        </div>

        <div class="ai-summary-content">
            {summary_html}
        </div>

    </div>

</div>
"""

    def tokenize(self, text):
        return set(
            token for token in re.findall(r"\w+", str(text).lower())
            if len(token) > 1
        )

    def compute_related(self, flat_items, limit=4):
        related_map = {}

        for i, current in enumerate(flat_items):
            scored = []

            for j, other in enumerate(flat_items):
                if i == j:
                    continue

                intersection = current["tokens"] & other["tokens"]

                if not intersection:
                    continue

                union = current["tokens"] | other["tokens"]
                score = len(intersection) / len(union)
                scored.append((score, other))

            scored.sort(key=lambda pair: pair[0], reverse=True)

            related_map[current["anchor"]] = [
                {
                    "anchor": entry["anchor"],
                    "title": entry["title"],
                    "date": entry["date"],
                    "source": entry["source"],
                    "thumbnail": entry["thumbnail"],
                }
                for _, entry in scored[:limit]
            ]

        return related_map

    def build_card(self, item, source, anchor, related, eager):

        title = getattr(item, "title", "")
        lang = StringUtils.detect_lang(title)
        content = getattr(item, "content", "")
        date = getattr(item, "date", "")
        link = getattr(item, "link", "")

        excerpt_source = str(content).replace("\n", " ").strip()
        excerpt = StringUtils.truncate_text_char(excerpt_source, 96)

        safe_title = StringUtils.safe(title)
        safe_content = StringUtils.safe(content).replace("\n", "<br>")
        safe_excerpt = StringUtils.safe(excerpt)
        safe_date = StringUtils.safe(date)
        safe_link = StringUtils.safe(link)
        safe_lang = StringUtils.safe(lang)

        rtl_style = "" if safe_lang == "fa" else "direction: ltr; text-align: left;"

        raw_media = getattr(item, "media", []) or []
        media_list = self.build_media_list(raw_media)

        media_json = StringUtils.safe(json.dumps(media_list, ensure_ascii=False))
        related_json = StringUtils.safe(json.dumps(related, ensure_ascii=False))

        loading_attr = "eager" if eager else "lazy"

        if media_list:
            first = media_list[0]

            if first["type"] == "video":
                thumb_src = first.get("poster") or ""
                if thumb_src:
                    media_thumb = f'<img class="card-media-thumb" src="{StringUtils.safe(thumb_src)}" alt="" loading="{loading_attr}">'
                else:
                    media_thumb = f'<div class="card-media-placeholder">{self.MEDIA_PLACEHOLDER_SVG}</div>'
            else:
                media_thumb = f'<img class="card-media-thumb" src="{StringUtils.safe(first["url"])}" alt="" loading="{loading_attr}">'

            badge = f'<span class="card-media-badge">+{len(media_list) - 1}</span>' if len(media_list) > 1 else ""

            if first["type"] == "gif":
                kind_badge = '<span class="card-media-kind">گیف</span>'
            elif first["type"] == "video":
                kind_badge = '<span class="card-media-kind">ویدیو</span>'
            else:
                kind_badge = ""

            media_block = f"""
<div class="card-media">
    {media_thumb}
    <div class="card-media-fade"></div>
    {kind_badge}
    {badge}
</div>
"""
        else:
            media_block = f"""
<div class="card-media card-media--empty">
    <div class="card-media-placeholder">{self.MEDIA_PLACEHOLDER_SVG}</div>
</div>
"""

        card_class = f"news-card has-media in-view" if eager else "news-card has-media"

        return f"""
<article
    class="{card_class}"
    role="button"
    tabindex="0"
    data-search="{safe_title} {safe_excerpt} {source}"
    data-anchor="{anchor}"
    aria-label="{safe_title}"
    onkeydown="if(event.key==='Enter'||event.key===' '){{event.preventDefault(); this.click();}}"
    onclick='this.classList.add("is-read"); markRead(`{anchor}`); openNewsModal(
        `{safe_lang}`,
        `{safe_title}`,
        `{safe_content}`,
        `{safe_date}`,
        `{safe_link}`,
        `{source}`,
        JSON.parse(`{media_json}`),
        JSON.parse(`{related_json}`)
    )'
>
    <a style="display: block; position: relative; top: -250px; visibility: hidden;" id="{anchor}"></a>

    <div class="card-background-glow"></div>

    {media_block}

    <div class="card-top">

        <div class="card-source">
            {source}
        </div>

        <div class="card-top-right">

            <div class="card-date" id="date-{anchor}" data-live-time="{safe_date}">
                {safe_date}
            </div>

            <span class="unread-dot" id="dot-{anchor}" title="خوانده نشده"></span>

        </div>

    </div>

    <div class="card-content">

        <div class="card-text">

            <p class="card-excerpt" style="{rtl_style}">
                {safe_excerpt}
            </p>

        </div>

    </div>

    <div class="card-bottom">

        <div class="read-more">
            بیشتر بخوانید
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"></path></svg>
        </div>

    </div>

</article>
"""

    def build_section(self, feed, anchors, related_map):

        source = StringUtils.safe(feed.get("source", "خبرگزاری"))
        section_id = "section-" + str(IDGenerator.generate(source))

        items = feed.get("items", [])

        cards = []

        for index, (item, anchor) in enumerate(zip(items, anchors)):
            related = related_map.get(anchor, [])
            cards.append(self.build_card(item, source, anchor, related, index < 2))

        body = ''.join(cards) if cards else """
<div class="feed-empty">
    فعلاً خبری در این بخش موجود نیست
</div>
"""

        return f"""
<section class="feed-section" id="{section_id}" data-source-section>

    <div class="feed-header">

        <div class="feed-title-container">

            <div class="feed-indicator"></div>

            <div class="feed-title">
                {source}
            </div>

        </div>

        <div class="carousel-nav-group">

            <button
                class="carousel-nav"
                aria-label="نمایش کارت راست"
                onclick="scrollCarousel('{section_id}', 1)"
            >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
            </button>

            <button
                class="carousel-nav"
                aria-label="نمایش کارت چپ"
                onclick="scrollCarousel('{section_id}', -1)"
            >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
            </button>

        </div>

    </div>

    <div class="feed-carousel">
        {body}
    </div>

</section>
"""

    def build_price_cards(self, prices):
        if not prices:
            return ""

        cards = []

        for entry in prices:
            currency = StringUtils.safe(entry.get("currency", ""))
            price = StringUtils.safe(entry.get("price", ""))
            time = StringUtils.safe(entry.get("time", ""))

            cards.append(f"""
<div class="price-card in-view" data-search="{currency}" data-time="{time}">
    <div class="price-card-glow"></div>
    <div class="price-currency">{currency}</div>
    <div class="price-value">{price}</div>
    <div class="price-time" data-live-time="{time}">{time}</div>
</div>
""")

        return f"""
<section class="feed-section price-section" id="section-prices" data-source-section>

    <div class="feed-header">

        <div class="feed-title-container">

            <div class="feed-indicator"></div>

            <div class="feed-title">
                نرخ ارز و طلا
            </div>

        </div>

        <div class="carousel-nav-group">

            <button
                class="carousel-nav"
                aria-label="نمایش نرخ راست"
                onclick="scrollCarousel('section-prices', 1)"
            >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
            </button>

            <button
                class="carousel-nav"
                aria-label="نمایش نرخ چپ"
                onclick="scrollCarousel('section-prices', -1)"
            >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
            </button>

        </div>

    </div>

    <div class="feed-carousel price-carousel">
        {''.join(cards)}
    </div>

</section>
"""

    def build(self, feeds, prices, summery=None):
        
        latest_update = TimeUtils.to_string(
            TimeUtils.now()
        )

        flat_items = []
        feed_anchor_lists = []

        for feed in feeds:
            source_raw = feed.get("source", "-")
            anchors = []

            for item in feed.get("items", []):
                title = getattr(item, "title", "")
                content = getattr(item, "content", "")
                date = getattr(item, "date", "")

                anchor = IDGenerator.generate(
                    str(date) + str(title) + str(content)
                )

                anchors.append(anchor)

                raw_media = getattr(item, "media", []) or []
                thumbnail = self.resolve_card_thumbnail(
                    raw_media[0] if raw_media else ""
                )

                flat_items.append({
                    "anchor": anchor,
                    "tokens": self.tokenize(f"{title} {content}"),
                    "title": StringUtils.safe(title),
                    "date": StringUtils.safe(date),
                    "source": StringUtils.safe(source_raw),
                    "thumbnail": thumbnail,
                })

            feed_anchor_lists.append(anchors)

        related_map = self.compute_related(flat_items)

        sections = []
        chips = []

        if prices:
            chips.append("""
<button
    class="chip chip-price"
    data-chip-target="section-prices"
    onclick="jumpToSection('section-prices')"
>
    نرخ ارز و طلا
</button>
""")

        for feed, anchors in zip(feeds, feed_anchor_lists):
            source = StringUtils.safe(feed.get("source", "خبرگزاری"))
            section_id = "section-" + str(IDGenerator.generate(source))

            sections.append(
                self.build_section(feed, anchors, related_map)
            )

            chips.append(f"""
<button
    class="chip"
    data-chip-target="{section_id}"
    onclick="jumpToSection('{section_id}')"
>
    {source}
</button>
""")

        has_any_feed = len(feeds) > 0

        summary_html = self.build_summary_content(summery[0] if len(summery) > 0 else "")
        summary_trigger = self.build_summary_trigger(summary_html if summary_html != "" else None)
        summary_modal = self.build_summary_modal(
            summary_html,
            summery[1] if len(summery) > 1 else "",
        )
        price_cards = self.build_price_cards(prices)

        main_content = ''.join(sections) if has_any_feed else """
<div class="empty-state">

    <div class="empty-state-icon">◌</div>

    <div class="empty-state-title">
        هنوز خبری برای نمایش وجود ندارد
    </div>

    <div class="empty-state-subtitle">
        به‌محض انتشار اخبار جدید، اینجا نمایش داده می‌شوند
    </div>

</div>
"""

        return f"""
<!DOCTYPE html>

<html lang="fa" dir="auto">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
/>

<meta
    name="theme-color"
    content="#000000"
/>

<meta
    name="description"
    content="دایره؛ دسترسی سریع و زیبا به تازه‌ترین اخبار از منابع مختلف"
/>

<title>پلتفرم دایره</title>

<link
    rel="icon"
    type="image/webp"
    href="https://raw.githubusercontent.com/ch3fferson/dayereh/main/feeds/view/assets/favicon.webp"
/>

<script>
document.documentElement.classList.add("js");
</script>

<style>

@font-face {{
    font-family: Peyda;

    src:
        url('https://raw.githubusercontent.com/ch3fferson/dayereh/main/feeds/view/assets/fonts/Peyda-Regular.ttf')
        format('truetype');

    font-weight: 400;
}}

@font-face {{
    font-family: Peyda;

    src:
        url('https://raw.githubusercontent.com/ch3fferson/dayereh/main/feeds/view/assets/fonts/Peyda-Bold.ttf')
        format('truetype');

    font-weight: 700;
}}

@font-face {{
    font-family: Peyda;

    src:
        url('https://raw.githubusercontent.com/ch3fferson/dayereh/main/feeds/view/assets/fonts/Peyda-Black.ttf')
        format('truetype');

    font-weight: 900;
}}

:root {{

    --bg-primary: #000000;

    --surface:
        linear-gradient(
            180deg,
            rgba(22,22,26,0.85),
            rgba(6,6,8,0.9)
        );

    --modal-bg:
        linear-gradient(
            180deg,
            rgba(20,20,24,0.6),
            rgba(4,4,6,0.72)
        );

    --grid-line: rgba(255,255,255,0.025);

    --border: rgba(255,255,255,0.1);

    --border-hover: rgba(96,165,250,0.45);

    --text-primary: #ffffff;

    --text-secondary: #c3cbd6;

    --accent: #60a5fa;

    --danger: #f87171;

    --surface-shadow: 0 20px 50px rgba(0,0,0,0.55);

    --blur: blur(22px) saturate(150%);

    --radius-card: 28px;
}}

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

html {{
    scroll-behavior: smooth;
}}

body {{
    background-color: var(--bg-primary);
    color: var(--text-primary);
    font-family: Peyda, sans-serif;
    font-size: 16px;
    min-height: 100vh;
    overflow-x: hidden;
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
}}

body::before {{
    content: "";
    position: fixed;
    inset: 0;
    z-index: -1;
    pointer-events: none;

    background-image:
        radial-gradient(
            circle at 50% 35%,
            transparent 0%,
            var(--bg-primary) 72%
        ),
        radial-gradient(
            circle at 50% 15%,
            rgba(96,165,250,0.07),
            transparent 55%
        ),
        linear-gradient(var(--grid-line) 1px, transparent 1px),
        linear-gradient(90deg, var(--grid-line) 1px, transparent 1px);

    background-size:
        100% 100%,
        100% 100%,
        64px 64px,
        64px 64px;
}}

body.modal-open {{
    overflow: hidden;
}}

a {{
    color: inherit;
    text-decoration: none;
}}

::-webkit-scrollbar {{
    width: 0;
    height: 0;
}}

:focus-visible {{
    outline: 2px solid var(--accent);
    outline-offset: 3px;
    border-radius: 6px;
}}

.app-header,
.app-footer {{

    position: sticky;

    top: 0;

    z-index: 999;

    backdrop-filter: var(--blur);

    -webkit-backdrop-filter: var(--blur);

    background: rgba(0,0,0,0.78);

    padding: 1rem 1.2rem;
}}

.app-header {{
    border-bottom: 1px solid rgba(255,255,255,0.07);
}}

.app-footer {{
    position: static;
    border-top: 1px solid rgba(255,255,255,0.07);
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    margin-top: 1rem;
}}

.footer-text {{
    color: var(--text-secondary);
    font-size: 0.92rem;
    line-height: 1.9;
    letter-spacing: 0.01em;
}}

.header-inner {{
    display: flex;
    flex-direction: column;
    gap: 0.9rem;
}}

.header-top {{
    display: flex;
    align-items: center;
    gap: 1rem;
}}

.header-top .search-wrap {{
    flex: 1;
    min-width: 0;
}}

.header-actions {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex: 0 0 auto;
}}

.live-badge {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.55rem 0.9rem;
    border-radius: 999px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    color: var(--text-secondary);
    font-size: 0.78rem;
    letter-spacing: 0.01em;
}}

.live-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #22c55e;
    box-shadow: 0 0 12px #22c55e;
    animation: pulseDot 2s ease-in-out infinite;
}}

@keyframes pulseDot {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.45; }}
}}

.main-layout {{
    padding: 1.3rem;
    display: flex;
    flex-direction: column;
    gap: 2rem;
}}

.ai-summary-trigger {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.55rem 0.95rem;
    border-radius: 999px;
    background: var(--surface);
    border: 1px solid var(--border);
    box-shadow: var(--surface-shadow);
    backdrop-filter: var(--blur);
    -webkit-backdrop-filter: var(--blur);
    color: var(--text-primary);
    font-family: Peyda, sans-serif;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.01em;
    cursor: pointer;
    white-space: nowrap;
    transition: border 0.2s ease, background 0.2s ease, transform 0.15s ease;
}}

.ai-summary-trigger svg {{
    color: var(--accent);
    flex: 0 0 auto;
}}

.ai-summary-trigger:hover {{
    border: 1px solid var(--border-hover);
    background: rgba(255,255,255,0.1);
    transform: translateY(-1px);
}}

.ai-summary-modal-header {{
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.55rem;
}}

.ai-summary-badge {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--text-primary);
    font-size: 1.15rem;
    font-weight: 900;
    letter-spacing: -0.01em;
}}

.ai-summary-badge svg {{
    color: var(--accent);
    flex: 0 0 auto;
}}

.ai-summary-meta {{
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.45rem;
}}

.ai-summary-tag {{
    color: var(--accent);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.01em;
    background: rgba(96,165,250,0.14);
    border: 1px solid rgba(96,165,250,0.25);
    padding: 0.3rem 0.75rem;
    border-radius: 999px;
    white-space: nowrap;
}}

.ai-summary-time {{
    color: var(--text-secondary);
    font-size: 0.72rem;
    font-weight: 600;
    white-space: nowrap;
}}

.ai-summary-content {{
    direction: rtl;
    text-align: justify;
    color: #e6ecf4;
    font-size: 1.06rem;
    line-height: 2.25;
    margin-top: 1.6rem;
}}

.ai-summary-content > *:first-child {{
    margin-top: 0;
}}

.ai-summary-content > *:last-child {{
    margin-bottom: 0;
}}

.ai-summary-content p {{
    margin: 0 0 1rem 0;
}}

.ai-summary-content h1,
.ai-summary-content h2,
.ai-summary-content h3,
.ai-summary-content h4,
.ai-summary-content h5,
.ai-summary-content h6 {{
    color: var(--text-primary);
    font-weight: 800;
    letter-spacing: -0.01em;
    line-height: 1.8;
    text-align: right;
    margin: 1.4rem 0 0.7rem 0;
}}

.ai-summary-content strong {{
    color: var(--text-primary);
    font-weight: 800;
}}

.ai-summary-content em {{
    color: var(--text-primary);
    font-style: normal;
    opacity: 0.85;
}}

.ai-summary-content a {{
    color: var(--accent);
    text-decoration: underline;
    text-underline-offset: 3px;
}}

.ai-summary-content code {{
    background: rgba(255,255,255,0.08);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.1rem 0.4rem;
    font-size: 0.88em;
    direction: ltr;
    display: inline-block;
}}

.ai-summary-content ul,
.ai-summary-content ol {{
    margin: 0 0 1rem 0;
    padding-right: 1.5rem;
    padding-left: 0;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    text-align: right;
}}

.ai-summary-content blockquote {{
    margin: 0 0 1rem 0;
    padding: 0.2rem 1.1rem 0.2rem 0;
    border-right: 3px solid var(--border-hover);
    color: var(--text-secondary);
    text-align: right;
    opacity: 0.9;
}}

.ai-summary-content hr {{
    border: none;
    height: 1px;
    background: var(--border);
    margin: 1.6rem 0;
}}

@media (max-width: 768px) {{
    .ai-summary-trigger span {{
        display: none;
    }}

    .ai-summary-trigger {{
        padding: 0.6rem;
        width: 44px;
        height: 44px;
        justify-content: center;
    }}

    .ai-summary-content {{
        font-size: 1rem;
        line-height: 2.05;
    }}
}}

.search-wrap {{
    position: relative;
    display: flex;
    align-items: center;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 22px;
    box-shadow: var(--surface-shadow);
    backdrop-filter: var(--blur);
    -webkit-backdrop-filter: var(--blur);
    transition: border 0.2s ease;
}}

.search-wrap:focus-within {{
    border: 1px solid var(--border-hover);
}}

.search-icon {{
    position: absolute;
    right: 1.1rem;
    display: flex;
    align-items: center;
    color: var(--text-secondary);
    pointer-events: none;
}}

.search-input {{
    width: 100%;
    height: 36px;
    padding: 0.95rem 2.7rem 0.95rem 1.3rem;
    border: none;
    background: transparent;
    color: var(--text-primary);
    font-family: Peyda, sans-serif;
    font-size: 0.9rem;
    outline: none;
}}

.search-input::placeholder {{
    color: var(--text-secondary);
}}

.chips-row {{
    display: flex;
    align-items: center;
    gap: 0.55rem;
    overflow-x: auto;
    padding-bottom: 0.15rem;

    margin-left: -1rem;
    margin-right: -1rem;
    padding-inline-start: 1rem;
    padding-inline-end: 1rem;
}}

.chip {{
    flex: 0 0 auto;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.5rem 1.05rem;
    border-radius: 999px;
    background: var(--surface);
    border: 1px solid var(--border);
    box-shadow: var(--surface-shadow);
    backdrop-filter: var(--blur);
    -webkit-backdrop-filter: var(--blur);
    color: var(--text-secondary);
    font-family: Peyda, sans-serif;
    font-size: 0.84rem;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
    transition: border 0.2s ease, color 0.2s ease, background 0.2s ease, transform 0.15s ease;
}}

.chip:hover,
.chip:focus-visible {{
    border: 1px solid var(--border-hover);
    color: var(--text-primary);
}}

.chip.active {{
    background: rgba(96,165,250,0.16);
    border: 1px solid rgba(96,165,250,0.4);
    color: var(--text-primary);
}}

.chip-price {{
    color: #fbbf24;
    border: 1px solid rgba(251,191,36,0.22);
}}

.chip-price:hover {{
    border: 1px solid rgba(251,191,36,0.5);
    color: #fcd34d;
}}

.chip-price.active {{
    background: rgba(251,191,36,0.14);
    border: 1px solid rgba(251,191,36,0.45);
    color: #fcd34d;
}}

.price-card {{
    direction: rtl;
    position: relative;
    flex: 0 0 172px;
    width: 172px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 0.45rem;
    padding: 1.25rem;
    overflow: hidden;
    border-radius: var(--radius-card);
    background: var(--surface);
    border: 1px solid var(--border);
    box-shadow: var(--surface-shadow);
    backdrop-filter: var(--blur);
    -webkit-backdrop-filter: var(--blur);
    cursor: default;
    transition: transform 0.25s ease, border 0.25s ease, opacity 0.5s ease;
}}

.js .price-card {{
    opacity: 0;
}}

.js .price-card.in-view {{
    opacity: 1;
}}

.price-card:hover {{
    border: 1px solid rgba(251,191,36,0.4);
}}

.price-card.hidden-by-search {{
    display: none;
}}

.price-card-glow {{
    position: absolute;
    width: 220px;
    height: 200px;
    top: -90px;
    left: -90px;
    background: radial-gradient(circle, rgba(251,191,36,0.16), transparent 70%);
    pointer-events: none;
}}

.price-currency,
.price-value,
.price-time {{
    position: relative;
    z-index: 2;
}}

.price-currency {{
    color: var(--text-secondary);
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.01em;
}}

.price-value {{
    color: var(--text-primary);
    font-size: 1.32rem;
    font-weight: 900;
    letter-spacing: -0.01em;
    font-variant-numeric: tabular-nums;
    direction: ltr;
    text-align: right;
}}

.price-time {{
    color: var(--text-secondary);
    font-size: 0.76rem;
    opacity: 0.8;
}}

@media (max-width: 768px) {{
    .price-card {{
        flex: 0 0 42vw;
        width: 42vw;
        padding: 1rem 1.1rem;
    }}

    .price-value {{
        font-size: 1.18rem;
    }}
}}

.no-results {{
    display: none;
    flex-direction: column;
    align-items: center;
    gap: 0.4rem;
    padding: 3.5rem 1rem;
    color: var(--text-secondary);
    text-align: center;
}}

.no-results.visible {{
    display: flex;
}}

.no-results-icon {{
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--accent);
    opacity: 0.8;
    margin-bottom: 0.4rem;
}}

.no-results-title {{
    color: var(--text-primary);
    font-weight: 800;
    font-size: 1.05rem;
    letter-spacing: -0.01em;
}}

.no-results-subtitle {{
    font-size: 0.88rem;
}}

.empty-state {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.6rem;
    padding: 4rem 1rem;
    color: var(--text-secondary);
    text-align: center;
}}

.empty-state-icon {{
    font-size: 2.2rem;
    color: var(--accent);
}}

.empty-state-title {{
    color: var(--text-primary);
    font-weight: 800;
    font-size: 1.15rem;
    letter-spacing: -0.01em;
}}

.feed-empty {{
    flex: 0 0 100%;
    padding: 2rem 1rem;
    color: var(--text-secondary);
    font-size: 0.9rem;
    text-align: center;
    border-radius: 22px;
    border: 1px dashed var(--border);
}}

.feed-section {{
    display: flex;
    flex-direction: column;
    gap: 1rem;
    scroll-margin-top: 9rem;
    transition: background 0.6s ease;
}}

.feed-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
}}

.feed-title-container {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
}}

.feed-indicator {{
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 14px var(--accent);
}}

.feed-title {{
    font-size: 1.08rem;
    font-weight: 900;
    letter-spacing: -0.01em;
}}

.carousel-nav-group {{
    display: flex;
    gap: 0.5rem;
}}

.carousel-nav {{
    width: 40px;
    height: 40px;
    border-radius: 50%;
    border: 1px solid var(--border);
    background: var(--surface);
    box-shadow: var(--surface-shadow);
    backdrop-filter: var(--blur);
    -webkit-backdrop-filter: var(--blur);
    color: #ffffff;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: border 0.2s ease, background 0.2s ease, transform 0.15s ease;
}}

.carousel-nav:focus-visible {{
    border: 1px solid var(--border-hover);
}}

.carousel-nav svg {{
    filter: drop-shadow(0 1px 2px rgba(0,0,0,0.5));
}}

.carousel-nav:hover {{
    border: 1px solid var(--border-hover);
    background: rgba(255,255,255,0.1);
    transform: translateY(-1px);
}}

.feed-carousel {{
    display: flex;
    direction: ltr;
    flex-direction: row-reverse;
    gap: 1rem;
    overflow-x: auto;
    overflow-y: hidden;
    scroll-behavior: smooth;
    padding: 0 0 0.5rem 0;
    
    margin: 0;
    margin-left: -1rem;
    margin-right: -1rem;
    padding-inline-start: 1rem;
    padding-inline-end: 1rem;
}}

.news-card {{
    direction: rtl;
    position: relative;
    flex: 0 0 320px;
    width: 320px;
    border-radius: var(--radius-card);
    overflow: hidden;
    background: var(--surface);
    border: 1px solid var(--border);
    box-shadow: var(--surface-shadow);
    backdrop-filter: var(--blur);
    -webkit-backdrop-filter: var(--blur);
    display: flex;
    flex-direction: column;
    cursor: pointer;
    transition: transform 0.25s ease, border 0.25s ease, opacity 0.5s ease, filter 0.3s ease;
}}

.js .news-card {{
    opacity: 0;
    transform: translateY(16px);
}}

.js .news-card.in-view {{
    opacity: 1;
    transform: translateY(0);
}}

.news-card.hidden-by-search {{
    display: none;
}}

.news-card.is-read {{
    filter: saturate(0.55) brightness(0.82);
}}

.news-card.is-read:hover {{
    filter: saturate(0.75) brightness(0.92);
}}

.news-card:hover,
.news-card:focus-visible {{
    transform: translateY(-6px);
    border: 1px solid var(--border-hover);
}}

.news-card:focus-visible {{
    outline: 2px solid var(--accent);
    outline-offset: -3px;
}}

.card-background-glow {{
    position: absolute;
    width: 320px;
    height: 280px;
    top: -120px;
    left: -120px;
    background: radial-gradient(circle, rgba(96,165,250,0.18), transparent 70%);
    pointer-events: none;
}}

.card-top,
.card-content,
.card-bottom {{
    position: relative;
    z-index: 3;
}}

.card-top {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
    padding: 1.1rem 1.25rem 0 1.25rem;
}}

.has-media .card-top {{
    padding-top: 0.85rem;
}}

.card-source {{
    color: var(--accent);
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.01em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}

.card-top-right {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex: 0 0 auto;
}}

.card-date {{
    color: var(--text-secondary);
    font-size: 0.78rem;
    letter-spacing: 0.01em;
    white-space: nowrap;
}}

.unread-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 8px var(--accent);
    flex: 0 0 auto;
}}

.is-read .unread-dot {{
    display: none;
}}

.card-media {{
    position: relative;
    width: 100%;
    aspect-ratio: 16 / 9;
    overflow: hidden;
    background: rgba(255,255,255,0.05);
}}

.card-media-thumb {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    transition: transform 0.4s ease;
}}

.card-media-placeholder {{
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--accent);
    background: rgba(96,165,250,0.08);
}}

.card-media-placeholder svg {{
    opacity: 0.72;
}}

.card-media--empty .card-media-placeholder {{
    background: rgba(96,165,250,0.06);
}}

.news-card:hover .card-media-thumb {{
    transform: scale(1.04);
}}

.card-media-fade {{
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, transparent 55%, rgba(10,10,12,0.55) 100%);
    pointer-events: none;
}}

.card-media--empty .card-media-fade {{
    display: none;
}}

.card-media-badge {{
    position: absolute;
    bottom: 0.6rem;
    left: 0.6rem;
    background: rgba(0,0,0,0.72);
    color: #ffffff;
    font-size: 0.68rem;
    font-weight: 700;
    padding: 0.15rem 0.55rem;
    border-radius: 999px;
    backdrop-filter: blur(6px);
}}

.card-media-kind {{
    position: absolute;
    bottom: 0.6rem;
    right: 0.6rem;
    background: rgba(0,0,0,0.72);
    color: #ffffff;
    font-size: 0.62rem;
    font-weight: 800;
    letter-spacing: 0.04em;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    backdrop-filter: blur(6px);
}}

.card-content {{
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 0.65rem 1.25rem 1.1rem 1.25rem;
}}

.card-text {{
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 0.5rem;
}}

.card-excerpt {{
    font-size: 0.96rem;
    color: var(--text-primary);
    line-height: 1.75;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
    min-height: calc(1.75em * 3);
}}

.card-bottom {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 1.25rem 1.1rem 1.25rem;
}}

.read-more {{
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    color: var(--accent);
    font-size: 0.85rem;
    font-weight: 700;
    transition: gap 0.2s ease;
}}

.news-card:hover .read-more {{
    gap: 0.55rem;
}}

.modal-overlay {{
    position: fixed;
    inset: 0;
    z-index: 5000;
    display: none;
    align-items: center;
    justify-content: center;
    padding: 1rem;
    background: rgba(0,0,0,0.7);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
}}

.modal-overlay.active {{
    display: flex;
}}

.news-modal {{
    position: relative;
    width: 100%;
    max-width: 900px;
    max-height: 92vh;
    overflow-y: auto;
    border-radius: 34px;
    padding: 2rem;
    background: var(--modal-bg);
    border: 1px solid rgba(255,255,255,0.1);
    box-shadow: 0 30px 80px rgba(0,0,0,0.6);
    backdrop-filter: blur(34px) saturate(160%);
    -webkit-backdrop-filter: blur(34px) saturate(160%);
    animation: modalShow 0.25s ease;
}}

@keyframes modalShow {{
    from {{ opacity: 0; transform: translateY(20px) scale(0.98); }}
    to {{ opacity: 1; transform: translateY(0) scale(1); }}
}}

.modal-close {{
    position: absolute;
    top: 1rem;
    left: 1rem;
    width: 48px;
    height: 48px;
    border-radius: 50%;
    border: 0;
    background: rgba(255,255,255,0.1);
    color: white;
    font-size: 1.2rem;
    cursor: pointer;
    transition: background 0.2s ease;
}}

.modal-close:hover {{
    background: rgba(255,255,255,0.18);
}}

.modal-header {{
    margin-bottom: 1.6rem;
}}

.modal-source {{
    display: inline-block;
    color: var(--accent);
    font-size: 0.8rem;
    font-weight: 700;
    background: rgba(96,165,250,0.16);
    padding: 0.32rem 0.85rem;
    border-radius: 999px;
    margin-bottom: 0.75rem;
}}

.modal-date {{
    color: var(--text-secondary);
    font-size: 0.9rem;
    margin-bottom: 1rem;
}}

.modal-title {{
    font-weight: 900;
    line-height: 2.15;
    font-size: 1.42rem;
    letter-spacing: -0.01em;
}}

.modal-media-strip {{
    display: none;
    gap: 0.75rem;
    overflow-x: auto;
    margin-bottom: 1.6rem;
}}

.modal-media-item {{
    flex: 0 0 auto;
    max-height: 380px;
    max-width: 100%;
    border-radius: 22px;
    background: #000;
}}

.modal-content {{
    color: #e6ecf4;
    line-height: 2.25;
    font-size: 1.06rem;
}}

.modal-related {{
    display: none;
    margin-top: 1.8rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border);
}}

.modal-related-title {{
    font-size: 0.98rem;
    font-weight: 800;
    margin-bottom: 0.9rem;
}}

.modal-related-list {{
    display: flex;
    gap: 0.75rem;
    overflow-x: auto;
}}

.related-item {{
    flex: 0 0 210px;
    display: flex;
    gap: 0.6rem;
    align-items: center;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 0.6rem;
    cursor: pointer;
    transition: border 0.2s ease;
}}

.related-item:hover,
.related-item:focus-visible {{
    border-color: var(--border-hover);
}}

.related-item:focus-visible {{
    outline: 2px solid var(--accent);
    outline-offset: 2px;
}}

.related-thumb {{
    width: 46px;
    height: 46px;
    border-radius: 12px;
    object-fit: cover;
    flex: 0 0 auto;
    background: rgba(255,255,255,0.06);
}}

.related-thumb-placeholder {{
    width: 46px;
    height: 46px;
    border-radius: 12px;
    flex: 0 0 auto;
    background: rgba(96,165,250,0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--accent);
}}

.related-text {{
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}}

.related-meta {{
    display: flex;
    align-items: center;
    gap: 0.35rem;
}}

.related-source {{
    font-size: 0.7rem;
    color: var(--accent);
    font-weight: 700;
}}

.related-time {{
    font-size: 0.7rem;
    color: var(--text-secondary);
}}

.related-title {{
    font-size: 0.82rem;
    color: var(--text-primary);
    line-height: 1.6;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}}

.scroll-top-btn {{
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    z-index: 2000;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    background: var(--surface);
    backdrop-filter: var(--blur);
    -webkit-backdrop-filter: var(--blur);
    border: 1px solid var(--border);
    box-shadow: var(--surface-shadow);
    color: #ffffff;
    opacity: 0;
    pointer-events: none;
    transform: translateY(10px);
    transition: opacity 0.25s ease, transform 0.2s ease, background 0.2s ease;
}}

.scroll-top-btn svg {{
    filter: drop-shadow(0 1px 2px rgba(0,0,0,0.5));
}}

.scroll-top-btn.visible {{
    opacity: 1;
    pointer-events: auto;
    transform: translateY(0);
}}

.scroll-top-btn:hover,
.scroll-top-btn:focus-visible {{
    transform: translateY(-4px);
    background: rgba(255,255,255,0.14);
}}

@media (prefers-reduced-motion: reduce) {{
    html {{ scroll-behavior: auto; }}
    .js .news-card {{ opacity: 1; transform: none; }}
    .news-card,
    .scroll-top-btn,
    .live-dot {{
        transition: none;
        animation: none;
    }}
}}

@media (max-width: 768px) {{
    .main-layout {{ padding: 1rem; }}

    .app-header {{
        padding: 0.85rem 1rem;
    }}

    .header-top {{
        gap: 0.6rem;
    }}

    .header-actions {{
        gap: 0.5rem;
    }}

    .live-badge {{
        padding: 0.6rem;
        height: 36px;
        justify-content: center;
    }}

    .news-card {{
        flex: 0 0 78vw;
        width: 78vw;
    }}

    .news-modal {{
        padding: 1.5rem;
        border-radius: 28px;
    }}
}}

</style>

</head>

<body>

<header class="app-header">

    <div class="header-inner">

        <div class="header-top">

            <div class="search-wrap">

                <input
                    type="text"
                    class="search-input"
                    id="searchInput"
                    placeholder="جستجو در صفحه..."
                    oninput="filterNews(this.value)"
                    aria-label="جستجو در اخبار"
                />

                <span class="search-icon">
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"></circle><path d="m21 21-4.3-4.3"></path></svg>
                </span>

            </div>

            <div class="header-actions">
                {summary_trigger}

                <div class="live-badge">
                    <div class="live-dot"></div>

                    <span id="latest-update" data-time="{latest_update}">
                        در حال بروزرسانی...
                    </span>
                </div>
            </div>

        </div>

        <div class="chips-row">
            {''.join(chips)}
        </div>

    </div>

</header>

<main class="main-layout">

    <div class="no-results" id="noResults">
        <div class="no-results-icon">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"></circle><path d="m21 21-4.3-4.3"></path><path d="M8 8l6 6M14 8l-6 6"></path></svg>
        </div>
        <div class="no-results-title">نتیجه‌ای پیدا نشد</div>
        <div class="no-results-subtitle">عبارت دیگری را امتحان کنید</div>
    </div>

    {price_cards}

    {main_content}

</main>

<footer class="app-footer">
    <div class="footer-text">
        تقدیم به همه جاویدنامان ایران - شِف
    </div>
</footer>

<div
    class="modal-overlay"
    id="newsModal"
    role="dialog"
    aria-modal="true"
    aria-labelledby="modalTitle"
>

    <div class="news-modal">

        <button
            class="modal-close"
            onclick="closeNewsModal()"
            aria-label="بستن"
        >
            ✕
        </button>

        <div class="modal-header" id="modalHeader">

            <div class="modal-source" id="modalSource"></div>

            <div class="modal-date" id="modalDate"></div>

            <div class="modal-title" id="modalTitle"></div>

        </div>

        <div class="modal-media-strip" id="modalMedia"></div>

        <div
            class="modal-content"
            style="text-align: justify"
            id="modalContent"
        ></div>

        <div class="modal-related" id="modalRelated">
            <div class="modal-related-title">اخبار مرتبط</div>
            <div class="modal-related-list" id="modalRelatedList"></div>
        </div>

    </div>

</div>

{summary_modal}

<button
    class="scroll-top-btn"
    onclick="scrollToTop()"
    aria-label="بازگشت به بالا"
>
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>
</button>

<script>

function timeAgo(dateString) {{
    const parts = dateString.split(/[- :]/);

    const date = new Date(
        parts[0],
        parts[1] - 1,
        parts[2],
        parts[3],
        parts[4],
        parts[5]
    );

    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60) {{
        return "چند لحظه پیش";
    }}

    const minutes = Math.floor(seconds / 60);

    if (minutes < 60) {{
        return `${{minutes}} دقیقه پیش`;
    }}

    const hours = Math.floor(minutes / 60);

    if (hours < 24) {{
        return `${{hours}} ساعت پیش`;
    }}

    const days = Math.floor(hours / 24);

    if (days < 30) {{
        return `${{days}} روز پیش`;
    }}

    const months = Math.floor(days / 30);

    if (months < 12) {{
        return `${{months}} ماه پیش`;
    }}

    const years = Math.floor(months / 12);

    return `${{years}} سال پیش`;
}}

const updateElement = document.getElementById("latest-update");
const updateTime = updateElement.dataset.time;

function refreshAllTimes() {{
    updateElement.textContent = timeAgo(updateTime);

    document.querySelectorAll("[data-live-time]").forEach(function(el) {{
        const value = el.dataset.liveTime;
        if (value) {{
            el.textContent = timeAgo(value);
        }}
    }});
}}

refreshAllTimes();

setInterval(refreshAllTimes, 60000);

const modal = document.getElementById("newsModal");

function renderModalMedia(media) {{
    const container = document.getElementById("modalMedia");
    container.innerHTML = "";

    if (!media || media.length === 0) {{
        container.style.display = "none";
        return;
    }}

    container.style.display = "flex";

    media.forEach(function(item) {{
        let el;

        if (item.type === "video") {{
            el = document.createElement("video");
            el.src = item.url;
            el.controls = true;
            el.playsInline = true;
            el.preload = "metadata";
            if (item.poster) {{
                el.poster = item.poster;
            }}
        }} else {{
            el = document.createElement("img");
            el.src = item.url;
            el.loading = "lazy";
            el.alt = "";
        }}

        el.className = "modal-media-item";
        container.appendChild(el);
    }});
}}

function openRelated(anchor) {{
    const target = document.querySelector('[data-anchor="' + anchor + '"]');

    if (target) {{
        target.click();
        document.querySelector(".news-modal").scrollTo({{ top: 0, behavior: "smooth" }});
    }}
}}

function renderRelated(related) {{
    const section = document.getElementById("modalRelated");
    const list = document.getElementById("modalRelatedList");
    list.innerHTML = "";

    if (!related || related.length === 0) {{
        section.style.display = "none";
        return;
    }}

    section.style.display = "block";

    related.forEach(function(item) {{
        const el = document.createElement("div");
        el.className = "related-item";
        el.setAttribute("role", "button");
        el.setAttribute("tabindex", "0");
        el.onclick = function() {{ openRelated(item.anchor); }};
        el.onkeydown = function(event) {{
            if (event.key === "Enter" || event.key === " ") {{
                event.preventDefault();
                openRelated(item.anchor);
            }}
        }};

        if (item.thumbnail) {{
            const thumb = document.createElement("img");
            thumb.className = "related-thumb";
            thumb.src = item.thumbnail;
            thumb.alt = "";
            thumb.loading = "lazy";
            el.appendChild(thumb);
        }} else {{
            const placeholder = document.createElement("div");
            placeholder.className = "related-thumb-placeholder";
            placeholder.innerHTML = '{self.RELATED_PLACEHOLDER_SVG}';
            el.appendChild(placeholder);
        }}

        const textWrap = document.createElement("div");
        textWrap.className = "related-text";

        const metaWrap = document.createElement("div");
        metaWrap.className = "related-meta";

        const sourceEl = document.createElement("div");
        sourceEl.className = "related-source";
        sourceEl.textContent = item.source || "";

        const timeEl = document.createElement("div");
        timeEl.className = "related-time";
        if (item.date) {{
            timeEl.dataset.liveTime = item.date;
            timeEl.textContent = timeAgo(item.date);
        }}

        metaWrap.appendChild(sourceEl);
        metaWrap.appendChild(timeEl);

        const titleEl = document.createElement("div");
        titleEl.className = "related-title";
        titleEl.textContent = item.title || "";

        textWrap.appendChild(metaWrap);
        textWrap.appendChild(titleEl);
        el.appendChild(textWrap);

        list.appendChild(el);
    }});

    list.scrollLeft = 0;
}}

function openNewsModal(lang, title, content, date, link, source, media, related) {{

    document.body.classList.add("modal-open");
    modal.classList.add("active");

    var modalTitleElement = document.getElementById("modalTitle");
    var modalContentElement = document.getElementById("modalContent");

    if (lang == "fa") {{
        modalContentElement.innerHTML = content + "<br><br><a href='" + link + "' style='text-decoration: underline; color: var(--accent);'>لینک فید</a>";

        modalTitleElement.style.direction = "rtl";
        modalTitleElement.style.textAlign = "right";

        modalContentElement.style.direction = "rtl";
        modalContentElement.style.textAlign = "right";
    }} else {{
        modalContentElement.innerHTML = content + "<br><br><a href='" + link + "' style='text-decoration: underline; color: var(--accent);'>Feed Link</a>";

        modalTitleElement.style.direction = "ltr";
        modalTitleElement.style.textAlign = "left";

        modalContentElement.style.direction = "ltr";
        modalContentElement.style.textAlign = "left";
    }}

    document.getElementById("modalSource").textContent = source;

    const modalDateElement = document.getElementById("modalDate");
    modalDateElement.dataset.liveTime = date;
    modalDateElement.textContent = date ? timeAgo(date) : "";

    renderModalMedia(media);
    renderRelated(related);

    document.querySelector(".modal-close").focus();
}}

function closeNewsModal() {{
    document.body.classList.remove("modal-open");
    modal.classList.remove("active");
}}

modal.addEventListener("click", function(event) {{
    if (event.target === modal) {{
        closeNewsModal();
    }}
}});

const summaryModal = document.getElementById("aiSummaryModal");

function openSummaryModal() {{
    if (!summaryModal) {{
        return;
    }}

    document.body.classList.add("modal-open");
    summaryModal.classList.add("active");

    const closeBtn = summaryModal.querySelector(".modal-close");
    if (closeBtn) {{
        closeBtn.focus();
    }}
}}

function closeSummaryModal() {{
    if (!summaryModal) {{
        return;
    }}

    document.body.classList.remove("modal-open");
    summaryModal.classList.remove("active");
}}

if (summaryModal) {{
    summaryModal.addEventListener("click", function(event) {{
        if (event.target === summaryModal) {{
            closeSummaryModal();
        }}
    }});
}}

document.addEventListener("keydown", function(event) {{
    if (event.key === "Escape") {{
        closeNewsModal();
        closeSummaryModal();
    }}
}});

function scrollToTop() {{
    window.scrollTo({{ top: 0, behavior: "smooth" }});
}}

const READ_KEY = "dayereh_read_articles";

function getReadSet() {{
    try {{
        return new Set(JSON.parse(localStorage.getItem(READ_KEY)) || []);
    }} catch (e) {{
        return new Set();
    }}
}}

function markRead(anchor) {{
    const readSet = getReadSet();
    readSet.add(anchor);

    try {{
        localStorage.setItem(READ_KEY, JSON.stringify([...readSet]));
    }} catch (e) {{}}
}}

(function applyReadState() {{
    const readSet = getReadSet();

    document.querySelectorAll(".news-card[data-anchor]").forEach(function(card) {{
        if (readSet.has(card.dataset.anchor)) {{
            card.classList.add("is-read");
        }}
    }});
}})();

function scrollCarousel(sectionId, direction) {{
    const section = document.getElementById(sectionId);

    if (!section) {{
        return;
    }}

    const carousel = section.querySelector(".feed-carousel");
    carousel.scrollBy({{ left: direction * 340, behavior: "smooth" }});
}}

function jumpToSection(sectionId) {{
    const section = document.getElementById(sectionId);

    if (!section) {{
        return;
    }}

    section.scrollIntoView({{ behavior: "smooth", block: "start" }});
    setActiveChip(sectionId);
}}

const chipMap = new Map();
document.querySelectorAll(".chip[data-chip-target]").forEach(function(chip) {{
    chipMap.set(chip.dataset.chipTarget, chip);
}});

function setActiveChip(sectionId) {{
    chipMap.forEach(function(chip) {{
        chip.classList.remove("active");
    }});

    const chip = chipMap.get(sectionId);
    if (chip) {{
        chip.classList.add("active");
        chip.scrollIntoView({{ behavior: "smooth", inline: "center", block: "nearest" }});
    }}
}}

if (chipMap.size > 0 && "IntersectionObserver" in window) {{
    const spyObserver = new IntersectionObserver(function(entries) {{
        const visible = entries.filter(function(entry) {{ return entry.isIntersecting; }});

        if (visible.length > 0) {{
            visible.sort(function(a, b) {{ return b.intersectionRatio - a.intersectionRatio; }});
            setActiveChip(visible[0].target.id);
        }}
    }}, {{ rootMargin: "-15% 0px -70% 0px", threshold: [0, 0.25, 0.5, 0.75, 1] }});

    document.querySelectorAll(".feed-section[data-source-section]").forEach(function(section) {{
        spyObserver.observe(section);
    }});
}}

function alignCarouselsToStart() {{
    document.querySelectorAll(".feed-carousel").forEach(function(carousel) {{
        carousel.scrollLeft = carousel.scrollWidth;
    }});
}}

alignCarouselsToStart();
window.addEventListener("load", alignCarouselsToStart);

function normalize(text) {{
    return (text || "").toLowerCase().trim();
}}

function filterNews(query) {{
    const q = normalize(query);
    const sections = document.querySelectorAll(".feed-section");
    let anyVisible = false;

    sections.forEach(function(section) {{
        const cards = section.querySelectorAll(".news-card, .price-card");
        let sectionHasMatch = q === "";

        cards.forEach(function(card) {{
            const haystack = normalize(card.dataset.search);
            const matches = q === "" || haystack.indexOf(q) !== -1;

            card.classList.toggle("hidden-by-search", !matches);

            if (matches) {{
                sectionHasMatch = true;
            }}
        }});

        section.style.display = sectionHasMatch ? "" : "none";

        if (sectionHasMatch) {{
            anyVisible = true;
        }}
    }});

    document.getElementById("noResults").classList.toggle(
        "visible",
        sections.length > 0 && !anyVisible
    );
}}

const scrollBtn = document.querySelector(".scroll-top-btn");

window.addEventListener("scroll", function() {{
    if (window.scrollY > 400) {{
        scrollBtn.classList.add("visible");
    }} else {{
        scrollBtn.classList.remove("visible");
    }}
}});

if ("IntersectionObserver" in window) {{
    const revealObserver = new IntersectionObserver(function(entries) {{
        entries.forEach(function(entry) {{
            if (entry.isIntersecting) {{
                entry.target.classList.add("in-view");
                revealObserver.unobserve(entry.target);
            }}
        }});
    }}, {{ threshold: 0.12 }});

    document.querySelectorAll(".news-card").forEach(function(card) {{
        revealObserver.observe(card);
    }});
}} else {{
    document.querySelectorAll(".news-card").forEach(function(card) {{
        card.classList.add("in-view");
    }});
}}

</script>

</body>

</html>
"""
