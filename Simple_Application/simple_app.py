from flask import Flask

# Create a server instance
app = Flask(__name__)

@app.route('/')
def index():
    return "Hello Pankaj!!!"

# Run the server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)