import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

Panel {
    id: root
    moduleName: "simondrey.agents-capslock"
    ipcTarget: "simondrey.agents-capslock"
    manageIpc: false
    IpcHandler {
        target: root.ipcTarget
        function open(): void { root.open() }
        function close(): void { root.close() }
        function toggle(): void { root.toggle() }
        function activate(): void { root.choose(root.selectedIndex) }
    }
    property var entries: []
    property string selectedId: ""
    property string errorText: ""
    readonly property string cli: Qt.resolvedUrl("bin/attention").toString().replace(/^file:\/\//, "")
    readonly property int selectedIndex: {
        for (var i = 0; i < entries.length; i++) if (entries[i].id === selectedId) return i
        return entries.length ? 0 : -1
    }
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight
    function refresh() {
        try {
            var data = JSON.parse(snapshot.text())
            entries = data.entries || []
            if (selectedIndex >= 0) selectedId = entries[selectedIndex].id
        } catch (e) { /* Atomic writer may not have created its first snapshot yet. */ }
    }
    function move(delta) {
        if (!entries.length) return
        var i = Math.max(0, Math.min(entries.length - 1, selectedIndex + delta))
        selectedId = entries[i].id
        list.positionViewAtIndex(i, ListView.Contain)
    }
    function choose(index) {
        if (activation.running || focusDelay.running || index < 0 || index >= entries.length) return
        var e = entries[index]
        errorText = ""
        activation.command = [cli, "focus", e.id, "--revision", e.revision]
        // Release the panel's keyboard focus before asking Hyprland to focus the caller.
        root.close()
        focusDelay.start()
    }
    onOpenedChanged: if (opened) { refresh(); Qt.callLater(function() { catcher.forceActiveFocus() }) }
    Timer { id: focusDelay; interval: 200; onTriggered: activation.running = true }
    Process {
        id: activation
        stderr: StdioCollector { onStreamFinished: root.errorText = text.trim() }
        onExited: function(code) { if (code !== 0) root.open() }
    }
    FileView {
        id: snapshot
        path: Quickshell.env("XDG_RUNTIME_DIR") + "/omarchy-attention/snapshot.json"
        watchChanges: true
        printErrors: false
        onFileChanged: reload()
        onLoaded: root.refresh()
    }
    BarIconButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        text: root.entries.length ? "󰂞 " + root.entries.length : "󰂜"
        active: root.entries.length > 0
        tooltipText: root.entries.length ? root.entries.length + " calls for attention" : "No calls for attention"
        onPressed: root.toggle()
    }
    KeyboardPanel {
        id: panel
        anchorItem: button
        owner: root
        bar: root.bar
        open: root.opened
        focusTarget: catcher
        contentWidth: panel.fittedContentWidth(Style.space(440))
        contentHeight: panel.fittedContentHeight(Style.space(120 + Math.min(root.entries.length, 6) * 78), Style.space(620))
        PanelKeyCatcher {
            id: catcher
            anchors.fill: parent
            onMoveRequested: function(dx, dy) { root.move(dy) }
            onActivateRequested: root.choose(root.selectedIndex)
            onCloseRequested: root.close()
            onTabRequested: function(direction) { root.switchPanel(direction) }
            Column {
                anchors.fill: parent
                spacing: Style.space(12)
                Text {
                    text: "Agents CapsLock"; color: Color.foreground
                    font.family: Style.font.family; font.pixelSize: Style.space(22); font.bold: true
                }
                Text {
                    width: parent.width
                    text: root.errorText || (root.entries.length ? "Select a call to return to its tool" : "All clear — nothing needs your attention")
                    color: root.errorText ? Color.urgent : Color.foreground
                    opacity: root.errorText ? 1 : 0.65
                    font.family: Style.font.family; font.pixelSize: Style.space(12)
                    wrapMode: Text.Wrap
                }
                ListView {
                    id: list
                    width: parent.width
                    height: Math.max(0, catcher.height - y - Style.space(24))
                    clip: true; spacing: Style.space(6)
                    model: root.entries
                    ScrollBar.vertical: ScrollBar {}
                    delegate: Rectangle {
                        required property var modelData
                        required property int index
                        width: list.width; height: Style.space(72); radius: Style.space(6)
                        color: index === root.selectedIndex ? Qt.alpha(Color.foreground, 0.12) : Qt.alpha(Color.foreground, 0.04)
                        border.width: index === root.selectedIndex ? 1 : 0
                        border.color: Color.accent
                        Column {
                            anchors.fill: parent; anchors.margins: Style.space(10); spacing: Style.space(5)
                            Text {
                                width: parent.width; text: modelData.title
                                color: Color.foreground; font.family: Style.font.family
                                font.pixelSize: Style.space(14); elide: Text.ElideRight
                                textFormat: Text.PlainText
                            }
                            Text {
                                width: parent.width
                                text: modelData.source + " · " + modelData.status + " · " + modelData.target.kind + (modelData.target.pane ? " " + modelData.target.pane : "")
                                color: Color.foreground; opacity: 0.6; font.family: Style.font.family
                                font.pixelSize: Style.space(11); elide: Text.ElideRight
                                textFormat: Text.PlainText
                            }
                        }
                        MouseArea {
                            anchors.fill: parent; hoverEnabled: true
                            onEntered: root.selectedId = modelData.id
                            onClicked: root.choose(index)
                        }
                    }
                }
            }
        }
    }
}
