# ☕ Coffee Shop POS System — Project README
 
> هذا الملف هو المرجع الكامل للمشروع. اقرأه بالكامل قبل ما تكتب أي سطر كود.
> كل قرار معماري، كل جدول، كل صفحة — موثق هنا مع السبب.
 
---
 
## 🧠 فهم المشروع أولاً
 
### ما هو هذا المشروع؟
نظام متكامل لإدارة كوفي شوب، مكون من ثلاثة أجزاء رئيسية تعمل معاً:
 
1. **نقطة البيع (POS)** — شاشة الكاشير داخل المحل
2. **لوحة الإدارة (Dashboard)** — تحليلات، مصاريف، إنفنتوري، أرباح
3. **المتجر الإلكتروني** — الزبون يطلب أونلاين ويتوصله تأكيد على واتساب
### لمن هذا النظام؟
- **العميل الحالي:** كوفي شوب واحد (محل قهوة وحلويات)
- **النموذج التجاري:** كل عميل يحصل على نسخة مستقلة مثبتة عنده — **ليس SaaS**
- **الهدف المستقبلي:** بيع نسخ من النظام لكوفي شوبات أخرى
### التقنيات المستخدمة
| الطبقة | التقنية |
|--------|---------|
| Backend | Python + FastAPI |
| Frontend | HTML + CSS + Vanilla JS |
| Database | MySQL |
| WhatsApp | Evolution API v2 (مجانية + مفتوحة المصدر) |
| Architecture | REST API + Jinja2 Templates |
 
---
 
## 🗂️ هيكل الصفحات الكامل
 
### لوحة الإدارة (Admin Dashboard)
 
#### صفحة 1 — Dashboard التحليلات
**من يستخدمها:** المالك والمدير فقط
 
**محتوياتها:**
- إجمالي مبيعات اليوم (إيرادات + عدد الطلبات)
- رسم بياني شهري للمبيعات اليومية
- أوقات الذروة (الساعات الأكثر طلباً)
- أكثر 5 منتجات مبيعاً
- صافي الربح (إيرادات ناقص تكلفة المواد)
- تنبيهات المخزون (مواد قاربت على النفاد)
- مقارنة مع أمس / الأسبوع الماضي
#### صفحة 2 — نقطة البيع (POS)
**من يستخدمها:** الكاشير والمدير
 
**محتوياتها:**
- شبكة منتجات مع فلتر بالكاتيقوري وبحث سريع
- سلة الطلب (إضافة، حذف، تعديل الكمية)
- حقل اسم العميل ورقمه (اختياري)
- الإضافات (Modifiers) — سايز، نوع الحليب، السكر
- ملاحظات على الطلب (مثال: بدون سكر)
- طرق الدفع: كاش / بطاقة / تحويل
- طباعة الفاتورة (Thermal Printer + PDF)
**ما يحصل في الخلفية عند كل بيع:**
1. يُسجل الطلب في جدول `orders`
2. يُسجل كل منتج في `order_items` مع سعره وتكلفته وقت البيع
3. يُخصم مخزون المواد الخام تلقائياً حسب وصفة كل منتج
4. يُحسب الربح = سعر البيع - تكلفة المواد المستخدمة
#### صفحة 3 — المنتجات والكاتيقوري
**من يستخدمها:** المدير والمالك
 
**محتوياتها:**
- إدارة الكاتيقوري (إضافة، تعديل، ترتيب)
- إضافة منتج جديد: اسم، سعر، صورة، وصف، كاتيقوري
- **وصفة المنتج (Recipe):** ربط كل منتج بمواده الخام ومقاديرها
- الإضافات (Modifiers): مجموعات خيارات مثل السايز ونوع الحليب
- تفعيل/تعطيل منتج (يختفي من القائمة دون حذف)
- ترتيب العرض بالسحب والإفلات
**ملاحظة مهمة:** وصفة المنتج هي الرابط بين صفحة المنتجات وصفحة الإنفنتوري. بدونها لا يعمل خصم المخزون ولا حساب التكلفة الحقيقية.
 
#### صفحة 4 — الإنفنتوري والمصاريف
**من يستخدمها:** المدير والمالك
 
**محتوياتها:**
- قائمة المواد الخام (حليب، بن، سكر، كريمة...)
- تسجيل عمليات الشراء (كمية، سعر الوحدة، التاريخ)
- تتبع المخزون الحالي لكل مادة
- تحديد الحد الأدنى لكل مادة (يُطلق تنبيه عند الوصول له)
- تقرير استهلاك المواد (يومي / أسبوعي / شهري)
- تقرير المصاريف الكاملة
- تكلفة المنتج الواحد محسوبة تلقائياً من المواد
#### صفحات إضافية
- **الموظفون:** إضافة كاشير، تحديد الصلاحيات، سجل الدخول
- **سجل الطلبات:** كل الفواتير السابقة مع فلترة وإمكانية الاسترجاع
- **الإعدادات:** اسم المحل، الشعار، الضريبة، إعدادات الطابعة، العملة
### المتجر الإلكتروني
 
**ما يراه الزبون:**
- منيو أونلاين بتصميم جميل
- اختيار المنتجات وتخصيصها
- إدخال بياناته ورقم واتساب
- الدفع (كاش عند الاستلام أو بطاقة)
- تأكيد الطلب برسالة واتساب فورية
- رسالة ثانية عند تجهيز الطلب
**التكامل مع النظام:**
- الطلبات الأونلاين تظهر في نفس لوحة الإدارة
- تُخصم من نفس المخزون
- تُحسب في نفس تقارير الأرباح
- يُميزها `source = 'online'` في جدول الطلبات
---
 
## 🗄️ قاعدة البيانات (MySQL Schema)
 
### منطق التصميم
**قرار مهم:** كل نسخة من النظام لها قاعدة بيانات مستقلة. لا يوجد `tenant_id` لأن النظام ليس SaaS.
 
### المجموعة الأولى: القائمة والمنتجات
 
```sql
-- الكاتيقوري
CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    name_ar VARCHAR(100),
    sort_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
 
-- المنتجات
CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT NOT NULL,
    name VARCHAR(150) NOT NULL,
    name_ar VARCHAR(150),
    price DECIMAL(10,3) NOT NULL,
    cost_price DECIMAL(10,3) DEFAULT 0,  -- يُحسب من الوصفة
    description TEXT,
    image_url VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);
 
-- الإضافات (Modifiers) — مثال: سايز، نوع الحليب
CREATE TABLE product_modifiers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    group_name VARCHAR(100) NOT NULL,  -- مثال: "الحجم"
    option_name VARCHAR(100) NOT NULL, -- مثال: "كبير"
    extra_price DECIMAL(10,3) DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(id)
);
 
-- المواد الخام
CREATE TABLE raw_materials (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    unit VARCHAR(20) NOT NULL,         -- مثال: ml, g, piece
    current_stock DECIMAL(10,3) DEFAULT 0,
    min_stock_alert DECIMAL(10,3) DEFAULT 0,
    cost_per_unit DECIMAL(10,3) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
 
-- وصفة المنتج (الرابط بين المنتج والمواد الخام)
CREATE TABLE product_recipes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    raw_material_id INT NOT NULL,
    quantity_used DECIMAL(10,3) NOT NULL, -- الكمية المستخدمة لكل وحدة
    unit VARCHAR(20) NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (raw_material_id) REFERENCES raw_materials(id)
);
```
 
### المجموعة الثانية: المبيعات والإنفنتوري
 
```sql
-- الموظفون
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('owner', 'manager', 'cashier') NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
 
-- الطلبات
CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,              -- الكاشير الذي أخذ الطلب
    customer_name VARCHAR(100),
    customer_phone VARCHAR(20),
    total_amount DECIMAL(10,3) NOT NULL,  -- سعر البيع الكلي
    total_cost DECIMAL(10,3) DEFAULT 0,   -- تكلفة المواد وقت البيع
    profit DECIMAL(10,3) DEFAULT 0,       -- الربح الصافي
    payment_method ENUM('cash', 'card', 'transfer') NOT NULL,
    source ENUM('pos', 'online') DEFAULT 'pos',
    status ENUM('pending', 'preparing', 'ready', 'delivered', 'cancelled') DEFAULT 'pending',
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
 
-- تفاصيل الطلب
CREATE TABLE order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10,3) NOT NULL,    -- سعر البيع وقت الطلب
    unit_cost DECIMAL(10,3) DEFAULT 0,    -- التكلفة وقت الطلب
    modifiers_snapshot JSON,              -- نسخة محفوظة من الإضافات
    notes VARCHAR(255),
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
 
-- حركات المخزون (كل تغيير يُسجل)
CREATE TABLE inventory_movements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    raw_material_id INT NOT NULL,
    movement_type ENUM('purchase', 'sale_deduction', 'manual_adjustment', 'waste') NOT NULL,
    quantity DECIMAL(10,3) NOT NULL,      -- موجب = إضافة، سالب = خصم
    order_id INT,                         -- مرتبط بطلب إذا كان خصم بيع
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (raw_material_id) REFERENCES raw_materials(id),
    FOREIGN KEY (order_id) REFERENCES orders(id)
);
 
-- سجل المشتريات
CREATE TABLE purchases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    raw_material_id INT NOT NULL,
    user_id INT NOT NULL,
    quantity DECIMAL(10,3) NOT NULL,
    unit_cost DECIMAL(10,3) NOT NULL,
    total_cost DECIMAL(10,3) NOT NULL,
    purchased_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (raw_material_id) REFERENCES raw_materials(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```
 
### قرارات تصميمية مهمة — لا تتجاهلها
 
**1. حفظ التكلفة وقت البيع (`unit_cost` في `order_items`)**
- السبب: لو غيرت سعر المادة الخام لاحقاً، التقارير القديمة تظل صحيحة
- لا تحسب التكلفة بـ JOIN على وقت التقرير
**2. `modifiers_snapshot` كـ JSON**
- السبب: لو حذفت modifier قديم، الطلبات القديمة لا تتأثر
- احفظ نسخة كاملة من الإضافات مع كل طلب
**3. `inventory_movements` كجدول مستقل**
- السبب: تتبع كامل لكل حركة في المخزون
- يسمح بـ audit trail ومعرفة سبب كل تغيير
**4. `source` في `orders`**
- السبب: التمييز بين طلبات الـ POS والطلبات الأونلاين في التقارير
---
 
## 📋 خطة التنفيذ (Phases)
 
> **طريقة العمل:** ننجز كل مرحلة ونختبرها كاملاً قبل الانتقال للتالية.
> كل مرحلة لها نتيجة قابلة للاختبار ومحددة بوضوح.
 
---
 
### 🔵 المرحلة الأولى — الأساس والبنية التحتية
 
**الهدف:** نظام يعمل من الصفر مع قاعدة بيانات وصفحة POS كاملة.
 
**ما تبنيه:**
 
```
project/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── database.py          # MySQL connection + session
│   ├── models/
│   │   ├── category.py
│   │   ├── product.py
│   │   ├── raw_material.py
│   │   ├── product_recipe.py
│   │   ├── user.py
│   │   ├── order.py
│   │   └── order_item.py
│   ├── routers/
│   │   ├── auth.py          # login / logout
│   │   ├── categories.py    # CRUD
│   │   ├── products.py      # CRUD + recipe management
│   │   └── orders.py        # create order + auto inventory deduction
│   ├── services/
│   │   ├── inventory_service.py  # منطق خصم المخزون
│   │   └── order_service.py      # منطق حساب التكلفة والربح
│   └── templates/
│       ├── base.html
│       ├── login.html
│       └── pos/
│           └── index.html   # شاشة الكاشير
├── static/
│   ├── css/
│   └── js/
├── requirements.txt
└── README.md
```
 
**الـ Endpoints المطلوبة في هذه المرحلة:**
 
```
POST   /auth/login
POST   /auth/logout
 
GET    /api/categories
POST   /api/categories
PUT    /api/categories/{id}
DELETE /api/categories/{id}
 
GET    /api/products
GET    /api/products/{id}
POST   /api/products
PUT    /api/products/{id}
DELETE /api/products/{id}
POST   /api/products/{id}/recipe   # تحديث الوصفة
 
POST   /api/orders                 # إنشاء طلب جديد
GET    /api/orders/{id}
```
 
**منطق `POST /api/orders` — الأهم في هذه المرحلة:**
```
1. استقبل الطلب مع قائمة المنتجات والكميات
2. لكل منتج: اجلب وصفته من product_recipes
3. احسب unit_cost = مجموع (quantity_used × cost_per_unit) لكل مادة
4. اخصم الكميات من raw_materials.current_stock
5. سجل كل خصم في inventory_movements
6. احسب profit = total_amount - total_cost
7. احفظ الطلب
```
 
**نتيجة هذه المرحلة التي تختبرها:**
- [ ] تقدر تسجل دخول كاشير
- [ ] تقدر تضيف كاتيقوري ومنتجات
- [ ] تقدر تحدد وصفة لكل منتج
- [ ] شاشة POS تعرض المنتجات وتقدر تختار
- [ ] عند إنهاء الطلب: المخزون ينخصم تلقائياً والربح يُحسب
---
 
### 🟡 المرحلة الثانية — الإدارة والتحليلات
 
**الهدف:** لوحة الإدارة الكاملة مع التقارير والإنفنتوري.
 
**ما تبنيه:**
 
```
app/
├── routers/
│   ├── dashboard.py         # التحليلات
│   ├── inventory.py         # إدارة المخزون والمشتريات
│   └── users.py             # إدارة الموظفين
└── templates/
    ├── dashboard/
    │   └── index.html       # الداشبورد الرئيسي
    ├── inventory/
    │   ├── index.html       # قائمة المواد
    │   └── purchases.html   # سجل المشتريات
    ├── orders/
    │   └── history.html     # سجل الطلبات
    └── users/
        └── index.html       # إدارة الموظفين
```
 
**الـ Endpoints المطلوبة:**
 
```
GET  /api/dashboard/summary          # ?period=today|week|month
GET  /api/dashboard/sales-chart      # بيانات الرسم البياني
GET  /api/dashboard/top-products     # أكثر المنتجات مبيعاً
GET  /api/dashboard/peak-hours       # أوقات الذروة
GET  /api/dashboard/inventory-alerts # تنبيهات المخزون
 
GET  /api/inventory
POST /api/inventory/{id}/adjust      # تعديل يدوي
POST /api/purchases                  # تسجيل شراء جديد
GET  /api/purchases
 
GET  /api/orders                     # مع فلتر التاريخ والحالة
GET  /api/orders/{id}
PUT  /api/orders/{id}/status
 
POST /api/users
GET  /api/users
PUT  /api/users/{id}
```
 
**منطق الداشبورد — `GET /api/dashboard/summary`:**
```sql
-- الإيرادات
SELECT SUM(total_amount) as revenue,
       SUM(profit) as net_profit,
       COUNT(*) as orders_count,
       AVG(total_amount) as avg_order_value
FROM orders
WHERE DATE(created_at) = CURDATE()
  AND status != 'cancelled'
```
 
**نتيجة هذه المرحلة التي تختبرها:**
- [ ] الداشبورد يعرض أرقام اليوم بشكل صحيح
- [ ] الرسم البياني يعرض المبيعات الأسبوعية
- [ ] تقدر تسجل شراء مادة خام والمخزون يرتفع
- [ ] التنبيهات تظهر للمواد الناقصة
- [ ] سجل الطلبات يعمل مع الفلترة
- [ ] تقدر تضيف كاشير جديد وتحدد صلاحياته
---
 
### 🟢 المرحلة الثالثة — المتجر الإلكتروني وواتساب
 
**الهدف:** موقع الطلب الأونلاين مع تأكيد واتساب.
 
**ما تبنيه:**
 
```
app/
├── routers/
│   └── online_store.py      # API الموقع الإلكتروني
├── services/
│   └── whatsapp_service.py  # إرسال رسائل عبر Evolution API
└── templates/
    └── store/
        ├── index.html       # منيو الزبون
        ├── cart.html        # السلة والدفع
        └── confirmation.html # تأكيد الطلب
```
 
**الـ Endpoints المطلوبة:**
 
```
GET  /store                          # صفحة المنيو الأونلاين
GET  /api/store/menu                 # المنتجات النشطة للعرض
POST /api/store/orders               # طلب جديد من الموقع
GET  /api/store/orders/{id}/status   # تتبع الطلب
```
 
**منطق `POST /api/store/orders`:**
```
1. استقبل الطلب مع رقم واتساب الزبون
2. أنشئ الطلب مع source = 'online'
3. خصم المخزون (نفس منطق المرحلة الأولى)
4. أرسل رسالة واتساب: "تم استلام طلبك ✓ رقم الطلب: #123"
5. عند تغيير status إلى 'ready': أرسل رسالة ثانية: "طلبك جاهز ☕"
```
 
**إعداد Evolution API للواتساب:**
 
Evolution API هي أداة مجانية ومفتوحة المصدر تتيح إرسال واستقبال رسائل واتساب عبر HTTP API بسيط. تعمل عبر مكتبة Baileys (واتساب غير رسمي) أو WhatsApp Business API الرسمي.
 
**طريقة العمل في مشروعنا:**
 
```
1. Evolution API تُنصب على سيرفر منفصل (Docker)
2. مشروعنا يتواصل معها عبر HTTP requests
3. هي تتولى إرسال الرسائل للزبائن على واتساب
```
 
**الخطوات الأساسية للإعداد:**
 
الخطوة 1 — إنشاء Instance (مرة واحدة فقط عند الإعداد):
```python
import requests
 
EVOLUTION_URL = "https://your-evolution-server.com"
EVOLUTION_APIKEY = "your-global-apikey"
 
def create_instance():
    response = requests.post(
        f"{EVOLUTION_URL}/instance/create",
        headers={"apikey": EVOLUTION_APIKEY},
        json={
            "instanceName": "coffee-shop",
            "integration": "WHATSAPP-BAILEYS",
            "qrcode": True,
            "groupsIgnore": True
        }
    )
    return response.json()
    # بعدها تمسح QR Code وتربط الهاتف
```
 
الخطوة 2 — إرسال رسالة نصية:
```python
def send_whatsapp_message(phone: str, message: str):
    """
    phone: رقم الهاتف مع كود الدولة — مثال: 97333123456
    """
    response = requests.post(
        f"{EVOLUTION_URL}/message/sendText/coffee-shop",
        headers={"apikey": EVOLUTION_APIKEY},
        json={
            "number": phone,
            "text": message
        }
    )
    return response.json()
 
# مثال الاستخدام في مشروعنا:
def send_order_confirmation(phone: str, order_id: int):
    send_whatsapp_message(
        phone=phone,
        message=f"✅ تم استلام طلبك!\nرقم الطلب: #{order_id}\nسيتم إشعارك عند تجهيز الطلب ☕"
    )
 
def send_order_ready(phone: str, order_id: int):
    send_whatsapp_message(
        phone=phone,
        message=f"☕ طلبك جاهز!\nرقم الطلب: #{order_id}\nشكراً لك!"
    )
```
 
**متغيرات البيئة المطلوبة:**
```env
EVOLUTION_API_URL=https://your-evolution-server.com
EVOLUTION_API_KEY=your-apikey
EVOLUTION_INSTANCE_NAME=coffee-shop
```
 
**ملاحظات مهمة:**
- Evolution API تحتاج سيرفر منفصل — تُنصب عبر Docker
- بعد إنشاء الـ Instance لازم تمسح QR Code بهاتف واتساب المحل مرة واحدة
- الرقم يُكتب مع كود الدولة بدون + أو 00 — مثال البحرين: `97333123456`
- الـ Instance تبقى متصلة طالما الهاتف متصل بالإنترنت
**نتيجة هذه المرحلة التي تختبرها:**
- [ ] الموقع يعرض المنيو بشكل صحيح
- [ ] الزبون يقدر يطلب ويدفع
- [ ] رسالة واتساب تصل عند تأكيد الطلب
- [ ] رسالة ثانية تصل عند تجهيز الطلب
- [ ] الطلبات الأونلاين تظهر في لوحة الإدارة
- [ ] المخزون ينخصم من الطلبات الأونلاين أيضاً
---
 
## 🔐 نظام الصلاحيات
 
| الصفحة | مالك | مدير | كاشير |
|--------|------|------|-------|
| Dashboard التحليلات | ✅ | ✅ | ❌ |
| نقطة البيع | ✅ | ✅ | ✅ |
| المنتجات والكاتيقوري | ✅ | ✅ | ❌ |
| الإنفنتوري والمصاريف | ✅ | ✅ | ❌ |
| الموظفون | ✅ | ❌ | ❌ |
| سجل الطلبات | ✅ | ✅ | ✅ (طلباته فقط) |
| الإعدادات | ✅ | ❌ | ❌ |
| المتجر الإلكتروني | عام | عام | عام |
 
---
 
## ⚙️ متغيرات البيئة (.env)
 
```env
# Database
DB_HOST=localhost
DB_PORT=3306
DB_NAME=coffee_pos
DB_USER=root
DB_PASSWORD=your_password
 
# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=480
 
# Evolution API (WhatsApp)
EVOLUTION_API_URL=https://your-evolution-server.com
EVOLUTION_API_KEY=your-apikey
EVOLUTION_INSTANCE_NAME=coffee-shop
 
# App
APP_NAME=Coffee Shop POS
APP_CURRENCY=BHD
APP_TIMEZONE=Asia/Bahrain
```
 
---
 
## 📦 requirements.txt
 
```
fastapi
uvicorn[standard]
sqlalchemy
pymysql
python-jose[cryptography]
passlib[bcrypt]
python-multipart
jinja2
python-dotenv
requests
```
 
---
 
## 🚀 تشغيل المشروع
 
```bash
# تثبيت المتطلبات
pip install -r requirements.txt
 
# إنشاء قاعدة البيانات
mysql -u root -p < schema.sql
 
# تشغيل السيرفر
uvicorn app.main:app --reload --port 8000
```
 
---
 
## 📌 ملاحظات مهمة للـ AI
 
1. **لا تبدأ المرحلة الثانية قبل أن تكتمل الأولى وتُختبر**
2. **منطق خصم المخزون** يجب أن يكون في `inventory_service.py` — لا تكتبه مباشرة في الـ router
3. **التكلفة تُحسب وقت البيع** وتُخزن في قاعدة البيانات — لا تعيد حسابها من المواد الخام في التقارير
4. **كل تغيير في المخزون** يجب أن يمر عبر `inventory_movements` — لا تعدل `current_stock` مباشرة
5. **الكود العربي:** اسم المنتج يحفظ بالعربي والإنجليزي — استخدم `name` للإنجليزي و`name_ar` للعربي
6. **الصلاحيات** تُطبق عبر middleware في FastAPI — كل router يحدد الأدوار المسموحة
7. **العملة** البحرينية (BHD) — 3 خانات عشرية لذلك `DECIMAL(10,3)`
 