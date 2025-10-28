"""Stitch Dashboard integration

Provides a standalone view at /stitch-dashboard that renders the external
stitch dashboard HTML page. This route is login-protected and intentionally
does not extend the app base template to avoid Tailwind prefix conflicts.
"""
from flask import Blueprint, render_template
from flask_login import login_required

stitch_bp = Blueprint("stitch", __name__)


@stitch_bp.route("/stitch-dashboard")
@login_required
def stitch_dashboard():
    return render_template("external/stitch_dashboard.html")
