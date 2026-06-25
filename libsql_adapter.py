"""
libsql → SQLAlchemy pysqlite 方言适配器

libsql.Connection 实现了 DBAPI 2.0 基本接口，但缺少 SQLAlchemy
pysqlite 方言需要的一些可选方法（如 create_function / create_aggregate）。
此适配器补全这些缺失的方法，使 libsql 可以作为 SQLAlchemy 的
creator 连接工厂使用。
"""


class LibSQLAdapter:
    """包装 libsql.Connection，补全 pysqlite 方言兼容性"""

    def __init__(self, libsql_conn):
        self._conn = libsql_conn

    def __getattr__(self, name):
        # 代理所有未显式定义的方法/属性到原始 libsql.Connection
        return getattr(self._conn, name)

    # ---- 以下是 pysqlite 方言需要但 libsql 不支持的方法 ----

    def create_function(self, name, num_params, func, **kwargs):
        """pysqlite 方言用此注册 REGEXP 等自定义函数，no-op"""
        pass

    def create_aggregate(self, name, num_params, aggregate_class, **kwargs):
        """pysqlite 方言用此注册自定义聚合函数，no-op"""
        pass
