import json
import lxml 
import requests
import spacy
import yaml
from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta
from spacy.matcher import PhraseMatcher
from time import sleep 

api_key = secrets()["nyt"]

nlp = spacy.load('en_core_web_sm')
# matcher = PhraseMatcher(nlp.vocab)

article_search_url = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
time_format = "%Y%m%d"
sleepy_time = 6.15 # 6 seconds between requests is the NYT requested rate limit. Total limit is 4K requests/day 


def secrets(secrets_file: str = ".secret.yaml") -> dict:
    """
    input file path to secrets.yaml file
    parse the file
    output the resulting dictionary 
    """
    with open(secrets_file, "r") as f:
        try:
            return yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(e)


def load_search_terms(search_terms_filename: str="climate_terms.txt") -> list: 
    with open("search_terms.txt", "r") as f: 
        txt = f.readlines()
    terms = [t.strip() for t in txt]
    return terms


def search_q_for_date( 
    url: str = article_search_url,
    api_key: str = api_key,
    date: str = date.today().strftime(time_format),
    q="climate",
) -> dict:
    """
    date must be a string in "%Y%m%d" format
    """
    params = {
        "q": q,
        "begin_date": date,
        "end_date": date,
        "api-key": api_key,
    }
    return requests.get(article_search_url, params=params).json()


def get_climate_story_count_for_date(
    date: str = date.today().strftime(time_format),
) -> dict:
    """
    date must be a string in "%Y%m%d" format
    """
    d = search_q_for_date(date=date) 
    sleep(sleepy_time) 
    return {"date": date, "count": d["response"]["meta"]["hits"]}


def generate_list_of_days_in_range(start_date: str, end_date: str) -> list:
    end = datetime.strptime(end_date, time_format)
    start = datetime.strptime(start_date, time_format)
    delta = timedelta(days=1)
    dates = []
    while start <= end:
        dates.append(start.strftime(time_format))
        start += delta
    return dates


def get_climate_counts_per_day_in_range(
    start_date: str = date.today().strftime(time_format),
    end_date: str = date.today().strftime(time_format),
) -> list:
    dates = generate_list_of_days_in_range(start_date, end_date) 
    print(f"{len(dates)} dates at {sleepy_time} seconds per request.  Should be ready in {len(dates) * sleepy_timel} seconds")
    return [get_climate_story_count_for_date(date) for date in dates] 


# homage to https://github.com/nilmolne/Text-Mining-The-New-York-Times-Articles/blob/master/Code/textminingnyt.py lines 115 - 129
def url_to_article_text(web_url:str) -> str: 
    r = requests.get(web_url)
    soup = BeautifulSoup(r.text, "lxml")
    paragraph_tags = soup.find_all('p')
    p_tag_texts = [p.get_text().strip() for p in paragraph_tags]
    article_text = " ".join(p_tag_texts)
    if article_text.startswith("Advertisement"): 
        article_text = article_text[len("Advertisement"):].strip()
    if article_text.endswith("Advertisement"):
        article_text = article_text[:-len("Advertisement")].strip()
    if article_text.startswith("Supported by"): 
        article_text = article_text[len("Supported by"):].strip()
    return article_text

def create_term_matcher(terms: list) -> PhraseMatcher:
    nlp = spacy.load('en_core_web_sm')
    matcher = PhraseMatcher(nlp.vocab) 
    patterns = [nlp.make_doc(text) for text in terms] 
    matcher.add("TerminologyList", None, *patterns)
    return matcher 


def term_matches_from_text(text: str, matcher: PhraseMatcher, nlp_model: spacy.lang.en.English) -> dict: 
    doc = nlp_model(text)
    matches = matcher(doc) 
    matched_terms = [doc[start:end].text for match_id, start, end in matches]
    return matched_terms 


def count_matches(terms: list, matched_terms: list) -> dict: 
    return {term: matched_terms.count(term) for term in list(set(terms))}


def log_article(document_json: dict):
    pass 
    