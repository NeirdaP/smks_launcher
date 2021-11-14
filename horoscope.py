from __future__ import print_function

SIGNS = ["Belier", "Taureau", "Gemeaux", "Cancer",
         "Lion", "Vierge", "Balance", "Scorpion", "Sagittaire",
         "Capricorne", "Verseau", "Poissons"]

HOROSCOPE_LINK = "https://www.voyance.fr/horoscopes/horoscope_{}.html"


def get_today_horoscope():
    import qtpy
    from qtpy.QtWidgets import QLabel
    try:
        from qtpy.QtWebEngineWidgets import QWebEngineView
        from qtpy.QtWebChannel import QWebChannel
    except (ImportError, qtpy.PythonQtError):
        QWebEngineView = None
        QWebChannel = None
    from qtpy import QtCore
    from qtpy.QtCore import QSize, QUrl, QObject, QTimer
    from xml.etree import ElementTree as ET
    import random
    import functools

    try:
        from urllib import request
    except ImportError:
        return QLabel("Web plugin not installed")

    class Thread(QtCore.QThread):

        def __init__(self, callback, args=None, kwargs=None):
            super(Thread, self).__init__()
            self._callback = callback
            self._args = args or []
            self._kwargs = kwargs or dict()

        def run(self):
            self._callback(*self._args, **self._kwargs)

    class HoroscopeCallback(QObject):

        def __init__(self, web_view):
            super(HoroscopeCallback, self).__init__(web_view)
            self._web_view = web_view

        @QtCore.Slot(str)
        def reload_page(self, sign):
            self._web_view.reload_page(sign)

    class HoroscopeView(QWebEngineView):

        def __init__(self, parent=None):
            super(HoroscopeView, self).__init__(parent)

            self._pages = dict()

            self._buttons_html = '<ul class="signs">%s</ul>' % '\n'.join(
                '<li class="sign-item" title="{sign}">'
                '<script>'
                'function onClick(sign){{window.qt_view.reload_page(sign)}};'
                '</script>'
                '<button type="button" class="sign-button" title="{sign}" onclick="onClick(\'{sign}\')">'
                '<span style="background: url(./images/horoscope/{sign}.png);'
                'background-repeat: no-repeat; background-size: cover;"></span>'
                '</button></li>'.format(
                    sign=sign
                )
                for sign in SIGNS
            )
            self._callback = HoroscopeCallback(self)

        def showEvent(self, event):
            super(HoroscopeView, self).showEvent(event)
            self.reload_page()

        def _fetch_page(self, sign, load_it=True):
            link = HOROSCOPE_LINK.format(sign.lower())
            page = request.urlopen(link)
            self._pages[sign] = page.read().decode('utf-8')
            if load_it:
                QtCore.QTimer.singleShot(100, lambda _sign=sign: self.reload_page(_sign))

        @QtCore.Slot(str)
        def reload_page(self, sign=None):
            import ssl
            import html
            import datetime

            if not sign:
                sign = self.window().settings.value("horoscope_sign", SIGNS[random.randint(0, len(SIGNS) - 1)])
            else:
                self.window().settings.setValue("horoscope_sign", sign)

            ssl._create_default_https_context = ssl._create_unverified_context

            if sign not in self._pages:
                QtCore.QTimer.singleShot(50, lambda _sign=sign:self._fetch_page(sign))
                return

            content = self._pages[sign]

            if 'horo_module' not in content:
                content = "<h2>No content available</h2>" + self._buttons_html
            else:
                seed = (datetime.datetime.now().day + SIGNS.index(sign)) % 100
                random.seed(seed)
                friend_png = '%d.png' % (int(random.random()*2)+1)

                content = content.split('"horo_module" >', 1)[-1]

                content = "<div class=\"horo_module\">{}</div>".format(content.split('<form', 1)[0])
                content = content.replace('//cdn1.tlmq.fr/1/', './images/')
                content = content.replace('0.png', friend_png, 1)
                content = content.replace('color:#000000', '')
                content = content.replace('<</span>', '</span>')
                content = content.replace(' & ', html.escape(' & '))
                button_html = self._buttons_html+"\n\t<div class=\"menu_horo\">"
                content = button_html.join(content.split('<div class="menu_horo">', 1))

            try:
                tree = ET.fromstring(content)
            except ET.ParseError as e:
                import traceback
                traceback.print_exc()
                content = content.replace("<div class=\"menu_horo\">", "<div class=\"menu_horo\" hidden>")
                label = content
            else:
                for div in tree.iterfind("div"):
                    if "menu" in div.attrib["class"]:
                        tree.remove(div)

                for p in tree.iter("p"):
                    if "class" in p.attrib and "nav" in p.attrib["class"]:
                        p.clear()
                        del p

                label = ET.tostring(tree, method='html', encoding='utf-8').decode()

            channel = QWebChannel(self.page())
            channel.registerObject("qt_view", self._callback)
            self.page().setWebChannel(channel)

            with open("./js/qwebchannel.js", 'r') as fp:
                qwebchannel_script = fp.read()

            qwebchannel_script += "\nnew QWebChannel(qt.webChannelTransport, function(channel)" \
                                  "{window.qt_view=channel.objects.qt_view;}" \
                                  ");"

            self.setHtml('<head>'
                           '<title>Clairoscope</title>'
                           '<link href="stylesheets/horoscope.css" rel="stylesheet" type="text/css"/>'
                           '<script>{}</script>'
                           '</head>'
                           '<html><body id="body">{}</body></html>'.format(qwebchannel_script, label),
                           QUrl("file:///./horoscope.html"))

            self.setMinimumSize(250, 250)
    return HoroscopeView()
