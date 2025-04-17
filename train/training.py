import os
import joblib
import pandas as pd
import numpy as np

from sklearn.linear_model import Ridge
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

from scipy.sparse import hstack, csr_matrix

# Settings
DATA_PATH = "C:/Users/cedri/Downloads/en.openfoodfacts.org.products.csv"
MODEL_DIR = "C:/Users/cedri/Downloads/"
os.makedirs(MODEL_DIR, exist_ok=True)

# Load dataset
df = pd.read_csv(DATA_PATH)

# --- Preprocessing ---
df = df[df['shelf_life_days'].notna()]
df = df[df['shelf_life_days'] > 0]

text_features = df[['product_name', 'categories']].fillna('').agg(" ".join, axis=1)
nutritional_cols = [
    'energy-kcal_100g', 'fat_100g', 'saturated-fat_100g',
    'carbohydrates_100g', 'sugars_100g', 'fiber_100g',
    'proteins_100g', 'salt_100g'
]
df[nutritional_cols] = df[nutritional_cols].fillna(0)

# --- Feature extraction ---
tfidf = TfidfVectorizer(max_features=500)
X_text = tfidf.fit_transform(text_features)

scaler = StandardScaler()
X_numeric = scaler.fit_transform(df[nutritional_cols])

X = hstack([X_text, csr_matrix(X_numeric)])
y = df['shelf_life_days'].values

# --- Train/test split ---
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# --- Train model ---
model = Ridge(alpha=1.0)
model.fit(X_train, y_train)

# --- Evaluate ---
y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
print(f"📏 Mean Absolute Error on test set: {mae:.2f} days")

# --- Save models ---
joblib.dump(tfidf, os.path.join(MODEL_DIR, "ridge_tfidf.pkl"))
joblib.dump(scaler, os.path.join(MODEL_DIR, "ridge_scaler.pkl"))
joblib.dump(model, os.path.join(MODEL_DIR, "ridge_shelf_life_model.pkl"))
print("✅ Models saved to:", MODEL_DIR)