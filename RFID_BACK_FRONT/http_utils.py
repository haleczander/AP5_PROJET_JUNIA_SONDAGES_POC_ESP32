HEADERS = {
    200: b"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n",
    400: b"HTTP/1.0 400 Bad Request\r\nContent-Type: text/plain\r\n\r\n",
    403: b"HTTP/1.0 403 Forbidden\r\nContent-Type: text/plain\r\n\r\n",
    404: b"HTTP/1.0 404 Not Found\r\nContent-Type: text/plain\r\n\r\n"
}

def response(connection, code=200, content=None):
    header = HEADERS.get(code, HEADERS[400])
    connection.send(header)
        
    if content:
        if isinstance(content, str):
            content = content.encode()
        connection.send(content)

def parse_request(conn):
    req = b""
    while True:
        part = conn.recv(1024)
        if not part:
            break
        req += part
        if b"\r\n\r\n" in req:
            break

    headers, _, body = req.partition(b"\r\n\r\n")
    headers = headers.decode().split("\r\n")
    method, path, _ = headers[0].split(" ")

    content_length = 0
    for h in headers[1:]:
        if h.lower().startswith("content-length"):
            content_length = int(h.split(":")[1].strip())
            break

    # Lire le reste du body si incomplet
    while len(body) < content_length:
        body += conn.recv(content_length - len(body))

    body = body.decode() if body else None
    return method, path, body
