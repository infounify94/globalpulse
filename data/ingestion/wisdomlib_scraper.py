import os
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

class WisdomLibScraper:
    """
    Crawls specific texts from WisdomLib, extracting content and strict metadata
    so it can be evaluated as a hypothesis source by the LLM pipeline.
    """
    def __init__(self, base_dir="data/datasets/wisdomlib"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def scrape_text_chapter(self, text_id: str, chapter_url: str) -> dict:
        """
        Scrapes a single chapter, stores it as a Markdown block with metadata.
        """
        try:
            print(f"Scraping: {chapter_url}")
            response = requests.get(chapter_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Wisdomlib content is usually in a div with id 'content' or class 'text'
            content_div = soup.find('div', id='content') or soup.find('div', class_='text')
            if not content_div:
                return {}

            paragraphs = content_div.find_all('p')
            text_content = "\n\n".join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
            
            title_tag = soup.find('h1')
            title = title_tag.get_text().strip() if title_tag else chapter_url.split('/')[-1]
            
            doc = {
                "text_id": text_id,
                "chapter_title": title,
                "url": chapter_url,
                "scraped_at": datetime.utcnow().isoformat() + "Z",
                "content": text_content,
                "source_type": "ancient_text",
                "hypothesis_valid": "pending_validation" # Walk-forward must validate
            }
            return doc
        except Exception as e:
            print(f"Failed to scrape {chapter_url}: {e}")
            return {}

    def save_corpus(self, text_id: str, documents: list):
        """Save the extracted documents to a JSONL corpus."""
        path = os.path.join(self.base_dir, f"{text_id}_corpus.jsonl")
        with open(path, 'a', encoding='utf-8') as f:
            for doc in documents:
                if doc:
                    f.write(json.dumps(doc, ensure_ascii=False) + '\n')
        print(f"Saved {len(documents)} documents to {path}")

if __name__ == "__main__":
    # Proof of Concept: Brihat Parashara Hora Shastra (BPHS)
    scraper = WisdomLibScraper()
    
    # We will scrape just one sample chapter to prove the architecture works
    # without overloading their servers.
    sample_url = "https://www.wisdomlib.org/hinduism/book/brihat-parasara-hora-sastra/d/doc161582.html"
    
    doc = scraper.scrape_text_chapter("bphs", sample_url)
    if doc:
        scraper.save_corpus("bphs", [doc])
        print("Proof of concept BPHS chapter successfully stored with metadata.")
