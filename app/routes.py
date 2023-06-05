from app import app # second app is the variable defined in app\__init__.py

@app.route('/')
def index():
    return "Hello, World!"