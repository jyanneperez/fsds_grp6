from duckduckgo_search import DDGS
import re
import tldextract
import time
import random

def lookup_country_from_web(product_name, query):
    # Country domain mapping
    domain_country_mapping = {
        ".ca": "Canada",
        ".us": "United States",
        ".uk": "United Kingdom",
        ".de": "Germany",
        ".fr": "France",
        ".it": "Italy",
        ".jp": "Japan",
        ".au": "Australia",
        ".nz": "New Zealand",
        ".cn": "China",
        ".in": "India",
        ".es": "Spain",
        ".br": "Brazil",
        ".mx": "Mexico",
        ".nl": "Netherlands",
        ".ch": "Switzerland",
        ".se": "Sweden",
        ".no": "Norway",
        ".fi": "Finland"
    }

    # Step 1: Try website-based lookup
    site_query = query
    try:
        with DDGS() as ddgs:
            results = ddgs.text(site_query, max_results=3)
            for result in results:
                url = result.get('href', '')
                ext = tldextract.extract(url)
                tld = f".{ext.suffix}" 

                if tld in domain_country_mapping:
                    return domain_country_mapping[tld]
    except Exception as e:
        print("Website lookup failed:", e)

    # Step 2: Fallback to manufacturing info from search snippet
    fallback_query = f"Where is {product_name} manufactured"
    try:
        with DDGS() as ddgs:
            results = ddgs.text(fallback_query, max_results=1)
            if results and 'body' in results[0]:
                snippet = results[0]['body'].lower()
                for key in domain_country_mapping.values():
                    if re.search(r'\b' + re.escape(key.lower()) + r'\b', snippet):
                        return key
    except Exception as e:
        print("Manufacturing lookup failed:", e)

    time.sleep(random.uniform(1.5, 3.0))
    return None

def rule_based_shelf_life(product_name):
    name = product_name.lower()
    if any(x in name for x in ["milk", "yogurt", "brie", "fresh", "ricotta", "cottage cheese"]):
        return 7
    elif any(x in name for x in ["fruit", "vegetable"]):
        return 10
    elif any(x in name for x in ["meat", "fish"]):
        return 14
    elif any(x in name for x in ["canned", "snack", "soda", "chocolate", "biscuit", 'butter', 'cheddar', 'swiss cheese', 'parmesan']):
        return 180
    else:
        return 0

def lookup_shelf_life_from_web(product_name):
    query = f"Shelf life of {product_name}"
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=1)
            if results and 'body' in results[0]:
                snippet = results[0]['body']
                match = re.search(r'(\d+)\s*(day|week|month|year)', snippet.lower())
                if match:
                    value = int(match.group(1))
                    unit = match.group(2)
                    if "year" in unit:
                        return value * 365
                    elif "month" in unit:
                        return value * 30
                    elif "week" in unit:
                        return value * 7
                    else:
                        return value
    except Exception as e:
        print("Web shelf life lookup failed:", e)
    return None