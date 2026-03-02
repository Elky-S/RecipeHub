# ==============================================================================
# קובץ routes/recipes.py - ניהול מתכונים, תמונות, דירוגים ומועדפים
# זהו הקובץ המרכזי שמטפל בכל הפעולות הקשורות למתכונים עצמם:
# יצירה, עריכה, מחיקה, שליפה, חיפוש, סינון, דירוג וניהול מועדפים.
# כמו כן, הוא מטפל בהעלאת תמונות ועיבודן.
# ==============================================================================
import os # לעבודה עם מערכת הקבצים (שמירה ומחיקה של תמונות)
import uuid # ליצירת מזהים ייחודיים (UUID) לשמות קבצי התמונות
import json # לעבודה עם נתונים בפורמט JSON (כמו רשימת רכיבים או נתיבי תמונות)
from PIL import Image, ImageFilter # ייבוא ספריית Pillow לעיבוד תמונות (שינוי גודל, פילטרים)
# current_app נחוץ כדי לגשת להגדרות השרת (כמו תיקיית ההעלאות) מתוך הבלופרינט
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity # כלים לאבטחת נתיבים וזיהוי המשתמש המחובר
from models import db, User, Recipe, IngredientEntry, Rating, Favorite # ייבוא המודלים לעבודה עם מסד הנתונים

# 1. הגדרת ה-Blueprint
# יצירת המודול 'recipes' שיאגד את כל הנתיבים בקובץ זה
recipe_bp = Blueprint('recipes', __name__)

# 2. פונקציות עזר (Helpers) -
# פונקציות פנימיות שמשמשות את הנתיבים בקובץ זה בלבד

def allowed_file(filename): # בודקת אם קובץ שהועלה הוא מסוג מותר (תמונה)
    # גישה להגדרות דרך current_app.config
    # בודק אם יש נקודה בשם הקובץ, ואם הסיומת (החלק אחרי הנקודה האחרונה) נמצאת ברשימת הסיומות המותרות שהוגדרה ב-app.py
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def calculate_rating_data(recipe): # מחשבת את ממוצע הדירוגים ומספר המדרגים עבור מתכון נתון
    if not recipe.ratings: return {'average': 0, 'count': 0} # אם אין דירוגים, החזר 0
    score_sum = sum(r.score for r in recipe.ratings) # סכום כל הדירוגים
    count = len(recipe.ratings) # מספר הדירוגים
    average = round(score_sum / count, 1) if count > 0 else 0 # חישוב ממוצע ועגול לספרה אחת אחרי הנקודה
    return {'average': average, 'count': count} # החזרת מילון עם הממוצע והכמות

def format_recipe_json(recipe, current_user=None): # הופכת אובייקט מתכון ממסד הנתונים למילון שניתן להחזיר כ-JSON ללקוח
    # יצירת רשימת מילונים עבור הרכיבים
    ingredients_data = [{'name': i.name, 'quantity': i.quantity, 'unit': i.unit} for i in recipe.ingredients]
    # המרת מחרוזת ה-JSON של נתיבי התמונות חזרה למילון פייתון (אם קיימת)
    images_dict = json.loads(recipe.image_paths_json) if recipe.image_paths_json else None
    # חישוב נתוני הדירוג
    rating_data = calculate_rating_data(recipe)
    # בדיקה אם המתכון נמצא במועדפים של המשתמש הנוכחי (אם יש כזה)
    is_favorite = False
    if current_user:
        # חיפוש רשומה בטבלת המועדפים שמקשרת בין המשתמש למתכון
        fav = Favorite.query.filter_by(user_id=current_user.id, recipe_id=recipe.id).first()
        if fav: is_favorite = True
    # בניית המילון הסופי שיוחזר ללקוח
    return {'id': recipe.id, 'title': recipe.title, 'category': recipe.category, 'images': images_dict, 'author': recipe.author.username, 'ingredients': ingredients_data, 'rating': rating_data, 'preparation_time': recipe.preparation_time, 'is_favorite': is_favorite}

# 3. נתיבי מתכונים (Routes) - שימי לב לשימוש ב-@recipe_bp

# קבלת כל המתכונים (כולל סינון ומיון)
@recipe_bp.route('/api/recipes', methods=['GET'])
@jwt_required(optional=True) # מאפשר גישה גם ללא טוקן, אבל אם יש טוקן, מזהה את המשתמש (כדי לבדוק מועדפים)
def get_all_recipes():
    current_username = get_jwt_identity() # קבלת שם המשתמש מהטוקן (אם קיים)
    current_user = User.query.filter_by(username=current_username).first() if current_username else None # שליפת אובייקט המשתמש
    # קבלת פרמטרים לסינון ומיון משורת הכתובת (Query Parameters)
    sort_by = request.args.get('sort')
    max_time = request.args.get('max_time')
    ingredient_filters_list = request.args.getlist('ingredient') # קבלת רשימה של רכיבים לסינון
    category_filter = request.args.get('category')

    query = Recipe.query # התחלת בניית שאילתה בסיסית לשליפת כל המתכונים

    # הוספת תנאי סינון לשאילתה בהתאם לפרמטרים שהתקבלו
    if max_time:
        try:
            query = query.filter(Recipe.preparation_time <= int(max_time)) # סינון לפי זמן הכנה מקסימלי
        except: pass
    if ingredient_filters_list:
        # סינון לפי רכיבים: עובר על כל רכיב ברשימה ומוסיף תנאי שבודק אם הוא קיים במתכון (יצירת תנאי "וגם")
        for ing_name in ingredient_filters_list:
            query = query.filter(Recipe.ingredients.any(IngredientEntry.name.ilike(f'%{ing_name}%'))) # ilike מאפשר חיפוש ללא תלות באותיות רישיות/קטנות
    if category_filter: query = query.filter(Recipe.category == category_filter) # סינון לפי קטגוריה

    recipes_list = query.all() # ביצוע השאילתה ושליפת התוצאות ממסד הנתונים
    # המרת כל מתכון לפורמט JSON בעזרת פונקציית העזר
    output = [format_recipe_json(r, current_user) for r in recipes_list]
    # מיון התוצאות בזיכרון אם התבקש מיון לפי דירוג
    if sort_by == 'rating': output.sort(key=lambda x: x['rating']['average'], reverse=True) # מיון יורד לפי ממוצע הדירוג
    return jsonify({'recipes': output}) # החזרת הרשימה הסופית כ-JSON

# קבלת מתכון בודד לפי מזהה (ID)
@recipe_bp.route('/api/recipes/<int:recipe_id>', methods=['GET'])
@jwt_required(optional=True) # גם כאן, זיהוי המשתמש הוא אופציונלי (לצורך הצגת סטטוס מועדף)
def get_recipe(recipe_id):
    current_username = get_jwt_identity()
    current_user = User.query.filter_by(username=current_username).first() if current_username else None
    recipe = Recipe.query.get_or_404(recipe_id) # שליפת המתכון לפי ID, או החזרת שגיאת 404 אם לא נמצא
    return jsonify(format_recipe_json(recipe, current_user)) # החזרת פרטי המתכון בפורמט JSON

# יצירת מתכון חדש
@recipe_bp.route('/api/recipes', methods=['POST'])
@jwt_required() # מחייב התחברות (טוקן תקין)
def create_recipe():
    current_user = User.query.filter_by(username=get_jwt_identity()).first() # זיהוי המשתמש היוצר
    # בדיקת הרשאות: רק משתמש מאושר או מנהל יכולים ליצור מתכון
    if not current_user.is_approved_uploader and current_user.role != 'Admin': return jsonify({'message': 'Permission denied.'}), 403
    # קבלת הנתונים מטופס ה-multipart/form-data
    title = request.form.get('title')
    instructions = request.form.get('instructions')
    preparation_time = request.form.get('preparation_time')
    ingredients_json = request.form.get('ingredients')
    category = request.form.get('category')
    # בדיקה שכל שדות החובה מולאו
    if not all([title, instructions, preparation_time, ingredients_json, category]): return jsonify({'message': 'Missing data.'}), 400

    saved_images_paths = {} # מילון לשמירת הנתיבים של התמונות שייווצרו
    # טיפול בהעלאת תמונה (אם נשלחה)
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            try:
                # שימוש ב-current_app.config כדי לקבל את נתיב תיקיית ההעלאות
                user_folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], str(current_user.id)) # יצירת נתיב לתיקייה אישית עבור המשתמש
                os.makedirs(user_folder_path, exist_ok=True) # יצירת התיקייה בפועל אם אינה קיימת
                # יצירת שמות קבצים ייחודיים לכל הגרסאות
                ext = file.filename.rsplit('.', 1)[1].lower(); unique_base = str(uuid.uuid4())
                original_fn = f"{unique_base}.{ext}" #שמירת המקורי
                bw_fn = f"bw_{unique_base}.{ext}" #השחור לבן
                thumb_fn = f"thumb_{unique_base}.{ext}" #המוקטנת
                blur_fn = f"blur_{unique_base}.{ext}" #המטושטשת

                img = Image.open(file) # טעינת התמונה לזיכרון באמצעות PIL- מודל לשימוש בתמונות
                # שמירת הגרסה המקורית
                img.save(os.path.join(user_folder_path, original_fn)); saved_images_paths['original'] = os.path.join(str(current_user.id), original_fn)
                # יצירה ושמירה של גרסת שחור-לבן
                img.convert('L').save(os.path.join(user_folder_path, bw_fn)); saved_images_paths['bw'] = os.path.join(str(current_user.id), bw_fn)
                # יצירה ושמירה של תמונה מוקטנת (Thumbnail)
                thumb=img.copy(); thumb.thumbnail((300,300)); thumb.save(os.path.join(user_folder_path, thumb_fn)); saved_images_paths['thumbnail'] = os.path.join(str(current_user.id), thumb_fn)
                # יצירה ושמירה של גרסה מטושטשת
                img.filter(ImageFilter.GaussianBlur(5)).save(os.path.join(user_folder_path, blur_fn)); saved_images_paths['blurred'] = os.path.join(str(current_user.id), blur_fn)
            except Exception as e: print(f"Image save error: {e}"); return jsonify({'message': 'Image error.'}), 400

    # עיבוד רשימת הרכיבים (שנשלחה כ-JSON בתוך הטופס)
    try: ingredients_objects = [IngredientEntry(name=i['name'], quantity=i['quantity'], unit=i['unit']) for i in json.loads(ingredients_json)]
    except: return jsonify({'message': 'Invalid ingredients.'}), 400
    # יצירת אובייקט המתכון החדש בזיכרון
    new_recipe = Recipe(title=title, instructions=instructions, preparation_time=preparation_time, image_paths_json=json.dumps(saved_images_paths) if saved_images_paths else None, author=current_user, ingredients=ingredients_objects, category=category)
    new_recipe.save() # שמירת המתכון והרכיבים במסד הנתונים
    return jsonify({'message': 'Recipe created!', 'recipe_id': new_recipe.id}), 201

# עריכת מתכון קיים
@recipe_bp.route('/api/recipes/<int:recipe_id>', methods=['PUT'])
@jwt_required()
def update_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id) # שליפת המתכון לעריכה
    current_user = User.query.filter_by(username=get_jwt_identity()).first()
    # בדיקת הרשאות: רק יוצר המתכון או מנהל יכולים לערוך
    if recipe.author != current_user and current_user.role != 'Admin': return jsonify({'message': 'Permission denied.'}), 403
    # קבלת הנתונים לעדכון (רק שדות שנשלחו יעודכנו)
    title = request.form.get('title'); instructions = request.form.get('instructions'); preparation_time = request.form.get('preparation_time'); ingredients_json = request.form.get('ingredients'); category = request.form.get('category')
    # עדכון השדות הפשוטים אם נשלחו ערכים חדשים
    if title: recipe.title = title
    if instructions: recipe.instructions = instructions
    if preparation_time: recipe.preparation_time = preparation_time
    if category: recipe.category = category
    # עדכון רשימת הרכיבים (אם נשלחה רשימה חדשה)
    if ingredients_json:
        try:
            IngredientEntry.query.filter_by(recipe_id=recipe.id).delete() # מחיקת כל הרכיבים הישנים
            # הוספת הרכיבים החדשים
            for ing_data in json.loads(ingredients_json): db.session.add(IngredientEntry(name=ing_data['name'], quantity=ing_data['quantity'], unit=ing_data['unit'], recipe=recipe))
        except: return jsonify({'message': 'Invalid new ingredients format.'}), 400
    # טיפול בהחלפת תמונה (אם נשלחה תמונה חדשה)
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            # מחיקת התמונות הישנות מהשרת
            if recipe.image_paths_json:
                try:
                    for filename in json.loads(recipe.image_paths_json).values():
                        fp = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                        if os.path.exists(fp): os.remove(fp)
                except: pass
            # תהליך שמירת התמונות החדשות ויצירת הווריאציות (זהה לתהליך ביצירה)
            try:
                user_folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], str(current_user.id))
                os.makedirs(user_folder_path, exist_ok=True)
                ext = file.filename.rsplit('.', 1)[1].lower(); unique_base = str(uuid.uuid4())
                original_fn = f"{unique_base}.{ext}"; bw_fn = f"bw_{unique_base}.{ext}"; thumb_fn = f"thumb_{unique_base}.{ext}"; blur_fn = f"blur_{unique_base}.{ext}"
                saved = {}; img = Image.open(file)
                img.save(os.path.join(user_folder_path, original_fn)); saved['original'] = os.path.join(str(current_user.id), original_fn)
                img.convert('L').save(os.path.join(user_folder_path, bw_fn)); saved['bw'] = os.path.join(str(current_user.id), bw_fn)
                thumb=img.copy(); thumb.thumbnail((300,300)); thumb.save(os.path.join(user_folder_path, thumb_fn)); saved['thumbnail'] = os.path.join(str(current_user.id), thumb_fn)
                img.filter(ImageFilter.GaussianBlur(5)).save(os.path.join(user_folder_path, blur_fn)); saved['blurred'] = os.path.join(str(current_user.id), blur_fn)
                recipe.image_paths_json = json.dumps(saved) # עדכון שדה נתיבי התמונות במתכון
            except Exception as e: print(f"Image save error: {e}"); return jsonify({'message': 'Image error.'}), 400
    db.session.commit() # שמירת כל השינויים במסד הנתונים
    return jsonify({'message': 'Recipe updated successfully!'}), 200

# מחיקת מתכון
@recipe_bp.route('/api/recipes/<int:recipe_id>', methods=['DELETE'])
@jwt_required()
def delete_recipe(recipe_id):
    current_user = User.query.filter_by(username=get_jwt_identity()).first()
    recipe = Recipe.query.get_or_404(recipe_id)
    # בדיקת הרשאות: רק יוצר המתכון או מנהל
    if recipe.author != current_user and current_user.role != 'Admin': return jsonify({'message': 'Permission denied.'}), 403
    # מחיקת קבצי התמונות מהשרת
    if recipe.image_paths_json:
        try:
            for filename in json.loads(recipe.image_paths_json).values():
                fp = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                if os.path.exists(fp): os.remove(fp)
        except: pass
    # מחיקת כל הנתונים הקשורים למתכון ממסד הנתונים (דירוגים, מועדפים, רכיבים)
    Rating.query.filter_by(recipe_id=recipe.id).delete()
    Favorite.query.filter_by(recipe_id=recipe.id).delete()
    IngredientEntry.query.filter_by(recipe_id=recipe.id).delete()
    db.session.delete(recipe) # מחיקת המתכון עצמו
    db.session.commit()
    return jsonify({'message': f'Recipe {recipe_id} deleted successfully.'}), 200

# הוספה או עדכון דירוג למתכון
@recipe_bp.route('/api/recipes/<int:recipe_id>/rate', methods=['POST'])
@jwt_required()
def rate_recipe(recipe_id):
    current_user = User.query.filter_by(username=get_jwt_identity()).first()
    recipe = Recipe.query.get_or_404(recipe_id)
    data = request.get_json() # קבלת הציון מה-JSON שנשלח
    if not data or 'score' not in data: return jsonify({'message': 'Missing score.'}), 400
    try: score = int(data['score']); assert 1 <= score <= 5 # וידוא שהציון הוא מספר שלם בין 1 ל-5
    except: return jsonify({'message': 'Score must be integer 1-5.'}), 400
    # בדיקה אם המשתמש כבר דירג את המתכון הזה בעבר
    existing = Rating.query.filter_by(user_id=current_user.id, recipe_id=recipe.id).first()
    if existing: existing.score = score; msg = 'Rating updated!' # אם כן, עדכון הציון הקיים
    else: db.session.add(Rating(score=score, user_id=current_user.id, recipe_id=recipe.id)); msg = 'Rating submitted!' # אם לא, יצירת דירוג חדש
    db.session.commit()
    return jsonify({'message': msg}), 200

# הוספה/הסרה ממועדפים (Toggle)
@recipe_bp.route('/api/recipes/<int:recipe_id>/favorite', methods=['POST'])
@jwt_required()
def toggle_favorite(recipe_id):
    current_user = User.query.filter_by(username=get_jwt_identity()).first()
    recipe = Recipe.query.get_or_404(recipe_id)
    # בדיקה אם המתכון כבר נמצא במועדפים של המשתמש
    existing = Favorite.query.filter_by(user_id=current_user.id, recipe_id=recipe.id).first()
    if existing:
        db.session.delete(existing); msg='Removed from favorites.'; is_fav=False # אם כן, הסרה מהמועדפים
    else:
        db.session.add(Favorite(user_id=current_user.id, recipe_id=recipe.id)); msg='Added to favorites!'; is_fav=True # אם לא, הוספה למועדפים
    db.session.commit()
    return jsonify({'message': msg, 'is_favorite': is_fav}), 200 # החזרת המצב החדש (האם מועדף או לא)

# קבלת רשימת המועדפים של המשתמש הנוכחי
@recipe_bp.route('/api/my-favorites', methods=['GET'])
@jwt_required()
def get_my_favorites():
    current_user = User.query.filter_by(username=get_jwt_identity()).first()
    # שליפת רשימת המועדפים דרך הקשר שהוגדר במודל User והמרתם לפורמט JSON
    output = [format_recipe_json(fav.recipe, current_user) for fav in current_user.favorites]
    return jsonify({'favorites': output})