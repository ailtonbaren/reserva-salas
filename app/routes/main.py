from datetime import date

from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.models import Reserva, Sala

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("auth.login"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_admin:
        reservas_ativas = Reserva.query.filter_by(status="ativa").count()
        salas_disponiveis = Sala.query.filter_by(ativa=True, bloqueada=False).count()
        return render_template(
            "dashboard.html",
            reservas_ativas=reservas_ativas,
            proximas_reservas=Reserva.query.filter(
                Reserva.status == "ativa", Reserva.data >= date.today()
            )
            .order_by(Reserva.data, Reserva.hora_inicio)
            .limit(5)
            .all(),
            salas_disponiveis=salas_disponiveis,
        )

    reservas_ativas = Reserva.query.filter_by(usuario_id=current_user.id, status="ativa").count()
    proximas_reservas = (
        Reserva.query.filter(
            Reserva.usuario_id == current_user.id,
            Reserva.status == "ativa",
            Reserva.data >= date.today(),
        )
        .order_by(Reserva.data, Reserva.hora_inicio)
        .limit(5)
        .all()
    )
    salas_disponiveis = Sala.query.filter_by(ativa=True, bloqueada=False).count()
    return render_template(
        "dashboard.html",
        reservas_ativas=reservas_ativas,
        proximas_reservas=proximas_reservas,
        salas_disponiveis=salas_disponiveis,
    )
