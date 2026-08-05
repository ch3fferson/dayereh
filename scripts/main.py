import sys
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.path_utils import PathUtils
from utils.time_utils import TimeUtils
from net.fetcher import Fetcher
from net.media_downloader import MediaDownloader
from parsers.telegram import Telegram
#from parsers.website import Website
from parsers.rss import RSS
from parsers.tgju import TGJU
from parsers.live_rates import LiveRates
from builders.json_builder import JsonBuilder
from builders.xml_builder import XMLBuilder
from builders.html_builder import HTMLBuilder
from ai.gemini import GeminiClient
from ai.gemini_prompt_compressor import GeminiPromptCompressor


BASE = Path(__file__).resolve().parents[1]
SOURCE_WORKERS = 4


class App:

    def __init__(self):

        self.config = json.loads(
            (BASE / "config" / "sources.json").read_text(encoding="utf-8")
        )

        self.title_char_limit = 100
        self.html_feed_items_limit = 12
 
        self.storage = PathUtils(BASE)

        self.media_downloader = MediaDownloader(self.storage)
        self.fetcher = Fetcher()

        with ThreadPoolExecutor(max_workers=2) as executor:
            tgju_future = executor.submit(TGJU)
            live_rates_future = executor.submit(LiveRates)

            self.tgju_parser = tgju_future.result()
            self.live_rates_parser = live_rates_future.result()

        self.tgm_parser = Telegram(self.media_downloader, False, True)
        self.rss_parser = RSS(self.media_downloader, False, False)

        #self.website_parser = Website(False, False)
        
        self.json_builder = JsonBuilder()
        self.xml_builder = XMLBuilder()
        self.html_builder = HTMLBuilder(self.storage)

        self.storage.clear_media()

    def _process_source(self, kind: str, source: dict) -> dict | None:

        label = "Telegram" if kind == "telegram" else "RSS"

        try:
            if kind == "telegram":
                html = self.fetcher.get_text_by_requests(source["url"])
                items = self.tgm_parser.parse(html=html, title_char_limit=self.title_char_limit)
            else:
                xml = self.fetcher.get_text_by_requests(source["url"])
                items = self.rss_parser.parse(xml=xml, title_char_limit=self.title_char_limit)

            xml_data = self.xml_builder.build(
                items,
                source["title"]
            )

            self.storage.save_xml(
                source["app_name"],
                xml_data
            )

            print(f"✓ {label} -> feeds/{source['app_name']}.xml")

            return {
                "source": source["title"],
                "file": source["app_name"],
                "items": items[0:self.html_feed_items_limit]
            }

        except Exception as e:
            print(f"⚠ {label} failed -> {source['title']}")
            print(f"error: {e}")
            return None

    def run(self):

        prices = []
        now = TimeUtils.to_string(TimeUtils.now())

        for currency in self.config.get("tgju", []):

            try:
            
                data = self.tgju_parser.find(currency["slang"])

                price_rial = data.price
                readable_price_toman = f"{price_rial / 10:,.0f}" if price_rial % 10 == 0 else f"{price_rial / 10:,.2f}"

                if data.time:
                    formatted_time = TimeUtils.to_string(TimeUtils.parse_persian_time())
                else:
                    formatted_time = now

                prices.append({
                    "currency": currency["title"],
                    "price": readable_price_toman,
                    "time": formatted_time
                })

                print(f"✓ TGJU -> {currency['title']}")

            except Exception as e:
                print(f"⚠ TGJU failed -> {currency['title']}")
                print(f"error: {e}")

        for currency in self.config.get("live-rates", []):

            try:
            
                data = self.live_rates_parser.get(currency['currency'])

                prices.append({
                    "currency": currency["title"],
                    "price": data.rate,
                    "time": TimeUtils.from_timestamp(data.timestamp, fmt="%Y-%m-%d %H:%M:%S")
                })

                print(f"✓ Live Rates -> {currency['title']}")

            except Exception as e:
                print(f"⚠ Live Rates failed -> {currency['title']}")
                print(f"error: {e}")

        try:

            json_data = self.json_builder.build(prices)
        
            self.storage.save_json(
                "prices",
                json_data
            )

            print(f"✓ feeds/prices.json generated")

        except Exception as e:
            print(f"⚠ feeds/prices.json was not generated")
            print(f"error: {e}")

        telegram_sources = self.config.get("telegram", [])
        rss_sources = self.config.get("rss", [])

        jobs = (
            [("telegram", source) for source in telegram_sources]
            + [("rss", source) for source in rss_sources]
        )

        results = [None] * len(jobs)

        with ThreadPoolExecutor(max_workers=SOURCE_WORKERS) as executor:
            future_to_index = {
                executor.submit(self._process_source, kind, source): index
                for index, (kind, source) in enumerate(jobs)
            }

            for future in as_completed(future_to_index):
                results[future_to_index[future]] = future.result()

        feeds = [feed for feed in results if feed]

        """ for source in self.config.get("website", []):

            try:
                html = self.fetcher.get_text_by_selenium_by_css(source["url"], source["selectors"]["title"])
                items = self.website_parser.parse(html=html, scraping_rules=json.dumps(source["selectors"]), title_char_limit=self.title_char_limit)

                xml_data = self.xml_builder.build(
                    items,
                    source["title"]
                )

                self.storage.save_xml(
                    source["app_name"],
                    xml_data
                )

                feeds.append({
                    "source": source["title"],
                    "file": source["app_name"],
                    "items": items[0:self.html_feed_items_limit]
                })

                print(f"✓ Website -> feeds/{source['app_name']}.xml")

            except Exception as e:
                print(f"⚠ Website failed -> {source['title']}")
                print(f"error: {e}") """

        gemini_key = (
            sys.argv[1]
            if len(sys.argv) > 1
            else None
        )
        
        result = None
        summary_text = None
        
        MEMORY_START = "---MEMORY_START---"
        MEMORY_END = "---MEMORY_END---"
        
        if gemini_key:
        
            try:
        
                with (
                    open(
                        BASE / "scripts" / "ai" / "soul.md",
                        "r",
                        encoding="utf-8",
                    ) as soulf,
                    open(
                        BASE / "scripts" / "ai" / "memory.md",
                        "r+",
                        encoding="utf-8",
                    ) as memoryf,
                ):
        
                    print(
                        "⟳ Reading soul and memory for Gemini"
                    )
        
                    soul = soulf.read()
                    memory = memoryf.read()
        
                    print(
                        "✓ Gemini soul and memory loaded"
                    )
        
                    client = GeminiClient(
                        api_key=gemini_key,
                        model="gemini-3.5-flash",
                        system_instruction=soul,
                        temperature=0.2,
                        top_p=1.0,
                        max_output_tokens=3000,
                    )
        
                    print(
                        f"✓ Model: {client.model}"
                    )
        
                    print(
                        f"✓ Input limit: "
                        f"{client.input_token_limit:,}"
                    )
        
                    print(
                        f"✓ Output limit: "
                        f"{client.output_token_limit:,}"
                    )
        
                    items_content = [
                        content
                        for feed in feeds
                        for item in feed.get("items", [])
                        if (
                            content :=
                            getattr(
                                item,
                                "content",
                                "",
                            ).strip()
                        )
                    ]
        
                    prices_text = ", ".join(
                        f"{p['currency']}: {p['price']}"
                        for p in prices
                    )
        
                    prompt_template = f"""مورخ {now}:
آخرین قیمت‌ها:
{prices_text}
فیدهای خبری:
{{NEWS}}
Context Memory:
{memory}
"""
        
                    fixed_prompt = (
                        prompt_template.replace(
                            "{NEWS}",
                            "",
                        )
                    )
        
                    fixed_tokens = (
                        client.count_tokens(
                            fixed_prompt
                        )
                    )
        
                    available_tokens = max(
                        1,
                        client.input_token_limit
                        - fixed_tokens,
                    )
        
                    compression_budget = max(
                        1,
                        int(
                            available_tokens * 0.92
                        ),
                    )
        
                    print(
                        f"⟳ News budget: "
                        f"{compression_budget:,} tokens"
                    )
        
                    compressor = GeminiPromptCompressor(
                        max_tokens=compression_budget,
                        device="cpu",
                    )
        
                    compressed = (
                        compressor.compress_items(
                            items_content
                        )
                    )
        
                    prompt = (
                        prompt_template.replace(
                            "{NEWS}",
                            compressed,
                        )
                    )
        
                    prompt_tokens = (
                        client.count_tokens(
                            prompt
                        )
                    )
        
                    if (
                        prompt_tokens
                        > client.input_token_limit
                    ):
        
                        print(
                            "⚠ Prompt still exceeds "
                            "Gemini limit; recompressing"
                        )
        
                        compression_budget = max(
                            1,
                            int(
                                compression_budget
                                * client.input_token_limit
                                / prompt_tokens
                                * 0.95
                            ),
                        )
        
                        compressor = GeminiPromptCompressor(
                            max_tokens=compression_budget,
                            device="cpu",
                        )
        
                        compressed = (
                            compressor.compress_items(
                                items_content
                            )
                        )
        
                        prompt = (
                            prompt_template.replace(
                                "{NEWS}",
                                compressed,
                            )
                        )
        
                        prompt_tokens = (
                            client.count_tokens(
                                prompt
                            )
                        )
        
                    print(
                        f"✓ Final prompt: "
                        f"{prompt_tokens:,} / "
                        f"{client.input_token_limit:,} "
                        f"Gemini tokens"
                    )
        
                    print(
                        "⟳ Summarizing Data using Gemini"
                    )
        
                    result = client.send(
                        prompt
                    )
        
                    if (
                        MEMORY_START in result
                        and MEMORY_END in result
                    ):
        
                        summary_text, remainder = (
                            result.split(
                                MEMORY_START,
                                1,
                            )
                        )
        
                        memory_text, _ = (
                            remainder.split(
                                MEMORY_END,
                                1,
                            )
                        )
        
                        summary_text = (
                            summary_text.strip()
                        )
        
                        memory_text = (
                            memory_text.strip()
                        )
        
                    else:
        
                        print(
                            "⚠ Memory delimiter not found"
                        )
        
                        summary_text = result.strip()
                        memory_text = None
        
                    json_data = (
                        self.json_builder.build(
                            {
                                "summary": summary_text,
                                "time": now,
                            }
                        )
                    )
        
                    self.storage.save_json(
                        "news-summary",
                        json_data,
                    )
        
                    print(
                        "✓ Gemini -> news-summary.json"
                    )
        
                    if memory_text is not None:
        
                        print(
                            "⟳ Updating Memory"
                        )
        
                        memoryf.seek(0)
                        memoryf.write(memory_text)
                        memoryf.truncate()
        
                        print(
                            "✓ Memory updated successfully"
                        )
        
            except Exception as e:
        
                print(
                    "⚠ Data summarization failed"
                )
        
                print(
                    f"error: {e}"
                )
        
        
        summary = None
        
        try:
        
            if result and summary_text:
        
                summary = (
                    summary_text,
                    now,
                )
        
            else:
        
                print(
                    "⟳ Using most recent summary"
                )
        
                with open(
                    BASE
                    / "feeds"
                    / "news-summary.json",
                    "r",
                    encoding="utf-8",
                ) as summaryf:
        
                    data = json.load(
                        summaryf
                    )
        
                    summary = (
                        data.get("summary"),
                        data.get("time"),
                    )
        
        except Exception as e:
        
            print(
                "⚠ Couldn't read most recent summary"
            )
        
            print(
                f"error: {e}"
            )
        
        
        try:
        
            html = self.html_builder.build(
                feeds,
                prices,
                summary,
            )
        
            self.storage.save_html(
                html
            )
        
            print(
                "✓ SITE LAUNCHED -> "
                "feeds/view/index.html"
            )
        
        except Exception as e:
        
            print(
                "⚠ failed to launch site"
            )
        
            print(
                f"error: {e}"
            )


if __name__ == "__main__":
    App().run()
