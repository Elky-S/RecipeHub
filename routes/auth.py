# ==============================================================================
# קובץ routes/auth.py - טיפול בהזדהות משתמשים
# קובץ זה מכיל את כל הנתיבים (End-points) הקשורים להרשמה, התחברות ויצירת טוקנים.
# ==============================================================================
from flask import Blueprint, request, jsonify # ייבוא כלים של פלאסק: Blueprint (ליצירת מודול), request (לקבלת מידע מהלקוח), jsonify (להחזרת תשובות בפורמט JSON)
from flask_jwt_extended import create_access_token # ייבוא פונקציה ליצירת טוקן גישה מאובטח (JWT) לאחר התחברות מוצלחת
# אנו מייבאים את המודלים מקובץ models.py שנמצא בתיקייה מעל
# הנקודה האחת (.) לפני models מציינת שמדובר בייבוא יחסי מהתיקייה שמעל התיקייה הנוכחית
from models import db, User, bcrypt # ייבוא אובייקט מסד הנתונים, מודל המשתמש, וכלי ההצפנה

# 1. הגדרת ה-Blueprint
# יצירת "תוכנית מתאר" (Blueprint) בשם 'auth'. זהו המיכל שיחזיק את כל הנתיבים בקובץ זה.
auth_bp = Blueprint('auth', __name__)

# 2. נתיבים (Routes) - שימי לב לשימוש ב-@auth_bp
# במקום להשתמש ב-@app.route (כמו בקובץ ראשי), אנו משתמשים ב-@auth_bp.route כדי לשייך את הנתיב למודול הזה.

@auth_bp.route('/api/login', methods=['POST']) # הגדרת נתיב להתחברות. מקבל רק בקשות מסוג POST.
def login(): # הפונקציה שמטפלת בבקשת ההתחברות
    data = request.get_json() # חילוץ נתוני ה-JSON שנשלחו בגוף הבקשה (אמור להכיל username ו-password)
    # בדיקת תקינות בסיסית: האם התקבל מידע והאם השדות הנדרשים קיימים
    if not data or 'username' not in data or 'password' not in data: return jsonify({'message': 'Missing username or password'}), 400 # החזרת שגיאה 400 (Bad Request) אם חסר מידע
    user = User.query.filter_by(username=data['username']).first() # חיפוש משתמש במסד הנתונים לפי שם המשתמש שהתקבל. מחזיר את המשתמש או None.
    # בדיקה כפולה: האם המשתמש נמצא ב-DB, *וגם* האם הסיסמה שהוזנה תואמת להאש המוצפן ב-DB (באמצעות הפונקציה במודל User)
    if user and user.check_password(data['password']):
        access_token = create_access_token(identity=user.username) # אם ההזדהות הצליחה: יצירת טוקן גישה (JWT) המכיל את שם המשתמש (ה"זהות")
        # החזרת תשובת הצלחה (200) בפורמט JSON, הכוללת את הטוקן החדש ופרטי המשתמש
        return jsonify({'message': 'Login successful!', 'access_token': access_token, 'username': user.username, 'role': user.role}), 200
    else: return jsonify({'message': 'Invalid username or password'}), 401 # אם המשתמש לא נמצא או הסיסמה שגויה: החזרת שגיאת 401 (Unauthorized - לא מורשה)

@auth_bp.route('/api/register', methods=['POST']) # הגדרת נתיב להרשמה. מקבל בקשות POST.
def register(): # הפונקציה שמטפלת בבקשת ההרשמה
    data = request.get_json() # קבלת פרטי המשתמש החדש (שם, אימייל, סיסמה) מתוך ה-JSON שנשלח
    new_user = User(username=data['username'], email=data['email']) # יצירת מופע חדש של מחלקת User בזיכרון (עדיין לא נשמר ב-DB), עם השם והאימייל
    new_user.set_password(data['password']) # קריאה לפונקציה במודל שמצפינה את הסיסמה ושומרת את ההאש באובייקט המשתמש
    try: new_user.save() # בלוק ניסיון (try): מנסה לשמור את המשתמש החדש במסד הנתונים (באמצעות פונקציית העזר ב-BaseModel)
    # אם השמירה נכשלה (לרוב בגלל ששם המשתמש או האימייל כבר קיימים במסד הנתונים ומוגדרים כ-unique), נכנסים לבלוק הטיפול בשגיאה (except)
    except: return jsonify({'message': 'User or Email exists'}), 400 # החזרת שגיאת 400 אם המשתמש כבר קיים
    # אם השמירה הצליחה, החזרת הודעת הצלחה עם סטטוס 201 (Created - נוצר)
    return jsonify({'message': 'User created successfully!', 'username': new_user.username}), 201