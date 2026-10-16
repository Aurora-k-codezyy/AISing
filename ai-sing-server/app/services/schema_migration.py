from sqlalchemy import Engine, inspect, text

from app.services.security import hash_password


def sync_schema(engine: Engine) -> None:
    """Apply small startup migrations for existing MVP databases.

    SQLAlchemy create_all creates missing tables, but it does not add columns to
    existing tables. These guarded ALTER statements keep older deployments usable
    without introducing a full migration tool yet.
    """
    with engine.begin() as conn:
        dialect = conn.dialect.name
        sync_users(conn, dialect)
        sync_admins(conn, dialect)


def sync_users(conn, dialect: str) -> None:
    if not inspect(conn).has_table("users"):
        return
    columns = column_names(conn, "users")
    add_column(conn, dialect, "users", columns, "password_hash", "VARCHAR(256) NOT NULL DEFAULT ''")
    add_column(conn, dialect, "users", columns, "phone", "VARCHAR(32) NOT NULL DEFAULT ''")
    add_column(conn, dialect, "users", columns, "credits", "INT NOT NULL DEFAULT 480")
    add_column(conn, dialect, "users", columns, "active_token", "VARCHAR(128) NULL DEFAULT NULL")
    add_column(conn, dialect, "users", columns, "status", "VARCHAR(32) NOT NULL DEFAULT 'active'")
    make_token_nullable(conn, dialect, "users")
    default_user_password = hash_password("123456")
    conn.execute(
        text("UPDATE users SET password_hash = :password WHERE password_hash IS NULL OR password_hash = ''"),
        {"password": default_user_password},
    )
    conn.execute(text("UPDATE users SET phone = '' WHERE phone IS NULL"))
    conn.execute(text("UPDATE users SET credits = 480 WHERE credits IS NULL"))
    conn.execute(text("UPDATE users SET active_token = NULL WHERE active_token = ''"))
    conn.execute(text("UPDATE users SET status = 'active' WHERE status IS NULL OR status = ''"))


def sync_admins(conn, dialect: str) -> None:
    if not inspect(conn).has_table("admins"):
        return
    columns = column_names(conn, "admins")
    add_column(conn, dialect, "admins", columns, "active_token", "VARCHAR(128) NULL DEFAULT NULL")
    make_token_nullable(conn, dialect, "admins")
    conn.execute(text("UPDATE admins SET active_token = NULL WHERE active_token = ''"))


def column_names(conn, table_name: str) -> set[str]:
    return {column["name"] for column in inspect(conn).get_columns(table_name)}


def add_column(conn, dialect: str, table_name: str, columns: set[str], column_name: str, ddl: str) -> None:
    if column_name in columns:
        return
    if dialect == "sqlite":
        ddl = ddl.replace("INT ", "INTEGER ")
    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"))
    columns.add(column_name)


def make_token_nullable(conn, dialect: str, table_name: str) -> None:
    if dialect in {"mysql", "mariadb"}:
        conn.execute(text(f"ALTER TABLE {table_name} MODIFY COLUMN active_token VARCHAR(128) NULL DEFAULT NULL"))

