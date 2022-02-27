from __future__ import print_function
import urllib.error
import os


ECO_SERVER = "https://www.linfodurable.fr"
ECO_LINK = "{}/conso".format(ECO_SERVER)

CACHE = "C:/SmksEcoTips/cache.html"


def get_today_eco():
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

    class EcoCallback(QObject):

        def __init__(self, web_view):
            super(EcoCallback, self).__init__(web_view)
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
                    path = ECO_SERVER + path
                os.startfile(path)
                return False
            return True

    class EcoView(QWebEngineView):

        def __init__(self, parent=None):
            super(EcoView, self).__init__(parent)

            self._page = None

            self.setMinimumSize(100, 100)
            self._callback = EcoCallback(self)
            self._dev_page = QWebEnginePage()
            self._inspect_page = QWebEnginePage()
            self._dev_view = QWebEngineView()
            self._dev_view.setPage(self._dev_page)
            self._articles_element = None

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
                        self._page_downloads[url] = request.urlopen(url).read().decode('utf-8')
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
                    img_path = os.path.join(tempfile.gettempdir(), urllib.request.unquote(img_basename).replace(' ', '_'))
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
            super(EcoView, self).showEvent(event)
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
                        link = ECO_LINK
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
                             '<title>Simoneco</title>'
                             '<link href="stylesheets/eco.css" rel="stylesheet" type="text/css"/>'
                             '</head>'
                             '<html><body id="body"><h1>Simon\'Eco</h1>{}</body></html>'.format("<h2>LOADING</h2>"),
                             QUrl("file:///./eco.html"))
                QtCore.QTimer.singleShot(50, self._fetch_page)
                return

            reload = False

            if 'linfodurable' not in content:
                self.setMinimumSize(100, 100)
                content = "<body>"
                label = content or "Not Available"
                label += "</body>"
            else:
                self.setMinimumSize(250, 250)

                if not self._articles_element:
                    try:
                        tree = MyHTMLParser()
                        tree.feed(content)
                    except ET.ParseError as e:
                        label = "<body>Cannot parse the page !<body/>"
                    else:
                        self._articles_element = tree.find(".//*[@class=\"view-content\"]/div/ul")

                if self._articles_element:
                    for article in self._articles_element.findall(".//*article"):
                        title = article.find("div")
                        if title and title != article.getchildren()[0]:
                            article.remove(title)
                            article.insert(0, title)

                        for a in article.findall(".//*a"):
                            article_src = a.attrib["href"]
                            if ECO_SERVER not in article_src:
                                article_src = ECO_SERVER + article_src
                                a.attrib["href"] = article_src

                            article_content = self._page_downloads.get(article_src)
                            if article_content == 'DONE':
                                continue
                            if not article_content:
                                reload = True
                                self._page_downloads[article_src] = None
                                continue

                            try:
                                article_content = request.urlopen(article_src).read().decode('utf-8')
                            except urllib.error.URLError:
                                continue
                            article_content = article_content.split('<h2 class', 1)[-1].split('>', 1)[-1]
                            article_content = article_content.split('</h2>', 1)[0]
                            content_div = ET.SubElement(article, "div", {"class": "cover_text"})
                            content_div.text = article_content
                            self._page_downloads[article_src] = 'DONE'

                        for img in article.findall(".//*img"):
                            img_url = img.attrib["src"]
                            if img_url.startswith('file:'):
                                continue

                            if ECO_SERVER not in img_url:
                                img_url = ECO_SERVER + img_url

                            img_path = self._img_downloads.get(img_url)
                            if not img_path:
                                reload = True
                                self._img_downloads[img_url] = None
                                continue
                            if os.path.isfile(img_path):
                                img.attrib["src"] = "file:///{}".format(img_path)
                            if "height" in img.attrib:
                                del img.attrib["height"]
                                del img.attrib["width"]

                        for figure in article.findall("figure/div"):
                            for svg in figure.findall("svg"):
                                figure.remove(svg)

                    label = ET.tostring(self._articles_element, encoding='unicode', method='html')
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

            self.page().setHtml('<head>'
                                '<title>Simoneco</title>'
                                '<link href="stylesheets/eco.css" rel="stylesheet" type="text/css"/>'
                                '<script>{}</script>'
                                '</head>'
                                '<html><body id="body"><h1>Simon\'Eco</h1>'
                                '<a href="https://www.linfodurable.fr/conso"><h3>www.linfodurable.fr</h3></a>'
                                '{}</body></html>'.format(
                                    qwebchannel_script,
                                    label
                                ),  QUrl("file:///./eco.html")
            )
            self.adjustSize()
            self.parentWidget().adjustSize()
            if reload:
                self.run_downloads()
                QtCore.QTimer.singleShot(1000, self.reload_page)

    return EcoView()
