"""
数据库初始化模块 (T006)
使用SQLAlchemy管理SQLite数据库连接，启用外键约束。
生产环境可切换PostgreSQL连接字符串。
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# 数据库文件路径，默认存储在项目后端目录
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./eval_platform.db"
)

# 创建引擎，SQLite需特殊配置
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False  # 生产环境关闭SQL日志
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 声明式基类
class Base(DeclarativeBase):
    pass


def init_db():
    """
    初始化数据库：创建所有表 + 启用SQLite外键约束。
    在FastAPI lifespan中调用。
    """
    # SQLite外键约束默认关闭，需要在每次连接时启用
    if "sqlite" in DATABASE_URL:

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ARG001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    # 导入所有模型以确保表被创建
    from models.dataset import Dataset  # noqa: F401
    from models.task import Task  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db():
    """
    获取数据库会话的依赖注入生成器。
    FastAPI Depends中使用，请求结束后自动关闭会话。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
