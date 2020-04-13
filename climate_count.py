import argparse 
import json
import lxml
import requests
import spacy
#import yaml
from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta
from math import ceil
#from pathlib import Path
from utils import initialize_json_directory, read_config, save_doc_json_to_file
from spacy.matcher import PhraseMatcher
from time import sleep


nlp = spacy.load("en_core_web_sm")
# matcher = PhraseMatcher(nlp.vocab)

article_search_url = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
time_format = "%Y%m%d"
sleepy_time = 6.15  # 6 seconds between requests is the NYT requested rate limit. Total limit is 4K requests/day

api_key = read_config(".secret.yaml")["nyt"]
json_directory = read_config(".config.yaml")["json"]


def load_search_terms(search_terms_filename: str = "climate_terms.txt") -> list:
    with open("search_terms.txt", "r") as f:
        txt = f.readlines()
    terms = [t.strip() for t in txt]
    return terms


def search_q_for_date(
    url: str = article_search_url,
    api_key: str = api_key,
    date_string:str = date.today().strftime(time_format),
    q="climate",
    page=0,
) -> dict:
    """
    date must be a string in "%Y%m%d" format
    """
    params = {
        "q": q,
        "begin_date": date_string,
        "end_date": date_string,
        "api-key": api_key,
        "page": page,
    }
    return requests.get(article_search_url, params=params).json()

#TODO: Add retries on error
def get_all_article_docs_from_query(url: str = article_search_url, api_key: str = api_key, date_str:str=date.today().strftime(time_format), q="climate", page=0) -> dict:
    params = {
        "q": q,
        "begin_date": date_str,
        "end_date": date_str,
        "api-key": api_key,
        "page": page,
    }
    response_json = requests.get(article_search_url, params=params).json()
    print(f"len(response_json): {len(response_json)}")
    hits = response_json["response"]["meta"]["hits"]
    print(f"hits: {hits}")
    total_pages = ceil(hits/10.0)
    print(f"total_pages: {total_pages}")
    docs = response_json['response']['docs']
    print(f"len(docs): {len(docs)}; params['page']: {params['page']}")
    params['page'] += 1
    for p in range(params["page"], total_pages):
        sleep(sleepy_time)
        params["page"] = p
        docs.extend(requests.get(article_search_url, params=params).json()['response']['docs'])
        print(f"len(docs): {len(docs)}; params['page']: {params['page']}")
    if len(docs) < hits: 
        print(f"only collected {len(docs)} documents out of {hits}.")
    return docs


def generate_list_of_days_in_range(start_date: str, end_date: str) -> list:
    end = datetime.strptime(end_date, time_format)
    start = datetime.strptime(start_date, time_format)
    delta = timedelta(days=1)
    dates = []
    while start <= end:
        dates.append(start.strftime(time_format))
        start += delta
    return dates


# def get_climate_counts_per_day_in_range(
#     start_date: str = date.today().strftime(time_format),
#     end_date: str = date.today().strftime(time_format),
# ) -> list:
#     dates = generate_list_of_days_in_range(start_date, end_date)
#     print(
#         f"{len(dates)} dates at {sleepy_time} seconds per request.  Should be ready in {len(dates) * sleepy_timel} seconds"
#     )
#     return [get_climate_story_count_for_date(date) for date in dates]


# homage to https://github.com/nilmolne/Text-Mining-The-New-York-Times-Articles/blob/master/Code/textminingnyt.py lines 115 - 129
def url_to_article_text(web_url: str) -> str:
    r = requests.get(web_url)
    soup = BeautifulSoup(r.text, "lxml")
    paragraph_tags = soup.find_all("p")
    p_tag_texts = [p.get_text().strip() for p in paragraph_tags]
    article_text = " ".join(p_tag_texts)
    if article_text.startswith("Advertisement"):
        article_text = article_text[len("Advertisement") :].strip()
    if article_text.endswith("Advertisement"):
        article_text = article_text[: -len("Advertisement")].strip()
    if article_text.startswith("Supported by"):
        article_text = article_text[len("Supported by") :].strip()
    return article_text


def create_term_matcher(terms: list) -> PhraseMatcher:
    nlp = spacy.load("en_core_web_sm")
    matcher = PhraseMatcher(nlp.vocab)
    patterns = [nlp.make_doc(text) for text in terms]
    matcher.add("TerminologyList", None, *patterns)
    return matcher


def term_matches_from_text(
    text: str, matcher: PhraseMatcher, nlp_model: spacy.lang.en.English
) -> dict:
    doc = nlp_model(text)
    matches = matcher(doc)
    matched_terms = [doc[start:end].text for match_id, start, end in matches]
    return matched_terms


def count_matches(terms: list, matched_terms: list) -> dict:
    return {term: matched_terms.count(term) for term in list(set(terms))}


def enrich_article(
    doc: dict, terms: list, matcher: PhraseMatcher, nlp_model: spacy.lang.en.English
) -> dict:
    """
    input: nyt_api_response_json['response']['docs']
    Add term counts
    return updated json 
    """
    # multimedia can get pretty big.
    # not going to use it.  Why not drop it?
    if doc.get("multimedia"):
        doc.pop("multimedia")

    # pull the article, grab the text
    doc["text"] = url_to_article_text(doc["web_url"])

    # count matched terms
    matched_terms = term_matches_from_text(doc["text"], matcher, nlp_model)
    doc["term_counts"] = count_matches(terms, matched_terms)
    return doc


def term_count_for_date_range(start_date: str, end_date: str=date.today().strftime(time_format), query_term: str="climate"):

    # load model 
    nlp = spacy.load("en_core_web_sm")

    # prep terms for nlp
    search_terms = load_search_terms("climate_terms.txt")
    matcher = create_term_matcher(search_terms)

    #read in configs
    json_directory = read_config(".config.yaml")["json"]

    # initialize file repo
    json_repo = initialize_json_directory(json_directory)

    date_list = generate_list_of_days_in_range(start_date, end_date) 
    for date in date_list: 
        docs = get_all_article_docs_from_query(date_str=date, q=query_term)
        for doc in docs: 
            enrich_article(doc, search_terms, matcher, nlp)
            save_doc_json_to_file(doc, json_repo)
        print(date)
        sleep(sleepy_time) 

def main(): 

    parser = argparse.ArgumentParser(description="Set start and end dates for query")

    parser.add_argument("start_date",
                        type=str,
                        help=f"format: {time_format}",
                        )

    parser.add_argument("end_date",
                    type=str,
                    default=date.today().strftime(time_format),
                    help=f"format: {time_format}")

    parser.add_argument("query_term",
                type=str,
                default="climate",
                help=f"Term for API query.  ex: 'climate'") 

    args = parser.parse_args() 

    term_count_for_date_range(start_date=args.start_date, end_date=args.end_date, query_term=args.query_term)

if __name__ == "__main__":
    main() 