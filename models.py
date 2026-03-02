# =================================================================
# קובץ המודלים (models.py) - סופי + קטגוריות + מועדפים
# זהו הקובץ שמגדיר את מבנה מסד הנתונים שלנו (הטבלאות והקשרים ביניהן)
# =================================================================
from flask_sqlalchemy import SQLAlchemy # ייבוא ספריית ORM שמאפשרת עבודה נוחה עם מסד הנתונים דרך קוד פייתון
from sqlalchemy.ext.declarative import declared_attr # ייבוא כלי עזר להגדרת תכונות במודל בסיס (כמו שם הטבלה)
from flask_bcrypt import Bcrypt # ייבוא ספרייה המשמשת להצפנה בטוחה של סיסמאות משתמשים

db = SQLAlchemy() # יצירת האובייקט הראשי של מסד הנתונים. דרכו נבצע את כל השמירות והשליפות
bcrypt = Bcrypt() # יצירת אובייקט ההצפנה. נשתמש בו כדי להצפין סיסמאות לפני שמירתן ב-DB


# ====================
# מודל הבסיס (BaseModel)
# זוהי מחלקה ששאר המודלים יירשו ממנה, כדי לא לכתוב קוד כפול
# ====================
class BaseModel(db.Model):
    __abstract__ = True # הגדרה שזוהי מחלקה מופשטת - לא תיווצר עבורה טבלה ממשית במסד הנתונים

    @declared_attr # דקורטור שמאפשר לקבוע את שם הטבלה באופן דינמי במחלקות היורשות
    def __tablename__(cls): # פונקציה שקובעת את שם הטבלה במסד הנתונים
        return cls.__name__.lower() # שם הטבלה יהיה זהה לשם המחלקה, אך באותיות קטנות (למשל, User יהפוך ל-user)

    id = db.Column(db.Integer, primary_key=True) # הגדרת עמודת מזהה ייחודי (Primary Key) מסוג מספר שלם לכל טבלה שתרש מכאן

    def save(self): # פונקציית עזר לשמירת האובייקט הנוכחי במסד הנתונים
        db.session.add(self) # הוספת האובייקט לרשימת ההמתנה לשמירה (Session)
        db.session.commit() # ביצוע השמירה בפועל למסד הנתונים (Commit)
        #COMMIT - מתרגם למסד SQL את הנתונים-
        # ושם בודקים שהכל עונה על ההגדרות ואז דוחפים- ובעצם הכל נשמר, אחרת נזרקת שגיאה


# ====================
# מודל משתמש (User)
# מגדיר את טבלת המשתמשים במערכת
# ====================
class User(BaseModel): # יורש מ-BaseModel, ולכן מקבל אוטומטית שדה id ופונקציית save
    username = db.Column(db.String(50), unique=True, nullable=False) # עמודת שם משתמש: טקסט עד 50 תווים, חייב להיות ייחודי, לא יכול להיות ריק
    email = db.Column(db.String(120), unique=True, nullable=False) # עמודת אימייל: טקסט עד 120 תווים, ייחודי, לא ריק
    password = db.Column(db.String(128), nullable=False) # עמודת סיסמה: תשמור את ההאש המוצפן של הסיסמה (טקסט ארוך), לא ריק
    role = db.Column(db.String(20), nullable=False, default='Reader') # עמודת תפקיד: טקסט קצר, ברירת המחדל היא 'Reader' (קורא בלבד)
    is_approved_uploader = db.Column(db.Boolean, default=False) # דגל בוליאני (אמת/שקר): האם המשתמש מאושר להעלות תוכן. ברירת מחדל: לא מאושר
    # קשר למתכונים שהמשתמש יצר
    recipes = db.relationship('Recipe', backref='author', lazy=True) # הגדרת קשר "אחד-לרבים": משתמש אחד יוצר הרבה מתכונים. backref יוצר תכונה 'author' אצל המתכון
    # --- חדש! קשר למועדפים ---
    # מאפשר לגשת לכל המתכונים שהמשתמש סימן בלב דרך user.favorites
    favorites = db.relationship('Favorite', backref='user', lazy=True) # הגדרת קשר לטבלת המועדפים. מאפשר לשלוף בקלות את כל המועדפים של משתמש זה

    def set_password(self, password_text): # פונקציה שמקבלת סיסמה גלויה ומצפינה אות
        self.password = bcrypt.generate_password_hash(password_text).decode('utf-8') # יצירת האש (Hash) של הסיסמה ושמירתו בשדה password

    def check_password(self, password_text): # פונקציה לבדיקת סיסמה בעת התחברות
        return bcrypt.check_password_hash(self.password, password_text) # השוואה בין הסיסמה שהוזנה כעת לבין ההאש השמור ב-DB. מחזיר אמת/שקר

    def __repr__(self): return f'<User {self.username}>' # מגדיר איך האובייקט יוצג כטקסט (למשל בהדפסה ללוגים)


# ====================
# מודל מתכון (Recipe)
# מגדיר את טבלת המתכונים
# ====================
class Recipe(BaseModel): # יורש מ-BaseModel (מקבל id ו-save)
    title = db.Column(db.String(100), nullable=False) # כותרת המתכון: טקסט עד 100 תווים, חובה
    instructions = db.Column(db.Text, nullable=False) # הוראות הכנה: טקסט ארוך ללא הגבלה קשיחה, חובה
    preparation_time = db.Column(db.Integer, nullable=False) # זמן הכנה בדקות: מספר שלם, חובה
    image_paths_json = db.Column(db.Text, nullable=True) # נתיבי תמונות: טקסט ארוך שיכיל מבנה JSON של מיקומי הקבצים, יכול להיות ריק

    # --- חדש! שדה קטגוריה ---
    # ברירת מחדל 'General' למקרה שלא הוזן כלום
    category = db.Column(db.String(50), nullable=False, default='General') # קטגוריה: טקסט קצר, עם ברירת מחדל 'General'

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # מפתח זר (Foreign Key): מקשר את המתכון לטבלת המשתמשים (user.id). מצביע על יוצר המתכון.
    ingredients = db.relationship('IngredientEntry', backref='recipe', lazy=True) # קשר "אחד-לרבים": מתכון אחד מכיל הרבה שורות רכיבים
    ratings = db.relationship('Rating', backref='recipe', lazy=True) # קשר "אחד-לרבים": מתכון אחד יכול לקבל הרבה דירוגים
    # --- חדש! קשר למי שסימן את המתכון כמועדף ---
    favorited_by = db.relationship('Favorite', backref='recipe', lazy=True) # קשר "רבים-לרבים" (דרך טבלת ביניים): מאפשר לראות מי המשתמשים שסימנו את המתכון הזה

    def __repr__(self): return f'<Recipe {self.title}>' # תצוגת טקסט של המתכון


# ====================
# מודל שורת רכיב (IngredientEntry)
# מגדיר את טבלת הרכיבים (כל שורה היא רכיב בודד במתכון)
# ====================
class IngredientEntry(BaseModel): # יורש מ-BaseModel
    name = db.Column(db.String(50), nullable=False) # שם הרכיב: טקסט, חובה (למשל "קמח")
    quantity = db.Column(db.Float, nullable=False) # כמות: מספר עשרוני (Float), חובה (למשל 2.5)
    unit = db.Column(db.String(20), nullable=False) # יחידת מידה: טקסט קצר, חובה (למשל "כוסות")
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False) # מפתח זר: מקשר את הרכיב למתכון הספציפי שאליו הוא שייך

    def __repr__(self): return f'<Ingredient {self.name}>' # תצוגת טקסט של הרכיב


# ====================
# מודל דירוג (Rating)
# טבלה ששומרת מי דירג איזה מתכון ובכמה כוכבים
# ====================
class Rating(BaseModel): # יורש מ-BaseModel
    score = db.Column(db.Integer, nullable=False) # הציון: מספר שלם (למשל 1-5), חובה
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # מפתח זר: המשתמש שנתן את הדירוג
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False) # מפתח זר: המתכון שדורג
    __table_args__ = (db.UniqueConstraint('user_id', 'recipe_id', name='_user_recipe_rating_uc'),) # אילוץ ייחודיות: מונע ממשתמש אחד לדרג את אותו מתכון יותר מפעם אחת

    def __repr__(self): return f'<Rating {self.score}>' # תצוגת טקסט של הדירוג


# ====================
# מודל מועדפים (Favorite) - חדש!
# טבלת קישור ששומרת איזה משתמש סימן איזה מתכון ב"לב"
# ====================
class Favorite(BaseModel): # יורש מ-BaseModel
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # מפתח זר: המשתמש שסימן כמועדף
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False) # מפתח זר: המתכון שסומן

    # מגבלה: אי אפשר לסמן את אותו מתכון פעמיים כמועדף לאותו משתמש
    __table_args__ = (db.UniqueConstraint('user_id', 'recipe_id', name='_user_recipe_fav_uc'),) # אילוץ ייחודיות למניעת כפילויות

    def __repr__(self): # תצוגת טקסט של רשומת המועדף
        return f'<Favorite User:{self.user_id} Recipe:{self.recipe_id}>'