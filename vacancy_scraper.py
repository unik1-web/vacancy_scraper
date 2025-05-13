import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import json
import os
import re
from urllib.parse import quote_plus

# Конфигурация
CONFIG = {
    "telegram_bot_token": "7739167340:AAHfiWC6F29K7EDGP4ugnGv0d9S0e-j3Qlk",
    "telegram_chat_id": "340159288",
    "search_queries": ["python junior удаленно", "python стажировка удаленно"],
    "check_interval": 3600,  # Проверка каждые 3600 секунд (1 час)
    "data_file": "vacancies.json",
    "custom_sites": [
        {
            "name": "HH.ru",
            "url_template": "https://hh.ru/search/vacancy?text={query}&schedule=remote",
            "parser": "parse_hh"
        },
        {
            "name": "Habr Career",
            "url_template": "https://career.habr.com/vacancies?q={query}&remote=true",
            "parser": "parse_habr"
        },
        {
            "name": "Rabota.ru",
            "url_template": "https://rabota.ru/vacancy/?query={query}&employment=remote",
            "parser": "parse_rabota"
        },
        {
            "name": "Remote job",
            "url_template": "https://remote-job.ru/search?search%5Bquery%5D={query}&search%5BsearchType%5D=vacancy",
            "parser": "parse_remote_job"
        },
        # Добавьте свои сайты по образцу:
        # {
        #     "name": "Название сайта",
        #     "url_template": "URL с {query} вместо поискового запроса",
        #     "parser": "ваша_функция_парсера"
        # }
    ]
}


class VacancyScraper:
    def __init__(self):
        self.sent_vacancies = self.load_sent_vacancies()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

    def load_sent_vacancies(self):
        """Загружает уже отправленные вакансии из файла"""
        if os.path.exists(CONFIG["data_file"]):
            with open(CONFIG["data_file"], "r", encoding="utf-8") as f:
                return set(json.load(f))
        return set()

    def save_sent_vacancies(self):
        """Сохраняет отправленные вакансии в файл"""
        with open(CONFIG["data_file"], "w", encoding="utf-8") as f:
            json.dump(list(self.sent_vacancies), f)

    def clean_text(self, text):
        """Очищает текст от лишних пробелов и переносов строк"""
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text).strip()

    def parse_remote_job(self, html):
        """Парсер для remote-job.ru"""
        try:
            # код парсера
            soup = BeautifulSoup(html, "html.parser")
            vacancies = []

            for item in soup.find_all("div", class_="vacancy-card"):
                title_tag = item.find("h3", class_="vacancy-card__title")
                if not title_tag:
                    continue

                title = self.clean_text(title_tag.text)
                link = "https://remote-job.ru" + title_tag.find("a")["href"]
                company = item.find("div", class_="vacancy-card__company-name")
                company = self.clean_text(company.text) if company else "Не указано"
                location = item.find("div", class_="vacancy-card__locations")
                location = self.clean_text(location.text) if location else "Не указано"
                salary = item.find("div", class_="vacancy-card__salary")
                salary = self.clean_text(salary.text) if salary else "Не указана"

                # Проверяем, что вакансия удалённая
                if "удален" not in location.lower() and "remote" not in location.lower():
                    continue

                vacancy_id = link.split("/")[-1]

                vacancies.append({
                    "id": f"remotejob_{vacancy_id}",
                    "title": title,
                    "company": company,
                    "location": location,
                    "salary": salary,
                    "link": link,
                    "requirements": "См. описание на сайте",
                    "source": "remote-job.ru"
                })
        except Exception as e:
            print(f"Ошибка при парсинге {site_config['name']}: {e}")
            return []


        return vacancies

    def parse_rabota(self, html):
        """Парсер для rabota.ru"""
        soup = BeautifulSoup(html, "html.parser")
        vacancies = []

        for item in soup.find_all("article", class_="vacancy-preview-card"):
            title_tag = item.find("h3", class_="vacancy-preview-card__title")
            if not title_tag:
                continue

            title = self.clean_text(title_tag.text)
            link = "https://rabota.ru" + title_tag.find("a")["href"]
            company = item.find("span", class_="vacancy-preview-card__company-name")
            company = self.clean_text(company.text) if company else "Не указано"
            location = item.find("span", class_="vacancy-preview-card__location")
            location = self.clean_text(location.text) if location else "Не указано"
            salary = item.find("span", class_="vacancy-preview-card__salary")
            salary = self.clean_text(salary.text) if salary else "Не указана"

            # Проверяем, что вакансия удалённая
            if "удален" not in location.lower() and "remote" not in location.lower():
                continue

            vacancy_id = link.split("/")[-2]

            vacancies.append({
                "id": f"rabota_{vacancy_id}",
                "title": title,
                "company": company,
                "location": location,
                "salary": salary,
                "link": link,
                "requirements": "См. описание на сайте",
                "source": "Rabota.ru"
            })

        return vacancies

    def parse_hh(self, html):
        """Парсер для hh.ru"""
        soup = BeautifulSoup(html, "html.parser")
        vacancies = []

        for item in soup.find_all("div", class_="vacancy-serp-item-body"):
            title_tag = item.find("a", class_="serp-item__title")
            if not title_tag:
                continue

            title = self.clean_text(title_tag.text)
            link = title_tag["href"].split("?")[0]
            company = item.find("a", class_="bloko-link_kind-tertiary")
            company = self.clean_text(company.text) if company else "Не указано"
            location = item.find("div", {"data-qa": "vacancy-serp__vacancy-address"})
            location = self.clean_text(location.text) if location else "Не указано"
            salary = item.find("span", {"data-qa": "vacancy-serp__vacancy-compensation"})
            salary = self.clean_text(salary.text) if salary else "Не указана"

            if "удален" not in location.lower() and "remote" not in location.lower():
                continue

            vacancy_id = link.split("/")[-1]
            requirements = self.get_hh_requirements(link) if "hh.ru" in link else "Не указаны"

            vacancies.append({
                "id": vacancy_id,
                "title": title,
                "company": company,
                "location": location,
                "salary": salary,
                "link": link,
                "requirements": requirements,
                "source": "hh.ru"
            })

        return vacancies

    def get_hh_requirements(self, url):
        """Получает требования с hh.ru"""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            section = soup.find("div", {"data-qa": "vacancy-description"})
            if not section:
                return "Не указаны"

            text = self.clean_text(section.text)
            return text[:1000] + "..." if len(text) > 1000 else text
        except Exception as e:
            print(f"Ошибка при получении требований с hh.ru: {e}")
            return "Не удалось получить требования"

    def parse_habr(self, html):
        """Парсер для career.habr.com"""
        soup = BeautifulSoup(html, "html.parser")
        vacancies = []

        for item in soup.find_all("div", class_="vacancy-card"):
            title_tag = item.find("a", class_="vacancy-card__title-link")
            if not title_tag:
                continue

            title = self.clean_text(title_tag.text)
            link = "https://career.habr.com" + title_tag["href"]
            company = item.find("a", class_="vacancy-card__company-title")
            company = self.clean_text(company.text) if company else "Не указано"
            meta = item.find("div", class_="vacancy-card__meta")
            location = self.clean_text(meta.text) if meta else "Не указано"
            salary = item.find("div", class_="vacancy-card__salary")
            salary = self.clean_text(salary.text) if salary else "Не указана"

            if "удален" not in location.lower() and "remote" not in location.lower():
                continue

            vacancy_id = link.split("/")[-1]
            requirements = self.get_habr_requirements(link)

            vacancies.append({
                "id": vacancy_id,
                "title": title,
                "company": company,
                "location": location,
                "salary": salary,
                "link": link,
                "requirements": requirements,
                "source": "career.habr.com"
            })

        return vacancies

    def get_habr_requirements(self, url):
        """Получает требования с career.habr.com"""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            section = soup.find("div", class_="vacancy-description__text")
            if not section:
                return "Не указаны"

            text = self.clean_text(section.text)
            return text[:1000] + "..." if len(text) > 1000 else text
        except Exception as e:
            print(f"Ошибка при получении требований с career.habr.com: {e}")
            return "Не удалось получить требования"

    def scrape_site(self, site_config, query):
        """Общая функция для скрапинга сайта"""
        try:
            url = site_config["url_template"].format(query=quote_plus(query))
            response = self.session.get(url)
            response.raise_for_status()

            parser = getattr(self, site_config["parser"])
            return parser(response.text)
        except Exception as e:
            print(f"Ошибка при парсинге {site_config['name']}: {e}")
            return []

    def send_to_telegram(self, vacancy):
        """Отправляет вакансию в Telegram"""
        message = (
            f"🏢 <b>{vacancy['title']}</b>\n"
            f"📌 <b>Компания:</b> {vacancy['company']}\n"
            f"💰 <b>Зарплата:</b> {vacancy['salary']}\n"
            f"🌍 <b>Локация:</b> {vacancy['location']}\n"
            f"🔗 <a href='{vacancy['link']}'>Ссылка на вакансию</a>\n"
            f"📌 <b>Источник:</b> {vacancy['source']}\n\n"
            f"📝 <b>Требования:</b>\n{vacancy['requirements']}"
        )

        url = f"https://api.telegram.org/bot{CONFIG['telegram_bot_token']}/sendMessage"
        params = {
            "chat_id": CONFIG["telegram_chat_id"],
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

        try:
            response = requests.post(url, params=params)
            response.raise_for_status()
            print(f"Отправлено в Telegram: {vacancy['title']}")
            return True
        except Exception as e:
            print(f"Ошибка при отправке в Telegram: {e}")
            return False

    def process_vacancies(self):
        """Основной метод обработки вакансий"""
        all_vacancies = []

        for query in CONFIG["search_queries"]:
            for site in CONFIG["custom_sites"]:
                all_vacancies.extend(self.scrape_site(site, query))

        new_vacancies = 0

        for vacancy in all_vacancies:
            if vacancy["id"] not in self.sent_vacancies:
                if self.send_to_telegram(vacancy):
                    self.sent_vacancies.add(vacancy["id"])
                    new_vacancies += 1

        if new_vacancies > 0:
            self.save_sent_vacancies()

        print(f"Найдено новых вакансий: {new_vacancies}")

    def run(self):
        """Запуск скрапера в бесконечном цикле"""
        print("Скрапер вакансий запущен. Для остановки нажмите Ctrl+C")
        print(f"Зарегистрированные сайты: {[s['name'] for s in CONFIG['custom_sites']]}")

        try:
            while True:
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Начинаю проверку вакансий...")
                self.process_vacancies()
                print(f"Следующая проверка через {CONFIG['check_interval']} секунд...")
                time.sleep(CONFIG["check_interval"])
        except KeyboardInterrupt:
            print("Скрапер остановлен")


if __name__ == "__main__":
    # Перед запуском замените YOUR_TELEGRAM_BOT_TOKEN и YOUR_TELEGRAM_CHAT_ID

    # Пример добавления нового сайта:
    # CONFIG["custom_sites"].append({
    #     "name": "Новый сайт",
    #     "url_template": "https://example.com/search?q={query}&remote=1",
    #     "parser": "parse_new_site"  # Нужно создать метод parse_new_site(self, html)
    # })

    scraper = VacancyScraper()
    scraper.run()
