# Crawler Dockerfile
FROM python:3.9

WORKDIR /app

COPY crawler/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY crawler/ .

RUN apt-get update && apt-get install -y postgresql-client
COPY wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh
CMD ["/wait-for-it.sh", "db:5432", "--", "python", "generateDB.py"]

# RUN python generateDB.py

CMD ["sh", "-c", "python sentiment.py && python main.py"]