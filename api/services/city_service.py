def get_all_cities(conn) -> list[dict]:
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, station, latitude, longitude,
               timezone, strategy_code, active
        FROM cities
        ORDER BY name
    """)
    return [dict(r) for r in cur.fetchall()]