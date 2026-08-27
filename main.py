from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.clock import Clock
import threading

try:
    from jnius import autoclass
    ANDROID = True
except:
    ANDROID = False

class DiagnosticApp(App):
    def build(self):
        self.title = "Burgman Master Diagnostic"
        self.is_connected = False
        self.bluetooth_socket = None
        self.output_stream = None

        root = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # TOP BAR
        top_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        self.status_label = Label(text="Status: Disconnected", color=(1, 0.2, 0.2, 1), bold=True)
        connect_btn = Button(text="Connect BT", background_color=(0.1, 0.6, 0.8, 1))
        connect_btn.bind(on_press=self.connect_bluetooth)
        top_layout.add_widget(self.status_label)
        top_layout.add_widget(connect_btn)
        root.add_widget(top_layout)

        # TERMINAL OUTPUT
        self.terminal_log = Label(
            text="[System] Initialized. Ready to connect...\n",
            size_hint_y=None,
            halign='left',
            valign='top',
            markup=True
        )
        self.terminal_log.bind(texture_size=self.terminal_log.setter('size'))
        
        scroll = ScrollView(size_hint=(1, 0.45))
        scroll.add_widget(self.terminal_log)
        root.add_widget(scroll)

        # BUTTONS GRID
        buttons_grid = GridLayout(cols=4, spacing=5, size_hint_y=0.3)
        commands = [
            ("UNLOCK", "unlock"), ("START", "start"), ("LOCK", "lock"), ("STATUS", "status"),
            ("J1", "J1"), ("J2", "J2"), ("RESET", "reset"), ("TEST", "test")
        ]

        for label_text, cmd in commands:
            btn = Button(text=label_text, background_color=(0.3, 0.3, 0.3, 1))
            btn.bind(on_press=lambda x, c=cmd: self.send_command(c))
            buttons_grid.add_widget(btn)

        root.add_widget(buttons_grid)

        # BOTTOM CUSTOM INPUT & SEND
        bottom_layout = BoxLayout(size_hint_y=None, height=50, spacing=5)
        self.custom_input = TextInput(
            hint_text="Type custom command...",
            multiline=False,
            size_hint_x=0.8
        )
        self.custom_input.bind(on_text_validate=self.send_custom_command)
        
        send_btn = Button(text="SEND", size_hint_x=0.2, background_color=(0.2, 0.7, 0.3, 1))
        send_btn.bind(on_press=self.send_custom_command)

        bottom_layout.add_widget(self.custom_input)
        bottom_layout.add_widget(send_btn)
        root.add_widget(bottom_layout)

        return root

    def log(self, message):
        Clock.schedule_once(lambda dt: self._update_log(message))

    def _update_log(self, message):
        self.terminal_log.text += message + "\n"

    def connect_bluetooth(self, instance):
        if not ANDROID:
            self.log("[Error] Bluetooth works only on Android!")
            return
        threading.Thread(target=self._bt_connect_thread).start()

    def _bt_connect_thread(self):
        try:
            self.log("[BT] Searching paired devices...")
            BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
            adapter = BluetoothAdapter.getDefaultAdapter()
            paired_devices = adapter.getBondedDevices().toArray()
            
            target_device = paired_devices[0] if len(paired_devices) > 0 else None
            for device in paired_devices:
                if "ESP32" in device.getName() or "HC-" in device.getName():
                    target_device = device
                    break

            if target_device:
                self.log(f"[BT] Connecting to {target_device.getName()}...")
                UUID = autoclass('java.util.UUID')
                uuid = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")
                socket = target_device.createRfcommSocketToServiceRecord(uuid)
                socket.connect()
                
                self.bluetooth_socket = socket
                self.output_stream = socket.getOutputStream()
                self.is_connected = True
                
                Clock.schedule_once(lambda dt: self.update_status_ui(True))
                self.log("[BT] Connected Successfully!")
            else:
                self.log("[BT Error] No device found!")
        except Exception as e:
            self.log(f"[BT Error] {str(e)}")

    def update_status_ui(self, status):
        if status:
            self.status_label.text = "Status: Connected"
            self.status_label.color = (0.2, 1, 0.2, 1)
        else:
            self.status_label.text = "Status: Disconnected"
            self.status_label.color = (1, 0.2, 0.2, 1)

    def send_command(self, cmd):
        if not self.is_connected or not self.output_stream:
            self.log("[Error] Not connected!")
            return
        try:
            self.output_stream.write((cmd + "\n").encode('utf-8'))
            self.output_stream.flush()
            self.log(f">> Sent: {cmd}")
        except Exception as e:
            self.log(f"[Send Error] {str(e)}")

    def send_custom_command(self, instance):
        text = self.custom_input.text.strip()
        if text:
            self.send_command(text)
            self.custom_input.text = ""

if __name__ == '__main__':
    DiagnosticApp().run()
