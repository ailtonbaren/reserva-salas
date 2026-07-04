from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Reserva
from app.services import RegraReservaErro, cancelar_reserva

reservas_bp = Blueprint("reservas", __name__, url_prefix="/reservas")


@reservas_bp.route("/minhas")
@login_required
def minhas():
    filtro = request.args.get("status", "todas")
    query = Reserva.query.filter_by(usuario_id=current_user.id)

    if filtro == "ativas":
        query = query.filter_by(status="ativa")
    elif filtro == "canceladas":
        query = query.filter_by(status="cancelada")
    elif filtro == "passadas":
        query = query.filter(Reserva.data < date.today())

    reservas = query.order_by(Reserva.data.desc(), Reserva.hora_inicio.desc()).all()
    return render_template("reservas/minhas.html", reservas=reservas, filtro=filtro)


@reservas_bp.route("/<int:reserva_id>/cancelar", methods=["POST"])
@login_required
def cancelar(reserva_id):
    reserva = db.get_or_404(Reserva, reserva_id)
    try:
        cancelar_reserva(reserva, current_user, request.form.get("motivo_cancelamento"))
        flash("Reserva cancelada com sucesso.", "success")
    except PermissionError:
        abort(403)
    except RegraReservaErro as erro:
        flash(str(erro), "warning")

    destino = request.form.get("next") or url_for("reservas.minhas")
    return redirect(destino)
