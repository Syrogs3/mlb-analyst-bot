FROM python:3.12-slim

WORKDIR /app

# Copiar requirements primero
COPY requirements.txt .

# Instalar solo lo necesario (más rápido)
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Eliminar archivos innecesarios para reducir tamaño
RUN rm -rf __pycache__ .git venv .env

CMD ["python", "main.py"]