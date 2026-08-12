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


_TOKEN_RE = re.compile(r"\w+")

_MEDIA_PLACEHOLDER_SVG = (
    '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="3" y="4" width="18" height="16" rx="2"></rect>'
    '<circle cx="8.5" cy="9" r="1.5"></circle>'
    '<path d="M3 17l5-5 4 4 3-3 6 6"></path>'
    '</svg>'
)

_RELATED_PLACEHOLDER_SVG = (
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="3" y="4" width="18" height="16" rx="2"></rect>'
    '<circle cx="8.5" cy="9" r="1.5"></circle>'
    '<path d="M3 17l5-5 4 4 3-3 6 6"></path>'
    '</svg>'
)

_FULLSCREEN_ICON_SVG = (
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M21 16v3a2 2 0 0 1-2 2h-3M8 21H5a2 2 0 0 1-2-2v-3"></path>'
    '</svg>'
)


class HTMLBuilder:

    def __init__(self, storage=None):
        self.storage = storage
        self.compressor = MediaCompressor(image_quality=70, video_crf=30)
        self._thumb_cache = {}

    def video_thumb_url(self, video_url):
        parsed = urlparse(str(video_url))
        stem = Path(parsed.path).stem
        base = str(video_url).rsplit("/", 1)[0]
        return f"{base}/{stem}_thumb.jpg"

    def ensure_video_thumbnail(self, video_url):
        if not video_url:
            return ""

        cached = self._thumb_cache.get(video_url)
        if cached is not None:
            return cached

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
            self.compressor.extract_video_thumbnail(str(video_path), str(thumb_path))
            self._thumb_cache[video_url] = thumb_url
            return thumb_url
        except Exception as e:
            print(f"error generating video thumbnail: {e}")
            self._thumb_cache[video_url] = ""
            return ""

    def resolve_card_thumbnail(self, media_url):
        if not media_url:
            return ""

        if MediaType.detect_media_type_url(media_url) == "video":
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

        return (
            '<button class="summary-pill" type="button" onclick="openSummaryModal()" '
            'aria-haspopup="dialog" aria-controls="aiSummaryModal">'
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M12 3v3M12 18v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M3 12h3M18 12h3'
            'M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"></path><circle cx="12" cy="12" r="3.2"></circle></svg>'
            '<span>خلاصه هوشمند</span>'
            '</button>'
        )

    def build_summary_modal(self, summary_html, update_time=""):
        if not summary_html:
            return ""

        safe_time = StringUtils.safe(update_time) if update_time else ""
        time_html = (
            f'<span class="ai-summary-time" data-live-time="{safe_time}"></span>'
            if safe_time else ""
        )

        return f"""
<div class="modal-overlay" id="aiSummaryModal" role="dialog" aria-modal="true" aria-labelledby="aiSummaryModalTitle">
    <button class="modal-close" type="button" onclick="closeSummaryModal()" aria-label="بستن">
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18M6 6l12 12"></path></svg>
    </button>
    <div class="news-modal">
        <div class="modal-inner">
            <div class="ai-summary-header">
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
</div>
"""

    def tokenize(self, text):
        return {t for t in _TOKEN_RE.findall(str(text).lower()) if len(t) > 1}

    def compute_related(self, flat_items, limit=4):
        related_map = {}
        n = len(flat_items)

        for i in range(n):
            current = flat_items[i]
            current_tokens = current["tokens"]
            scored = []

            for j in range(n):
                if i == j:
                    continue

                other = flat_items[j]
                other_tokens = other["tokens"]
                intersection = current_tokens & other_tokens

                if not intersection:
                    continue

                union_len = len(current_tokens) + len(other_tokens) - len(intersection)
                score = len(intersection) / union_len
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

    def _build_media_badges(self, media_list):
        if not media_list:
            return ""

        first = media_list[0]
        kind_badge = ""

        if first["type"] == "gif":
            kind_badge = '<span class="card-media-kind">گیف</span>'
        elif first["type"] == "video":
            kind_badge = '<span class="card-media-kind">ویدیو</span>'

        overflow_badge = (
            f'<span class="card-media-badge">+{len(media_list) - 1}</span>'
            if len(media_list) > 1 else ""
        )

        return kind_badge + overflow_badge

    def _build_media_block(self, media_list, loading_attr):
        if not media_list:
            return f'<div class="card-media card-media-empty">{_MEDIA_PLACEHOLDER_SVG}</div>'

        first = media_list[0]

        if first["type"] == "video":
            thumb_src = first.get("poster") or ""
            media_thumb = (
                f'<img class="card-media-thumb" src="{StringUtils.safe(thumb_src)}" alt="" loading="{loading_attr}">'
                if thumb_src else
                f'<div class="card-media-thumb-empty">{_MEDIA_PLACEHOLDER_SVG}</div>'
            )
        else:
            media_thumb = (
                f'<img class="card-media-thumb" src="{StringUtils.safe(first["url"])}" alt="" loading="{loading_attr}">'
            )

        badges = self._build_media_badges(media_list)

        return f'<div class="card-media">{media_thumb}{badges}</div>'

    def build_card(self, item, source, anchor, related, eager):
        title = getattr(item, "title", "")
        lang = StringUtils.detect_lang(title)
        content = getattr(item, "content", "")
        date = getattr(item, "date", "")
        link = getattr(item, "link", "")

        excerpt_source = str(content).replace("\n", " ").strip()
        excerpt = StringUtils.truncate_text_char(excerpt_source, 110)

        safe_title = StringUtils.safe(title)
        safe_content = StringUtils.safe(content).replace("\n", "<br>")
        safe_excerpt = StringUtils.safe(excerpt)
        safe_date = StringUtils.safe(date)
        safe_link = StringUtils.safe(link)
        safe_lang = StringUtils.safe(lang)

        rtl_style = "" if safe_lang == "fa" else " style=\"direction: ltr; text-align: left;\""

        raw_media = getattr(item, "media", []) or []
        media_list = self.build_media_list(raw_media)
        media_block = self._build_media_block(media_list, "eager" if eager else "lazy")

        media_json = StringUtils.safe(json.dumps(media_list, ensure_ascii=False))
        related_json = StringUtils.safe(json.dumps(related, ensure_ascii=False))

        card_class = "news-card in-view" if eager else "news-card"

        return f"""
<article
    class="{card_class}"
    role="button"
    tabindex="0"
    data-search="{safe_title} {safe_excerpt} {source}"
    data-anchor="{anchor}"
    aria-label="{safe_title}"
    onkeydown="if(event.key==='Enter'||event.key===' '){{event.preventDefault();this.click();}}"
    onclick='this.classList.add("is-read");markRead(`{anchor}`);openNewsModal(`{safe_lang}`,`{safe_title}`,`{safe_content}`,`{safe_date}`,`{safe_link}`,`{source}`,JSON.parse(`{media_json}`),JSON.parse(`{related_json}`))'
><a id="{anchor}" class="anchor-marker"></a>
    {media_block}
    <div class="card-body">
        <div class="card-meta">
            <span class="card-source">{source}</span>
            <div class="card-time-wrap">
                <span class="card-time" id="date-{anchor}" data-live-time="{safe_date}">{safe_date}</span>
                <span class="unread-dot" id="dot-{anchor}"></span>
            </div>
        </div>
        <p class="card-excerpt"{rtl_style}>{safe_excerpt}</p>
    </div>
</article>
"""

    def build_section(self, feed, anchors, related_map):
        source = StringUtils.safe(feed.get("source", "خبرگزاری"))
        section_id = "section-" + str(IDGenerator.generate(source))
        items = feed.get("items", [])

        cards = [
            self.build_card(item, source, anchor, related_map.get(anchor, []), index < 2)
            for index, (item, anchor) in enumerate(zip(items, anchors))
        ]

        body = "".join(cards) if cards else '<div class="feed-empty">فعلاً خبری در این بخش موجود نیست</div>'

        return f"""
<section class="feed-section" id="{section_id}" data-source-section>
    <div class="section-label">
        <div class="section-label-left">
            <span class="section-dot"></span>
            <span class="section-title">{source}</span>
        </div>
    </div>
    <div class="feed-grid">
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

            cards.append(
                f'<div class="price-card" data-search="{currency}" data-time="{time}">'
                f'<span class="price-currency">{currency}</span>'
                f'<span class="price-value numeral">{price}</span>'
                f'<span class="price-time numeral" data-live-time="{time}">{time}</span>'
                f'</div>'
            )

        return f"""
<section class="price-section" id="section-prices" data-source-section>
    <div class="section-label">
        <div class="section-label-left">
            <span class="section-dot"></span>
            <span class="section-title">نرخ ارز و طلا</span>
        </div>
    </div>
    <div class="price-strip">
        {''.join(cards)}
    </div>
</section>
"""

    def build(self, feeds, prices, summery=None):
        summery = summery or []
        latest_update = TimeUtils.to_string(TimeUtils.now())

        flat_items = []
        feed_anchor_lists = []

        for feed in feeds:
            source_raw = feed.get("source", "-")
            anchors = []

            for item in feed.get("items", []):
                title = getattr(item, "title", "")
                content = getattr(item, "content", "")
                date = getattr(item, "date", "")

                anchor = IDGenerator.generate(f"{date}{title}{content}")
                anchors.append(anchor)

                raw_media = getattr(item, "media", []) or []
                thumbnail = self.resolve_card_thumbnail(raw_media[0] if raw_media else "")

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
            chips.append(
                '<button class="chip chip-price" data-chip-target="section-prices" '
                'onclick="jumpToSection(\'section-prices\')">نرخ ارز و طلا</button>'
            )

        for feed, anchors in zip(feeds, feed_anchor_lists):
            source = StringUtils.safe(feed.get("source", "خبرگزاری"))
            section_id = "section-" + str(IDGenerator.generate(source))

            sections.append(self.build_section(feed, anchors, related_map))
            chips.append(
                f'<button class="chip" data-chip-target="{section_id}" '
                f'onclick="jumpToSection(\'{section_id}\')">{source}</button>'
            )

        has_any_feed = len(feeds) > 0

        summary_html = self.build_summary_content(summery[0] if len(summery) > 0 else "")
        summary_trigger = self.build_summary_trigger(summary_html if summary_html != "" else None)
        summary_modal = self.build_summary_modal(summary_html, summery[1] if len(summery) > 1 else "")
        price_cards = self.build_price_cards(prices)

        main_content = "".join(sections) if has_any_feed else """
<div class="empty-state">
    <div class="empty-state-icon">
        <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="9"></circle></svg>
    </div>
    <div class="empty-state-title">هنوز خبری برای نمایش وجود ندارد</div>
    <div class="empty-state-subtitle">به‌محض انتشار اخبار جدید، اینجا نمایش داده می‌شوند</div>
</div>
"""

        return _PAGE_TEMPLATE.format(
            latest_update=latest_update,
            summary_trigger=summary_trigger,
            chips="".join(chips),
            price_cards=price_cards,
            main_content=main_content,
            summary_modal=summary_modal,
            related_placeholder_svg=_RELATED_PLACEHOLDER_SVG,
            fullscreen_icon_svg=_FULLSCREEN_ICON_SVG,
        )


_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0A0A0B">
<meta name="description" content="دایره؛ دسترسی سریع و زیبا به تازه‌ترین اخبار از منابع مختلف">
<title>دایره</title>
<link rel="icon" type="image/webp" href="https://raw.githubusercontent.com/ch3fferson/dayereh/main/feeds/view/assets/favicon.webp">
<script>document.documentElement.classList.add("js");</script>
<style>
@font-face {{
    font-family: Peyda;
    src: url('https://raw.githubusercontent.com/ch3fferson/dayereh/main/feeds/view/assets/fonts/Peyda-Regular.ttf') format('truetype');
    font-weight: 400;
    font-display: swap;
}}
@font-face {{
    font-family: Peyda;
    src: url('https://raw.githubusercontent.com/ch3fferson/dayereh/main/feeds/view/assets/fonts/Peyda-Bold.ttf') format('truetype');
    font-weight: 700;
    font-display: swap;
}}
@font-face {{
    font-family: Peyda;
    src: url('https://raw.githubusercontent.com/ch3fferson/dayereh/main/feeds/view/assets/fonts/Peyda-Black.ttf') format('truetype');
    font-weight: 900;
    font-display: swap;
}}
:root {{
    --bg: #FAFAF8;
    --surface: #FFFFFF;
    --border: rgba(20,20,22,0.09);
    --border-strong: rgba(20,20,22,0.16);
    --text: #16161A;
    --text-secondary: #6B6B72;
    --text-tertiary: #9A9A9F;
    --accent: #3D5CFF;
    --accent-dim: rgba(61,92,255,0.09);
    --accent-line: rgba(61,92,255,0.35);
    --gold: #B8860B;
    --shadow: 0 1px 2px rgba(20,20,22,0.04), 0 8px 24px rgba(20,20,22,0.05);
    --divider: rgba(20,20,22,0.07);
    color-scheme: light;
}}
:root[data-theme="dark"] {{
    --bg: #0A0A0B;
    --surface: #131316;
    --border: rgba(255,255,255,0.08);
    --border-strong: rgba(255,255,255,0.14);
    --text: #EDEDEF;
    --text-secondary: #8E8E96;
    --text-tertiary: #6A6A70;
    --accent: #6C8CFF;
    --accent-dim: rgba(108,140,255,0.14);
    --accent-line: rgba(108,140,255,0.4);
    --gold: #E0B23D;
    --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 12px 32px rgba(0,0,0,0.45);
    --divider: rgba(255,255,255,0.06);
    color-scheme: dark;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{
    background: var(--bg);
    color: var(--text);
    font-family: Peyda, sans-serif;
    font-size: 16px;
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
}}
body.modal-open {{ overflow: hidden; }}
a {{ color: inherit; text-decoration: none; }}
::-webkit-scrollbar {{ width: 0; height: 0; }}
:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 6px; }}
.numeral {{
    font-variant-numeric: tabular-nums;
    direction: ltr;
    unicode-bidi: isolate;
    letter-spacing: 0.01em;
}}
.anchor-marker {{
    display: block;
    position: relative;
    top: -170px;
    visibility: hidden;
}}
.app-header {{
    position: sticky;
    top: 0;
    z-index: 900;
    background: color-mix(in srgb, var(--bg) 88%, transparent);
    backdrop-filter: blur(16px) saturate(160%);
    -webkit-backdrop-filter: blur(16px) saturate(160%);
    border-bottom: 1px solid var(--divider);
}}
.header-inner {{
    max-width: 1180px;
    margin: 0 auto;
    padding: 0.85rem 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.8rem;
}}
.header-top {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1.1rem;
}}
.search-wrap {{
    flex: 1;
    max-width: 480px;
    position: relative;
    display: flex;
    align-items: center;
}}
.search-input {{
    width: 100%;
    height: 38px;
    padding: 0 2.6rem 0 1rem;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text);
    font-family: Peyda, sans-serif;
    font-size: 0.86rem;
    outline: none;
    transition: border-color 0.15s ease;
}}
.search-input::placeholder {{ color: var(--text-tertiary); }}
.search-input:focus {{ border-color: var(--accent-line); }}
.search-icon {{
    position: absolute;
    right: 0.85rem;
    color: var(--text-tertiary);
    display: flex;
    pointer-events: none;
}}
.header-actions {{
    display: flex;
    align-items: center;
    gap: 1.1rem;
    flex: 0 0 auto;
}}
.header-actions-buttons {{
    display: flex;
    gap: 1.1rem;
}}
.summary-pill {{
    display: flex;
    align-items: center;
    gap: 0.45rem;
    height: 38px;
    padding: 0 0.9rem;
    border-radius: 10px;
    border: 1px solid var(--accent-line);
    background: var(--accent-dim);
    color: var(--accent);
    font-family: Peyda, sans-serif;
    font-size: 0.8rem;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
}}
.theme-toggle {{
    width: 38px;
    height: 38px;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    flex: 0 0 auto;
    transition: border-color 0.15s ease, color 0.15s ease;
}}
.theme-toggle:hover {{ border-color: var(--border-strong); color: var(--text); }}
.theme-toggle .ico-sun {{ display: none; }}
:root[data-theme="dark"] .theme-toggle .ico-sun {{ display: flex; }}
:root[data-theme="dark"] .theme-toggle .ico-moon {{ display: none; }}
.live-indicator {{
    display: flex;
    align-items: center;
    gap: 0.45rem;
    color: var(--text-tertiary);
    font-size: 0.74rem;
    white-space: nowrap;
    padding: 0 0.15rem;
}}
.pulse-ring {{ position: relative; width: 7px; height: 7px; flex: 0 0 auto; }}
.pulse-ring::before, .pulse-ring::after {{
    content: "";
    position: absolute;
    inset: 0;
    border-radius: 50%;
    background: #22c55e;
}}
.pulse-ring::before {{ animation: ringExpand 2.4s ease-out infinite; }}
@keyframes ringExpand {{
    0% {{ transform: scale(1); opacity: 0.55; }}
    100% {{ transform: scale(3.2); opacity: 0; }}
}}
.chips-row {{
    display: flex;
    gap: 0.5rem;
    overflow-x: auto;
    padding-bottom: 0.15rem;
    scrollbar-width: none;
}}
.chips-row::-webkit-scrollbar {{ display: none; }}
.chip {{
    flex: 0 0 auto;
    padding: 0.4rem 0.9rem;
    border-radius: 8px;
    background: transparent;
    border: none;
    color: var(--text-secondary);
    font-family: Peyda, sans-serif;
    font-size: 0.82rem;
    font-weight: 700;
    cursor: pointer;
    position: relative;
    transition: color 0.15s ease;
}}
.chip::after {{
    content: "";
    position: absolute;
    bottom: -3px;
    right: 0.9rem;
    left: 0.9rem;
    height: 2px;
    border-radius: 2px;
    background: var(--accent);
    transform: scaleX(0);
    transition: transform 0.2s ease;
}}
.chip:hover {{ color: var(--text); }}
.chip.active {{ color: var(--text); }}
.chip.active::after {{ transform: scaleX(1); }}
.chip.chip-price {{ color: var(--gold); }}
.main-layout {{
    max-width: 1180px;
    margin: 0 auto;
    padding: 1.75rem 1.5rem 4rem;
    display: flex;
    flex-direction: column;
    gap: 2.75rem;
}}
.section-label {{ display: flex; align-items: baseline; justify-content: space-between; }}
.section-label-left {{ display: flex; align-items: center; gap: 0.55rem; }}
.section-dot {{ width: 5px; height: 5px; border-radius: 50%; background: var(--accent); }}
.section-title {{ font-size: 0.98rem; font-weight: 900; letter-spacing: -0.01em; }}
.price-section {{ display: flex; flex-direction: column; gap: 0.9rem; }}
.price-strip {{ display: flex; gap: 0.7rem; overflow-x: auto; scrollbar-width: none; }}
.price-strip::-webkit-scrollbar {{ display: none; }}
.price-card {{
    flex: 0 0 152px;
    padding: 1rem 1.1rem;
    border-radius: 14px;
    background: var(--surface);
    border: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    transition: border-color 0.15s ease, transform 0.15s ease;
}}
.price-card:hover {{ border-color: var(--border-strong); transform: translateY(-1px); }}
.price-card.hidden-by-search {{ display: none; }}
.price-currency {{ font-size: 0.74rem; color: var(--text-secondary); font-weight: 700; }}
.price-value {{ font-size: 1.2rem; font-weight: 900; letter-spacing: -0.01em; }}
.price-time {{ font-size: 0.72rem; color: var(--text-tertiary); direction: rtl; }}
.feed-section {{ display: flex; flex-direction: column; gap: 1rem; }}
.feed-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.1rem; }}
.feed-empty {{
    grid-column: 1 / -1;
    padding: 2rem 1rem;
    color: var(--text-secondary);
    font-size: 0.9rem;
    text-align: center;
    border-radius: 14px;
    border: 1px dashed var(--border-strong);
}}
.news-card {{
    display: flex;
    flex-direction: column;
    border-radius: 16px;
    background: var(--surface);
    border: 1px solid var(--border);
    overflow: hidden;
    cursor: pointer;
    transition: border-color 0.18s ease, transform 0.18s ease, opacity 0.4s ease;
}}
.js .news-card {{ opacity: 0; }}
.js .news-card.in-view {{ opacity: 1; }}
.news-card:hover {{ border-color: var(--border-strong); transform: translateY(-2px); }}
.news-card:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
.news-card.hidden-by-search {{ display: none; }}
.news-card.is-read {{ opacity: 0.6; }}
.news-card.is-read .card-source {{ color: var(--text-tertiary); }}
.card-media {{
    width: 100%;
    aspect-ratio: 16/10;
    background: var(--divider);
    position: relative;
    overflow: hidden;
}}
.card-media-thumb {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
.card-media-thumb-empty, .card-media-empty {{
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-tertiary);
}}
.card-media-badge {{
    position: absolute;
    bottom: 0.55rem;
    left: 0.55rem;
    background: rgba(0,0,0,0.65);
    color: #fff;
    font-size: 0.66rem;
    font-weight: 700;
    padding: 0.14rem 0.5rem;
    border-radius: 999px;
}}
.card-media-kind {{
    position: absolute;
    bottom: 0.55rem;
    right: 0.55rem;
    background: rgba(0,0,0,0.65);
    color: #fff;
    font-size: 0.6rem;
    font-weight: 800;
    letter-spacing: 0.03em;
    padding: 0.14rem 0.5rem;
    border-radius: 999px;
}}
.card-body {{ padding: 1rem 1.1rem 1.1rem; display: flex; flex-direction: column; gap: 0.6rem; flex: 1; }}
.card-meta {{ display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; }}
.card-source {{
    font-size: 0.72rem;
    font-weight: 700;
    color: var(--accent);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.card-time-wrap {{ display: flex; align-items: center; gap: 0.4rem; flex: 0 0 auto; }}
.card-time {{ font-size: 0.72rem; color: var(--text-tertiary); white-space: nowrap; }}
.unread-dot {{ width: 6px; height: 6px; border-radius: 50%; background: var(--accent); flex: 0 0 auto; }}
.is-read .unread-dot {{ display: none; }}
.card-excerpt {{
    font-size: 0.94rem;
    line-height: 1.7;
    color: var(--text);
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
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
.no-results.visible {{ display: flex; }}
.no-results-icon {{ display: flex; align-items: center; justify-content: center; color: var(--accent); opacity: 0.8; margin-bottom: 0.4rem; }}
.no-results-title {{ color: var(--text); font-weight: 800; font-size: 1.05rem; }}
.no-results-subtitle {{ font-size: 0.88rem; }}
.empty-state {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.6rem;
    padding: 4rem 1rem;
    color: var(--text-secondary);
    text-align: center;
}}
.empty-state-icon {{ color: var(--accent); }}
.empty-state-title {{ color: var(--text); font-weight: 800; font-size: 1.15rem; }}
.modal-overlay {{
    position: fixed;
    inset: 0;
    z-index: 5000;
    display: none;
    background: var(--bg);
    overflow-y: auto;
}}
.modal-overlay.active {{ display: block; }}
.modal-close {{
    position: fixed;
    top: 1.1rem;
    left: 1.1rem;
    z-index: 5100;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text-secondary);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: var(--shadow);
    transition: border-color 0.15s ease, color 0.15s ease, transform 0.15s ease;
}}
.modal-close:hover {{ border-color: var(--border-strong); color: var(--text); transform: scale(1.05); }}
.news-modal {{ width: 100%; max-width: 720px; margin: 0 auto; min-height: 100vh; background: var(--bg); }}
.modal-media {{ width: 100%; aspect-ratio: 16/9; background: #000; position: relative; }}
.modal-media.is-empty {{ display: none; }}
.media-player {{ width: 100%; height: 100%; position: relative; background: #000; }}
.media-player:fullscreen, .media-player:-webkit-full-screen {{ display: flex; align-items: center; justify-content: center; }}
.media-player video {{ width: 100%; height: 100%; object-fit: contain; display: block; background: #000; }}
.player-overlay {{
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0,0,0,0.28);
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.15s ease;
    cursor: pointer;
}}
.media-player:hover .player-overlay, .media-player.is-paused .player-overlay {{ opacity: 1; pointer-events: auto; }}
.player-play-btn {{
    width: 62px;
    height: 62px;
    border-radius: 50%;
    background: rgba(255,255,255,0.94);
    color: #101012;
    display: flex;
    align-items: center;
    justify-content: center;
    border: none;
    cursor: pointer;
    transition: transform 0.15s ease;
}}
.player-play-btn:hover {{ transform: scale(1.06); }}
.player-play-btn svg {{ margin-right: -2px; }}
.media-player.is-playing .player-play-btn {{ display: none; }}
.player-controls {{
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    padding: 1.4rem 0.9rem 0.7rem;
    background: linear-gradient(180deg, transparent, rgba(0,0,0,0.75));
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    opacity: 0;
    transition: opacity 0.15s ease;
    direction: ltr;
}}
.media-player:hover .player-controls, .media-player.is-paused .player-controls {{ opacity: 1; }}
.player-progress {{
    -webkit-appearance: none;
    appearance: none;
    width: 100%;
    height: 3px;
    border-radius: 2px;
    background: rgba(255,255,255,0.3);
    cursor: pointer;
    outline: none;
}}
.player-progress::-webkit-slider-thumb {{
    -webkit-appearance: none;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #fff;
    cursor: pointer;
    margin-top: -4.5px;
}}
.player-progress::-moz-range-thumb {{ width: 12px; height: 12px; border-radius: 50%; background: #fff; border: none; cursor: pointer; }}
.player-bottom-row {{ display: flex; align-items: center; gap: 0.7rem; }}
.player-btn {{
    width: 30px;
    height: 30px;
    border-radius: 6px;
    border: none;
    background: transparent;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    flex: 0 0 auto;
}}
.player-btn:hover {{ background: rgba(255,255,255,0.14); }}
.player-time {{ font-size: 0.72rem; color: rgba(255,255,255,0.85); font-variant-numeric: tabular-nums; direction: ltr; white-space: nowrap; }}
.player-spacer {{ flex: 1; }}
.media-gallery {{
    width: 100%;
    height: 100%;
    position: relative;
    background: #000;
    overflow: hidden;
}}
.media-gallery-stage {{
    width: 100%;
    height: 100%;
    position: relative;
    touch-action: pan-y;
    user-select: none;
}}
.media-gallery-media {{
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
}}
.media-gallery-media.is-image {{
    object-fit: contain;
}}
.media-gallery-media.is-video {{
    background: #000;
}}
.media-gallery-control {{
    position: absolute;
    top: 50%;
    width: 42px;
    height: 42px;
    margin-top: -21px;
    border: 1px solid rgba(255,255,255,0.16);
    border-radius: 50%;
    background: rgba(0,0,0,0.52);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    z-index: 4;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: opacity 0.15s ease, transform 0.15s ease, background 0.15s ease;
}}
.media-gallery-control:hover {{
    background: rgba(0,0,0,0.72);
    transform: translateY(-1px) scale(1.04);
}}
.media-gallery-control:disabled {{
    opacity: 0;
    pointer-events: none;
}}
.media-gallery-prev {{
    right: 0.9rem;
}}
.media-gallery-next {{
    left: 0.9rem;
}}
.media-gallery-counter {{
    position: absolute;
    top: 0.9rem;
    left: 50%;
    transform: translateX(-50%);
    z-index: 4;
    min-width: 54px;
    padding: 0.28rem 0.65rem;
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 999px;
    background: rgba(0,0,0,0.52);
    color: #fff;
    font-size: 0.7rem;
    font-weight: 700;
    text-align: center;
    direction: ltr;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
}}
.media-gallery-progress {{
    position: absolute;
    right: 0.9rem;
    left: 0.9rem;
    bottom: 0.85rem;
    height: 3px;
    display: flex;
    gap: 3px;
    z-index: 4;
    pointer-events: none;
}}
.media-gallery-progress-item {{
    flex: 1;
    min-width: 0;
    border-radius: 999px;
    background: rgba(255,255,255,0.28);
    transition: background 0.15s ease;
}}
.media-gallery-progress-item.active {{
    background: rgba(255,255,255,0.92);
}}
.media-gallery-empty {{
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
}}
.media-gallery-fullscreen {{
    position: absolute;
    bottom: 1.25rem;
    left: 0.9rem;
    width: 34px;
    height: 34px;
    border-radius: 8px;
    border: none;
    background: rgba(0,0,0,0.5);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    z-index: 5;
    transition: background 0.15s ease, opacity 0.15s ease;
}}
.media-gallery-fullscreen:hover {{
    background: rgba(0,0,0,0.72);
}}
@media (hover: hover) {{
    .media-gallery-fullscreen {{
        opacity: 0;
    }}
    .media-gallery:hover .media-gallery-fullscreen {{
        opacity: 1;
    }}
}}
@media (max-width: 640px) {{
    .media-gallery-control {{
        width: 36px;
        height: 36px;
        margin-top: -18px;
    }}
    .media-gallery-prev {{
        right: 0.65rem;
    }}
    .media-gallery-next {{
        left: 0.65rem;
    }}
    .media-gallery-counter {{
        top: 0.65rem;
    }}
    .media-gallery-progress {{
        right: 0.65rem;
        left: 0.65rem;
        bottom: 0.65rem;
    }}
}}
.modal-inner {{ padding: 1.7rem 1.7rem 3rem; max-width: 720px; margin: 0 auto; }}
.modal-source-row {{ display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.7rem; }}
.modal-source {{ font-size: 0.78rem; font-weight: 700; color: var(--accent); }}
.modal-date {{ font-size: 0.78rem; color: var(--text-tertiary); }}
.modal-title {{ font-size: 1.5rem; font-weight: 900; line-height: 1.6; letter-spacing: -0.01em; margin-bottom: 1.2rem; }}
.modal-content {{ font-size: 1.04rem; line-height: 2; color: var(--text); text-align: justify; }}
.modal-related {{ display: none; margin-top: 1.8rem; padding-top: 1.5rem; border-top: 1px solid var(--divider); }}
.modal-related-title {{ font-size: 0.86rem; font-weight: 700; color: var(--text-secondary); margin-bottom: 0.8rem; }}
.related-item {{ display: flex; gap: 0.7rem; padding: 0.65rem 0; cursor: pointer; border-radius: 8px; }}
.related-item + .related-item {{ border-top: 1px solid var(--divider); }}
.related-thumb {{ width: 52px; height: 52px; border-radius: 10px; object-fit: cover; background: var(--divider); flex: 0 0 auto; }}
.related-thumb-placeholder {{
    width: 52px;
    height: 52px;
    border-radius: 10px;
    flex: 0 0 auto;
    background: var(--accent-dim);
    color: var(--accent);
    display: flex;
    align-items: center;
    justify-content: center;
}}
.related-text {{ min-width: 0; display: flex; flex-direction: column; gap: 0.2rem; justify-content: center; }}
.related-source {{ font-size: 0.7rem; color: var(--accent); font-weight: 700; }}
.related-title {{ font-size: 0.86rem; line-height: 1.6; color: var(--text); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
.ai-summary-header {{ display: flex; flex-direction: column; gap: 0.55rem; margin-bottom: 1.6rem; }}
.ai-summary-badge {{ display: flex; align-items: center; gap: 0.5rem; color: var(--text); font-size: 1.15rem; font-weight: 900; }}
.ai-summary-badge svg {{ color: var(--accent); flex: 0 0 auto; }}
.ai-summary-meta {{ display: flex; align-items: center; flex-wrap: wrap; gap: 0.45rem; }}
.ai-summary-tag {{
    color: var(--accent);
    font-size: 0.72rem;
    font-weight: 700;
    background: var(--accent-dim);
    border: 1px solid var(--accent-line);
    padding: 0.3rem 0.75rem;
    border-radius: 999px;
    white-space: nowrap;
}}
.ai-summary-time {{ color: var(--text-tertiary); font-size: 0.72rem; font-weight: 600; white-space: nowrap; }}
.ai-summary-content {{ text-align: justify; color: var(--text); font-size: 1.04rem; line-height: 2.1; }}
.ai-summary-content > *:first-child {{ margin-top: 0; }}
.ai-summary-content > *:last-child {{ margin-bottom: 0; }}
.ai-summary-content p {{ margin: 0 0 1rem 0; }}
.ai-summary-content h1, .ai-summary-content h2, .ai-summary-content h3,
.ai-summary-content h4, .ai-summary-content h5, .ai-summary-content h6 {{
    color: var(--text);
    font-weight: 800;
    line-height: 1.8;
    margin: 1.4rem 0 0.7rem 0;
}}
.ai-summary-content strong {{ color: var(--text); font-weight: 800; }}
.ai-summary-content a {{ color: var(--accent); text-decoration: underline; text-underline-offset: 3px; }}
.ai-summary-content code {{
    background: var(--divider);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.1rem 0.4rem;
    font-size: 0.88em;
    direction: ltr;
    display: inline-block;
}}
.ai-summary-content ul, .ai-summary-content ol {{
    margin: 0 0 1rem 0;
    padding-right: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}}
.ai-summary-content blockquote {{
    margin: 0 0 1rem 0;
    padding: 0.2rem 1.1rem 0.2rem 0;
    border-right: 3px solid var(--accent-line);
    color: var(--text-secondary);
}}
.ai-summary-content hr {{ border: none; height: 1px; background: var(--border); margin: 1.6rem 0; }}
.app-footer {{ border-top: 1px solid var(--divider); margin-top: 1rem; }}
.footer-inner {{ max-width: 1180px; margin: 0 auto; padding: 2rem 1.5rem 1.6rem; display: flex; flex-direction: column; gap: 1.4rem; }}
.footer-top {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 2rem; flex-wrap: wrap; }}
.footer-sources {{ display: flex; flex-direction: column; gap: 0.7rem; }}
.footer-label {{ font-size: 0.74rem; font-weight: 700; color: var(--text-tertiary); }}
.footer-links {{ display: flex; flex-wrap: wrap; gap: 0.5rem 1rem; }}
.footer-links a {{ font-size: 0.84rem; color: var(--text-secondary); transition: color 0.15s ease; }}
.footer-links a:hover {{ color: var(--accent); }}
.footer-actions {{ display: flex; flex-direction: column; align-items: flex-start; gap: 0.7rem; }}
.back-to-top {{
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-family: Peyda, sans-serif;
    font-size: 0.82rem;
    font-weight: 700;
    color: var(--text-secondary);
    background: transparent;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.45rem 0.8rem;
    cursor: pointer;
    transition: border-color 0.15s ease, color 0.15s ease;
}}
.back-to-top:hover {{ border-color: var(--border-strong); color: var(--text); }}
.footer-bottom {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    padding-top: 1.2rem;
    border-top: 1px solid var(--divider);
    font-size: 0.78rem;
    color: var(--text-tertiary);
}}
@media (prefers-reduced-motion: reduce) {{
    html {{ scroll-behavior: auto; }}
    .js .news-card {{ opacity: 1; }}
    .news-card, .pulse-ring::before, .price-card, .modal-close {{ transition: none; animation: none; }}
}}
@media (max-width: 980px) {{
    .feed-grid {{ grid-template-columns: repeat(2, 1fr); }}
}}
@media (max-width: 640px) {{
    .feed-grid {{ grid-template-columns: 1fr; }}
    .header-top {{ flex-wrap: wrap; }}
    .header-actions {{ display: flex; align-items: center; flex: 1 1 100%; justify-content: space-between; }}
    .search-wrap {{ order: 3; max-width: none; flex: 1 1 100%; }}
}}
</style>
</head>
<body>
<header class="app-header">
    <div class="header-inner">
        <div class="header-top">
            <div class="search-wrap">
                <input type="text" class="search-input" id="searchInput" placeholder="جستجو در اخبار..." oninput="filterNews(this.value)" aria-label="جستجو در اخبار">
                <span class="search-icon">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"></circle><path d="m21 21-4.3-4.3"></path></svg>
                </span>
            </div>
            <div class="header-actions">
                <div class="header-actions-buttons">
                    <button class="theme-toggle" type="button" onclick="toggleTheme()" aria-label="تغییر پوسته">
                        <span class="ico-moon"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg></span>
                        <span class="ico-sun"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"></path></svg></span>
                    </button>
                    {summary_trigger}
                </div>
                <div class="live-indicator">
                    <span class="pulse-ring"></span>
                    <span id="latest-update" data-time="{latest_update}">در حال بروزرسانی...</span>
                </div>
            </div>
        </div>
        <div class="chips-row">
            {chips}
        </div>
    </div>
</header>
<main class="main-layout">
    <div class="no-results" id="noResults">
        <div class="no-results-icon">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"></circle><path d="m21 21-4.3-4.3"></path></svg>
        </div>
        <div class="no-results-title">نتیجه‌ای پیدا نشد</div>
        <div class="no-results-subtitle">عبارت دیگری را امتحان کنید</div>
    </div>
    {price_cards}
    {main_content}
</main>
<footer class="app-footer">
    <div class="footer-inner">
        <div class="footer-top">
            <div class="footer-sources">
                <span class="footer-label">منابع خبری</span>
                <div class="footer-links" id="footerLinks"></div>
            </div>
            <div class="footer-actions">
                <span class="footer-label">دسترسی سریع</span>
                <button class="back-to-top" type="button" onclick="window.scrollTo({{top:0,behavior:'smooth'}})">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>
                    بازگشت به بالا
                </button>
            </div>
        </div>
        <div class="footer-bottom">
            <span id="footerUpdateTime"></span>
            <span>تقدیم به همه جاویدنامان ایران - شِف</span>
        </div>
    </div>
</footer>
<div class="modal-overlay" id="newsModal">
    <button class="modal-close" type="button" onclick="closeNewsModal()" aria-label="بستن">
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18M6 6l12 12"></path></svg>
    </button>
    <div class="news-modal">
        <div class="modal-media is-empty" id="modalMedia">
            <div class="media-player" id="mediaPlayer">
                <video id="modalVideo" playsinline preload="metadata"></video>
                <div class="player-overlay" onclick="togglePlay()">
                    <button class="player-play-btn" aria-label="پخش" tabindex="-1">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"></path></svg>
                    </button>
                </div>
                <div class="player-controls" onclick="event.stopPropagation()">
                    <input type="range" class="player-progress" id="playerProgress" value="0" min="0" max="100" step="0.1">
                    <div class="player-bottom-row">
                        <button class="player-btn" type="button" onclick="togglePlay()" aria-label="پخش/توقف" id="playPauseBtn">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"></path></svg>
                        </button>
                        <span class="player-time" id="playerTime">0:00 / 0:00</span>
                        <span class="player-spacer"></span>
                        <button class="player-btn" type="button" onclick="toggleMute()" aria-label="بی‌صدا" id="muteBtn">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5 6 9H2v6h4l5 4V5z"></path><path d="M15.5 8.5a5 5 0 0 1 0 7"></path></svg>
                        </button>
                        <button class="player-btn" type="button" onclick="toggleFullscreen('mediaPlayer')" aria-label="تمام‌صفحه">{fullscreen_icon_svg}</button>
                    </div>
                </div>
            </div>
            <div class="media-gallery" id="mediaGallery" style="display:none">
                <div class="media-gallery-stage" id="mediaGalleryStage"></div>
                <button class="media-gallery-control media-gallery-prev" id="mediaGalleryPrev" type="button" aria-label="رسانه قبلی">
                    
                    
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"></path></svg>
                    
                </button>
                <button class="media-gallery-control media-gallery-next" id="mediaGalleryNext" type="button" aria-label="رسانه بعدی">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"></path></svg>
                </button>
                <span class="media-gallery-counter" id="mediaGalleryCounter"></span>
                <div class="media-gallery-progress" id="mediaGalleryProgress"></div>
                <button class="media-gallery-fullscreen" type="button" onclick="toggleFullscreen('mediaGallery')" aria-label="تمام‌صفحه">{fullscreen_icon_svg}</button>
            </div>
        </div>
        <div class="modal-inner">
            <div class="modal-source-row">
                <span class="modal-source" id="modalSource"></span>
                <span class="modal-date numeral" id="modalDate"></span>
            </div>
            <h2 class="modal-title" id="modalTitle"></h2>
            <div class="modal-content" id="modalContent"></div>
            <div class="modal-related" id="modalRelated">
                <div class="modal-related-title">اخبار مرتبط</div>
                <div id="modalRelatedList"></div>
            </div>
        </div>
    </div>
</div>
{summary_modal}
<script>
(function() {{
    var docEl = document.documentElement;

    function applySystemTheme() {{
        var stored = null;
        try {{ stored = localStorage.getItem("dayereh_theme"); }} catch (e) {{}}
        if (stored === "light" || stored === "dark") {{
            docEl.setAttribute("data-theme", stored);
            return;
        }}
        var prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
        docEl.setAttribute("data-theme", prefersDark ? "dark" : "light");
    }}

    applySystemTheme();

    if (window.matchMedia) {{
        window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", applySystemTheme);
    }}

    window.toggleTheme = function() {{
        var next = docEl.getAttribute("data-theme") === "dark" ? "light" : "dark";
        docEl.setAttribute("data-theme", next);
        try {{ localStorage.setItem("dayereh_theme", next); }} catch (e) {{}}
    }};
}})();

function timeAgo(dateString) {{
    var parts = dateString.split(/[- :]/);
    var date = new Date(parts[0], parts[1] - 1, parts[2], parts[3], parts[4], parts[5]);
    var seconds = Math.floor((Date.now() - date) / 1000);

    if (seconds < 60) return "چند لحظه پیش";
    var minutes = Math.floor(seconds / 60);
    if (minutes < 60) return minutes + " دقیقه پیش";
    var hours = Math.floor(minutes / 60);
    if (hours < 24) return hours + " ساعت پیش";
    var days = Math.floor(hours / 24);
    if (days < 30) return days + " روز پیش";
    var months = Math.floor(days / 30);
    if (months < 12) return months + " ماه پیش";
    return Math.floor(months / 12) + " سال پیش";
}}

var liveTimeNodes = document.querySelectorAll("[data-live-time]");
var updateEl = document.getElementById("latest-update");
var footerUpdateEl = document.getElementById("footerUpdateTime");
var updateTimeValue = updateEl.dataset.time;

function refreshAllTimes() {{
    var relative = timeAgo(updateTimeValue);
    updateEl.textContent = relative;
    footerUpdateEl.textContent = "آخرین بروزرسانی: " + relative;

    for (var i = 0; i < liveTimeNodes.length; i++) {{
        var value = liveTimeNodes[i].dataset.liveTime;
        if (value) liveTimeNodes[i].textContent = timeAgo(value);
    }}
}}

refreshAllTimes();
setInterval(refreshAllTimes, 60000);

var READ_KEY = "dayereh_read_articles";

function getReadSet() {{
    try {{
        return new Set(JSON.parse(localStorage.getItem(READ_KEY)) || []);
    }} catch (e) {{
        return new Set();
    }}
}}

function markRead(anchor) {{
    var readSet = getReadSet();
    readSet.add(anchor);
    try {{ localStorage.setItem(READ_KEY, JSON.stringify(Array.from(readSet))); }} catch (e) {{}}
}}

(function applyReadState() {{
    var readSet = getReadSet();
    document.querySelectorAll(".news-card[data-anchor]").forEach(function(card) {{
        if (readSet.has(card.dataset.anchor)) card.classList.add("is-read");
    }});
}})();

var modal = document.getElementById("newsModal");
var modalMedia = document.getElementById("modalMedia");
var mediaPlayerBlock = document.getElementById("mediaPlayer");
var mediaGallery = document.getElementById("mediaGallery");
var mediaGalleryStage = document.getElementById("mediaGalleryStage");
var mediaGalleryPrev = document.getElementById("mediaGalleryPrev");
var mediaGalleryNext = document.getElementById("mediaGalleryNext");
var mediaGalleryCounter = document.getElementById("mediaGalleryCounter");
var mediaGalleryProgress = document.getElementById("mediaGalleryProgress");
var video = document.getElementById("modalVideo");
var playerEl = document.getElementById("mediaPlayer");
var progressEl = document.getElementById("playerProgress");
var timeEl = document.getElementById("playerTime");
var playPauseBtn = document.getElementById("playPauseBtn");
var muteBtn = document.getElementById("muteBtn");

var mediaState = {{
    items: [],
    index: 0,
    touchStartX: 0,
    touchStartY: 0,
    touchActive: false
}};

var ICON_PLAY = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"></path></svg>';
var ICON_PAUSE = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M7 5h4v14H7zM13 5h4v14h-4z"></path></svg>';
var ICON_MUTE = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5 6 9H2v6h4l5 4V5z"></path><line x1="23" y1="9" x2="17" y2="15"></line><line x1="17" y1="9" x2="23" y2="15"></line></svg>';
var ICON_SOUND = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5 6 9H2v6h4l5 4V5z"></path><path d="M15.5 8.5a5 5 0 0 1 0 7"></path></svg>';

function formatDuration(sec) {{
    if (!isFinite(sec)) return "0:00";
    var m = Math.floor(sec / 60);
    var s = Math.floor(sec % 60);
    return m + ":" + (s < 10 ? "0" : "") + s;
}}

function togglePlay() {{
    if (!video.src) return;
    if (video.paused) video.play(); else video.pause();
}}

function toggleMute() {{
    video.muted = !video.muted;
    muteBtn.innerHTML = video.muted ? ICON_MUTE : ICON_SOUND;
}}

function toggleFullscreen(elementId) {{
    var el = document.getElementById(elementId);
    var isFullscreen = document.fullscreenElement || document.webkitFullscreenElement;

    if (!isFullscreen) {{
        if (el.requestFullscreen) el.requestFullscreen();
        else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen();
    }} else {{
        if (document.exitFullscreen) document.exitFullscreen();
        else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
    }}
}}

video.addEventListener("play", function() {{
    playerEl.classList.add("is-playing");
    playerEl.classList.remove("is-paused");
    playPauseBtn.innerHTML = ICON_PAUSE;
}});
video.addEventListener("pause", function() {{
    playerEl.classList.remove("is-playing");
    playerEl.classList.add("is-paused");
    playPauseBtn.innerHTML = ICON_PLAY;
}});
video.addEventListener("timeupdate", function() {{
    if (video.duration) progressEl.value = (video.currentTime / video.duration) * 100;
    timeEl.textContent = formatDuration(video.currentTime) + " / " + formatDuration(video.duration);
}});
video.addEventListener("loadedmetadata", function() {{
    timeEl.textContent = "0:00 / " + formatDuration(video.duration);
}});
progressEl.addEventListener("input", function() {{
    if (video.duration) video.currentTime = (progressEl.value / 100) * video.duration;
}});

function resetVideo() {{
    video.pause();
    video.removeAttribute("src");
    video.removeAttribute("poster");
    video.load();
}}

function createGalleryMedia(item) {{
    if (item.type === "video") {{
        var media = document.createElement("video");
        media.className = "media-gallery-media is-video";
        media.src = item.url;
        media.playsInline = true;
        media.controls = true;
        media.preload = "metadata";
        if (item.poster) media.poster = item.poster;
        return media;
    }}

    var image = document.createElement("img");
    image.className = "media-gallery-media is-image";
    image.src = item.url;
    image.alt = "";
    image.draggable = false;
    image.loading = "eager";
    return image;
}}

function preloadGalleryMedia(index) {{
    var item = mediaState.items[index];
    if (!item || item.type === "video") return;

    var image = new Image();
    image.src = item.url;
}}

function updateGalleryControls() {{
    var total = mediaState.items.length;
    var hasMultiple = total > 1;

    mediaGalleryPrev.hidden = !hasMultiple;
    mediaGalleryNext.hidden = !hasMultiple;
    mediaGalleryCounter.hidden = !hasMultiple;
    mediaGalleryProgress.hidden = !hasMultiple;

    if (!hasMultiple) return;

    mediaGalleryPrev.disabled = mediaState.index === 0;
    mediaGalleryNext.disabled = mediaState.index === total - 1;
    mediaGalleryCounter.textContent = (mediaState.index + 1) + " / " + total;

    mediaGalleryProgress.querySelectorAll(".media-gallery-progress-item").forEach(function(item, index) {{
        item.classList.toggle("active", index === mediaState.index);
    }});
}}

function renderGallery() {{
    var item = mediaState.items[mediaState.index];
    if (!item) return;

    var media = createGalleryMedia(item);
    mediaGalleryStage.replaceChildren(media);
    updateGalleryControls();

    preloadGalleryMedia(mediaState.index - 1);
    preloadGalleryMedia(mediaState.index + 1);
}}

function showGalleryItem(index) {{
    var total = mediaState.items.length;
    if (!total || index < 0 || index >= total || index === mediaState.index) return;

    var currentMedia = mediaGalleryStage.querySelector("video");
    if (currentMedia) currentMedia.pause();

    mediaState.index = index;
    renderGallery();
}}

function nextGalleryItem() {{
    showGalleryItem(mediaState.index + 1);
}}

function previousGalleryItem() {{
    showGalleryItem(mediaState.index - 1);
}}

function handleGalleryTouchStart(event) {{
    if (event.touches.length !== 1) return;
    mediaState.touchStartX = event.touches[0].clientX;
    mediaState.touchStartY = event.touches[0].clientY;
    mediaState.touchActive = true;
}}

function handleGalleryTouchEnd(event) {{
    if (!mediaState.touchActive || !event.changedTouches.length) return;

    var touch = event.changedTouches[0];
    var deltaX = touch.clientX - mediaState.touchStartX;
    var deltaY = touch.clientY - mediaState.touchStartY;
    mediaState.touchActive = false;

    if (Math.abs(deltaX) < 45 || Math.abs(deltaX) < Math.abs(deltaY)) return;

    if (deltaX < 0) nextGalleryItem();
    else previousGalleryItem();
}}

function renderGalleryProgress() {{
    mediaGalleryProgress.replaceChildren();

    mediaState.items.forEach(function(_, index) {{
        var item = document.createElement("span");
        item.className = "media-gallery-progress-item";
        item.classList.toggle("active", index === mediaState.index);
        mediaGalleryProgress.appendChild(item);
    }});
}}

function renderModalMedia(mediaList) {{
    mediaState.items = Array.isArray(mediaList) ? mediaList.filter(function(item) {{
        return item && item.url;
    }}) : [];
    mediaState.index = 0;

    if (!mediaState.items.length) {{
        modalMedia.classList.add("is-empty");
        mediaPlayerBlock.style.display = "none";
        mediaGallery.style.display = "none";
        resetVideo();
        return;
    }}

    modalMedia.classList.remove("is-empty");

    var first = mediaState.items[0];
    var isSingleVideo = mediaState.items.length === 1 && first.type === "video";

    if (isSingleVideo) {{
        mediaGallery.style.display = "none";
        mediaPlayerBlock.style.display = "";
        video.src = first.url;
        if (first.poster) video.poster = first.poster;
        video.load();
        return;
    }}

    mediaPlayerBlock.style.display = "none";
    resetVideo();
    mediaGallery.style.display = "";
    renderGalleryProgress();
    renderGallery();
}}

mediaGalleryPrev.addEventListener("click", previousGalleryItem);
mediaGalleryNext.addEventListener("click", nextGalleryItem);
mediaGalleryStage.addEventListener("touchstart", handleGalleryTouchStart, {{ passive: true }});
mediaGalleryStage.addEventListener("touchend", handleGalleryTouchEnd, {{ passive: true }});

mediaGalleryStage.addEventListener("keydown", function(event) {{
    if (event.key === "ArrowLeft") {{
        event.preventDefault();
        nextGalleryItem();
    }}
    if (event.key === "ArrowRight") {{
        event.preventDefault();
        previousGalleryItem();
    }}
}});

document.addEventListener("keydown", function(event) {{
    if (!modal.classList.contains("active") || mediaState.items.length < 2) return;

    if (event.key === "ArrowLeft") {{
        event.preventDefault();
        nextGalleryItem();
    }}

    if (event.key === "ArrowRight") {{
        event.preventDefault();
        previousGalleryItem();
    }}
}});
function openRelated(anchor) {{
    var target = document.querySelector('[data-anchor="' + anchor + '"]');
    if (target) {{
        target.click();
        document.querySelector(".news-modal").scrollTo({{ top: 0, behavior: "smooth" }});
    }}
}}

function renderRelated(related) {{
    var section = document.getElementById("modalRelated");
    var list = document.getElementById("modalRelatedList");
    list.innerHTML = "";

    if (!related || related.length === 0) {{
        section.style.display = "none";
        return;
    }}

    section.style.display = "block";

    related.forEach(function(item) {{
        var el = document.createElement("div");
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
            var thumb = document.createElement("img");
            thumb.className = "related-thumb";
            thumb.src = item.thumbnail;
            thumb.alt = "";
            thumb.loading = "lazy";
            el.appendChild(thumb);
        }} else {{
            var placeholder = document.createElement("div");
            placeholder.className = "related-thumb-placeholder";
            placeholder.innerHTML = '{related_placeholder_svg}';
            el.appendChild(placeholder);
        }}

        var textWrap = document.createElement("div");
        textWrap.className = "related-text";

        var sourceEl = document.createElement("div");
        sourceEl.className = "related-source";
        sourceEl.textContent = item.source || "";

        var titleEl = document.createElement("div");
        titleEl.className = "related-title";
        titleEl.textContent = item.title || "";

        textWrap.appendChild(sourceEl);
        textWrap.appendChild(titleEl);
        el.appendChild(textWrap);
        list.appendChild(el);
    }});
}}

function openNewsModal(lang, title, content, date, link, source, media, related) {{
    document.body.classList.add("modal-open");
    modal.classList.add("active");
    modal.scrollTop = 0;

    var titleEl = document.getElementById("modalTitle");
    var contentEl = document.getElementById("modalContent");
    var linkLabel = lang === "fa" ? "لینک فید" : "Feed Link";
    var direction = lang === "fa" ? "rtl" : "ltr";

    contentEl.innerHTML = content + "<br><br><a href='" + link + "' style='text-decoration:underline;color:var(--accent)'>" + linkLabel + "</a>";
    titleEl.style.direction = direction;
    contentEl.style.direction = direction;
    titleEl.style.textAlign = lang === "fa" ? "right" : "left";

    document.getElementById("modalSource").textContent = source;

    var dateEl = document.getElementById("modalDate");
    dateEl.dataset.liveTime = date;
    dateEl.textContent = date ? timeAgo(date) : "";
    titleEl.textContent = title;

    renderModalMedia(media);
    renderRelated(related);

    document.querySelector(".modal-close").focus();
}}

function closeNewsModal() {{
    resetVideo();

    var galleryVideo = mediaGalleryStage.querySelector("video");
    if (galleryVideo) galleryVideo.pause();

    if (document.fullscreenElement || document.webkitFullscreenElement) {{
        if (document.exitFullscreen) document.exitFullscreen();
        else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
    }}

    mediaState.items = [];
    mediaState.index = 0;
    mediaGalleryStage.replaceChildren();

    document.body.classList.remove("modal-open");
    modal.classList.remove("active");
}}

var summaryModal = document.getElementById("aiSummaryModal");

function openSummaryModal() {{
    if (!summaryModal) return;
    document.body.classList.add("modal-open");
    summaryModal.classList.add("active");
    summaryModal.scrollTop = 0;
    var closeBtn = summaryModal.querySelector(".modal-close");
    if (closeBtn) closeBtn.focus();
}}

function closeSummaryModal() {{
    if (!summaryModal) return;
    document.body.classList.remove("modal-open");
    summaryModal.classList.remove("active");
}}

document.addEventListener("keydown", function(event) {{
    if (event.key === "Escape") {{
        closeNewsModal();
        closeSummaryModal();
    }}
}});

function scrollCarousel(sectionId, direction) {{
    var section = document.getElementById(sectionId);
    if (!section) return;
    section.querySelector(".feed-grid, .price-strip").scrollBy({{ left: direction * 340, behavior: "smooth" }});
}}

var chipMap = new Map();
document.querySelectorAll(".chip[data-chip-target]").forEach(function(chip) {{
    chipMap.set(chip.dataset.chipTarget, chip);
}});

function setActiveChip(sectionId) {{
    chipMap.forEach(function(chip) {{ chip.classList.remove("active"); }});
    var chip = chipMap.get(sectionId);
    if (chip) {{
        chip.classList.add("active");
        chip.scrollIntoView({{ behavior: "smooth", inline: "center", block: "nearest" }});
    }}
}}

function jumpToSection(sectionId) {{
    var section = document.getElementById(sectionId);
    if (!section) return;

    var offset = window.innerWidth <= 640 ? 190 : 130;
    var position = section.getBoundingClientRect().top + window.scrollY - offset;

    window.scrollTo({{
        top: position,
        behavior: "smooth"
    }});

    setActiveChip(sectionId);
}}

if (chipMap.size > 0 && "IntersectionObserver" in window) {{
    var spyObserver = new IntersectionObserver(function(entries) {{
        var visible = entries.filter(function(entry) {{ return entry.isIntersecting; }});
        if (visible.length > 0) {{
            visible.sort(function(a, b) {{ return b.intersectionRatio - a.intersectionRatio; }});
            setActiveChip(visible[0].target.id);
        }}
    }}, {{ rootMargin: "-15% 0px -70% 0px", threshold: [0, 0.25, 0.5, 0.75, 1] }});

    document.querySelectorAll("[data-source-section]").forEach(function(section) {{
        spyObserver.observe(section);
    }});
}}

var footerLinks = document.getElementById("footerLinks");
document.querySelectorAll(".chip:not(.chip-price)").forEach(function(chip) {{
    var a = document.createElement("a");
    a.href = "#" + chip.dataset.chipTarget;
    a.textContent = chip.textContent;
    a.onclick = function(e) {{ e.preventDefault(); jumpToSection(chip.dataset.chipTarget); }};
    footerLinks.appendChild(a);
}});

function normalize(text) {{ return (text || "").toLowerCase().trim(); }}

function filterNews(query) {{
    var q = normalize(query);
    var sections = document.querySelectorAll("[data-source-section]");
    var anyVisible = false;

    sections.forEach(function(section) {{
        var cards = section.querySelectorAll(".news-card, .price-card");
        var sectionHasMatch = q === "";

        cards.forEach(function(card) {{
            var matches = q === "" || normalize(card.dataset.search).indexOf(q) !== -1;
            card.classList.toggle("hidden-by-search", !matches);
            if (matches) sectionHasMatch = true;
        }});

        section.style.display = sectionHasMatch ? "" : "none";
        if (sectionHasMatch) anyVisible = true;
    }});

    document.getElementById("noResults").classList.toggle("visible", sections.length > 0 && !anyVisible);
}}

if ("IntersectionObserver" in window) {{
    var revealObserver = new IntersectionObserver(function(entries) {{
        entries.forEach(function(entry) {{
            if (entry.isIntersecting) {{
                entry.target.classList.add("in-view");
                revealObserver.unobserve(entry.target);
            }}
        }});
    }}, {{ threshold: 0.12 }});

    document.querySelectorAll(".news-card").forEach(function(card) {{ revealObserver.observe(card); }});
}} else {{
    document.querySelectorAll(".news-card").forEach(function(card) {{ card.classList.add("in-view"); }});
}}
</script>
</body>
</html>
"""