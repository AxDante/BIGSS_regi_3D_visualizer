import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    id: root
    width: 480
    height: 720
    visible: true
    title: "SE(3) Controls"
    Material.theme: Material.Light
    Material.accent: Material.Blue
    Material.primary: Material.Grey

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Label {
                text: visualizerController.statusText
                Layout.fillWidth: true
                elide: Label.ElideRight
            }
            Button {
                text: "Refresh"
                onClicked: visualizerController.refreshLists()
            }
        }

        TabBar {
            id: tabs
            Layout.fillWidth: true
            TabButton { text: "Frames" }
            TabButton { text: "Transforms" }
            TabButton { text: "Vectors" }
            TabButton { text: "Ref Planes" }
            TabButton { text: "Settings" }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            Flickable {
                contentWidth: parent.width
                contentHeight: framesColumn.implicitHeight
                clip: true
                ColumnLayout {
                    id: framesColumn
                    width: parent.width
                    Repeater {
                        model: visualizerController.frames
                        delegate: Frame {
                            Layout.fillWidth: true
                            ColumnLayout {
                                width: parent.width
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label {
                                        text: modelData.abbr.length > 0 ? (modelData.name + " (" + modelData.abbr + ")") : modelData.name
                                        Layout.fillWidth: true
                                        elide: Label.ElideRight
                                    }
                                    Switch {
                                        text: "Visible"
                                        checked: modelData.visible
                                        onToggled: visualizerController.setObjectVisible(modelData.name, checked)
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Switch {
                                        text: "Frame"
                                        checked: modelData.showFrame
                                        onToggled: visualizerController.setFrameVisible(modelData.name, checked)
                                    }
                                    Switch {
                                        text: "Model"
                                        checked: modelData.showModel
                                        enabled: modelData.hasModel
                                        onToggled: visualizerController.setModelVisible(modelData.name, checked)
                                    }
                                    Switch {
                                        text: "Landmarks"
                                        checked: modelData.showLandmarks
                                        enabled: modelData.hasLandmarks
                                        onToggled: visualizerController.setLandmarksVisible(modelData.name, checked)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Flickable {
                contentWidth: parent.width
                contentHeight: transformsColumn.implicitHeight
                clip: true
                ColumnLayout {
                    id: transformsColumn
                    width: parent.width
                    Label { text: "Transform Selection" }
                    ComboBox {
                        Layout.fillWidth: true
                        model: visualizerController.transformNames
                        currentIndex: visualizerController.transformNames.indexOf(visualizerController.selectedTransform)
                        onActivated: visualizerController.setSelectedTransform(currentText)
                    }
                    Label {
                        text: visualizerController.chain.length > 0 ? ("Chain: " + visualizerController.chain) : "Chain: -"
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }

                    Frame {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            Label { text: "Translation (mm)" }
                            RowLayout {
                                Layout.fillWidth: true
                                TextField {
                                    id: txField
                                    Layout.fillWidth: true
                                    text: Number(visualizerController.tx).toFixed(2)
                                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                                }
                                Button {
                                    text: "Set X"
                                    enabled: visualizerController.canEdit
                                    onClicked: visualizerController.setTranslation("x", parseFloat(txField.text))
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                TextField {
                                    id: tyField
                                    Layout.fillWidth: true
                                    text: Number(visualizerController.ty).toFixed(2)
                                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                                }
                                Button {
                                    text: "Set Y"
                                    enabled: visualizerController.canEdit
                                    onClicked: visualizerController.setTranslation("y", parseFloat(tyField.text))
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                TextField {
                                    id: tzField
                                    Layout.fillWidth: true
                                    text: Number(visualizerController.tz).toFixed(2)
                                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                                }
                                Button {
                                    text: "Set Z"
                                    enabled: visualizerController.canEdit
                                    onClicked: visualizerController.setTranslation("z", parseFloat(tzField.text))
                                }
                            }
                        }
                    }

                    Frame {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            Label { text: "Rotation (deg)" }
                            RowLayout {
                                Layout.fillWidth: true
                                TextField {
                                    id: rollField
                                    Layout.fillWidth: true
                                    text: Number(visualizerController.roll).toFixed(1)
                                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                                }
                                Button {
                                    text: "Set Roll"
                                    enabled: visualizerController.canEdit
                                    onClicked: visualizerController.setRotation("roll", parseFloat(rollField.text))
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                TextField {
                                    id: pitchField
                                    Layout.fillWidth: true
                                    text: Number(visualizerController.pitch).toFixed(1)
                                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                                }
                                Button {
                                    text: "Set Pitch"
                                    enabled: visualizerController.canEdit
                                    onClicked: visualizerController.setRotation("pitch", parseFloat(pitchField.text))
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                TextField {
                                    id: yawField
                                    Layout.fillWidth: true
                                    text: Number(visualizerController.yaw).toFixed(1)
                                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                                }
                                Button {
                                    text: "Set Yaw"
                                    enabled: visualizerController.canEdit
                                    onClicked: visualizerController.setRotation("yaw", parseFloat(yawField.text))
                                }
                            }
                        }
                    }

                    Label { text: "Matrix" }
                    ScrollView {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 220
                        TextArea {
                            text: visualizerController.matrixText
                            readOnly: true
                            wrapMode: Text.Wrap
                        }
                    }
                }
            }

            Flickable {
                contentWidth: parent.width
                contentHeight: vectorsColumn.implicitHeight
                clip: true
                ColumnLayout {
                    id: vectorsColumn
                    width: parent.width
                    Label { text: "Vectors" }
                    ListView {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 300
                        model: visualizerController.vectorNames
                        delegate: ItemDelegate { text: modelData }
                    }
                }
            }

            Flickable {
                contentWidth: parent.width
                contentHeight: planesColumn.implicitHeight
                clip: true
                ColumnLayout {
                    id: planesColumn
                    width: parent.width
                    Label { text: "Reference Planes" }
                    ListView {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 300
                        model: visualizerController.planeNames
                        delegate: ItemDelegate { text: modelData }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Button {
                            text: "Generate DRR"
                            enabled: false
                        }
                        Button {
                            text: "Refresh DRR"
                            enabled: false
                        }
                    }
                }
            }

            Flickable {
                contentWidth: parent.width
                contentHeight: settingsColumn.implicitHeight
                clip: true
                ColumnLayout {
                    id: settingsColumn
                    width: parent.width
                    Label { text: "Settings" }
                    RowLayout {
                        Layout.fillWidth: true
                        Button {
                            text: "Toggle Logging"
                            onClicked: visualizerController.toggleLogging()
                        }
                        Button {
                            text: "Toggle Recording"
                            onClicked: visualizerController.toggleRecording()
                        }
                    }
                }
            }
        }
    }
}
