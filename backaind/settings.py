"""Allow users to see and change their settings."""
from flask import Blueprint, request, flash, render_template, g
from backaind.auth import (
    login_required_allow_demo,
    is_password_correct,
    set_password,
    is_demo_user,
)
from backaind.db import get_db

bp = Blueprint("settings", __name__, url_prefix="/settings")

EXTERNAL_PROVIDER_ENVVARS = [
    "AI21_API_KEY",
    "ALEPH_ALPHA_API_KEY",
    "ANYSCALE_SERVICE_URL",
    "ANYSCALE_SERVICE_ROUTE",
    "ANYSCALE_SERVICE_TOKEN",
    "AVIARY_URL",
    "AVIARY_TOKEN",
    "BANANA_API_KEY",
    "BEAM_CLIENT_ID",
    "BEAM_CLIENT_SECRET",
    "COHERE_API_KEY",
    "DATABRICKS_HOST",
    "DATABRICKS_API_TOKEN",
    "DEEPINFRA_API_TOKEN",
    "FOREFRONTAI_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOSEAI_API_KEY",
    "HUGGINGFACE_API_KEY",
    "HUGGINGFACEHUB_API_TOKEN",
    "MOSAICML_API_TOKEN",
    "NLPCLOUD_API_KEY",
    "OPENAI_API_KEY",
    "REPLICATE_API_TOKEN",
    "STOCHASTICAI_API_KEY",
    "TEXT_GENERATION_INFERENCE_TOKEN",
    "WRITER_API_KEY",
    "WRITER_ORG_ID",
]


@bp.route("/password", methods=("GET", "POST"))
@login_required_allow_demo
def password():
    """Render the password change page or change the user's password."""
    if is_demo_user():
        flash("You cannot change the password of the demo user.", "warning")
    elif request.method == "POST":
        current_password = request.form["current-password"]
        new_password = request.form["new-password"]
        new_password_confirmation = request.form["new-password-confirmation"]

        if new_password != new_password_confirmation:
            flash("Password and confirmation do not match.", "danger")
        elif not is_password_correct(g.user["username"], current_password):
            flash("Incorrect current password.", "danger")
        elif len(new_password) < 10:
            flash("Password must be at least 10 characters long.", "danger")
        else:
            set_password(g.user["username"], new_password)
            flash("Password changed successfully.", "success")

    return render_template("settings/password.html")


@bp.route("/external-providers", methods=("GET", "POST"))
@login_required_allow_demo
def external_providers():
    """Render the external providers page or save changed external providers settings."""
    if is_demo_user():
        flash(
            "You cannot change the external providers settings of the demo user.",
            "warning",
        )
    elif request.method == "POST":
        database = get_db()
        for envvar in EXTERNAL_PROVIDER_ENVVARS:
            if envvar in request.form and request.form[envvar].strip():
                database.execute(
                    """INSERT OR REPLACE INTO settings (user_id, domain, name, value)
                    VALUES (?, ?, ?, ?)""",
                    (
                        g.user["id"],
                        "external-providers",
                        envvar,
                        request.form[envvar].strip(),
                    ),
                )
            else:
                database.execute(
                    "DELETE FROM settings WHERE user_id = ? AND domain = ? AND name = ?",
                    (g.user["id"], "external-providers", envvar),
                )
        database.commit()
        flash("Settings saved successfully.", "success")

    settings = get_settings(g.user["id"])
    return render_template(
        "settings/external_providers.html",
        envvars=EXTERNAL_PROVIDER_ENVVARS,
        settings=settings.get("external-providers", {}),
    )


def get_settings(user_id: int):
    """Return the settings for a specified user."""
    database = get_db()
    settings = {}
    for row in database.execute(
        "SELECT domain, name, value FROM settings WHERE user_id = ?", (user_id,)
    ):
        settings.setdefault(row["domain"], {})[row["name"]] = row["value"]
    return settings
