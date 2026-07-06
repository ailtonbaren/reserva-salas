from app.extensions import db
from app.models import ConfiguracaoSistema, Sala, Usuario


def seed_data():
    if not Usuario.query.filter_by(email="admin@uema.com").first():
        admin = Usuario(
            nome="Administrador",
            email="admin@uema.com",
            matricula=None,
            perfil="administrador",
            ativo=True,
        )
        admin.set_password("admin123")
        db.session.add(admin)

    alunos = [
        ("Aluno test", "aluno@uema.com", "2026001", "aluno123"),
        ("Ailton Baren", "aluno1@uema.com", "2026002", "aluno123"),
        ("Tomás Araújo", "aluno2@uema.com", "2026003", "aluno123"),
        ("Fredrik Aursnes", "aluno3@uema.com", "2026004", "aluno123"),
    ]
    for nome, email, matricula, senha in alunos:
        if not Usuario.query.filter_by(email=email).first():
            aluno = Usuario(
                nome=nome,
                email=email,
                matricula=matricula,
                perfil="aluno",
                ativo=True,
            )
            aluno.set_password(senha)
            db.session.add(aluno)

    salas = [
        ("Sala de Estudos 01", 4),
        ("Sala de Estudos 02", 6),
        ("Sala de Estudos 03", 8),
    ]
    for nome, capacidade in salas:
        if not Sala.query.filter_by(nome=nome).first():
            db.session.add(
                Sala(
                    nome=nome,
                    localizacao="CCT",
                    capacidade=capacidade,
                    descricao="Sala equipada para estudos em grupo.",
                    ativa=True,
                    bloqueada=False,
                )
            )

    if not ConfiguracaoSistema.query.filter_by(
        chave="max_reservas_ativas_aluno"
    ).first():
        db.session.add(
            ConfiguracaoSistema(
                chave="max_reservas_ativas_aluno",
                valor="3",
                descricao="Quantidade máxima de reservas ativas por aluno.",
            )
        )

    db.session.commit()
