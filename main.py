from app.application import Application
from ui.gui import LibraryGUI


if __name__ == "__main__":
    application = Application()
    try:
        LibraryGUI(application).run()
    finally:
        application.database.close()
