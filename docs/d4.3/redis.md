2️⃣ Running Redis Locally via Docker (Recommended)
Since Redis is lightweight, you can easily run it using Docker.

Steps:
Install Docker (if not already installed).

Run Redis in a container:

bash
Copy
Edit
docker run --name redis-dev -p 6379:6379 -d redis
Connect your FastAPI app to localhost:

python
Copy
Edit
redis_client = redis.Redis(host="localhost", port=6379, db=0)
Stop Redis when done:

bash
Copy
Edit
docker stop redis-dev && docker rm redis-dev
✅ Pros: Fully functional Redis instance.
❌ Cons: Requires Docker to be running.
---
🔧 1. From WSL (Ubuntu)
Redis is in the Docker container, so check it directly from WSL:

Option A: Use redis-cli (most direct)
Install if missing:

bash
Copy
Edit
sudo apt install redis-tools
Then:

bash
Copy
Edit
redis-cli ping
Expected output:

text
Copy
Edit
PONG
If Redis is running on the default port (6379), this should just work. If not, try:

bash
Copy
Edit
redis-cli -h 127.0.0.1 -p 6379 ping
---
Option B: Use curl for a basic TCP check (not ideal for Redis)
Redis is not an HTTP server, but you can send a raw Redis protocol command using curl with netcat or a raw TCP client, though it’s hacky:

bash
Copy
Edit
(echo -en '*1\r\n$4\r\nPING\r\n'; sleep 1) | nc 127.0.0.1 6379
Expected response:

diff
Copy
Edit
+PONG

