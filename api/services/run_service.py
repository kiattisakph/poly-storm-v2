def get_latest_runs(conn, city_id: str | None, limit: int) -> list[dict]:
    where = "WHERE r.action != 'taf_update'"
    params = []

    if city_id:
        where += " AND r.city_id = %s"
        params.append(city_id)

    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            r.id, r.taf_raw, r.tx_temp, r.tn_temp,
            r.metar_temp, r.wind_dir, r.action, r.note,
            r.updated_date, r.created_at,
            c.name AS city_name, c.station
        FROM run_logs r
        JOIN cities c ON c.id = r.city_id
        {where}
        ORDER BY r.created_at DESC
        LIMIT %s
    """, params + [limit])

    return [dict(r) for r in cur.fetchall()]
