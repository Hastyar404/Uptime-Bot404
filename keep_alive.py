from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

# Starts the Flask app in a separate thread to keep the host alive

def run():
    app.run(host='0.0.0.0', port=8080)

# Call this before running your manager bot

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
