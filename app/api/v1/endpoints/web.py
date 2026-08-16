from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.templating import render

router = APIRouter(tags=["web"])


@router.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/login")


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(request: Request):
    return render(request, "login.html")


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard_page(request: Request):
    return render(request, "dashboard.html")


@router.get("/reports", response_class=HTMLResponse, include_in_schema=False)
def reports_page(request: Request):
    return render(request, "reports/index.html")


@router.get("/pos", response_class=HTMLResponse, include_in_schema=False)
def pos_page(request: Request):
    return render(request, "pos/index.html")


@router.get("/menu/categories", response_class=HTMLResponse, include_in_schema=False)
def menu_categories_page(request: Request):
    return render(request, "menu/categories.html")


@router.get("/menu/products", response_class=HTMLResponse, include_in_schema=False)
def menu_products_page(request: Request):
    return render(request, "menu/products.html")


@router.get("/menu/products/{product_id}", response_class=HTMLResponse, include_in_schema=False)
def menu_product_detail_page(request: Request, product_id: int):
    return render(request, "menu/product_detail.html", {"product_id": product_id})


@router.get("/menu/inventory", response_class=HTMLResponse, include_in_schema=False)
def menu_inventory_page(request: Request):
    return render(request, "menu/inventory.html")


@router.get("/orders/history", response_class=HTMLResponse, include_in_schema=False)
def orders_history_page(request: Request):
    return render(request, "orders/history.html")


@router.get("/orders/{order_id}/receipt", response_class=HTMLResponse, include_in_schema=False)
def order_receipt_page(request: Request, order_id: int):
    return render(request, "orders/receipt.html", {"order_id": order_id})


@router.get("/inventory/purchases", response_class=HTMLResponse, include_in_schema=False)
def inventory_purchases_page(request: Request):
    return render(request, "inventory/purchases.html")


@router.get("/users", response_class=HTMLResponse, include_in_schema=False)
def users_page(request: Request):
    return render(request, "users/index.html")


@router.get("/settings", response_class=HTMLResponse, include_in_schema=False)
def settings_page(request: Request):
    return render(request, "settings/index.html")


@router.get("/store", response_class=HTMLResponse, include_in_schema=False)
def store_menu_page(request: Request):
    return render(request, "store/index.html")


@router.get("/store/cart", response_class=HTMLResponse, include_in_schema=False)
def store_cart_page(request: Request):
    return render(request, "store/cart.html")


@router.get("/store/confirmation", response_class=HTMLResponse, include_in_schema=False)
def store_confirmation_page(request: Request):
    return render(request, "store/confirmation.html")
