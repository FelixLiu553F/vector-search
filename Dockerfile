FROM python:3.11.0

ENV TOKENIZERS_PARALLELISM=false

COPY requirements.txt ./

RUN pip install -r requirements.txt

WORKDIR /app

COPY ./ ./

RUN python setup.py

EXPOSE 8000

CMD ["python", "main.py"]