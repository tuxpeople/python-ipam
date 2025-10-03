"""IPAM Application Entry Point."""

from dotenv import load_dotenv

from ipam import create_app

load_dotenv()

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
