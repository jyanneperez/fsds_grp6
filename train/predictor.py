import pandas as pd
import numpy as np
from scipy.sparse import hstack, csr_matrix
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
import joblib

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None
    print("duckduckgo_search not installed. Image search will not work.")

# Load saved models and encoders
tfidf = joblib.load("ridge_tfidf.pkl")
scaler = joblib.load("ridge_scaler.pkl")
shelf_life_model = joblib.load("ridge_shelf_life_model.pkl")
country_clf = joblib.load("xgb_country_model.pkl")
le_country = joblib.load("label_encoder_country.pkl")

# Fallback shelf life logic
def rule_based_shelf_life(product_name):
    name = product_name.lower()
    if any(x in name for x in ["milk", "yogurt", "cheese", "fresh"]):
        return 7
    elif any(x in name for x in ["fruit", "vegetable"]):
        return 10
    elif any(x in name for x in ["meat", "fish"]):
        return 14
    elif any(x in name for x in ["canned", "snack", "soda", "chocolate", "biscuit"]):
        return 180
    else:
        return 30

# Optional image retrieval
def get_image_url(product_name):
    if DDGS is None:
        return None
    try:
        with DDGS() as ddgs:
            results = ddgs.images(product_name, max_results=1)
            if results:
                return results[0].get("image")
    except Exception as e:
        print("Image search failed:", e)
    return None

# Inference function
def predict(product_name, manufacture_date_str):
    try:
        manufacture_date = pd.to_datetime(manufacture_date_str)
    except:
        return {"error": "Invalid date format. Use YYYY-MM-DD."}

    input_text = f"{product_name} {product_name.lower()}"
    X_text = tfidf.transform([input_text])
    X_numeric = scaler.transform([np.zeros(8)])  # no nutrition at inference
    X_input = hstack([X_text, csr_matrix(X_numeric)])

    try:
        predicted_days = max(0, round(shelf_life_model.predict(X_input)[0]))
    except:
        predicted_days = 0

    used_fallback = False
    if predicted_days < 3:
        predicted_days = rule_based_shelf_life(product_name)
        used_fallback = True

    expiry_date = manufacture_date + pd.to_timedelta(predicted_days, unit='d')

    try:
        country_label = country_clf.predict(X_input)[0]
        predicted_country = le_country.inverse_transform([country_label])[0]
    except:
        predicted_country = "Unknown"

    image_url = get_image_url(product_name)

    return {
        "product": product_name,
        "predicted_shelf_life_days": predicted_days,
        "predicted_expiry_date": expiry_date.strftime('%Y-%m-%d'),
        "predicted_country": predicted_country,
        "image_url": image_url,
        "used_fallback": used_fallback
    }

# Example usage
if __name__ == "__main__":
    products = [
        ("Nutella", "2025-04-08"),
        ("Coca Cola Zero", "2024-11-01"),
        ("Organic Greek Yogurt", "2025-01-15")
    ]

    for product_name, date_str in products:
        result = predict(product_name, date_str)
        print("\n--- Prediction ---")
        for k, v in result.items():
            print(f"{k}: {v}")
