#!/usr/bin/env python3
"""Display campaign schedules, their groups and timing info."""

import sqlite3
import json
import files


DAY_MAP = {
    'monday': 'lunes',
    'tuesday': 'martes',
    'wednesday': 'miercoles',
    'thursday': 'jueves',
    'friday': 'viernes',
    'saturday': 'sabado',
    'sunday': 'domingo',
}


def main():
    conn = sqlite3.connect(files.main_db)
    cur = conn.cursor()

    cur.execute(
        """SELECT id, schedule_name, frequency, schedule_json, is_active,
                  next_send_telegram, group_ids
           FROM campaign_schedules ORDER BY id"""
    )
    schedules = cur.fetchall()

    if not schedules:
        print("No hay programaciones registradas")
        return

    for sched_id, name, freq, sched_json, active, next_send, group_ids in schedules:
        estado = "activa" if active else "inactiva"
        print(f"\nProgramación {sched_id}: {name} ({estado})")
        if freq:
            print(f"  Frecuencia: {freq}")

        if sched_json:
            try:
                data = json.loads(sched_json)
            except Exception:
                data = {}
            if data:
                print("  Horarios:")
                for day, hours in data.items():
                    d = DAY_MAP.get(day.lower(), day)
                    if hours:
                        print(f"    {d} {', '.join(hours)}")

        if next_send:
            print(f"  Próximo envío Telegram: {next_send}")

        groups = []
        if group_ids:
            ids = [int(g) for g in str(group_ids).split(',') if g.strip()]
            if ids:
                placeholders = ",".join("?" for _ in ids)
                cur.execute(
                    f"SELECT group_id, topic_id FROM target_groups WHERE id IN ({placeholders})",
                    ids,
                )
                groups = cur.fetchall()
        if not groups:
            print("  (sin grupos asociados)")
        else:
            for gid, topic in groups:
                topic_str = f"/{topic}" if topic is not None else ""
                print(f"  {gid}{topic_str}")

    conn.close()


if __name__ == "__main__":
    main()