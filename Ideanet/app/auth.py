from flask import Flask
from . import auth


def create_app():
    app = Flask(__name__)

   
    app.config["SECRET_KEY"] = "change-this-secret-key"

   
    auth.init_app(app)

    @app.route("/")
    def home():
        return """
        <h1>Welcome to Ideanet</h1>
        <p>You are logged in successfully!</p>
        <a href="/profile">Profile</a>
        <br><br>
        <form method="POST" action="/logout">
            <button type="submit">Logout</button>
        </form>
        """

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
