import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from csv_to_png_table import render_csv_to_png

TABLES_DIR = Path("tables")

class AnyCSVChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        path = Path(event.src_path)
        if path.suffix == ".csv" and path.parent == TABLES_DIR:
            try:
                print(f"🔄 Detected change in {path.name}")
                render_csv_to_png(path)
            except Exception as e:
                print(f"❌ Error rendering {path.name}: {e}")

def start_watching():
    print(f"👀 Watching all CSVs in: {TABLES_DIR.resolve()}")
    observer = Observer()
    observer.schedule(AnyCSVChangeHandler(), path=str(TABLES_DIR), recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_watching()

