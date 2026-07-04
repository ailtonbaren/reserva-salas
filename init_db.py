import argparse

from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError

from app import create_app
from app.extensions import db
from app.seed import seed_data


def ensure_database_columns():
    inspector = inspect(db.engine)
    if "reservas" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("reservas")}
    with db.engine.begin() as connection:
        if "motivo_cancelamento" not in columns:
            connection.exec_driver_sql("ALTER TABLE reservas ADD COLUMN motivo_cancelamento VARCHAR(255)")
        if "cancelada_em" not in columns:
            connection.exec_driver_sql("ALTER TABLE reservas ADD COLUMN cancelada_em DATETIME")

    if "bloqueios_sala" not in inspector.get_table_names():
        return

    bloqueio_columns = {column["name"] for column in inspector.get_columns("bloqueios_sala")}
    with db.engine.begin() as connection:
        if "data_fim" not in bloqueio_columns:
            connection.exec_driver_sql("ALTER TABLE bloqueios_sala ADD COLUMN data_fim DATE")
        connection.exec_driver_sql("UPDATE bloqueios_sala SET data_fim = data WHERE data_fim IS NULL")


def main():
    parser = argparse.ArgumentParser(description="Inicializa ou atualiza o banco PostgreSQL.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Apaga e recria todas as tabelas antes de inserir os dados iniciais.",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        try:
            if args.reset:
                db.drop_all()
            db.create_all()
            ensure_database_columns()
            seed_data()
            if args.reset:
                print("Banco de dados recriado com dados iniciais.")
            else:
                print("Banco de dados atualizado/criado com dados iniciais.")
        except OperationalError as error:
            print("Não foi possível conectar ao PostgreSQL.")
            print("Verifique se o serviço está rodando e se a variável DATABASE_URL está correta.")
            print(f"DATABASE_URL atual: {app.config['SQLALCHEMY_DATABASE_URI']}")
            print(f"Erro original: {error.orig}")
            raise SystemExit(1) from error


if __name__ == "__main__":
    main()
