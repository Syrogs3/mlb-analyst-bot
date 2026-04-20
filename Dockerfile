FROM python:3.12-slim

WORKDIR /app

# Copiar requirements primero (mejor cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Comando para ejecutar el bot
CMD ["python", "main.py"]