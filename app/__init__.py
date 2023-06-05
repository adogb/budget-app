from flask import Flask
app = Flask(__name__)

# import routes.py from app package (not the same as app variable)
from app import routes