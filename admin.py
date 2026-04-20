"""
AI BI Copilot - Admin Panel
============================
Use this script to manage subscription keys and users.

Usage:
    python admin.py generate 5          # Generate 5 new 30-day keys
    python admin.py generate 3 90       # Generate 3 new 90-day keys
    python admin.py list-keys           # List all subscription keys
    python admin.py list-users          # List all registered users
    python admin.py reset-device user@email.com   # Unbind a user's device
    python admin.py set-sub user@email.com 2026-12-31  # Manually set subscription expiry
"""

import sqlite3
import os
import sys
import secrets
import string

AUTH_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auth.db')

def get_conn():
    conn = sqlite3.connect(AUTH_DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def generate_key():
    chars = string.ascii_uppercase + string.digits
    parts = [''.join(secrets.choice(chars) for _ in range(4)) for _ in range(4)]
    return '-'.join(parts)

def cmd_generate(count=5, days=30):
    conn = get_conn()
    keys = []
    for _ in range(count):
        key = generate_key()
        conn.execute("INSERT INTO subscription_keys (key, days) VALUES (?, ?)", (key, days))
        keys.append(key)
    conn.commit()
    conn.close()

    print("")
    print("[OK] Generated %d subscription key(s) (%d days each):" % (count, days))
    print("")
    print("-" * 30)
    for k in keys:
        print("  " + k)
    print("-" * 30)
    print("")
    print("Share these keys with your customers.")
    print("")

def cmd_list_keys():
    conn = get_conn()
    rows = conn.execute("SELECT key, days, used_by, used_at, created_at FROM subscription_keys ORDER BY id DESC").fetchall()
    conn.close()

    if not rows:
        print("")
        print("No subscription keys found. Run: python admin.py generate 5")
        print("")
        return

    print("")
    print("%-22s %5s  %-14s %-30s %s" % ("KEY", "DAYS", "STATUS", "USED BY", "CREATED"))
    print("-" * 100)
    for key, days, used_by, used_at, created_at in rows:
        status = "[USED]" if used_by else "[AVAILABLE]"
        used_by_display = used_by or ""
        print("  %-20s %5d  %-14s %-30s %s" % (key, days, status, used_by_display, created_at))
    print("")

def cmd_list_users():
    conn = get_conn()
    rows = conn.execute("SELECT email, device_id, subscription_expiry, created_at FROM users ORDER BY id DESC").fetchall()
    conn.close()

    if not rows:
        print("")
        print("No registered users found.")
        print("")
        return

    print("")
    print("%-35s %-15s %-14s %s" % ("EMAIL", "DEVICE", "SUB EXPIRY", "REGISTERED"))
    print("-" * 90)
    for email, device_id, sub_exp, created in rows:
        device_short = (device_id[:12] + "...") if device_id else "Not bound"
        sub_display = sub_exp or "None"
        print("  %-33s %-15s %-14s %s" % (email, device_short, sub_display, created))
    print("")

def cmd_reset_device(email):
    conn = get_conn()
    result = conn.execute("UPDATE users SET device_id = NULL WHERE email = ?", (email.lower().strip(),))
    conn.commit()
    conn.close()

    if result.rowcount > 0:
        print("")
        print("[OK] Device binding cleared for %s. They can now login from a new device." % email)
        print("")
    else:
        print("")
        print("[ERROR] No user found with email: %s" % email)
        print("")

def cmd_set_sub(email, expiry_date):
    conn = get_conn()
    result = conn.execute("UPDATE users SET subscription_expiry = ? WHERE email = ?", (expiry_date, email.lower().strip()))
    conn.commit()
    conn.close()

    if result.rowcount > 0:
        print("")
        print("[OK] Subscription for %s set to expire on %s." % (email, expiry_date))
        print("")
    else:
        print("")
        print("[ERROR] No user found with email: %s" % email)
        print("")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "generate":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        cmd_generate(count, days)
    elif command == "list-keys":
        cmd_list_keys()
    elif command == "list-users":
        cmd_list_users()
    elif command == "reset-device":
        if len(sys.argv) < 3:
            print("Usage: python admin.py reset-device user@email.com")
        else:
            cmd_reset_device(sys.argv[2])
    elif command == "set-sub":
        if len(sys.argv) < 4:
            print("Usage: python admin.py set-sub user@email.com 2026-12-31")
        else:
            cmd_set_sub(sys.argv[2], sys.argv[3])
    else:
        print("Unknown command: " + command)
        print(__doc__)
