import traceback
try:
    with open("run_final_recency_calendar_sweep.py", "r", encoding="utf-8") as f:
        exec(f.read())
except Exception as e:
    with open("tb.txt", "w", encoding="utf-8") as out:
        traceback.print_exc(file=out)
