from duckduckgo_search import DDGS

# Helper function to get product image from DuckDuckGo
def get_image_from_duckduckgo(query):
    try:
        with DDGS() as ddgs:
            results = ddgs.images(query, max_results=1)
            if results:
                return results[0].get("image") or results[0].get("thumbnail")
    except Exception as e:
        print("DuckDuckGo image search failed:", e)
    return None
