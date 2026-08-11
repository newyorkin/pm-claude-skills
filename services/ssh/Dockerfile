FROM python:3.13-alpine

RUN apk add --no-cache openssh-client

WORKDIR /app
RUN pip install --no-cache-dir fastmcp
COPY server.py .
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["python", "server.py"]
