# Reserva de Salas de Estudo

Sistema web acadêmico para reserva de salas de estudo, com autenticação, perfis de aluno e administrador, controle de conflitos de horário e documentação do projeto.

## Stack

- Python 3
- Flask
- Flask-SQLAlchemy
- Flask-Login
- PostgreSQL
- psycopg
- Jinja2
- Bootstrap 5
- pytest

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Banco de dados

O sistema usa PostgreSQL. A URL padrão usada pela aplicação é:

```text
postgresql+psycopg://reserva_salas:reserva_salas@localhost:5432/reserva_salas
```

Se o banco usar outros dados de conexão:

```bash
export DATABASE_URL="postgresql+psycopg://usuario:senha@localhost:5432/reserva_salas"
```

## Criar ou atualizar banco e dados iniciais

```bash
source .venv/bin/activate
python init_db.py
```

O script cria ou atualiza as tabelas no PostgreSQL, adiciona colunas faltantes sem apagar dados existentes e cadastra os dados iniciais quando ainda não existem:

- Administrador: `admin@uema.com` / `admin123`
- Aluno demonstração: `aluno@uema.com` / `aluno123`
- Ailton Baren: `aluno1@uema.com` / `aluno123`
- Tomás Araújo: `aluno2@uema.com` / `aluno123`
- Fredrik Aursnes: `aluno3@uema.com` / `aluno123`
- Salas de Estudos 01, 02 e 03

## Recriar banco do zero

Use somente quando quiser apagar os dados atuais:

```bash
source .venv/bin/activate
python init_db.py --reset
```

## Executar a aplicação

```bash
source .venv/bin/activate
python run.py
```

Acesse em um navegador:

```text
http://127.0.0.1:5000
```

## Executar testes

```bash
source .venv/bin/activate
pytest
```

Os testes usam banco isolado em memória. A aplicação em execução usa PostgreSQL.

## Documentação

A pasta `docs/` contém os documentos:

- `solicitacao_projeto.pdf`
- `termo_abertura_projeto.pdf`
- `documentacao_tecnica.pdf`
- `plano_de_testes.pdf`
- `manual_do_usuario.pdf`
- `termo_de_homologacao.pdf`
- `validacaoFINAL`
- `comandosFINAL`

A pasta `docsLocal/`, quando existir, é apenas material local de apoio e está ignorada pelo Git.

## Funcionalidades

- Login de aluno e administrador.
- Gestão administrativa de usuários, com cadastro, edição, perfil, matrícula, senha e status ativo/inativo.
- Consulta de salas.
- Criação e cancelamento de reservas.
- Bloqueio de reservas com data passada, duração maior que duas horas, horário final anterior ao inicial e conflitos de horário.
- Painel administrativo para cadastrar, editar, ativar, desativar e bloquear salas.
- Bloqueio de salas por período e configuração do limite de reservas ativas por aluno.
- Lista administrativa de reservas com cancelamento.
- Páginas 403 e 404.

## Estrutura

```text
app/
  routes/
  templates/
  static/
  models.py
  services.py
  seed.py
tests/
docs/
init_db.py
run.py
requirements.txt
```
