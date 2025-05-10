#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
from pydantic import BaseModel, field_validator
from urllib.parse import urlencode
import re, argparse, os, requests
from typing import List, Literal
from bs4 import BeautifulSoup
from time import sleep


''' ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ '''

def mk_search_url(params: dict):
    base_url = "https://catalog.apps.asu.edu/catalog/classes/classlist"
    return f'{base_url}?{urlencode(params)}'


def mk_soup(full_url: str, wait=False) -> BeautifulSoup:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(full_url)
        if wait: # TODO: A hack, but it needs time to make api calls to fetch course info
            sleep(5)

        html = page.content()
        browser.close()
        return BeautifulSoup(html, "html.parser")


def get_terms() -> dict:
    soup = mk_soup('https://catalog.apps.asu.edu/catalog/classes/classlist', wait=True)
    select = soup.find("select", id="term"); assert select

    # Should return an enum of term to term ID mappings
    options = [option.get_text(strip=True) for option in select.find_all("option")]
    values = [option['value'] for option in select.find_all("option") if option.has_attr("value")]
    return { option: value for option, value in zip(options, values) }


''' ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ '''

'''
TODO: I am not checking if subject and catalog number are valid. Checking subject would make sense but
      there may be a use case where a course isn't listed yet but will be in the future.
'''
all_terms = None
class SearchParams(BaseModel):

    subject: str
    term: str
    catalogNbr: int
    searchType: Literal["all", "open"]


    @field_validator('term')
    @classmethod
    def term_validator(cls, v) -> str:
        if v not in all_terms.keys():
            raise ValueError(f"Term must be one of {all_terms.keys()}")
        return v


    @field_validator('subject')
    @classmethod
    def subject_validator(cls, v) -> str:
        if not re.fullmatch(r"[A-Z]{3}", v):
            raise ValueError("Course subject is three capital letters (ex: CSE)")
        return v


''' ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ '''

class CourseInfo(BaseModel):
    number: int
    instructor: str
    location: str
    available: int
    total: int


def ping_webhook(webhook_url: str, message: str):
    json = {
        "content": message,
        "username": "RedTail - Seat Monitor"
    }
    response = requests.post(webhook_url, json=json)
    response.raise_for_status()
    return response.text


def start_poll(params: SearchParams, sleep_time):
    webhook, course_dict = os.getenv("WEBHOOK_URL"), dict()
    if not webhook:
        raise ValueError("WEBHOOK_URL is not set in environment variables.")
    course_title = f'{params.subject}-{params.catalogNbr}'

    while True:
        sleep(sleep_time)

        finds = get_course_list(params)
        for found in finds:
            description = f'{found.number} {found.instructor} *at* {found.location}, {found.available}/{found.total} seats open'
            print(f'[LOG]: checking {found}')

            if found.number not in course_dict.keys():
                ping_webhook(webhook, f'**{course_title} discovered:** {description}')

            else:
                # We want to detect both existing seats freeing up, AND new seats being added
                old = course_dict.get(found.number)
                old_diff = old.total - old.available
                new_diff = found.total - found.available
                if old_diff != new_diff and new_diff > 0:
                    ping_webhook(webhook, f'**{course_title} availability:** {description}')

            # Maintain this to avoid spam
            course_dict[found.number] = found


def __get_seat_info(text: str):
    cleaned_text = text.replace("\xa0", " ")
    match = re.search(r'(\d+)\s+of\s+(\d+)', cleaned_text)
    
    if match:
        available = match.group(1)
        total = match.group(2)
        return available, total

    return None, None


def __get_course_list(soup: BeautifulSoup) -> List[CourseInfo]:
    elements = soup.select(".focus.class-accordion.odd, .focus.class-accordion.even")
    course_list = list()

    for element in elements:
        seats = element.find("div", class_="class-results-cell seats").text
        available, total = __get_seat_info(seats)
        course_list.append(CourseInfo(
            number=element.find("div", class_="class-results-cell number").text,
            instructor=element.find("div", class_="class-results-cell instructor").text,
            location=element.find("div", class_="class-results-cell text-nowrap location").text,
            available=available, total=total
        ))

    return course_list


def get_course_list(params: SearchParams):
    # This is kinda hacky, the url needs a term ID, but I've opted to use the string
    # representation for user friendly-ness, hence this needs to be converted first
    params_dict = params.model_dump()
    params_dict['term'] = all_terms.get(params.term)
    search_url = mk_search_url(params_dict)

    soup = mk_soup(search_url, wait=True)
    return __get_course_list(soup)


''' ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ '''

def parse_args():
    parser = argparse.ArgumentParser(description="Search course catalog")
    parser.add_argument('--subject', type=str, required=True, help="3-letter subject code, e.g., CSE")
    parser.add_argument('--term', type=str, required=True, help="Term name, e.g., 'Fall 2025'")
    parser.add_argument('--number', type=int, required=True, help="Catalog number, e.g., 571")
    parser.add_argument("--sleep_time", type=int, default=10, help="Seconds between queries (default: 10)")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    all_terms = get_terms()
    params = SearchParams(
        subject=args.subject,
        term=args.term,
        catalogNbr=args.number,
        searchType='all')
    start_poll(params, args.sleep_time)

