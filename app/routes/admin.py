from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.auth_utils import admin_required
from app.extensions import db
from app.models import BloqueioSala, Reserva, Sala, Usuario
from app.services import (
    RegraReservaErro,
    cancelar_bloqueio_sala,
    criar_bloqueio_sala,
    definir_configuracao,
    obter_limite_reservas_ativas_aluno,
    parse_date,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
@admin_required
def painel():
    return render_template(
        "admin/painel.html",
        total_salas=Sala.query.count(),
        total_usuarios=Usuario.query.count(),
        salas_bloqueadas=Sala.query.filter_by(bloqueada=True).count(),
        reservas_ativas=Reserva.query.filter_by(status="ativa").count(),
    )


@admin_bp.route("/salas")
@login_required
@admin_required
def salas():
    return render_template("admin/salas.html", salas=Sala.query.order_by(Sala.nome).all())


@admin_bp.route("/salas/nova", methods=["GET", "POST"])
@login_required
@admin_required
def nova_sala():
    sala = Sala()
    if request.method == "POST":
        if not preencher_sala(sala):
            return render_template("admin/sala_form.html", sala=sala), 400
        db.session.add(sala)
        db.session.commit()
        flash("Sala cadastrada com sucesso.", "success")
        return redirect(url_for("admin.salas"))
    return render_template("admin/sala_form.html", sala=sala)


@admin_bp.route("/salas/<int:sala_id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def editar_sala(sala_id):
    sala = db.get_or_404(Sala, sala_id)
    if request.method == "POST":
        if not preencher_sala(sala):
            return render_template("admin/sala_form.html", sala=sala), 400
        db.session.commit()
        flash("Sala atualizada com sucesso.", "success")
        return redirect(url_for("admin.salas"))
    return render_template("admin/sala_form.html", sala=sala)


@admin_bp.route("/salas/<int:sala_id>/excluir", methods=["POST"])
@login_required
@admin_required
def excluir_sala(sala_id):
    sala = db.get_or_404(Sala, sala_id)

    possui_reservas = Reserva.query.filter_by(sala_id=sala.id).first() is not None
    possui_bloqueios = BloqueioSala.query.filter_by(sala_id=sala.id).first() is not None

    if possui_reservas or possui_bloqueios:
        flash(
            "Não é possível excluir uma sala com reservas ou bloqueios registrados. "
            "Desative a sala para impedir novas reservas.",
            "danger",
        )
        return redirect(url_for("admin.salas"))

    db.session.delete(sala)
    db.session.commit()
    flash("Sala excluída com sucesso.", "success")
    return redirect(url_for("admin.salas"))


@admin_bp.route("/usuarios")
@login_required
@admin_required
def usuarios():
    usuarios_lista = Usuario.query.order_by(Usuario.nome).all()
    return render_template("admin/usuarios.html", usuarios=usuarios_lista)


@admin_bp.route("/usuarios/novo", methods=["GET", "POST"])
@login_required
@admin_required
def novo_usuario():
    usuario = Usuario(perfil="aluno", ativo=True)
    if request.method == "POST":
        if not preencher_usuario(usuario, senha_obrigatoria=True):
            return render_template("admin/usuario_form.html", usuario=usuario), 400
        db.session.add(usuario)
        db.session.commit()
        flash("Usuário cadastrado com sucesso.", "success")
        return redirect(url_for("admin.usuarios"))
    return render_template("admin/usuario_form.html", usuario=usuario)


@admin_bp.route("/usuarios/<int:usuario_id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def editar_usuario(usuario_id):
    usuario = db.get_or_404(Usuario, usuario_id)
    if request.method == "POST":
        if not preencher_usuario(usuario, senha_obrigatoria=False):
            return render_template("admin/usuario_form.html", usuario=usuario), 400
        db.session.commit()
        flash("Usuário atualizado com sucesso.", "success")
        return redirect(url_for("admin.usuarios"))
    return render_template("admin/usuario_form.html", usuario=usuario)


@admin_bp.route("/reservas")
@login_required
@admin_required
def reservas():
    aluno = request.args.get("aluno", "").strip()
    sala_id = request.args.get("sala_id", type=int)
    status = request.args.get("status", "").strip()
    data_texto = request.args.get("data", "").strip()

    query = Reserva.query.join(Usuario).join(Sala)

    if aluno:
        query = query.filter(
            Usuario.nome.ilike(f"%{aluno}%") | Usuario.email.ilike(f"%{aluno}%")
        )

    if sala_id:
        query = query.filter(Reserva.sala_id == sala_id)

    if status in ("ativa", "cancelada"):
        query = query.filter(Reserva.status == status)

    if data_texto:
        try:
            query = query.filter(Reserva.data == parse_date(data_texto))
        except ValueError:
            flash("Data inválida no filtro. Use uma data válida.", "warning")

    reservas_lista = query.order_by(Reserva.data.desc(), Reserva.hora_inicio.desc()).all()
    return render_template(
        "admin/reservas.html",
        reservas=reservas_lista,
        salas=Sala.query.order_by(Sala.nome).all(),
        filtros={
            "aluno": aluno,
            "sala_id": sala_id,
            "status": status,
            "data": data_texto,
        },
    )


@admin_bp.route("/bloqueios", methods=["GET", "POST"])
@login_required
@admin_required
def bloqueios():
    salas = Sala.query.order_by(Sala.nome).all()
    if request.method == "POST":
        try:
            criar_bloqueio_sala(
                request.form.get("sala_id"),
                request.form.get("data_inicio"),
                request.form.get("data_fim"),
                request.form.get("motivo", ""),
            )
            flash("Bloqueio criado com sucesso.", "success")
            return redirect(url_for("admin.bloqueios"))
        except (RegraReservaErro, ValueError, TypeError) as erro:
            flash(str(erro) if str(erro) else "Não foi possível criar o bloqueio.", "danger")

    bloqueios_lista = (
        BloqueioSala.query.order_by(BloqueioSala.data.desc(), BloqueioSala.hora_inicio.desc()).all()
    )
    return render_template("admin/bloqueios.html", salas=salas, bloqueios=bloqueios_lista)


@admin_bp.route("/bloqueios/<int:bloqueio_id>/cancelar", methods=["POST"])
@login_required
@admin_required
def cancelar_bloqueio(bloqueio_id):
    bloqueio = db.get_or_404(BloqueioSala, bloqueio_id)
    cancelar_bloqueio_sala(bloqueio)
    flash("Bloqueio cancelado com sucesso.", "success")
    return redirect(url_for("admin.bloqueios"))


@admin_bp.route("/configuracoes", methods=["GET", "POST"])
@login_required
@admin_required
def configuracoes():
    if request.method == "POST":
        try:
            limite = int(request.form.get("max_reservas_ativas_aluno") or 0)
        except ValueError:
            limite = 0

        if limite < 1:
            flash("O limite de reservas deve ser maior que zero.", "danger")
        else:
            definir_configuracao(
                "max_reservas_ativas_aluno",
                limite,
                "Quantidade máxima de reservas ativas por aluno.",
            )
            flash("Configurações atualizadas com sucesso.", "success")
            return redirect(url_for("admin.configuracoes"))

    return render_template(
        "admin/configuracoes.html",
        max_reservas_ativas_aluno=obter_limite_reservas_ativas_aluno(),
    )


def preencher_sala(sala):
    nome = request.form.get("nome", "").strip()
    localizacao = request.form.get("localizacao", "").strip()
    descricao = request.form.get("descricao", "").strip()

    try:
        capacidade = int(request.form.get("capacidade") or 0)
    except ValueError:
        capacidade = 0

    if not nome:
        flash("Informe o nome da sala.", "danger")
        return False

    if not localizacao:
        flash("Informe a localização da sala.", "danger")
        return False

    if capacidade < 1:
        flash("A capacidade da sala deve ser maior que zero.", "danger")
        return False

    sala.nome = nome
    sala.localizacao = localizacao
    sala.capacidade = capacidade
    sala.descricao = descricao
    sala.ativa = bool(request.form.get("ativa"))
    sala.bloqueada = bool(request.form.get("bloqueada"))
    return True


def preencher_usuario(usuario, senha_obrigatoria=False):
    nome = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip().lower()
    matricula = request.form.get("matricula", "").strip() or None
    senha = request.form.get("senha", "")
    perfil = request.form.get("perfil", "aluno").strip()
    ativo = bool(request.form.get("ativo"))

    if not nome:
        flash("Informe o nome do usuário.", "danger")
        return False

    if not email or "@" not in email:
        flash("Informe um e-mail válido.", "danger")
        return False

    usuario_existente = Usuario.query.filter_by(email=email).first()
    if usuario_existente and usuario_existente.id != usuario.id:
        flash("Já existe um usuário cadastrado com este e-mail.", "danger")
        return False

    if perfil not in ("aluno", "administrador"):
        flash("Perfil de usuário inválido.", "danger")
        return False

    if senha_obrigatoria and not senha:
        flash("Informe a senha do usuário.", "danger")
        return False

    if senha and len(senha) < 6:
        flash("A senha deve ter pelo menos 6 caracteres.", "danger")
        return False

    if usuario.id == current_user.id and not ativo:
        flash("Você não pode desativar seu próprio usuário.", "danger")
        return False

    usuario.nome = nome
    usuario.email = email
    usuario.matricula = matricula
    usuario.perfil = perfil
    usuario.ativo = ativo
    if senha:
        usuario.set_password(senha)
    return True
