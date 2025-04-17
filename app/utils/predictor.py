import pandas as pd
import numpy as np
from scipy.sparse import hstack, csr_matrix
import joblib
from pathlib import Path
from datetime import datetime
from app.utils.image_search import get_image_from_duckduckgo
from app.utils.lookup import lookup_country_from_web
from app.utils.lookup import lookup_shelf_life_from_web
from app.utils.lookup import rule_based_shelf_life
import warnings
warnings.filterwarnings("ignore")

class ProductPredictor:
    def __init__(self):
        self.BASE_DIR = Path(__file__).resolve().parent.parent
        self.expiration_model = joblib.load(self.BASE_DIR / "ridge_shelf_life_model.pkl")
        self.expiration_tfidf = joblib.load(self.BASE_DIR / "ridge_tfidf.pkl")
        self.expiration_scaler = joblib.load(self.BASE_DIR / "ridge_scaler.pkl")
        #self.country_model = joblib.load(self.BASE_DIR / "xgb_country_model.pkl")
        self.country_model = joblib.load(self.BASE_DIR / "country_model_stacked.pkl")
        self.country_le = joblib.load(self.BASE_DIR / "label_encoder_country_f.pkl")
        try:
            self.product_image_df = pd.read_csv(self.BASE_DIR / "products_with_images.csv")
        except:
            self.product_image_df = pd.DataFrame(columns=["product_name", "image_url"])

    def _prepare_features(self, product_name):
        input_text = f"{product_name} {product_name.lower()}"
        X_text = self.expiration_tfidf.transform([input_text])
        X_numeric = self.expiration_scaler.transform([np.zeros(8)])
        return hstack([X_text, csr_matrix(X_numeric)])

    def predict_shelf_life(self, product_name, manufacture_date_str):
        try:
            manufacture_date = pd.to_datetime(manufacture_date_str)
            if manufacture_date > datetime.now():
                raise ValueError("Manufacturing date cannot be in the future.")
        except ValueError as e:
            return {"error": str(e)}

        used_fallback = False

        # Predict with model
        try:
            X_input = self._prepare_features(product_name)
            predicted_days = max(0, round(self.expiration_model.predict(X_input)[0]))
        except Exception as e:
            print(f"Model prediction failed: {e}")
            predicted_days = 0
            #used_fallback = True

        final_days = predicted_days
        expiry_date = manufacture_date + pd.to_timedelta(final_days, unit='d')
        days_left = (expiry_date - datetime.now()).days if expiry_date else None

        return final_days, expiry_date, days_left

    def _normalize_country_name(self, country):
        country = country.strip().lower()
        if country in ["usa", "us"]:
            return "United States"
        elif country in ["uk", "england", "britain"]:
            return "United Kingdom"
        else:
            return country.title()

    def predict_country(self, product_name):
        web_country = lookup_country_from_web(product_name, f"{product_name} official site")
        if web_country:
            return self._normalize_country_name(web_country)

        X_input = self._prepare_features(product_name)
        try:
            country_label = self.country_model.predict(X_input)[0]
            predicted = self.country_le.inverse_transform([country_label])[0].capitalize()
            return self._normalize_country_name(predicted)
        except:
            return "Unknown"

    def get_image_url(self, product_name):
        match = self.product_image_df[
            self.product_image_df['product_name'].str.contains(product_name, case=False, na=False)
        ].head(1)

        if not match.empty and 'image_url' in match.columns:
            image_url = match.iloc[0]['image_url']
            if pd.notna(image_url) and image_url.strip() != '':
                return image_url

        return get_image_from_duckduckgo(product_name)

    def predict_and_display(self, product_name, manufacture_date_str, include_image=True):
        shelf_life_result = self.predict_shelf_life(product_name, manufacture_date_str)

        if isinstance(shelf_life_result, dict) and "error" in shelf_life_result:
            return {"error": shelf_life_result["error"]}

        shelf_life, expiry_date, days_left = shelf_life_result

        predicted_country = self.predict_country(product_name)
        image_url = self.get_image_url(product_name) if include_image else None

        return {
            "product": product_name,
            "predicted_shelf_life_days": shelf_life,
            "predicted_expiry_date": expiry_date.strftime('%B %d, %Y'),
            "days_left": days_left,
            "predicted_country": predicted_country,
            "image_url": image_url
        }
