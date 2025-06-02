FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

RUN pip3 install torch --index-url https://download.pytorch.org/whl/cpu
COPY . . 

CMD ["python", "main.py"]