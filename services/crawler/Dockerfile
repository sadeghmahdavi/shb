FROM docker-mirror.liara.ir/library/python:3.12-slim
WORKDIR /app
COPY services/crawler/requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt
COPY services/crawler/src/ /app/
COPY services/crawler/tests/ /app/tests/
COPY utils/ /app/utils/
CMD ["python", "main.py"]
