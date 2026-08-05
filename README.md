<div align="center">

# ⟡ دایره <br><sub>Dayereh</sub>

**A Persian-language news aggregator that costs nothing to run.**

*No server. No database. No hosting bill — just a static site rebuilt by a cron job.*

<br>

[![Build](https://img.shields.io/github/actions/workflow/status/ch3fferson/dayereh/deploy.yml?branch=main&label=build&style=for-the-badge&color=3b5bff)](https://github.com/ch3fferson/dayereh/actions)
[![License](https://img.shields.io/badge/license-MIT-7dd8ff?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-3b5bff?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Made in Iran](https://img.shields.io/badge/made%20with-%E2%9D%A4%EF%B8%8F%20for%20Iran-7dd8ff?style=for-the-badge)](#)

<br>

<a href="#-what-is-dayereh">Overview</a> ·
<a href="#-features">Features</a> ·
<a href="#-how-it-works">How it works</a> ·
<a href="#-tech-stack">Stack</a> ·
<a href="#-quickstart">Quickstart</a> ·
<a href="#-deployment">Deployment</a>

</div>

<br>

---

## ◌ What is Dayereh?

**دایره** به معنای *"دایره"* یا *"چرخه"* است — تجمیع، پالایش و خلاصه‌سازی هوشمند اخبار فارسی، بدون هیچ زیرساخت سرور.

Dayereh pulls news from Telegram channels, RSS feeds, and financial market sources, cleans and structures it, and renders it into a single fast, RTL-native static site. A GitHub Actions cron job does the rebuilding — the entire output is static HTML/XML/JSON, committed straight back to the repo. No backend, no database, no cost.

<br>

## ✦ Features

<table>
<tr>
<td width="50%" valign="top">

**📡 Multi-source aggregation**
Telegram public channels · RSS outlets · TGJU · Live Rates

**🧠 AI daily bulletin**
Gemini-generated geopolitical/economic summary with a persistent rolling memory — each bulletin builds on the last instead of starting cold

**🛡️ Resilient scraping**
Exponential backoff, pooled connections sized for worst-case concurrency, Google News proxy fallback for bot-protected domains

</td>
<td width="50%" valign="top">

**🎞️ Full media pipeline**
Thread-safe download cache, gallery/album support, automatic image & video compression, video thumbnail extraction

**🎨 Modern static frontend**
dark theme · fully RTL

**⚡ Zero-cost deploy**
Static assets only — served straight from GitHub, rebuilt on a cron schedule

</td>
</tr>
</table>

<br>

## ⟳ How it works

```
sources.json
     │
     ▼
  Fetcher  ──►  Parsers  ──►  FeedItem  ──►  Builders  ──►  index.html
(requests/       (Telegram,    (dataclass)    (XML / JSON /
 Selenium)        RSS, TGJU,                    HTML)
                  LiveRates)
                                  │
                                  ▼
                         TextCompressor ──► Gemini ──► news-summary.json
                                                   │
                                                   ▼
                                          memory.md (rolling context)
```

| Step | What happens |
|---|---|
| **1. Fetch** | Sources pulled in parallel via `ThreadPoolExecutor` |
| **2. Parse** | Per-source parser normalizes content into `FeedItem`s |
| **3. Media** | Thread-safe cache downloads + compresses images/video via ffmpeg/Pillow |
| **4. Build** | Per-source XML (MRSS) and a combined JSON price feed |
| **5. Summarize** | Feed text is TF-IDF compressed, then sent to Gemini with a fixed analyst persona + rolling memory |
| **6. Render** | Static `index.html` with related-article clustering and read-state tracking |
| **7. Deploy** | GitHub Actions commits output back to `main` on a cron schedule |

<br>

## ⚙ Tech stack

<div align="center">

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-lxml-3b5bff?style=for-the-badge)
![Selenium](https://img.shields.io/badge/Selenium-43B02A?style=for-the-badge&logo=selenium&logoColor=white)
![FFmpeg](https://img.shields.io/badge/FFmpeg-007808?style=for-the-badge&logo=ffmpeg&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini_API-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)

</div>

<br>

## 🗂 Project structure

<br>

```
.
├── main.py                      # pipeline entrypoint
├── config/
│   └── sources.json             # telegram / rss / tgju / live-rates definitions
├── core/
│   ├── parsers/
│   │   ├── telegram.py          # public channel scraper (posts, albums, polls, video)
│   │   ├── rss.py               # RSS/Atom item parser
│   │   ├── website.py           # generic CSS-selector scraper
│   │   ├── tgju.py              # currency/gold/coin market data
│   │   ├── live_rates.py        # FX/crypto rate feed
│   │   └── tgstat.py            # TGStat channel stats
│   ├── net/
│   │   ├── fetcher.py           # requests + Selenium fetch layer
│   │   └── media_downloader.py  # retrying media downloader
│   ├── converters/
│   │   ├── media_type.py
│   │   ├── media_compressor.py  # ffmpeg/Pillow compression
│   │   └── markdown_to_html.py
│   ├── builders/
│   │   ├── xml_builder.py       # per-source MRSS output
│   │   ├── json_builder.py      # price feed JSON
│   │   └── html_builder.py      # static site renderer
│   ├── ai/
│   │   ├── gemini.py            # Gemini API client
│   │   ├── text_compressor.py   # TF-IDF summarization pre-pass
│   │   ├── soul.md              # analyst persona / system prompt
│   │   └── memory.md            # rolling summarization memory
│   ├── models/
│   │   └── feed_item.py
│   └── utils/
│       ├── string_utils.py
│       ├── time_utils.py        # Tehran (UTC+3:30) time normalization
│       ├── path_utils.py
│       └── id_generator.py
└── feeds/                       # generated output (XML, JSON, static site)
    └── view/
        ├── index.html
        └── media/
```

<br>

## 🔧 Configuration

Sources live in `config/sources.json`:

```json
{
  "telegram": [
    { "app_name": "tgm-example", "title": "کانال نمونه", "url": "https://t.me/s/example" }
  ],
  "rss": [
    { "app_name": "rss-example", "title": "سایت نمونه", "url": "https://example.com/rss" }
  ],
  "tgju": [
    { "slang": "price_dollar_rl", "title": "دلار آمریکا" }
  ],
  "live-rates": [
    { "currency": "GOLD", "title": "طلای جهانی" }
  ]
}
```

The Gemini key is passed as a CLI argument, never stored in config.

<br>

## 🚀 Quickstart

```bash
git clone https://github.com/ch3fferson/dayereh.git
cd dayereh
pip install -r requirements.txt

python main.py                    # build without AI summary
python main.py $GEMINI_API_KEY    # build with AI summary
```

Output lands in `feeds/` and `feeds/view/index.html`. Skipping the Gemini key reuses the most recent cached bulletin.

<br>

## 📦 Deployment

Deployment is entirely handled by a scheduled GitHub Actions workflow:

- Cron trigger fixed to Tehran time (UTC+3:30, no DST): **`30 */2 * * *`** (UTC)
- Runs on the standard 2-vCPU / 7GB Actions runner
- Commits regenerated `feeds/` output back to `main`

<br>

## 📄 License

MIT — see [`LICENSE`](LICENSE).

<br>

---

<div align="center">

**تقدیم به همه جاویدنامان ایران**

<sub>شِف</sub>

</div>
