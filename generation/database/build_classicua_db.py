import argparse
import hashlib
import pathlib
import shutil
import sqlite3
import sys
import tempfile

from generation.utils.utils import classicua_root

# Builds ClassicUA/dev/database/classicua.db, which its dev/gen_*_lua.py scripts read. Replaces the
# hand copy behind the "Update DB" commits.
#
# Not to be confused with generation/quests/classicua.db, an input to quests.py that merge_with_db
# folds hand fixes forward from. Nothing here writes to it.
#
# Run as a script it rebuilds every table; quests.py, npc.py and objects.py call update_table() at the
# end of their run to replace their own table after the owner types UPDATE.

REPO_ROOT = pathlib.Path(__file__).parents[2]

SOURCES = {
    'quests': (
        REPO_ROOT / 'generation' / 'quests' / 'cache' / 'quests.db',
        '''CREATE TABLE quests (
                id INTEGER NOT NULL,
                expansion TEXT NOT NULL,
                title TEXT,
                objective TEXT,
                description TEXT,
                progress TEXT,
                completion TEXT,
                cat TEXT NOT NULL,
                side TEXT NOT NULL,
                type TEXT NOT NULL,
                lvl INTEGER NOT NULL,
                rlvl INTEGER NOT NULL,
                UNIQUE("id","expansion")
        )''',
    ),
    'npcs': (
        REPO_ROOT / 'generation' / 'npc' / 'cache' / 'npcs.db',
        '''CREATE TABLE npcs (
                id INT NOT NULL,
                expansion TEXT,
                name TEXT,
                tag TEXT,
                name_ua TEXT,
                tag_ua TEXT,
                type TEXT,
                boss TEXT,
                classification TEXT,
                location TEXT,
                names TEXT,
                react TEXT
        )''',
    ),
    'objects': (
        REPO_ROOT / 'generation' / 'objects' / 'cache' / 'objects.db',
        '''CREATE TABLE objects (
                id INT NOT NULL,
                expansion TEXT,
                name TEXT,
                name_ua TEXT,
                text_pages INT,
                type TEXT
        )''',
    ),
}


def target_path() -> pathlib.Path:
    root = classicua_root()
    if not root:
        raise Exception('CLASSICUA_ROOT is not set - add it to .env in the repository root')
    return pathlib.Path(root) / 'dev' / 'database' / 'classicua.db'


def update_table(table: str) -> bool:
    # Replaces one table of the addon database in place, once the owner has typed UPDATE.
    source, schema = SOURCES[table]
    target = target_path()
    before = count_rows(target, table)
    after = count_rows(source, table)
    columns = schema_columns(schema)
    same = before is not None and content_hash(target, table, columns) == content_hash(source, table, columns)
    print('-' * 100)
    print(f'{target}: "{table}" holds {"-" if before is None else before} row(s), '
          f'the cache holds {after}, contents {"identical" if same else "CHANGED"}')
    if same:
        print('Nothing to update.')
        return False
    if input(f'Type UPDATE to replace the "{table}" table: ').strip() != 'UPDATE':
        print('Left as is.')
        return False
    conn = sqlite3.connect(f'file:{target.as_posix()}', uri=True)
    try:
        copy_table(conn, source, table, schema)
    finally:
        conn.close()
    print(f'Updated "{table}" in {target}')
    return True


def __columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f'pragma table_info({table})')]


def __read_only(path: pathlib.Path) -> sqlite3.Connection:
    return sqlite3.connect(f'file:{path.as_posix()}?mode=ro', uri=True)


def count_rows(path: pathlib.Path, table: str) -> int:
    # None, not 0, when the table is absent: a missing target has no previous value to compare against.
    if not path.is_file():
        return None
    conn = __read_only(path)
    try:
        if not conn.execute('SELECT 1 FROM sqlite_master WHERE type="table" AND name=?', (table,)).fetchone():
            return None
        return conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    finally:
        conn.close()


def schema_columns(schema: str) -> list[str]:
    conn = sqlite3.connect(':memory:')
    conn.execute(schema)
    return __columns(conn, schema.split('(')[0].split()[-1])


def content_hash(path: pathlib.Path, table: str, columns: list[str] = None) -> str:
    # Rows, not bytes: two SQLite files with the same contents differ byte for byte by page layout.
    if count_rows(path, table) is None:
        return None
    conn = __read_only(path)
    try:
        columns = ', '.join(columns or __columns(conn, table))
        digest = hashlib.sha256()
        for row in conn.execute(f'SELECT {columns} FROM {table} ORDER BY 1, 2'):
            digest.update(repr(row).encode('utf-8'))
        return digest.hexdigest()
    finally:
        conn.close()


def copy_table(target: sqlite3.Connection, source: pathlib.Path, table: str, schema: str) -> int:
    if count_rows(source, table) is None:
        raise Exception(f'No table "{table}" in {source}')

    target.execute(f'DROP TABLE IF EXISTS {table}')
    target.execute(schema)
    target.execute('ATTACH DATABASE ? AS src', (f'file:{source.as_posix()}?mode=ro',))
    try:
        columns = ', '.join(__columns(target, table))
        target.execute(f'INSERT INTO {table} ({columns}) SELECT {columns} FROM src.{table}')
        target.commit()
        return target.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    finally:
        target.execute('DETACH DATABASE src')


def build(target_path: pathlib.Path, write: bool) -> bool:
    before = {table: count_rows(target_path, table) for table in SOURCES}
    before_hashes = {table: content_hash(target_path, table) for table in SOURCES}

    # Stage first, so a failure cannot leave the addon with one fresh table and one stale one.
    staging = pathlib.Path(tempfile.mkdtemp(prefix='classicua_db_')) / 'classicua.db'
    conn = sqlite3.connect(f'file:{staging.as_posix()}', uri=True)  # uri=True so ATTACH accepts a ro source
    after = {}
    try:
        for table, (source, schema) in SOURCES.items():
            after[table] = copy_table(conn, source, table, schema)
        conn.execute('VACUUM')
    finally:
        conn.close()

    print(f'Target: {target_path}')
    print()
    print(f'  {"table":<8}{"before":>10}{"after":>10}{"delta":>10}   contents')
    unchanged = True
    for table in SOURCES:
        previous = before[table]
        delta = 'n/a' if previous is None else f'{after[table] - previous:+d}'
        same = before_hashes[table] is not None and before_hashes[table] == content_hash(staging, table)
        unchanged = unchanged and same
        print(f'  {table:<8}{"-" if previous is None else previous:>10}{after[table]:>10}{delta:>10}'
              f'   {"identical" if same else "CHANGED"}')
    print()

    if write:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(staging, target_path)
        print(f'Written: {target_path}')
    else:
        print('Nothing written. Pass --write to install it.')

    shutil.rmtree(staging.parent, ignore_errors=True)
    return unchanged


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Build ClassicUA/dev/database/classicua.db from the quests and npc caches.')
    parser.add_argument('--classicua', type=pathlib.Path,
                        help='ClassicUA checkout (default: CLASSICUA_ROOT from .env)')
    parser.add_argument('--write', action='store_true',
                        help='install the rebuilt database (default: report the deltas and stop)')
    args = parser.parse_args()

    root = args.classicua or classicua_root()
    if not root:
        print('CLASSICUA_ROOT is not set - add it to .env in the repository root, or pass --classicua.',
              file=sys.stderr)
        return 2

    for table, (source, _) in SOURCES.items():
        if not source.is_file():
            print(f'Missing source for "{table}": {source}', file=sys.stderr)
            return 2

    build(pathlib.Path(root) / 'dev' / 'database' / 'classicua.db', args.write)
    return 0


if __name__ == '__main__':
    sys.exit(main())
