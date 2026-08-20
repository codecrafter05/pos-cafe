from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.templating import render

router = APIRouter(tags=["web"])


def render_protected(request: Request, name: str, context: dict | None = None):
    """Admin HTML pages. JWT is in localStorage, so auth is gated in <head>
    (auth-gate.js). Disable caching so a logged-out visit never shows a
    stale shell.
    """
    response = render(request, name, context)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response


@router.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/login")


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(request: Request):
    return render(request, "login.html")


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard_page(request: Request):
    return render_protected(request, "dashboard.html")


@router.get("/reports", response_class=HTMLResponse, include_in_schema=False)
def reports_page(request: Request):
    return render_protected(request, "reports/index.html")


@router.get("/pos", response_class=HTMLResponse, include_in_schema=False)
def pos_page(request: Request):
    return render_protected(request, "pos/index.html")


@router.get("/menu/categories", response_class=HTMLResponse, include_in_schema=False)
def menu_categories_page(request: Request):
    return render_protected(request, "menu/categories.html")


@router.get("/menu/products", response_class=HTMLResponse, include_in_schema=False)
def menu_products_page(request: Request):
    return render_protected(request, "menu/products.html")


@router.get("/menu/products/{product_id}", response_class=HTMLResponse, include_in_schema=False)
def menu_product_detail_page(request: Request, product_id: int):
    return render_protected(request, "menu/product_detail.html", {"product_id": product_id})


@router.get("/menu/inventory", response_class=HTMLResponse, include_in_schema=False)
def menu_inventory_page(request: Request):
    return render_protected(request, "menu/inventory.html")


@router.get("/orders/history", response_class=HTMLResponse, include_in_schema=False)
def orders_history_page(request: Request):
    return render_protected(request, "orders/history.html")


@router.get("/orders/{order_id}/receipt", response_class=HTMLResponse, include_in_schema=False)
def order_receipt_page(request: Request, order_id: int):
    return render_protected(request, "orders/receipt.html", {"order_id": order_id})


@router.get("/inventory/purchases", response_class=HTMLResponse, include_in_schema=False)
def inventory_purchases_page(request: Request):
    return render_protected(request, "inventory/purchases.html")


@router.get("/users", response_class=HTMLResponse, include_in_schema=False)
def users_page(request: Request):
    return render_protected(request, "users/index.html")


@router.get("/settings", response_class=HTMLResponse, include_in_schema=False)
def settings_page(request: Request):
    return render_protected(request, "settings/index.html")


@router.get("/store", response_class=HTMLResponse, include_in_schema=False)
def store_menu_page(request: Request):
    return render(request, "store/index.html")


@router.get("/store/cart", response_class=HTMLResponse, include_in_schema=False)
def store_cart_page(request: Request):
    return render(request, "store/cart.html")


@router.get("/store/confirmation", response_class=HTMLResponse, include_in_schema=False)
def store_confirmation_page(request: Request):
    return render(request, "store/confirmation.html")
