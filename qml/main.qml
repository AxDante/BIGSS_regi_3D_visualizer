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
                            padding: 8
                            ColumnLayout {
                                Layout.fillWidth: true
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label {
                                        text: modelData.abbr.length > 0 ? (modelData.name + " (" + modelData.abbr + ")") : modelData.name
                                        Layout.fillWidth: true
                                        elide: Label.ElideRight
                                        font.bold: true
                                    }
                                    ToolButton {
                                        checkable: true
                                        checked: modelData.visible
                                        text: checked ? "Hide" : "Show"
                                        icon.name: checked ? "view-visible" : "view-hidden"
                                        display: AbstractButton.TextBesideIcon
                                        onToggled: visualizerController.setObjectVisible(modelData.name, checked)
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    ToolButton {
                                        checkable: true
                                        text: "Frame"
                                        checked: modelData.showFrame
                                        onToggled: visualizerController.setFrameVisible(modelData.name, checked)
                                    }
                                    ToolButton {
                                        checkable: true
                                        text: "Model"
                                        enabled: modelData.hasModel
                                        checked: modelData.showModel
                                        onToggled: visualizerController.setModelVisible(modelData.name, checked)
                                    }
                                    ToolButton {
                                        checkable: true
                                        text: "Landmarks"
                                        enabled: modelData.hasLandmarks
                                        checked: modelData.showLandmarks
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
                        id: translationCard
                        Layout.fillWidth: true
                        padding: 8
                        property bool editingTranslation: false
                        ColumnLayout {
                            Layout.fillWidth: true
                            Label { text: "Translation (mm)" }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6
                                TextField {
                                    id: txField
                                    Layout.preferredWidth: 72
                                    text: Number(visualizerController.tx).toFixed(2)
                                    readOnly: !translationCard.editingTranslation
                                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                                    placeholderText: "X"
                                    background: Rectangle {
                                        color: txField.readOnly ? "#f5f5f5" : "#ffffff"
                                        border.color: txField.readOnly ? "#d6d6d6" : "#b0b0b0"
                                        radius: 4
                                    }
                                }
                                TextField {
                                    id: tyField
                                    Layout.preferredWidth: 72
                                    text: Number(visualizerController.ty).toFixed(2)
                                    readOnly: !translationCard.editingTranslation
                                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                                    placeholderText: "Y"
                                    background: Rectangle {
                                        color: tyField.readOnly ? "#f5f5f5" : "#ffffff"
                                        border.color: tyField.readOnly ? "#d6d6d6" : "#b0b0b0"
                                        radius: 4
                                    }
                                }
                                TextField {
                                    id: tzField
                                    Layout.preferredWidth: 72
                                    text: Number(visualizerController.tz).toFixed(2)
                                    readOnly: !translationCard.editingTranslation
                                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                                    placeholderText: "Z"
                                    background: Rectangle {
                                        color: tzField.readOnly ? "#f5f5f5" : "#ffffff"
                                        border.color: tzField.readOnly ? "#d6d6d6" : "#b0b0b0"
                                        radius: 4
                                    }
                                }
                                Item { Layout.fillWidth: true }
                                Button {
                                    text: "Edit"
                                    enabled: visualizerController.canEdit && !translationCard.editingTranslation
                                    onClicked: {
                                        translationCard.editingTranslation = true
                                        txField.text = Number(visualizerController.tx).toFixed(2)
                                        tyField.text = Number(visualizerController.ty).toFixed(2)
                                        tzField.text = Number(visualizerController.tz).toFixed(2)
                                    }
                                }
                                Button {
                                    text: "Apply"
                                    enabled: visualizerController.canEdit && translationCard.editingTranslation
                                    onClicked: {
                                        const x = parseFloat(txField.text)
                                        const y = parseFloat(tyField.text)
                                        const z = parseFloat(tzField.text)
                                        if (!isNaN(x)) visualizerController.setTranslation("x", x)
                                        if (!isNaN(y)) visualizerController.setTranslation("y", y)
                                        if (!isNaN(z)) visualizerController.setTranslation("z", z)
                                        translationCard.editingTranslation = false
                                    }
                                }
                            }
                        }
                    }

                    Frame {
                        id: rotationCard
                        Layout.fillWidth: true
                        padding: 8
                        property bool editingRotation: false
                        ColumnLayout {
                            Layout.fillWidth: true
                            Label { text: "Rotation (deg)" }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6
                                TextField {
                                    id: rollField
                                    Layout.preferredWidth: 72
                                    text: Number(visualizerController.roll).toFixed(1)
                                    readOnly: !rotationCard.editingRotation
                                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                                    placeholderText: "Roll"
                                    background: Rectangle {
                                        color: rollField.readOnly ? "#f5f5f5" : "#ffffff"
                                        border.color: rollField.readOnly ? "#d6d6d6" : "#b0b0b0"
                                        radius: 4
                                    }
                                }
                                TextField {
                                    id: pitchField
                                    Layout.preferredWidth: 72
                                    text: Number(visualizerController.pitch).toFixed(1)
                                    readOnly: !rotationCard.editingRotation
                                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                                    placeholderText: "Pitch"
                                    background: Rectangle {
                                        color: pitchField.readOnly ? "#f5f5f5" : "#ffffff"
                                        border.color: pitchField.readOnly ? "#d6d6d6" : "#b0b0b0"
                                        radius: 4
                                    }
                                }
                                TextField {
                                    id: yawField
                                    Layout.preferredWidth: 72
                                    text: Number(visualizerController.yaw).toFixed(1)
                                    readOnly: !rotationCard.editingRotation
                                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                                    placeholderText: "Yaw"
                                    background: Rectangle {
                                        color: yawField.readOnly ? "#f5f5f5" : "#ffffff"
                                        border.color: yawField.readOnly ? "#d6d6d6" : "#b0b0b0"
                                        radius: 4
                                    }
                                }
                                Item { Layout.fillWidth: true }
                                Button {
                                    text: "Edit"
                                    enabled: visualizerController.canEdit && !rotationCard.editingRotation
                                    onClicked: {
                                        rotationCard.editingRotation = true
                                        rollField.text = Number(visualizerController.roll).toFixed(1)
                                        pitchField.text = Number(visualizerController.pitch).toFixed(1)
                                        yawField.text = Number(visualizerController.yaw).toFixed(1)
                                    }
                                }
                                Button {
                                    text: "Apply"
                                    enabled: visualizerController.canEdit && rotationCard.editingRotation
                                    onClicked: {
                                        const r = parseFloat(rollField.text)
                                        const p = parseFloat(pitchField.text)
                                        const y = parseFloat(yawField.text)
                                        if (!isNaN(r)) visualizerController.setRotation("roll", r)
                                        if (!isNaN(p)) visualizerController.setRotation("pitch", p)
                                        if (!isNaN(y)) visualizerController.setRotation("yaw", y)
                                        rotationCard.editingRotation = false
                                    }
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

                    Connections {
                        target: visualizerController
                        function onSelectionChanged() {
                            if (!translationCard.editingTranslation) {
                                txField.text = Number(visualizerController.tx).toFixed(2)
                                tyField.text = Number(visualizerController.ty).toFixed(2)
                                tzField.text = Number(visualizerController.tz).toFixed(2)
                            }
                            if (!rotationCard.editingRotation) {
                                rollField.text = Number(visualizerController.roll).toFixed(1)
                                pitchField.text = Number(visualizerController.pitch).toFixed(1)
                                yawField.text = Number(visualizerController.yaw).toFixed(1)
                            }
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
