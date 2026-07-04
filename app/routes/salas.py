from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Sala
from app.services import RegraReservaErro, criar_reserva, gerar_horarios_disponiveis, parse_date

salas_bp = Blueprint("salas", __name__, url_prefix="/salas")


@salas_bp.route("/")
@login_required
def listar():
    query = Sala.query
    termo = request.args.get("q", "").strip()
    capacidade = request.args.get("capacidade", "").strip()
    status = request.args.get("status", "").strip()

    if termo:
        query = query.filter(
            Sala.nome.ilike(f"%{termo}%") | Sala.localizacao.ilike(f"%{termo}%")
        )

    if capacidade.isdigit():
        query = query.filter(Sala.capacidade >= int(capacidade))

    if status == "disponivel":
        query = query.filter_by(ativa=True, bloqueada=False)
    elif status == "bloqueada":
        query = query.filter_by(bloqueada=True)
    elif status == "inativa":
        query = query.filter_by(ativa=False)

    salas = query.order_by(Sala.nome).all()
    return render_template("salas/lista.html", salas=salas)


@salas_bp.route("/horarios", methods=["GET", "POST"])
@login_required
def horarios():
    if request.method == "POST":
        try:
            criar_reserva(
                current_user,
                request.form.get("sala_id"),
                request.form.get("data"),
                request.form.get("hora_inicio"),
                request.form.get("hora_fim"),
                request.form.get("finalidade", ""),
            )
            flash("Reserva criada com sucesso.", "success")
            return redirect(url_for("reservas.minhas"))
        except RegraReservaErro as erro:
            flash(str(erro), "danger")
        except (ValueError, TypeError):
            flash("Não foi possível criar a reserva. Verifique os dados informados.", "danger")

    salas = Sala.query.filter_by(ativa=True).order_by(Sala.nome).all()
    sala_id = request.values.get("sala_id", type=int)
    data_texto = request.values.get("data") or date.today().strftime("%Y-%m-%d")
    duracao = request.values.get("duracao", type=int) or 1
    if duracao not in (1, 2):
        duracao = 1
    sala = None
    horarios_disponiveis = []

    try:
        data_consulta = parse_date(data_texto)
    except ValueError:
        data_consulta = date.today()

    if sala_id:
        sala = db.session.get(Sala, sala_id)
    elif salas:
        sala = salas[0]

    if sala:
        horarios_disponiveis = gerar_horarios_disponiveis(sala, data_consulta, duracao)

    return render_template(
        "salas/horarios.html",
        salas=salas,
        sala=sala,
        data_consulta=data_consulta,
        duracao=duracao,
        horarios=horarios_disponiveis,
    )
