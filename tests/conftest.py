import pytest

from app import create_app
from app.extensions import db
from app.models import Usuario
from app.seed import seed_data


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )
    with app.app_context():
        db.create_all()
        seed_data()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email=None, senha="aluno123"):
    if email is None:
        with client.application.app_context():
            email = Usuario.query.filter_by(perfil="aluno").first().email
    return client.post("/login", data={"email": email, "senha": senha}, follow_redirects=True)


def login_admin(client):
    with client.application.app_context():
        email = Usuario.query.filter_by(perfil="administrador").first().email
    return login(client, email=email, senha="admin123")
