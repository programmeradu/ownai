"""Test the authentication."""
import os
import pytest
from flask import g, session

from backaind.auth import (
    add_user,
    is_password_correct,
    set_password,
    set_password_command,
    login_required,
    login_required_allow_demo,
)
from backaind.db import get_db


def test_login(client, auth):
    """Test whether login works and redirects to index page."""
    assert client.get("/auth/login").status_code == 200
    response = auth.login()
    assert response.headers["Location"] == "/"

    with client:
        client.get("/")
        assert session["user_id"] == 1
        assert g.user["username"] == "test"


@pytest.mark.parametrize(
    ("username", "password", "message"),
    (
        ("a", "test", b"Incorrect username or password."),
        ("test", "a", b"Incorrect username or password."),
    ),
)
def test_login_validate_input(auth, username, password, message):
    """Test whether entering invalid credentials returns an error message."""
    response = auth.login(username, password)
    assert message in response.data


def test_logout(client, auth):
    """Test whether logout removes the user from session."""
    auth.login()

    with client:
        auth.logout()
        assert "user_id" not in session


def test_is_password_correct(app):
    """Test whether checking the password works."""
    with app.app_context():
        assert not is_password_correct("test", "a")
        assert not is_password_correct("a", "test")
        assert is_password_correct("test", "test")


def test_set_password(app):
    """Test whether setting the password works."""
    with app.app_context():
        set_password("test", "a")
        assert not is_password_correct("test", "test")
        assert is_password_correct("test", "a")
        set_password("test", "test")
        assert is_password_correct("test", "test")


def test_demo_user(client):
    """Test whether the demo user is enabled automatically iff ENABLE_DEMO_MODE is set."""
    with client:
        client.get("/")
        assert session.get("user_id") is None
        assert g.user is None
        assert not g.is_demo_user

        os.environ["ENABLE_DEMO_MODE"] = "1"
        client.get("/")
        assert session["user_id"] == -1
        assert g.user["username"] == "demo"
        assert g.user["id"] == -1
        assert g.is_demo_user

        del os.environ["ENABLE_DEMO_MODE"]
        client.get("/")
        assert session.get("user_id") is None
        assert g.user is None
        assert not g.is_demo_user


def test_login_required_redirects_if_not_logged_in(app, client):
    """Test whether the login_required decorator redirects to login page."""
    with app.app_context(), app.test_request_context():
        client.get("/")
        response = login_required(lambda: "the_view")()
        assert (
            not isinstance(response, str)
            and response.headers["Location"] == "/auth/login"
        )


def test_login_required_declines_demo(app, client):
    """Test whether the login_required decorator does not accept the demo user."""
    with app.app_context(), app.test_request_context():
        os.environ["ENABLE_DEMO_MODE"] = "1"
        client.get("/")
        response = login_required(lambda: "the_view")()
        assert (
            not isinstance(response, str)
            and response.headers["Location"] == "/auth/login"
        )
        del os.environ["ENABLE_DEMO_MODE"]


def test_login_required_accepts_user(app, client, auth):
    """Test whether the login_required decorator allows signed in users."""
    with app.app_context(), app.test_request_context():
        auth.login()
        client.get("/")
        response = login_required(lambda: "the_view")()
        assert response == "the_view"


def test_login_required_allow_demo_redirects_if_not_logged_in(app, client):
    """Test whether the login_required_allow_demo decorator redirects to login page."""
    with app.app_context(), app.test_request_context():
        client.get("/")
        response = login_required_allow_demo(lambda: "the_view")()
        assert (
            not isinstance(response, str)
            and response.headers["Location"] == "/auth/login"
        )


def test_login_required_allow_demo_accepts_demo(app, client):
    """Test whether the login_required_allow_demo decorator allows the demo user."""
    with app.app_context(), app.test_request_context():
        os.environ["ENABLE_DEMO_MODE"] = "1"
        client.get("/")
        response = login_required_allow_demo(lambda: "the_view")()
        assert response == "the_view"
        del os.environ["ENABLE_DEMO_MODE"]


def test_login_required_allow_demo_accepts_user(app, client, auth):
    """Test whether the login_required decorator allows signed in users."""
    with app.app_context(), app.test_request_context():
        auth.login()
        client.get("/")
        response = login_required_allow_demo(lambda: "the_view")()
        assert response == "the_view"


def test_add_user_command(app, runner):
    """Test whether registering a new user works."""
    username = "a-new-user"
    password = "a-password"
    with app.app_context():
        database = get_db()

        user = database.execute(
            "SELECT * FROM user WHERE username = ?", (username,)
        ).fetchone()
        assert user is None

        result = runner.invoke(add_user, input=f"{username}\n{password}\n{password}\n")
        assert "Registration successful" in result.output

        user = database.execute(
            "SELECT * FROM user WHERE username = ?", (username,)
        ).fetchone()
        assert user is not None

        result = runner.invoke(add_user, input=f"{username}\n{password}\n{password}\n")
        assert "already registered" in result.output


def test_set_password_command(app, runner):
    """Test whether setting the password works."""
    username = "test"
    password = "a-password"
    with app.app_context():
        assert is_password_correct(username, "test")
        result = runner.invoke(
            set_password_command, input=f"{username}\n{password}\n{password}\n"
        )
        assert "Successfully set the password" in result.output
        assert is_password_correct(username, password)
        assert not is_password_correct(username, "test")
        set_password("test", "test")
