from starlette.concurrency import run_in_threadpool
from fastapi import APIRouter, Request, Form, UploadFile, File, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from app.utils.predictor import ProductPredictor
from app.utils.models import save_prediction, Product
from app.utils.database import get_db 
import pandas as pd
from io import BytesIO
from datetime import datetime
from sqlalchemy.orm import Session
from typing import List


# Initialize
router = APIRouter()
predictor = ProductPredictor()
templates = Jinja2Templates(directory="app/templates")


# --- Helper: Default context for template rendering ---
def default_context(request, message=None):
    return {
        "request": request,
        "message": message,
        "product": None,
        "manufacturing_date": None,
        "expiry_date": None,
        "shelf_life": None,
        "predicted_country": None,
        "days_left": None,
        "image_url": None
    }


# --- Route: Homepage Form ---
@router.get("/", response_class=HTMLResponse)
async def render_homepage(request: Request):
    return templates.TemplateResponse("home.html", default_context(request))


# --- Route: Handle Single Form Submission ---
@router.post("/single-input/", response_class=HTMLResponse)
async def submit_form(
    request: Request,
    product: str = Form(...),
    manufacturing_date: str = Form(...),
    db: Session = Depends(get_db)
):
    result = predictor.predict_and_display(product, manufacturing_date, include_image=True)
    manufacturing_date_obj = datetime.strptime(manufacturing_date, "%Y-%m-%d")

    if "error" in result:
        return templates.TemplateResponse("home.html", {
            **default_context(request, result["error"]),
            "product": product,
            "manufacturing_date": manufacturing_date
        })

    # Save prediction to the database
    save_prediction(
        db=db,
        product=result["product"],
        predicted_country=result["predicted_country"],
        manufacturing_date=manufacturing_date_obj,
        predicted_shelf_life_days=result["predicted_shelf_life_days"],
        predicted_expiry_date=result["predicted_expiry_date"],
        days_left=result["days_left"]
    )

    return templates.TemplateResponse("home.html", {
        "request": request,
        "product": result["product"],
        "manufacturing_date": manufacturing_date_obj.strftime('%B %d, %Y'),
        "expiry_date": result["predicted_expiry_date"],
        "shelf_life": result["predicted_shelf_life_days"],
        "days_left": result["days_left"],
        "predicted_country": result["predicted_country"],
        "image_url": result["image_url"],
        "show_modal": True
    })


# --- Route: Handle Bulk Excel Upload ---
@router.post("/bulk-upload/", response_class=HTMLResponse)
async def upload_excel(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        contents = await file.read()

        # Offload processing to thread
        results, message = await run_in_threadpool(process_bulk_upload, contents, db, predictor)

        if results is None:
            return templates.TemplateResponse("home.html", default_context(request, message))

        return templates.TemplateResponse("bulk_results.html", {
            "request": request,
            "results": results,
            "message": message
        })

    except Exception as e:
        return templates.TemplateResponse("home.html", default_context(
            request, f"Error processing file: {e}")
        )

def process_bulk_upload(contents: bytes, db: Session, predictor: ProductPredictor):
    df = pd.read_excel(BytesIO(contents))
    df.columns = df.columns.str.strip().str.lower()

    if not {"product", "manufacturing_date"}.issubset(df.columns):
        return None, "Excel must contain 'product' and 'manufacturing_date' columns."

    results = []
    invalid_rows = []

    for i, (_, row) in enumerate(df.iterrows()):
        product = row.get("product")
        date = row.get("manufacturing_date")

        if pd.isna(product) or pd.isna(date):
            invalid_rows.append(i + 2)
            continue

        prediction = predictor.predict_and_display(product, date, include_image=False)

        if "error" in prediction:
            invalid_rows.append(i + 2)
            continue

        if isinstance(date, pd.Timestamp):
            prediction["manufacturing_date"] = date.strftime('%B %d, %Y')

        save_prediction(
            db=db,
            product=prediction["product"],
            predicted_country=prediction["predicted_country"],
            manufacturing_date=date,
            predicted_shelf_life_days=prediction["predicted_shelf_life_days"],
            predicted_expiry_date=prediction["predicted_expiry_date"],
            days_left=prediction["days_left"]
        )

        results.append(prediction)

    message = None
    if invalid_rows:
        message = (
            f"{len(invalid_rows)} row(s) were skipped due to missing or invalid data "
            f"(Excel row numbers: {invalid_rows})."
        )

    return results, message


@router.get("/view-history")
def view_history(request: Request, db: Session = Depends(get_db)):
    products = db.query(Product).all()

    result = []
    for product in products:
        result.append({
            "id": product.id,
            "product": product.product,
            "predicted_country": product.predicted_country,
            "manufacturing_date": product.manufacturing_date,
            "predicted_shelf_life_days": product.predicted_shelf_life_days,
            "predicted_expiry_date": product.predicted_expiry_date,
            "days_left": product.days_left,
        })

    result = sorted(result, key=lambda x: x["days_left"])

    return templates.TemplateResponse("history.html", {
        "request": request,
        "products": result
    })

@router.post("/delete-product/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product:
        db.delete(product)
        db.commit()
    return RedirectResponse(url="/view-history", status_code=303)

@router.post("/handle-products")
def handle_products(
    product_ids: List[int] = Form([]),  # Default to empty list
    action: str = Form(...),
    db: Session = Depends(get_db)
):
    if not product_ids:
        return RedirectResponse(url="/view-history?message=No+products+selected", status_code=303)

    if action == "delete":
        for pid in product_ids:
            product = db.query(Product).filter(Product.id == pid).first()
            if product:
                db.delete(product)
        db.commit()
        return RedirectResponse(url="/view-history", status_code=303)

    elif action == "download":
        # Query selected products
        products = db.query(Product).filter(Product.id.in_(product_ids)).all()

        # Convert to DataFrame
        data = [{
            "Product": p.product,
            "Country of Origin": p.predicted_country,
            "Manufacturing Date": p.manufacturing_date,
            "Shelf Life (days)": p.predicted_shelf_life_days,
            "Expiry Date": p.predicted_expiry_date,
            "Days Left": p.days_left
        } for p in products]
        
        df = pd.DataFrame(data)

        # Save to in-memory Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name="Selected Products")
        output.seek(0)

        return StreamingResponse(
            output,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={"Content-Disposition": "attachment; filename=selected_products.xlsx"}
        )

    return RedirectResponse(url="/view-history", status_code=303)
