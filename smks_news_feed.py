import os
import getpass
import shutil
import tempfile
import json
import logging
import time

try:
    from importlib import reload
except ImportError:
    from imp import reload

from qtpy import PythonQtError, QtWidgets, QtGui, QtCore

try:
    from qtpy import QtMultimediaWidgets, QtMultimedia
except (ImportError, PythonQtError):
    QtMultimediaWidgets, QtMultimedia = None, None

from qt_utils import ColorEditButton

from file import file_modification_date


class SmksNewsFeedActor(object):

    NAMESPACE = "SmksNewsFeed"
    NEWS_LIST_KEY = "News"

    def __init__(self):
        super(SmksNewsFeedActor, self).__init__()
        self._json_db = "./news_data"
        self._news_data = dict()
        self.load()

    def load(self):
        self._news_data = dict()
        if os.path.isfile(self._json_db):
            with open(self._json_db) as fp:
                self._news_data = json.load(fp)

    def save(self):
        with open(self._json_db, 'w') as fp:
            json.dump(self._news_data, fp)

    def get_last_news(self):
        return self.get_all_news()[-5:]

    def get_all_news(self):
        news_list = self._news_data.get(self.NEWS_LIST_KEY, [])
        for i, news in enumerate(news_list):
            news["id"] = i
        return news_list

    def get_news(self, index):
        return self.get_all_news()[index]

    def add_news(self, message, media_path, link, **kwargs):
        if not any((media_path.startswith(prefix) for prefix in ("file://", "http://",))):
            media_path = "file://" + media_path

        news_list = self._news_data.get(self.NEWS_LIST_KEY, [])

        news = dict(
            id=len(news_list),
            date=time.time(),
            message=message,
            media_path=media_path,
            link=link
        )
        news.update(kwargs)
        news_list.append(news)
        self._news_data[self.NEWS_LIST_KEY] = news_list
        self.save()

    def change_news(self, id, message, media_path, link, **kwargs):
        news_list = self._news_data.get(self.NEWS_LIST_KEY, [])
        news = news_list[id]
        news.update(dict(
            message=message,
            media_path=media_path,
            link=link
        ))
        news.update(kwargs)
        news_list[id] = news
        self._news_data[self.NEWS_LIST_KEY] = news_list
        self.save()

    def switch_news(self, id_1, id_2):
        news_list = self._news_data.get(self.NEWS_LIST_KEY, [])

        news_1 = news_list[id_1]
        news_2 = news_list[id_2]

        news_list[id_1] = news_2
        news_list[id_2] = news_1

        self._news_data[self.NEWS_LIST_KEY] = news_list
        self.save()

    def remove_news(self, id):
        news_list = self._news_data.get(self.NEWS_LIST_KEY, [])

        news_list.pop(id)

        self._news_data[self.NEWS_LIST_KEY] = news_list
        self.save()


class NewsTable(QtWidgets.QTableWidget):

    def __init__(self, parent):
        super(NewsTable, self).__init__(4, 3, parent)
        self.smks_news = SmksNewsFeedActor()

        self._row_editor_dialog = None
        self._add_action = QtWidgets.QAction("Add", self)
        self._add_action.setIcon(QtGui.QIcon("./images/plus-sign-in-a-black-circle.png"))
        self.addAction(self._add_action)

        self._remove_action = QtWidgets.QAction("Remove", self)
        icon = QtGui.QIcon("./images/remove-symbol.png")
        icon.addPixmap(QtGui.QPixmap.fromImage("./images/blank_overlay.png"), QtGui.QIcon.Disabled)
        self._remove_action.setIcon(icon)
        self._remove_action.setEnabled(False)
        self.addAction(self._remove_action)

        self._media_checker = None

        self.itemDoubleClicked.connect(self._edit_row)
        self.itemSelectionChanged.connect(self.handle_selection)
        self._add_action.triggered.connect(self._create_row)
        self._remove_action.triggered.connect(self._remove_row)

        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

    def handle_selection(self):
        self._remove_action.setEnabled(self.currentItem() is not None)

    def showEvent(self, event):
        super(NewsTable, self).showEvent(event)
        self.update_content()

    def update_content(self):
        news_list = self.smks_news.get_all_news()

        self.clearContents()

        self.setRowCount(len(news_list))
        self.setHorizontalHeaderLabels(["Message", "Media Path", "Link"])
        self.horizontalHeader().setStretchLastSection(True)

        for i, news in enumerate(news_list):
            self.setItem(i, 0, QtWidgets.QTableWidgetItem(news["message"]))
            self.setItem(i, 1, QtWidgets.QTableWidgetItem(news["media_path"]))
            self.setItem(i, 2, QtWidgets.QTableWidgetItem(news["link"]))
            for j in range(3):
                self.item(i, j).setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

    def _build_row_editor(self):
        self._row_editor_dialog = QtWidgets.QDialog()

        self._order_spin_box = QtWidgets.QSpinBox()
        self._message_line_edit = QtWidgets.QLineEdit()
        self._media_path_line_edit = QtWidgets.QLineEdit()
        self._link_line_edit = QtWidgets.QLineEdit()
        self._message_color_edit = ColorEditButton(QtGui.QColor(255,255,255))

        self._media_checker = QtMultimedia.QMediaPlayer()
        self._media_checker.setMuted(True)

        self._row_editor_dialog.setWindowTitle("Edit News")

        self._row_editor_dialog.setLayout(QtWidgets.QVBoxLayout())

        media_path_field = QtWidgets.QWidget()
        media_path_browse_btn = QtWidgets.QPushButton('...')

        media_path_field.setLayout(QtWidgets.QHBoxLayout())
        media_path_field.layout().addWidget(self._media_path_line_edit, 9)
        media_path_field.layout().addWidget(media_path_browse_btn, 1)
        media_path_field.layout().setContentsMargins(0, 0, 0, 0)

        form_layout = QtWidgets.QFormLayout()

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)

        form_layout.addRow("Order", self._order_spin_box)
        form_layout.addRow("Message", self._message_line_edit)
        form_layout.addRow("Message Color", self._message_color_edit)
        form_layout.addRow("Media", media_path_field)
        form_layout.addRow("Link", self._link_line_edit)

        buttons.accepted.connect(self._row_editor_dialog.accept)
        buttons.rejected.connect(self._row_editor_dialog.reject)
        media_path_browse_btn.clicked.connect(self._browse_media_file)
        self._media_path_line_edit.returnPressed.connect(self._check_media_path)
        self._media_checker.mediaStatusChanged.connect(self._check_status)

        self._row_editor_dialog.layout().addLayout(form_layout, 7)
        self._row_editor_dialog.layout().addStretch(2)
        self._row_editor_dialog.layout().addWidget(buttons)
        self._row_editor_dialog.adjustSize()

    def _check_media_path(self):
        self._media_path_line_edit.setStyleSheet("")
        path = self._media_path_line_edit.text()
        base, ext = os.path.splitext(path)
        if ext not in (".png", ".jpg", ".gif"):
            self._media_checker.setMedia(QtMultimedia.QMediaContent(path))
        # self._media_checker.play()

    def _check_status(self):
        status = self._media_checker.mediaStatus()
        if status == QtMultimedia.QMediaPlayer.InvalidMedia:
            self._media_path_line_edit.setStyleSheet("background: red;")
            self._media_path_line_edit.setToolTip(self._media_checker.errorString())
        elif status in (QtMultimedia.QMediaPlayer.LoadedMedia, QtMultimedia.QMediaPlayer.LoadingMedia) :
            self._media_path_line_edit.setStyleSheet("background: green;")

    def _browse_media_file(self):
        url = QtWidgets.QFileDialog.getOpenFileUrl(self, "Select Media", QtCore.QUrl(self._media_path_line_edit.text()),
                                                   "*.jpg;*.jpeg;*.png;*.gif;*.mp4;*.amv;*.avi")
        if url[0] and url[0].isValid():
            self._media_path_line_edit.setText(url[0].toDisplayString())
        self._check_media_path()

    def _edit_row(self, index):
        if not self._row_editor_dialog:
            self._build_row_editor()
        news = self.smks_news.get_news(index.row())

        self._order_spin_box.setRange(1, self.rowCount())
        self._order_spin_box.setValue(index.row()+1)
        self._media_path_line_edit.setText(news.get("media_path", ''))
        self._link_line_edit.setText(news.get("link", ''))
        self._message_line_edit.setText(news.get("message", ''))
        self._message_color_edit.set_color(QtGui.QColor(news.get("message_color", 0xffffff)))
        result = self._open_row_editor()
        if result == QtWidgets.QDialog.Accepted:
            self.smks_news.change_news(index.row(), self._message_line_edit.text(), self._media_path_line_edit.text(),
                                    self._link_line_edit.text(), message_color=self._message_color_edit.color().rgb())
            if (self._order_spin_box.value()-1) != index.row():
                self.smks_news.switch_news(index.row(), self._order_spin_box.value()-1)
            self.update_content()

    def _create_row(self):
        if not self._row_editor_dialog:
            self._build_row_editor()
        result = self._open_row_editor()
        if result == QtWidgets.QDialog.Accepted:
            self.smks_news.add_news(self._message_line_edit.text(), self._media_path_line_edit.text(),
                                    self._link_line_edit.text(), message_color=self._message_color_edit.color().rgb())
            self.update_content()

    def _open_row_editor(self):
        if not self._row_editor_dialog:
            self._build_row_editor()
        return self._row_editor_dialog.exec_()

    def _remove_row(self):
        current_row = self.currentRow()
        if current_row >= 0:
            self.smks_news.remove_news(current_row)
        self.removeRow(current_row)


class NewsManagerDialog(QtWidgets.QDialog):

    def __init__(self, parent):
        super(NewsManagerDialog, self).__init__(parent)
        self.setWindowTitle("News")
        self.setLayout(QtWidgets.QVBoxLayout())

        self._table = NewsTable(self)
        self._actions_bar = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        layout.setDirection(QtWidgets.QBoxLayout.RightToLeft)
        self._actions_bar.setLayout(layout)

        for action in self._table.actions():
            button = QtWidgets.QToolButton(self._actions_bar)
            button.setDefaultAction(action)
            layout.addWidget(button)
        layout.addStretch(10)

        self.layout().addWidget(self._actions_bar)
        self.layout().addWidget(self._table)
        self.resize(500, 200)


class SmksNewsFeed(QtWidgets.QWidget):

    ANIM_DELAY = 66
    ANIM_DURATION = 20000
    TRANSITION_DURATION = 800

    class SmksSceneView(QtWidgets.QGraphicsView):

        def __init__(self, news_feed_parent):
            super(SmksNewsFeed.SmksSceneView, self).__init__(news_feed_parent)
            self._news_feed = news_feed_parent

        def mousePressEvent(self, event):
            super(SmksNewsFeed.SmksSceneView, self).mousePressEvent(event)
            if event.button() == QtCore.Qt.LeftButton and self._news_feed.current_link():
                os.startfile(self._news_feed.current_link())

    @classmethod
    def Actor(cls):
        return SmksNewsFeedActor()

    def __init__(self, parent=None):
        super(SmksNewsFeed, self).__init__(parent)

        self.smks_news = self.Actor()
        self._news_manager_dialog = None

        main_layout = QtWidgets.QHBoxLayout()
        self.setLayout(main_layout)
        self.layout().setContentsMargins(1, 1, 1, 1)

        self._background_lbl = QtWidgets.QLabel()
        self._background_lbl.setLayout(QtWidgets.QHBoxLayout())

        self._left_button = QtWidgets.QPushButton()
        self._left_button.setIcon(QtGui.QIcon("./images/sign-left.png"))
        self._left_button.setMaximumSize(20, 1000)
        self._right_button = QtWidgets.QPushButton()
        self._right_button.setIcon(QtGui.QIcon("./images/sign-right.png"))
        self._right_button.setMaximumSize(20, 1000)

        self._view = self.SmksSceneView(self)

        self._scene = QtWidgets.QGraphicsScene()
        self._scene.setSceneRect(-1000, -1000, 2000, 2000)
        self._scene.setBackgroundBrush(QtGui.QColor(25, 25, 25))
        self._view.setScene(self._scene)
        self._view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        main_layout.addWidget(self._left_button)
        main_layout.addWidget(self._view)
        main_layout.addWidget(self._right_button)

        self._news = []
        self._current_news_index = 0
        self._media_path = ''
        self._rerun_lock = False

        tempdir = tempfile.gettempdir()
        self._tmp_media_path = os.path.join(tempdir, "_NEWS_MEDIA_")
        try:
            os.makedirs(self._tmp_media_path)
        except OSError:
            pass

        self._media_player = None
        self._media_item = None

        self._media_pixmap = QtWidgets.QGraphicsPixmapItem()
        self._scene.addItem(self._media_pixmap)

        self._transition_timer = QtCore.QTimeLine(self.TRANSITION_DURATION)
        # self._media_timer.setCurveShape(QtCore.QTimeLine.EaseInCurve)
        self._transition_timer.setUpdateInterval(self.ANIM_DELAY)
        self._transition_timer.setFrameRange(0, 100)
        self._transition_timer.setCurrentTime(self.TRANSITION_DURATION/2)
        self._transition_timer.frameChanged.connect(self.update_transition)
        self._transition_timer.finished.connect(self.end_transition)

        self._text_document = QtGui.QTextDocument(self)
        self._text_format = QtGui.QTextCharFormat()
        font = self.font()
        font.setPointSize(18)
        font.setWeight(QtGui.QFont.Bold)
        self._text_format.setFont(font)

        outlinePen = QtGui.QPen(QtGui.QColor(0, 0, 0), 1, QtCore.Qt.SolidLine)
        self._text_format.setTextOutline(outlinePen)

        self._information_item = QtWidgets.QGraphicsTextItem("")
        self._information_item.setDocument(self._text_document)

        self._update_timer = QtCore.QTimer(self)

        self._animation_timer = QtCore.QTimeLine(self.ANIM_DURATION)
        self._animation_timer.setLoopCount(0)
        self._animation_timer.setUpdateInterval(self.ANIM_DELAY)
        self._animation_timer.setFrameRange(0, self.ANIM_DURATION / self.ANIM_DELAY)
        self._animation_timer.valueChanged.connect(self._update_media_pixmap)

        try:
            self._text_animation = QtWidgets.QGraphicsItemAnimation(self._scene)
        except AttributeError:
            self._text_animation = None
        else:
            self._text_animation.setTimeLine(self._animation_timer)
            self._text_animation.setItem(self._information_item)

        self._scene.addItem(self._information_item)

        self._news_timer = QtCore.QTimer(self)

        self._manage_news_action = QtWidgets.QAction("Manage...", self)
        
        self._news_timer.timeout.connect(self.update_current_news)
        self._update_timer.timeout.connect(self._player_update)
        self._manage_news_action.triggered.connect(self.open_news_manager)
        self._left_button.clicked.connect(self._switch_news_left)
        self._right_button.clicked.connect(self._switch_news_right)

        if getpass.getuser() in ('firegreen', ):
            self.addAction(self._manage_news_action)
            self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

        self.setMaximumSize(9999, 400)
        self.setMinimumSize(0, 200)
        # self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)

    def showEvent(self, event):
        super(SmksNewsFeed, self).showEvent(event)
        QtCore.QTimer.singleShot(100, self._load_news)

    def _load_news(self):
        self.update_news()
        self.adjust_media_size()
        self.start()

    def update_transition(self):
        self._media_pixmap.setOpacity(self._transition_timer.currentValue())

    def set_media(self, media_path):
        self.resize(self.sizeHint())
        base, ext = os.path.splitext(media_path)

        if self._media_player:
            self._media_player.stop()
            self._media_player.playlist().clear()
        current_movie = self._background_lbl.movie()
        if current_movie:
            current_movie.stop()
            current_movie.deleteLater()
            self._background_lbl.setMovie(None)
        self._background_lbl.setPixmap(QtGui.QPixmap())

        self._media_pixmap.setPixmap(QtGui.QPixmap())

        if not media_path:
            return

        media_url = QtCore.QUrl(media_path)
        media_path = media_url.toLocalFile()
        if not os.path.exists(media_path):
            return

        local_media_path = os.path.join(self._tmp_media_path, os.path.basename(media_path))
        if not os.path.isfile(local_media_path) or \
                file_modification_date(local_media_path) < file_modification_date(media_path):
            shutil.copyfile(media_path, local_media_path)

        self._media_path = local_media_path

        if os.path.isdir(os.path.dirname(self._media_path)):
            if ext in ('.png', '.jpg', '.jpeg'):
                pixmap = QtGui.QPixmap(self._media_path)
                self._background_lbl.setFixedSize(pixmap.size())
                self._background_lbl.setPixmap(pixmap)
                self._media_pixmap.setPixmap(pixmap)
            else:
                movie = QtGui.QMovie(self._media_path)
                self._background_lbl.setFixedSize(movie.currentPixmap().size())
                self._background_lbl.setMovie(movie)
                movie.start()
        self.adjust_media_size()

    def end_transition(self):
        self._transition_timer.toggleDirection()
        if self._transition_timer.currentValue() <= 0.1:
            self.set_media(self._news[self._current_news_index].get("media_path", ''))
            self._transition_timer.start()

    def start(self):
        self.resize(self.sizeHint())
        self._information_item.show()
        if self._media_player and self._media_player.playlist().mediaCount():
            self._media_player.play()
        elif self._background_lbl.movie():
            self._background_lbl.movie().setPaused(False)
        if self._animation_timer.state() != QtCore.QTimeLine.Running:
            self._animation_timer.start()
        if not self._news_timer.isActive():
            self._news_timer.start(int(self.ANIM_DURATION*0.9))
        if not self._update_timer.isActive():
            self._update_timer.start(self.ANIM_DELAY)

    def stop(self):
        self._information_item.hide()
        if self._media_player:
            self._media_player.stop()
        if self._background_lbl.movie():
            self._background_lbl.movie().setPaused(True)
        self._animation_timer.stop()
        self._news_timer.stop()

    def _build_news_manager(self):
        self._news_manager_dialog = NewsManagerDialog(self)
        self._news_manager_dialog.finished.connect(self.update_news)

    def open_news_manager(self):
        if not self._news_manager_dialog:
            self._build_news_manager()
        self._news_manager_dialog.show()

    def update_news(self):
        self._news = self.smks_news.get_last_news()
        self._current_news_index = -1
        self.update_current_news()

    def _switch_news_left(self):
        self.update_current_news(-1)

    def _switch_news_right(self):
        self.update_current_news(1)

    def update_current_news(self, next_index_incr=1):
        self.stop()

        self._information_item.hide()
        if not self._news:
            return
        self._current_news_index = (self._current_news_index + next_index_incr) % len(self._news)
        news = self._news[self._current_news_index]
        if news.get("link"):
            self._view.setCursor(QtCore.Qt.PointingHandCursor)
        else:
            self._view.setCursor(QtCore.Qt.ArrowCursor)

        media_path = news.get("media_path", '')
        if media_path and os.path.isdir(os.path.dirname(media_path)):
            self._transition_timer.setDirection(QtCore.QTimeLine.Backward)
            self._transition_timer.setCurrentTime(self.TRANSITION_DURATION)
            self._transition_timer.start()
        self._information_item.show()

        message = news.get("message", media_path)

        color = QtGui.QColor(news.get("message_color", 0xeeeeeeee))
        outlinePen = QtGui.QPen(QtGui.QColor(0xffffffff - color.rgb()).lighter(), 1, QtCore.Qt.SolidLine)
        self._text_format.setTextOutline(outlinePen)
        self._information_item.setDefaultTextColor(color)

        self._text_document.clear()
        QtGui.QTextCursor(self._text_document).insertText(message, self._text_format)

        if self._text_animation:
            self._text_animation.setPosAt(0, QtCore.QPoint(self.width()*0.6, self.height()*-0.3))
            self._text_animation.setPosAt(1, QtCore.QPoint(-self.width(), self.height()*-0.3))
        self.start()

    def current_link(self):
        if not self._news:
            return None
        return self._news[self._current_news_index].get("link")

    def _rerun_player(self, *args):
        self._rerun_lock = False
        logging.getLogger("kabaret.smks_studio.news_feed").debug("Rerun play %r" % self._media_path)
        self._media_player.playlist().addMedia(QtCore.QUrl.fromLocalFile(self._media_path))
        self._media_player.play()

    def player_error(self):
        self._media_player.stop()
        self._media_player.playlist().clear()

        if self._rerun_lock:
            return
        self._rerun_lock = True
        QtCore.QTimer.singleShot(100, self._rerun_player)

    def resizeEvent(self, event):
        super(SmksNewsFeed, self).resizeEvent(event)

        self._view.setMaximumSize(self.size())

        sceneRect = self._scene.sceneRect()
        scroll_bar = self._view.horizontalScrollBar()
        length = scroll_bar.pageStep() + scroll_bar.maximum() - scroll_bar.minimum()
        scroll_bar.setValue(scroll_bar.minimum() +
                            (-sceneRect.x()) * length / sceneRect.width() +
                            (scroll_bar.pageStep() / -2))

        scroll_bar = self._view.verticalScrollBar()
        length = scroll_bar.pageStep() + scroll_bar.maximum() - scroll_bar.minimum()
        scroll_bar.setValue(scroll_bar.minimum() +
                            (-sceneRect.y()) * length / sceneRect.height() +
                            (scroll_bar.pageStep() / -2))
        self.adjust_media_size()

        if self._text_animation:
            self._text_animation.setPosAt(0, QtCore.QPoint(self.width()*0.6, self.height()*-0.3))
            self._text_animation.setPosAt(1, QtCore.QPoint(-self.width(), self.height()*-0.3))
    #
    # def sizeHint(self):
    #     return self.parentWidget().size()

    def adjust_media_size(self):
        if self._media_item:
            if self._media_item.nativeSize().width() != self._media_item.boundingRect().width():
                self._media_item.setSize(self._media_item.nativeSize())
        size = self._view.size()
        real_size = self._background_lbl.sizeHint()
        size = real_size * size.width() / real_size.width()
        self._background_lbl.setMaximumSize(size)
        self._background_lbl.resize(size)
        if self._background_lbl.movie():
            self._background_lbl.movie().setScaledSize(size)
        self._media_pixmap.setPos(-size.width()*0.5, -size.height()*0.5)

    def _update_media_pixmap(self):
        if self._background_lbl.pixmap():
            if not self._media_pixmap.pixmap() or self._media_pixmap.pixmap().isNull():
                self._media_pixmap.setPixmap(self._background_lbl.pixmap())
        elif self._background_lbl.movie():
            if self._background_lbl.movie().state() == QtGui.QMovie.Running:
                size = self._background_lbl.size()
                pixmap = QtGui.QPixmap(size)
                painter = QtGui.QPainter(pixmap)
                self._background_lbl.render(painter, QtCore.QPoint(), QtGui.QRegion(self._background_lbl.rect()))
                painter.end()

                current_width = self._view.width()
                self._media_pixmap.setPixmap(pixmap)
                if current_width != pixmap.width():
                    self.adjust_media_size()

    def _player_update(self):
        if self._animation_timer.state() == QtCore.QTimeLine.Running:
            if not self.isVisible() or \
                    not self.window().isVisible() or not self.window().isActiveWindow():
                self.stop()
            elif self._media_player and \
                    self._media_player.position() >= self._media_player.duration()-180:
                self._media_player.stop()
                self._media_player.setPosition(1)
                self._media_player.play()
        else:
            if self.isVisible() and self.window().isActiveWindow():
                self.start()

    def closeEvent(self, event):
        super(SmksNewsFeed, self).closeEvent(event)
        self.stop()
