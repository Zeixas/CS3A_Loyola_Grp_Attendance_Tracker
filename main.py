from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.utils import platform
from kivy.clock import Clock


class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Main layout for the login screen
        layout = BoxLayout(orientation='vertical', padding=30, spacing=20)

        layout.add_widget(Label(text="NFC App Login", font_size='32sp', size_hint_y=0.2))

        # Username Field
        self.username = TextInput(
            hint_text="Username",
            multiline=False,
            size_hint_y=None,
            height='50dp'
        )
        layout.add_widget(self.username)

        # Password Field
        self.password = TextInput(
            hint_text="Password",
            password=True,
            multiline=False,
            size_hint_y=None,
            height='50dp'
        )
        layout.add_widget(self.password)

        # Login Button
        login_btn = Button(text="Login", size_hint_y=None, height='60dp')
        login_btn.bind(on_press=self.do_login)
        layout.add_widget(login_btn)

        # Push everything to the top/center
        layout.add_widget(Label())

        self.add_widget(layout)

    def do_login(self, instance):
        # Placeholder authentication logic
        user = self.username.text
        pwd = self.password.text

        # For now, we allow any login. Add your API/Database check here.
        print(f"Logging in with {user}")

        # Switch to NFC Screen
        self.manager.current = 'nfc_screen'


class NFCScanner(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)

        self.status_label = Label(
            text="Waiting for NFC Tag...",
            font_size='24sp',
            halign='center'
        )
        layout.add_widget(self.status_label)

        # Logout / Back button
        logout_btn = Button(text="Log Out", size_hint_y=None, height='50dp')
        logout_btn.bind(on_press=self.do_logout)
        layout.add_widget(logout_btn)

        self.add_widget(layout)

        # Only initialize Android classes if running on Android
        self.nfc_adapter = None
        if platform == 'android':
            self.init_nfc()

    def do_logout(self, instance):
        self.manager.current = 'login_screen'

    def init_nfc(self):
        try:
            from jnius import autoclass, cast
            from android.runnable import run_on_ui_thread
            from android import activity

            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            NfcAdapter = autoclass('android.nfc.NfcAdapter')
            Intent = autoclass('android.content.Intent')
            PendingIntent = autoclass('android.app.PendingIntent')

            self.activity = PythonActivity.mActivity
            self.nfc_adapter = NfcAdapter.getDefaultAdapter(self.activity)

            if not self.nfc_adapter:
                self.update_status("Error: NFC hardware not found.")
                return

            # Create PendingIntent
            # FLAG_MUTABLE = 33554432, FLAG_ACTIVITY_SINGLE_TOP = 536870912
            self.pending_intent = PendingIntent.getActivity(
                self.activity, 0,
                Intent(self.activity, self.activity.getClass()).addFlags(536870912),
                33554432
            )

            activity.bind(on_new_intent=self.on_new_intent)

        except Exception as e:
            self.update_status(f"Init Error: {str(e)}")

    def on_new_intent(self, intent):
        try:
            from jnius import autoclass
            NfcAdapter = autoclass('android.nfc.NfcAdapter')

            if NfcAdapter.ACTION_TAG_DISCOVERED == intent.getAction() or \
                    NfcAdapter.ACTION_TECH_DISCOVERED == intent.getAction() or \
                    NfcAdapter.ACTION_NDEF_DISCOVERED == intent.getAction():
                tag = intent.getParcelableExtra(NfcAdapter.EXTRA_TAG)
                tag_id_bytes = tag.getId()
                tag_id_hex = ''.join('{:02x}'.format(b & 0xff) for b in tag_id_bytes).upper()

                self.update_status(f"Tag Detected!\nID: {tag_id_hex}")

        except Exception as e:
            self.update_status(f"Read Error: {str(e)}")

    def update_status(self, text):
        def _update(dt):
            self.status_label.text = text

        Clock.schedule_once(_update)

    def enable_nfc(self):
        """Called by App when this screen is active and app resumes."""
        if self.nfc_adapter:
            self.nfc_adapter.enableForegroundDispatch(
                self.activity, self.pending_intent, None, None
            )

    def disable_nfc(self):
        """Called by App when pausing or switching screens."""
        if self.nfc_adapter:
            self.nfc_adapter.disableForegroundDispatch(self.activity)


class NFCApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login_screen'))
        sm.add_widget(NFCScanner(name='nfc_screen'))
        return sm

    def on_resume(self):
        # Only enable NFC if we are currently on the NFC screen
        if self.root.current == 'nfc_screen':
            self.root.get_screen('nfc_screen').enable_nfc()

    def on_pause(self):
        # Disable NFC if we are currently on the NFC screen
        if self.root.current == 'nfc_screen':
            self.root.get_screen('nfc_screen').disable_nfc()
        return True


if __name__ == '__main__':
    NFCApp().run()
