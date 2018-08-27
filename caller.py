#!/usr/bin/env python

import sys
import click
import wave
import pjsua as pj
import signal
import threading
import time


def logger_callback(level, message, _len):
    print level, message


class NoopAccountCallback(pj.AccountCallback):
    sem = None

    def __init__(self, account=None):
        pj.AccountCallback.__init__(self, account)

    def wait(self):
        self.sem = threading.Semaphore(0)
        self.sem.acquire()

    def on_reg_state(self):
        if self.sem:
            if self.account.info().reg_status >= 200:
                self.sem.release()

    def on_incoming_call(self, incoming_call):
        incoming_call.answer(488, "Not Acceptable Here")


class PlayWaveCallCallback(pj.CallCallback):
    in_call = True
    audio_file = None
    last_state_code = 0
    thread = None
    event = None

    def __init__(self, audio_file, outgoing_call=None):
        self.audio_file = audio_file
        pj.CallCallback.__init__(self, outgoing_call)

    def on_state(self):
        self.last_state_code = self.call.info().last_code

        print "Call with", self.call.info().remote_uri,
        print "is", self.call.info().state_text,
        print "last code =", self.last_state_code,
        print "(" + self.call.info().last_reason + ")"

        if self.call.info().state == pj.CallState.DISCONNECTED:
            self.in_call = False

        elif self.call.info().state == pj.CallState.CONFIRMED:
            self.event = threading.Event()
            self.thread = threading.Thread(
                target=thread_wav,
                name="music",
                args=(self.audio_file, self.call, self.event)
            )
            self.thread.start()

    def destroy(self):
        self.in_call = False
        if self.event is not None:
            self.event.set()
        if self.call is not None:
            self.call.hangup()


def thread_wav(audio_file, call, event):
    pj.Lib.instance().thread_register("music")
    loc = pj.Lib.instance().auto_lock()
    wave_time = get_wave_file_duration(audio_file)
    wav_player_id = pj.Lib.instance().create_player(audio_file, loop=False)
    wav_slot = pj.Lib.instance().player_get_slot(wav_player_id)

    start = time.time()
    end = start + wave_time
    pj.Lib.instance().conf_connect(wav_slot, call.info().conf_slot)
    try:
        while (time.time() < end) and not event.wait(1):
            time.sleep(0.001)
            del loc
            loc = pj.Lib.instance().auto_lock()
            pj.Lib.instance().conf_connect(wav_slot, call.info().conf_slot)
        call.hangup()
        pj.Lib.instance().player_destroy(wav_player_id)
    except:
        pass


def get_wave_file_duration(filepath):
    wave_file = wave.open(filepath)
    time = (1.0 * wave_file.getnframes()) / wave_file.getframerate()
    wave_file.close()

    return time


def make_callee_uri(callee, server):
    if callee.startswith("sip:"):
        return callee

    return "sip:" + callee + "@" + server


class SipCaller(object):
    callback = None
    account = None
    exiting = False
    verbose = 0

    def __init__(self, verbose):
        self.pjsip = pj.Lib()
        self.verbose = verbose

    def start(self):
        ua = pj.UAConfig()
        ua.nameserver = ['8.8.8.8', '8.8.4.4']
        ua.user_agent = "PJSIP Python EasyPhone"

        media = pj.MediaConfig()
        media.enable_ice = True

        logger = pj.LogConfig(level=self.verbose, callback=logger_callback)

        self.pjsip.init(ua_cfg=ua, media_cfg=media, log_cfg=logger)
        self.pjsip.create_transport(pj.TransportType.TCP, pj.TransportConfig())
        self.pjsip.set_null_snd_dev()
        self.pjsip.start()
        self.pjsip.handle_events()

    def register(self, login, server, password, realm="*"):
        config = pj.AccountConfig()
        config.id = "sip:" + login + "@" + server
        config.reg_uri = "sip:" + server + ";transport=tcp"

        config.auth_cred = [pj.AuthCred(realm, login, password)]

        account_callback = NoopAccountCallback()
        self.account = self.pjsip.create_account(config, cb=account_callback)
        account_callback.wait()

    def make_call(self, uri, wav):
        try:
            print "Call to", uri
            self.callback = PlayWaveCallCallback(wav)
            self.account.make_call(uri, cb=self.callback)
            while self.callback.in_call:
                pass

            print "Result: ", self.get_last_code()
        except pj.Error, e:
            print "Exception: " + str(e)
            return None

    def get_last_code(self):
        if self.callback:
            return self.callback.last_state_code
        return 0

    def destroy(self):
        if self.callback:
            self.callback.destroy()
            del self.callback
        self.pjsip.destroy()
        del self.pjsip


@click.command()
@click.option('--server', '-s', default="sip.zadarma.com", required=True, help="SIP Server", type=str)
@click.option('--login', '-l', required=True, help="SIP Username", type=str)
@click.option('--password', '-p', required=True, help="SIP password", type=str)
@click.option('--realm', '-r', default="*", help="SIP realm", type=str)
@click.argument('callee', type=str)
@click.argument('wav', envvar='WAV', type=click.Path(exists=True))
@click.option('-v', '--verbose', count=True, help="Verbosity 0-5")
def cli(server, login, password, realm, callee, wav, verbose):
    server = str(server)
    login = str(login)
    password = str(password)
    realm = str(realm)
    callee = str(callee)
    caller = SipCaller(verbose)

    def on_signal(_signal, _frame):
        print ""
        print "Got exit signal"
        print "Result: ", caller.get_last_code()
        caller.destroy()
        sys.exit(0)

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    try:
        caller.start()
        caller.register(login, server, password, realm)
        if str(caller.account.info().reg_status) != "200":
            print "Registration error", caller.account.info().info().reg_status
            sys.exit(2)

        print "Registration complete, status=", caller.account.info().reg_status, \
            "(" + caller.account.info().reg_reason + ")"
        caller.make_call(make_callee_uri(callee, server), wav)
    except pj.Error:
        caller.destroy()
        sys.exit(1)

    caller.destroy()
    sys.exit(0)


if __name__ == "__main__":
    cli()
