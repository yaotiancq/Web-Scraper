import subprocess
import webbrowser
import os
import threading


def start_flask():
    os.chdir('../src')
    subprocess.call('flask run --port=8000', shell=True)


def open_html():
    abs_path = os.path.abspath('../Front-end/home.html')
    webbrowser.open_new_tab(f'file://{abs_path}')


if __name__ == '__main__':
    os.environ['FLASK_APP'] = 'flask_app.py'
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.start()
    open_html()
    flask_thread.join()
