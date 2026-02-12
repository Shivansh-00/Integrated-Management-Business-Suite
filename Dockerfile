FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir frappe-bench || true
EXPOSE 8000
CMD ["bash", "-lc", "python -m http.server 8000"]
