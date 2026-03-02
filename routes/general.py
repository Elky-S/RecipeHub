# ==============================================================================
# קובץ routes/general.py - נתיבים כלליים וניהול
# קובץ זה מאגד נתיבים שלא שייכים ישירות למתכונים או להרשמה,
# כולל נתיבי בדיקה, קבלת פרטי משתמש, ופעולות ניהול (Admin).
# ==============================================================================
from flask import Blueprint, jsonify # ייבוא כלים ליצירת הבלופרינט ולהחזרת תשובות JSON
from flask_jwt_extended import jwt_required, get_jwt_identity # כלים לאבטחת נתיבים (דורש טוקן) וזיהוי המשתמש המחובר
from models import db, User # ייבוא הגישה למסד הנתונים ומודל המשתמש

# 1. הגדרת ה-Blueprint
# יצירת מודול בשם 'general' שיכיל את הנתיבים הללו
general_bp = Blueprint('general', __name__)

# 2. נתיבים כלליים

# נתיב השורש (Root Route) - הכתובת הראשית של האתר (/)
@general_bp.route('/')
def hello():
    # מחזיר הודעת טקסט פשוטה. שימושי כדי לבדוק מהר שהשרת עובד ומגיב.
    return "Hello! The Server is MODULAR and organized with Blueprints!"

# קבלת פרטי החשבון של המשתמש המחובר
@general_bp.route('/api/account', methods=['GET'])
@jwt_required() # דורש שהמשתמש יהיה מחובר (ישלח טוקן בבקשה)
def get_account_info():
    # שליפת אובייקט המשתמש המלא ממסד הנתונים לפי שם המשתמש שנמצא בטוקן
    u = User.query.filter_by(username=get_jwt_identity()).first()
    # החזרת הפרטים החשובים של המשתמש בפורמט JSON (כולל תפקיד וסטטוס אישור)
    return jsonify({'id': u.id, 'username': u.username, 'role': u.role, 'is_approved': u.is_approved_uploader}), 200

# נתיב לאישור משתמש להעלאת תוכן (Admin בלבד)
# מקבל את ה-ID של המשתמש שאותו רוצים לאשר כחלק מהכתובת
@general_bp.route('/api/users/<int:user_id>/approve', methods=['PUT'])
@jwt_required() # דורש התחברות
def approve_user_as_uploader(user_id):
    # זיהוי המשתמש שמבצע את הבקשה (זה ששלח את הטוקן)
    current_user = User.query.filter_by(username=get_jwt_identity()).first()
    # בדיקת אבטחה: רק אם המשתמש המבצע הוא מנהל ('Admin') מותר לו להמשיך
    if current_user.role != 'Admin': return jsonify({'message': 'Admin only.'}), 403
    # שליפת המשתמש שאותו רוצים לאשר לפי ה-ID שהתקבל בכתובת (מחזיר 404 אם לא נמצא)
    target_user = User.query.get_or_404(user_id)
    target_user.is_approved_uploader = True # שינוי הדגל 'is_approved_uploader' של המשתמש ל-True (מאושר)
    db.session.commit() # שמירת השינוי במסד הנתונים
    return jsonify({'message': f'User {target_user.username} approved.'}), 200

# דלת אחורית זמנית (אפשר למחוק אם לא צריך)
# נתיב עזר לפיתוח: הופך את המשתמש הנוכחי לאדמין ומאשר אותו בלחיצת כפתור
@general_bp.route('/api/make_me_admin', methods=['GET'])
@jwt_required() # דורש התחברות
def make_me_admin_temp():
    u = User.query.filter_by(username=get_jwt_identity()).first() # שליפת המשתמש הנוכחי
    # עדכון התפקיד לאדמין ואישור העלאה בשורה אחת, ושמירה מיידית
    u.role = 'Admin'; u.is_approved_uploader = True; db.session.commit()
    return jsonify({'message': f'{u.username} is now Admin.'}), 200 # החזרת הודעת הצלחה