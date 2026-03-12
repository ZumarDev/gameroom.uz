# 🎮 GameRoom.uz - O'yinxona Boshqaruv Tizimi

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12+-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.1.1-green?style=for-the-badge&logo=flask)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.x-purple?style=for-the-badge&logo=bootstrap)
![SQLite](https://img.shields.io/badge/SQLite-3-lightblue?style=for-the-badge&logo=sqlite)

**O'zbekistondagi o'yinxonalar uchun to'liq boshqaruv tizimi**

🇺🇿 O'zbekcha • 🇷🇺 Ruscha • 🇬🇧 Inglizcha

[O'rnatish](#-ornatish) • [Xususiyatlar](#-xususiyatlar) • [Skrinshot](#-skrinshot)

</div>

---

## 📋 Loyiha Haqida

**GameRoom.uz** - bu o'yinxona (gaming center) egalariga o'z bizneslarini samarali boshqarish imkonini beruvchi web ilova. Seanslarni avtomatik hisoblash, xonalar bandligini kuzatish, mahsulot sotuvlari va zaxirani tartibga solish hamda daromad hisobotlarini ko'rish uchun yaratilgan.

### 🎯 Kimlar Uchun?

- 🏢 O'yinxona egalari
- 👨‍💼 O'yinxona menejerlari
- 🎮 Gaming center operatorlari
- 💼 Kichik va o'rta biznes egalari

---

## ✨ Xususiyatlar

### 🌐 Ko'p Tillilik (i18n)
- **O'zbek tili** (🇺🇿) - to'liq qo'llab-quvvatlanadi
- **Rus tili** (🇷🇺) - to'liq qo'llab-quvvatlanadi
- **Ingliz tili** (🇬🇧) - to'liq qo'llab-quvvatlanadi
- PDF hisobotlar ham barcha tillarda

### 🏠 Xonalar Boshqaruvi
- Xonalar va kategoriyalarni yaratish
- Har bir kategoriya uchun narx belgilash (30 daqiqalik)
- Xonaga individual narx qo'yish imkoniyati
- Xonalar holatini real vaqtda kuzatish

### ⏱️ Seanslar Boshqaruvi
- **Belgilangan vaqt** - oldindan vaqt yoki summa kiritish
- **VIP rejim** - cheksiz o'yin, vaqt bo'yicha hisoblash
- Real vaqtda taymer va narx ko'rsatkich
- Bir nechta xonani bir vaqtda ochish
- Seansni to'xtatishda hisob-kitob tanlash (to'liq/haqiqiy vaqt)

### 🛒 Mahsulotlar va Inventar
- Mahsulotlar katalogi (ichimliklar, gazaklar, snacklar)
- Kategoriyalar bo'yicha guruhlash
- Zaxira (stock) boshqaruvi
- Avtomatik zaxira kamaytirish
- Kam qolgan mahsulotlar haqida ogohlantirish

### 📊 Hisobotlar va Analitika
- Kunlik/Haftalik/Oylik daromad hisobotlari
- Maxsus sana oralig'i bo'yicha hisobot
- Eng ko'p daromad keltiradigan xonalar
- Eng ko'p sotiladigan mahsulotlar
- **PDF formatida hisobot** (barcha tillarda)

### 👤 Foydalanuvchi Boshqaruvi
- Ko'p foydalanuvchilik (Multi-tenant)
- Xavfsiz autentifikatsiya
- Parolni tiklash funksiyasi
- Profil sozlamalari
- O'z logosini yuklash imkoniyati

### 🎨 Interfeys
- Zamonaviy professional qorong'i tema
- Mobil qurilmalarga moslashgan (responsive)
- 3 tilda interfeys (UZ/RU/EN)
- Real vaqtda yangilanish

---

## 🛠️ Texnologiyalar

| Texnologiya | Versiya | Maqsad |
|-------------|---------|--------|
| **Python** | 3.12+ | Backend dasturlash tili |
| **Flask** | 3.1.1 | Web framework |
| **SQLAlchemy** | 2.x | ORM (ma'lumotlar bazasi) |
| **SQLite** | 3 | Ma'lumotlar bazasi |
| **Flask-Login** | 0.6+ | Autentifikatsiya |
| **Bootstrap** | 5.x | CSS framework |
| **ReportLab** | 4.x | PDF yaratish |
| **Gunicorn** | 23.x | Production server |

---

## 🚀 O'rnatish

### Talablar
- Python 3.12 yoki undan yuqori
- pip (Python paket menejeri)
- Git

### 1. Loyihani yuklab olish

```bash
git clone https://github.com/ZumarDev/gameroom.uz.git
cd gameroom.uz
```

### 2. Ishga tushirish

```bash
# Birinchi marta ishga tushirish (avtomatik o'rnatish)
chmod +x start.sh
./start.sh

# Production rejimida (Gunicorn)
./start.sh prod
```

### 3. Brauzerda ochish

```
http://localhost:3000
```

### 4. Kirish (Login)

- Login sahifa: `/login`
- Login qilgandan keyin admin panel (dashboard) ochiladi: `/dashboard`

### 5. Ro'yxatdan o'tish / foydalanuvchi qo'shish

GameRoom.uz da ro'yxatdan o'tish **default holatda ochiq emas** (login sahifada ham link chiqmaydi). Yangi akkauntlarni faqat admin (superadmin) panel orqali yaratish tavsiya qilinadi.

#### ✅ 4.1 Birinchi superadminni yaratish (bootstrap)
1. `.env` ga vaqtincha quyidagini qo'shing:
   - `ALLOW_PUBLIC_REGISTRATION=true`
2. Brauzerda `/register` sahifasiga kiring
3. Foydalanuvchi nomi, parol, o'yinxona nomini kiriting
4. Admin kalitini kiriting (`SECRET_ADMIN_KEY`, standart: `gameroom2026`)
5. Ro'yxatdan o'tgandan keyin `.env` ni qayta sozlang:
   - `SUPERADMIN_USERS=<sizning_username>` (masalan: `SUPERADMIN_USERS=admin`)
   - `ALLOW_PUBLIC_REGISTRATION=false`
6. Ilovani qayta ishga tushiring

#### ✅ 4.2 Yangi foydalanuvchi qo'shish (faqat admin panel orqali)
1. Superadmin bo'lib login qiling
2. Profil menyusidan **"Ro’yxatdan o’tish"** bandini tanlang yoki to'g'ridan-to'g'ri oching:
   - `/admin/users/new`
3. Yangi foydalanuvchi ma'lumotlarini kiriting va saqlang

---

## 📁 Loyiha Strukturasi

```
gameroom.uz/
├── app.py              # Flask ilovasi va konfiguratsiya
├── models.py           # SQLAlchemy modellari
├── views.py            # Route'lar va controller'lar
├── forms.py            # WTForms formalar
├── translations.py     # Ko'p tillilik (UZ/RU/EN)
├── start.sh            # Ishga tushirish scripti
├── requirements.txt    # Python paketlar
├── static/
│   ├── css/
│   │   ├── custom.css      # Asosiy stillar
│   │   └── enhanced.css    # Qo'shimcha stillar
│   ├── js/
│   │   ├── timer.js        # Taymer funksiyalari
│   │   ├── dashboard.js    # Dashboard JS
│   │   └── filters.js      # Filter funksiyalari
│   └── uploads/            # Yuklangan fayllar (logolar)
└── templates/
    ├── base.html           # Asosiy shablon
    ├── dashboard.html      # Bosh sahifa
    ├── sessions.html       # Seanslar
    ├── rooms_management.html
    ├── products.html
    ├── inventory.html
    ├── analytics.html
    └── ...
```

---

## 🔐 Xavfsizlik

- ✅ Parollar hash qilinadi (Werkzeug)
- ✅ CSRF himoyasi (WTForms)
- ✅ Session boshqaruvi (Flask-Login)
- ✅ Multi-tenant izolyatsiya
- ✅ Input validatsiya
- ✅ Xavfsiz fayl yuklash

---

## ⚙️ Konfiguratsiya

### Muhit o'zgaruvchilari (.env)

| O'zgaruvchi | Tavsif | Standart |
|-------------|--------|----------|
| `SESSION_SECRET` | Flask session kaliti | Avtomatik yaratiladi |
| `SECRET_ADMIN_KEY` | Admin ro'yxatdan o'tish kaliti | `gameroom2026` |
| `DATABASE_URL` | Ma'lumotlar bazasi URL | `sqlite:///gaming_center.db` |
| `SUPERADMIN_USERS` | Superadmin username'lar (vergul bilan) | *(bo'sh bo'lsa: id=1 superadmin)* |
| `ALLOW_PUBLIC_REGISTRATION` | `/register` ni vaqtincha yoqish/o'chirish | `false` |
| `LOG_LEVEL` | Log darajasi (`INFO`, `DEBUG` va h.k.) | `INFO` |

---

## 📈 Rivojlantirish Yo'nalishi

- [x] ✅ Ko'p tillilik (UZ/RU/EN)
- [x] ✅ PDF hisobotlar
- [x] ✅ Logo yuklash
- [ ] 💳 Payme/Click integratsiyasi
- [ ] 📱 PWA (Progressive Web App)
- [ ] 🤖 Telegram bot integratsiyasi
- [ ] 👥 Mijozlar bazasi
- [ ] 🎁 Bonus/chegirma tizimi

---

## 🤝 Hissa Qo'shish

1. Loyihani fork qiling
2. Yangi branch yarating (`git checkout -b feature/amazing-feature`)
3. O'zgarishlarni commit qiling (`git commit -m 'Add amazing feature'`)
4. Branch'ni push qiling (`git push origin feature/amazing-feature`)
5. Pull Request yarating

---

## 📄 Litsenziya

Bu loyiha MIT litsenziyasi ostida tarqatiladi.

---

## 📞 Aloqa

- **GitHub**: [@ZumarDev](https://github.com/ZumarDev)
- **Telegram**: [@gameroom_uz](https://t.me/gameroom_uz)

---

<div align="center">

**O'zbekistonda ishlab chiqilgan 🇺🇿**

⭐ Agar loyiha yoqqan bo'lsa, yulduzcha qo'ying!

</div>
