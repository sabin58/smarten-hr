import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
]


class Mero(models.Model):
    _name = "mero.rashifal"
    _description = "Mero Rashifal"
    _order = "date desc"

    rashi = fields.Char(required=True)
    description = fields.Text()
    image_url = fields.Char()
    detail_url = fields.Char()
    date = fields.Date(default=fields.Date.today)

    _sql_constraints = [
        (
            "unique_rashi_date",
            "unique(rashi, date)",
            "Rashifal already exists for this rashi today!",
        )
    ]

    @api.model
    def scrape_daily_rashifal(self):
        BASE_URL = "https://www.hamropatro.com/"
        URL = urljoin(BASE_URL, "rashifal")
        headers = {"User-Agent": random.choice(USER_AGENTS)}

        try:
            response = requests.get(URL, headers=headers, timeout=20)
            response.raise_for_status()
        except Exception as e:
            raise UserError(f"Failed to fetch data: {e}")

        soup = BeautifulSoup(response.text, "lxml")

        rashifal_section = soup.find("div", id="rashifal")
        if not rashifal_section:
            raise UserError("Rashifal section not found!")

        items = rashifal_section.select(".item")

        today = date.today()

        for item in items:
            title = item.find("h3").get_text(strip=True)
            description = item.select_one(".desc p").get_text(strip=True)

            img_tag = item.find("img")
            image_url = urljoin(BASE_URL, img_tag["src"]) if img_tag else ""

            parent_link = item.find_parent("a")
            detail_url = urljoin(BASE_URL, parent_link["href"]) if parent_link else ""

            existing = self.search(
                [("rashi", "=", title), ("date", "=", today)], limit=1
            )

            if not existing:
                self.create(
                    {
                        "rashi": title,
                        "description": description,
                        "image_url": image_url,
                        "detail_url": detail_url,
                        "date": today,
                    }
                )

        return True
