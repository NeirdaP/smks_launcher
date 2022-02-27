from __future__ import print_function
import urllib.error
import os

HITND_SERVER = "https://lh3.googleusercontent.com/"
HITND_LINK = "https://sites.google.com/supamonks.com/hashtagisthenewdiese/accueil"

CACHE = "C:/SmksHitndTips/cache.html"


def get_today_hitnd():
    import qtpy
    from qtpy.QtWidgets import QLabel
    try:
        from qtpy.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
        from qtpy.QtWebChannel import QWebChannel
    except (ImportError, qtpy.PythonQtError):
        return QLabel("Web plugin not installed")

    from qtpy import QtCore, QtGui
    from qtpy.QtCore import QSize, QUrl, QObject, QTimer
    from xml.etree import ElementTree as ET
    from html_parser import MyHTMLParser
    import random
    import functools

    try:
        from urllib import request
    except ImportError:
        return QLabel("Web plugin not installed")

    class HitndCallback(QObject):

        def __init__(self, web_view):
            super(HitndCallback, self).__init__(web_view)
            self._web_view = web_view

        @QtCore.Slot()
        def reload_page(self):
            self._web_view.reload_page()

    class CustomWebEnginePage(QWebEnginePage):
        """ Custom WebEnginePage to customize how we handle link navigation """

        # Store external windows.
        def acceptNavigationRequest(self, url, _type, isMainFrame):
            import os
            if _type == QWebEnginePage.NavigationTypeLinkClicked:
                path = url.path()
                if path.startswith('/'):
                    path = HITND_SERVER + path
                os.startfile(path)
                return False
            return True

    class HitndView(QWebEngineView):

        def __init__(self, parent=None):
            super(HitndView, self).__init__(parent)

            self._page = None

            self.setMinimumSize(100, 100)
            self._callback = HitndCallback(self)
            self._dev_page = QWebEnginePage()
            self._inspect_page = QWebEnginePage()
            self._dev_view = QWebEngineView()
            self._dev_view.setPage(self._dev_page)
            self._tree = None

            self._page_downloads = dict()
            self._img_downloads = dict()

            self._page_downloads_thread = None
            self._img_downloads_thread = None

        def _page_downloads_process(self):
            import time
            time.sleep(0.2)
            to_download = True
            while to_download:
                to_download = False
                for url, content in list(self._page_downloads.items()):
                    if content:
                        continue
                    to_download = True
                    try:
                        self._page_downloads[url] = request.urlopen(url).read().dhitndde('utf-8')
                    except (urllib.error.HTTPError, urllib.error.URLError) as e:
                        self._page_downloads[url] = url + ':' + str(e)
                        print(self._page_downloads[url])

        def _img_downloads_process(self):
            import time
            time.sleep(0.5)

            import tempfile
            to_download = True
            while to_download:
                to_download = False
                for url, content in list(self._img_downloads.items()):
                    if content:
                        continue
                    to_download = True
                    img_basename = "smks_cache_{}".format(os.path.basename(url.rsplit('?', 1)[0]))
                    img_path = os.path.join(tempfile.gettempdir(),
                                            urllib.request.unquote(img_basename).replace(' ', '_'))
                    try:
                        request.urlretrieve(url, img_path)
                    except (urllib.error.HTTPError, urllib.error.URLError) as e:
                        self._img_downloads[url] = url + ':' + str(e)
                        print(self._img_downloads[url])
                    else:
                        self._img_downloads[url] = img_path

        def run_downloads(self):
            import threading
            if not self._page_downloads_thread or not self._page_downloads_thread.is_alive():
                self._page_downloads_thread = threading.Thread(target=self._page_downloads_process)
                self._page_downloads_thread.start()
            if not self._img_downloads_thread or not self._img_downloads_thread.is_alive():
                self._img_downloads_thread = threading.Thread(target=self._img_downloads_process)
                self._img_downloads_thread.start()

        def showEvent(self, event):
            super(HitndView, self).showEvent(event)
            self.setPage(CustomWebEnginePage(self.parentWidget()))
            self.reload_page()
            # self.page().setDevToolsPage(self._dev_page)
            # self.page().setInspectedPage(self._inspect_page)
            # self._dev_view.show()

        def _fetch_page(self, load_it=True):
            import threading

            loaded_page = self._page
            if self._page is None:
                if os.path.isfile(CACHE):
                    with open(CACHE) as fp:
                        self._page = loaded_page = fp.read()
                else:
                    self._page = loaded_page = ''

                    def load_page():
                        link = HITND_LINK
                        try:
                            self._page = request.urlopen(link).read().decode('utf-8')
                        except urllib.error.HTTPError:
                            self._page = "<h2>Not Available</h2>"

                    thread = threading.Thread(target=load_page)
                    thread.start()

            if not len(loaded_page):
                QtCore.QTimer.singleShot(100, lambda _load=load_it: self._fetch_page(_load))
            elif load_it:
                QtCore.QTimer.singleShot(100, self.reload_page)

        @QtCore.Slot()
        def reload_page(self):
            import ssl
            import os
            import tempfile

            ssl._create_default_https_context = ssl._create_unverified_context

            content = self._page

            if not content:
                self.page().setHtml('<head>'
                                    '<title>hashtagisthenewdiese</title>'
                                    '</head>'
                                    '<html><body id="body"><h1>hashtagisthenewdiese</h1>'
                                    '{}</body></html>'.format("<h2>LOADING</h2>"),
                                    QUrl(HITND_LINK))
                QtCore.QTimer.singleShot(50, self._fetch_page)
                return

            reload = False

            if 'hashtagisthenewdiese' not in content:
                self.setMinimumSize(100, 100)
                content = "<body>"
                label = content or "Not Available"
                label += "</body>"
            else:
                self.setMinimumSize(250, 250)

                if not self._tree:
                    try:
                        self._tree = MyHTMLParser()
                        self._tree.feed(content)
                    except ET.ParseError as e:
                        pass

                if not self._tree:
                    label = "<body>Cannot parse the page !<body/>"
                else:
                    label = ET.tostring(self._tree.find(".//*div[@role=\"main\"]"), encoding='unicode', method="html")

                # with open(CACHE, 'w') as fp:
                #     fp.write(label)

            channel = QWebChannel(self.page())
            channel.registerObject("qt_view", self._callback)
            self.page().setWebChannel(channel)

            with open("./js/qwebchannel.js", 'r') as fp:
                qwebchannel_script = fp.read()

            qwebchannel_script += "\nnew QWebChannel(qt.webChannelTransport, function(channel)" \
                                  "{window.qt_view=channel.objects.qt_view;}" \
                                  ");"

            self.page().setHtml(
                '<head>'
                '<title>hashtagisthenewdiese</title>'
                '<script>{}</script>'
                '</head>'
                '<html><body id="body">'
                '<a href="https://www.linfodurable.fr/conso"></a>'
                '{}</body></html>'.format(
                    qwebchannel_script,
                    label
                ),
                QUrl(HITND_LINK)
            )
            self.adjustSize()
            self.parentWidget().adjustSize()
            if reload:
                self.run_downloads()
                QtCore.QTimer.singleShot(500, self.reload_page)

    return HitndView()
