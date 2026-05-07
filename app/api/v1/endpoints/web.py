import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["web"])

_PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)

templates = Jinja2Templates(directory=os.path.join(_PROJECT_ROOT, "views"))


@router.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/login")


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/pos", response_class=HTMLResponse, include_in_schema=False)
def pos_page(request: Request):
    return templates.TemplateResponse("pos/index.html", {"request": request})


@router.get("/menu/categories", response_class=HTMLResponse, include_in_schema=False)
def menu_categories_page(request: Request):
    return templates.TemplateResponse("menu/categories.html", {"request": request})


@router.get("/menu/products", response_class=HTMLResponse, include_in_schema=False)
def menu_products_page(request: Request):
    return templates.TemplateResponse("menu/products.html", {"request": request})


@router.get("/menu/products/{product_id}", response_class=HTMLResponse, include_in_schema=False)
def menu_product_detail_page(request: Request, product_id: int):
    return templates.TemplateResponse(
        "menu/product_detail.html", {"request": request, "product_id": product_id}
    )


@router.get("/menu/inventory", response_class=HTMLResponse, include_in_schema=False)
def menu_inventory_page(request: Request):
    return templates.TemplateResponse("menu/inventory.html", {"request": request})


@router.get("/orders/history", response_class=HTMLResponse, include_in_schema=False)
def orders_history_page(request: Request):
    return templates.TemplateResponse("orders/history.html", {"request": request})


@router.get("/inventory/purchases", response_class=HTMLResponse, include_in_schema=False)
def inventory_purchases_page(request: Request):
    return templates.TemplateResponse("inventory/purchases.html", {"request": request})


@router.get("/users", response_class=HTMLResponse, include_in_schema=False)
def users_page(request: Request):
    return templates.TemplateResponse("users/index.html", {"request": request})
