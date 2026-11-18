FROM docker-mirror.liara.ir/library/python:3.12-slim
WORKDIR /app

COPY services/network_analyzer/requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY services/network_analyzer/src/ /app/
COPY services/network_analyzer/tests/ /app/tests/
COPY utils/ /app/utils/
CMD ["python", "main.py"]
