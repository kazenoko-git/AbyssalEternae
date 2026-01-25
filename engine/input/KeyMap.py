from panda3d.core import KeyboardButton, MouseButton


class KeyMap:
    Forward = KeyboardButton.asciiKey(b'w')
    Backward = KeyboardButton.asciiKey(b's')
    Left = KeyboardButton.asciiKey(b'a')
    Right = KeyboardButton.asciiKey(b'd')

    Jump = KeyboardButton.space()

    MouseLeft = MouseButton.one()
    MouseRight = MouseButton.three()
