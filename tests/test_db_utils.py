# tests/test_db_utils.py
import os
import gc
import sqlite3
import pytest

# Isolated test DB path before import
os.environ['TEST_DB_PATH'] = 'test_db_utils_gen.sqlite'

from app.utils.db import (  # relative import per package
    get_db_path,
    get_db,
    table_exists,
    get_all_messages,
    fetch_counts,
    fetch_by_statuses,
    fetch_by_interception,
)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    path = get_db_path()
    if os.path.exists(path):
        os.remove(path)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE email_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER,
            status TEXT,
            interception_status TEXT,
            direction TEXT,
            sender TEXT,
            recipients TEXT,
            subject TEXT,
            original_uid TEXT,
            original_internaldate TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    seed_rows = [
        # account_id, status, interception_status, direction, subject, original_uid, original_internaldate
        (1, 'PENDING',   None,       'inbound',  'Pending A1', None,   None),
        (1, 'PENDING',   'HELD',     'inbound',  'Held A1',    'UID1001', '2025-10-01T12:00:00'),
        (1, 'APPROVED',  None,       'inbound',  'Approved A', None,   None),
        (1, 'DELIVERED', 'RELEASED', 'inbound',  'Released A', None,   None),
        (1, 'SENT',      None,       'outbound', 'Sent A1',    None,   None),
        (2, 'SENT',      None,       'outbound', 'Sent B1',    None,   None),
        (2, 'DELIVERED', 'RELEASED', 'inbound',  'Released B1',None,   None),
        (2, 'DELIVERED', None,       'inbound',  'Delivered B Plain', None, None),
        (2, 'REJECTED',  None,       'inbound',  'Rejected B1',None,   None),
    ]
    cur.executemany("""
        INSERT INTO email_messages
        (account_id, status, interception_status, direction, subject, original_uid, original_internaldate)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, seed_rows)
    conn.commit()
    conn.close()
    yield
    gc.collect()
    try:
        if os.path.exists(path):
            os.remove(path)
    except PermissionError:
        pass

def test_get_db_path_env():
    assert get_db_path() == 'test_db_utils_gen.sqlite'

def test_dynamic_db_path_getattr():
    import app.utils.db as m
    assert getattr(m, 'DB_PATH') == 'test_db_utils_gen.sqlite'

def test_getattr_unknown_raises():
    import app.utils.db as m
    with pytest.raises(AttributeError):
        getattr(m, 'NON_EXISTENT_CONST')

def test_table_exists_true_false():
    assert table_exists('email_messages') is True
    assert table_exists('not_real') is False

def test_fetch_counts_global():
    c = fetch_counts()
    assert c['total'] == 9
    assert c['pending'] == 2
    assert c['approved'] == 1
    assert c['rejected'] == 1
    assert c['sent'] == 2
    assert c['held'] == 1
    assert c['released'] == 6  # Approved + Released A + Sent A1 + Sent B1 + Released B1 + Delivered B Plain

def test_fetch_counts_account1():
    c1 = fetch_counts(account_id=1)
    assert c1['total'] == 5
    assert c1['pending'] == 2
    assert c1['approved'] == 1
    assert c1['rejected'] == 0
    assert c1['sent'] == 1
    assert c1['held'] == 1
    assert c1['released'] == 3  # Approved A, Released A, Sent A1

def test_fetch_counts_account2():
    c2 = fetch_counts(account_id=2)
    assert c2['total'] == 4
    assert c2['pending'] == 0
    assert c2['approved'] == 0
    assert c2['rejected'] == 1
    assert c2['sent'] == 1
    assert c2['held'] == 0
    assert c2['released'] == 3  # Sent B1, Released B1, Delivered B Plain

def test_get_all_messages_no_filter_limit():
    # Insert extra rows to test limit
    conn = get_db(); cur = conn.cursor()
    for i in range(10):
        cur.execute("INSERT INTO email_messages (account_id, status, subject) VALUES (3,'PENDING',?)", (f'Extra {i}',))
    conn.commit(); conn.close()
    rows = get_all_messages(limit=3)
    assert len(rows) == 3  # newest 3 only

def test_get_all_messages_filter_held():
    held = get_all_messages(status_filter='HELD')
    assert len(held) == 1 and held[0]['subject'] == 'Held A1'

def test_get_all_messages_filter_released():
    released = get_all_messages(status_filter='RELEASED')
    subs = {r['subject'] for r in released}
    assert {'Approved A','Released A','Sent A1','Sent B1','Released B1','Delivered B Plain'}.issubset(subs)

def test_get_all_messages_filter_pending():
    pending = get_all_messages(status_filter='PENDING')
    subs = {r['subject'] for r in pending}
    assert subs == {'Pending A1','Held A1'}

def test_fetch_by_statuses_empty():
    assert fetch_by_statuses([]) == []

def test_fetch_by_statuses_sent_delivered_subjects():
    rows = fetch_by_statuses(['SENT','DELIVERED'])
    subs = {r['subject'] for r in rows}
    expected = {'Sent A1','Sent B1','Released A','Released B1','Delivered B Plain'}
    assert expected.issubset(subs)

def test_fetch_by_interception_empty():
    assert fetch_by_interception([]) == []

def test_fetch_by_interception_held_released_subjects():
    rows = fetch_by_interception(['HELD','RELEASED'])
    subs = {r['subject'] for r in rows}
    assert subs == {'Held A1','Released A','Released B1'}

def test_original_uid_internaldate_present_for_held():
    held = get_all_messages(status_filter='HELD')
    assert held[0]['original_uid'] == 'UID1001'
    assert held[0]['original_internaldate'].startswith('2025-10-01T')

def test_fetch_by_statuses_limit():
    # Add multiple SENT rows then limit
    conn = get_db(); cur = conn.cursor()
    for i in range(5):
        cur.execute("INSERT INTO email_messages (account_id, status, subject) VALUES (4,'SENT',?)", (f'Sent Extra {i}',))
    conn.commit(); conn.close()
    rows = fetch_by_statuses(['SENT'], limit=3)
    assert len(rows) == 3
