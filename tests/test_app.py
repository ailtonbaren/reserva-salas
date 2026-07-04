from datetime import date, timedelta

from app.extensions import db
from app.models import BloqueioSala, ConfiguracaoSistema, Reserva, Sala, Usuario

from .conftest import login, login_admin


def reserva_payload(**overrides):
    amanha = date.today() + timedelta(days=1)
    payload = {
        "sala_id": "1",
        "data": amanha.strftime("%Y-%m-%d"),
        "hora_inicio": "09:00",
        "hora_fim": "10:00",
        "finalidade": "Estudo em grupo",
    }
    payload.update(overrides)
    return payload


def test_login_valido(client):
    response = login(client)
    assert response.status_code == 200
    assert "Login realizado com sucesso".encode() in response.data


def test_nome_do_aluno_aparece_no_menu_superior(client):
    response = login(client, email="aluno1@uema.com")
    assert response.status_code == 200
    assert "Ailton Baren".encode() in response.data


def test_login_invalido(client):
    response = login(client, senha="senha-errada")
    assert response.status_code == 200
    assert "E-mail ou senha inválidos".encode() in response.data


def test_criacao_reserva_valida(client, app):
    login(client)
    response = client.post(
        "/salas/horarios", data=reserva_payload(), follow_redirects=True
    )
    assert response.status_code == 200
    assert "Reserva criada com sucesso".encode() in response.data
    with app.app_context():
        assert Reserva.query.filter_by(status="ativa").count() == 1


def test_criacao_reserva_valida_com_data_brasileira(client, app):
    login(client)
    amanha = date.today() + timedelta(days=1)
    response = client.post(
        "/salas/horarios",
        data=reserva_payload(data=amanha.strftime("%d/%m/%Y")),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Reserva criada com sucesso".encode() in response.data
    with app.app_context():
        assert Reserva.query.filter_by(status="ativa").count() == 1


def test_criacao_reserva_valida_com_duracao_de_duas_horas(client, app):
    login(client)
    response = client.post(
        "/salas/horarios",
        data=reserva_payload(hora_inicio="08:00", hora_fim="10:00", duracao="2"),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Reserva criada com sucesso".encode() in response.data
    with app.app_context():
        reserva = Reserva.query.first()
        assert reserva.hora_inicio.strftime("%H:%M") == "08:00"
        assert reserva.hora_fim.strftime("%H:%M") == "10:00"


def test_rejeita_reserva_data_passada(client, app):
    login(client)
    ontem = date.today() - timedelta(days=1)
    response = client.post(
        "/salas/horarios",
        data=reserva_payload(data=ontem.strftime("%Y-%m-%d")),
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        assert Reserva.query.count() == 0


def test_rejeita_hora_final_anterior_ao_inicio(client, app):
    login(client)
    client.post(
        "/salas/horarios", data=reserva_payload(hora_inicio="10:00", hora_fim="09:00")
    )
    with app.app_context():
        assert Reserva.query.count() == 0


def test_rejeita_reserva_com_mais_de_duas_horas(client, app):
    login(client)
    client.post(
        "/salas/horarios", data=reserva_payload(hora_inicio="09:00", hora_fim="11:30")
    )
    with app.app_context():
        assert Reserva.query.count() == 0


def test_rejeita_conflito_de_horarios(client, app):
    login(client)
    client.post(
        "/salas/horarios", data=reserva_payload(hora_inicio="09:00", hora_fim="10:00")
    )
    response = client.post(
        "/salas/horarios",
        data=reserva_payload(hora_inicio="09:30", hora_fim="10:30"),
        follow_redirects=True,
    )
    assert (
        "Sala de Estudos 01 já está reservada das 09:00 às 10:00".encode()
        in response.data
    )
    with app.app_context():
        assert Reserva.query.count() == 1


def test_cancelamento_de_reserva(client, app):
    login(client)
    client.post("/salas/horarios", data=reserva_payload())
    with app.app_context():
        reserva_id = Reserva.query.first().id
    response = client.post(
        f"/reservas/{reserva_id}/cancelar",
        data={"motivo_cancelamento": "Não será mais necessário"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        reserva = Reserva.query.first()
        assert reserva.status == "cancelada"
        assert reserva.motivo_cancelamento == "Não será mais necessário"


def test_rejeita_cancelamento_sem_motivo(client, app):
    login(client)
    client.post("/salas/horarios", data=reserva_payload())
    with app.app_context():
        reserva_id = Reserva.query.first().id
    response = client.post(f"/reservas/{reserva_id}/cancelar", follow_redirects=True)
    assert response.status_code == 200
    assert "Informe o motivo do cancelamento".encode() in response.data
    with app.app_context():
        assert Reserva.query.first().status == "ativa"


def test_bloqueio_acesso_administrativo_para_aluno(client):
    login(client)
    response = client.get("/admin/", follow_redirects=False)
    assert response.status_code == 403


def test_acesso_protegido_redireciona_para_login(client):
    response = client.get("/reservas/minhas", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_sala_bloqueada_nao_pode_ser_reservada(client, app):
    with app.app_context():
        sala = Sala.query.first()
        sala.bloqueada = True
        db.session.commit()
    login(client)
    client.post("/salas/horarios", data=reserva_payload())
    with app.app_context():
        assert Reserva.query.count() == 0


def test_horarios_disponiveis_renderiza(client):
    login(client)
    response = client.get("/salas/horarios?sala_id=1")
    assert response.status_code == 200
    assert "Horários disponíveis".encode() in response.data


def test_horarios_disponiveis_com_duracao_de_duas_horas(client):
    login(client)
    response = client.get("/salas/horarios?sala_id=1&duracao=2")
    assert response.status_code == 200
    assert b"08:00 - 10:00" in response.data
    assert b"2h" in response.data


def test_horario_reservado_mostra_finalidade(client):
    login(client)
    amanha = date.today() + timedelta(days=1)
    client.post(
        "/salas/horarios",
        data=reserva_payload(
            data=amanha.strftime("%Y-%m-%d"),
            hora_inicio="08:00",
            hora_fim="09:00",
            finalidade="Revisão de cálculo",
        ),
    )
    response = client.get(
        f"/salas/horarios?sala_id=1&data={amanha.strftime('%Y-%m-%d')}"
    )
    assert response.status_code == 200
    assert "Revisão de cálculo".encode() in response.data


def test_filtro_de_salas_por_capacidade(client):
    login(client)
    response = client.get("/salas/?capacidade=8")
    assert response.status_code == 200
    assert "Sala de Estudos 03".encode() in response.data
    assert "Sala de Estudos 01".encode() not in response.data


def test_templates_principais_do_aluno_renderizam(client):
    login(client)
    for rota in ["/dashboard", "/salas/", "/salas/horarios", "/reservas/minhas"]:
        response = client.get(rota)
        assert response.status_code == 200


def test_templates_principais_do_admin_renderizam(client):
    login_admin(client)
    for rota in [
        "/dashboard",
        "/admin/",
        "/admin/usuarios",
        "/admin/usuarios/novo",
        "/admin/salas",
        "/admin/salas/nova",
        "/admin/reservas",
        "/admin/bloqueios",
        "/admin/configuracoes",
    ]:
        response = client.get(rota)
        assert response.status_code == 200


def test_admin_filtra_reservas_por_aluno_status_sala_e_data(client, app):
    login(client, email="aluno1@uema.com")
    amanha = date.today() + timedelta(days=1)
    client.post(
        "/salas/horarios",
        data=reserva_payload(
            sala_id="1",
            data=amanha.strftime("%Y-%m-%d"),
            hora_inicio="08:00",
            hora_fim="09:00",
            finalidade="Estudo dirigido",
        ),
    )
    client.get("/logout", follow_redirects=True)
    login_admin(client)
    response = client.get(
        f"/admin/reservas?aluno=Ailton&sala_id=1&status=ativa&data={amanha.strftime('%Y-%m-%d')}"
    )
    assert response.status_code == 200
    assert "Ailton Baren".encode() in response.data
    assert "Estudo dirigido".encode() in response.data


def test_admin_cadastra_usuario_aluno(client, app):
    login_admin(client)
    response = client.post(
        "/admin/usuarios/novo",
        data={
            "nome": "Maria Oliveira",
            "email": "maria@uema.com",
            "matricula": "2026999",
            "perfil": "aluno",
            "senha": "maria123",
            "ativo": "on",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Usuário cadastrado com sucesso".encode() in response.data
    assert "Maria Oliveira".encode() in response.data

    with app.app_context():
        usuario = Usuario.query.filter_by(email="maria@uema.com").first()
        assert usuario is not None
        assert usuario.nome == "Maria Oliveira"
        assert usuario.matricula == "2026999"
        assert usuario.perfil == "aluno"
        assert usuario.check_password("maria123")

    client.get("/logout", follow_redirects=True)
    response = login(client, email="maria@uema.com", senha="maria123")
    assert response.status_code == 200
    assert "Maria Oliveira".encode() in response.data


def test_admin_rejeita_usuario_com_email_duplicado(client, app):
    login_admin(client)
    response = client.post(
        "/admin/usuarios/novo",
        data={
            "nome": "Outro Admin",
            "email": "admin@uema.com",
            "matricula": "",
            "perfil": "administrador",
            "senha": "admin456",
            "ativo": "on",
        },
    )
    assert response.status_code == 400
    assert "Já existe um usuário cadastrado com este e-mail".encode() in response.data


def test_admin_edita_usuario_sem_alterar_senha(client, app):
    login_admin(client)
    with app.app_context():
        usuario = Usuario.query.filter_by(email="aluno1@uema.com").first()
        usuario_id = usuario.id
        senha_hash = usuario.senha_hash

    response = client.post(
        f"/admin/usuarios/{usuario_id}/editar",
        data={
            "nome": "Ailton Baren Pereira",
            "email": "ailton.baren@uema.com",
            "matricula": "2026001",
            "perfil": "aluno",
            "senha": "",
            "ativo": "on",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Usuário atualizado com sucesso".encode() in response.data

    with app.app_context():
        usuario = db.session.get(Usuario, usuario_id)
        assert usuario.nome == "Ailton Baren Pereira"
        assert usuario.email == "ailton.baren@uema.com"
        assert usuario.senha_hash == senha_hash


def test_admin_cadastra_sala_valida(client, app):
    login_admin(client)
    response = client.post(
        "/admin/salas/nova",
        data={
            "nome": "Sala de Estudos 04",
            "localizacao": "Bloco B",
            "capacidade": "5",
            "descricao": "Sala para estudo individual e em grupo.",
            "ativa": "on",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Sala cadastrada com sucesso".encode() in response.data
    with app.app_context():
        sala = Sala.query.filter_by(nome="Sala de Estudos 04").first()
        assert sala is not None
        assert sala.capacidade == 5


def test_admin_rejeita_sala_com_capacidade_invalida(client, app):
    login_admin(client)
    response = client.post(
        "/admin/salas/nova",
        data={
            "nome": "Sala inválida",
            "localizacao": "Bloco C",
            "capacidade": "0",
            "descricao": "",
            "ativa": "on",
        },
    )
    assert response.status_code == 400
    assert "A capacidade da sala deve ser maior que zero".encode() in response.data
    with app.app_context():
        assert Sala.query.filter_by(nome="Sala inválida").first() is None


def test_admin_edita_e_bloqueia_sala(client, app):
    login_admin(client)
    response = client.post(
        "/admin/salas/1/editar",
        data={
            "nome": "Sala de Estudos 01",
            "localizacao": "CCT",
            "capacidade": "4",
            "descricao": "Em manutenção.",
            "ativa": "on",
            "bloqueada": "on",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        sala = db.session.get(Sala, 1)
        assert sala.bloqueada is True


def test_admin_cria_bloqueio_por_periodo(client, app):
    login_admin(client)
    amanha = date.today() + timedelta(days=1)
    depois_de_amanha = date.today() + timedelta(days=2)
    response = client.post(
        "/admin/bloqueios",
        data={
            "sala_id": "1",
            "data_inicio": amanha.strftime("%Y-%m-%d"),
            "data_fim": depois_de_amanha.strftime("%Y-%m-%d"),
            "motivo": "Manutenção preventiva",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Bloqueio criado com sucesso".encode() in response.data
    with app.app_context():
        bloqueio = BloqueioSala.query.first()
        assert bloqueio is not None
        assert bloqueio.ativo is True
        assert bloqueio.data == amanha
        assert bloqueio.data_fim == depois_de_amanha


def test_bloqueio_por_periodo_impede_reserva(client, app):
    login_admin(client)
    amanha = date.today() + timedelta(days=1)
    depois_de_amanha = date.today() + timedelta(days=2)
    client.post(
        "/admin/bloqueios",
        data={
            "sala_id": "1",
            "data_inicio": amanha.strftime("%Y-%m-%d"),
            "data_fim": depois_de_amanha.strftime("%Y-%m-%d"),
            "motivo": "Manutenção",
        },
    )
    client.get("/logout", follow_redirects=True)
    login(client)
    response = client.post(
        "/salas/horarios",
        data=reserva_payload(data=depois_de_amanha.strftime("%Y-%m-%d")),
        follow_redirects=True,
    )
    assert "está bloqueada de".encode() in response.data
    with app.app_context():
        assert Reserva.query.count() == 0


def test_admin_cancela_bloqueio(client, app):
    login_admin(client)
    amanha = date.today() + timedelta(days=1)
    client.post(
        "/admin/bloqueios",
        data={
            "sala_id": "1",
            "data_inicio": amanha.strftime("%Y-%m-%d"),
            "data_fim": amanha.strftime("%Y-%m-%d"),
            "motivo": "Manutenção",
        },
    )
    with app.app_context():
        bloqueio_id = BloqueioSala.query.first().id
    response = client.post(
        f"/admin/bloqueios/{bloqueio_id}/cancelar", follow_redirects=True
    )
    assert response.status_code == 200
    with app.app_context():
        assert BloqueioSala.query.first().ativo is False


def test_admin_atualiza_limite_de_reservas(client, app):
    login_admin(client)
    response = client.post(
        "/admin/configuracoes",
        data={"max_reservas_ativas_aluno": "2"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Configurações atualizadas com sucesso".encode() in response.data
    with app.app_context():
        configuracao = ConfiguracaoSistema.query.filter_by(
            chave="max_reservas_ativas_aluno"
        ).first()
        assert configuracao.valor == "2"


def test_limite_de_reservas_ativas_por_aluno(client, app):
    login_admin(client)
    client.post("/admin/configuracoes", data={"max_reservas_ativas_aluno": "2"})
    client.get("/logout", follow_redirects=True)

    login(client)
    amanha = date.today() + timedelta(days=1)
    client.post(
        "/salas/horarios",
        data=reserva_payload(
            data=amanha.strftime("%Y-%m-%d"),
            sala_id="1",
            hora_inicio="08:00",
            hora_fim="09:00",
        ),
    )
    client.post(
        "/salas/horarios",
        data=reserva_payload(
            data=amanha.strftime("%Y-%m-%d"),
            sala_id="2",
            hora_inicio="09:00",
            hora_fim="10:00",
        ),
    )
    response = client.post(
        "/salas/horarios",
        data=reserva_payload(
            data=amanha.strftime("%Y-%m-%d"),
            sala_id="3",
            hora_inicio="10:00",
            hora_fim="11:00",
        ),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Você atingiu o limite de 2 reservas ativas".encode() in response.data
    with app.app_context():
        assert Reserva.query.filter_by(status="ativa").count() == 2
