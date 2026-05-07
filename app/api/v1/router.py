from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    categories,
    dashboard,
    health,
    inventory,
    orders,
    products,
    purchases,
    raw_materials,
    users,
)

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(categories.router)
router.include_router(products.router)
router.include_router(raw_materials.router)
router.include_router(dashboard.router)
router.include_router(inventory.router)
router.include_router(purchases.router)
router.include_router(orders.router)
router.include_router(users.router)
