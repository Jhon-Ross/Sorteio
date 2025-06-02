# Vercel entry point
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Importa o app principal
from app import app

# Vercel expects this
app = app 