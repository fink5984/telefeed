# README - Telefeed Multi-Account System

## 🚀 מערכת ניהול חשבונות טלגרם עם UI

מערכת מתקדמת לניהול מספר חשבונות טלגרם, כל אחד עם routing משלו.

## 📦 התקנה

```bash
pip install -r requirements.txt
```

## 🎯 שימוש

### 1. הרצת Web UI לניהול חשבונות

```bash
python web_ui.py
```

פתח דפדפן: http://localhost:5000

### 2. הוספת חשבונות

דרך ה-UI:
- לחץ "הוסף חשבון חדש"
- מלא פרטי API (מ-my.telegram.org)
- בחר סוג: משתמש או בוט
- לחץ "שמור"

### 3. התחברות לחשבון

- לחץ "התחבר" ליד החשבון
- הזן קוד אימות שנשלח לטלגרם
- החשבון יישמר אוטומטית

### 4. הגדרת Routes

- לחץ "עריכת Routes" ליד החשבון
- ערוך קובץ YAML:

```yaml
routes:
  - source: -1001234567890  # ערוץ מקור
    dest: -1009876543210    # ערוץ יעד
    filters:
      keywords: ["חשוב", "דחוף"]
      min_length: 10
      only_media: false
```

### 5. הרצת המערכת

```bash
python telefeed_multi.py
```

## 🎨 תכונות

✅ ניהול ריבוי חשבונות
✅ UI אינטואיטיבי
✅ התחברות מאובטחת
✅ Routes נפרדים לכל חשבון
✅ Reload אוטומטי של Routes
✅ הפעלה/כיבוי חשבונות
✅ תמיכה בבוטים ומשתמשים

## 📂 מבנה קבצים

```
telefeed/
├── web_ui.py              # Web UI
├── telefeed_multi.py      # מערכת ריבוי חשבונות
├── accounts_manager.py    # מנהל חשבונות
├── telefeed.py            # גרסה ישנה (חשבון יחיד)
├── templates/             # תבניות HTML
│   ├── index.html
│   ├── add_account.html
│   ├── login.html
│   └── edit_routes.html
└── accounts/              # נתוני חשבונות (לא ב-git)
    ├── accounts.json
    └── [account]_routes.yaml
```

## 🔒 אבטחה

- קבצי session לא מועלים ל-git
- תיקיית accounts/ מוגנת ב-.gitignore
- שימוש ב-session_string מומלץ ל-production

## 🚢 Deploy ל-Railway

1. העלה את הקוד ל-GitHub
2. צור פרויקט ב-Railway מה-repo
3. הוסף משתנה סביבה: `PORT=5000`
4. ה-UI יהיה זמין ב-URL של Railway
5. נהל חשבונות דרך הדפדפן

## ⚙️ הגדרות

משתני סביבה:
- `ROUTES_RELOAD_EVERY=5` - שניות לבדיקת שינויים ב-routes

## 📝 דוגמת Routes

```yaml
routes:
  # העברה פשוטה
  - source: -1001234567890
    dest: -1009876543210
  
  # עם מסננים
  - source: "@channel_name"
    dest: -1009876543210
    filters:
      keywords: ["bitcoin", "crypto"]
      min_length: 50
      only_media: false
  
  # מדיה בלבד
  - source: -1001234567890
    dest: -1009876543210
    filters:
      only_media: true
```

## 🆘 תמיכה

בעיות? פתח issue ב-GitHub!
