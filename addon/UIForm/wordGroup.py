# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'word_group.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

import aqt

# from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(395, 261)
        # self.verticalLayout = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout = aqt.qt.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        # self.wordGroupListWidget = QtWidgets.QListWidget(Dialog)
        self.wordGroupListWidget = aqt.qt.QListWidget(Dialog)
        self.wordGroupListWidget.setAlternatingRowColors(True)
        self.wordGroupListWidget.setObjectName("wordGroupListWidget")
        self.verticalLayout.addWidget(self.wordGroupListWidget)
        # self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox = aqt.qt.QDialogButtonBox(Dialog)
        # self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setOrientation(aqt.Qt.Orientation.Horizontal)
        # self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setStandardButtons(aqt.qt.QDialogButtonBox.StandardButton.Cancel|aqt.qt.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)
        # QtCore.QMetaObject.connectSlotsByName(Dialog)
        aqt.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        # _translate = QtCore.QCoreApplication.translate
        _translate = aqt.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "单词本分组"))

