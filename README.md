# Insta Clone

Loyihani ishga tushirish uchun Python 3.12 yoki undan yangi versiyasi kerak. Barcha buyruqlarni `manage.py` turgan papkada bajaring.

## 1. Virtual muhit yarating

macOS / Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

## 2. Kutubxonalarni o'rnating

```bash
pip install -r requirements.txt
```

## 3. `.env` faylini tayyorlang

`.env.example` fayli nomidan `.example` qismini olib tashlang, shunda fayl nomi `.env` bo'ladi.

macOS / Linux:

```bash
mv .env.example .env
```

Windows:

```bash
ren .env.example .env
```

Keyin `.env` faylini oching va ichiga o'z ma'lumotlaringizni yozing:

| O'zgaruvchi | Nima yoziladi |
| --- | --- |
| `SECRET_KEY` | O'zingizning maxfiy kalitingiz (albatta o'zgartiring) |
| `DEBUG` | Kompyuteringizda ishlatganda `True` |
| `ALLOWED_HOSTS` | Sayt ochiladigan manzillar, vergul bilan ajratiladi |
| `DB_NAME` | SQLite baza fayli nomi |
| `LANGUAGE_CODE` | Til kodi, masalan `en-us` |
| `TIME_ZONE` | Vaqt mintaqasi, masalan `Asia/Tashkent` |

`SECRET_KEY` dan boshqa qiymatlarni shundayligicha qoldirsangiz ham bo'ladi.

Yangi `SECRET_KEY` yaratish uchun:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Chiqqan natijani bittalik qo'shtirnoq ichida yozing:

```
SECRET_KEY='shu-yerga-kalitingiz'
```

## 4. Bazani tayyorlang

```bash
python manage.py migrate
```

## 5. Serverni ishga tushiring

```bash
python manage.py runserver
```

Brauzerda http://127.0.0.1:8000/ manzilini oching. Akkauntingiz bo'lmasa, http://127.0.0.1:8000/register/ sahifasida ro'yxatdan o'ting.

## Admin panel

Admin panelga kirish uchun avval admin foydalanuvchi yarating:

```bash
python manage.py createsuperuser
```

Keyin http://127.0.0.1:8000/admin/ manzilini oching.
