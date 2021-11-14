from qtpy import QtWidgets, QtCore, QtGui


class PathEditor(QtWidgets.QWidget):
    """
    Text field + file browser
    Editor Type Names:
        path
    Options:
        mode: 'r' Read, 'w' Write, 'd' Directory ('r' by default)
        filters: extension filters ('*' by default)
    """

    def __init__(self, parent=None, filter='*', mode='d', label=None, placeholder=None):
        QtWidgets.QWidget.__init__(self, parent)

        self._filter = filter
        self._mode = mode

        self._path_line_edit = QtWidgets.QLineEdit()
        self._path_browse_btn = QtWidgets.QPushButton()
        self._path_browse_btn.setIcon(QtGui.QIcon('./images/open_folder'))
        self._label = QtWidgets.QLabel(label) if label is not None else None
        if placeholder:
            self._path_line_edit.setPlaceholderText(placeholder)

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        if self._label:
            layout.addWidget(self._label, 1)
        layout.addWidget(self._path_line_edit, 9)
        layout.addWidget(self._path_browse_btn, 1)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignLeft)

        self._path_browse_btn.setMaximumWidth(64)

        self.setAcceptDrops(True)

        self._path_browse_btn.clicked.connect(self._browse_path)

    def _browse_path(self):
        dialog = QtWidgets.QFileDialog(self, "", self._path_line_edit.text())
        # dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)

        if 'd' in self._mode:
            dialog.setFileMode(QtWidgets.QFileDialog.Directory)
            if '+' in self._mode:
                dialog.setFileMode(QtWidgets.QFileDialog.DirectoryOnly)
                dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
                file_view = dialog.findChild(QtWidgets.QListView, 'listView')

                # to make it possible to select multiple directories:
                if file_view:
                    file_view.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
                f_tree_view = dialog.findChild(QtWidgets.QTreeView)
                if f_tree_view:
                    f_tree_view.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        else:
            if 'w' in self._mode:
                dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
            else:
                dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
            if '+' in self._mode:
                dialog.setFileMode(QtWidgets.QFileDialog.ExistingFiles)

        dialog.setNameFilter(self._filter.replace(';', ' '))

        dialog.exec_()
        if dialog.result() == QtWidgets.QFileDialog.Rejected:
            return
        path = ';'.join(dialog.selectedFiles())
        if path:
            self._path_line_edit.setText(path)

    def set_editable(self, b):
        '''
        Must be implemented to prevent editing if b is False.
        Visual cue show also be given to the user.
        '''
        self._path_line_edit.setReadOnly(not b)
        self._path_browse_btn.setEnabled(b)

    def get_edited_value(self):
        try:
            return eval(self._path_line_edit.text().replace('\\', "\\\\"))
        except Exception:
            return self._path_line_edit.text()

    def set_value(self, text):
        self._path_line_edit.setText(text)

    def _show_edited(self):
        self._path_line_edit.setProperty('edited', True)
        self.style().polish(self._path_line_edit)

    def _show_applied(self):
        self._path_line_edit.setProperty('applying', True)

    def _show_clean(self):
        self._path_line_edit.setProperty('edited', False)
        self._path_line_edit.setProperty('applying', False)
        self.style().polish(self._path_line_edit)

    def _show_error(self, error_message):
        self._path_line_edit.setProperty('error', True)
        self.style().polish(self._path_line_edit)
        self._path_line_edit.setToolTip('!!!\nERROR: %s' % (error_message,))

    def dragEnterEvent(self, event):
        data = event.mimeData()
        urls = data.urls()
        if len(urls) == 1 and urls[0].scheme() == 'file':
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        data = event.mimeData()
        urls = data.urls()
        if len(urls) == 1 and urls[0].scheme() == 'file':
            event.acceptProposedAction()

    def dropEvent(self, event):
        data = event.mimeData()
        urls = data.urls()
        if len(urls) == 1 and urls[0].scheme() == 'file':
            filepath = str(urls[0].toLocalFile())
            self._path_line_edit.setText(filepath)
            self._on_edited()

from qtpy import QtWidgets, QtGui, QtCore
from kabaret.app import resources


class ColorPicker(QtWidgets.QDialog):

    def __init__(self):
        super(ColorPicker, self).__init__(None)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.color = QtGui.QColor()
        self.dropper_pix = resources.get_icon(('icons.gui','dropper')).pixmap(20, 20)
        desktop = QtWidgets.QApplication.desktop()
        self.screen_pix = QtGui.QPixmap.grabWindow(desktop.winId(), 0, 0, desktop.width(), desktop.height()).toImage()
        self.setFixedSize(desktop.width(), desktop.height())
        self.timer = QtCore.QTimer()
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.update)

    def showEvent(self, e):
        self.move(0, 0)
        self.timer.start()
        super(ColorPicker, self).showEvent(e)

    def mouseReleaseEvent(self, event):
        self.releaseMouse()
        self.color = QtGui.QColor(self.screen_pix.pixel(event.pos()))
        self.accept()

    def keyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.releaseMouse()
            self.reject()

    def paintEvent(self, event):
        super(ColorPicker, self).paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.drawImage(QtCore.QPoint(0, 0), self.screen_pix)

        painter = QtGui.QPainter()
        pix = QtGui.QPixmap(60,60)
        pix.fill(QtGui.QColor(255,255,255,0))
        painter.begin(pix)
        color = QtGui.QColor(self.screen_pix.pixel(self.mapFromGlobal(self.cursor().pos())))
        painter.setBrush(color)
        painter.drawPixmap(QtCore.QPoint(30, 10), self.dropper_pix)
        painter.drawEllipse(QtCore.QPoint(45, 25), 5, 5)

        painter.end()
        self.setCursor(pix)


class SmksColorDialog(QtWidgets.QColorDialog):

    def __init__(self, parent):
        super(SmksColorDialog, self).__init__(parent)
        hbox = QtWidgets.QHBoxLayout()
        self.layout().insertLayout(self.layout().count()-1, hbox)
        html_label = QtWidgets.QLabel(self)
        html_label.setText("HTML:")
        self.color_edit = QtWidgets.QLineEdit(self)
        self.pipette_btn = QtWidgets.QPushButton(self)
        self.pipette_btn.setIcon(resources.get_icon(('icons.gui', 'dropper')))

        self.color_edit.editingFinished.connect(self.handle_color_edit)
        self.currentColorChanged.connect(self.handle_color_changed)
        self.pipette_btn.clicked.connect(self.show_pipette)

        hbox.addWidget(html_label,10)
        hbox.addWidget(self.color_edit,50)
        hbox.addStretch()
        hbox.addWidget(self.pipette_btn,10)

    def handle_color_edit(self):
        if not self.color_edit.text().startswith('#'):
            self.color_edit.setText('#'+self.color_edit.text())
        self.setCurrentColor(QtGui.QColor(self.color_edit.text()))

    def handle_color_changed(self):
        self.color_edit.setText(self.currentColor().name())

    def keyPressEvent(self, event):
        event.ignore()
        pass

    def show_pipette(self):
        dialog = ColorPicker()
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.setCurrentColor(dialog.color)


class ColorEditButton(QtWidgets.QPushButton):
    color_changed = QtCore.Signal(QtGui.QColor)

    def __init__(self, color=QtGui.QColor(), parent=None):
        super(ColorEditButton, self).__init__(parent)
        self._color = color

        pixmap = QtGui.QPixmap(64, 64)
        pixmap.fill(color)
        self.setIcon(QtGui.QIcon(pixmap))
        self.clicked.connect(self.edit_color)

    def color(self):
        return self._color

    def set_color(self, color):
        self._color = color
        pixmap = QtGui.QPixmap(64, 64)
        pixmap.fill(QtGui.QColor(color))
        self.setIcon(QtGui.QIcon(pixmap))

    def edit_color(self):
        color = SmksColorDialog.getColor(self._color, self)
        if color.isValid():
            self.set_color(color)
            self.color_changed.emit(color)
