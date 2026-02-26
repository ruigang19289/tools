import json
try:
    import psycopg2
    from psycopg2 import sql
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    psycopg2 = None
    sql = None
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

# 连接缓存
connections = {}


def get_connection(connection_id):
    """根据 connection_id 获取数据库连接"""
    return connections.get(connection_id)


def get_connection_by_params(host, port, database, user, password):
    """根据参数获取或创建数据库连接"""
    key = f"{host}:{port}:{database}:{user}"
    return connections.get(key)


def set_connection(key, conn):
    """保存连接"""
    connections[key] = conn


def close_connection(key):
    """关闭并移除连接"""
    if key in connections:
        try:
            connections[key].close()
        except Exception:
            pass
        del connections[key]


@csrf_exempt
@require_http_methods(["POST"])
def connect(request):
    """连接到 PostgreSQL 数据库"""
    if not PSYCOPG2_AVAILABLE:
        return JsonResponse({
            'status': 'error',
            'error': 'psycopg2 module not available. Please install: pip install psycopg2-binary'
        }, status=400)

    data = json.loads(request.body)

    host = data.get('host', 'localhost')
    port = int(data.get('port', 5432))
    database = data.get('database', 'postgres')
    user = data.get('username', 'postgres')
    password = data.get('password', '')

    try:
        # 测试连接
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            connect_timeout=10
        )
        conn.autocommit = True

        # 保存连接
        key = f"{host}:{port}:{database}:{user}"
        set_connection(key, conn)

        # 获取当前数据库的表和视图（不包含序列）
        tables = []
        try:
            with conn.cursor() as cursor:
                # 只查询表和视图
                cursor.execute("""
                    SELECT
                        schemaname,
                        tablename as name,
                        'table' as type,
                        tableowner as owner
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    UNION ALL
                    SELECT
                        schemaname,
                        viewname as name,
                        'view' as type,
                        viewowner as owner
                    FROM pg_views
                    WHERE schemaname = 'public'
                    ORDER BY name
                """)
                rows = cursor.fetchall()
                for row in rows:
                    tables.append({
                        'schema': row[0],
                        'name': row[1],
                        'type': row[2],
                        'owner': row[3]
                    })
        except Exception as e:
            print(f"Error fetching tables: {e}")
            pass

        return JsonResponse({
            'status': 'success',
            'message': '连接成功',
            'connection_id': key,
            'server_version': conn.server_version,
            'database': database,
            'tables': tables,
            'connection_params': {
                'host': host,
                'port': port,
                'database': database,
                'user': user
            }
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def disconnect(request):
    """断开数据库连接"""
    if not PSYCOPG2_AVAILABLE:
        return JsonResponse({
            'status': 'error',
            'error': 'psycopg2 module not available. Please install: pip install psycopg2-binary'
        }, status=400)

    data = json.loads(request.body)
    connection_id = data.get('connection_id')

    if connection_id:
        close_connection(connection_id)
        return JsonResponse({'status': 'success', 'message': '已断开连接'})

    return JsonResponse({'status': 'error', 'error': '未指定连接'}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def get_databases(request):
    """获取数据库列表"""
    if not PSYCOPG2_AVAILABLE:
        return JsonResponse({
            'status': 'error',
            'error': 'psycopg2 module not available. Please install: pip install psycopg2-binary'
        }, status=400)

    data = json.loads(request.body)
    connection_id = data.get('connection_id')

    if not connection_id:
        return JsonResponse({'status': 'error', 'error': '未指定连接'}, status=400)

    conn = get_connection(connection_id)
    if not conn:
        return JsonResponse({'status': 'error', 'error': '连接已失效，请重新连接'}, status=400)

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT datname, datowner, encoding, datcollate, datctype
                FROM pg_database
                WHERE datistemplate = false
                ORDER BY datname
            """)
            rows = cursor.fetchall()
            databases = []
            for row in rows:
                databases.append({
                    'name': row[0],
                    'owner': row[1],
                    'encoding': row[2],
                    'collate': row[3],
                    'ctype': row[4]
                })
            return JsonResponse({'status': 'success', 'databases': databases})
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def get_tables(request):
    """获取指定数据库的表列表"""
    if not PSYCOPG2_AVAILABLE:
        return JsonResponse({
            'status': 'error',
            'error': 'psycopg2 module not available. Please install: pip install psycopg2-binary'
        }, status=400)

    data = json.loads(request.body)
    connection_id = data.get('connection_id')
    database = data.get('database')

    if not connection_id or not database:
        return JsonResponse({'status': 'error', 'error': '参数不完整'}, status=400)

    try:
        # 先连接到指定数据库
        conn_info = connection_id.split(':')
        if len(conn_info) >= 4:
            host, port, _, user = conn_info[0], int(conn_info[1]), conn_info[2], conn_info[3]
            # 找到原始密码（从现有连接获取）
            orig_conn = get_connection(connection_id)
            if orig_conn:
                password = orig_conn.info.password if hasattr(orig_conn.info, 'password') else ''
            else:
                return JsonResponse({'status': 'error', 'error': '连接已失效'}, status=400)

            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                connect_timeout=10
            )
            conn.autocommit = True
        else:
            return JsonResponse({'status': 'error', 'error': '无效的连接ID'}, status=400)

        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    tablename,
                    tableowner,
                    schemaname,
                    hasindexes,
                    hasrules,
                    hastriggers
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
            """)
            rows = cursor.fetchall()
            tables = []
            for row in rows:
                tables.append({
                    'name': row[0],
                    'owner': row[1],
                    'schema': row[2],
                    'has_indexes': row[3],
                    'has_rules': row[4],
                    'has_triggers': row[5]
                })

            conn.close()
            return JsonResponse({'status': 'success', 'tables': tables})
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def get_table_info(request):
    """获取表结构信息"""
    if not PSYCOPG2_AVAILABLE:
        return JsonResponse({
            'status': 'error',
            'error': 'psycopg2 module not available. Please install: pip install psycopg2-binary'
        }, status=400)

    data = json.loads(request.body)
    connection_id = data.get('connection_id')
    database = data.get('database')
    table = data.get('table')

    if not all([connection_id, database, table]):
        return JsonResponse({'status': 'error', 'error': '参数不完整'}, status=400)

    try:
        conn = get_connection(connection_id)
        if not conn:
            return JsonResponse({'status': 'error', 'error': '连接已失效'}, status=400)

        # 临时连接到指定数据库
        conn_info = connection_id.split(':')
        host, port, _, user = conn_info[0], int(conn_info[1]), conn_info[2], conn_info[3]
        password = conn.info.password if hasattr(conn.info, 'password') else ''

        temp_conn = psycopg2.connect(
            host=host, port=port, database=database, user=user, password=password
        )
        temp_conn.autocommit = True

        with temp_conn.cursor() as cursor:
            # 获取列信息
            cursor.execute("""
                SELECT
                    a.attname AS column_name,
                    pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
                    a.attnotnull AS not_null,
                    a.atthasdef AS has_default,
                    pg_get_expr(d.adbin, d.adrelid) AS default_value,
                    c.column_comment AS comment
                FROM pg_catalog.pg_attribute a
                LEFT JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
                LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
                LEFT JOIN pg_catalog.pg_description dsc ON dsc.objoid = a.attrelid AND dsc.objsubid = a.attnum
                LEFT JOIN information_schema.columns c ON c.table_schema = 'public'
                    AND c.table_name = %s AND c.column_name = a.attname
                WHERE a.attrelid = %s::regclass
                    AND a.attnum > 0
                    AND NOT a.attisdropped
                ORDER BY a.attnum
            """, [table, table])

            columns = []
            for row in cursor.fetchall():
                columns.append({
                    'name': row[0],
                    'type': row[1],
                    'not_null': row[2],
                    'has_default': row[3],
                    'default': row[4]
                })

            # 获取索引信息
            cursor.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = %s AND schemaname = 'public'
            """, [table])

            indexes = []
            for row in cursor.fetchall():
                indexes.append({
                    'name': row[0],
                    'definition': row[1]
                })

            # 获取行数
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]

        temp_conn.close()

        return JsonResponse({
            'status': 'success',
            'table': {
                'name': table,
                'columns': columns,
                'indexes': indexes,
                'row_count': row_count
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def execute_query(request):
    """执行 SQL 查询"""
    if not PSYCOPG2_AVAILABLE:
        return JsonResponse({
            'status': 'error',
            'error': 'psycopg2 module not available. Please install: pip install psycopg2-binary'
        }, status=400)

    data = json.loads(request.body)
    connection_id = data.get('connection_id')
    query = data.get('query', '').strip()
    database = data.get('database')

    if not connection_id:
        return JsonResponse({'status': 'error', 'error': '未指定连接'}, status=400)
    if not query:
        return JsonResponse({'status': 'error', 'error': '查询为空'}, status=400)

    try:
        conn = get_connection(connection_id)
        if not conn:
            return JsonResponse({'status': 'error', 'error': '连接已失效'}, status=400)

        # 临时连接到指定数据库
        conn_info = connection_id.split(':')
        host, port, _, user = conn_info[0], int(conn_info[1]), conn_info[2], conn_info[3]
        password = conn.info.password if hasattr(conn.info, 'password') else ''

        temp_conn = psycopg2.connect(
            host=host, port=port, database=database or 'postgres', user=user, password=password
        )
        temp_conn.autocommit = True

        with temp_conn.cursor() as cursor:
            # 只允许 SELECT 查询
            query_upper = query.upper()
            if not (query_upper.startswith('SELECT') or
                     query_upper.startswith('SHOW') or
                     query_upper.startswith('DESCRIBE') or
                     query_upper.startswith('EXPLAIN')):
                temp_conn.close()
                return JsonResponse({
                    'status': 'error',
                    'error': '只允许执行 SELECT、SHOW、DESCRIBE、EXPLAIN 查询'
                }, status=400)

            cursor.execute(query)

            # 获取列名
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            # 获取数据（限制 1000 行）
            rows = cursor.fetchmany(1000)
            data = [dict(zip(columns, row)) for row in rows]

            # 检查是否还有更多数据
            has_more = len(rows) == 1000
            total_rows = cursor.rowcount if cursor.rowcount > 0 else len(data)

        temp_conn.close()

        return JsonResponse({
            'status': 'success',
            'columns': columns,
            'data': data,
            'total_rows': total_rows,
            'has_more': has_more,
            'message': f'返回 {len(data)} 行数据' + (' (还有更多)' if has_more else '')
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def get_schema(request):
    """获取数据库 Schema 信息"""
    if not PSYCOPG2_AVAILABLE:
        return JsonResponse({
            'status': 'error',
            'error': 'psycopg2 module not available. Please install: pip install psycopg2-binary'
        }, status=400)

    data = json.loads(request.body)
    connection_id = data.get('connection_id')

    if not connection_id:
        return JsonResponse({'status': 'error', 'error': '未指定连接'}, status=400)

    conn = get_connection(connection_id)
    if not conn:
        return JsonResponse({'status': 'error', 'error': '连接已失效'}, status=400)

    try:
        with conn.cursor() as cursor:
            # schemas
            cursor.execute("""
                SELECT schema_name, schema_owner
                FROM information_schema.schemata
                WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
                ORDER BY schema_name
            """)
            schemas = [{'name': row[0], 'owner': row[1]} for row in cursor.fetchall()]

            # views
            cursor.execute("""
                SELECT table_name, table_owner, view_definition
                FROM information_schema.views
                WHERE table_schema = 'public'
            """)
            views = [{'name': row[0], 'owner': row[1], 'definition': row[2][:500]} for row in cursor.fetchall()]

            # functions
            cursor.execute("""
                SELECT proname, proowner, pg_get_function_arguments(oid) as args
                FROM pg_proc
                WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            """)
            functions = [{'name': row[0], 'owner': row[1], 'args': row[2]} for row in cursor.fetchall()]

        return JsonResponse({
            'status': 'success',
            'schemas': schemas,
            'views': views,
            'functions': functions
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def get_table_structure(request):
    """获取表结构和关系"""
    if not PSYCOPG2_AVAILABLE:
        return JsonResponse({
            'status': 'error',
            'error': 'psycopg2 module not available'
        }, status=400)

    data = json.loads(request.body)
    connection_id = data.get('connection_id')
    table_name = data.get('table_name')

    if not connection_id or not table_name:
        return JsonResponse({'status': 'error', 'error': '参数不完整'}, status=400)

    conn = get_connection(connection_id)
    if not conn:
        return JsonResponse({'status': 'error', 'error': '连接已失效'}, status=400)

    try:
        with conn.cursor() as cursor:
            # 获取表的列信息
            cursor.execute("""
                SELECT
                    a.attname AS column_name,
                    pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
                    CASE WHEN a.attnotnull THEN 'NO' ELSE 'YES' END AS is_nullable,
                    pg_get_expr(d.adbin, d.adrelid) AS column_default,
                    col_description(a.attrelid, a.attnum) AS description
                FROM pg_catalog.pg_attribute a
                LEFT JOIN pg_catalog.pg_attrdef d ON (a.attrelid = d.adrelid AND a.attnum = d.adnum)
                WHERE a.attrelid = %s::regclass
                    AND a.attnum > 0
                    AND NOT a.attisdropped
                ORDER BY a.attnum
            """, [table_name])

            columns = []
            for row in cursor.fetchall():
                columns.append({
                    'column_name': row[0],
                    'data_type': row[1],
                    'is_nullable': row[2],
                    'column_default': row[3],
                    'description': row[4] or ''
                })

            # 获取外键关系 - 当前表引用的其他表
            cursor.execute("""
                SELECT
                    tc.constraint_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_name = %s
                    AND tc.table_schema = 'public'
            """, [table_name])

            foreign_keys = []
            for row in cursor.fetchall():
                foreign_keys.append({
                    'constraint_name': row[0],
                    'column': row[1],
                    'referenced_table': row[2],
                    'referenced_column': row[3],
                    'direction': 'outgoing'
                })

            # 获取被引用关系 - 其他表引用当前表（通过外键）
            cursor.execute("""
                SELECT
                    tc.constraint_name,
                    tc.table_name AS referencing_table,
                    kcu.column_name AS referencing_column,
                    ccu.column_name AS referenced_column
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND ccu.table_name = %s
                    AND tc.table_schema = 'public'
            """, [table_name])

            referenced_by = []
            for row in cursor.fetchall():
                referenced_by.append({
                    'constraint_name': row[0],
                    'referencing_table': row[1],
                    'referencing_column': row[2],
                    'column': row[3],
                    'direction': 'incoming',
                    'type': 'foreign_key'
                })

            # 查找可能的关联关系 - 基于列名模式（{table_name}_id）
            # 查找所有包含 {table_name}_id 列的表
            pattern_exact = f"{table_name}_id"
            pattern_like = f"%{table_name}%id%"

            cursor.execute("""
                SELECT DISTINCT
                    t.table_name,
                    c.column_name
                FROM information_schema.tables t
                JOIN information_schema.columns c
                    ON t.table_name = c.table_name
                    AND t.table_schema = c.table_schema
                WHERE t.table_schema = 'public'
                    AND t.table_type = 'BASE TABLE'
                    AND (c.column_name = %s OR c.column_name LIKE %s)
                    AND t.table_name != %s
                ORDER BY t.table_name
            """, [pattern_exact, pattern_like, table_name])

            potential_references = []
            candidate_tables = cursor.fetchall()
            print(f"Found {len(candidate_tables)} candidate tables for {table_name}")

            for row in candidate_tables:
                ref_table = row[0]
                ref_column = row[1]

                # 检查是否已经在外键关系中
                already_in_fk = any(
                    r['referencing_table'] == ref_table and r['referencing_column'] == ref_column
                    for r in referenced_by
                )

                if not already_in_fk:
                    # 检查是否有实际数据关联
                    try:
                        cursor.execute(f"""
                            SELECT COUNT(*)
                            FROM {ref_table}
                            WHERE {ref_column} IS NOT NULL
                            LIMIT 1
                        """)
                        has_data = cursor.fetchone()[0] > 0
                        print(f"  {ref_table}.{ref_column}: has_data={has_data}")

                        if has_data:
                            potential_references.append({
                                'referencing_table': ref_table,
                                'referencing_column': ref_column,
                                'column': 'id',  # 假设引用主键 id
                                'direction': 'incoming',
                                'type': 'potential',
                                'constraint_name': f'潜在关联 (无外键约束)'
                            })
                    except Exception as e:
                        print(f"  Error checking {ref_table}.{ref_column}: {e}")
                        pass

            print(f"Found {len(potential_references)} potential references")
            # 合并外键关系和潜在关系
            referenced_by.extend(potential_references)

        return JsonResponse({
            'status': 'success',
            'table_name': table_name,
            'columns': columns,
            'foreign_keys': foreign_keys,
            'referenced_by': referenced_by
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)



@csrf_exempt
@require_http_methods(["POST"])
def get_table_data(request):
    """获取表数据"""
    if not PSYCOPG2_AVAILABLE:
        return JsonResponse({
            'status': 'error',
            'error': 'psycopg2 module not available'
        }, status=400)

    data = json.loads(request.body)
    connection_id = data.get('connection_id')
    table_name = data.get('table_name')
    limit = data.get('limit', 100)
    offset = data.get('offset', 0)

    if not connection_id or not table_name:
        return JsonResponse({'status': 'error', 'error': '参数不完整'}, status=400)

    conn = get_connection(connection_id)
    if not conn:
        return JsonResponse({'status': 'error', 'error': '连接已失效'}, status=400)

    try:
        with conn.cursor() as cursor:
            # 获取总行数
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_rows = cursor.fetchone()[0]

            # 检查表是否有 id 列
            cursor.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = %s AND column_name = 'id'
            """, [table_name])
            has_id = cursor.fetchone() is not None

            # 获取数据，如果有 id 列则按 id 排序
            if has_id:
                cursor.execute(f"SELECT * FROM {table_name} ORDER BY id ASC LIMIT %s OFFSET %s", [limit, offset])
            else:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT %s OFFSET %s", [limit, offset])

            # 获取列名
            columns = [desc[0] for desc in cursor.description]

            # 获取数据
            rows = cursor.fetchall()
            data_list = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    if value is None:
                        row_dict[col] = None
                    elif isinstance(value, (str, int, float, bool)):
                        row_dict[col] = value
                    else:
                        row_dict[col] = str(value)
                data_list.append(row_dict)

        return JsonResponse({
            'status': 'success',
            'table_name': table_name,
            'columns': columns,
            'data': data_list,
            'total_rows': total_rows,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)
