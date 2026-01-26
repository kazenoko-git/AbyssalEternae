from direct.gui.DirectGui import *
import sys


# ==================================================================================
# 🛠️ ENGINE EDITOR & STORY
# ==================================================================================

class InputSystem:
    def __init__(self):
        self.keys = {}
        base.buttonThrowers[0].node().setButtonDownEvent('buttonDown')
        base.buttonThrowers[0].node().setButtonUpEvent('buttonUp')
        base.accept('buttonDown', self.on_key_down)
        base.accept('buttonUp', self.on_key_up)

    def on_key_down(self, key):
        self.keys[key] = True
        if key == 'tab': base.engine.editor.toggle()
        if key == 'escape': sys.exit()

    def on_key_up(self, key):
        self.keys[key] = False

    def get_key(self, key):
        return self.keys.get(key, False)


class StorySystem:
    def __init__(self):
        self.data = {
            "intro": {"text": "Welcome, Traveler. The engine awaits.", "next": "forest"},
            "forest": {"text": "You see a dark forest ahead.", "next": "intro"}
        }
        self.current = "intro"

        # HUD
        self.panel = DirectFrame(frameColor=(0, 0, 0, 0.7), frameSize=(-1, 1, -0.3, 0), pos=(0, 0, -0.7),
                                 parent=base.aspect2d)
        self.text = DirectLabel(parent=self.panel, text="", text_scale=0.06, text_fg=(1, 1, 1, 1), pos=(0, 0, 0.1))
        self.btn = DirectButton(parent=self.panel, text="Next >", scale=0.05, pos=(0.8, 0, -0.1), command=self.advance)
        self.update_display()

    def update_node(self, node_id, text):
        if node_id not in self.data:
            self.data[node_id] = {"text": text, "next": "intro"}
        else:
            self.data[node_id]["text"] = text
        self.update_display()

    def advance(self):
        node = self.data.get(self.current)
        if node and "next" in node:
            self.current = node["next"]
            self.update_display()

    def update_display(self):
        node = self.data.get(self.current, {"text": "MISSING NODE"})
        self.text['text'] = node['text']


class EngineEditor:
    def __init__(self):
        self.frame = DirectFrame(frameColor=(0.15, 0.15, 0.15, 0.95), frameSize=(-0.6, 0.6, -0.8, 0.8),
                                 pos=(-1.2, 0, 0), parent=base.aspect2d)
        self.title = DirectLabel(parent=self.frame, text="PY-UNITY EDITOR", scale=0.07, pos=(0, 0, 0.7),
                                 text_fg=(1, 1, 1, 1))

        self.tabs = ["Inspector", "Story"]
        self.current_tab = "Inspector"
        self.tab_buttons = []

        # Inspector Elements
        self.obj_list_title = DirectLabel(parent=self.frame, text="Hierarchy", scale=0.04, pos=(-0.4, 0, 0.5),
                                          text_fg=(0.7, 0.7, 0.7, 1))
        self.selected_obj = None
        self.inputs = {}

        # Story Editor Elements
        self.story_node_input = None
        self.story_text_input = None

        self.create_tabs()
        self.create_inspector_ui()
        self.create_story_ui()
        self.refresh_ui()

    def create_tabs(self):
        x = -0.3
        for tab in self.tabs:
            btn = DirectButton(parent=self.frame, text=tab, scale=0.05, pos=(x, 0, 0.6), command=self.switch_tab,
                               extraArgs=[tab])
            self.tab_buttons.append(btn)
            x += 0.4

    def switch_tab(self, tab):
        self.current_tab = tab
        self.refresh_ui()

    def create_inspector_ui(self):
        self.inspector_node = self.frame.attachNewNode("InspectorNode")
        # Position Editors
        DirectLabel(parent=self.inspector_node, text="Position X/Y/Z", scale=0.04, pos=(0.3, 0, 0.5))
        for i, axis in enumerate(['x', 'y', 'z']):
            self.inputs[axis] = DirectEntry(parent=self.inspector_node, scale=0.04, pos=(0.2, 0, 0.4 - (i * 0.1)),
                                            width=6, command=self.on_transform_change)

    def create_story_ui(self):
        self.story_node_ui = self.frame.attachNewNode("StoryNode")
        DirectLabel(parent=self.story_node_ui, text="Story Node ID", scale=0.04, pos=(0, 0, 0.4))
        self.story_id_input = DirectEntry(parent=self.story_node_ui, scale=0.04, pos=(-0.2, 0, 0.3), width=10,
                                          initialText="intro")

        DirectLabel(parent=self.story_node_ui, text="Dialogue Text", scale=0.04, pos=(0, 0, 0.1))
        self.story_content_input = DirectEntry(parent=self.story_node_ui, scale=0.04, pos=(-0.4, 0, 0.0), width=20,
                                               initialText="...")

        DirectButton(parent=self.story_node_ui, text="Update Node", scale=0.05, pos=(0, 0, -0.2),
                     command=self.update_story_data)

    def refresh_ui(self):
        if self.current_tab == "Inspector":
            self.inspector_node.show()
            self.story_node_ui.hide()
        else:
            self.inspector_node.hide()
            self.story_node_ui.show()

    def on_transform_change(self, text):
        if not self.selected_obj: return
        try:
            x = float(self.inputs['x'].get())
            y = float(self.inputs['y'].get())
            z = float(self.inputs['z'].get())
            self.selected_obj.node.setPos(x, y, z)
        except:
            pass

    def update_story_data(self):
        node_id = self.story_id_input.get()
        text = self.story_content_input.get()
        base.engine.story_system.update_node(node_id, text)
        print(f"Updated Story Node [{node_id}]: {text}")

    def toggle(self):
        current_x = self.frame.getX()
        target = 0 if current_x < -1 else -1.2
        self.frame.setX(target)
        base.engine.editor_active = (target == 0)