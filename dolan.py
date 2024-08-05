from fasthtml import FastHTML

app = FastHTML()

@app.get("/")
def home():
    return "<h1>Hello, World</h1>"