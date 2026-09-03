"""Xiaomi S20 joystick and gamepad feature controller."""

import argparse
import getpass
import os
import sys
import time

import pygame
from miio import Device

DEVICE_ID = "1069182766"
DIRECTION_SIID = 7
DIRECTION_PIID = 16
VACUUM_SIID = 2
MODE_PIID = 4
FORWARD, LEFT, RIGHT, BACKWARD, STOP, EXIT = 1, 2, 3, 4, 5, 10
MODES = (0, 1, 2, 3)
MODE_NAMES = ("Süpürme", "Süpürme + paspas", "Paspas", "Önce süpür, sonra paspas")
BUTTON_AUTO = 0
BUTTON_CHARGE = 1
BUTTON_FIND = 2
BUTTON_MODE = 3
HORN_BUTTON = 9
EMERGENCY_BUTTON = 10
START_BUTTON = 7
DEADZONE = 0.1
COMMAND_INTERVAL = 0.1
LT_AXIS = 4
RT_AXIS = 5
TRIGGER_THRESHOLD = 0.2


def send_property(vacuum: Device, siid: int, piid: int, value: int) -> None:
    vacuum.send(
        "set_properties",
        [{"did": DEVICE_ID, "siid": siid, "piid": piid, "value": value}],
    )


def call_action(vacuum: Device, siid: int, aiid: int, params=None) -> None:
    vacuum.send(
        "action",
        {"did": f"call-{siid}-{aiid}", "siid": siid, "aiid": aiid, "in": params or []},
    )


def apply_deadzone(value: float) -> float:
    return 0.0 if abs(value) < DEADZONE else value


def trigger_pressed(value: float) -> bool:
    return value > TRIGGER_THRESHOLD


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Xiaomi S20 özellik ve joystick kontrolü")
    parser.add_argument("--ip", default=os.getenv("VACUUM_IP"))
    parser.add_argument("--token", default=os.getenv("VACUUM_TOKEN"))
    return parser.parse_args()


def request_info(args: argparse.Namespace) -> argparse.Namespace:
    if not args.ip:
        args.ip = input("Robotun IP adresi: ").strip()
    if not args.token:
        args.token = getpass.getpass("32 karakterlik token: ").strip()
    return args


def asset_path(filename: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, filename)


def main() -> None:
    args = request_info(parse_args())
    if not args.ip or not args.token or len(args.token) != 32:
        raise SystemExit("Geçerli IP ve 32 karakterlik token gerekli")

    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        pygame.quit()
        raise SystemExit("Joystick bulunamadı")

    joystick = pygame.joystick.Joystick(0)
    pygame.mixer.init()
    horn_sounds = (pygame.mixer.Sound(asset_path("horn_1.wav")), pygame.mixer.Sound(asset_path("horn_2.wav")))
    horn_index = 0
    vacuum = Device(args.ip, args.token)
    mode_index = 0
    last_button_time = {}
    autonomous_command_sent = False
    cleaning_active = False
    returning_active = False
    control_active = False
    print(f"Joystick bağlandı: {joystick.get_name()}")
    print(f"{args.ip} adresindeki robot bağlantısı hazırlanıyor...")
    vacuum.info()
    print("Bağlantı hazır. START tuşuna basarak kontrolü başlat.")
    print("START tekrar: bağlantıyı kes | A: süpürme | B: şarj | X: bul | Y: mod | Sol kol: korna | Sağ kol: ACİL DUR")

    try:
        while True:
            pygame.event.pump()
            for event in pygame.event.get():
                if event.type != pygame.JOYBUTTONDOWN:
                    continue
                if not control_active and event.button != START_BUTTON:
                    continue
                now = time.monotonic()
                if now - last_button_time.get(event.button, 0) < 0.4:
                    continue
                last_button_time[event.button] = now

                if event.button == HORN_BUTTON:
                    horn_sounds[horn_index].play()
                    print(f"Korna {horn_index + 1} çaldı")
                    horn_index = (horn_index + 1) % len(horn_sounds)
                elif event.button == START_BUTTON:
                    control_active = not control_active
                    if control_active:
                        print("Kontrol aktif")
                    else:
                        print("START: Robot durduruluyor ve bağlantı kesiliyor")
                        return
                elif event.button == EMERGENCY_BUTTON:
                    send_property(vacuum, DIRECTION_SIID, DIRECTION_PIID, STOP)
                    print("ACİL DUR: Robot durduruldu")
                    return
                elif event.button == BUTTON_AUTO:
                    if cleaning_active:
                        call_action(vacuum, VACUUM_SIID, 2)
                        cleaning_active = False
                        autonomous_command_sent = False
                        print("Süpürme iptal edildi")
                    else:
                        if returning_active:
                            call_action(vacuum, VACUUM_SIID, 2)
                            returning_active = False
                        call_action(vacuum, VACUUM_SIID, 1)
                        cleaning_active = True
                        autonomous_command_sent = True
                        print("Otomatik süpürme başladı")
                elif event.button == BUTTON_CHARGE:
                    if returning_active:
                        call_action(vacuum, VACUUM_SIID, 2)
                        returning_active = False
                        autonomous_command_sent = False
                        print("Şarja dönüş iptal edildi")
                    else:
                        if cleaning_active:
                            call_action(vacuum, VACUUM_SIID, 2)
                            cleaning_active = False
                        call_action(vacuum, 3, 1)
                        returning_active = True
                        autonomous_command_sent = True
                        print("Şarj istasyonuna dönüyor")
                elif event.button == BUTTON_FIND:
                    call_action(vacuum, DIRECTION_SIID, 11)
                    print("Robot sesli olarak konumunu bildiriyor")
                elif event.button == BUTTON_MODE:
                    mode_index = (mode_index + 1) % len(MODES)
                    send_property(vacuum, VACUUM_SIID, MODE_PIID, MODES[mode_index])
                    print(f"Mod: {MODE_NAMES[mode_index]}")

            if not control_active:
                time.sleep(COMMAND_INTERVAL)
                continue

            axis_y = apply_deadzone(-joystick.get_axis(1))
            axis_x = apply_deadzone(joystick.get_axis(0))
            left_trigger = trigger_pressed(joystick.get_axis(LT_AXIS))
            right_trigger = trigger_pressed(joystick.get_axis(RT_AXIS))
            has_direction_input = bool(axis_y or axis_x or left_trigger or right_trigger)
            if has_direction_input:
                autonomous_command_sent = False
            if autonomous_command_sent and not has_direction_input:
                time.sleep(COMMAND_INTERVAL)
                continue
            if left_trigger and right_trigger:
                direction = STOP
            elif right_trigger:
                direction = FORWARD
            elif left_trigger:
                direction = BACKWARD
            elif axis_y > DEADZONE:
                direction = FORWARD
            elif axis_y < -DEADZONE:
                direction = BACKWARD
            elif axis_x > DEADZONE:
                direction = RIGHT
            elif axis_x < -DEADZONE:
                direction = LEFT
            else:
                direction = STOP
            if has_direction_input or direction == STOP:
                send_property(vacuum, DIRECTION_SIID, DIRECTION_PIID, direction)
            time.sleep(COMMAND_INTERVAL)
    except KeyboardInterrupt:
        print("Çıkış yapılıyor")
    except Exception as error:
        print(f"Bağlantı koptu veya komut gönderilemedi: {error}")
    finally:
        try:
            send_property(vacuum, DIRECTION_SIID, DIRECTION_PIID, STOP)
            send_property(vacuum, DIRECTION_SIID, DIRECTION_PIID, EXIT)
        except Exception as error:
            print(f"Güvenli durdurma gönderilemedi: {error}")
        pygame.mixer.quit()
        pygame.quit()


if __name__ == "__main__":
    main()
