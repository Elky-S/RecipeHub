# RecipeHub 🍳

RecipeHub is a professional Python Backend API for managing and sharing recipes. Built with Flask, it features secure user authentication and image processing capabilities.

## ✨ Features
* **Secure Authentication:** User login and registration using **JWT (JSON Web Tokens)**.
* **Recipe CRUD:** Full support for creating, reading, updating, and deleting recipes.
* **Image Processing:** Automatic generation of thumbnails, grayscale (BW), and blurred versions of recipe photos.
* **Database Management:** Structured data handling with SQLAlchemy models.

## 🛠️ Tech Stack
* **Framework:** Flask
* **Authentication:** Flask-JWT-Extended
* **Database:** SQLite & SQLAlchemy
* **Security:** Bcrypt for password hashing
* **Environment:** Python 3.x

## 🚀 Getting Started

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Elky-S/RecipeHub.git
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the server:
   ```bash
   python app.py
   ```

## 📂Project Structure
/routes - API endpoints (Auth, Recipes, General).
/static/images - Uploaded and processed recipe images.
models.py - Database schema and User/Recipe models.
app.py - Main application entry point and configuration.

## 🔒 Security Note
This project uses `python-dotenv` to manage sensitive information. 
- **JWT Secret Key:** Stored in a local `.env` file (not uploaded to GitHub) to prevent unauthorized token synthesis.
- **Debug Mode:** Hardcoded for development; should be disabled or managed via environment variables in a production environment.
